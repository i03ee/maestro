"""مزوّد HTTP لواجهة متوافقة مع OpenAI — بلا أي تبعية خارجية.

لماذا `urllib` لا `requests` أو `httpx`: النواة يجب أن تعمل بلا تثبيت وبلا
شبكة في الاختبار. الاستعمال: `urllib.request` من المكتبة القياسية يكفي لطلب
JSON بسيط، والاختبار يشغّل خادماً محلياً حقيقياً (http.server) فيُختبر
الطلب والاستجابة فعلياً — لا محاكاة.

الواجهة المتوافقة مع OpenAI: `POST {base_url}/chat/completions` بجسم
`{model, messages, max_tokens, temperature}`، والردّ `choices[0].message.content`.
"""

from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from dataclasses import dataclass

from .base import CompletionRequest, CompletionResponse, ModelProfile


class ProviderError(RuntimeError):
    """فشل المزوّد: رفض الخادم، أو ردّ غير متوقع."""


class MissingCredentials(ProviderError):
    """مفتاح الواجهة غير مضبوط."""


@dataclass
class OpenAICompatibleProvider:
    """مزوّد يتكلم HTTP مع واجهة متوافقة مع OpenAI."""

    name: str
    timeout_seconds: int = 60
    temperature: float = 0.2
    extra_headers: dict[str, str] | None = None

    def complete(self, request: CompletionRequest, profile: ModelProfile) -> CompletionResponse:
        """يرسل الطلب ويعيد الردّ معدَّلاً."""
        if not profile.base_url:
            raise ProviderError(f"لا يوجد عنوان أساسي في بطاقة النموذج {profile.name}.")
        if profile.api_key_env and not os.environ.get(profile.api_key_env):
            raise MissingCredentials(
                f"المتغيّر {profile.api_key_env} غير مضبوط؛ لا يُرسَل أي طلب بلا مفتاح."
            )

        payload = {
            "model": profile.model,
            "messages": [{"role": "user", "content": request.prompt}],
            "max_tokens": request.max_output_tokens,
            "temperature": self.temperature,
        }
        if profile.extra_body:
            try:
                extra = json.loads(profile.extra_body)
            except json.JSONDecodeError as error:
                raise ProviderError(
                    f"extra_body في بطاقة {profile.name} ليس JSON صالحاً."
                ) from error
            if not isinstance(extra, dict):
                raise ProviderError(f"extra_body في بطاقة {profile.name} ليس كائناً.")
            payload.update(extra)
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
        }
        if profile.api_key_env:
            headers["Authorization"] = f"Bearer {os.environ[profile.api_key_env]}"
        if self.extra_headers:
            headers.update(self.extra_headers)

        url = f"{profile.base_url.rstrip('/')}/chat/completions"
        data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        http_request = urllib.request.Request(url, data=data, headers=headers, method="POST")

        try:
            with urllib.request.urlopen(http_request, timeout=self.timeout_seconds) as response:
                body = response.read().decode("utf-8")
        except urllib.error.HTTPError as error:
            detail = error.read().decode("utf-8", errors="ignore")[:300]
            raise ProviderError(f"الخادم ردّ {error.code}: {detail}") from error
        except urllib.error.URLError as error:
            raise ProviderError(f"تعذّر الاتصال بـ{url}: {error.reason}") from error

        return self._parse(body, profile)

    def _parse(self, body: str, profile: ModelProfile) -> CompletionResponse:
        """يحلّل ردّ OpenAI-style ويستخرج النص واستهلاك الرموز."""
        try:
            data = json.loads(body)
        except json.JSONDecodeError as error:
            raise ProviderError(f"الردّ ليس JSON: {error}") from error
        if not isinstance(data, dict):
            raise ProviderError("الردّ ليس كائن JSON.")
        choices = data.get("choices")
        if not isinstance(choices, list) or not choices:
            raise ProviderError("الردّ بلا اختيارات.")
        message = choices[0].get("message") or {}
        text = message.get("content")
        if not isinstance(text, str) or not text.strip():
            # نماذج التفكير تستهلك الرموز في reasoning ثم تُعيد content فارغاً.
            # هذه رسالة تشخيص لا غموض: من رفعَ سقف الرموز أو خفّض الجهد.
            reasoning = message.get("reasoning")
            if isinstance(reasoning, str) and reasoning.strip():
                raise ProviderError(
                    "الردّ بلا نص: النموذج استهلك الرموز في التفكير (reasoning) ولم يُخرج "
                    "إجابة. ارفع max_output_tokens أو اضبط reasoning.effort على low."
                )
            raise ProviderError("الردّ بلا نص في message.content.")
        usage = data.get("usage") or {}
        tokens_in = int(usage.get("prompt_tokens", 0) or 0)
        tokens_out = int(usage.get("completion_tokens", 0) or 0)
        return CompletionResponse(
            text=text,
            tokens_in=tokens_in,
            tokens_out=tokens_out,
            model=str(data.get("model", profile.model)),
        )

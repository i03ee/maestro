#!/usr/bin/env python3
"""مِقياس حمل بسيط — بلا تبعيات، وبلا تسامح.

يقيس زمن الاستجابة تحت تزامن معيَّن مقابل **خادم محلي تجريبي**، ويتحقق من
ثلاثة أشياء: لا خطأ واحد، وزمن الاستجابة95 تحت الحدّ، وعدد الطلبات المنفَّذة
كما طُلب.

لماذا خادم محلي؟ لأن الهدف **قياس مسار التنفيذ** (الطلب ← الموجّه ← المزوّد
← السجل) لا قياس الشبكة. ولأن الاختبار يجب أن يكون حتمياً وبلا خدمة خارجية.

    python3 scripts/load_check.py --requests 200 --concurrency 20
"""

from __future__ import annotations

import argparse
import json
import statistics
import sys
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from maestro.evidence.log import EvidenceLog  # noqa: E402
from maestro.guards.budget import BudgetGuard  # noqa: E402
from maestro.guards.permission import PermissionGuard  # noqa: E402
from maestro.routing.base import CompletionRequest, CompletionResponse, ModelProfile  # noqa: E402
from maestro.routing.http_provider import OpenAICompatibleProvider  # noqa: E402
from maestro.routing.router import ModelRouter  # noqa: E402
from maestro.runtime.registry import CapabilityRegistry  # noqa: E402
from maestro.runtime.runner import CapabilityRunner  # noqa: E402
from maestro.runtime.spec import CapabilitySpec  # noqa: E402


class _Handler(BaseHTTPRequestHandler):
    """خادم تجريبي يردّ بردّ OpenAI-style."""

    protocol_version = "HTTP/1.1"

    def do_POST(self) -> None:  # noqa: N802 — اسم الطريق في المكتبة القياسية
        length = int(self.headers.get("Content-Length", "0"))
        self.rfile.read(length)
        body = json.dumps(
            {
                "model": "stub",
                "choices": [{"message": {"role": "assistant", "content": "نتيجة"}}],
                "usage": {"prompt_tokens": 20, "completion_tokens": 10},
            }
        ).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *args) -> None:  # noqa: A003
        return


def run_load(
    *, requests: int, concurrency: int, max_p95_ms: float, evidence_path: Path
) -> dict[str, object]:
    """يشغّل الحمل ويعيد تقريراً."""
    server = _Server(("127.0.0.1", 0), _Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    base_url = f"http://127.0.0.1:{server.server_address[1]}/v1"

    profile = ModelProfile(
        name="stub",
        tier="api",
        model="stub",
        cost_in_per_mtok=0.0,
        cost_out_per_mtok=0.0,
        max_context=8192,
        api_key_env="MAESTRO_LOAD_KEY",
        base_url=base_url,
    )
    router = ModelRouter(
        providers={"stub": OpenAICompatibleProvider(name="stub")},
        profiles={"stub": profile},
        budget=BudgetGuard(max_cost_usd=1000.0, max_tokens=10_000_000),
    )
    registry = CapabilityRegistry()
    registry.register(
        CapabilitySpec(
            name="media.render",
            description_ar="قدرة توضيحية للقياس",
            required_tools=("render.image",),
            default_authority=1,
        )
    )
    runner = CapabilityRunner(
        registry,
        router,
        PermissionGuard(allowed_capabilities=frozenset({"media.render"}), max_authority=1),
        EvidenceLog(evidence_path),
    )
    document = {
        "ir_version": "1.0",
        "capability": "media.render",
        "intent": "قياس حمل على مسار التنفيذ",
        "authority": 1,
        "steps": [{"id": "s1", "agent": "renderer", "action": "رسم", "tools": ["render.image"]}],
        "budget": {"max_tokens": 4000, "max_cost_usd": 0.1, "max_wall_seconds": 30},
    }

    latencies: list[float] = []
    errors: list[str] = []
    lock = threading.Lock()
    import os

    os.environ.setdefault("MAESTRO_LOAD_KEY", "local-test-key")

    def worker(count: int) -> None:
        for _ in range(count):
            started = time.perf_counter()
            try:
                report = runner.run(document)
                if not report.ok:
                    with lock:
                        errors.append(f"{report.stage}: {report.detail_ar}")
            except Exception as error:  # noqa: BLE001 — يُسجَّل
                with lock:
                    errors.append(f"{type(error).__name__}: {error}")
            elapsed = (time.perf_counter() - started) * 1000
            with lock:
                latencies.append(elapsed)

    try:
        per_worker = requests // concurrency
        remainder = requests - per_worker * concurrency
        threads: list[threading.Thread] = []
        for index in range(concurrency):
            count = per_worker + (1 if index < remainder else 0)
            worker_thread = threading.Thread(target=worker, args=(count,))
            threads.append(worker_thread)
            worker_thread.start()
        for worker_thread in threads:
            worker_thread.join()
    finally:
        server.shutdown()
        server.server_close()

    ordered = sorted(latencies)
    p95 = ordered[min(len(ordered) - 1, int(len(ordered) * 0.95))] if ordered else 0.0
    return {
        "requests": requests,
        "completed": len(latencies),
        "errors": len(errors),
        "error_samples": errors[:5],
        "p50_ms": round(statistics.median(ordered), 2) if ordered else 0.0,
        "p95_ms": round(p95, 2),
        "max_p95_ms": max_p95_ms,
        "passed": not errors and len(latencies) == requests and p95 <= max_p95_ms,
    }


class _Server(ThreadingHTTPServer):
    """خادم تجريبي بطابور قبول واسع.

    الافتراضي في المكتبة القياسية 5 اتصالات، فينتظر ما زاد عن ذلك في الطابور
    حتى إعادة الإرسال بعد ثانية — وهو ما يظهر كـ p95 ≈ 1000ms.
    حتى إعادة الإرسال بعد ثانية — وهو ما يظهر كـ p95 ≈ 1000ms.
    """

    request_queue_size = 128
    daemon_threads = True


def main() -> int:
    """يشغّل المقياس ويطبع التقرير."""
    parser = argparse.ArgumentParser(description="مِقياس حمل بلا تبعيات.")
    parser.add_argument("--requests", type=int, default=100)
    parser.add_argument("--concurrency", type=int, default=10)
    parser.add_argument("--max-p95-ms", type=float, default=500.0)
    parser.add_argument("--out", default=None, help="مسار تقرير JSON")
    args = parser.parse_args()

    with __import__("tempfile").TemporaryDirectory() as tmp:
        report = run_load(
            requests=args.requests,
            concurrency=args.concurrency,
            max_p95_ms=args.max_p95_ms,
            evidence_path=Path(tmp) / "evidence.jsonl",
        )

    print(json.dumps(report, ensure_ascii=False, indent=2))
    if args.out:
        Path(args.out).write_text(
            json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8"
        )
    print()
    print("نجح المقياس." if report["passed"] else "فشل المقياس.")
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())

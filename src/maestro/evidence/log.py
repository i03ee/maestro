"""سجل أدلة إلحاقي: كل سطر مربوط ببصمة السطر قبله.

الغرض: كشف أي تعديل لاحق على السجل. لا يُعدَّل السجل ولا يُحذف منه؛
تصحيح خطأ يُسجَّل كسطر جديد.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

GENESIS = "0" * 64


def _canonical(payload: Any) -> str:
    return json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


@dataclass(frozen=True)
class EvidenceEntry:
    """سطر واحد في سجل الأدلة."""

    seq: int
    kind: str
    payload: dict[str, Any]
    prev_hash: str
    entry_hash: str

    def as_dict(self) -> dict[str, Any]:
        return {
            "seq": self.seq,
            "kind": self.kind,
            "payload": self.payload,
            "prev_hash": self.prev_hash,
            "entry_hash": self.entry_hash,
        }


class EvidenceLog:
    """سجل JSONL بسلسلة بصمات."""

    def __init__(self, path: str | Path):
        self.path = Path(path)
        # رأس السجل محفوظ في الذاكرة: بلا ذلك تقرأ كل كتابة الملف كاملاً
        # فتتحوّل العملية إلى O(n²) تحت التزامن — وهو ما كشفه مقياس الحمل.
        self._head_hash: str = GENESIS
        self._count: int = 0
        self._load_head()

    # -- قراءة -------------------------------------------------------------
    def _load_head(self) -> None:
        """يقرأ رأس السطر الأخير مرة واحدة عند الفتح."""
        entries = self.entries()
        self._count = len(entries)
        self._head_hash = entries[-1].entry_hash if entries else GENESIS

    def entries(self) -> list[EvidenceEntry]:
        """كل السطور بالترتيب."""
        if not self.path.exists():
            return []
        entries: list[EvidenceEntry] = []
        for line in self.path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line:
                continue
            raw = json.loads(line)
            entries.append(
                EvidenceEntry(
                    seq=raw["seq"],
                    kind=raw["kind"],
                    payload=raw["payload"],
                    prev_hash=raw["prev_hash"],
                    entry_hash=raw["entry_hash"],
                )
            )
        return entries

    @property
    def head_hash(self) -> str:
        """بصمة آخر سطر (محفوظة في الذاكرة)."""
        return self._head_hash

    # -- كتابة -------------------------------------------------------------
    def append(self, kind: str, payload: dict[str, Any]) -> str:
        """يضيف سطراً جديداً ويعيد بصمته."""
        prev_hash = self._head_hash
        seq = self._count + 1
        entry_hash = hashlib.sha256(
            f"{prev_hash}|{seq}|{kind}|{_canonical(payload)}".encode("utf-8")
        ).hexdigest()
        line = {
            "seq": seq,
            "kind": kind,
            "payload": payload,
            "prev_hash": prev_hash,
            "entry_hash": entry_hash,
        }
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(line, ensure_ascii=False, sort_keys=True) + "\n")
        self._head_hash = entry_hash
        self._count = seq
        return entry_hash

    # -- تحقق --------------------------------------------------------------
    def verify(self) -> bool:
        """يعيد حساب السلسلة كاملة: صحيح/خطأ، بلا احتمال."""
        prev_hash = GENESIS
        for index, entry in enumerate(self.entries(), start=1):
            if entry.seq != index:
                return False
            if entry.prev_hash != prev_hash:
                return False
            expected = hashlib.sha256(
                f"{entry.prev_hash}|{entry.seq}|{entry.kind}|{_canonical(entry.payload)}".encode(
                    "utf-8"
                )
            ).hexdigest()
            if expected != entry.entry_hash:
                return False
            prev_hash = entry.entry_hash
        return True


if __name__ == "__main__":  # فحص ذاتي سريع لسلسلة البصمات
    import tempfile
    from pathlib import Path as _Path

    with tempfile.TemporaryDirectory() as _tmp:
        _log = EvidenceLog(_Path(_tmp) / "evidence.jsonl")
        _log.append("selftest", {"case": "chain"})
        _ok = _log.verify()
        print("سيرى سجل الأدلة: السلسلة صحيحة." if _ok else "FAIL: السلسلة مكسورة.")
        raise SystemExit(0 if _ok else 1)

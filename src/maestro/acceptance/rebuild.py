"""بصمة إعادة البناء: هل البناء الثاني يطابق الأول؟

الحساب: بصمة sha256 لكل ملفات المصدر (بمساراتها النسبية وبصماتها) مرتّبة
ترتيباً معجمياً، ثم بصمة واحدة فوق هذه السلسلة كلها. النتيجة حتمية: نفس الشجرة تعطي
نفس البصمة. أي تغيير في الشيفرة يغيّر البصمة — وهذا ما يجعل «إعادة البناء
من الإصدارات» قابلاً للفحص آلياً.
"""

from __future__ import annotations

import hashlib
from pathlib import Path

#: المسارات التي تدخل البصمة.
INCLUDED: tuple[str, ...] = (
    "src",
    "scripts",
    "docs/CAPABILITY_CATALOGUE.md",
    "pyproject.toml",
    "THIRD_PARTY_NOTICES.md",
)

#: أنماط تُتجاهل (مخرجات مؤقتة وليست مصدراً).
EXCLUDED_SUFFIXES: frozenset[str] = frozenset({".pyc", ".pyo"})


def _iter_files(root: Path) -> list[Path]:
    """ملفات المصدر بالترتيب المعجمي."""
    files: list[Path] = []
    for relative in INCLUDED:
        target = root / relative
        if target.is_file():
            files.append(target)
        elif target.is_dir():
            files.extend(
                path
                for path in target.rglob("*")
                if path.is_file()
                and path.suffix.lower() not in EXCLUDED_SUFFIXES
                and "__pycache__" not in path.parts
            )
    return sorted(files, key=lambda path: path.relative_to(root).as_posix())


def compute_rebuild_hash(root: Path | str = ".") -> str:
    """بصمة الشجرة الحالية."""
    base = Path(root).resolve()
    digest = hashlib.sha256()
    for path in _iter_files(base):
        relative = path.relative_to(base).as_posix()
        file_hash = hashlib.sha256(path.read_bytes()).hexdigest()
        digest.update(f"{relative}:{file_hash}\n".encode("utf-8"))
    return digest.hexdigest()

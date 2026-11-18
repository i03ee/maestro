"""تكامل نَسمة: من ملف مورّد إلى بطاقة منتج جاهزة للكتالوج."""

from .catalog import (
    LOCALES,
    NasmaProduct,
    format_iqd,
    load_supplier_rows,
    safe_image,
    validate_product,
)
from .pipeline import (
    CatalogRunResult,
    build_product_task,
    default_registry,
    run_catalog,
    write_catalog,
)

__all__ = [
    "LOCALES",
    "NasmaProduct",
    "format_iqd",
    "load_supplier_rows",
    "safe_image",
    "validate_product",
    "CatalogRunResult",
    "build_product_task",
    "default_registry",
    "run_catalog",
    "write_catalog",
]

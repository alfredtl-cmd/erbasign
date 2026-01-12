from __future__ import annotations

import argparse
import os
import re
from pathlib import Path
from decimal import Decimal, InvalidOperation
from datetime import datetime

import pandas as pd


# --- Django setup (standalone script) ---
def setup_django() -> None:
    """
    Make this script runnable from anywhere by:
    1) adding project root to sys.path
    2) auto-detecting the Django settings module
    """
    import sys

    project_root = Path(__file__).resolve().parent.parent
    os.chdir(project_root)

    # ensure python can import the Django project package
    if str(project_root) not in sys.path:
        sys.path.insert(0, str(project_root))

    # auto-detect settings module (config.settings OR <projectname>.settings)
    # Try common names first:
    candidates = [
        "config.settings",
        "erbasign.settings",  # <--- 如果你 project 叫 erbasign
        "project.settings",
        "mysite.settings",
    ]

    # If still not found, discover by finding settings.py under project_root
    settings_py = list(project_root.glob("*/settings.py"))
    for p in settings_py:
        pkg = p.parent.name
        candidates.insert(0, f"{pkg}.settings")

    for m in candidates:
        try:
            __import__(m)
            os.environ.setdefault("DJANGO_SETTINGS_MODULE", m)
            break
        except ModuleNotFoundError:
            continue

    import django  # noqa

    django.setup()


BASE_DIR = Path(__file__).resolve().parent
RAW_DIR = BASE_DIR / "raw"
CLEAN_DIR = BASE_DIR / "cleaned"
FMT_DIR = BASE_DIR / "formatted"
EXPORT_DIR = BASE_DIR / "exports"


def ensure_dirs() -> None:
    for d in (CLEAN_DIR, FMT_DIR, EXPORT_DIR):
        d.mkdir(parents=True, exist_ok=True)


# -----------------------
# a) CLEAN (raw -> cleaned)
# -----------------------
def clean_email(x: str) -> str:
    if pd.isna(x):
        return ""
    return str(x).strip().lower()


def clean_phone(x: str) -> str:
    if pd.isna(x):
        return ""
    s = str(x).strip()
    digits = re.sub(r"\D+", "", s)
    # keep last 8 digits as HK style (simple rule for assignment)
    if len(digits) > 8:
        digits = digits[-8:]
    return digits


def clean_bool(x) -> bool:
    if pd.isna(x) or str(x).strip() == "":
        return True  # default active
    s = str(x).strip().lower()
    return s in ("1", "true", "t", "yes", "y")


def clean_price(x) -> str:
    if pd.isna(x):
        return "0"
    s = str(x).strip()
    s = s.replace("HK$", "").replace("$", "")
    s = s.replace(",", "").strip()
    # keep numeric only (and dot)
    s = re.sub(r"[^0-9.]+", "", s)
    return s or "0"


def clean_date(x: str) -> str:
    if pd.isna(x):
        return ""
    s = str(x).strip()
    # try multiple formats
    for fmt in ("%Y-%m-%d", "%Y/%m/%d", "%d-%m-%Y", "%d/%m/%Y"):
        try:
            return datetime.strptime(s, fmt).date().isoformat()
        except ValueError:
            continue
    return ""  # if cannot parse


def cmd_clean() -> None:
    ensure_dirs()

    # customers
    c_path = RAW_DIR / "customers_raw.csv"
    dfc = pd.read_csv(c_path)
    dfc["full_name"] = dfc["full_name"].astype(str).str.strip()
    dfc["email"] = dfc["email"].apply(clean_email)
    dfc["phone"] = dfc["phone"].apply(clean_phone)

    # drop rows without email
    dfc = dfc[dfc["email"] != ""].copy()
    # remove duplicate emails keeping first
    dfc = dfc.drop_duplicates(subset=["email"], keep="first")

    dfc.to_csv(CLEAN_DIR / "customers_cleaned.csv", index=False, encoding="utf-8")

    # products
    p_path = RAW_DIR / "products_raw.csv"
    dfp = pd.read_csv(p_path)
    dfp["sku"] = dfp["sku"].astype(str).str.strip()
    dfp["name"] = dfp["name"].astype(str).str.strip()
    dfp["price"] = dfp["price"].apply(clean_price)
    dfp["is_active"] = dfp["is_active"].apply(clean_bool)

    dfp = dfp.drop_duplicates(subset=["sku"], keep="first")
    dfp.to_csv(CLEAN_DIR / "products_cleaned.csv", index=False, encoding="utf-8")

    # orders
    o_path = RAW_DIR / "orders_raw.csv"
    dfo = pd.read_csv(o_path)
    dfo["customer_email"] = dfo["customer_email"].apply(clean_email)
    dfo["product_sku"] = dfo["product_sku"].astype(str).str.strip()
    dfo["quantity"] = dfo["quantity"].astype(str).str.strip()
    dfo["quantity"] = (
        pd.to_numeric(dfo["quantity"], errors="coerce").fillna(1).astype(int)
    )
    dfo["order_date"] = dfo["order_date"].apply(clean_date)
    dfo["note"] = dfo["note"].astype(str).str.strip()

    dfo = dfo[
        (dfo["customer_email"] != "")
        & (dfo["product_sku"] != "")
        & (dfo["order_date"] != "")
    ]
    dfo.to_csv(CLEAN_DIR / "orders_cleaned.csv", index=False, encoding="utf-8")

    print("✅ CLEAN complete -> scripts/cleaned/*.csv")


# --------------------------
# b) FORMAT (cleaned -> formatted)
# --------------------------
def to_decimal_str(x: str) -> str:
    try:
        return str(Decimal(x).quantize(Decimal("0.01")))
    except (InvalidOperation, TypeError):
        return "0.00"


def cmd_format() -> None:
    ensure_dirs()

    dfc = pd.read_csv(CLEAN_DIR / "customers_cleaned.csv")
    # ensure schema consistency
    dfc = dfc[["full_name", "email", "phone"]].copy()
    dfc.to_csv(FMT_DIR / "customers_formatted.csv", index=False, encoding="utf-8")

    dfp = pd.read_csv(CLEAN_DIR / "products_cleaned.csv")
    dfp["price"] = dfp["price"].apply(to_decimal_str)
    dfp = dfp[["sku", "name", "price", "is_active"]].copy()
    dfp.to_csv(FMT_DIR / "products_formatted.csv", index=False, encoding="utf-8")

    dfo = pd.read_csv(CLEAN_DIR / "orders_cleaned.csv")
    # strict columns + ISO date already
    dfo = dfo[
        ["customer_email", "product_sku", "quantity", "order_date", "note"]
    ].copy()
    dfo.to_csv(FMT_DIR / "orders_formatted.csv", index=False, encoding="utf-8")

    print("✅ FORMAT complete -> scripts/formatted/*.csv")


# --------------------------------
# c) IMPORT (formatted -> Postgres via Django ORM)
# --------------------------------
def cmd_import() -> None:
    ensure_dirs()
    setup_django()

    from pages.models import Customer, Product, Order  # noqa

    # customers
    dfc = pd.read_csv(FMT_DIR / "customers_formatted.csv")
    customers = []
    for _, r in dfc.iterrows():
        customers.append(
            Customer(
                full_name=r["full_name"],
                email=r["email"],
                phone=r.get("phone", ""),
            )
        )

    existing_emails = set(
        Customer.objects.filter(email__in=dfc["email"].tolist()).values_list(
            "email", flat=True
        )
    )
    to_create = [c for c in customers if c.email not in existing_emails]
    Customer.objects.bulk_create(to_create, ignore_conflicts=True)

    # products
    dfp = pd.read_csv(FMT_DIR / "products_formatted.csv")
    existing_skus = set(
        Product.objects.filter(sku__in=dfp["sku"].tolist()).values_list(
            "sku", flat=True
        )
    )
    prods = []
    for _, r in dfp.iterrows():
        sku = str(r["sku"]).strip()
        if sku in existing_skus:
            continue
        prods.append(
            Product(
                sku=sku,
                name=str(r["name"]).strip(),
                price=Decimal(str(r["price"])),
                is_active=bool(r["is_active"]),
            )
        )
    Product.objects.bulk_create(prods, ignore_conflicts=True)

    # orders (need FK)
    dfo = pd.read_csv(FMT_DIR / "orders_formatted.csv")

    # drop duplicate rows inside the file
    dfo = dfo.drop_duplicates(
        subset=["customer_email", "product_sku", "quantity", "order_date", "note"]
    )

    cust_map = {
        c.email: c
        for c in Customer.objects.filter(email__in=dfo["customer_email"].unique()).all()
    }
    prod_map = {
        p.sku: p
        for p in Product.objects.filter(sku__in=dfo["product_sku"].unique()).all()
    }

    orders = []
    for _, r in dfo.iterrows():
        c = cust_map.get(r["customer_email"])
        p = prod_map.get(r["product_sku"])
        if not c or not p:
            continue

        orders.append(
            Order(
                customer=c,
                product=p,
                quantity=int(r["quantity"]),
                order_date=datetime.strptime(r["order_date"], "%Y-%m-%d").date(),
                note=str(r.get("note", "")).strip(),
            )
        )

    # idempotent import: only insert orders not already in DB
    existing = set(
        Order.objects.values_list(
            "customer__email", "product__sku", "quantity", "order_date", "note"
        )
    )

    filtered = []
    for o in orders:
        key = (o.customer.email, o.product.sku, o.quantity, o.order_date, o.note)
        if key not in existing:
            filtered.append(o)

    Order.objects.bulk_create(filtered)

    print("✅ IMPORT complete -> data inserted into Postgres (check /admin/)")


# --------------------------------
# c) EXPORT (Postgres -> CSV)
# --------------------------------
def cmd_export() -> None:
    ensure_dirs()
    setup_django()

    from pages.models import Customer, Product, Order  # noqa

    # Customers
    customers = Customer.objects.all().values(
        "id", "full_name", "email", "phone", "created_at"
    )
    pd.DataFrame(list(customers)).to_csv(
        EXPORT_DIR / "customers_export.csv", index=False, encoding="utf-8"
    )

    # Products
    products = Product.objects.all().values(
        "id", "sku", "name", "price", "is_active", "created_at"
    )
    pd.DataFrame(list(products)).to_csv(
        EXPORT_DIR / "products_export.csv", index=False, encoding="utf-8"
    )

    # Orders (include FK fields)
    orders = Order.objects.select_related("customer", "product").all()
    rows = []
    for o in orders:
        rows.append(
            {
                "id": o.id,
                "customer_email": o.customer.email,
                "product_sku": o.product.sku,
                "quantity": o.quantity,
                "order_date": o.order_date.isoformat(),
                "note": o.note,
            }
        )
    pd.DataFrame(rows).to_csv(
        EXPORT_DIR / "orders_export.csv", index=False, encoding="utf-8"
    )

    print("✅ EXPORT complete -> scripts/exports/*.csv")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Data pipeline: clean/format/import/export"
    )
    sub = parser.add_subparsers(dest="cmd", required=True)

    sub.add_parser("clean")
    sub.add_parser("format")
    sub.add_parser("import")
    sub.add_parser("export")

    args = parser.parse_args()

    if args.cmd == "clean":
        cmd_clean()
    elif args.cmd == "format":
        cmd_format()
    elif args.cmd == "import":
        cmd_import()
    elif args.cmd == "export":
        cmd_export()
    else:
        raise SystemExit("Unknown command")


if __name__ == "__main__":
    main()

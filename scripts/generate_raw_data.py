from __future__ import annotations
import random
from pathlib import Path
from datetime import date, timedelta
import csv

BASE_DIR = Path(__file__).resolve().parent
RAW_DIR = BASE_DIR / "raw"

random.seed(7)

FIRST_NAMES = [
    "Kit",
    "Alex",
    "Chris",
    "Taylor",
    "Jordan",
    "Sam",
    "Jamie",
    "Morgan",
    "Casey",
    "Robin",
]
LAST_NAMES = ["Wong", "Chan", "Lee", "Cheung", "Ng", "Lam", "Ho", "Lau", "Yip", "Chow"]
DOMAINS = ["gmail.com", "yahoo.com", "outlook.com", "example.com"]

PRODUCTS = [
    ("SKU-001", "NMN 32000", " $1,299.00 "),
    ("SKU-002", "Fish Oil 1000mg", "HK$399"),
    ("SKU-003", "Vitamin C 1000", "399.5"),
    ("SKU-004", "Collagen Peptide", "$ 899"),
    ("SKU-005", "Magnesium Glycinate", " 259 "),
    ("SKU-006", "Probiotic 30B", "HK$ 699.00"),
    ("SKU-007", "Zinc 50mg", " $99 "),
    ("SKU-008", "NADH Booster", "1,599"),
    ("SKU-009", "PQQ Complex", " 799 "),
    ("SKU-010", "Spermidine", "HK$1,099"),
    ("SKU-011", "EGT 麥角硫因", " $1,499 "),
    ("SKU-012", "CoQ10", "299"),
    ("SKU-013", "Iron", " $129 "),
    ("SKU-014", "B-Complex", " 219.00 "),
    ("SKU-015", "Omega 3 Premium", "HK$ 599"),
    ("SKU-016", "Sleep Support", " 459 "),
    ("SKU-017", "Joint Care", " $699 "),
    ("SKU-018", "Eye Care", "HK$ 329"),
    ("SKU-019", "Calcium D3", " 279 "),
    ("SKU-020", "Protein Bar", " $39 "),
]


def messy_email(first: str, last: str, i: int) -> str:
    base = f"{first}.{last}{i}"
    if random.random() < 0.25:
        base = base.upper()
    if random.random() < 0.25:
        base = " " + base + " "
    return f"{base}@{random.choice(DOMAINS)}"


def messy_phone() -> str:
    # mix formats: spaces, +852, hyphens
    n = "".join(str(random.randint(0, 9)) for _ in range(8))
    fmt = random.choice(
        [
            n,
            f"+852 {n[:4]} {n[4:]}",
            f"(852) {n[:4]}-{n[4:]}",
            f"{n[:4]} {n[4:]}",
            f"{n[:4]}-{n[4:]}",
            f"  {n[:4]}-{n[4:]}  ",
        ]
    )
    return fmt


def messy_date(d: date) -> str:
    fmt = random.choice(
        [
            d.strftime("%Y-%m-%d"),
            d.strftime("%Y/%m/%d"),
            d.strftime("%d-%m-%Y"),
            d.strftime("%d/%m/%Y"),
        ]
    )
    # sometimes with spaces
    if random.random() < 0.2:
        fmt = " " + fmt + " "
    return fmt


def ensure_dirs() -> None:
    RAW_DIR.mkdir(parents=True, exist_ok=True)


def write_customers(rows: int = 25) -> None:
    path = RAW_DIR / "customers_raw.csv"
    lines = ["full_name,email,phone\n"]
    for i in range(1, rows + 1):
        first = random.choice(FIRST_NAMES)
        last = random.choice(LAST_NAMES)
        full_name = f"{first} {last}"
        email = messy_email(first, last, i)
        phone = messy_phone()
        # Inject some duplicates / messy spaces for cleaning challenge
        if i in (5, 12):
            email = "  ALEX.CHAN5@gmail.com "  # duplicate-like
        lines.append(f"{full_name},{email},{phone}\n")
    path.write_text("".join(lines), encoding="utf-8")


def write_products() -> None:
    path = RAW_DIR / "products_raw.csv"
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["sku", "name", "price", "is_active"])

        for sku, name, price in PRODUCTS:
            # keep your "messy" active flag styles
            is_active = random.choice(["TRUE", "True", "true", "FALSE", "False", ""])
            # csv.writer will automatically quote fields when needed (e.g. "$1,299.00")
            writer.writerow([sku, name, price, is_active])


def write_orders(rows: int = 40) -> None:
    path = RAW_DIR / "orders_raw.csv"
    cust_path = RAW_DIR / "customers_raw.csv"

    # read customers emails from the already generated customers file
    import csv

    emails = []
    with cust_path.open("r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            emails.append(row["email"])

    lines = ["customer_email,product_sku,quantity,order_date,note\n"]
    today = date.today()

    for _ in range(rows):
        # ✅ ensure FK match: choose from existing customer emails
        email = random.choice(emails)

        sku, _, _ = random.choice(PRODUCTS)
        qty = random.choice([1, 2, 3, " 2 ", "1 ", " 4"])
        od = messy_date(today - timedelta(days=random.randint(0, 120)))
        note = random.choice(["", " first order ", "VIP", "  deliver pm  ", "gift"])
        lines.append(f"{email},{sku},{qty},{od},{note}\n")

    path.write_text("".join(lines), encoding="utf-8")


def main() -> None:
    ensure_dirs()
    write_customers(25)  # >=20
    write_products()  # 20 products
    write_orders(40)  # >=20
    print("✅ Raw CSV generated under scripts/raw/")


if __name__ == "__main__":
    main()

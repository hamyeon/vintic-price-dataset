from pathlib import Path
import pandas as pd

RAW_PATH = Path("data/raw/ebay_raw.csv")
OUTPUT_PATH = Path("data/processed/ebay_normalized.csv")

EXCHANGE_RATE_DEFAULT = 1360

REQUIRED_COLUMNS = [
    "target_id",
    "brand",
    "model",
    "colorway",
    "size_us",
    "size_kr",
    "ebay_price_original",
    "currency_original",
    "exchange_rate",
    "ebay_price_krw",
    "price_type",
    "item_url",
    "item_title",
    "item_condition",
    "shipping_price",
    "collected_at",
    "memo",
]


def round_to_1000(value: float) -> int:
    return int(round(value / 1000) * 1000)


def normalize_condition(item_condition: str) -> str:
    condition = str(item_condition).lower()

    if "new with box" in condition:
        return "DS"
    if "new without box" in condition:
        return "A"
    if "new with defects" in condition:
        return "B"
    if "very good" in condition:
        return "A"
    if "excellent" in condition:
        return "A"
    if "good" in condition:
        return "B"
    if "pre-owned" in condition or "preowned" in condition:
        return "B"
    if "fair" in condition:
        return "C"
    if "parts" in condition or "repair" in condition:
        return "D"

    return "unknown"


def infer_box_included(item_condition: str, memo: str) -> str:
    text = f"{item_condition} {memo}".lower()

    if "new with box" in text or "with box" in text:
        return "true"
    if "without box" in text or "no box" in text:
        return "false"

    return "unknown"


def main():
    if not RAW_PATH.exists():
        raise FileNotFoundError(f"Raw file not found: {RAW_PATH}")

    df = pd.read_csv(RAW_PATH)

    missing_columns = [col for col in REQUIRED_COLUMNS if col not in df.columns]
    if missing_columns:
        raise ValueError(f"Missing columns in ebay_raw.csv: {missing_columns}")

    df["exchange_rate"] = df["exchange_rate"].fillna(EXCHANGE_RATE_DEFAULT)

    df["ebay_price_krw"] = df.apply(
        lambda row: round_to_1000(
            float(row["ebay_price_krw"])
            if pd.notna(row["ebay_price_krw"]) and str(row["ebay_price_krw"]).strip() != ""
            else float(row["ebay_price_original"]) * float(row["exchange_rate"])
        ),
        axis=1,
    )

    df["condition_grade"] = df["item_condition"].apply(normalize_condition)

    df["box_included"] = df.apply(
        lambda row: infer_box_included(row["item_condition"], row["memo"]),
        axis=1,
    )

    df["source"] = "EBAY"
    df["currency"] = "KRW"

    df["shipping_price_usd"] = pd.to_numeric(
    df["shipping_price"], errors="coerce"
    ).fillna(0)

    df["total_price_krw"] = df.apply(
        lambda row: round_to_1000(
            float(row["ebay_price_krw"])
            + float(row["shipping_price_usd"]) * float(row["exchange_rate"])
        ),
        axis=1,
    )

    df["description"] = df.apply(
        lambda row: (
            f"{row['brand']} {row['model']} {row['colorway']} "
            f"size {row['size_kr']} KR / US {row['size_us']}. "
            f"Condition {row['condition_grade']}. "
            f"Box included {row['box_included']}. "
            f"eBay reference listing price {row['ebay_price_krw']} KRW. "
            f"Original eBay price {row['ebay_price_original']} {row['currency_original']}. "
            f"Collected on {row['collected_at']}. "
            f"Item title: {row['item_title']}."
        ),
        axis=1,
    )

    output_columns = [
        "target_id",
        "source",
        "brand",
        "model",
        "colorway",
        "size_kr",
        "size_us",
        "condition_grade",
        "box_included",
        "ebay_price_krw",
        "currency",
        "price_type",
        "item_url",
        "item_title",
        "item_condition",
        "shipping_price",
        "collected_at",
        "description",
    ]

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    df[output_columns].to_csv(OUTPUT_PATH, index=False, encoding="utf-8-sig")

    print(f"Saved: {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
import csv
import os
import time
from datetime import date
from pathlib import Path

import pandas as pd
import requests
from dotenv import load_dotenv

from get_ebay_token import get_application_token

load_dotenv()

MARKETPLACE_ID = os.getenv("EBAY_MARKETPLACE_ID", "EBAY_US")
EXCHANGE_RATE = int(os.getenv("EXCHANGE_RATE", "1360"))

TARGETS_PATH = Path("data/targets/target_shoes.csv")
OUTPUT_PATH = Path("data/raw/ebay_raw.csv")

SEARCH_LIMIT = 50
REQUEST_SLEEP_SECONDS = 1


def round_to_1000(value: float) -> int:
    return int(round(value / 1000) * 1000)


def search_ebay(query: str, limit: int = SEARCH_LIMIT) -> list[dict]:
    token = get_application_token()

    url = "https://api.ebay.com/buy/browse/v1/item_summary/search"

    headers = {
        "Authorization": f"Bearer {token}",
        "X-EBAY-C-MARKETPLACE-ID": MARKETPLACE_ID,
    }

    params = {
        "q": query,
        "limit": limit,
    }

    response = requests.get(url, headers=headers, params=params, timeout=20)

    if response.status_code != 200:
        print("eBay 검색 실패")
        print("query:", query)
        print("status_code:", response.status_code)
        print("response:", response.text)
        response.raise_for_status()

    data = response.json()
    return data.get("itemSummaries", [])


def get_shipping_price(item: dict) -> float:
    shipping_options = item.get("shippingOptions", [])

    if not shipping_options:
        return 0.0

    shipping_cost = shipping_options[0].get("shippingCost", {})
    shipping_value = shipping_cost.get("value")

    if shipping_value is None:
        return 0.0

    try:
        return float(shipping_value)
    except ValueError:
        return 0.0


def convert_price_to_krw(original_price: float, currency: str) -> int | None:
    if currency == "USD":
        return round_to_1000(original_price * EXCHANGE_RATE)

    if currency == "KRW":
        return round_to_1000(original_price)

    # MVP에서는 USD/KRW 외 통화는 제외
    return None


def ensure_output_header(fieldnames: list[str]) -> None:
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)

    if not OUTPUT_PATH.exists():
        with OUTPUT_PATH.open("w", newline="", encoding="utf-8-sig") as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()


def append_items_to_csv(
    target_id: int,
    brand: str,
    model: str,
    colorway: str,
    size_us: str,
    size_kr: str,
    query: str,
    limit: int = SEARCH_LIMIT,
) -> int:
    items = search_ebay(query=query, limit=limit)

    if not items:
        print(f"[target_id={target_id}] 검색 결과 없음: {query}")
        return 0

    fieldnames = [
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

    ensure_output_header(fieldnames)

    saved_count = 0

    with OUTPUT_PATH.open("a", newline="", encoding="utf-8-sig") as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)

        for item in items:
            price_info = item.get("price", {})
            price_value = price_info.get("value")
            currency = price_info.get("currency", "USD")

            if price_value is None:
                continue

            try:
                original_price = float(price_value)
            except ValueError:
                continue

            price_krw = convert_price_to_krw(original_price, currency)

            if price_krw is None:
                continue

            shipping_price = get_shipping_price(item)

            writer.writerow(
                {
                    "target_id": target_id,
                    "brand": brand,
                    "model": model,
                    "colorway": colorway,
                    "size_us": size_us,
                    "size_kr": size_kr,
                    "ebay_price_original": original_price,
                    "currency_original": currency,
                    "exchange_rate": EXCHANGE_RATE,
                    "ebay_price_krw": price_krw,
                    "price_type": "listing_price",
                    "item_url": item.get("itemWebUrl", ""),
                    "item_title": item.get("title", ""),
                    "item_condition": item.get("condition", ""),
                    "shipping_price": shipping_price,
                    "collected_at": date.today().isoformat(),
                    "memo": f"query={query}; collected_by_browse_api",
                }
            )

            saved_count += 1

    print(f"[target_id={target_id}] saved {saved_count} rows: {query}")
    return saved_count


def collect_all_targets() -> None:
    if not TARGETS_PATH.exists():
        raise FileNotFoundError(f"Target file not found: {TARGETS_PATH}")

    targets = pd.read_csv(TARGETS_PATH)

    required_columns = [
        "target_id",
        "brand",
        "model",
        "colorway",
        "size_kr",
        "size_us",
        "search_query_ebay",
    ]

    missing_columns = [col for col in required_columns if col not in targets.columns]

    if missing_columns:
        raise ValueError(f"Missing columns in target_shoes.csv: {missing_columns}")

    total_saved = 0

    for _, row in targets.iterrows():
        target_id = int(row["target_id"])
        brand = str(row["brand"])
        model = str(row["model"])
        colorway = str(row["colorway"])
        size_us = str(row["size_us"])
        size_kr = str(row["size_kr"])
        query = str(row["search_query_ebay"])

        print(f"\n[target_id={target_id}] collecting: {query}")

        saved_count = append_items_to_csv(
            target_id=target_id,
            brand=brand,
            model=model,
            colorway=colorway,
            size_us=size_us,
            size_kr=size_kr,
            query=query,
            limit=SEARCH_LIMIT,
        )

        total_saved += saved_count

        # 대량 요청 방지용 짧은 대기
        time.sleep(REQUEST_SLEEP_SECONDS)

    print(f"\nDone. Total saved rows: {total_saved}")
    print(f"Saved eBay search results to {OUTPUT_PATH}")


if __name__ == "__main__":
    collect_all_targets()
import csv
import os
from datetime import date
from pathlib import Path

import requests
from dotenv import load_dotenv

from get_ebay_token import get_application_token

load_dotenv()

MARKETPLACE_ID = os.getenv("EBAY_MARKETPLACE_ID", "EBAY_US")
EXCHANGE_RATE = 1360

OUTPUT_PATH = Path("data/raw/ebay_raw.csv")


def round_to_1000(value: float) -> int:
    return int(round(value / 1000) * 1000)


def search_ebay(query: str, limit: int = 50) -> list[dict]:
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
        print("status_code:", response.status_code)
        print("response:", response.text)
        response.raise_for_status()

    data = response.json()
    return data.get("itemSummaries", [])


def append_items_to_csv(
    target_id: int,
    brand: str,
    model: str,
    colorway: str,
    size_us: str,
    size_kr: str,
    query: str,
):
    items = search_ebay(query=query, limit=50)

    if not items:
        print("검색 결과가 없습니다.")
        return

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)

    file_exists = OUTPUT_PATH.exists()

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

    with OUTPUT_PATH.open("a", newline="", encoding="utf-8-sig") as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)

        if not file_exists:
            writer.writeheader()

        for item in items:
            price_info = item.get("price", {})
            price_value = price_info.get("value")
            currency = price_info.get("currency", "USD")

            if price_value is None:
                continue

            original_price = float(price_value)

            if currency == "USD":
                price_krw = round_to_1000(original_price * EXCHANGE_RATE)
            elif currency == "KRW":
                price_krw = round_to_1000(original_price)
            else:
                # MVP에서는 USD/KRW 외 통화는 일단 제외
                continue

            shipping_options = item.get("shippingOptions", [])
            shipping_price = 0

            if shipping_options:
                shipping_cost = shipping_options[0].get("shippingCost", {})
                shipping_value = shipping_cost.get("value")
                if shipping_value is not None:
                    shipping_price = float(shipping_value) if shipping_value is not None else 0.0

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

    print(f"Saved eBay search results to {OUTPUT_PATH}")


if __name__ == "__main__":
    append_items_to_csv(
        target_id=1,
        brand="Nike",
        model="Air Jordan 1 Retro High OG",
        colorway="Chicago Lost and Found",
        size_us="9",
        size_kr="270",
        query="Nike Air Jordan 1 Lost and Found US 9",
    )
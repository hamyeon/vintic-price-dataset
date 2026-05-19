import base64
import os

import requests
from dotenv import load_dotenv

load_dotenv()

CLIENT_ID = os.getenv("EBAY_CLIENT_ID")
CLIENT_SECRET = os.getenv("EBAY_CLIENT_SECRET")
EBAY_ENV = os.getenv("EBAY_ENV", "production")

if EBAY_ENV == "sandbox":
    TOKEN_URL = "https://api.sandbox.ebay.com/identity/v1/oauth2/token"
else:
    TOKEN_URL = "https://api.ebay.com/identity/v1/oauth2/token"


def get_application_token() -> str:
    if not CLIENT_ID or not CLIENT_SECRET:
        raise ValueError("EBAY_CLIENT_ID 또는 EBAY_CLIENT_SECRET이 .env에 없습니다.")

    credentials = f"{CLIENT_ID}:{CLIENT_SECRET}"
    encoded_credentials = base64.b64encode(credentials.encode()).decode()

    headers = {
        "Content-Type": "application/x-www-form-urlencoded",
        "Authorization": f"Basic {encoded_credentials}",
    }

    data = {
        "grant_type": "client_credentials",
        "scope": "https://api.ebay.com/oauth/api_scope",
    }

    response = requests.post(TOKEN_URL, headers=headers, data=data, timeout=15)

    if response.status_code != 200:
        print("토큰 발급 실패")
        print("status_code:", response.status_code)
        print("response:", response.text)
        response.raise_for_status()

    token_data = response.json()
    return token_data["access_token"]


if __name__ == "__main__":
    token = get_application_token()
    print("eBay application token 발급 성공")
    print("token preview:", token[:20] + "...")
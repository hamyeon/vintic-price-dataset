import re
from pathlib import Path

import pandas as pd

INPUT_PATH = Path("data/processed/ebay_normalized.csv")
OUTPUT_PATH = Path("data/processed/ebay_filtered.csv")
LOG_PATH = Path("data/processed/ebay_filter_log.csv")

# IQR 이상치 제거 배수 (1.5 = 일반적인 박스플롯 기준)
IQR_MULTIPLIER = 1.5

# target_id별 검색에 반드시 포함되어야 할 키워드 목록
# 새 신발을 추가할 때 여기에 함께 등록하세요.
MODEL_KEYWORDS: dict[int, list[str]] = {
    1: ["jordan 1", "lost and found"],
    # 2: ["dunk low", "panda"],
    # 3: ["yeezy", "350"],
}


# ---------------------------------------------------------------------------
# 필터 함수
# ---------------------------------------------------------------------------

def filter_grade_d(df: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    """D등급(Parts/Repair) 행을 제거합니다."""
    mask = df["condition_grade"] == "D"
    return df[~mask].copy(), df[mask].copy()


def is_youth_or_kids_title(title: str) -> bool:
    """
    키즈/아동/GS/PS/TD/C 사이즈 상품인지 확인합니다.

    MVP에서는 성인 남성 US 사이즈 기준으로 비교하므로
    키즈 계열 상품은 제거합니다.
    """
    title_lower = str(title).lower()

    youth_patterns = [
        r"\b\d+(?:\.\d+)?c\b",      # 9C, 10.5C
        r"\b\d+(?:\.\d+)?y\b",      # 6Y, 7Y
        r"\bgs\b",                  # Grade School
        r"\bps\b",                  # Preschool
        r"\btd\b",                  # Toddler
        r"\bgrade school\b",
        r"\bbig kids\b",
        r"\blittle kids\b",
        r"\bchild\b",
        r"\bkids\b",
        r"\byouth\b",
    ]

    return any(re.search(pattern, title_lower) for pattern in youth_patterns)


def _extract_sizes_from_title(title: str) -> list[float]:
    """
    item_title에서 명확한 성인 US 사이즈만 추출합니다.

    허용 예시:
      "Size 9", "Size 9.5", "US 9", "US9", "Sz 9",
      "Men Size 9", "Men's Size 9", "Men Size 9 US"

    제외하고 싶은 숫자 예시:
      "Jordan 1", "2022", "DZ5485-612", "9C", "GS", "PS", "TD"
    """
    title_lower = str(title).lower()

    patterns = [
        r"\bmen(?:'s)?\s*size\s*(\d+(?:\.\d+)?)\b",
        r"\bmens\s*size\s*(\d+(?:\.\d+)?)\b",
        r"\bmen(?:'s)?\s*(\d+(?:\.\d+)?)\b",
        r"\bsize\s*(\d+(?:\.\d+)?)\b",
        r"\bsz\s*(\d+(?:\.\d+)?)\b",
        r"\bus\s*(\d+(?:\.\d+)?)\b",
        r"\b(\d+(?:\.\d+)?)\s*us\b",
    ]

    sizes: list[float] = []

    for pattern in patterns:
        matches = re.findall(pattern, title_lower)
        for match in matches:
            try:
                sizes.append(float(match))
            except ValueError:
                pass

    return sizes


def filter_size_mismatch(df: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    """
    item_title에서 사이즈를 추출해서 target size_us와 다른 행을 제거합니다.

    기준:
      - 키즈/아동/GS/PS/TD/C/Y 상품은 제거
      - 타이틀에 명확한 사이즈 정보가 없으면 통과
      - 추출된 사이즈 중 하나라도 target과 일치하면 통과
      - 사이즈가 추출됐는데 target과 다르면 제거
    """
    def is_size_ok(row) -> bool:
        title = str(row["item_title"])

        # 키즈/아동 사이즈는 성인 US 9 비교 데이터에서 제외
        if is_youth_or_kids_title(title):
            return False

        try:
            target = float(row["size_us"])
        except (ValueError, TypeError):
            return True  # size_us 자체가 이상하면 일단 통과

        found_sizes = _extract_sizes_from_title(title)

        if not found_sizes:
            return True  # 타이틀에 명확한 사이즈가 없으면 통과

        return target in found_sizes

    mask = df.apply(is_size_ok, axis=1)
    return df[mask].copy(), df[~mask].copy()


def filter_model_keywords(df: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    """
    MODEL_KEYWORDS에 정의된 키워드가 item_title에 모두 포함되는지 확인합니다.

    - target_id가 MODEL_KEYWORDS에 없으면 통과시킵니다.
    """
    def is_model_ok(row) -> bool:
        tid = int(row["target_id"])
        keywords = MODEL_KEYWORDS.get(tid)

        if not keywords:
            return True  # 등록된 키워드 없으면 통과

        title_lower = str(row["item_title"]).lower()
        return all(kw.lower() in title_lower for kw in keywords)

    mask = df.apply(is_model_ok, axis=1)
    return df[mask].copy(), df[~mask].copy()


def filter_price_outliers(df: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    """
    target_id + size_us 그룹별로 IQR 기반 가격 이상치를 제거합니다.

    그룹 내 데이터가 3개 미만이면 이상치 제거를 건너뜁니다.
    """
    keep_indices = []
    drop_indices = []

    group_cols = ["target_id", "size_us"]

    for _, group in df.groupby(group_cols):
        if len(group) < 3:
            # 데이터가 너무 적으면 이상치 판단 불가 → 전부 유지
            keep_indices.extend(group.index.tolist())
            continue

        prices = group["ebay_price_krw"]
        q1 = prices.quantile(0.25)
        q3 = prices.quantile(0.75)
        iqr = q3 - q1

        lower = q1 - IQR_MULTIPLIER * iqr
        upper = q3 + IQR_MULTIPLIER * iqr

        in_range = group[(prices >= lower) & (prices <= upper)].index.tolist()
        out_range = group[(prices < lower) | (prices > upper)].index.tolist()

        keep_indices.extend(in_range)
        drop_indices.extend(out_range)

    return df.loc[keep_indices].copy(), df.loc[drop_indices].copy()


# ---------------------------------------------------------------------------
# 메인
# ---------------------------------------------------------------------------

def main():
    if not INPUT_PATH.exists():
        raise FileNotFoundError(f"Input file not found: {INPUT_PATH}")

    df = pd.read_csv(INPUT_PATH)
    original_count = len(df)
    print(f"[filter] 입력 행 수: {original_count}")

    # 제거된 행을 이유와 함께 기록
    dropped_rows: list[pd.DataFrame] = []

    # 1. D등급 제거
    df, dropped = filter_grade_d(df)
    dropped["filter_reason"] = "condition_grade=D"
    dropped_rows.append(dropped)
    print(f"[filter] D등급 제거: {len(dropped)}건 → 잔여 {len(df)}건")

    # 2. 사이즈 불일치 / 키즈 상품 제거
    df, dropped = filter_size_mismatch(df)
    dropped["filter_reason"] = "size_mismatch_or_kids"
    dropped_rows.append(dropped)
    print(f"[filter] 사이즈 불일치/키즈 상품 제거: {len(dropped)}건 → 잔여 {len(df)}건")

    # 3. 모델 키워드 불일치 제거
    df, dropped = filter_model_keywords(df)
    dropped["filter_reason"] = "keyword_mismatch"
    dropped_rows.append(dropped)
    print(f"[filter] 키워드 불일치 제거: {len(dropped)}건 → 잔여 {len(df)}건")

    # 4. 가격 이상치 제거 (IQR)
    df, dropped = filter_price_outliers(df)
    dropped["filter_reason"] = "price_outlier_iqr"
    dropped_rows.append(dropped)
    print(f"[filter] 가격 이상치 제거: {len(dropped)}건 → 잔여 {len(df)}건")

    # 결과 저장
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(OUTPUT_PATH, index=False, encoding="utf-8-sig")
    print(f"\n[filter] 최종 저장: {OUTPUT_PATH}  ({len(df)}/{original_count}건 유지)")

    # 제거 로그 저장
    log_df = pd.concat(dropped_rows, ignore_index=True)
    log_df.to_csv(LOG_PATH, index=False, encoding="utf-8-sig")
    print(f"[filter] 제거 로그 저장: {LOG_PATH}  ({len(log_df)}건)")


if __name__ == "__main__":
    main()
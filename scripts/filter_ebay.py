from __future__ import annotations

import re
from pathlib import Path

import pandas as pd


BASE_DIR = Path(__file__).resolve().parents[1]

INPUT_PATH = BASE_DIR / "data" / "processed" / "ebay_normalized.csv"
OUTPUT_PATH = BASE_DIR / "data" / "processed" / "ebay_filtered.csv"
LOG_PATH = BASE_DIR / "data" / "processed" / "ebay_filter_log.csv"

IQR_MULTIPLIER = 1.5


# ---------------------------------------------------------------------------
# target_id별 포함 키워드
# ---------------------------------------------------------------------------
# 각 target은 아래 그룹을 모두 만족해야 통과합니다.
# 한 그룹 안에서는 하나만 포함되어도 통과합니다.
# ---------------------------------------------------------------------------

MODEL_KEYWORD_GROUPS: dict[int, list[list[str]]] = {
    1: [
        ["jordan 1", "air jordan 1", "jordan retro 1", "jordan1", "aj1", "dz5485"],
        ["lost and found", "lost & found", "chicago", "reimagined", "dz5485"],
    ],
    2: [
        ["samba og", "adidas samba og", "b75806", "js3832", "ih6820"],
        ["cloud white", "white black", "core black", "white/black", "black white"],
    ],
    3: [
        ["993", "mr993gl"],
        ["new balance", "nb"],
        ["gray", "grey", "core grey", "core gray"],
    ],
    4: [
        ["dunk low", "nike dunk low", "dd1391-100"],
        ["panda", "black white", "black/white", "white black", "white/black", "dd1391-100"],
    ],
    5: [
        ["air force 1", "af1", "cw2288-111"],
        ["white", "triple white", "cw2288-111"],
    ],
    6: [
        ["gel kayano 14", "gel-kayano 14", "kayano 14", "1201a019-108"],
        ["cream black", "cream/black", "silver cream", "metallic plum", "1201a019-108"],
    ],
    7: [
        ["salomon"],
        ["xt-6", "xt 6", "l410866", "410866"],
        ["black"],
    ],
    8: [
        ["2002r", "m2002r"],
        ["protection pack", "rain cloud", "m2002rda"],
    ],
    9: [
        ["gazelle indoor"],
        ["blue bird", "bluebird", "blue", "collegiate blue", "ji2061", "h06260"],
    ],
    10: [
        ["jordan 4", "air jordan 4", "retro 4", "dh6927"],
        ["military black", "dh6927"],
    ],
    11: [
        ["jordan 4", "air jordan 4", "retro 4", "fq8138"],
        ["white thunder", "black white thunder", "fq8138"],
    ],
    12: [
        ["990v4", "990 v4", "u990", "m990gl4"],
        ["new balance", "nb"],
        ["gray", "grey"],
    ],
    13: [
        ["air max 95", "am95"],
        ["neon", "volt"],
    ],
    14: [
        ["yeezy boost 350", "350 v2", "yeezy 350", "cp9654"],
        ["zebra", "cp9654"],
    ],
    15: [
        ["dunk low", "nike dunk low", "dd1391-103"],
        ["gray fog", "grey fog", "dd1391-103"],
    ],
}


# ---------------------------------------------------------------------------
# 전역 제외 키워드
# ---------------------------------------------------------------------------

GLOBAL_EXCLUDE_KEYWORDS = [
    "replica",
    "reps",
    "fake",
    "unauthorized",
    "custom",
    "replacement box only",
    "box only",
    "empty box",
    "laces only",
    "replacement laces",
    "keychain",
    "poster",
    "shirt",
    "hoodie",
]


# ---------------------------------------------------------------------------
# target_id별 제외 키워드
# ---------------------------------------------------------------------------

EXCLUDE_KEYWORDS_BY_TARGET: dict[int, list[str]] = {
    1: [
        "mid",
        "low",
        "cleat",
        "golf",
        "size 10m",
        "10m",
        "size 10 m",
        "10 m",
    ],

    2: [
        "sambae",
        "samba lt",
        "samba xlg",
        "samba jp",
        "jp cloud",
        "japan",
        "rhinestone",
        "crystal",
        "platform",
        "vegan",
        "(w)",
        "women",
        "woman",
        "women's",
        "woman's",
        "womens",
        "wmns",
    ],

    3: [
        "shadow gray",
        "shadow grey",
        "shadow gray driftwood",
        "shadow grey driftwood",
        "covert green",
        "incense grey",
        "incense gray",
        "baltic sea",
        "black slate",
        "u993rg",
        "u993gg",
        "u993bb",
        "wr993",
        "wr993gl",
        "woman",
        "woman's",
        "women",
        "women's",
        "womens",
        "joefreshgoods",
        "jfg",
    ],

    4: [
        "reverse panda",
        "world champ",
        "panda-monium",
        "panda monium",
        "panda mon",
        "ib2990",
        "dd1503",
        "dj6188",
        "dunk high",
        "dunk mid",
        "sb dunk",
        "platform",
        "disrupt",
        "twist",
    ],

    5: [
        "purple",
        "pink",
        "blue",
        "orange",
        "red",
        "green",
        "black white",
        "black/white",
        "white black",
        "white/black",
        "volt",
        "pixel",
        "multi-color",
        "multicolor",
        "multi color",
        "premium black",
        "sail",
        "independence day",
        "shadow",
        "react",
        "crater",
        "boot",
        "high",
        "mid",
        "dz4510",
        "cv8480",
        "im6643",
    ],

    6: [
        "pure silver",
        "pure gold",
        "piquant orange",
        "1201a019-006",
        "1201a019 006",
        "1201a019-102",
        "1201a019 102",
        "gel kayano 20",
        "gel-kayano 20",
        "gel nimbus",
        "gel-nimbus",
        "versablast",
        "trail scout",
        "kith",
        "scarab",
        "gel lyte",
        "gt-2160",
    ],

    7: [
        "gore-tex",
        "gore tex",
        "gtx",
        "skyline",
        "expanse",
        "jjjjound",
        "nautical",
        "dragon fire",
        "coffee",
        "vanilla ice",
        "maritime",
        "pewter",
        "portabella",
        "mahogany",
        "safari",
        "bistro",
        "almond cream",
        "aurora red",
        "sharp green",
        "french roast",
        "castlerock",
        "lunar rock",
        "north atlantic",
        "flame scarlet",
        "fiery red",
        "rose",
        "tawny port",
        "green milieu",
        "cxt",
        "acs",
        "xt-4",
        "xt4",
    ],

    8: [
        "phantom",
        "refined future",
        "2002rd",
        "2002rx",
        "sea salt",
        "black",
        "navy",
        "women",
        "woman",
        "women's",
        "woman's",
        "womens",
    ],

    9: [
        "samba",
        "handball",
        "campus",
        "spezial",
    ],

    10: [
        "jordan 4 rm",
        "red thunder",
        "thunder",
        "white thunder",
        "midnight navy",
        "infrared",
        "craft",
        "breds",
        "bred",
    ],

    11: [
        "red thunder",
        "military black",
        "midnight navy",
        "infrared",
        "craft",
        "breds",
        "bred",
    ],

    12: [
        "990v3",
        "990 v3",
        "990v5",
        "990 v5",
        "990v6",
        "990 v6",
        "991",
        "992",
        "993",
        "women",
        "woman",
        "women's",
        "woman's",
        "womens",
    ],

    13: [
        "air max 90",
        "air max 97",
        "air max plus",
        "vapormax",
    ],

    14: [
        "semi frozen",
        "beluga",
        "bone",
        "cream",
        "static",
        "carbon",
        "slate",
        "slide",
        "foam",
        "yeezy 500",
        "yeezy 700",
    ],

    15: [
        "panda",
        "black white",
        "black/white",
        "white black",
        "white/black",
        "grey fog camo",
        "gray fog camo",
        "unlv",
        "satin",
        "lottery",
        "championship",
        "dunk high",
        "dunk mid",
        "sb dunk",
        "platform",
    ],
}


# ---------------------------------------------------------------------------
# 공통 유틸
# ---------------------------------------------------------------------------

def normalize_text(value: str) -> str:
    """
    비교용 텍스트 정규화.
    특수문자를 공백으로 바꿔서 keyword 비교를 쉽게 만든다.
    """
    text = str(value).lower()
    text = text.replace("&", " and ")
    text = text.replace("/", " ")
    text = text.replace("-", " ")
    text = text.replace("_", " ")
    text = text.replace("’", "'")
    text = text.replace("“", '"').replace("”", '"')
    text = re.sub(r"[^a-z0-9.\s]", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def add_filter_reason(df: pd.DataFrame, reason: str) -> pd.DataFrame:
    df = df.copy()
    df["filter_reason"] = reason
    return df


def keyword_match(title: str, keyword: str) -> bool:
    """
    raw title과 normalized title을 둘 다 검사한다.

    중요한 예외:
    - "(W)"는 raw title에서만 검사해야 한다.
    - normalize_text("(W)")는 "w"가 되는데,
      이걸 normalized 비교에 쓰면 cloud white, new with box 같은 정상 상품까지 전부 걸린다.
    """
    raw_title = str(title).lower()
    raw_keyword = str(keyword).lower()

    # 원문 기준 먼저 검사
    if raw_keyword in raw_title:
        return True

    normalized_title = normalize_text(title)
    normalized_keyword = normalize_text(keyword)

    # 정규화 결과가 너무 짧으면 normalized 비교 금지
    # 예: "(w)" -> "w"
    if len(normalized_keyword) <= 1:
        return False

    return normalized_keyword in normalized_title


# ---------------------------------------------------------------------------
# 사이즈 / 성별 판별
# ---------------------------------------------------------------------------

YOUTH_KIDS_PATTERNS = [
    r"\b\d+(?:\.\d+)?c\b",
    r"\b\d+(?:\.\d+)?\s*c\b",
    r"\b\d+(?:\.\d+)?y\b",
    r"\b\d+(?:\.\d+)?\s*y\b",
    r"\bgs\b",
    r"\bps\b",
    r"\btd\b",
    r"\bgrade school\b",
    r"\bbig kids\b",
    r"\blittle kids\b",
    r"\bchild\b",
    r"\bkids\b",
    r"\byouth\b",
    r"\binfant\b",
    r"\btoddler\b",
    r"\bpreschool\b",
]


WOMEN_PATTERNS = [
    r"\bwomen\b",
    r"\bwoman\b",
    r"\bwomens\b",
    r"\bwomen's\b",
    r"\bwoman's\b",
    r"\bwomen s\b",
    r"\bwoman s\b",
    r"\bladies\b",
    r"\bwmns\b",
    r"\(w\)",
    r"\b\(women\)\b",
    r"\b\d+(?:\.\d+)?w\b",
    r"\b\d+(?:\.\d+)?\s*w\b",
    r"\bw\s*\d+(?:\.\d+)?\b",
    r"\b\d+(?:\.\d+)?m\s*/\s*\d+(?:\.\d+)?w\b",
]


def is_youth_or_kids_title(title: str) -> bool:
    title_lower = str(title).lower()
    return any(re.search(pattern, title_lower) for pattern in YOUTH_KIDS_PATTERNS)


def is_women_title(title: str) -> bool:
    title_lower = str(title).lower()
    return any(re.search(pattern, title_lower) for pattern in WOMEN_PATTERNS)


def extract_men_sizes_from_title(title: str) -> list[float]:
    """
    item_title에서 성인 남성 US 사이즈로 보이는 숫자를 추출한다.

    잡는 케이스:
    - Size 9
    - Size 10M
    - 10M
    - US10.5
    - 8.5M/10W
    """
    title_lower = str(title).lower()

    patterns = [
        r"\bmen(?:'s)?\s*size\s*(\d+(?:\.\d+)?)\b",
        r"\bmens\s*size\s*(\d+(?:\.\d+)?)\b",
        r"\bmen(?:'s)?\s*us\s*(\d+(?:\.\d+)?)\b",
        r"\bmens\s*us\s*(\d+(?:\.\d+)?)\b",
        r"\bmen(?:'s)?\s*(\d+(?:\.\d+)?)\b",
        r"\bmens\s*(\d+(?:\.\d+)?)\b",

        r"\bsize\s*us\s*(\d+(?:\.\d+)?)\b",
        r"\bus\s*(\d+(?:\.\d+)?)\b",
        r"\bus(\d+(?:\.\d+)?)\b",
        r"\b(\d+(?:\.\d+)?)\s*us\b",

        r"\bsize\s*(\d+(?:\.\d+)?)\s*mens\b",
        r"\bsize\s*(\d+(?:\.\d+)?)\s*men(?:'s)?\b",
        r"\bsize\s*(\d+(?:\.\d+)?)m\b",
        r"\bsize\s*(\d+(?:\.\d+)?)\s*m\b",
        r"\bsize\s*(\d+(?:\.\d+)?)\b",

        r"\bsz\s*(\d+(?:\.\d+)?)\b",
        r"\b(\d+(?:\.\d+)?)m\b",
        r"\b(\d+(?:\.\d+)?)\s*m\b",
        r"\b(\d+(?:\.\d+)?)m\s*/\s*\d+(?:\.\d+)?w\b",
        r"\b(\d+(?:\.\d+)?)\s*m\s*/\s*\d+(?:\.\d+)?\s*w\b",
    ]

    sizes: list[float] = []

    for pattern in patterns:
        for match in re.findall(pattern, title_lower):
            try:
                size = float(match)

                # 신발 사이즈로 현실적인 범위만 허용
                if 3.0 <= size <= 18.0:
                    sizes.append(size)
            except ValueError:
                pass

    return sorted(set(sizes))


# ---------------------------------------------------------------------------
# 필터 함수
# ---------------------------------------------------------------------------

def filter_grade_d(df: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    """
    D등급 상품 제거.
    unknown은 일단 남긴다.
    """
    mask = df["condition_grade"].astype(str).str.upper() != "D"
    return df[mask].copy(), df[~mask].copy()


def filter_duplicate_urls(df: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    """
    동일 item_url 중복 제거.
    """
    if "item_url" not in df.columns:
        return df.copy(), df.iloc[0:0].copy()

    duplicate_mask = df.duplicated(subset=["item_url"], keep="first")
    return df[~duplicate_mask].copy(), df[duplicate_mask].copy()


def filter_size_mismatch(df: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    """
    사이즈 불일치 제거.

    기준:
    - 키즈/GS/PS/TD/C/Y 제거
    - 여성용/W 제거
    - title에서 남성 사이즈가 발견되면 target size_us와 일치해야 통과
    - title에 사이즈 정보가 아예 없으면 일단 통과
    """
    def is_size_ok(row) -> bool:
        title = str(row.get("item_title", ""))

        if is_youth_or_kids_title(title):
            return False

        if is_women_title(title):
            return False

        try:
            target_size = float(row["size_us"])
        except (ValueError, TypeError, KeyError):
            return True

        found_sizes = extract_men_sizes_from_title(title)

        if not found_sizes:
            return True

        return target_size in found_sizes

    mask = df.apply(is_size_ok, axis=1)
    return df[mask].copy(), df[~mask].copy()


def filter_excluded_keywords(df: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    """
    전역 제외 키워드 + target별 제외 키워드 제거.
    """
    def is_not_excluded(row) -> bool:
        title = str(row.get("item_title", ""))

        try:
            tid = int(row["target_id"])
        except (ValueError, TypeError, KeyError):
            return True

        for keyword in GLOBAL_EXCLUDE_KEYWORDS:
            if keyword_match(title, keyword):
                return False

        for keyword in EXCLUDE_KEYWORDS_BY_TARGET.get(tid, []):
            if keyword_match(title, keyword):
                return False

        return True

    mask = df.apply(is_not_excluded, axis=1)
    return df[mask].copy(), df[~mask].copy()


def filter_model_keywords(df: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    """
    target_id별 포함 키워드 그룹 검사.
    """
    def is_model_ok(row) -> bool:
        title = str(row.get("item_title", ""))

        try:
            tid = int(row["target_id"])
        except (ValueError, TypeError, KeyError):
            return True

        groups = MODEL_KEYWORD_GROUPS.get(tid)

        if not groups:
            return True

        for group in groups:
            if not any(keyword_match(title, keyword) for keyword in group):
                return False

        return True

    mask = df.apply(is_model_ok, axis=1)
    return df[mask].copy(), df[~mask].copy()


def filter_price_outliers(df: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    """
    target_id + size_us 그룹별 IQR 가격 이상치 제거.
    그룹 내 데이터가 4개 미만이면 이상치 판단을 건너뜁니다.
    """
    keep_parts = []
    drop_parts = []

    group_cols = ["target_id", "size_us"]

    for _, group in df.groupby(group_cols):
        group = group.copy()

        if len(group) < 4:
            keep_parts.append(group)
            continue

        prices = pd.to_numeric(group["ebay_price_krw"], errors="coerce")

        q1 = prices.quantile(0.25)
        q3 = prices.quantile(0.75)
        iqr = q3 - q1

        if iqr == 0:
            keep_parts.append(group)
            continue

        lower = q1 - IQR_MULTIPLIER * iqr
        upper = q3 + IQR_MULTIPLIER * iqr

        mask = prices.between(lower, upper)

        keep_parts.append(group[mask].copy())
        drop_parts.append(group[~mask].copy())

    keep_df = pd.concat(keep_parts, ignore_index=True) if keep_parts else pd.DataFrame(columns=df.columns)
    drop_df = pd.concat(drop_parts, ignore_index=True) if drop_parts else pd.DataFrame(columns=df.columns)

    return keep_df.copy(), drop_df.copy()


def print_target_counts(df: pd.DataFrame) -> None:
    print("\n[filter] target_id별 최종 개수")

    if df.empty:
        print("비어 있음")
        return

    counts = (
        df.groupby(["target_id", "brand", "model", "colorway"])
        .size()
        .reset_index(name="count")
        .sort_values("target_id")
    )

    print(counts.to_string(index=False))


# ---------------------------------------------------------------------------
# 메인
# ---------------------------------------------------------------------------

def main() -> None:
    if not INPUT_PATH.exists():
        raise FileNotFoundError(f"Input file not found: {INPUT_PATH}")

    print(f"[filter] INPUT_PATH: {INPUT_PATH.resolve()}")
    print(f"[filter] OUTPUT_PATH: {OUTPUT_PATH.resolve()}")
    print(f"[filter] LOG_PATH: {LOG_PATH.resolve()}")

    df = pd.read_csv(INPUT_PATH)
    original_count = len(df)

    print(f"\n[filter] 입력 행 수: {original_count}")

    dropped_rows: list[pd.DataFrame] = []

    # 가격 숫자화
    df["ebay_price_krw"] = pd.to_numeric(df["ebay_price_krw"], errors="coerce")

    # 가격 없는 행 제거
    missing_price = df[df["ebay_price_krw"].isna()].copy()
    if not missing_price.empty:
        dropped_rows.append(add_filter_reason(missing_price, "missing_price"))

    df = df[df["ebay_price_krw"].notna()].copy()
    print(f"[filter] 가격 없는 행 제거: {len(missing_price)}건 → 잔여 {len(df)}건")

    # 1. D등급 제거
    df, dropped = filter_grade_d(df)
    if not dropped.empty:
        dropped_rows.append(add_filter_reason(dropped, "condition_grade_D"))
    print(f"[filter] D등급 제거: {len(dropped)}건 → 잔여 {len(df)}건")

    # 2. URL 중복 제거
    df, dropped = filter_duplicate_urls(df)
    if not dropped.empty:
        dropped_rows.append(add_filter_reason(dropped, "duplicate_item_url"))
    print(f"[filter] 중복 URL 제거: {len(dropped)}건 → 잔여 {len(df)}건")

    # 3. 사이즈 / 키즈 / 여성용 제거
    df, dropped = filter_size_mismatch(df)
    if not dropped.empty:
        dropped_rows.append(add_filter_reason(dropped, "size_mismatch_kids_or_women"))
    print(f"[filter] 사이즈/키즈/여성용 제거: {len(dropped)}건 → 잔여 {len(df)}건")

    # 4. 제외 키워드 제거
    df, dropped = filter_excluded_keywords(df)
    if not dropped.empty:
        dropped_rows.append(add_filter_reason(dropped, "excluded_keyword"))
    print(f"[filter] 제외 키워드 제거: {len(dropped)}건 → 잔여 {len(df)}건")

    # 5. 모델 / 컬러 키워드 불일치 제거
    df, dropped = filter_model_keywords(df)
    if not dropped.empty:
        dropped_rows.append(add_filter_reason(dropped, "keyword_mismatch"))
    print(f"[filter] 모델/컬러 키워드 불일치 제거: {len(dropped)}건 → 잔여 {len(df)}건")

    # 6. 가격 이상치 제거
    df, dropped = filter_price_outliers(df)
    if not dropped.empty:
        dropped_rows.append(add_filter_reason(dropped, "price_outlier_iqr"))
    print(f"[filter] 가격 이상치 제거: {len(dropped)}건 → 잔여 {len(df)}건")

    # 정렬
    sort_cols = [col for col in ["target_id", "ebay_price_krw"] if col in df.columns]
    if sort_cols:
        df = df.sort_values(sort_cols).reset_index(drop=True)

    # 저장
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(OUTPUT_PATH, index=False, encoding="utf-8-sig")

    if dropped_rows:
        log_df = pd.concat(dropped_rows, ignore_index=True)
    else:
        log_df = pd.DataFrame(columns=list(df.columns) + ["filter_reason"])

    log_df.to_csv(LOG_PATH, index=False, encoding="utf-8-sig")

    print_target_counts(df)

    print("\n[filter] 완료")
    print(f"[filter] 최종 저장: {OUTPUT_PATH}")
    print(f"[filter] 제거 로그 저장: {LOG_PATH}")
    print(f"[filter] 최종 남은 데이터: {len(df)}/{original_count}건")
    print(f"[filter] 제거된 데이터: {len(log_df)}건")


if __name__ == "__main__":
    main()
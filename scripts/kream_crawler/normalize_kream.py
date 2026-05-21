import os
import glob
import re
import pandas as pd

product_mapping = {
    'jordan1lostandfound': {'target_id': 'SH-001', '브랜드': 'Jordan', '모델명': '1 Retro High', '컬러웨이': 'Lost and Found', '상품명': 'Jordan 1 Lost and Found'},
    'adidassambaogcloudwhiteblack': {'target_id': 'SH-002', '브랜드': 'Adidas', '모델명': 'Samba OG', '컬러웨이': 'Cloud White Black', '상품명': 'Adidas Samba OG Cloud White Black'},
    'newbalance993gray': {'target_id': 'SH-003', '브랜드': 'New Balance', '모델명': '993', '컬러웨이': 'Gray', '상품명': 'New Balance 993 Gray'},
    'nikedunklowpanda': {'target_id': 'SH-004', '브랜드': 'Nike', '모델명': 'Dunk Low', '컬러웨이': 'Panda', '상품명': 'Nike Dunk Low Panda'},
    'nikeairforce1lowwhite': {'target_id': 'SH-005', '브랜드': 'Nike', '모델명': 'Air Force 1 Low', '컬러웨이': 'White', '상품명': 'Nike Air Force 1 Low White'},
    'asicsgelkayano14creamblack': {'target_id': 'SH-006', '브랜드': 'Asics', '모델명': 'Gel-Kayano 14', '컬러웨이': 'Cream Black', '상품명': 'Asics Gel-Kayano 14 Cream Black'},
    'salomonxt6black': {'target_id': 'SH-007', '브랜드': 'Salomon', '모델명': 'XT-6', '컬러웨이': 'Black', '상품명': 'Salomon XT-6 Black'},
    'newbalance2002rprotectionpackraincloud': {'target_id': 'SH-008', '브랜드': 'New Balance', '모델명': '2002R', '컬러웨이': 'Protection Pack Rain Cloud', '상품명': 'New Balance 2002R Protection Pack Rain Cloud'},
    'adidasgazelleindoorbluebird': {'target_id': 'SH-009', '브랜드': 'Adidas', '모델명': 'Gazelle Indoor', '컬러웨이': 'Blue Bird', '상품명': 'Adidas Gazelle Indoor Blue Bird'},
    'jordan4militaryblack': {'target_id': 'SH-010', '브랜드': 'Jordan', '모델명': '4 Retro', '컬러웨이': 'Military Black', '상품명': 'Jordan 4 Military Black'},
    'jordan4whitethunder': {'target_id': 'SH-011', '브랜드': 'Jordan', '모델명': '4 Retro', '컬러웨이': 'White Thunder', '상품명': 'Jordan 4 White Thunder'},
    'newbalance990v4gray': {'target_id': 'SH-012', '브랜드': 'New Balance', '모델명': '990v4', '컬러웨이': 'Gray', '상품명': 'New Balance 990v4 Gray'},
    'nikeairmax95neon': {'target_id': 'SH-013', '브랜드': 'Nike', '모델명': 'Air Max 95', '컬러웨이': 'Neon', '상품명': 'Nike Air Max 95 Neon'},
    'yeezyboost350v2zebra': {'target_id': 'SH-014', '브랜드': 'Adidas', '모델명': 'Yeezy Boost 350 V2', '컬러웨이': 'Zebra', '상품명': 'Yeezy Boost 350 V2 Zebra'},
    'nikedunklowgrayfog': {'target_id': 'SH-015', '브랜드': 'Nike', '모델명': 'Dunk Low', '컬러웨이': 'Gray Fog', '상품명': 'Nike Dunk Low Gray Fog'}
}

input_dir = 'data/output'
output_file = 'data/output/reference_dataset.csv'

search_files = glob.glob(os.path.join(input_dir, 'search_*.csv'))
transaction_files = glob.glob(os.path.join(input_dir, 'transactions_*.csv'))

url_to_meta = {}
clean_data = []

# Step 1: Search 파일에서 URL과 메타데이터 매핑 생성
for s_file in search_files:
    try:
        df = pd.read_csv(s_file)
        if df.empty or 'product_url' not in df.columns: continue
        
        url = df.iloc[0]['product_url']
        filename = os.path.basename(s_file)
        raw_keyword = filename.split('_')[-1].replace('.csv', '')
        normalized_name = re.sub(r'[^a-zA-Z0-9]', '', raw_keyword).lower()
        
        for key, meta in product_mapping.items():
            if key.startswith(normalized_name) or normalized_name.startswith(key):
                url_to_meta[url] = meta
                break
    except Exception as e:
        print(f"[검색 데이터 매핑 실패] {s_file}: {e}")

# Step 2: Transactions 파일 내의 모든 거래 데이터(최대 50건) 처리
for t_file in transaction_files:
    if os.path.basename(t_file) == 'reference_dataset.csv':
        continue
        
    try:
        df = pd.read_csv(t_file)
        if df.empty or 'product_url' not in df.columns:
            continue
            
        url = df.iloc[0]['product_url']
        meta = url_to_meta.get(url)
        
        if not meta:
            print(f"[스킵] 검색 결과와 매칭되는 URL을 찾을 수 없음: {t_file}")
            continue

        # df.iterrows()를 사용하여 파일 내의 모든 행(최대 50건)을 순회
        for index, row in df.iterrows():
            price_str = str(row['price'])
            clean_price_str = re.sub(r'[^0-9]', '', price_str)
            
            # 가격 정보가 없는 불량 데이터는 건너뜀
            if not clean_price_str:
                continue
                
            clean_price = int(clean_price_str)
            
            clean_row = {
                'target_id': meta['target_id'],
                '브랜드': meta['브랜드'],
                '모델명': meta['모델명'],
                '컬러웨이': meta['컬러웨이'],
                '한국 사이즈': row['size_option'],
                'KREAM 가격': clean_price,
                '가격 유형': row['tab_name'],
                '상품 URL': row['product_url'],
                '상품명': meta['상품명'],
                '수집일': str(row['collected_at']).split('T')[0],
                '상태': 'DS',
                '메모': f"거래시점: {row['trade_time']}" # 원래 몇 분 전/며칠 전 거래인지 기록
            }
            clean_data.append(clean_row)
            
    except Exception as e:
        print(f"[오류] 파일 처리 실패 ({t_file}): {e}")

if clean_data:
    final_df = pd.DataFrame(clean_data)
    final_df.to_csv(output_file, index=False, encoding='utf-8-sig')
    print(f"총 {len(clean_data)}건의 데이터 정제 및 '{output_file}' 저장 완료.")
else:
    print("처리할 수 있는 데이터가 없습니다.")
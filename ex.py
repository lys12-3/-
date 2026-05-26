import pandas as pd
import requests
import time
import re

# ==========================================
# 설정 구역
# ==========================================
TMAP_APP_KEY = 'qUnTOF5CvF5pb0wbvQ13b83kErTAvFDSa4OsT6Dt' 
INPUT_FILE = r"C:\Users\lys\Desktop\_mysite - 복사본\mysite\map\data\보안등_수정2.csv"
OUTPUT_FILE = '보안등_지오코딩_최종결과.csv'
# ==========================================

def clean_address(address):
    """주소 텍스트 보정 (띄어쓰기 및 불필요한 문구 제거)"""
    if not address or pd.isna(address) or str(address).lower() == "nan":
        return ""
    
    addr = str(address).strip()
    # 1. 괄호와 내용 제거 (예: (초원어린이집) -> 삭제)
    addr = re.sub(r'\(.*?\)', '', addr)
    # 2. '번지' 단어 제거
    addr = addr.replace('번지', '')
    # 3. 한글 뒤에 숫자가 바로 붙으면 띄어쓰기 (예: 진흥로450-8 -> 진흥로 450-8)
    addr = re.sub(r'([가-힣])(\d)', r'\1 \2', addr)
    # 4. 불필요한 공백 정리
    addr = ' '.join(addr.split())
    return addr

def call_tmap_api(address):
    """실제 Tmap API 호출 함수"""
    if not address: return None, None
    
    url = "https://apis.openapi.sk.com/tmap/geo/fullAddrGeo?version=1&format=json"
    headers = {"appKey": TMAP_APP_KEY}
    params = {"fullAddr": address}
    
    try:
        response = requests.get(url, headers=headers, params=params, timeout=5)
        if response.status_code == 200:
            result = response.json()
            if 'coordinateInfo' in result and 'coordinate' in result['coordinateInfo']:
                coord = result['coordinateInfo']['coordinate'][0]
                lat = coord.get('newLat') or coord.get('lat')
                lon = coord.get('newLon') or coord.get('lon')
                return float(lat), float(lon)
    except:
        pass
    return None, None

def get_coords_smart(road_addr, jibun_addr):
    """주소 종류별/형태별 3단계 재시도 로직"""
    # 1단계: 보정된 도로명 주소로 시도
    clean_road = clean_address(road_addr)
    lat, lon = call_tmap_api(clean_road)
    if lat: return lat, lon
    
    # 2단계: 보정된 지번 주소로 시도
    clean_jibun = clean_address(jibun_addr)
    lat, lon = call_tmap_api(clean_jibun)
    if lat: return lat, lon
    
    # 3단계: 주소 단순화 시도 (앞부분 '서울특별시' 제거)
    # 때로는 시/도 명칭이 없어야 더 잘 찾는 경우가 있음
    if clean_road:
        simple_road = clean_road.replace("서울특별시 ", "").replace("서울시 ", "")
        lat, lon = call_tmap_api(simple_road)
        if lat: return lat, lon
        
    return None, None

# 1. 데이터 불러오기
try:
    df = pd.read_csv(INPUT_FILE, encoding='utf-8-sig')
except:
    df = pd.read_csv(INPUT_FILE, encoding='cp949')

# 컬럼명 정리
df.columns = [col.strip() for col in df.columns]
df['위도'] = pd.to_numeric(df['위도'], errors='coerce')
df['경도'] = pd.to_numeric(df['경도'], errors='coerce')

print(f"총 {len(df)}건의 데이터를 처리합니다.")

# 2. 행별 반복 처리
for index, row in df.iterrows():
    # 이미 좌표가 있는 행은 건너뛰기 (선택 사항: 처음부터 다시 하려면 주석 처리)
    if pd.notna(row['위도']) and row['위도'] != 0:
        continue

    # 스마트 검색 실행
    lat, lon = get_coords_smart(row.get('소재지도로명주소'), row.get('소재지지번주소'))
    
    if lat:
        df.at[index, '위도'] = lat
        df.at[index, '경도'] = lon
    
    # 진행 상황 출력
    if index % 10 == 0:
        print(f"[{index}/{len(df)}] 처리 중... 결과: {lat}, {lon}")
        # 500개마다 중간 저장 (에러 대비)
        if index % 500 == 0:
            df.to_csv(OUTPUT_FILE, index=False, encoding='utf-8-sig')

    time.sleep(0.02) # TPS 제한 준수

# 3. 최종 결과 저장
df.to_csv(OUTPUT_FILE, index=False, encoding='utf-8-sig')
print(f"지오코딩 완료! 결과가 '{OUTPUT_FILE}'에 저장되었습니다.")
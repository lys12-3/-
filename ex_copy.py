import pandas as pd
import requests
import time
import re

# ==========================================
# 설정 구역
# ==========================================
KAKAO_API_KEY = 'daf233212eceeed858cd021549959868' 
INPUT_FILE = r"C:\Users\lys\Desktop\_mysite - 복사본\mysite\map\data\보안등_지오코딩_결과1.csv"
OUTPUT_FILE = '보안등_지오코딩_결과.csv'
LOG_FILE = 'failure_report.txt'
# ==========================================

def refine_address(address):
    """주소 텍스트 보정 (괄호 제거 및 도로명-번호 간 띄어쓰기)"""
    if not address or pd.isna(address) or str(address).lower() == "nan":
        return ""
    addr = str(address).strip()
    addr = re.sub(r'\(.*?\)', '', addr) # 괄호 및 내용 제거
    addr = addr.replace('번지', '')
    
    # 한글 뒤에 숫자가 붙어있는 경우 대비 (예: 진흥로450-8 -> 진흥로 450-8)
    addr = re.sub(r'([가-힣])(\d)', r'\1 \2', addr)
    return ' '.join(addr.split())

def call_kakao_address_api(query):
    """카카오 '주소 검색' API만 사용 (키워드 검색 X)"""
    if not query: return None
    url = 'https://dapi.kakao.com/v2/local/search/address.json'
    headers = {"Authorization": f"KakaoAK {KAKAO_API_KEY}"}
    
    try:
        response = requests.get(url, headers=headers, params={'query': query}, timeout=5)
        if response.status_code == 200:
            result = response.json()
            if result['documents']:
                # 가장 정확도가 높은 첫 번째 결과 반환
                return float(result['documents'][0]['y']), float(result['documents'][0]['x'])
        return None
    except:
        return None

# 데이터 로드
try:
    df = pd.read_csv(INPUT_FILE, encoding='utf-8-sig')
except:
    df = pd.read_csv(INPUT_FILE, encoding='cp949')

df.columns = [col.strip() for col in df.columns]
df['위도'] = pd.to_numeric(df.get('위도'), errors='coerce')
df['경도'] = pd.to_numeric(df.get('경도'), errors='coerce')

failure_list = []
total_rows = len(df)
processed_count = 0
success_count = 0

print(f"지오코딩 시작... 대상: {total_rows}건 (비어있는 좌표만 처리)")

for index, row in df.iterrows():
    # 이미 좌표가 있는 행은 건너뜀
    if pd.notna(row['위도']) and row['위도'] != 0:
        continue

    processed_count += 1
    road_raw = row.get('소재지도로명주소', '')
    jibun_raw = row.get('소재지지번주소', '')
    lat, lon = None, None

    # 1. 보정된 도로명 주소로 검색
    addr_road = refine_address(road_raw)
    if addr_road:
        res = call_kakao_address_api(addr_road)
        if res: lat, lon = res
    
    # 2. 도로명 실패 시 보정된 지번 주소로 검색
    if not lat:
        addr_jibun = refine_address(jibun_raw)
        if addr_jibun:
            res = call_kakao_address_api(addr_jibun)
            if res: lat, lon = res

    # 결과 처리
    if lat:
        df.at[index, '위도'] = lat
        df.at[index, '경도'] = lon
        success_count += 1
    else:
        # 실패한 경우 리스트에 담기
        reason = "검색 결과 없음" if (addr_road or addr_jibun) else "주소 데이터 비어있음"
        failure_list.append(f"행 {index} | 도로명: {road_raw} | 지번: {jibun_raw} | 사유: {reason}")

    # 100번마다 진행 상황 출력
    if processed_count % 100 == 0:
        print(f"진행 중... ({processed_count}건 시도 / 현재까지 {success_count}건 성공)")
        # 중간 저장 (비상용)
        df.to_csv(OUTPUT_FILE, index=False, encoding='utf-8-sig')

# 최종 저장
df.to_csv(OUTPUT_FILE, index=False, encoding='utf-8-sig')

# 실패 보고서 작성
with open(LOG_FILE, 'w', encoding='utf-8') as f:
    f.write("=== 지오코딩 실패 항목 리스트 (주소 검색 기준) ===\n")
    f.write(f"시도 횟수: {processed_count}건 / 성공: {success_count}건 / 실패: {len(failure_list)}건\n")
    f.write("-" * 80 + "\n")
    if not failure_list:
        f.write("실패한 항목이 없습니다.\n")
    for fail in failure_list:
        f.write(fail + "\n")

print(f"\n작업이 완료되었습니다.")
print(f"1. 결과 파일: {OUTPUT_FILE}")
print(f"2. 실패 리포트: {LOG_FILE} (이 파일을 열어 직접 처리할 항목을 확인하세요.)")
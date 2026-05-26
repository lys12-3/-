import os
import math
import pandas as pd
from rtree import index

# ──────────────────────────────────────────────
# 반경 설정 (미터) - 수정이 필요하면 여기서만 바꾸세요
# ──────────────────────────────────────────────
RADIUS = {
    "police":     300,
    "cctv":        50,
    "security":    30,
    "streetlamp":  20,
}

# 시설별 가중치 - 수정이 필요하면 여기서만 바꾸세요
WEIGHT = {
    "경찰서":     10,
    "지구대":      7,
    "파출소":      5,
    "cctv":        3,
    "security":    2,
    "streetlamp":  1,
}

# CSV 파일 경로 - 실제 경로로 수정하세요
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CSV_PATHS = {
    "police":     os.path.join(BASE_DIR, "data", "경찰서.csv"),
    "cctv":       os.path.join(BASE_DIR, "data", "CCTV.csv"),
    "security":   os.path.join(BASE_DIR, "data", "보안등.csv"),
    "streetlamp": os.path.join(BASE_DIR, "data", "가로등.csv"),
}

# 시설 타입별 아이콘 이름 (JS에서 마커 이미지 선택에 사용)
ICON_TYPE = {
    "경찰서":     "police",
    "지구대":     "police",
    "파출소":     "police",
    "cctv":       "cctv",
    "security":   "security",
    "streetlamp": "streetlamp",
}


# ──────────────────────────────────────────────
# 유틸
# ──────────────────────────────────────────────
def haversine(lat1, lon1, lat2, lon2):
    R = 6371000
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = math.sin(dlat/2)**2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon/2)**2
    return R * 2 * math.asin(math.sqrt(a))

def meters_to_deg(meters, lat=37.5):
    lat_deg = meters / 111320
    lon_deg = meters / (111320 * math.cos(math.radians(lat)))
    return lat_deg, lon_deg


# ──────────────────────────────────────────────
# 시설 데이터 로드 및 R-tree 인덱스 생성
# ──────────────────────────────────────────────
class SafetyIndex:
    def __init__(self):
        self.facilities = []
        self.rtree      = None
        self._load_all()
        self._build_rtree()

    def _add(self, lat, lon, ftype, weight, count=1):
        self.facilities.append({
            "lat": lat, "lon": lon,
            "type": ftype, "weight": weight, "count": count
        })

    def _load_all(self):
        self._load_police()
        self._load_cctv()
        self._load_security()
        self._load_streetlamp()
        print(f"[SafetyIndex] 총 시설 수: {len(self.facilities)}")

    def _load_police(self):
        try:
            df = pd.read_csv(CSV_PATHS["police"], encoding="utf-8")
            for _, row in df.iterrows():
                detail = str(row.get("상세", "파출소"))
                weight = WEIGHT.get(detail, WEIGHT["파출소"])
                self._add(row["위도"], row["경도"], detail, weight, int(row.get("개수", 1)))
            print(f"  경찰서/지구대/파출소: {len(df)}개")
        except Exception as e:
            print(f"  [경고] 경찰서 로드 실패: {e}")

    def _load_cctv(self):
        try:
            df = pd.read_csv(CSV_PATHS["cctv"], encoding="utf-8")
            for _, row in df.iterrows():
                self._add(row["위도"], row["경도"], "cctv", WEIGHT["cctv"], int(row.get("개수", 1)))
            print(f"  CCTV: {len(df)}개")
        except Exception as e:
            print(f"  [경고] CCTV 로드 실패: {e}")

    def _load_security(self):
        try:
            df = pd.read_csv(CSV_PATHS["security"], encoding="utf-8")
            for _, row in df.iterrows():
                self._add(row["위도"], row["경도"], "security", WEIGHT["security"], int(row.get("개수", 1)))
            print(f"  보안등: {len(df)}개")
        except Exception as e:
            print(f"  [경고] 보안등 로드 실패: {e}")

    def _load_streetlamp(self):
        try:
            df = pd.read_csv(CSV_PATHS["streetlamp"], encoding="utf-8")
            for _, row in df.iterrows():
                self._add(row["위도"], row["경도"], "streetlamp", WEIGHT["streetlamp"], int(row.get("개수", 1)))
            print(f"  가로등: {len(df)}개")
        except Exception as e:
            print(f"  [경고] 가로등 로드 실패: {e}")

    def _build_rtree(self):
        idx = index.Index()
        for i, f in enumerate(self.facilities):
            idx.insert(i, (f["lon"], f["lat"], f["lon"], f["lat"]))
        self.rtree = idx
        print(f"[SafetyIndex] R-tree 인덱스 생성 완료")


# ──────────────────────────────────────────────
# 경로 안전지수 계산 + 포함 시설 목록 반환
# ──────────────────────────────────────────────
def calc_route_safety(coords, safety_index, facility_type, radius_m):
    """
    반환: { "score": float, "facilities": [{"lat", "lon", "type", "icon"}] }
    """
    if not coords:
        return {"score": 0.0, "facilities": []}

    checked      = set()
    total_score  = 0.0
    found        = []
    lat_deg, lon_deg = meters_to_deg(radius_m)

    for coord in coords:
        clat, clon = coord["lat"], coord["lon"]

        candidates = list(safety_index.rtree.intersection((
            clon - lon_deg, clat - lat_deg,
            clon + lon_deg, clat + lat_deg
        )))

        for idx in candidates:
            if idx in checked:
                continue
            f = safety_index.facilities[idx]

            if facility_type == "police"     and f["type"] not in ("경찰서", "지구대", "파출소"): continue
            if facility_type == "cctv"       and f["type"] != "cctv":        continue
            if facility_type == "security"   and f["type"] != "security":    continue
            if facility_type == "streetlamp" and f["type"] != "streetlamp":  continue

            dist = haversine(clat, clon, f["lat"], f["lon"])
            if dist <= radius_m:
                total_score += f["weight"] * f["count"]
                checked.add(idx)
                found.append({
                    "lat":  f["lat"],
                    "lon":  f["lon"],
                    "type": f["type"],
                    "icon": ICON_TYPE.get(f["type"], "default")
                })

    return {"score": round(total_score, 2), "facilities": found}


def calc_safety_score(route, safety_index):
    coords = route.get("coords", [])

    police     = calc_route_safety(coords, safety_index, "police",     RADIUS["police"])
    cctv       = calc_route_safety(coords, safety_index, "cctv",       RADIUS["cctv"])
    security   = calc_route_safety(coords, safety_index, "security",   RADIUS["security"])
    streetlamp = calc_route_safety(coords, safety_index, "streetlamp", RADIUS["streetlamp"])

    return {
        "police_score":     police["score"],
        "cctv_score":       cctv["score"],
        "security_score":   security["score"],
        "streetlamp_score": streetlamp["score"],
        "total_score":      round(police["score"] + cctv["score"] + security["score"] + streetlamp["score"], 2),
        # 시설 목록 (JS 마커 표시용)
        "facilities": police["facilities"] + cctv["facilities"] + security["facilities"] + streetlamp["facilities"]
    }
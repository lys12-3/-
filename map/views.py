import json
from django.conf import settings
from django.shortcuts import render
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods

from .safety_score import SafetyIndex, calc_safety_score

# 서버 시작 시 CSV 한 번만 로드
safety_index = SafetyIndex()


def index(request):
    return render(request, 'map/simple_map.html', {
        'tmap_app_key': settings.TMAP_APP_KEY,
    })


@csrf_exempt
@require_http_methods(["POST"])
def recommend(request):
    try:
        body   = json.loads(request.body)
        routes = body.get("routes", [])

        if not routes:
            return JsonResponse({"error": "경로 데이터가 없습니다."}, status=400)

        results = []
        for route in routes:
            scores = calc_safety_score(route, safety_index)

            #지수 시간 반영 계산
            raw_total_score = scores["total_score"]
            duration_min = route.get("duration", 0)
            
            #시간 단위:분
            if duration_min > 0:
                adjusted_score = round((raw_total_score / duration_min), 1)
            else:
                adjusted_score = 0

            results.append({
                "name":             route.get("name"),
                "searchOption":     route.get("searchOption"),
                "distance":         round(route.get("distance", 0), 2),
                "duration":         round(route.get("duration", 0), 1),
                "coords":           route.get("coords", []),
                "police_score":     scores["police_score"],
                "cctv_score":       scores["cctv_score"],
                "security_score":   scores["security_score"],
                "streetlamp_score": scores["streetlamp_score"],
                "total_score":      adjusted_score,
                "facilities":       scores["facilities"],  # 마커 표시용
            })

        results.sort(key=lambda x: x["total_score"], reverse=True)

        print("=== 안전지수 계산 결과 ===")
        for r in results:
            print(f"  [{r['name']}] 총점:{r['total_score']} 시설수:{len(r['facilities'])}")

        return JsonResponse({"routes": results})

    except Exception as e:
        import traceback
        traceback.print_exc()
        return JsonResponse({"error": str(e)}, status=500)
from django.conf import settings
from django.shortcuts import render


def index(request):
    return render(request, 'map/simple_map.html', {
        'tmap_app_key': settings.TMAP_APP_KEY,
    })

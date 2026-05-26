from django.urls import path
from . import views

app_name = 'map'

urlpatterns = [
    path('', views.index, name='index'),
    path('api/recommend/', views.recommend, name='recommend'),
]
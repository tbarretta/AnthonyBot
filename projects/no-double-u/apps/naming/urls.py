from django.urls import path
from . import views

app_name = 'naming'

urlpatterns = [
    path('', views.name_it, name='name_it'),
    path('vote/<int:pk>/', views.vote, name='vote'),
    path('suggest/', views.suggest, name='suggest'),
]

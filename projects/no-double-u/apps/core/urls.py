from django.urls import path
from . import views

app_name = 'core'

urlpatterns = [
    path('', views.home, name='home'),
    path('the-case/', views.the_case, name='the_case'),
    path('hall-of-fame/', views.hall_of_fame, name='hall_of_fame'),
    path('join/', views.join, name='join'),
    path('moderation/', views.moderation_hub, name='moderation_hub'),
]

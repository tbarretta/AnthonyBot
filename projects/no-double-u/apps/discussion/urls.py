from django.urls import path
from . import views

app_name = 'discussion'

urlpatterns = [
    path('', views.discussion, name='discussion'),
    path('comment/', views.add_comment, name='add_comment'),
    path('comment/<int:pk>/flag/', views.flag_comment, name='flag_comment'),
]

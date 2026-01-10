from django.urls import path
from . import views

urlpatterns = [
    path('login/', views.login, name='login'),
    path('inbox_view/', views.inbox_view, name='inbox_view'),
]
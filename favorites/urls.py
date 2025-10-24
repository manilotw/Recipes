from django.urls import path
from . import views

app_name = 'favorites'

urlpatterns = [
    path('', views.index, name='index'),
    path('auth/', views.auth_view, name='auth'),
    path('card1/', views.card1, name='card1'),
    path('card2/', views.card2, name='card2'),
    path('card3/', views.card3, name='card3'),
    path('lk/', views.lk, name='lk'),
    path('order/', views.order, name='order'),
    path('registration/', views.registration, name='registration'),
    path('logout/', views.logout_view, name='logout'),
]

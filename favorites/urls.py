from django.urls import path
from . import views

app_name = 'favorites'

urlpatterns = [
    path('', views.index, name='index'),
    path('auth/', views.auth_view, name='auth'),
    path('card/<int:pk>/', views.card, name='card'),
    path('lk/', views.lk, name='lk'),
    path('order/', views.order, name='order'),
    path('registration/', views.registration, name='registration'),
    path('logout/', views.logout_view, name='logout'),
    path('replace-dish/<str:meal_type>/', views.replace_dish, name='replace_dish'),
]


from django.urls import path
from . import views

app_name = 'users'

urlpatterns = [
    path('', views.home, name='home'),                          # /users/
    path('register/', views.RegisterView.as_view(), name='users-register'),
    path('profile/', views.profile, name='users-profile'),      # /users/profile/
    path('profile/<str:username>/', views.profile_detail, name='profile_detail'),
    path('profile/<str:username>/treinos/', views.profile_treinos, name='profile_treinos'),
    path('profile/<str:username>/historico/', views.profile_historico, name='profile_historico'),
]

from django.urls import path
from . import views

urlpatterns = [
    path('', views.dashboard, name='dashboard'),
    path('puzzles/', views.puzzle_list, name='puzzle_list'),
    path('profile/', views.profile, name='profile'),
    path('toggle-owned/<int:puzzle_id>/', views.toggle_owned, name='toggle_owned'),
    path('toggle-completed/<int:puzzle_id>/', views.toggle_completed, name='toggle_completed'),
    path('register/', views.register, name='register'),
    path('puzzle/<int:puzzle_id>/', views.puzzle_detail, name='puzzle_detail'),
    path('friends/', views.friends_list, name='friends_list'),
    path('friends/handle-request/<int:friendship_id>/', views.handle_friend_request, name='handle_friend_request'),
    path('admin/import-puzzles/', views.trigger_import, name='trigger_import'),
    path('admin-dashboard/', views.admin_dashboard, name='admin_dashboard'),
] 
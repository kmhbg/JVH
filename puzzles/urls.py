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
    path('friend-puzzles/<int:friend_id>/', views.friend_puzzles, name='friend_puzzles'),
    path('request-borrow/<int:puzzle_id>/', views.request_borrow, name='request_borrow'),
    path('handle-borrow-request/<int:request_id>/', views.handle_borrow_request, name='handle_borrow_request'),
    path('delete-puzzle-image/<int:image_id>/', views.delete_puzzle_image, name='delete_puzzle_image'),
    path('mark-puzzle-sold/<int:puzzle_id>/', views.mark_puzzle_sold, name='mark_puzzle_sold'),
    path('remove-puzzle/<int:puzzle_id>/', views.remove_puzzle, name='remove_puzzle'),
] 
from django.urls import path

from . import views

urlpatterns = [
    # Public pages
    path('', views.landing_view, name='landing'),
    path('signup/', views.signup_view, name='signup'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),

    # Onboarding
    path('onboarding/', views.onboarding_view, name='onboarding'),

    # Main pages (bottom nav)
    path('home/', views.home_view, name='home'),
    path('stats/', views.stats_view, name='stats'),
    path('friends/', views.friends_view, name='friends'),
    path('calories/', views.calories_view, name='calories'),
    path('profile/', views.profile_view, name='profile'),

    # Actions (POST only)
    path('meal/save/', views.save_meal, name='save_meal'),
    path('weight/save/', views.save_weight, name='save_weight'),
    path('calories/add/', views.add_calorie, name='add_calorie'),
    path('calories/delete/<int:pk>/', views.delete_calorie, name='delete_calorie'),
    path('friends/request/<int:user_id>/', views.send_request, name='send_request'),
    path('friends/respond/<int:pk>/<str:action>/', views.respond_request, name='respond_request'),
    path('friends/remove/<int:user_id>/', views.remove_friend, name='remove_friend'),
    path('friends/cheer/<int:user_id>/', views.cheer_friend, name='cheer_friend'),
]
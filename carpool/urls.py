from django.urls import path
from django.contrib.auth import views as auth_views
from . import views

urlpatterns = [
    # General / Auth
    path('', views.splash_view, name='splash'),
    path('accounts/login/', auth_views.LoginView.as_view(template_name='accounts/login.html'), name='login'),
    path('accounts/logout/', auth_views.LogoutView.as_view(), name='logout'),
    path('accounts/signup/', views.signup_view, name='signup'),
    path('accounts/profile/', views.profile_view, name='profile'),
    
    # Dashboard
    path('dashboard/', views.dashboard_view, name='dashboard'),
    
    # Rides Finding & Offering
    path('rides/find/', views.find_ride_view, name='find_ride'),
    path('rides/find/confirm/', views.find_confirm_view, name='find_confirm'),
    path('rides/find/results/', views.ride_results_view, name='ride_results'),
    path('rides/book/', views.book_ride_view, name='book_ride'),
    path('rides/offer/', views.offer_ride_view, name='offer_ride'),
    path('rides/offer/confirm/', views.offer_confirm_view, name='offer_confirm'),
    path('rides/offer/publish/', views.publish_ride_view, name='publish_ride'),
    
    # Vehicles
    path('vehicles/', views.vehicle_list_view, name='vehicles'),
    path('vehicles/add/', views.add_vehicle_view, name='add_vehicle'),
    path('vehicles/delete/<int:vehicle_id>/', views.delete_vehicle_view, name='delete_vehicle'),
    
    # Trips & Chat Polling
    path('trips/', views.trips_list_view, name='trips'),
    path('trips/<int:trip_id>/', views.trip_detail_view, name='trip_detail'),
    path('trips/<int:trip_id>/update-status/', views.update_trip_status_view, name='update_trip_status'),
    path('trips/<int:trip_id>/track/', views.track_trip_view, name='track_trip'),
    path('trips/<int:trip_id>/chat/', views.get_chat_messages_view, name='get_chat'),
    path('trips/<int:trip_id>/chat/send/', views.send_chat_message_view, name='send_chat'),
    
    # Wallet & Payments
    path('wallet/', views.wallet_view, name='wallet'),
    path('wallet/recharge/init/', views.wallet_recharge_init_view, name='wallet_recharge_init'),
    path('wallet/recharge/verify/<int:user_id>/', views.wallet_recharge_verify_view, name='wallet_recharge_verify'),
    path('payments/<int:trip_id>/', views.payment_checkout_view, name='payment'),
    
    # History
    path('history/', views.history_list_view, name='history_list'),
    path('history/<int:trip_id>/', views.history_detail_view, name='history_detail'),
    
    # Reports
    path('reports/', views.reports_view, name='reports'),
    
    # Settings & Places
    path('notifications/mark-read/', views.mark_notifications_read_view, name='mark_notifications_read'),
    path('settings/', views.settings_view, name='settings'),
    path('settings/saved-places/', views.saved_places_view, name='saved_places'),
    path('settings/saved-places/delete/<int:place_id>/', views.delete_saved_place_view, name='delete_saved_place'),
    
    # Company Admin Panel
    path('admin-panel/', views.admin_dashboard_view, name='admin_dashboard'),
    path('admin-panel/employees/', views.admin_employees_view, name='admin_employees'),
    path('admin-panel/vehicles/', views.admin_vehicles_view, name='admin_vehicles'),
    path('admin-panel/config/', views.admin_config_view, name='admin_config'),
]

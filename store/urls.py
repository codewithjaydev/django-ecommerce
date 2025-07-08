from django.contrib.auth import views as auth_views
from django.urls import path
from django.shortcuts import redirect

from . import views  

def redirect_to_login_with_register(request):
    return redirect('login?action=register')

urlpatterns = [
    path('', views.store, name="store"),
    path('cart/',views.cart,name="cart"),
    path('checkout', views.checkout, name="checkout"),
    path('update_item/', views.updateItem, name="update_item"),
    # path('process_order/', views.processOrder,name="process_order")
    path('accounts/login/', views.auth_view, name='login'),
    path('accounts/logout/', views.logout_view, name='logout'),
    path('profile/', views.profile, name='profile'),
    path('register/', redirect_to_login_with_register, name='register'),
    path('test-registration/', views.test_registration, name='test_registration'),
    
    # eSewa Payment URLs
    path('payment/initiate/', views.initiate_payment, name='initiate_payment'),
    path('payment/success/', views.payment_success, name='payment_success'),
    path('payment/failure/', views.payment_failure, name='payment_failure'),
    path('payment/cancel/', views.payment_cancel, name='payment_cancel'),
    path('payment/status/', views.payment_status, name='payment_status'),
]

from django.urls import path, reverse
from django.shortcuts import redirect
from . import views  

def redirect_to_login_with_register(request):
    url = reverse('login') + '?action=register'
    return redirect(url)

urlpatterns = [
    path('', views.store, name="store"),
    path('cart/', views.cart, name="cart"),
    path('checkout/', views.checkout, name="checkout"),
    path('update_item/', views.updateItem, name="update_item"),
    path('accounts/login/', views.auth_view, name='login'),
    path('accounts/logout/', views.logout_view, name='logout'),
    path('profile/', views.profile, name='profile'),
    path('register/', redirect_to_login_with_register, name='register'),
    path('clear-orders/', views.clear_orders, name='clear_orders'),
    # eSewa Payment URLs
    path('payment/initiate/', views.initiate_payment, name='initiate_payment'),
    path('payment/success/', views.payment_success, name='payment_success'),
    path('payment/failure/', views.payment_failure, name='payment_failure'),
    path('cod-order/', views.cod_order, name='cod_order'),
]

from django.contrib.auth import views as auth_views
from django.urls import path

from . import views  

urlpatterns = [
    path('', views.store, name="store"),
    path('cart/',views.cart,name="cart"),
    path('checkout', views.checkout, name="checkout"),
    path('update_item/', views.updateItem, name="update_item"),
    # path('process_order/', views.processOrder,name="process_order")
    path('accounts/login/', auth_views.LoginView.as_view(), name='login'),
    path('accounts/logout/', auth_views.LogoutView.as_view(), name='logout'),


    path('profile/', views.profile, name='profile'),
    path('register/', views.register, name='register'),
]

from django.urls import path
from . import adminpanel_views

urlpatterns = [
    path('', adminpanel_views.dashboard, name='adminpanel_dashboard'),
    path('orders/', adminpanel_views.orders, name='adminpanel_orders'),
    path('products/', adminpanel_views.products, name='adminpanel_products'),
    path('products/add/', adminpanel_views.product_add, name='adminpanel_product_add'),
    path('products/<int:product_id>/edit/', adminpanel_views.product_edit, name='adminpanel_product_edit'),
    path('products/<int:product_id>/delete/', adminpanel_views.product_delete, name='adminpanel_product_delete'),
    path('users/', adminpanel_views.users, name='adminpanel_users'),
    path('logout/', adminpanel_views.admin_logout, name='adminpanel_logout'),
] 
from django.contrib.admin.views.decorators import staff_member_required
from django.shortcuts import render, redirect
from django.contrib.auth import logout
from .models import Order, Product, Customer
from django.contrib.auth.models import User
from django import forms

class ProductForm(forms.ModelForm):
    class Meta:
        model = Product
        fields = ['name', 'price', 'image']

@staff_member_required
def dashboard(request):
    return render(request, 'adminpanel/dashboard.html')

@staff_member_required
def orders(request):
    orders = Order.objects.all().order_by('-date_orderd')
    return render(request, 'adminpanel/orders.html', {'orders': orders})

@staff_member_required
def products(request):
    products = Product.objects.all()
    return render(request, 'adminpanel/products.html', {'products': products})

@staff_member_required
def users(request):
    users = User.objects.all()
    return render(request, 'adminpanel/users.html', {'users': users})

@staff_member_required
def admin_logout(request):
    logout(request)
    return redirect('adminpanel_dashboard')

@staff_member_required
def product_add(request):
    if request.method == 'POST':
        form = ProductForm(request.POST, request.FILES)
        if form.is_valid():
            form.save()
            return redirect('adminpanel_products')
    else:
        form = ProductForm()
    return render(request, 'adminpanel/product_form.html', {'form': form, 'action': 'Add'})

@staff_member_required
def product_edit(request, product_id):
    product = Product.objects.get(id=product_id)
    if request.method == 'POST':
        form = ProductForm(request.POST, request.FILES, instance=product)
        if form.is_valid():
            form.save()
            return redirect('adminpanel_products')
    else:
        form = ProductForm(instance=product)
    return render(request, 'adminpanel/product_form.html', {'form': form, 'action': 'Edit'})

@staff_member_required
def product_delete(request, product_id):
    product = Product.objects.get(id=product_id)
    if request.method == 'POST':
        product.delete()
        return redirect('adminpanel_products')
    return render(request, 'adminpanel/product_confirm_delete.html', {'product': product}) 
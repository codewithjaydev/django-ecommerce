from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse
import json
import requests
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from django.contrib.auth import login, authenticate, logout
from django.contrib import messages
from django import forms
from .models import Customer, Order, OrderItem, Product
from .esewa_utils import ESewaPayment

# ---------- Custom User Form ----------

class CustomUserCreationForm(UserCreationForm):
    """User form without default password validation hints."""
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in ['password1', 'password2']:
            self.fields[field].validators = []
            self.fields[field].help_text = ''
        self.fields['username'].help_text = ''
        self.fields['password1'].label = 'Password'
        self.fields['password2'].label = 'Confirm Password'

    def clean_password1(self):
        pw = self.cleaned_data.get('password1')
        if not pw:
            raise forms.ValidationError('Password cannot be blank.')
        return pw

    def clean_password2(self):
        pw1 = self.cleaned_data.get('password1')
        pw2 = self.cleaned_data.get('password2')
        if pw1 and pw2 and pw1 != pw2:
            raise forms.ValidationError('Passwords do not match.')
        return pw2

# ---------- Authentication Views ----------

def auth_view(request):
    login_form = AuthenticationForm()
    register_form = CustomUserCreationForm()
    if request.method == 'POST':
        if 'login' in request.POST:
            login_form = AuthenticationForm(request, data=request.POST)
            if login_form.is_valid():
                user = authenticate(
                    username=login_form.cleaned_data['username'],
                    password=login_form.cleaned_data['password']
                )
                if user:
                    login(request, user)
                    return redirect('store')
                messages.error(request, 'Invalid credentials.')
        elif 'register' in request.POST:
            register_form = CustomUserCreationForm(request.POST)
            if register_form.is_valid():
                user = register_form.save()
                Customer.objects.get_or_create(user=user)
                login(request, user)
                messages.success(request, 'Account created!')
                return redirect('store')
            else:
                print("Registration errors:", register_form.errors)
    return render(request, 'registration/login.html', {
        'login_form': login_form, 'register_form': register_form
    })

def register(request):
    form = CustomUserCreationForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        user = form.save()
        Customer.objects.get_or_create(user=user)
        login(request, user)
        messages.success(request, 'User registered!')
        return redirect('store')
    return render(request, 'store/register.html', {'form': form})

@login_required
def logout_view(request):
    logout(request)
    messages.success(request, 'Logged out.')
    return redirect('store')

# ---------- Store & Cart Views ----------

def store(request):
    if request.user.is_authenticated:
        customer, _ = Customer.objects.get_or_create(user=request.user)
        order, _ = Order.objects.get_or_create(customer=customer, complete=False)
        cartItems = order.get_cart_items if hasattr(order, 'get_cart_items') else 0
    else:
        cartItems = 0
    products = Product.objects.all()
    return render(request, 'store/store.html', {'products': products, 'cartItems': cartItems})

@login_required
def cart(request):
    customer, _ = Customer.objects.get_or_create(user=request.user)
    order, _ = Order.objects.get_or_create(customer=customer, complete=False)
    items = [i for i in order.orderitem_set.all() if i.product]
    return render(request, 'store/cart.html', {
        'items': items, 'order': order, 'cartItems': order.get_cart_items
    })

@login_required
def checkout(request):
    customer, _ = Customer.objects.get_or_create(user=request.user)
    order, _ = Order.objects.get_or_create(customer=customer, complete=False)
    items = [i for i in order.orderitem_set.all() if i.product]
    return render(request, 'store/checkout.html', {
        'items': items, 'order': order, 'cartItems': order.get_cart_items
    })

@login_required
def updateItem(request):
    data = json.loads(request.body)
    product = Product.objects.get(id=data['productId'])
    customer, _ = Customer.objects.get_or_create(user=request.user)
    order, _ = Order.objects.get_or_create(customer=customer, complete=False)
    orderItem, _ = OrderItem.objects.get_or_create(order=order, product=product)
    
    if data['action'] == 'add':
        orderItem.quantity += 1
    elif data['action'] == 'remove':
        orderItem.quantity -= 1

    orderItem.save()
    if orderItem.quantity <= 0:
        orderItem.delete()
    
    return JsonResponse('Cart updated', safe=False)

@login_required
def profile(request):
    customer, _ = Customer.objects.get_or_create(user=request.user)
    orders = Order.objects.filter(customer=customer, complete=True).order_by('-date_orderd').prefetch_related('orderitem_set__product')
    return render(request, 'store/user/profile.html', {'orders': orders})

# ---------- eSewa Payment Flow ----------

@login_required
def initiate_payment(request):
    try:
        customer, _ = Customer.objects.get_or_create(user=request.user)
        order, _ = Order.objects.get_or_create(customer=customer, complete=False)
        if order.get_cart_items == 0:
            messages.error(request, 'Your cart is empty.')
            return redirect('cart')

        esewa = ESewaPayment()
        payment_data, transaction_id = esewa.generate_payment_data(order, request)
        order.transaction_id = transaction_id
        order.payment_method = 'esewa'
        order.save()

        payment_url = esewa.get_payment_url(payment_data)

        try:
            resp = requests.get('https://esewa.com.np', timeout=5)
            if resp.status_code != 200:
                messages.warning(request, 'eSewa seems down.')
        except requests.RequestException:
            messages.warning(request, 'Cannot reach eSewa now.')

        return redirect(payment_url)

    except Exception as e:
        messages.error(request, f'Error initiating payment: {e}')
        return redirect('checkout')

@login_required
def payment_success(request):
    oid = request.GET.get('oid')
    amt = request.GET.get('amt')
    refId = request.GET.get('refId')
    if not all([oid, amt, refId]):
        messages.error(request, 'Invalid payment callback.')
        return redirect('checkout')

    customer, _ = Customer.objects.get_or_create(user=request.user)
    order = get_object_or_404(Order, customer=customer, transaction_id=oid, complete=False)
    esewa = ESewaPayment()
    verified, msg = esewa.verify_payment(oid, amt, refId)

    if verified:
        if float(amt) != float(order.get_cart_total()):
            messages.error(request, 'Payment amount mismatch; please contact support.')
            return redirect('checkout')

        success, process_msg = esewa.process_successful_payment(order, refId, oid)
        if success:
            order.complete = True
            order.save()
            messages.success(request, 'Payment successful!')
            return redirect('store')
        messages.error(request, f'Post-verification error: {process_msg}')
    else:
        messages.error(request, f'Verification failed: {msg}')
    return redirect('checkout')

@login_required
def payment_failure(request):
    oid = request.GET.get('oid')
    if oid:
        customer, _ = Customer.objects.get_or_create(user=request.user)
        order = Order.objects.filter(customer=customer, transaction_id=oid, complete=False).first()
        if order:
            ESewaPayment().process_failed_payment(order, 'Failed/cancelled by user')
    messages.error(request, 'Payment cancelled or failed.')
    return redirect('checkout')

@login_required
def payment_cancel(request):
    messages.warning(request, 'Payment was cancelled.')
    return redirect('checkout')

@login_required
def payment_status(request):
    status = request.GET.get('status', 'unknown')
    error_message = request.GET.get('error', '')
    order = None
    if request.user.is_authenticated:
        customer, _ = Customer.objects.get_or_create(user=request.user)
        order = Order.objects.filter(customer=customer, complete=False).first()
    return render(request, 'store/payment_status.html', {
        'status': status, 'error_message': error_message, 'order': order
    })

@login_required
def cod_order(request):
    customer, _ = Customer.objects.get_or_create(user=request.user)
    order, _ = Order.objects.get_or_create(customer=customer, complete=False)
    if order.get_cart_items == 0:
        messages.error(request, 'Your cart is empty.')
        return redirect('cart')
    order.payment_method = 'cod'
    order.complete = True
    order.save()
    messages.success(request, 'Order placed with Cash on Delivery!')
    return redirect('store')

@login_required
def clear_orders(request):
    if request.method == 'POST':
        customer, _ = Customer.objects.get_or_create(user=request.user)
        Order.objects.filter(customer=customer, complete=True).delete()
        messages.success(request, 'All your completed orders have been cleared!')
    return redirect('profile')

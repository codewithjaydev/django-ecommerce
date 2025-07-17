import json
import requests
import hmac
import hashlib
import base64  # for decoding Base64 callback data
from urllib.parse import parse_qs, unquote  # to handle URL‑encoded callback strings

from django.shortcuts import render, redirect, get_object_or_404
from django.views.decorators.csrf import csrf_exempt
from django.http import HttpResponse, JsonResponse
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.conf import settings
from django import forms
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from django.contrib.auth import login, authenticate, logout
from django.utils import timezone
from django.contrib.admin.views.decorators import staff_member_required

from .models import Customer, Order, OrderItem, Product
from .esewa_utils import ESewaPayment

@csrf_exempt
def esewa_ipn(request):
    oid = amt = refId = status = None

    if request.method == 'POST':
        try:
            payload = json.loads(request.body)
            data = json.loads(base64.b64decode(payload.get('data', '')).decode())
        except Exception:
            return HttpResponse(status=400)

        oid = data.get('pid') or data.get('transaction_uuid')
        amt = data.get('total_amount')
        refId = data.get('refId')
        status = data.get('status')

    elif request.method == 'GET':
        raw = request.GET.get('data')
        if raw:
            try:
                data = json.loads(base64.b64decode(raw).decode())
                oid = data.get('pid')
                amt = data.get('total_amount')
                refId = data.get('refId')
                status = data.get('status')
            except Exception:
                pass

    if not all([oid, amt, refId, status]):
        return HttpResponse("Missing params", status=400)

    esewa = ESewaPayment()
    verified, msg = esewa.verify_payment(oid, amt, refId)
    order = get_object_or_404(Order, transaction_id=oid)

    if verified and status.upper() == 'COMPLETE':
        order.complete = True
        order.ref_id = refId
        order.payment_status = 'completed'
    else:
        order.payment_status = 'failed'
        order.payment_error = msg or 'Invalid status'
    order.save()

    return HttpResponse("OK" if order.payment_status == 'completed' else "FAILED")

# ---------- Custom User Form ----------

class CustomUserCreationForm(UserCreationForm):
    email = forms.EmailField(required=True, label='Email')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Reorder fields: username, email, password1, password2
        field_order = ['username', 'email', 'password1', 'password2']
        self.order_fields(field_order)
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

    def save(self, commit=True):
        user = super().save(commit=False)
        user.email = self.cleaned_data['email']
        if commit:
            user.save()
            # Also update Customer email if Customer exists or is created
            from .models import Customer
            customer, _ = Customer.objects.get_or_create(user=user)
            customer.email = user.email
            customer.save()
        return user

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

        # Instead of redirecting, render a template with the payment form
        return render(request, 'store/esewa_payment_form.html', {
            'payment_data': payment_data,
            'esewa_url': esewa.ESEWA_URL
        })

    except Exception as e:
        messages.error(request, f'Error initiating payment: {e}')
        return redirect('checkout')

def payment_success(request):
    """
    Handle eSewa payment success callback.
    Removed @login_required decorator to handle callbacks properly.
    """
    # Check if user is authenticated
    if not request.user.is_authenticated:
        messages.error(request, 'Please log in to complete payment verification.')
        return redirect('login')
    
    # Handle new eSewa callback format with encoded data
    data_param = request.GET.get('data')
    if data_param:
        try:
            import base64
            import json
            
            # Try base64 decode first
            try:
                decoded_data = base64.b64decode(data_param).decode('utf-8')
                
                # Try to parse as JSON
                try:
                    payment_data = json.loads(decoded_data)
                    
                    # Extract parameters from JSON
                    oid = payment_data.get('transaction_code') or payment_data.get('oid') or payment_data.get('pid')
                    amt = payment_data.get('amount') or payment_data.get('amt') or payment_data.get('total_amount')
                    refId = (
                        payment_data.get('reference_id')
                        or payment_data.get('refId')
                        or payment_data.get('rid')
                        or payment_data.get('transaction_code')
                        or payment_data.get('transaction_uuid')
                    )
                except json.JSONDecodeError:
                    # If not JSON, try to parse as URL-encoded string
                    from urllib.parse import parse_qs, unquote
                    decoded_url = unquote(decoded_data)
                    
                    # Parse as query string
                    parsed_params = parse_qs(decoded_url)
                    
                    oid = parsed_params.get('transaction_code', [None])[0] or parsed_params.get('oid', [None])[0]
                    amt = parsed_params.get('amount', [None])[0] or parsed_params.get('amt', [None])[0]
                    refId = (
                        parsed_params.get('reference_id', [None])[0]
                        or parsed_params.get('refId', [None])[0]
                        or parsed_params.get('rid', [None])[0]
                        or parsed_params.get('transaction_code', [None])[0]
                        or parsed_params.get('transaction_uuid', [None])[0]
                    )
            except Exception as e:
                # Try direct JSON parsing
                try:
                    payment_data = json.loads(data_param)
                    
                    oid = payment_data.get('transaction_code') or payment_data.get('oid') or payment_data.get('pid')
                    amt = payment_data.get('amount') or payment_data.get('amt') or payment_data.get('total_amount')
                    refId = (
                        payment_data.get('reference_id')
                        or payment_data.get('refId')
                        or payment_data.get('rid')
                        or payment_data.get('transaction_code')
                        or payment_data.get('transaction_uuid')
                    )
                except json.JSONDecodeError:
                    oid = amt = refId = None
        except Exception as e:
            oid = amt = refId = None
    else:
        # Fallback to original parameter extraction for backward compatibility
        oid = request.GET.get('oid') or request.GET.get('pid') or request.GET.get('transaction_uuid')
        amt = request.GET.get('amt') or request.GET.get('amount') or request.GET.get('total_amount')
        refId = request.GET.get('refId') or request.GET.get('rid') or request.GET.get('reference_id')
    
    if not all([oid, amt, refId]):
        missing_params = []
        if not oid:
            missing_params.append('oid/pid/transaction_uuid/transaction_code')
        if not amt:
            missing_params.append('amt/amount/total_amount')
        if not refId:
            missing_params.append('refId/rid/reference_id')
        
        error_msg = f'Invalid payment callback. Missing parameters: {", ".join(missing_params)}. Received parameters: {dict(request.GET)}'
        messages.error(request, error_msg)
        return redirect('checkout')

    customer, _ = Customer.objects.get_or_create(user=request.user)
    
    # Try to find the order with more flexible matching
    order = None
    try:
        # First try exact match
        order = get_object_or_404(Order, customer=customer, transaction_id=oid, complete=False)
    except:
        # If not found, try to find any incomplete order for this customer
        order = Order.objects.filter(customer=customer, complete=False).first()
        if order:
            print(f"Order found but transaction_id mismatch. Expected: {oid}, Found: {order.transaction_id}")
    
    if not order:
        error_msg = f'No matching order found for transaction_id: {oid}'
        messages.error(request, error_msg)
        return redirect('checkout')
    
    esewa = ESewaPayment()
    verified, msg = esewa.verify_payment(oid, amt, refId)
    
    if not verified and getattr(settings, 'ESEWA_ENV', 'RC') == 'RC' and '404' in str(msg):
        order.transaction_id = oid  # Set to eSewa transaction_code
        order.complete = True
        order.save()
        return render(request, 'registration/payment_successfull.html', {'test_mode': True})

    if verified:
        try:
            callback_amount = float(amt)
            order_amount = float(order.get_cart_total)
            if abs(callback_amount - order_amount) > 1.0:
                error_msg = f'Payment amount mismatch. Expected: {order_amount}, Received: {callback_amount}'
                messages.error(request, error_msg)
                return redirect('checkout')
        except (ValueError, TypeError) as e:
            error_msg = f'Amount comparison error: {e}'
            messages.error(request, error_msg)
            return redirect('checkout')

        # Only update transaction_id and mark complete once
        order.transaction_id = oid  # Set to eSewa transaction_code
        order.complete = True
        order.save()
        messages.success(request, 'Payment successful!')
        return redirect('store')
    else:
        error_msg = f'Verification failed: {msg}'
        messages.error(request, error_msg)
    
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

@login_required
def debug_payment_callback(request):
    """Debug endpoint to log all callback parameters"""
    print("=== PAYMENT CALLBACK DEBUG ===")
    print(f"Method: {request.method}")
    print(f"URL: {request.get_full_path()}")
    print(f"GET parameters: {dict(request.GET)}")
    print(f"POST parameters: {dict(request.POST)}")
    print(f"Headers: {dict(request.headers)}")
    
    # Handle encoded data parameter
    data_param = request.GET.get('data')
    if data_param:
        print(f"\n=== ENCODED DATA ANALYSIS ===")
        print(f"Raw data parameter: {data_param}")
        
        try:
            import base64
            import json
            
            # Try base64 decode
            try:
                decoded_data = base64.b64decode(data_param).decode('utf-8')
                print(f"Base64 decoded: {decoded_data}")
                
                # Try JSON parsing
                try:
                    payment_data = json.loads(decoded_data)
                    print(f"JSON parsed: {json.dumps(payment_data, indent=2)}")
                except json.JSONDecodeError:
                    print("Not valid JSON")
                    
                    # Try URL decoding
                    from urllib.parse import parse_qs, unquote
                    decoded_url = unquote(decoded_data)
                    print(f"URL decoded: {decoded_url}")
                    
                    parsed_params = parse_qs(decoded_url)
                    print(f"URL parameters: {parsed_params}")
                    
            except Exception as e:
                print(f"Base64 decode error: {e}")
                
                # Try direct JSON
                try:
                    payment_data = json.loads(data_param)
                    print(f"Direct JSON: {json.dumps(payment_data, indent=2)}")
                except json.JSONDecodeError:
                    print("Not valid JSON either")
                    
        except Exception as e:
            print(f"Error analyzing data: {e}")
    
    print("=== END DEBUG ===")
    
    # Return a simple response for testing
    return JsonResponse({
        'status': 'debug_received',
        'get_params': dict(request.GET),
        'post_params': dict(request.POST),
        'data_analysis': {
            'has_data_param': bool(data_param),
            'data_length': len(data_param) if data_param else 0
        }
    })

@staff_member_required
def mark_order_delivered(request, order_id):
    order = get_object_or_404(Order, id=order_id)
    order.payment_status = 'delivered'
    order.save()
    messages.success(request, 'Order has been delivered you will receive order soon.')
    return redirect('adminpanel_orders')

def product_detail(request, product_id):
    product = get_object_or_404(Product, id=product_id)
    cartItems = 0
    if request.user.is_authenticated:
        customer, _ = Customer.objects.get_or_create(user=request.user)
        order, _ = Order.objects.get_or_create(customer=customer, complete=False)
        cartItems = order.get_cart_items if hasattr(order, 'get_cart_items') else 0
    return render(request, 'store/product_detail.html', {'product': product, 'cartItems': cartItems})
from django.shortcuts import render, redirect
from django.http import JsonResponse
import json
import datetime
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from django.contrib.auth import login, authenticate, logout
from django.contrib import messages
from django import forms
from django.contrib.auth.models import User
from .models import *
# Create your views here.
class CustomUserCreationForm(UserCreationForm):
    """Custom user creation form with minimal password validation"""
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Remove all password validators
        self.fields['password1'].validators = []
        self.fields['password2'].validators = []
        
        # Clear help text
        self.fields['username'].help_text = ''
        self.fields['password1'].help_text = ''
        self.fields['password2'].help_text = ''
        
        # Update labels
        self.fields['password1'].label = 'Password'
        self.fields['password2'].label = 'Confirm Password'
    
    def clean_password1(self):
        password1 = self.cleaned_data.get('password1')
        if not password1:
            raise forms.ValidationError('Password cannot be blank.')
        return password1
    
    def clean_password2(self):
        password1 = self.cleaned_data.get('password1')
        password2 = self.cleaned_data.get('password2')
        if password1 and password2 and password1 != password2:
            raise forms.ValidationError('Passwords do not match.')
        return password2



def auth_view(request):
    login_form = AuthenticationForm()
    register_form = CustomUserCreationForm()
    
    if request.method == 'POST':
        if 'login' in request.POST:
            login_form = AuthenticationForm(request, data=request.POST)
            if login_form.is_valid():
                username = login_form.cleaned_data.get('username')
                password = login_form.cleaned_data.get('password')
                user = authenticate(username=username, password=password)
                if user is not None:
                    login(request, user)
                    return redirect('store')
                else:
                    messages.error(request, 'Invalid username or password.')
        
        elif 'register' in request.POST:
            register_form = CustomUserCreationForm(request.POST)
            if register_form.is_valid():
                try:
                    user = register_form.save()
                    # Ensure customer is created
                    from .models import Customer
                    Customer.objects.get_or_create(user=user)
                    login(request, user)
                    messages.success(request, 'User registered successfully!')
                    return redirect('store')
                except Exception as e:
                    print("Error creating user:", e)
                    messages.error(request, 'Error creating account. Please try again.')
            else:
                print("Registration form errors:", register_form.errors)
    
    context = {
        'login_form': login_form,
        'register_form': register_form,
    }
    return render(request, 'registration/login.html', context)

def register(request):
    if request.method == 'POST':
        form = CustomUserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            # Ensure customer is created
            from .models import Customer
            Customer.objects.get_or_create(user=user)
            login(request, user)  # Log the user in after successful registration
            messages.success(request, 'User registered successfully!')
            return redirect('store')  # Redirect to the store page
        else:
            # If registration fails, redirect to login page with error
            return redirect('login')
    else:
        form = CustomUserCreationForm()
    return render(request, 'store/register.html', {'form': form})

def store(request):
    if request.user.is_authenticated:
        # Ensure customer exists
        from .models import Customer
        customer, created = Customer.objects.get_or_create(user=request.user)
        order, created = Order.objects.get_or_create(customer=customer,complete=False)
        items=order.orderitem_set.all()
        cartItems = order.get_cart_items
    else:
        items=[]
        order={'get_cart_total':0, 'get_cart_items':0,'shipping':False}
        cartItems=order['get_cart_items']

    products=Product.objects.all()
    context={'products':products, 'cartItems':cartItems}
    return render(request, 'store/store.html',context)

@login_required
def cart(request):
    # Ensure customer exists
    from .models import Customer
    customer, created = Customer.objects.get_or_create(user=request.user)
    order, created = Order.objects.get_or_create(customer=customer,complete=False)
    items=order.orderitem_set.all()
    cartItems = order.get_cart_items

    context={'items':items, 'order':order,'cartItems':cartItems}
    return render(request, 'store/cart.html',context)

@login_required
def checkout(request):
    # Ensure customer exists
    from .models import Customer
    customer, created = Customer.objects.get_or_create(user=request.user)
    order, created = Order.objects.get_or_create(customer=customer,complete=False)
    items=order.orderitem_set.all()
    cartItems = order.get_cart_items

    context={'items':items, 'order':order,'cartItems':cartItems}
    return render(request, 'store/checkout.html', context)


@login_required
def updateItem(request):
    data= json.loads(request.body)
    productId= data['productId']
    action=data['action']

    print('productId:',productId)
    print('Action:', action)

    # Ensure customer exists
    from .models import Customer
    customer, created = Customer.objects.get_or_create(user=request.user)
    product= Product.objects.get(id=productId)
    order, created = Order.objects.get_or_create(customer=customer,complete=False)
    orderItem, created = OrderItem.objects.get_or_create(order=order, product=product)

    if action=='add':
        orderItem.quantity=(orderItem.quantity + 1)
    elif action== 'remove':
        orderItem.quantity =(orderItem.quantity - 1)    
    

    orderItem.save()
    if orderItem.quantity <=0:
        orderItem.delete()
    return JsonResponse('Item was added', safe=False)
@login_required
def profile(request):
    return render(request, 'store/user/profile.html')

def logout_view(request):
    logout(request)
    messages.success(request, 'You have been successfully logged out.')
    return redirect('store')

def test_registration(request):
    """Test view to debug registration issues"""
    if request.method == 'POST':
        print("Test registration POST data:", request.POST)
        # Try with regular UserCreationForm first
        form = UserCreationForm(request.POST)
        print("Regular form is valid:", form.is_valid())
        if form.is_valid():
            print("Regular form is valid, saving user...")
            user = form.save()
            print("User saved:", user.username)
            return JsonResponse({'success': True, 'username': user.username})
        else:
            print("Regular form errors:", form.errors)
            # Try with custom form
            custom_form = CustomUserCreationForm(request.POST)
            print("Custom form is valid:", custom_form.is_valid())
            if custom_form.is_valid():
                print("Custom form is valid, saving user...")
                user = custom_form.save()
                print("User saved:", user.username)
                return JsonResponse({'success': True, 'username': user.username})
            else:
                print("Custom form errors:", custom_form.errors)
                return JsonResponse({'success': False, 'errors': custom_form.errors})
    else:
        form = CustomUserCreationForm()
        return render(request, 'test_registration.html', {'form': form})

# eSewa Payment Views
@login_required
def initiate_payment(request):
    """Initiate eSewa payment"""
    try:
        # Get customer and order
        from .models import Customer
        customer, created = Customer.objects.get_or_create(user=request.user)
        order, created = Order.objects.get_or_create(customer=customer, complete=False)
        
        if order.get_cart_items == 0:
            messages.error(request, 'Your cart is empty.')
            return redirect('cart')
        

        
        # Initialize eSewa payment
        from .esewa_utils import ESewaPayment
        esewa = ESewaPayment()
        
        # Generate payment data
        payment_data, transaction_id = esewa.generate_payment_data(order, request)
        
        # Update order with transaction ID
        order.transaction_id = transaction_id
        order.payment_method = 'esewa'
        order.save()
        
        # Get payment URL
        payment_url = esewa.get_payment_url(payment_data)
        
        # Check if eSewa service is available (basic check)
        try:
            import requests
            response = requests.get('https://esewa.com.np', timeout=5)
            if response.status_code != 200:
                messages.warning(request, 'eSewa service may be temporarily unavailable. Please try again later.')
        except:
            messages.warning(request, 'eSewa service is currently unavailable. Please try again later.')
        
        return redirect(payment_url)
        
    except Exception as e:
        messages.error(request, f'Error initiating payment: {str(e)}')
        return redirect('checkout')



@login_required
def payment_success(request):
    """Handle successful payment"""
    try:
        # Get parameters from eSewa
        oid = request.GET.get('oid')  # Order ID (transaction ID)
        amt = request.GET.get('amt')  # Amount
        refId = request.GET.get('refId')  # Reference ID from eSewa
        
        if not all([oid, amt, refId]):
            messages.error(request, 'Invalid payment response from eSewa.')
            return redirect('checkout')
        
        # Get order
        from .models import Customer
        customer, created = Customer.objects.get_or_create(user=request.user)
        order = Order.objects.filter(customer=customer, transaction_id=oid, complete=False).first()
        
        if not order:
            messages.error(request, 'Order not found.')
            return redirect('checkout')
        
        # Verify payment with eSewa
        from .esewa_utils import ESewaPayment
        esewa = ESewaPayment()
        
        is_verified, message = esewa.verify_payment(oid, amt, refId)
        
        if is_verified:
            # Process successful payment
            success, msg = esewa.process_successful_payment(order, refId, oid)
            if success:
                messages.success(request, 'Payment successful! Your order has been placed.')
                return redirect('store')
            else:
                messages.error(request, f'Error processing payment: {msg}')
                return redirect('checkout')
        else:
            messages.error(request, f'Payment verification failed: {message}')
            return redirect('checkout')
            
    except Exception as e:
        messages.error(request, f'Error processing payment success: {str(e)}')
        return redirect('checkout')

@login_required
def payment_failure(request):
    """Handle failed payment"""
    try:
        # Get parameters from eSewa
        oid = request.GET.get('oid')  # Order ID (transaction ID)
        amt = request.GET.get('amt')  # Amount
        
        if oid:
            # Get order
            from .models import Customer
            customer, created = Customer.objects.get_or_create(user=request.user)
            order = Order.objects.filter(customer=customer, transaction_id=oid, complete=False).first()
            
            if order:
                # Process failed payment
                from .esewa_utils import ESewaPayment
                esewa = ESewaPayment()
                esewa.process_failed_payment(order, 'Payment failed by user')
        
        messages.error(request, 'Payment was cancelled or failed. Please try again.')
        return redirect('checkout')
        
    except Exception as e:
        messages.error(request, f'Error processing payment failure: {str(e)}')
        return redirect('checkout')

@login_required
def payment_cancel(request):
    """Handle cancelled payment"""
    messages.warning(request, 'Payment was cancelled. You can try again.')
    return redirect('checkout')

@login_required
def payment_status(request):
    """Show payment status page"""
    status = request.GET.get('status', 'unknown')
    error_message = request.GET.get('error', '')
    
    # Get order if available
    order = None
    if request.user.is_authenticated:
        from .models import Customer
        customer, created = Customer.objects.get_or_create(user=request.user)
        order = Order.objects.filter(customer=customer, complete=False).first()
    
    context = {
        'status': status,
        'error_message': error_message,
        'order': order,
    }
    return render(request, 'store/payment_status.html', context)

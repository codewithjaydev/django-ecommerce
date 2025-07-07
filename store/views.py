from django.shortcuts import render
from django.http import JsonResponse
import json
import datetime
from django.contrib.auth.decorators import login_required
from .models import *
# Create your views here.

def register(request):
    if request.method == 'POST':
        form = UserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)  # Log the user in after successful registration
            return redirect('home')  # Redirect to the home page or any other page
    else:
        form = UserCreationForm()
    return render(request, 'register.html', {'form': form})

def store(request):
    if request.user.is_authenticated:
        customer = request.user.customer
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

def cart(request):
    if request.user.is_authenticated:
        customer = request.user.customer
        order, created = Order.objects.get_or_create(customer=customer,complete=False)
        items=order.orderitem_set.all()
        cartItems = order.get_cart_items
    else:
        items=[]
        order={'get_cart_total':0, 'get_cart_items':0,'shipping':False}
        cartItems = order['get_cart_items']
        

    context={'items':items, 'order':order,'cartItems':cartItems}
    return render(request, 'store/cart.html',context)

def checkout(request):
    if request.user.is_authenticated:
        customer = request.user.customer
        order, created = Order.objects.get_or_create(customer=customer,complete=False)
        items=order.orderitem_set.all()
        cartItems = order.get_cart_items
    else:
        items=[]
        order={'get_cart_total':0, 'get_cart_items':0,'shipping':False}
        cartItems = order['get_cart_items']

    context={'items':items, 'order':order,'cartItems':cartItems}
    return render(request, 'store/checkout.html', context)


def updateItem(request):
    data= json.loads(request.body)
    productId= data['productId']
    action=data['action']

    print('productId:',productId)
    print('Action:', action)

    customer= request.user.customer
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

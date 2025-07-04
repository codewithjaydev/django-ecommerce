from django.db import models
from django.contrib.auth.models import User
from django.db.models.signals import post_save
from django.dispatch import receiver

# Create your models here.
class Customer(models.Model):
    user=models.OneToOneField(User, on_delete=models.CASCADE,null=True,blank=True)

    name=models.CharField(max_length=100, null=True)
    email=models.CharField(max_length=100,null=True)
    def __str__(self):
        return self.name
    
class Product(models.Model):
    name= models.CharField(max_length=100, null=True)
    price = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    digital=models.BooleanField(default=False, null=True, blank=False)
    image=models.ImageField(null=True,blank=True)
    def __str__(self):
        return self.name
    
    @property
    def imageURL(self):
        try:
            url= self.image.url
        except:
            url=''
        return url
    
class Order(models.Model):
    customer=models.ForeignKey(Customer,on_delete=models.SET_NULL,blank=True,null=True)
    date_orderd=models.DateTimeField(auto_now_add=True)
    complete=models.BooleanField(default=False,null=True,blank=False)
    transaction_id= models.CharField(max_length=100, null=True)

    def __str__(self):
        return str(self.id)
    
    @property
    def get_cart_total(self):
        orderitems = self.orderitem_set.all()
        total= sum([item.get_total for item in orderitems])
        return total
    @property
    def get_cart_items(self):
         orderitems = self.orderitem_set.all()
         total = len(orderitems)  # or orderitems.count()
         return total

    
class OrderItem(models.Model):
    product=models.ForeignKey(Product,on_delete=models.SET_NULL,blank=True,null=True)
    order=models.ForeignKey(Order,on_delete=models.SET_NULL,blank=True,null=True)
    quantity=models.IntegerField(default=0,null=True,blank=True)
    date_added=models.DateTimeField(auto_now_add=True)

    @property
    def get_total(self):
        total= self.product.price *self.quantity
        return total
    
class ShippingAddress(models.Model):
    customer=models.ForeignKey(Customer,on_delete=models.SET_NULL,blank=True,null=True)
    order=models.ForeignKey(Order,on_delete=models.SET_NULL,blank=True,null=True)
    city=models.CharField(max_length=100, null=True)
    state=models.CharField(max_length=100, null=True)
    zipcode=models.CharField(max_length=100, null=True)
    date_added=models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.city

# Signal to create Customer when a new User is created
@receiver(post_save, sender=User)
def create_customer(sender, instance, created, **kwargs):
    if created:
        Customer.objects.create(user=instance)
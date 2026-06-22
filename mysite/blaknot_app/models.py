from django.contrib.auth.models import AbstractUser
from django.db import models
from django.db.models import PositiveSmallIntegerField
from phonenumber_field.modelfields import PhoneNumberField
from django.core.validators import MinValueValidator

STATUS_CHOICE = (
    ('active','active'),
    ('completed', 'completed'),
    ('cancelled', 'cancelled')
)
LEVEL_CHOICE=(
    ('easy','easy'),
    ('medium','medium'),
    ('high','high'),
    ('critical','critical')
)

class User(AbstractUser):
    phone_number=PhoneNumberField(region='KG',default='996')
    age=PositiveSmallIntegerField(validators=[MinValueValidator(10)],default=10)
    profile_image=models.ImageField(upload_to='profile_image',null=True,blank=True)

    def __str__(self):
        return self.username
class Deal(models.Model):
    owner=models.ForeignKey(User,on_delete=models.CASCADE)
    title_deal=models.CharField(max_length=100)
    description=models.TextField()
    status=models.CharField(max_length=10,choices=STATUS_CHOICE,default='active')
    created_at=models.DateField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    cash=models.PositiveIntegerField(default=0)

    def __str__(self):
        return self.title_deal

class Tasks(models.Model):
    owner=models.ForeignKey(User,on_delete=models.CASCADE)
    deal=models.ForeignKey(Deal,on_delete=models.CASCADE)
    title_task=models.CharField(max_length=100)
    description=models.TextField()
    created_at=models.DateField(auto_now_add=True)
    deadline = models.DateField(null=True, blank=True)
    status=models.BooleanField(default=False)
    level=models.CharField(max_length=8,choices=LEVEL_CHOICE,default='easy')

    def __str__(self):
        return self.title_task

class Note(models.Model):
    deal=models.ForeignKey(Deal,on_delete=models.CASCADE,related_name='note')
    title_note=models.CharField(max_length=100)
    description=models.TextField(null=True,blank=True)
    date_note=models.DateField(auto_now_add=True)

    def __str__(self):
        return self.title_note




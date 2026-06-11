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


class User(AbstractUser):
    phone_number=PhoneNumberField(region='KG',default='996')
    age=PositiveSmallIntegerField(validators=[MinValueValidator(10)],default=10)
    profile_image=models.ImageField(upload_to='profile_image',null=True,blank=True)

    def __str__(self):
        return self.username

class Category(models.Model):
    title_category=models.CharField(max_length=100)
    def __str__(self):
        return self.title_category


class Goals(models.Model):
    user=models.ForeignKey(User,on_delete=models.CASCADE)
    category=models.ForeignKey(Category,on_delete=models.CASCADE)
    title_goals=models.CharField(max_length=100)
    description=models.TextField()
    status=models.CharField(max_length=10,choices=STATUS_CHOICE,default='active')
    now_date = models.DateField(auto_now_add=True)
    goals_date = models.DateField()

    def __str__(self):
        return f'{self.category}:{self.title_goals}'

class Tasks(models.Model):
    goals=models.ForeignKey(Goals,on_delete=models.CASCADE)
    title_task=models.CharField(max_length=100)
    description=models.TextField()

    def __str__(self):
        return self.title_task

class Note(models.Model):
    goals=models.ForeignKey(Goals,on_delete=models.CASCADE,related_name='note')
    title_note=models.CharField(max_length=100)
    description=models.TextField(null=True,blank=True)
    date_note=models.DateField(auto_now_add=True)

    def __str__(self):
        return self.title_note

class Habits(models.Model):
    category=models.ForeignKey(Category,on_delete=models.CASCADE)
    user=models.ForeignKey(User,on_delete=models.CASCADE)
    title_habit=models.CharField(max_length=100)
    STATUS_CHOICE_HABIT=(
    ('done','done'),
    ('not done','not done')
    )
    status=models.CharField(max_length=8,null=True,blank=True,choices=STATUS_CHOICE_HABIT,default='not done')

    def __str__(self):
        return self.title_habit




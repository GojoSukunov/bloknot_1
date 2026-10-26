import uuid
from pathlib import Path

from django.contrib.auth.models import AbstractUser
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from phonenumber_field.modelfields import PhoneNumberField

STATUS_CHOICE = (
    ("active", "active"),
    ("completed", "completed"),
    ("cancelled", "cancelled"),
)
LEVEL_CHOICE = (
    ("easy", "easy"),
    ("medium", "medium"),
    ("high", "high"),
    ("critical", "critical"),
)


def profile_image_path(instance, filename):
    """Имя файла — случайный UUID: исключает подмену путей и коллизии, расширение берём из белого списка."""
    ext = Path(filename).suffix.lower()
    if ext not in (".jpg", ".jpeg", ".png", ".webp"):
        ext = ".jpg"
    return f"profile_image/{uuid.uuid4().hex}{ext}"


class User(AbstractUser):
    email = models.EmailField("email address", unique=True)
    phone_number = PhoneNumberField(region="KG", blank=True, default="")
    age = models.PositiveSmallIntegerField(
        validators=[MinValueValidator(10), MaxValueValidator(120)], default=10
    )
    profile_image = models.ImageField(upload_to=profile_image_path, null=True, blank=True)

    def __str__(self):
        return self.username


class Deal(models.Model):
    owner = models.ForeignKey(User, on_delete=models.CASCADE)
    title_deal = models.CharField(max_length=100)
    description = models.TextField(blank=True, default="")
    status = models.CharField(max_length=10, choices=STATUS_CHOICE, default="active")
    created_at = models.DateField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    cash = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["-updated_at", "-id"]
        indexes = [models.Index(fields=["owner", "status"])]

    def __str__(self):
        return self.title_deal


class Tasks(models.Model):
    owner = models.ForeignKey(User, on_delete=models.CASCADE)
    deal = models.ForeignKey(Deal, on_delete=models.CASCADE)
    title_task = models.CharField(max_length=100)
    description = models.TextField(blank=True, default="")
    created_at = models.DateField(auto_now_add=True)
    deadline = models.DateField(null=True, blank=True)
    status = models.BooleanField(default=False)
    level = models.CharField(max_length=8, choices=LEVEL_CHOICE, default="easy")

    class Meta:
        ordering = ["status", "deadline", "-id"]
        indexes = [models.Index(fields=["owner", "status"])]

    def __str__(self):
        return self.title_task


class Note(models.Model):
    deal = models.ForeignKey(Deal, on_delete=models.CASCADE, related_name="note")
    title_note = models.CharField(max_length=100)
    description = models.TextField(null=True, blank=True)
    date_note = models.DateField(auto_now_add=True)

    class Meta:
        ordering = ["-date_note", "-id"]

    def __str__(self):
        return self.title_note

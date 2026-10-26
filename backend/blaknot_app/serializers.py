from django.conf import settings
from django.contrib.auth.password_validation import validate_password
from rest_framework import serializers

from .models import Deal, Note, Tasks, User

ALLOWED_IMAGE_FORMATS = {"JPEG", "PNG", "WEBP"}


class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, trim_whitespace=False, max_length=128)

    class Meta:
        model = User
        fields = ["username", "email", "password", "first_name", "last_name", "age", "phone_number"]

    def validate_email(self, value):
        value = value.strip().lower()
        if User.objects.filter(email__iexact=value).exists():
            raise serializers.ValidationError("Пользователь с таким email уже существует.")
        return value

    def validate(self, attrs):
        # Проверка пароля настроенными валидаторами (длина, частые пароли, схожесть с логином)
        candidate = User(username=attrs.get("username", ""), email=attrs.get("email", ""),
                         first_name=attrs.get("first_name", ""), last_name=attrs.get("last_name", ""))
        try:
            validate_password(attrs["password"], candidate)
        except Exception as exc:
            raise serializers.ValidationError({"password": list(getattr(exc, "messages", [str(exc)]))})
        return attrs

    def create(self, validated_data):
        return User.objects.create_user(**validated_data)


class LoginSerializer(serializers.Serializer):
    username = serializers.CharField(max_length=150)
    password = serializers.CharField(max_length=128, trim_whitespace=False)


class UserProfileSerializer(serializers.ModelSerializer):
    """Профиль текущего пользователя. Привилегии, пароль и служебные поля через API недоступны."""

    class Meta:
        model = User
        fields = ["id", "username", "email", "first_name", "last_name", "phone_number",
                  "age", "profile_image", "date_joined"]
        read_only_fields = ["id", "date_joined"]

    def validate_email(self, value):
        value = value.strip().lower()
        qs = User.objects.filter(email__iexact=value)
        if self.instance:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise serializers.ValidationError("Пользователь с таким email уже существует.")
        return value

    def validate_profile_image(self, value):
        if value is None:
            return value
        if value.size > settings.PROFILE_IMAGE_MAX_BYTES:
            raise serializers.ValidationError("Файл слишком большой (максимум 2 МБ).")
        image = getattr(value, "image", None)
        if image is not None and image.format not in ALLOWED_IMAGE_FORMATS:
            raise serializers.ValidationError("Допустимые форматы: JPEG, PNG, WEBP.")
        return value


class ChangePasswordSerializer(serializers.Serializer):
    old_password = serializers.CharField(max_length=128, trim_whitespace=False)
    new_password = serializers.CharField(max_length=128, trim_whitespace=False)

    def validate_old_password(self, value):
        if not self.context["request"].user.check_password(value):
            raise serializers.ValidationError("Неверный текущий пароль.")
        return value

    def validate_new_password(self, value):
        try:
            validate_password(value, self.context["request"].user)
        except Exception as exc:
            raise serializers.ValidationError(list(getattr(exc, "messages", [str(exc)])))
        return value


class UserSimpleSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ["username"]


class NoteSerializer(serializers.ModelSerializer):
    description = serializers.CharField(required=False, allow_blank=True, allow_null=True, max_length=5000)

    class Meta:
        model = Note
        fields = ["id", "deal", "title_note", "description", "date_note"]
        read_only_fields = ["id", "date_note"]

    def validate_deal(self, deal):
        # Работает и при создании, и при обновлении: нельзя привязать заметку к чужому делу
        if deal.owner_id != self.context["request"].user.pk:
            raise serializers.ValidationError("Нельзя добавлять заметки в чужое дело.")
        return deal


class DealSerializer(serializers.ModelSerializer):
    owner = UserSimpleSerializer(read_only=True)
    note_detail = NoteSerializer(source="note", many=True, read_only=True)
    description = serializers.CharField(required=False, allow_blank=True, max_length=5000)
    cash = serializers.IntegerField(required=False, min_value=0, max_value=2_000_000_000)

    class Meta:
        model = Deal
        fields = ["id", "owner", "title_deal", "description", "status", "cash",
                  "created_at", "updated_at", "note_detail"]
        read_only_fields = ["id", "owner", "created_at", "updated_at"]


class TasksSerializer(serializers.ModelSerializer):
    deal_title = serializers.CharField(source="deal.title_deal", read_only=True)
    description = serializers.CharField(required=False, allow_blank=True, max_length=5000)

    class Meta:
        model = Tasks
        fields = ["id", "deal", "deal_title", "status", "title_task", "created_at",
                  "owner", "description", "level", "deadline"]
        read_only_fields = ["id", "owner", "created_at"]

    def validate_deal(self, deal):
        if deal.owner_id != self.context["request"].user.pk:
            raise serializers.ValidationError("Нельзя добавлять задачи в чужое дело.")
        return deal

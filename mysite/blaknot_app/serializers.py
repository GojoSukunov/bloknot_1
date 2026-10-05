from .models import User,Deal,Tasks,Note
from rest_framework import serializers
from rest_framework_simplejwt.tokens import RefreshToken
from django.contrib.auth import authenticate

class RegisterSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['username', 'email', 'password', 'first_name', 'last_name', 'age',
                  'phone_number']
        extra_kwargs = {'password': {'write_only': True}}

    def create(self, validated_data):
        user = User.objects.create_user(**validated_data)
        return user


class LoginSerializer(serializers.Serializer):
    username = serializers.CharField()
    password = serializers.CharField(write_only=True)

    def validate(self, data):
        user = authenticate(**data)
        if user and user.is_active:
            return user
        raise serializers.ValidationError("Неверные учетные данные")

    def to_representation(self, instance):
        refresh = RefreshToken.for_user(instance)
        return {
            'user': {
                'username': instance.username,
                'email': instance.email,
            },
            'access': str(refresh.access_token),
            'refresh': str(refresh),
        }

class UserProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model=User
        fields='__all__'

class UserSimpleSerializer(serializers.ModelSerializer):
    class Meta:
        model=User
        fields=['username']

class NoteSerializer(serializers.ModelSerializer):
    class Meta:
        model = Note
        fields = ['id', 'deal', 'title_note', 'description', 'date_note']


class DealListSerializer(serializers.ModelSerializer):
    class Meta:
        model=Deal
        fields=['id','title_deal','status','created_at']



class DealDetailSerializer(serializers.ModelSerializer):
    owner=UserSimpleSerializer(read_only=True)
    note_detail=NoteSerializer(source='note',many=True,read_only=True)
    class Meta:
        model=Deal
        fields=['id','owner', 'title_deal',
                'description','status','cash','created_at','updated_at','note_detail']
        read_only_fields = ['owner']




class TasksSerializer(serializers.ModelSerializer):
    deal_detail = DealDetailSerializer(source='deal', read_only=True)

    class Meta:
        model = Tasks
        fields = ['id', 'deal', 'status', 'title_task', 'created_at',
                  'owner', 'description', 'deal_detail', 'level']


from .models import User,Deal,Tasks,Note
from rest_framework import serializers

class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model=User
        fields='__all__'

class UserSimpleSerializer(serializers.ModelSerializer):
    class Meta:
        model=User
        fields=['username']

class NoteSerializer(serializers.ModelSerializer):
    class Meta:
        model=Note
        fields=['id','title_note','description','date_note']

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
    deal_detail=DealDetailSerializer(read_only=True)
    class Meta:
        model=Tasks
        fields=['id','status','title_task','created_at','owner','description','deal_detail','level']


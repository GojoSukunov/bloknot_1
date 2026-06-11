from .models import User,Goals,Category,Tasks,Note,Habits
from rest_framework import serializers

class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model=User
        fields='__all__'

class UserSimpleSerializer(serializers.ModelSerializer):
    class Meta:
        model=User
        fields=['username']


class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model=Category
        fields='__all__'

class GoalsSimpleSerializer(serializers.ModelSerializer):
    user=UserSimpleSerializer(read_only=True)
    category_detail=CategorySerializer(source='category',read_only=True)
    class Meta:
        model=Goals
        fields=['id','user','category', 'category_detail','title_goals','status']
        read_only_fields=['user']

class NoteSerializer(serializers.ModelSerializer):
    class Meta:
        model=Note
        fields=['id','title_note','description','date_note']

class GoalsListSerializer(serializers.ModelSerializer):
    class Meta:
        model=Goals
        fields=['id','title_goals','status','now_date']



class GoalsDetailSerializer(serializers.ModelSerializer):
    user=UserSimpleSerializer(read_only=True)
    category_detail=CategorySerializer(source='category',read_only=True)
    note_detail=NoteSerializer(source='note',many=True,read_only=True)
    class Meta:
        model=Goals
        fields=['id','user','category','category_detail','title_goals',
                'description','status','now_date','goals_date','note_detail']
        read_only_fields = ['user']




class TasksSerializer(serializers.ModelSerializer):
    goals_detail=GoalsSimpleSerializer(read_only=True)
    class Meta:
        model=Tasks
        fields=['id','title_task','description','goals_detail']


class HabitsSerializer(serializers.ModelSerializer):
    user=UserSimpleSerializer(read_only=True)
    category_detail=CategorySerializer(source='category',read_only=True)
    class Meta:
        model=Habits
        fields=['id','title_habit','status','category','category_detail','user']
        read_only_fields = ['user']

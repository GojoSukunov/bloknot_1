from django_filters.rest_framework import FilterSet
from .models import Goals


class GoalsFilter(FilterSet):
    class Meta:
        model=Goals
        fields={
            'category':['exact']
        }
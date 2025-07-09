from rest_framework import serializers
from .models import TrafficData

class TrafficDataSerializer(serializers.ModelSerializer):
    class Meta:
        model = TrafficData
        fields = ['user_id', 'data', 'timestamp']
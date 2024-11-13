from rest_framework import serializers
from app.models.feedback import Feedback
from django.conf import settings


class FeedbackSerializer(serializers.ModelSerializer):
    class Meta:
        model = Feedback
        fields = ['id', 'rating', 'user', 'comment']
        read_only_fields = ['id', 'user']

    def validate(self, data):
        data['user'] = self.context['request'].user
        return super().validate(data)

    def create(self, validated_data):
        return Feedback.objects.create(**validated_data)

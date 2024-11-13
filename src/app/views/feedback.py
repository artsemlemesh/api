from rest_framework import viewsets, permissions
from app.models.feedback import Feedback
from app.serializers.feedback import FeedbackSerializer


class FeedbackViewSet(viewsets.ModelViewSet):
    queryset = Feedback.objects.all()
    serializer_class = FeedbackSerializer
    permission_classes = [permissions.IsAuthenticated]

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

    def get_queryset(self):
        return Feedback.objects.filter(user=self.request.user)

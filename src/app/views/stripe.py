from django.db.models import ObjectDoesNotExist
from django.views.generic import TemplateView
from rest_framework import status
from rest_framework.views import APIView
from rest_framework.viewsets import ModelViewSet
from rest_framework.generics import GenericAPIView
from rest_framework.mixins import (
    UpdateModelMixin, RetrieveModelMixin,
    CreateModelMixin, DestroyModelMixin
)
from rest_framework.response import Response
from app.permissions import IsAuthenticated
from app.serializers.stripe import ByndeAccountCreateSearializer


class TestViewSet(ModelViewSet):
    def get_serializer(self, **kwargs):
        return super().get_serializer(**kwargs)


class ByndeStripeAccountUpdateAPIView(
    CreateModelMixin, DestroyModelMixin, GenericAPIView
):
    permission_classes = (IsAuthenticated, )
    serializer_class = ByndeAccountCreateSearializer

    def get_object(self):
        return self.request.user.account

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.save()
        headers = self.get_success_headers(serializer.data)
        return Response(data.to_dict(), status=status.HTTP_201_CREATED, headers=headers)

    def post(self, request, *args, **kwargs):
        try:
            account = self.get_object()
            if account:
                serializer = self.serializer_class(instance=account)
                return Response(data=serializer.data, status=status.HTTP_200_OK)
            else:
                return self.create(request, *args, **kwargs)
        except ObjectDoesNotExist:
            return self.create(request, *args, **kwargs)

    def delete(self, request, *args, **kwargs):
        try:
            instance = self.get_object()
        except ObjectDoesNotExist:
            return Response(status=status.HTTP_404_NOT_FOUND)

        if instance is None:
            return Response(
                status=status.HTTP_404_NOT_FOUND)
        else:
            return super().destroy(request, *args, **kwargs)


class StripeRefreshView(TemplateView):
    template_name = 'stripe/refresh.html'


class StripeReturnView(TemplateView):
    template_name = 'stripe/return.html'

# -*- coding: utf-8 -*-
from rest_framework import serializers
from shop.models.customer import CustomerModel
from .utils import get_subscription_fields


# These serializers are for debugging only via the DRF browsable api and are not required for the form operations
class SubscribeSerializer(serializers.ModelSerializer):
    """Allows email address submissions"""
    email = serializers.EmailField()
    class Meta:
        model = CustomerModel
        fields = ('email',)


def ConfirmSerializer_factory():
    """Dynamically generate fields list"""

    subscription_fields = get_subscription_fields()

    class ConfirmSerializer(serializers.ModelSerializer):
        email = serializers.EmailField()
        sig = serializers.CharField(min_length=20)

        class Meta:
            model = CustomerModel
            fields = ['email', 'sig'] + subscription_fields

    return ConfirmSerializer

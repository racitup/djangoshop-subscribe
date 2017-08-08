# -*- coding: utf-8 -*-
from django.utils.translation import ugettext_lazy as _
from shop.admin.customer import CustomerInlineAdminBase
from .utils import get_subscription_fields


class SubscriptionsInlineAdmin(CustomerInlineAdminBase):
    """Add to CustomerInline for our fields and to take advantage of JS inline move to top"""
    fieldsets = list(CustomerInlineAdminBase.fieldsets) + [
        (_("Subscriptions"),        {'fields': get_subscription_fields()})
    ]

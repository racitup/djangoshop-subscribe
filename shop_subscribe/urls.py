# -*- coding: utf-8 -*-
from django.conf.urls import url
from .views import SubscribeView, ConfirmView


app_name = 'shop_subscribe'
urlpatterns = [
    url(r'^subscribe/$', SubscribeView.as_view(), name='subscribe'),
    url(r'^confirm/$', ConfirmView.as_view(), name='confirm'),
]

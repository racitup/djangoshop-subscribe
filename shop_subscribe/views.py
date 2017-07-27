# -*- coding: utf-8 -*-
from rest_framework.renderers import TemplateHTMLRenderer
from rest_framework import generics, status
from rest_framework.response import Response
from .forms import SubscribeForm, ConfirmForm_factory
from .serializers import SubscribeSerializer, ConfirmSerializer_factory


class SubscribeView(generics.CreateAPIView):
    """Only allows posts to create new customers or add the email address"""
    # for debugging via the DRF browsable api
    serializer_class = SubscribeSerializer

    def create(self, request):
        customer_form = SubscribeForm(data=request.data, request=request)

        if customer_form.is_valid():
            # if valid, customer_form will assign the email address to the customer
            # and an email will be sent
            customer_form.save()
            return Response(request.data, status=status.HTTP_201_CREATED) 
        else:
            return Response({'errors': customer_form.errors}, status=status.HTTP_400_BAD_REQUEST)


class ConfirmView(generics.UpdateAPIView):
    """
    PUT and PATCH methods for submitting new subscriptions
    Retrieve API not necessary as form will be rendered with params
    from the url
    Also supports GET to render a default form.
    """
    # for debugging via the DRF browsable api
    serializer_class = ConfirmSerializer_factory()
    renderer_classes = [TemplateHTMLRenderer] + generics.UpdateAPIView.renderer_classes
    template_name = "shop_subscribe/default-confirm-form.html"
    form_class = ConfirmForm_factory()

    def get(self, request):
        """For the default HTML confirm form template"""
        form = self.form_class(request=request)
        # fix to allow browsable api and template renderer
        if request.query_params.get('format', None) in ['json', 'api']:
            # form.initial contains the model data overridden by any initial data passed in
            context = form.initial
        else:
            # we assume 'html'
            context = {
                'form': form,
                'action': 'DO_NOTHING'
            }
        return Response(context)

    def update(self, request, *args, **kwargs):
        """PUT and PATCH go here"""
        customer_form = self.form_class(data=request.data, request=request)

        if customer_form.is_valid():
            customer_form.save()
            return Response(request.data) 
        else:
            return Response({'errors': customer_form.errors}, status=status.HTTP_400_BAD_REQUEST)

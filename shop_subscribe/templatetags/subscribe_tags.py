# -*- coding: utf-8 -*-
from django import template
from ..forms import SubscribeForm, ConfirmForm_factory

register = template.Library()

@register.simple_tag(takes_context=True)
def subscribe_form(context):
    "Get an empty subscription form. Added form context variable is only valid within the block scope."
    context['form'] = SubscribeForm(request=context['request'])
    context['action'] = 'DO_NOTHING'
    return ''

@register.simple_tag(takes_context=True)
def confirm_form(context):
    "Get an empty confirmation form. Added form context variable is only valid within the block scope."
    context['form'] = ConfirmForm_factory()(request=context['request'])
    context['action'] = 'DO_NOTHING'
    return ''

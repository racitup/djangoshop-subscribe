# -*- coding: utf-8 -*-
from django import template

register = template.Library()

@register.simple_tag(takes_context=True)
def subscribe_form(context):
    "Get an empty subscription form. Added form context variable is only valid within the block scope."
    from ..forms import SubscribeForm
    context['form'] = SubscribeForm(request=context['request'])
    context['action'] = 'DO_NOTHING'
    return ''

@register.simple_tag(takes_context=True)
def confirm_form(context):
    "Get an empty confirmation form. Added form context variable is only valid within the block scope."
    from ..forms import ConfirmForm_factory
    context['form'] = ConfirmForm_factory()(request=context['request'])
    context['action'] = 'DO_NOTHING'
    return ''

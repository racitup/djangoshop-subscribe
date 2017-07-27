# -*- coding: utf-8 -*-
from django.utils.translation import ugettext_lazy as _
from django.utils.html import format_html
from django.template.loader import select_template
from django.forms.fields import ChoiceField
from cms.plugin_pool import plugin_pool
from cmsplugin_cascade.link.forms import LinkForm
from shop import app_settings
from shop.cascade.plugin_base import DialogFormPluginBase, ShopLinkPluginBase, ShopLinkElementMixin
from shop.cascade.checkout import CustomerFormPluginBase
from .forms import SubscribeForm, ConfirmForm_factory


class CustomerFormMinimalPlugin(CustomerFormPluginBase):
    """A modified copy of CustomerFormPlugin"""
    name = _("Customer Form (minimal)")
    form_class = 'shop_subscribe.forms.CustomerFormMinimal'
    def render(self, context, instance, placeholder):
        if not context['request'].customer.is_registered():
            context['error_message'] = _("Only registered customers can access this form.")
            return context
        return super(CustomerFormMinimalPlugin, self).render(context, instance, placeholder)

DialogFormPluginBase.register_plugin(CustomerFormMinimalPlugin)


SUBSCRIPTION_FORM_TYPES = (
    ('subscribe', _("Subscribe Form"), SubscribeForm),
    ('confirm', _("Email Confirmation Form"), ConfirmForm_factory()),
)

class SubscriptionsAdminForm(LinkForm):
    LINK_TYPE_CHOICES = (('DO_NOTHING', _("Do Nothing")), ('RELOAD_PAGE', _("Reload Page")), ('cmspage', _("CMS Page")))
    form_type = ChoiceField(label=_("Rendered Form"), choices=(ft[:2] for ft in SUBSCRIPTION_FORM_TYPES),
        help_text=_("Select the required form."))

    def clean(self):
        cleaned_data = super(SubscriptionsAdminForm, self).clean()
        if self.is_valid():
            cleaned_data['glossary'].update(form_type=cleaned_data['form_type'])
        return cleaned_data

class SubscriptionsFormPlugin(ShopLinkPluginBase):
    """
    Cannot use the DialogFormPlugin framework since the form requires a cart which may not exist
    Use the shop GuestForm plugin for the checkout process
    """
    name = _("Subscriptions Form")
    require_parent = True
    parent_classes = ('BootstrapColumnPlugin', 'BootstrapPanelPlugin', 'SegmentPlugin', 'SimpleWrapperPlugin')
    model_mixins = (ShopLinkElementMixin,)
    cache = False
    form = SubscriptionsAdminForm
    fields = ('form_type', ('link_type', 'cms_page'), 'glossary',)

    @classmethod
    def get_identifier(cls, instance):
        identifier = super(SubscriptionsFormPlugin, cls).get_identifier(instance)
        content = dict(ft[:2] for ft in SUBSCRIPTION_FORM_TYPES).get(instance.glossary.get('form_type'), _("unknown"))
        return format_html('{0}{1}', identifier, content)

    def get_render_template(self, context, instance, placeholder):
        form_type = instance.glossary.get('form_type')
        template_names = [
            '{}/shop_subscribe/{}-form.html'.format(app_settings.APP_LABEL, form_type),
            'shop_subscribe/{}-form.html'.format(form_type),
        ]
        return select_template(template_names)

    def render(self, context, instance, placeholder):
        """
        Return the context to render the template
        """
        form_type = instance.glossary.get('form_type')
        form_class = dict( ((ft[0], ft[2]) for ft in SUBSCRIPTION_FORM_TYPES) ).get(form_type, None)
        context['form'] = form_class(request=context['request'])
        context['action'] = self.get_link(instance)
        return super(SubscriptionsFormPlugin, self).render(context, instance, placeholder)

plugin_pool.register_plugin(SubscriptionsFormPlugin)

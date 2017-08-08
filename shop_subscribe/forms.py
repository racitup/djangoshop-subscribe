# -*- coding: utf-8 -*-
from django.forms import fields, widgets, ValidationError
from django.urls import reverse
from django.core.signing import BadSignature
from django.utils.translation import ugettext_lazy as _
from djng.forms import NgModelFormMixin, NgFormValidationMixin
from djng.forms.angular_base import SafeTuple
from djng.styling.bootstrap3.forms import Bootstrap3ModelForm
from shop.forms.checkout import CustomerForm
from shop.models.customer import CustomerModel
from .utils import send_confirmation_email, logger, unsign, get_customer_from_emailsignature, get_subscription_fields


class CustomerFormMinimal(CustomerForm):
    """For use instead of the shop CustomerForm Plugin in checkout without the other customer fields like subscriptions"""
    form_name = 'customer_form'  # Override form name to reuse template `customer-form.html`
    class Meta:
        model = CustomerModel
        custom_fields = ('email', 'first_name', 'last_name')
        fields = ('plugin_id', 'plugin_order', 'email', 'first_name', 'last_name')


def debug_instance(instance):
    """Helper debug function"""
    print("Registration form instance: '{}', ".format(instance), end='')
    if instance:
        try:
            if instance.is_visitor():
                print('Visiting Customer')
            elif instance.is_authenticated():
                print('Registered Customer')
            elif instance.is_guest():
                print('Guest Customer')
            elif instance.is_anonymous():
                print('Unrecognized Customer')
            else:
                print('Unknown Concrete Customer')
        except AttributeError:
            print('User')
    else:
        print('None')


class NgSuccessMessageMixin(object):
    success_message = _("Form submitted successfully")
    def non_field_errors(self):
        errors = super(NgSuccessMessageMixin, self).non_field_errors()
        errors.append(SafeTuple((self.form_name, self.form_error_css_classes, '$dirty', 'success', 'valid', self.success_message)))
        return errors


class SubscribeForm(NgSuccessMessageMixin, NgModelFormMixin, NgFormValidationMixin, Bootstrap3ModelForm):
    email = fields.EmailField(label=_('Subscribe to product updates'), required=True)

    form_name = 'subscribe_form'
    scope_prefix = 'subscribe_data'
    required_css_class = 'djng-field-required'
    success_message = _("Thanks for subscribing!")

    class Meta:
        model = CustomerModel
        fields = ('email',)

    @classmethod
    def get_url(cls):
        """Returns the url for the form submission"""
        return reverse('shop_subscribe:subscribe')

    def __init__(self, request=None, instance=None, *args, **kwargs):
        """
        Always called with a Customer instance, not User.
        """
        #debug_instance(request.customer)
        if request is None:
            raise ValueError("Request must not be None")
        if instance:
            raise ValueError("Pass in 'request' instead of 'instance'")

        # for save()
        self.request = request

        if request.customer.is_visitor():
            request.customer = CustomerModel.objects.get_or_create_from_request(request)
        super(SubscribeForm, self).__init__(instance=request.customer, *args, **kwargs)

    # custom
    unchecked_error = _("At least one subscription must be checked")
    def clean_subscriptions(self):
        """
        Signups must have at least one subscription checked.
        Use this in your clean function if overriding this form.
        """
        cleaned_data = super(SignupSubscriptionForm, self).clean() or self.cleaned_data
        checked = 0
        for key, value in cleaned_data.items():
            if key.startswith('subscription') and value:
                checked += 1
        if checked > 0:
            return cleaned_data
        else:
            raise ValidationError(self.unchecked_error)

    registered_error = _("The current user is already registered")
    def clean_email(self):
        """
        Reject requests for sessions with email addresses
        Do not lookup user with current email and assign to customer as it is privilege escalation
        Also don't provide ValidationError that email exists as can be used to check db contents
        """
        if getattr(self.instance, 'email', None):
            raise ValidationError(self.registered_error)
        return self.cleaned_data['email']

    def save(self, **kwargs):
        """
        Only save if email address doesn't already exist in the db
        A confirmation email address will be sent where customers can change subscriptions
        """
        if CustomerModel.objects.filter(user__email=self.cleaned_data['email']).exists():
            logger.info('Subscription from {} dropped, email address exists.'.format(self.cleaned_data['email']))
            return self.instance
        # email is not assigned by the form probably because it is a related user object field
        self.instance.email = self.cleaned_data['email']
        if send_confirmation_email(self.request, self.instance):
            self.instance = super(SubscribeForm, self).save(**kwargs)
        return self.instance


class NgLoadSuccessMessageMixin(object):
    loadsuccess_message = _("Form loaded successfully")
    def non_field_errors(self):
        errors = super(NgLoadSuccessMessageMixin, self).non_field_errors()
        errors.append(SafeTuple((self.form_name, self.form_error_css_classes, '$pristine', 'email.$modelValue', 'valid', self.loadsuccess_message)))
        return errors


def ConfirmForm_factory():
    """Dynamically generate fields list"""

    subscription_fields = get_subscription_fields()

    class ConfirmForm(NgLoadSuccessMessageMixin, NgSuccessMessageMixin, NgModelFormMixin, NgFormValidationMixin, Bootstrap3ModelForm):
        "email and sig are obtained from a url and embedded in the form data hidden for posts"
        email = fields.EmailField(required=True, widget=widgets.HiddenInput)
        sig = fields.CharField(min_length=20, required=True, widget=widgets.HiddenInput)

        form_name = 'confirm_form'
        scope_prefix = 'confirm_data'
        required_css_class = 'djng-field-required'
        success_message = _("Subscriptions updated")
        loadsuccess_message = _("Email address confirmed")

        class Meta:
            model = CustomerModel
            fields = ['email', 'sig'] + subscription_fields

        @classmethod
        def get_url(cls):
            """Returns the url for the form submission"""
            return reverse('shop_subscribe:confirm')

        def __init__(self, request=None, instance=None, *args, **kwargs):
            """
            Always called with a Customer instance, not User.
            """
            if request is None:
                raise ValueError("Request must not be None")
            if instance:
                raise ValueError("Pass in 'request' instead of 'instance'")

            try:
                customer, initial = get_customer_from_emailsignature(request)
            except BadSignature:
                # if no/bad url params are given, uses a blank form
                customer, initial = None, None

            super(ConfirmForm, self).__init__(instance=customer, initial=initial, *args, **kwargs)

        confirm_error = _("Could not confirm the supplied email address.")
        def clean(self):
            """
            Checks the email signature.
            is_valid or full_clean won't check initial values unless data has been passed in
            """
            cleaned_data = super(ConfirmForm, self).clean() or self.cleaned_data
            try:
                unsign(cleaned_data)
                return cleaned_data
            except BadSignature:
                raise ValidationError(self.confirm_error)

    return ConfirmForm

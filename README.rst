djangoshop-subscribe
====================

Django-SHOP plugin for email subscriptions

Introduction
------------

This plugin allows Django-SHOP implementations to add email
subscriptions for their customers. The plugin is currently compatible
with Django v1.10.7 and
`Django-SHOP <https://github.com/awesto/django-shop>`__ v0.10.2. This
documentation assumes a working knowledge of Django and
`Django-SHOP <http://django-shop.readthedocs.io/en/latest/>`__.

Features
~~~~~~~~

This plugin currently has the following features:

-  Django-angular & bootstrap3 based subscription and confirmation forms
   that can be included in normal templates.
-  Automatic pickup of any Customer model fields that start with
   ``subscription_`` for inclusion in forms.
-  A CMS plugin for inclusion of either form in CMS placeholders.
-  Default confirmation and subscription management form, or use your
   own page.
-  A minimal customer form for the standard Django-SHOP checkout to
   prevent all fields annoying customers on every checkout.
-  Email link authentication for management of subscriptions.
-  Overridable forms and email templates including `Email
   Framework <https://github.com/g13nn/Email-Framework>`__ compatibility
   with the majority of email clients.

TODO
~~~~

Please let us know of you have any feature suggestions, or wish to
implement any of the below:

-  Admin interface to allow emails to be authored and sent out to
   subscribed users.
-  Tests.
-  Continuous build integration including compatibility testing with
   various python, Django and Django-SHOP versions.

Integration Guide
-----------------

Please follow the guide below to integrate the plugin into your own
shop.

Configuration
~~~~~~~~~~~~~

Please add the following to your Django settings. If you do not use CMS
you do not need the CMS plugin.

.. code:: python

    INSTALLED_APPS = [
        ...
        'shop',
        'shop_subscribe',
        ...
    ]

    CMSPLUGIN_CASCADE_PLUGINS = [
        ...
        'shop_subscribe.cmsplugin_cascade',
    ]

A logging configuration similar to below is also recommended to catch a few warnings
given off by this module. This configuration will also catch messages given off by
other modules for which there is no specific configuration. If you want to add a
specific configuration for this module, use the module name ``shop_subscribe``.

.. code:: python

    LOGGING = {
        'version': 1,
        # Use False to see deprecation warnings, etc
        'disable_existing_loggers': False,
        'filters': {
             'require_debug_false': {
                 '()': 'django.utils.log.RequireDebugFalse',
             }
        },
        'formatters': {
            'simple': {
                'format': '[%(asctime)s %(name)s] %(levelname)s: %(message)s'
            },
        },
        'handlers': {
            'console': {
                'level': 'INFO',
                'class': 'logging.StreamHandler',
                'formatter': 'simple',
            },
        },
        'loggers': {
            '': {
                'handlers': ['console'],
                # default is WARNING
                'level': 'INFO',
            },
        },
    }

Customer Model
~~~~~~~~~~~~~~

For the subscription plugin to work, you must create your own customer
model that extends the provided shop customer model. There are two
requirements:

-  Add the ``SubscriptionCustomerManagerMixin`` to a manager class
-  Add your own subscription options to the customer model which MUST be
   prefixed with ``subscription_``

For example:

.. code:: python

    from shop.models.customer import BaseCustomer, CustomerManager as BaseCustomerManager
    from shop_subscribe.models import SubscriptionCustomerManagerMixin


    class CustomerManager(SubscriptionCustomerManagerMixin, BaseCustomerManager):
        pass

    class Customer(BaseCustomer):
        """
        Specialised customer class for our additional fields
        """
        subscription_newsletter = models.BooleanField(_("Newsletter"), default=True,
            help_text=_("Company news subscription"))
        subscription_cart_products = models.BooleanField(_("Watched Product Updates"), default=True,
            help_text=_("Subscription to product developments in your watch list or shopping trolley"))
        subscription_order_products = models.BooleanField(_("Purchased Product Updates"), default=False,
            help_text=_("Subscription to product developments you have purchased"))

        objects = CustomerManager()

The subscription management form will use the default Django modelform
fields and widgets. Customising this form has not been considered!

URLs
~~~~

The subscribe plugin comes with two namespaced URLs that are Django REST
Framework endpoints:

-  subscribe: Used by the subscription form to sign up with just an
   email address. Visitors will be added as 'Unrecognized'. The email
   address used will receive an email asking the user to click a link to
   confirm their subscription.
-  confirm: The confirmation link contains a signature that
   authenticates the user. The form first recognizes the user as
   'Guest'. The form then allows users to manage their subscriptions.

Please include these urls in your own urlconf, for example:

.. code:: python

    api_urls = [
        url(r'^api/', include([
            url(r'^shop/', include('shop.urls', namespace='shop')),
            url(r'^shop_subscribe/', include('shop_subscribe.urls')), # for email subscriptions
        ]))
    ]
    urlpatterns += [url(r'', include(api_urls))]

Forms
~~~~~

Two forms are provided, one for initial subscription, the other for
confirming and managing subscriptions without the need to log in. The
latter is useful for Guest users that are unable to log in.

Either form can be integrated into existing CMS placeholders using the
CMS plugin called *Subscriptions Form*, which can be found in the *Shop*
plugin section. The template rendered for either form can be overridden
by creating the following templates in your shop app:

-  /shop\_subscribe/subscribe-form.html
-  /shop\_subscribe/confirm-form.html

These templates will be rendered with ``form`` and ``action`` context
variables. Here is what the plugin should look like:

.. figure:: https://github.com/racitup/djangoshop-subscribe/raw/master/doc/img/cms-plugin.png
   :alt: CMS Plugin

   CMS plugin image

Subscription Form
^^^^^^^^^^^^^^^^^

.. figure:: https://github.com/racitup/djangoshop-subscribe/raw/master/doc/img/subscribe.png
   :alt: Subscription form

   Subscription form image

It is recommended that the subscription form is embedded into an
existing product page, for example the product detail page. This can be
acheived using the CMS plugin as above. Alternatively you may include
the form directly into a template, for example:

.. code:: html+django

        <div class="col-md-4 text-center">
            ...
            {% include "shop_subscribe/subscribe-form.html" %}
            ...
        </div>

An included template tag ensures the relevant context variables are
available for rendering.

Confirmation Form
^^^^^^^^^^^^^^^^^

.. figure:: https://github.com/racitup/djangoshop-subscribe/raw/master/doc/img/confirm.png
   :alt: Confirmation form

   Confirmation form image

The confirmation form can be on a CMS page as above, included in a
standard Django template, or as a last resort, a default form is
included that will be rendered by Django REST Framework.

Confirmation form email link URL resolution order:

1. CMS page id (aka reverse\_id): ``shop-subscribe-confirm``;
2. Django URL name: ``shop-subscribe-confirm``;
3. Default URL ``shop_subscribe:confirm`` which renders a default form.

**Note:** The confirmation page must be live when the subscription form
is live and the URL must not be changed. Otherwise the confirmation
email links sent out will not point to the correct URL.

Minimal Checkout Customer Form
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Look for the *Customer Form (minimal)* CMS plugin.
*Note* that any fields added to the Customer Model must be configured to allow blank form entries
(``blank=True`` and/or specify a default value) for correct operation.

Admin
~~~~~

To add subscriptions management to the customer admin, you must create your own customer admin
module derived from the shop base module, like so:

.. code:: python

    from django.contrib import admin
    from shop.admin.customer import CustomerProxy, CustomerAdminBase
    from shop_subscribe.admin import SubscriptionsInlineAdmin


    # Because Customer is attached to the user model, use this proxy model:
    @admin.register(CustomerProxy)
    class CustomerAdmin(CustomerAdminBase):
        """Customised customeradmin class"""
        inlines = (SubscriptionsInlineAdmin,)

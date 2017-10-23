# -*- coding: utf-8 -*-
from collections import OrderedDict
from datetime import datetime
import re, logging
from django.core.signing import Signer, BadSignature
from django.template.loader import select_template
from django.contrib.sites.shortcuts import get_current_site
from django.utils.translation import get_language_from_request
from django.utils import timezone
from django.core.urlresolvers import reverse
from django.core.exceptions import ObjectDoesNotExist
from django.urls import NoReverseMatch
from cms.cache.page import get_page_url_cache, set_page_url_cache
from cms.templatetags.cms_tags import _get_page_by_untyped_arg
#from cms.utils import get_language_from_request
from rest_framework.request import Request as DRFRequest
from ipware.ip import get_real_ip, get_ip
from shop.conf import app_settings
from shop.models.customer import CustomerModel
from post_office import mail
from post_office.models import EmailTemplate


# Get an instance of a logger
logger = logging.getLogger('shop_subscribe')

sep = ':'
signer = Signer(sep=sep, salt='subscribe')
def sign(email):
    "Returns [email, signature]"
    return signer.sign(email).split(sep, 1)

def unsign(context):
    "Returns an ordereddict of email & signature, {} otherwise"
    sigcontext = OrderedDict([
        ('email', context.get('email', '')),
        ('sig', context.get('sig', ''))
    ])
    signer.unsign(sep.join( sigcontext.values() ))
    return sigcontext


def get_subscription_fields():
    """Returns the list of customer subscription fields"""
    return [item for item in dir(CustomerModel) if item.startswith('subscription_')]


def get_customer_from_emailsignature(request):
    """
    DRF or WSGI requests
    Validate the email signature in either the GET url for initial email link or POST hidden data for form submissions.
    If the signature is valid return a 'recognized' customer object if not already.
    """
    if isinstance(request, DRFRequest):
        try:
            # e.g. GET URLs
            context = unsign(request.query_params)
        except BadSignature:
            # e.g. POST data
            context = unsign(request.data)
    else:
        try:
            context = unsign(request.GET)
        except BadSignature:
            context = unsign(request.POST)

    customer, created = CustomerModel.objects.get_or_create_from_email(request, context['email'])
    # make the customer guest if not already
    if not customer.is_recognized():
        customer.recognize_as_guest()
    # remove sensitive data since the customer has confirmed
    customer.extra.pop('subscription_IP', None)
    customer.extra.pop('subscription_date', None)
    customer.last_access = timezone.now()
    customer.save()

    if created:
        logger.warning('Customer recreated from confirmation: %s' % context['email'])

    return customer, context


def reverse_cms_url(request, page_lookup):
    """Equivalent of CMS 'page_url' templatetag"""
    site_id = get_current_site(request).id
    lang = get_language_from_request(request)

    url = get_page_url_cache(page_lookup, lang, site_id)
    if url is None:
        try:
            page = _get_page_by_untyped_arg(page_lookup, request, site_id)
        except ObjectDoesNotExist:
            page = None
        if page:
            url = page.get_absolute_url(language=lang)
            set_page_url_cache(page_lookup, lang, site_id, url)
    if url:
        return url
    raise NoReverseMatch("CMS page not found")

def build_confirm_url(request, email='', sig=''):
    """
    Build the confirm url from supplied parameters
    """
    try:
        url = reverse_cms_url(request, 'shop-subscribe-confirm')
    except NoReverseMatch:
        try:
            url = reverse('shop-subscribe-confirm')
        except NoReverseMatch:
            url = reverse('shop_subscribe:confirm')
    url = url + '?email=' + '&sig='.join( (email, sig) )
    return request.build_absolute_uri(url)

def unisoformat(datestring):
    "Bit of a hacky way to get the date back from python's isoformat string"
    return datetime(*map(int, re.findall('\d+', datestring)))


_et_name = 'Subscription confirmation - customer'
def get_emailtemplate():
    """
    Gets or creates a post_office email template
    Returns the emailtemplate instance
    """
    try:
        et = EmailTemplate.objects.get(name=_et_name, language='', default_template=None)
    except EmailTemplate.DoesNotExist:
        subject = select_template([
            '{}/shop_subscribe/email/subscription-confirm-subject.txt'.format(app_settings.APP_LABEL),
            'shop_subscribe/email/subscription-confirm-subject.txt',
        ])
        html = select_template([
            '{}/shop_subscribe/email/subscription-confirm-body.html'.format(app_settings.APP_LABEL),
            'shop_subscribe/email/subscription-confirm-body.html',
        ])
        et = EmailTemplate(
            name=_et_name,
            description='Send the customer an email with a link to confirm their subscription',
            subject=''.join(subject.origin.loader.get_contents(subject.origin).splitlines()).strip(),
            html_content=html.origin.loader.get_contents(html.origin),
        )
        et.save()
    return et

def send_confirmation_email(request, customer):
    """
    Sends direct to post_office
    Assumes customer will be saved afterward externally
    """
    # check that same IP is not making lots of subscriptions and store IP
    ip = get_ip(request)
    now = datetime.now()
    for c in CustomerModel.objects.exclude(extra__exact='{}').all():
        try:
            if (c.extra['subscription_IP'] == ip and
                (now - unisoformat(c.extra['subscription_date'])).days < 1):
                logger.warning('Subscription from {} dropped. Same IP ({}) subscribed recently.'.format(customer.email, ip))
                return False
        except KeyError:
            continue

    context = {
        'site_name': get_current_site(request).name,
        'confirm_url': build_confirm_url(request, *sign(customer.email)),
        'email': customer.email,
        # requires django-ipware; only returns public IPs
        'ip': get_real_ip(request),
        'user_agent': request.META['HTTP_USER_AGENT'],
        'language': get_language_from_request(request, check_path=True)
    }

    mail.send(
        customer.email,
        template=get_emailtemplate(),
        context=context,
        render_on_delivery=True,
    )

    customer.extra.update({
        'subscription_IP': ip,
        'subscription_date': now.isoformat(),
    })
    return True

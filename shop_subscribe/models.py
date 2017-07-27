# -*- coding: utf-8 -*-
from django.contrib.auth import get_user_model
from django.core.exceptions import MultipleObjectsReturned
from shop.models.customer import CustomerModel


class SubscriptionCustomerManagerMixin(object):
    """
    Add method for subscriptions to lookup the customer by email address
    """
    def get_or_create_from_email(self, request, email):
        customers = self.filter(user__email=email)
        created = False
        try:
            customer = customers.get()
        except MultipleObjectsReturned:
            # find the best option and delete the others
            customers = customers.order_by('-recognized', '-last_access', '-pk')
            customer = customers[:1].get()
            for c in customers[1:]:
                c.delete()
        except CustomerModel.DoesNotExist:
            # make sure the user does not exist
            users = get_user_model().objects.filter(email=email)
            try:
                user = users.get()
            except MultipleObjectsReturned:
                # find the best option and delete the others
                users = users.order_by('-is_superuser', '-is_staff', '-is_active', '-last_login', '-date_joined', '-pk')
                user = users[:1].get()
                for u in users[1:]:
                    u.delete()
            except get_user_model().DoesNotExist:
                # our db has somehow lost the customer and their cart
                # or this is a new user with a cart
                if (not request.customer.is_visitor() and
                    request.customer.email in (email, '', None)):
                    # customer and user is in the db
                    request.customer.email = email
                    request.customer.save()
                    return request.customer, created
                else:
                    # create a fresh user like get_or_create_from_request()
                    request.session.cycle_key()
                    assert request.session.session_key
                    username = self.encode_session_key(request.session.session_key)
                    user = get_user_model().objects.create_user(username)
                    user.is_active = False
                    user.email = email
                    user.save()
            customer, created = self.get_or_create(user=user)
        return customer, created

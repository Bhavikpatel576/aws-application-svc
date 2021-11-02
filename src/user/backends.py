"""
User app backends.
"""
from django.conf import settings
from django.contrib.auth import get_user_model

from cas.utils import cas_response_callbacks
from cas.backends import (_verify_cas1, CASBackend as OriginalCASBackend)
from cas.backends import (logging, minidom, ElementTree, urlencode, urlopen, urljoin)

from rest_framework.exceptions import ValidationError


logger = logging.getLogger(__name__)

User = get_user_model()

try:
    _verify = {
        '1': _verify_cas1,
        '2': lambda ticket, service: _internal_verify_cas(ticket, service, 'proxyValidate'),
        '3': lambda ticket, service: _internal_verify_cas(ticket, service, 'p3/proxyValidate')
    }[settings.CAS_VERSION]
except KeyError as ke:
    logger.error(f"Invalid CAS version", extra=dict(
        type="invalid_cas_version",
        version=settings.CAS_VERSION if hasattr(settings, "CAS_VERSION") else "Missing"
    ))


def _internal_verify_cas(ticket, service, suffix):                       # pylint: disable=too-many-locals
    """Verifies CAS 2.0 and 3.0 XML-based authentication ticket.

    Returns username on success and None on failure.
    """
    params = {'ticket': ticket, 'service': service}
    url = (urljoin(settings.CAS_SERVER_URL, suffix) + '?' + urlencode(params))
    page = urlopen(url)
    user_data = {}
    try:
        response = page.read()
        tree = ElementTree.fromstring(response)
        document = minidom.parseString(response)
        if tree[0].tag.endswith('authenticationSuccess'):
            if settings.CAS_RESPONSE_CALLBACKS:
                cas_response_callbacks(tree)
            for tr in tree[0].iter():
                attr = tr.tag.split('}')[-1]
                if attr in ['email', 'first_name', 'last_name', 'is_staff', 'is_superuser', 'is_active']:
                    user_data[attr] = tr.text or ''
                elif attr == 'id':
                    user_data['username'] = tr.text
        else:
            failure = document.getElementsByTagName(
                'cas:authenticationFailure')
            code = failure[0].getAttribute('code')
            if code == 'INVALID_TICKET':
                user_data = {'ticket': 'INVALID_TICKET'}
            elif code == 'INVALID_SERVICE':
                user_data = {'service': 'INVALID_SERVICE'}
            if failure:
                logger.warning('Authentication failed from CAS server: %s', failure[0].firstChild.nodeValue)
    except Exception as e:
        logger.error('Failed to verify CAS authentication: %s', e)
    finally:
        page.close()
    return user_data


class CASBackend(OriginalCASBackend):

    def authenticate(self, request, ticket, service):
        """
        Verifies CAS ticket and gets or creates User object
        NB: Use of PT to identify proxy
        """
        User = get_user_model()
        service = service.split('?')[0]
        if service.endswith('/'):
            service = service[:-1]
        user_data = _verify(ticket, service)
        if 'email' in user_data:
            try:
                user = User.objects.get(email__iexact=user_data['email'])
                fields_to_update = []
                for attr, value in user_data.items():
                    if value and getattr(user, attr) != value:
                        setattr(user, attr, value)
                        fields_to_update.append(attr)
                if fields_to_update:
                    user.save(update_fields=fields_to_update)
            except User.DoesNotExist:
                # user will have an "unusable" password
                if settings.CAS_AUTO_CREATE_USER:
                    user = User.objects.create_user(**user_data)
                    user.save()
                else:
                    user = None
            except Exception as e:
                print('Exception :', e)
        elif user_data:
            raise ValidationError(user_data)
        else:
            user = None
        return user

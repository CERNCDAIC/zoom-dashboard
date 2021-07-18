from __future__ import absolute_import, unicode_literals
import time

import jwt
import contextlib
from urllib.parse import quote
from requests import Session
from requests.exceptions import HTTPError
from pytz import utc

@contextlib.contextmanager
def ignored(*exceptions):
    """Simple context manager to ignore expected Exceptions
    :param *exceptions: The exceptions to safely ignore
    """
    try:
        yield
    except exceptions:
        pass

def is_str_type(val):
    """Check whether the input is of a string type.
    We use this method to ensure python 2-3 capatibility.
    :param val: The value to check wither it is a string
    :return: In python2 it will return ``True`` if :attr:`val` is either an
             instance of str or unicode. In python3 it will return ``True`` if
             it is an instance of str
    """
    return isinstance(val, str)

def format_iso_dt(d):
    """Convertdatetime objects to a UTC-based string.
    :param d: The :class:`datetime.datetime` to convert to a string
    :returns: The string representation of the date
    """
    return d.astimezone(utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _handle_response(resp, expected_code=200, expects_json=True):
    resp.raise_for_status()
    if resp.status_code != expected_code:
        raise HTTPError("Unexpected status code {}".format(resp.status_code), response=resp)
    if expects_json:
        return resp.json()
    else:
        return resp


class APIException(Exception):
    pass


class BaseComponent(object):
    def __init__(self, base_uri, config, timeout):
        self.base_uri = base_uri
        self.config = config
        self.timeout = timeout

    @property
    def token(self):
        header = {"alg": "HS256", "typ": "JWT"}
        payload = {"iss": self.config['api_key'], "exp": int(time.time() + 3600)}
        token = jwt.encode(payload, self.config['api_secret'], algorithm="HS256", headers=header)
        return token.decode("utf-8")

    @property
    def session(self):
        session = Session()
        session.headers = {
            'Content-Type': 'application/json',
            'Authorization': 'Bearer {}'.format(self.token)
        }
        return session

def _require_keys(d, keys, allow_none=True):
    """Require that the object have the given keys
    :param d: The dict the check
    :param keys: The keys to check :attr:`obj` for. This can either be a single
                 string, or an iterable of strings
    :param allow_none: Whether ``None`` values are allowed
    :raises:
        :ValueError: If any of the keys are missing from the obj
    """
    if is_str_type(keys):
        keys = [keys]
    for k in keys:
        if k not in d:
            raise ValueError("'{}' must be set".format(k))
        if not allow_none and d[k] is None:
            raise ValueError("'{}' cannot be None".format(k))
    return True

def _encode_uuid(val):
    """Encode UUID as described by ZOOM API documentation
    > Note: Please double encode your UUID when using this API if the UUID
    > begins with a '/'or contains ‘//’ in it.
    :param val: The UUID to encode
    :returns: The encoded UUID
    """
    if val[0] == "/" or "//" in val:
        val = quote(quote(val, safe=""), safe="")
    return val

class MetricsComponent(BaseComponent):
    def list_meetings(self, **kwargs):
        return self.session.get("{}/metrics/meetings".format(self.base_uri), params=kwargs,)

    def get_meeting(self, **kwargs):
        _require_keys(kwargs, "meeting_id")
        kwargs["meeting_id"] = _encode_uuid(kwargs.get("meeting_id"))
        return self.session.get(
            "{}/metrics/meetings/{}".format(self.base_uri, kwargs.get("meeting_id")), params=kwargs
        )

    def list_participants_meeting(self, **kwargs):
        _require_keys(kwargs, "meeting_id")
        meeting_id = _encode_uuid(kwargs.get("meeting_id"))
        kwargs.pop('meeting_id', None)
        return self.session.get(
            "{}/metrics/meetings/{}/participants".format(self.base_uri, meeting_id),
            params=kwargs,
        )
    
    def list_webinars(self, **kwargs):
        return self.session.get("{}/metrics/webinars".format(self.base_uri), params=kwargs,)

    def get_webinar(self, **kwargs):
        _require_keys(kwargs, "webinarId")
        kwargs["webinarId"] = _encode_uuid(kwargs.get("webinarId"))
        return self.session.get(
            "{}/metrics/webinars/{}".format(self.base_uri, kwargs.get("webinarId")), params=kwargs
        )    

    def list_participants_webinar(self, **kwargs):
        _require_keys(kwargs, "webinarId")
        webinarId = _encode_uuid(kwargs.get("webinarId"))
        kwargs.pop('webinarId', None)
        return self.session.get(
            "{}/metrics/webinars/{}/participants".format(self.base_uri, webinarId),
            params=kwargs,
        )

class MeetingComponent(BaseComponent):
    def add_registrant_meeting(self, meeting_id, **kwargs):
        _require_keys(kwargs, "email")
        _require_keys(kwargs, "first_name")
        _require_keys(kwargs, "last_name")
        return self.session.post(
            "{}/meetings/{}/registrants".format(self.base_uri, _encode_uuid(meeting_id)),
            json=kwargs
        )        
    def list_registrants_meeting(self, **kwargs):
        _require_keys(kwargs, "meeting_id")
        kwargs["meeting_id"] = _encode_uuid(kwargs.get("meeting_id"))
        return self.session.get(
            "{}/meetings/{}/registrants".format(self.base_uri, kwargs.get("meeting_id")),
            params=kwargs,
        )  

class WebinarComponent(BaseComponent):
    def get_webinar_details(self, **kwargs):
        _require_keys(kwargs, "webinarid")
        return self.session.get(
            "{}/webinars/{}".format(self.base_uri, kwargs.get("webinarid")),
            params=kwargs,
        )  

class UserComponent(BaseComponent):
    def get(self, **kwargs):
        _require_keys(kwargs, "id")
        return self.session.get(
            "{}/users/{}/settings".format(self.base_uri, kwargs.get("id")),
            params=kwargs,
        )  
    def get_settings(self, **kwargs):
        _require_keys(kwargs, "id")
        return self.session.get(
            "{}/users/{}/settings".format(self.base_uri, kwargs.pop("id")),
            params=kwargs,
        )  
    def update_settings(self, **kwargs):
        _require_keys(kwargs, "id")
        return self.session.patch(
            "{}/users/{}/settings".format(self.base_uri, kwargs.pop("id")),
            json=kwargs,
        ) 
    def get_webinars(self, **kwargs):
        _require_keys(kwargs, "id")
        return self.session.get(
            "{}/users/{}/webinars".format(self.base_uri, kwargs.pop("id")),
            json=kwargs,
        )


class ZoomClient(object):
    """Zoom REST API Python Client."""

    _components = {
        'metrics': MetricsComponent,
        'meeting': MeetingComponent,
        'user': UserComponent,
        'webinar': WebinarComponent,
    }

    def __init__(self, api_key, api_secret, base_url, timeout=15):
        """Create a new Zoom client.
        :param api_key: the Zoom JWT API key
        :param api_secret: the Zoom JWT API Secret
        :param timeout: the time out to use for API requests
        """
        BASE_URI = base_url

        # Setup the config details
        config = {
            "api_key": api_key,
            "api_secret": api_secret
        }

        # Instantiate the components

        self.components = {
            key: component(base_uri=BASE_URI, config=config, timeout=timeout)
            for key, component in self._components.items()
        }

    @property
    def metrics(self):
        """Get the metrics component."""
        return self.components.get("metrics")

    @property
    def meeting(self):
        """Get the meeting component."""
        return self.components.get("meeting")

    @property
    def user(self):
        """Get the user component."""
        return self.components.get("user")
    
    @property
    def webinar(self):
        """Get the webinar component."""
        return self.components.get("webinar")

class ZoomAPIClient(object):
    def __init__(self, api_client, api_key, base_url):
        self.client = ZoomClient(
            api_client,
            api_key,
            base_url
        )

    def list_meetings(self, **kwargs):
        return _handle_response(self.client.metrics.list_meetings(**kwargs), 200)
    
    def list_webinars(self, **kwargs):
        return _handle_response(self.client.metrics.list_webinars(**kwargs), 200)

    def get_meeting(self, meeting_id):
        data = {
            "meeting_id": meeting_id
        }
        return _handle_response(self.client.metrics.get_meeting(data), 200)

    def list_participants_meeting(self, **kwargs):
        return _handle_response(self.client.metrics.list_participants_meeting(**kwargs), 200)

    def list_participants_webinar(self, **kwargs):
        return _handle_response(self.client.metrics.list_participants_webinar(**kwargs), 200)


    def list_registrants_meeting(self, **kwargs):
        return _handle_response(self.client.meeting.list_registrants_meeting(**kwargs), 200)

    def add_registrant_meeting(self, meeting_id, **kwargs):
        return _handle_response(self.client.meeting.add_registrant_meeting(meeting_id, **kwargs), 201)    
    
    def set_webinar_addon(self,  **kwargs):
        return _handle_response(self.client.user.update_settings(**kwargs), 204, expects_json=False)

    def list_user_webinars(self,  **kwargs):
        return _handle_response(self.client.user.get_webinars(**kwargs), 200, expects_json=True)

    def get_webinar_details(self, **kwargs):
        return _handle_response(self.client.webinar.get_webinar_details(**kwargs), 200, expects_json=True)



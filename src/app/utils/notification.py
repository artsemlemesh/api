from exponent_server_sdk import (
    DeviceNotRegisteredError,
    PushClient,
    PushMessage,
)
from requests.exceptions import ConnectionError, HTTPError


def send_push_message(token, message, extra=None):
    try:
        msg = PushMessage(to=token,
                    body=message,
                    data=extra)
        response = PushClient().publish(msg)
    except Exception as exc:
        print ("Invalid token!", exc)
    except (ConnectionError, HTTPError) as exc:
        print ("ConnectionError!", exc)

    try:
        response.validate_response()
    except DeviceNotRegisteredError as exc:
        print("Device not registered", exc)
    except Exception as exc:
        print ("Response not validate", exc)
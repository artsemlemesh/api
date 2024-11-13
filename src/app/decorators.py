from rest_framework.response import Response
from rest_framework.status import HTTP_403_FORBIDDEN


def stripe_required(func):
    """

    """
    def wrapper(*args, **kwargs):
        user = args[1].user
        if user.is_stripe_connected:
            return func(*args, **kwargs)
        else:
            return Response({
                'detail': 'You must first connect your stripe account. Please check payment settings'
            }, status=HTTP_403_FORBIDDEN)

    return wrapper

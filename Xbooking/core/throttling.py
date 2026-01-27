"""
Throttling classes for rate limiting
"""

from rest_framework.throttling import AnonRateThrottle, UserRateThrottle


class AnonSustainedThrottle(AnonRateThrottle):
    """
    Sustained throttle for anonymous users
    """
    scope = 'anon_sustained'
    rate = '100/hour'


class AnonBurstThrottle(AnonRateThrottle):
    """
    Burst throttle for anonymous users
    """
    scope = 'anon_burst'
    rate = '30/minute'


class UserSustainedThrottle(UserRateThrottle):
    """
    Sustained throttle for authenticated users
    """
    scope = 'user_sustained'
    rate = '1000/hour'


class UserBurstThrottle(UserRateThrottle):
    """
    Burst throttle for authenticated users
    """
    scope = 'user_burst'
    rate = '100/minute'

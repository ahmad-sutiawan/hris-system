"""Rate limits tuned for punch spike (per-user, not global)."""

from rest_framework.throttling import UserRateThrottle


class PunchRateThrottle(UserRateThrottle):
    """Allow high aggregate throughput while blocking double-tap / abuse per user."""

    scope = "punch"

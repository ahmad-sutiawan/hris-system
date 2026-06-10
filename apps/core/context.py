import threading

_state = threading.local()


def set_audit_context(*, user=None, ip_address=None, user_agent=""):
    _state.user = user
    _state.ip_address = ip_address
    _state.user_agent = user_agent or ""


def get_audit_context():
    return {
        "user": getattr(_state, "user", None),
        "ip_address": getattr(_state, "ip_address", None),
        "user_agent": getattr(_state, "user_agent", ""),
    }


def clear_audit_context():
    for attr in ("user", "ip_address", "user_agent"):
        if hasattr(_state, attr):
            delattr(_state, attr)

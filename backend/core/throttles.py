from rest_framework.throttling import SimpleRateThrottle


class ScopedIdentityThrottle(SimpleRateThrottle):
    """Rate limit by client IP plus a normalized request field when available."""

    request_field = ""

    def get_cache_key(self, request, view):
        parts = [self.get_ident(request)]
        value = request.data.get(self.request_field) if hasattr(request, "data") else ""
        if isinstance(value, str) and value.strip():
            parts.append(value.strip().lower())
        return self.cache_format % {
            "scope": self.scope,
            "ident": ":".join(parts),
        }


class AuthRateThrottle(ScopedIdentityThrottle):
    scope = "auth"
    request_field = "identifier"


class SignupRateThrottle(ScopedIdentityThrottle):
    scope = "signup"
    request_field = "email"


class ContactRateThrottle(ScopedIdentityThrottle):
    scope = "contact"
    request_field = "email"


class FormulationSubmitRateThrottle(SimpleRateThrottle):
    scope = "formulation_submit"

    def get_cache_key(self, request, view):
        if request.user and request.user.is_authenticated:
            ident = f"user:{request.user.pk}"
        else:
            ident = f"ip:{self.get_ident(request)}"
        return self.cache_format % {"scope": self.scope, "ident": ident}

"""Validate host-provided conversation identifiers."""


def session_key(value):
    # This value comes only from host-injected kwargs, never model tool arguments.
    if not isinstance(value, str) or not 1 <= len(value) <= 256:
        return None
    if any(ord(char) < 32 or ord(char) == 127 for char in value):
        return None
    return value

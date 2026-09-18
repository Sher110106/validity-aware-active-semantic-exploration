"""Credential loading from an operator-provisioned, permission-restricted file."""
from __future__ import annotations
import os
from .errors import CredentialError


def load_credential(path: str) -> str:
    if not isinstance(path, str) or not path or "\x00" in path:
        raise CredentialError("credential configuration is invalid")
    try:
        st = os.stat(path)
        if os.path.islink(path) or not os.path.isfile(path) or (st.st_mode & 0o077):
            raise CredentialError("credential file permissions are invalid")
        with open(path, "r", encoding="utf-8") as handle:
            value = handle.read().strip()
    except CredentialError:
        raise
    except (OSError, UnicodeError):
        raise CredentialError("credential file is unavailable")
    if not value or "\n" in value or "\r" in value:
        raise CredentialError("credential file contents are invalid")
    return value

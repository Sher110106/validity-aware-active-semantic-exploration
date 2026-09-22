"""Safe loading from an operator-provisioned credential file."""
from __future__ import annotations

import os
import stat
from pathlib import Path

from .errors import CredentialError

MAX_CREDENTIAL_BYTES = 4096


def _under(path: str, root: str) -> bool:
    try:
        return os.path.commonpath((path, root)) == root
    except ValueError:
        return False


def load_credential(path: str, *, forbidden_roots: tuple[str, ...]) -> str:
    """Load a single-line credential without a path/value-bearing error.

    The caller must explicitly provide repository roots which are forbidden. The
    descriptor is opened with O_NOFOLLOW, then ownership/mode/type/size are
    checked on that descriptor, closing the symlink/TOCTOU gap.
    """
    generic = "credential file is unavailable"
    if not isinstance(path, str) or not os.path.isabs(path) or "\x00" in path:
        raise CredentialError(generic)
    try:
        target = os.path.realpath(path)
        roots = tuple(os.path.realpath(root) for root in forbidden_roots)
        if any(not os.path.isabs(root) or _under(target, root) for root in roots):
            raise CredentialError(generic)
        flags = os.O_RDONLY | getattr(os, "O_CLOEXEC", 0)
        if hasattr(os, "O_NOFOLLOW"):
            flags |= os.O_NOFOLLOW
        fd = os.open(path, flags)
        try:
            info = os.fstat(fd)
            if not stat.S_ISREG(info.st_mode):
                raise CredentialError(generic)
            if info.st_uid != os.getuid():
                raise CredentialError(generic)
            if stat.S_IMODE(info.st_mode) not in (0o400, 0o600):
                raise CredentialError(generic)
            if info.st_size < 1 or info.st_size > MAX_CREDENTIAL_BYTES:
                raise CredentialError(generic)
            value = b""
            while len(value) <= MAX_CREDENTIAL_BYTES:
                chunk = os.read(fd, MAX_CREDENTIAL_BYTES + 1 - len(value))
                if not chunk:
                    break
                value += chunk
            if len(value) > MAX_CREDENTIAL_BYTES:
                raise CredentialError(generic)
        finally:
            os.close(fd)
    except CredentialError:
        raise
    except (OSError, UnicodeError):
        raise CredentialError(generic)
    try:
        decoded = value.decode("utf-8").strip()
    except UnicodeError as exc:
        raise CredentialError(generic) from exc
    if not decoded or "\n" in decoded or "\r" in decoded:
        raise CredentialError(generic)
    return decoded

import ipaddress
import os
from urllib.parse import urlsplit, urlunsplit


def _is_private_host(hostname: str) -> bool:
    normalized = hostname.strip().lower().rstrip(".")
    if normalized in {"localhost", "localhost.localdomain", "metadata.google.internal"}:
        return True
    try:
        address = ipaddress.ip_address(normalized)
    except ValueError:
        return normalized.endswith((".local", ".internal", ".localhost"))
    return bool(address.is_private or address.is_loopback or address.is_link_local or address.is_reserved)


def validate_provider_base_url(value: str) -> str:
    parsed = urlsplit(value.strip())
    if parsed.scheme not in {"http", "https"} or not parsed.hostname:
        raise ValueError("provider base URL must use http or https")
    allow_local = os.getenv("CODEATLAS_ALLOW_LOCAL_PROVIDER_URLS", "").strip() == "1"
    if _is_private_host(parsed.hostname) and not allow_local:
        raise ValueError("provider URL targets a private network")
    if parsed.username or parsed.password:
        raise ValueError("provider base URL must not contain credentials")
    path = parsed.path.rstrip("/")
    return urlunsplit((parsed.scheme, parsed.netloc, path, "", ""))

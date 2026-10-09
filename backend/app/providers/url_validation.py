import ipaddress
import os
import socket
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


def _validate_and_resolve(value: str) -> tuple[str, str, str]:
    parsed = urlsplit(value.strip())
    if parsed.scheme not in {"http", "https"} or not parsed.hostname:
        raise ValueError("provider base URL must use http or https")
    allow_local = os.getenv("CODEATLAS_ALLOW_LOCAL_PROVIDER_URLS", "").strip() == "1"
    if parsed.username or parsed.password:
        raise ValueError("provider base URL must not contain credentials")
    private_literal = _is_private_host(parsed.hostname)
    if parsed.scheme == "http" and os.getenv("APP_ENV", "development").lower() in {"prod", "production"} and not (allow_local and private_literal):
        raise ValueError("provider base URL must use https in production")
    if private_literal:
        if not allow_local:
            raise ValueError("provider URL targets a private network")
        address = parsed.hostname
    else:
        try:
            addresses = socket.getaddrinfo(parsed.hostname, parsed.port or (443 if parsed.scheme == "https" else 80), type=socket.SOCK_STREAM)
        except (OSError, ValueError) as error:
            raise ValueError("provider URL hostname could not be resolved") from error
        if not addresses or any(_is_private_host(address[4][0]) for address in addresses):
            raise ValueError("provider URL targets a private network")
        address = addresses[0][4][0]
    path = parsed.path.rstrip("/")
    return urlunsplit((parsed.scheme, parsed.netloc, path, "", "")), parsed.hostname, address


def validate_provider_base_url(value: str) -> str:
    return _validate_and_resolve(value)[0]


def pin_provider_base_url(value: str) -> tuple[str, dict[str, str], dict[str, str]]:
    """Resolve and validate once, then connect to that literal IP with original Host/SNI."""
    normalized, hostname, address = _validate_and_resolve(value)
    parsed = urlsplit(normalized)
    ip_host = f"[{address}]" if ":" in address else address
    port = f":{parsed.port}" if parsed.port else ""
    host_name = f"[{hostname}]" if ":" in hostname else hostname
    host_header = f"{host_name}{port}"
    pinned = urlunsplit((parsed.scheme, f"{ip_host}{port}", parsed.path, "", ""))
    return pinned, {"Host": host_header}, {"sni_hostname": hostname}

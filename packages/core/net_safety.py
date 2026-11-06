"""Guards for fetching user-supplied URLs from the server (SSRF protection).

Only plain web addresses on the public internet are fetched: http(s), default ports, and a host
that resolves exclusively to global IPs. Loopback, private networks, link-local (incl. the
169.254.169.254 cloud metadata service) and other reserved ranges are refused. Redirects are
followed by hand so each hop is checked again.
"""

import asyncio
import ipaddress
import socket
from urllib.parse import urljoin, urlparse

import httpx

MAX_REDIRECTS = 3


class UnsafeUrlError(ValueError):
    """The URL points somewhere the server must not fetch."""


async def _resolve(host: str, port: int) -> list[str]:
    infos = await asyncio.get_running_loop().getaddrinfo(host, port, type=socket.SOCK_STREAM)
    return [str(info[4][0]) for info in infos]


async def ensure_public_url(url: str) -> str:
    parsed = urlparse(url.strip())
    if parsed.scheme not in ("http", "https"):
        raise UnsafeUrlError("Use a web link that starts with http:// or https://.")
    if not parsed.hostname:
        raise UnsafeUrlError("That link has no website address.")
    if parsed.port not in (None, 80, 443):
        raise UnsafeUrlError("Links with a custom port can't be imported.")
    if parsed.username or parsed.password:
        raise UnsafeUrlError("Links with a username or password can't be imported.")
    try:
        addresses = await _resolve(parsed.hostname, parsed.port or 443)
    except socket.gaierror as e:
        raise UnsafeUrlError("That website couldn't be found.") from e
    for address in addresses:
        ip = ipaddress.ip_address(address)
        if isinstance(ip, ipaddress.IPv6Address) and ip.ipv4_mapped:
            ip = ip.ipv4_mapped
        if not ip.is_global or ip.is_multicast:
            raise UnsafeUrlError("That link points to a private or internal address, so it can't be imported.")
    return url.strip()


async def safe_get(client: httpx.AsyncClient, url: str) -> httpx.Response:
    """GET a user-supplied URL, re-checking every redirect target. The client must not follow redirects."""
    current = await ensure_public_url(url)
    for _ in range(MAX_REDIRECTS + 1):
        resp = await client.get(current, follow_redirects=False)
        if resp.is_redirect and "location" in resp.headers:
            current = await ensure_public_url(urljoin(current, resp.headers["location"]))
            continue
        return resp
    raise UnsafeUrlError("That link redirects too many times.")

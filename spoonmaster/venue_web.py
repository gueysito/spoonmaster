"""Bounded public HTTPS reads for venue pages. No browser, proxies or redirects."""

import http.client
import ipaddress
import re
import socket
import ssl
import time
from urllib.parse import urlsplit
from urllib.robotparser import RobotFileParser

from .discovery import USER_AGENT

MAX_BYTES = 512 * 1024
TIMEOUT = 8
RESTRICTED = (
    "yelp.com",
    "theinfatuation.com",
    "guide.michelin.com",
    "eater.com",
    "nytimes.com",
    "sfchronicle.com",
    "opentable.com",
    "google.com",
    "google.co.jp",
    "tabelog.com",
    "tripadvisor.com",
    "facebook.com",
    "instagram.com",
    "x.com",
    "twitter.com",
    "tablecheck.com",
    "hotpepper.jp",
)


class PageError(Exception):
    """A safe reason code, never remote response text."""


def target(url):
    if not isinstance(url, str) or len(url) > 2048 or not url.isascii():
        raise PageError("unsupported_url")
    if any(ord(c) <= 32 or ord(c) == 127 for c in url) or "\\" in url:
        raise PageError("unsupported_url")
    try:
        parts = urlsplit(url)
        if (
            parts.scheme != "https"
            or not parts.hostname
            or parts.username is not None
            or parts.password is not None
            or parts.port not in (None, 443)
        ):
            raise PageError("unsupported_url")
    except ValueError:
        raise PageError("unsupported_url") from None
    host = parts.hostname.rstrip(".").lower()
    if any(host == domain or host.endswith("." + domain) for domain in RESTRICTED):
        raise PageError("restricted_source")
    return host, parts.path or "/", parts.query


def public_addresses(host):
    try:
        records = socket.getaddrinfo(host, 443, type=socket.SOCK_STREAM)
        addresses = list(dict.fromkeys(record[4][0] for record in records))
        if not addresses or any(
            not ipaddress.ip_address(ip).is_global or ipaddress.ip_address(ip).is_multicast
            for ip in addresses
        ):
            raise PageError("nonpublic_address")
        # IPv4-mapped IPv6 and scoped addresses are not needed for this pilot.
        if any(
            "%" in ip
            or ipaddress.ip_address(ip).ipv4_mapped
            or ipaddress.ip_address(ip).sixtofour
            or ipaddress.ip_address(ip).teredo
            for ip in addresses
            if ":" in ip
        ):
            raise PageError("nonpublic_address")
        return addresses
    except (OSError, ValueError):
        raise PageError("dns_unavailable") from None


def read(url):
    """Pin the validated IP while verifying TLS against the original hostname."""
    host, path, query = target(url)
    address = public_addresses(host)[0]
    connection = http.client.HTTPSConnection(host, timeout=TIMEOUT)
    raw_socket = None
    started = time.monotonic()
    try:
        # Connect to the validated numeric IP, never resolve the host again.
        raw_socket = socket.create_connection((address, 443), timeout=TIMEOUT)
        connection.sock = ssl.create_default_context().wrap_socket(raw_socket, server_hostname=host)
        raw_socket = None
        connection.request(
            "GET",
            path + ("?" + query if query else ""),
            headers={
                "User-Agent": USER_AGENT,
                "Accept": "text/html,text/plain",
                "Accept-Encoding": "identity",
            },
        )
        response = connection.getresponse()
        if 300 <= response.status < 400:
            raise PageError("redirect_not_followed")
        if response.status != 200:
            return response.status, "", ""
        if response.getheader("Content-Encoding", "identity") != "identity":
            raise PageError("unsupported_encoding")
        content_type = response.getheader("Content-Type", "").lower()
        if not content_type.startswith(("text/html", "text/plain", "application/xhtml+xml")):
            raise PageError("unsupported_content_type")
        data = bytearray()
        while True:
            if time.monotonic() - started > TIMEOUT:
                raise PageError("page_timeout")
            chunk = response.read1(min(16384, MAX_BYTES + 1 - len(data)))
            if not chunk:
                break
            data.extend(chunk)
            if len(data) > MAX_BYTES:
                raise PageError("page_too_large")
        charset = response.headers.get_content_charset()
        if not charset:
            declared = re.search(
                rb"<meta\b[^>]*charset\s*=\s*[\"']?([a-zA-Z0-9_-]+)", data[:4096], re.I
            )
            charset = declared[1].decode("ascii") if declared else "utf-8"
        if charset.lower() not in ("utf-8", "utf8", "shift_jis", "euc-jp", "iso-8859-1"):
            raise PageError("unsupported_charset")
        return response.status, data.decode(charset, errors="replace"), content_type
    except (OSError, http.client.HTTPException, UnicodeError):
        raise PageError("page_unavailable") from None
    finally:
        connection.close()
        if raw_socket is not None:
            raw_socket.close()


def fetch_page(url):
    host, _, _ = target(url)
    status, robots, _ = read("https://" + host + "/robots.txt")
    if status == 200:
        policy = RobotFileParser()
        policy.parse(robots.splitlines())
        if not policy.can_fetch("Spoonmaster", url):
            raise PageError("robots_disallowed")
        delay = policy.crawl_delay("Spoonmaster") or 0
        rate = policy.request_rate("Spoonmaster")
        if delay or rate:
            # Fail closed rather than keeping a tool call asleep for a site's pacing rule.
            raise PageError("robots_pacing_requires_host_browser")
    elif status not in (404, 410):
        raise PageError("robots_unavailable")
    status, html, _ = read(url)
    if status != 200:
        raise PageError("page_http_error")
    return html

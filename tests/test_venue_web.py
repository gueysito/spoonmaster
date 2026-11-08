"""Network boundaries: private addresses, rebinding, redirects and bounded responses."""

import io
import socket
import unittest
from email.message import Message
from unittest.mock import Mock, patch

from spoonmaster import venue_web as web


class WebTests(unittest.TestCase):
    def test_invalid_and_restricted_urls_do_not_resolve(self):
        with patch.object(web.socket, "getaddrinfo") as resolve:
            for url in [
                "http://example.com",
                "https://u:p@example.com",
                "https://example.com:444",
                "https://example.com\n/x",
                "https://example.com\\@localhost",
                "file:///tmp/x",
                "https://tabelog.com/x",
                "https://www.instagram.com/x",
            ]:
                with self.subTest(url=url), self.assertRaises(web.PageError):
                    web.target(url)
            resolve.assert_not_called()

    def test_any_nonpublic_dns_answer_rejects_entire_host(self):
        for address in [
            "127.0.0.1",
            "10.0.0.1",
            "169.254.169.254",
            "::1",
            "fc00::1",
            "::ffff:127.0.0.1",
            "0.0.0.0",
            "224.0.0.1",
            "2002:7f00:0001::",
        ]:
            records = [
                (socket.AF_INET, socket.SOCK_STREAM, 6, "", (ip, 443))
                for ip in ("8.8.8.8", address)
            ]
            with patch.object(web.socket, "getaddrinfo", return_value=records):
                with self.subTest(address=address), self.assertRaises(web.PageError):
                    web.public_addresses("example.com")

    def response(self, body=b"<p>Hours</p>", status=200, content_type="text/html"):
        response = Mock(status=status)
        response.headers = Message()
        response.headers["Content-Type"] = content_type
        response.getheader.side_effect = lambda key, default=None: response.headers.get(
            key, default
        )
        response.read1.side_effect = io.BytesIO(body).read1
        return response

    def request(self, response):
        connection = Mock()
        connection.getresponse.return_value = response
        raw = Mock()
        context = Mock()
        with (
            patch.object(web, "public_addresses", return_value=["8.8.8.8"]) as addresses,
            patch.object(web.socket, "create_connection", return_value=raw) as connect,
            patch.object(web.ssl, "create_default_context", return_value=context),
            patch.object(web.http.client, "HTTPSConnection", return_value=connection),
        ):
            try:
                return web.read("https://example.com/branch")
            finally:
                addresses.assert_called_once_with("example.com")
                connect.assert_called_once_with(("8.8.8.8", 443), timeout=web.TIMEOUT)
                context.wrap_socket.assert_called_once_with(raw, server_hostname="example.com")
                connection.close.assert_called_once()

    def test_connection_pins_ip_and_preserves_hostname_tls(self):
        self.assertEqual(self.request(self.response())[1], "<p>Hours</p>")

    def test_redirect_body_is_not_followed_or_read(self):
        response = self.response(status=302)
        with self.assertRaisesRegex(web.PageError, "redirect_not_followed"):
            self.request(response)
        response.read1.assert_not_called()

    def test_cap_and_content_type_fail_closed(self):
        for response in [
            self.response(b"x" * (web.MAX_BYTES + 1)),
            self.response(content_type="application/octet-stream"),
        ]:
            with self.assertRaises(web.PageError):
                self.request(response)

    def test_japanese_html_charset_is_used_when_header_omits_it(self):
        text = '<meta http-equiv="Content-Type" content="text/html; charset=shift_jis">営業時間'
        self.assertEqual(self.request(self.response(text.encode("shift_jis")))[1], text)

    def test_robots_denial_failure_and_pacing_never_fetch_page(self):
        for status, body in [
            (200, "User-agent: *\nDisallow: /"),
            (403, ""),
            (429, ""),
            (200, "User-agent: *\nCrawl-delay: 10\nAllow: /"),
        ]:
            with patch.object(web, "read", return_value=(status, body, "text/plain")) as read:
                with self.assertRaises(web.PageError):
                    web.fetch_page("https://example.com/branch")
                self.assertEqual(read.call_count, 1)

    def test_robots_missing_or_allowing_permits_one_page(self):
        for status, body in [(404, ""), (200, "User-agent: *\nAllow: /")]:
            with patch.object(
                web,
                "read",
                side_effect=[(status, body, "text/plain"), (200, "<p>Hours</p>", "text/html")],
            ) as read:
                self.assertEqual(web.fetch_page("https://example.com/branch"), "<p>Hours</p>")
                self.assertEqual(read.call_count, 2)

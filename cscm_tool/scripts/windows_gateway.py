"""A stand-in for the organisation's authenticating gateway, for testing the Windows sign-in on a
Windows machine (docs/14-deployment-architecture.md, docs/03-srs.md FR-163, SEC-033).

In a deployment IIS (Windows authentication), Apache (Kerberos) or nginx (spnego) authenticates the
browser against Active Directory and hands the user to the application in a header. This script does
the same job with the operating system's own SSPI (Negotiate: Kerberos or NTLM) so that the
application can be tried against **a real Windows identity** - the user who runs the browser or
`curl.exe --ntlm -u :` - without installing IIS:

    python scripts/windows_gateway.py --listen 127.0.0.1:8080 --upstream http://127.0.0.1:5000

    curl.exe --ntlm -u : -c jar.txt -b jar.txt -L http://127.0.0.1:8080/login/windows

It strips any `X-Remote-User` the client sent, authenticates the connection with SSPI, and forwards
the request with `X-Remote-User: DOMAIN\\name` (the name SSPI reports). The upstream application
needs `AUTH_MODE=windows` (or `both`) and `WINDOWS_AUTH_TRUSTED_PROXIES` containing the address this
script connects from (`--source`, default 127.0.0.2 so that a request that reaches the application
from anywhere else with a forged header is ignored).

It is a **test tool**, not a production gateway: it binds to the loopback interface only, speaks
plain HTTP and has no TLS, no logging of credentials and no hardening."""

from __future__ import annotations

import argparse
import base64
import ctypes
import http.client
import sys
from ctypes import POINTER, Structure, byref, c_ulong, c_void_p, c_wchar_p, sizeof
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

if sys.platform == "win32":
    from ctypes import windll  # type: ignore[attr-defined]

    windll.secur32.FreeContextBuffer.argtypes = [c_void_p]
    windll.secur32.FreeContextBuffer.restype = ctypes.c_long

SECPKG_CRED_INBOUND = 1
SECPKG_CRED_OUTBOUND = 2
SECBUFFER_TOKEN = 2
SECBUFFER_VERSION = 0
SECURITY_NATIVE_DREP = 0x10
SECPKG_ATTR_NAMES = 1
ISC_REQ_ALLOCATE_MEMORY = 0x100
ISC_REQ_CONNECTION = 0x800
ASC_REQ_ALLOCATE_MEMORY = 0x100
ASC_REQ_CONNECTION = 0x800
SEC_E_OK = 0
SEC_I_CONTINUE_NEEDED = 0x00090312
SEC_I_COMPLETE_NEEDED = 0x00090313
SEC_I_COMPLETE_AND_CONTINUE = 0x00090314
HOP_BY_HOP = {
    "connection",
    "keep-alive",
    "proxy-authenticate",
    "proxy-authorization",
    "te",
    "trailers",
    "transfer-encoding",
    "upgrade",
    "authorization",
    "content-length",
    "host",
    "x-remote-user",
}


class SecBuffer(Structure):
    _fields_ = [("cbBuffer", c_ulong), ("BufferType", c_ulong), ("pvBuffer", c_void_p)]


class SecBufferDesc(Structure):
    _fields_ = [("ulVersion", c_ulong), ("cBuffers", c_ulong), ("pBuffers", POINTER(SecBuffer))]


class SecHandle(Structure):
    _fields_ = [("dwLower", c_void_p), ("dwUpper", c_void_p)]


class TimeStamp(Structure):
    _fields_ = [("low", c_ulong), ("high", ctypes.c_long)]


class SecPkgContextNames(Structure):
    _fields_ = [("sUserName", c_wchar_p)]


def _check(status: int, what: str) -> int:
    status &= 0xFFFFFFFF
    if status not in (
        SEC_E_OK,
        SEC_I_CONTINUE_NEEDED,
        SEC_I_COMPLETE_NEEDED,
        SEC_I_COMPLETE_AND_CONTINUE,
    ):
        raise OSError(f"{what} failed: 0x{status:08X}")
    return status


def _in_desc(token: bytes | None):
    if token is None:
        return None, None
    data = ctypes.create_string_buffer(token, len(token))
    buf = SecBuffer(len(token), SECBUFFER_TOKEN, ctypes.cast(data, c_void_p))
    desc = SecBufferDesc(SECBUFFER_VERSION, 1, ctypes.pointer(buf))
    return desc, (data, buf)


def _out_desc():
    buf = SecBuffer(0, SECBUFFER_TOKEN, None)
    return SecBufferDesc(SECBUFFER_VERSION, 1, ctypes.pointer(buf)), buf


def _take(buf: SecBuffer) -> bytes:
    out = ctypes.string_at(buf.pvBuffer, buf.cbBuffer) if buf.pvBuffer and buf.cbBuffer else b""
    if buf.pvBuffer:
        windll.secur32.FreeContextBuffer(buf.pvBuffer)
    return out


class _Side:
    """One side of an SSPI exchange (a credential handle and the security context)."""

    def __init__(self, package: str, direction: int):
        self.cred, self.ctx = SecHandle(), SecHandle()
        self.has_ctx = False
        self.done = False
        expiry = TimeStamp()
        _check(
            windll.secur32.AcquireCredentialsHandleW(
                None, package, direction, None, None, None, None, byref(self.cred), byref(expiry)
            ),
            "AcquireCredentialsHandle",
        )

    def close(self) -> None:
        if self.has_ctx:
            windll.secur32.DeleteSecurityContext(byref(self.ctx))
        windll.secur32.FreeCredentialsHandle(byref(self.cred))


class ServerContext(_Side):
    """The gateway's side: accepts the client's tokens and reports who the client is."""

    def __init__(self, package: str = "Negotiate"):
        super().__init__(package, SECPKG_CRED_INBOUND)

    def step(self, token: bytes) -> bytes:
        """Feeds one client token; returns the token for the client (may be empty)."""
        in_desc, keep = _in_desc(token)
        out_desc, out_buf = _out_desc()
        attrs, expiry = c_ulong(), TimeStamp()
        status = _check(
            windll.secur32.AcceptSecurityContext(
                byref(self.cred),
                byref(self.ctx) if self.has_ctx else None,
                byref(in_desc),
                ASC_REQ_ALLOCATE_MEMORY | ASC_REQ_CONNECTION,
                SECURITY_NATIVE_DREP,
                byref(self.ctx),
                byref(out_desc),
                byref(attrs),
                byref(expiry),
            ),
            "AcceptSecurityContext",
        )
        del keep
        self.has_ctx = True
        out = _take(out_buf)
        if status in (SEC_I_COMPLETE_NEEDED, SEC_I_COMPLETE_AND_CONTINUE):
            windll.secur32.CompleteAuthToken(byref(self.ctx), byref(out_desc))
        self.done = status in (SEC_E_OK, SEC_I_COMPLETE_NEEDED)
        return out

    def user(self) -> str:
        names = SecPkgContextNames()
        _check(
            windll.secur32.QueryContextAttributesW(
                byref(self.ctx), SECPKG_ATTR_NAMES, byref(names)
            ),
            "QueryContextAttributes",
        )
        name = names.sUserName or ""
        return name


class ClientContext(_Side):
    """A client with the credentials of the Windows user running this process (the tests use it
    in place of a browser; `curl.exe --ntlm -u :` does the same)."""

    def __init__(self, package: str = "Negotiate", target: str = "localhost"):
        super().__init__(package, SECPKG_CRED_OUTBOUND)
        self.target = target

    def step(self, token: bytes | None = None) -> bytes:
        in_desc, keep = _in_desc(token)
        out_desc, out_buf = _out_desc()
        attrs, expiry = c_ulong(), TimeStamp()
        status = _check(
            windll.secur32.InitializeSecurityContextW(
                byref(self.cred),
                byref(self.ctx) if self.has_ctx else None,
                self.target,
                ISC_REQ_ALLOCATE_MEMORY | ISC_REQ_CONNECTION,
                0,
                SECURITY_NATIVE_DREP,
                byref(in_desc) if in_desc is not None else None,
                0,
                byref(self.ctx),
                byref(out_desc),
                byref(attrs),
                byref(expiry),
            ),
            "InitializeSecurityContext",
        )
        del keep
        self.has_ctx = True
        self.done = status == SEC_E_OK
        return _take(out_buf)


# ------------------------------------------------------------------------------ the gateway
class Gateway(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"  # NTLM authenticates the connection, so it has to stay open
    upstream = ("127.0.0.1", 5000)
    source = "127.0.0.2"
    header = "X-Remote-User"

    def setup(self) -> None:
        super().setup()
        self.sspi: ServerContext | None = None
        self.user: str | None = None

    def finish(self) -> None:
        if self.sspi is not None:
            self.sspi.close()
        super().finish()

    def log_message(self, fmt: str, *args) -> None:  # one short line per request, no credentials
        sys.stderr.write("gateway: " + (fmt % args) + "\n")

    def _challenge(self, token: bytes | None = None, scheme: str = "Negotiate") -> None:
        value = scheme + (" " + base64.b64encode(token).decode() if token else "")
        self.send_response(401)
        self.send_header("WWW-Authenticate", value)
        self.send_header("Content-Length", "0")
        self.end_headers()

    def _authenticate(self) -> bool:
        if self.user:
            return True
        auth = self.headers.get("Authorization", "")
        scheme, _, blob = auth.partition(" ")
        if scheme.lower() not in ("negotiate", "ntlm") or not blob.strip():
            self._challenge(scheme="Negotiate")
            return False
        if self.sspi is None:
            self.sspi = ServerContext("Negotiate" if scheme.lower() == "negotiate" else "NTLM")
        try:
            out = self.sspi.step(base64.b64decode(blob))
        except OSError as exc:
            self.log_message("authentication failed: %s", exc)
            self.sspi.close()
            self.sspi = None
            self._challenge(scheme="Negotiate")
            return False
        if self.sspi.done:
            self.user = self.sspi.user()
            self.log_message("authenticated as %s", self.user)
            return True
        self._challenge(out, scheme.capitalize() if scheme.lower() == "ntlm" else "Negotiate")
        return False

    def _forward(self) -> None:
        length = int(self.headers.get("Content-Length") or 0)
        body = self.rfile.read(length) if length else None
        headers = {k: v for k, v in self.headers.items() if k.lower() not in HOP_BY_HOP}
        headers[self.header] = self.user or ""  # whatever the client sent was dropped above
        conn = http.client.HTTPConnection(
            *self.upstream, source_address=(self.source, 0), timeout=30
        )
        try:
            conn.request(self.command, self.path, body=body, headers=headers)
            response = conn.getresponse()
            payload = response.read()
            self.send_response(response.status)
            for key, value in response.getheaders():
                if key.lower() not in HOP_BY_HOP:
                    self.send_header(key, value)
            self.send_header("Content-Length", str(len(payload)))
            self.end_headers()
            self.wfile.write(payload)
        except OSError as exc:
            self.send_error(502, f"upstream unreachable: {exc}")
        finally:
            conn.close()

    def _handle(self) -> None:
        if self._authenticate():
            self._forward()

    do_GET = do_POST = do_PUT = do_DELETE = do_HEAD = _handle


def serve(listen: str, upstream: str, source: str, header: str) -> None:
    host, _, port = listen.rpartition(":")
    if host not in ("127.0.0.1", "localhost", "::1"):
        raise SystemExit("This is a test tool: it listens on the loopback interface only.")
    up_host, _, up_port = upstream.replace("http://", "").rstrip("/").rpartition(":")
    Gateway.upstream = (up_host, int(up_port))
    Gateway.source = source
    Gateway.header = header
    server = ThreadingHTTPServer((host, int(port)), Gateway)
    print(
        f"gateway on http://{listen} -> {upstream} (connects from {source}, header {header})",
        flush=True,
    )
    server.serve_forever()


def main(argv: list[str] | None = None) -> int:
    if sys.platform != "win32":
        print("The gateway uses Windows SSPI and runs on Windows only.")
        return 2
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawTextHelpFormatter
    )
    parser.add_argument("--listen", default="127.0.0.1:8080")
    parser.add_argument("--upstream", default="http://127.0.0.1:5000")
    parser.add_argument(
        "--source", default="127.0.0.2", help="address to connect from (the trusted proxy)"
    )
    parser.add_argument("--header", default="X-Remote-User")
    args = parser.parse_args(argv)
    serve(args.listen, args.upstream, args.source, args.header)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

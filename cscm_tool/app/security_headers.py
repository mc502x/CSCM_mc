"""Standard response security headers (SEC-025, docs/11-security-architecture.md §7).

The CSP is deliberately self-only: no CDN, no third-party origin of any kind
(docs/11-security-architecture.md §12 no-cloud checklist). Scripts are
`'self'` with no inline allowance — templates use data-* hooks wired up in
static/js/app.js. `style-src` still allows inline style attributes, which the
templates use for small layout tweaks; that is a style-only relaxation.
"""

from flask import Flask, Response, request

CONTENT_SECURITY_POLICY = "; ".join(
    [
        "default-src 'self'",
        "script-src 'self'",
        "style-src 'self' 'unsafe-inline'",
        "img-src 'self' data:",
        "font-src 'self'",
        "connect-src 'self'",
        "object-src 'none'",
        "base-uri 'self'",
        "form-action 'self'",
        "frame-ancestors 'none'",
    ]
)


def register_security_headers(app: Flask) -> None:
    @app.after_request
    def _add_security_headers(response: Response) -> Response:
        response.headers.setdefault("Content-Security-Policy", CONTENT_SECURITY_POLICY)
        response.headers.setdefault("X-Content-Type-Options", "nosniff")
        response.headers.setdefault("X-Frame-Options", "DENY")
        response.headers.setdefault("Referrer-Policy", "same-origin")
        response.headers.setdefault("Cross-Origin-Opener-Policy", "same-origin")
        if request.is_secure:
            response.headers.setdefault(
                "Strict-Transport-Security", "max-age=31536000; includeSubDomains"
            )
        if not request.path.startswith("/static/"):
            # Authenticated, governed data: never cache in shared/proxy caches.
            response.headers.setdefault("Cache-Control", "no-store")
        return response

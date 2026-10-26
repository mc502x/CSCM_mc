"""Who the product is and who to ask (FR-187): the one place the names are written, used by the
title pages of the release documents and decks (scripts/build_docs_pdf.py, scripts/showcase) and
checked against the deployment guide by tests/system/test_branding.py.

The Git account and the repository are deliberately not named anywhere: the address of the
repository is given by the Software Owner or the Administrator."""

PRODUCT = "CSCM Tool"
LONG_NAME = "Controller Status Code Management Tool"
OWNER_NAME = "Bastian Ritter"
OWNER_ROLES = "Software Owner and Administrator"
OWNER_EMAIL = "bastian.ritter@senvion.in"
OWNER_LINE = f"{OWNER_ROLES}: {OWNER_NAME} · {OWNER_EMAIL}"

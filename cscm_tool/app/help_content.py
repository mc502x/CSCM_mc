# ruff: noqa: E501  (user-facing help text and an embedded HTML page)
"""In-app help (I-35): glossary tooltips, "what happens next" hints and per-role quick starts.

The content is data here, next to the code, and tests/integration/test_help_and_i18n.py keeps
it complete: every lifecycle state, every role and every change-request state has an entry,
and the terms agree with docs/19-glossary.md. The manual itself is docs/23-user-manual.md."""

ROLES = ("ADMINISTRATOR", "STCD_OWNER", "ENGINEER", "REVIEWER", "CHIEF_ENGINEER", "VIEWER")

STATE_GLOSSARY: dict[str, str] = {
    "DRAFT": "Being written. Only its author (and an Administrator) can edit it; nobody reviews it until it is submitted.",
    "REVIEW": "Submitted. A Reviewer and an Administrator each sign off, independently of each other.",
    "PENDING_APPROVAL": "Both review sign-offs are in; waiting for the Chief Engineer's decision.",
    "APPROVED": "Decided and locked. It becomes Released when an Administrator publishes a Release that includes it.",
    "RELEASED": "Published in a Release. Immutable; a change needs a new revision.",
    "DEPRECATED": "No longer to be used. Kept for the retention period; its number is never reused.",
    "ARCHIVED": "Retired after the retention period. Read-only history.",
}

ROLE_GLOSSARY: dict[str, str] = {
    "ADMINISTRATOR": "Product owner of the catalogue: signs off reviews, confirms audience access, publishes Releases, manages users and vocabularies.",
    "STCD_OWNER": "Owner of the status code library: reads the library and the workflow and moves users between Viewer, Engineer and Reviewer; does not create users or decide anything.",
    "ENGINEER": "Creates and edits Drafts, gets cross-domain sign-offs and submits them for review.",
    "REVIEWER": "Gives the first independent review sign-off; cannot review their own work.",
    "CHIEF_ENGINEER": "Takes the final approval decision; must be a different person from the author and both reviewers.",
    "VIEWER": "Read-only access to Released data.",
}

TERM_GLOSSARY: dict[str, str] = {
    **{f"state:{k}": v for k, v in STATE_GLOSSARY.items()},
    **{f"role:{k}": v for k, v in ROLE_GLOSSARY.items()},
    "audience-access": "Eight values per code saying which audiences (Development, Sales, TCC, Service, Turbine Operator Package, Grid Operator, Service Partner, Customer) may see it. Proposed by the Engineer, confirmed by the Administrator.",
    "covert": "Treated as 'not visible to that audience' in audience exports until the business defines it otherwise.",
    "segregation-of-duties": "Nobody may take two decisions on the same change: author, Reviewer, Administrator and Chief Engineer are four different people.",
    "step-up": "Sign-offs, approvals, publishing and the full backup ask for your password again so each is a deliberate, attributable act.",
    "row-version": "A counter that increases on every save of a Draft; it lets the tool notice that someone else saved first.",
    "change-set": "A group of change requests that ship with one controller software release, shown and queued together.",
    "legacy-reference": "The code's number in the old library; used to match rows when you re-import.",
}

# What happens next, by change-request state (shown on the CR screen).
NEXT_STEP: dict[str, str] = {
    "DRAFT": "The author gets any required cross-domain sign-offs, then submits the change request for review.",
    "REVIEW": "A Reviewer and an Administrator each sign off (in any order). If either rejects, it goes back to the author.",
    "PENDING_APPROVAL": "The Chief Engineer approves or rejects. Approval makes the revision Approved (or Deprecated for a deprecation request).",
    "APPROVED": "An Administrator includes the revision in a Release and publishes it; then it is Released.",
    "REJECTED": "It went back to Draft: the author revises it and submits again.",
    "WITHDRAWN": "The author withdrew it; nothing further happens.",
}

QUICK_START: dict[str, list[tuple[str, str]]] = {
    "ENGINEER": [
        (
            "Create a code",
            "New Status Code: pick group and subgroup, fill in the fields, save as Draft.",
        ),
        (
            "Get sign-offs",
            "Open the change request; request any missing cross-domain sign-off from a colleague.",
        ),
        ("Submit", "Submit for Review - the number is allocated now."),
        (
            "Follow it",
            "My Change Requests shows every state; comments appear on the change request.",
        ),
    ],
    "REVIEWER": [
        ("Pick a request", "Review Queue lists everything waiting; amber/red shows how long."),
        (
            "Read the changes",
            "The change request shows a field-by-field diff; add field comments where something is wrong.",
        ),
        (
            "Decide",
            "Confirm the review checklist, approve or reject (a comment is required for rejection), and enter your password.",
        ),
    ],
    "ADMINISTRATOR": [
        (
            "Sign off",
            "Review Queue: confirm or override the audience-access values, then approve or reject.",
        ),
        ("Release", "Releases: build a Release from Approved codes, check warnings, publish."),
        (
            "Publish files",
            "Export Center: choose a profile and audience; each file comes with a manifest.",
        ),
        (
            "Keep it healthy",
            "Catalogue Health, Stalled requests, Backups and the Audit Log are under Administration.",
        ),
    ],
    "CHIEF_ENGINEER": [
        (
            "Decide",
            "Approval Queue: read the change, the reviews and the evidence, then approve or reject.",
        ),
        (
            "Watch the pipeline",
            "Success Metrics shows approval times and how long requests have waited.",
        ),
    ],
    "STCD_OWNER": [
        (
            "Place people",
            "Administration > Users: move a user between Viewer, Engineer and Reviewer. Every other role needs an Administrator.",
        ),
        (
            "Follow the work",
            "Change Sets and the change request pages show where the library stands; you read, you do not decide.",
        ),
    ],
    "VIEWER": [
        (
            "Browse",
            "Status Codes lists everything Released; search by identifier, title or description.",
        ),
        ("Export", "Export Center downloads the Released catalogue as CSV, JSON, XLSX or PDF."),
    ],
}

# ruff: noqa: E501  (docstring lines and the sentences of messages)
"""Bulk work on a change set (FR-180): the way ~1,250 imported codes can go through the governance.

The governance of the catalogue - cross-domain sign-off, two reviews, the Chief Engineer - is right for a
new code and impossible for the first migration of ~900 Main and ~350 Hub Controller codes, one code at a
time. A change set (I-11) groups the codes of one batch; this service lets the people who hold each step
work on the whole batch, **without making the step weaker**:

* every code still gets its own service call, its own segregation-of-duties check, its own audit entry and
  - for the decisions - its own password check (the one entered for the sitting); a code the person may not
  decide is reported and skipped, never decided;
* a bulk decision (a domain sign-off, a review, the approval) on more than a handful of codes needs a
  **sample inspection**: the system draws a random sample of the batch - stratified by subgroup, so every
  part of the controller is looked at, 10 % but at least 8 codes by default (settings `bulk.sample_percent`,
  `bulk.sample_minimum`, `bulk.sample_above`) - and the person who decides marks every sampled code OK or
  DEFECT after looking at it. One defect blocks the bulk decision: the defective codes are sent back (or
  fixed) and a new sample is drawn from what is left. The sample, who drew it, the seed and every verdict are
  kept (`bulk_sample`, `bulk_sample_item`), named in the comment of every code that was decided with it and
  written to the audit log, and the *dossier* of the change set (an XLSX) puts it all in one document for an
  auditor;
* bulk edit, submit and sign-off need no more than the single-code rules say: only the author edits and
  submits, only a holder of the domain signs it.

What a bulk action never does: decide a code the person wrote, skip a step, hide a code from the sample
because it looks fine, or let one sample serve two decisions."""

from __future__ import annotations

import hashlib
import io
import math
import random
import secrets
from datetime import UTC, datetime, timedelta
from typing import Any

from app.domain.errors import DomainError, ForbiddenError, NotFoundError
from app.extensions import db
from app.models.audit import AuditLogEntry
from app.models.change_request import (
    BulkSample,
    BulkSampleItem,
    ChangeRequest,
    ChangeSet,
)
from app.services.audit_service import AuditService
from app.services.change_request_service import ChangeRequestService
from app.services.domain_signoff_service import DomainSignoffService
from app.services.settings_service import SettingsService
from app.services.status_code_service import StatusCodeService, revision_to_data
from app.utils import utcnow_iso

STEPS = ("domain", "reviewer", "admin", "chief-engineer")
STEP_STATE = {
    "domain": "DRAFT",
    "reviewer": "REVIEW",
    "admin": "REVIEW",
    "chief-engineer": "PENDING_APPROVAL",
}
STEP_ROLE = {
    "domain": None,
    "reviewer": "REVIEWER",
    "admin": "ADMINISTRATOR",
    "chief-engineer": "CHIEF_ENGINEER",
}
SAMPLE_LIFETIME = timedelta(hours=24)
EDITABLE = (
    "status_category",
    "turbine_platforms",
    "available_group",
    "development_access",
    "sales_access",
    "tcc_access",
    "service_access",
    "turbine_operator_package_access",
    "grid_operator_access",
    "service_partner_access",
    "customer_access",
)


def _parse(stamp: str) -> datetime:
    return datetime.fromisoformat(stamp.replace("Z", "+00:00")).astimezone(UTC)


def _hash(ids: list[int]) -> str:
    return hashlib.sha256(",".join(str(i) for i in sorted(ids)).encode()).hexdigest()[:16]


class BulkService:
    # ------------------------------------------------------------------ the rule
    @staticmethod
    def rules() -> dict[str, int]:
        return {
            "percent": int(SettingsService.get("bulk.sample_percent")),
            "minimum": int(SettingsService.get("bulk.sample_minimum")),
            "above": int(SettingsService.get("bulk.sample_above")),
        }

    @staticmethod
    def sample_size(population: int) -> int:
        """0 when no sample is needed (at most `above` codes), else the share of the batch but at
        least `minimum`, never more than the batch."""
        rules = BulkService.rules()
        if population <= rules["above"]:
            return 0
        return min(
            population, max(rules["minimum"], math.ceil(population * rules["percent"] / 100))
        )

    # ------------------------------------------------------------------ who may be decided
    @staticmethod
    def eligible(
        change_set: ChangeSet,
        step: str,
        actor,
        domain_code: str | None = None,
        cr_ids: list[int] | None = None,
    ) -> list[ChangeRequest]:
        """The change requests of the set the actor can take through `step` right now."""
        if step not in STEPS:
            raise ValueError("step must be domain, reviewer, admin or chief-engineer")
        if step == "domain":
            if not domain_code:
                raise ValueError("A domain sign-off needs the engineering domain.")
            if domain_code not in actor.engineering_domain_codes:
                raise DomainError(f"You do not hold the {domain_code} Engineering Domain.")
        else:
            role = STEP_ROLE[step]
            if role is not None and not actor.can_act_as(role):
                raise ForbiddenError(f"SEC-010: your role cannot take the {step} step.")
        wanted = set(cr_ids) if cr_ids else None
        out = []
        for cr in change_set.change_requests:
            if wanted is not None and cr.id not in wanted:
                continue
            revision = cr.revision
            if revision.lifecycle_status != STEP_STATE[step] or cr.requested_by == actor.id:
                continue
            if step == "domain" and domain_code in DomainSignoffService.signed_off_domains(cr):
                continue
            if step == "reviewer" and revision.reviewer_signoff_by is not None:
                continue
            if step == "admin" and revision.admin_signoff_by is not None:
                continue
            out.append(cr)
        return out

    # ------------------------------------------------------------------ the sample
    @staticmethod
    def _stratified(eligible: list[ChangeRequest], size: int, rng: random.Random) -> list[int]:
        """`size` change requests, spread over the subgroups in proportion to their share, at least
        one from every subgroup while the sample is large enough for that."""
        groups: dict[int, list[int]] = {}
        for cr in sorted(eligible, key=lambda c: c.id):
            groups.setdefault(cr.revision.status_code.functional_subgroup_id, []).append(cr.id)
        total = len(eligible)
        keys = sorted(groups)
        quota = {k: int(size * len(groups[k]) / total) for k in keys}
        if size >= len(keys):
            quota = {k: max(1, quota[k]) for k in keys}
        remainders = sorted(keys, key=lambda k: (-((size * len(groups[k]) / total) % 1), k))
        while sum(quota.values()) < size:
            for k in remainders:
                if sum(quota.values()) >= size:
                    break
                if quota[k] < len(groups[k]):
                    quota[k] += 1
        while sum(quota.values()) > size:
            largest = max(keys, key=lambda k: (quota[k], k))
            quota[largest] -= 1
        chosen: list[int] = []
        for k in keys:
            members = list(groups[k])
            rng.shuffle(members)
            chosen.extend(members[: min(quota[k], len(members))])
        return sorted(chosen)

    @staticmethod
    def draw_sample(
        change_set_id: int,
        step: str,
        actor,
        domain_code: str | None = None,
        cr_ids: list[int] | None = None,
    ) -> BulkSample:
        change_set = BulkService._set(change_set_id)
        eligible = BulkService.eligible(change_set, step, actor, domain_code, cr_ids)
        size = BulkService.sample_size(len(eligible))
        if not eligible:
            raise DomainError("No change request of the set is waiting for you at this step.")
        if size == 0:
            raise DomainError(
                f"No sample is needed for {len(eligible)} codes; decide them one by one or all at once."
            )
        for old in db.session.query(BulkSample).filter(
            BulkSample.change_set_id == change_set.id,
            BulkSample.drawn_by == actor.id,
            BulkSample.step == step,
            BulkSample.domain_code == domain_code,
            BulkSample.status.in_(("OPEN", "PASSED", "FAILED")),
        ):
            old.status = "VOID"
        seed = secrets.token_hex(8)
        rng = random.Random(seed)  # nosec B311 - a draw, not a secret
        chosen = BulkService._stratified(eligible, size, rng)
        sample = BulkSample(
            change_set_id=change_set.id,
            step=step,
            domain_code=domain_code,
            drawn_by=actor.id,
            drawn_at=utcnow_iso(),
            seed=seed,
            population=len(eligible),
            population_hash=_hash([c.id for c in eligible]),
            rate_percent=BulkService.rules()["percent"],
            status="OPEN",
        )
        db.session.add(sample)
        db.session.flush()
        for cr_id in chosen:
            db.session.add(BulkSampleItem(sample_id=sample.id, change_request_id=cr_id))
        AuditService.log(
            "ChangeSet",
            change_set.id,
            "BULK_SAMPLE_DRAW",
            actor=actor,
            after={
                "sample_id": sample.id,
                "step": step,
                "domain": domain_code,
                "population": len(eligible),
                "sample": len(chosen),
                "seed": seed,
                "change_request_ids": chosen,
            },
        )
        db.session.commit()
        return sample

    @staticmethod
    def record_verdict(
        sample_id: int, cr_id: int, verdict: str, note: str | None, actor
    ) -> BulkSample:
        sample = BulkService.get_sample(sample_id)
        if sample.drawn_by != actor.id:
            raise ForbiddenError("This is not your sample: the person who decides inspects.")
        if sample.status in ("USED", "VOID"):
            raise DomainError("This sample is closed.")
        verdict = (verdict or "").strip().upper()
        if verdict not in ("OK", "DEFECT"):
            raise ValueError("The verdict must be OK or DEFECT.")
        note = (note or "").strip() or None
        if verdict == "DEFECT" and not note:
            raise ValueError("A defect needs a note: say what is wrong.")
        if note and len(note) > 1000:
            raise ValueError("A note has at most 1000 characters.")
        item = next((i for i in sample.items if i.change_request_id == cr_id), None)
        if item is None:
            raise NotFoundError("That change request is not in the sample.")
        item.verdict, item.note, item.checked_at = verdict, note, utcnow_iso()
        BulkService._settle(sample)
        AuditService.log(
            "BulkSample",
            sample.id,
            "BULK_SAMPLE_VERDICT",
            actor=actor,
            after={"change_request_id": cr_id, "verdict": verdict, "note": note},
        )
        db.session.commit()
        return sample

    @staticmethod
    def _settle(sample: BulkSample) -> None:
        verdicts = [i.verdict for i in sample.items]
        if any(v is None for v in verdicts):
            sample.status = "OPEN"
        elif any(v == "DEFECT" for v in verdicts):
            sample.status = "FAILED"
        else:
            sample.status = "PASSED"

    @staticmethod
    def get_sample(sample_id: int) -> BulkSample:
        sample = db.session.get(BulkSample, sample_id)
        if sample is None:
            raise NotFoundError("Sample not found")
        return sample

    @staticmethod
    def samples(change_set_id: int) -> list[BulkSample]:
        return (
            db.session.query(BulkSample)
            .filter_by(change_set_id=change_set_id)
            .order_by(BulkSample.id.desc())
            .all()
        )

    @staticmethod
    def require_sample(
        sample_id: int | None,
        change_set: ChangeSet,
        step: str,
        actor,
        eligible: list[ChangeRequest],
        domain_code: str | None = None,
    ) -> BulkSample | None:
        """The gate of a bulk decision: None when the batch is small enough to need no sample,
        else the passed sample that covers exactly this batch, or an error that says what is missing.
        """
        if BulkService.sample_size(len(eligible)) == 0:
            return None
        if sample_id is None:
            raise DomainError(
                f"{len(eligible)} codes need a sample inspection first: draw a sample, mark every "
                "sampled code OK or DEFECT, then decide."
            )
        sample = BulkService.get_sample(sample_id)
        if (
            sample.change_set_id != change_set.id
            or sample.step != step
            or sample.domain_code != domain_code
        ):
            raise DomainError("This sample belongs to another change set or another step.")
        if sample.drawn_by != actor.id:
            raise ForbiddenError("This is not your sample: the person who decides inspects.")
        if sample.status == "USED":
            raise DomainError("This sample has been used for a decision already; draw a new one.")
        if sample.status == "VOID":
            raise DomainError("This sample was replaced by a newer one.")
        if datetime.now(UTC) - _parse(sample.drawn_at) > SAMPLE_LIFETIME:
            raise DomainError("This sample is older than 24 hours; draw a new one.")
        open_items = sum(1 for i in sample.items if i.verdict is None)
        if open_items:
            raise DomainError(f"{open_items} sampled codes still need your verdict.")
        defects = sum(1 for i in sample.items if i.verdict == "DEFECT")
        if defects:
            raise DomainError(
                f"{defects} sampled codes have defects: send them back or correct them, then draw "
                "a new sample of what is left."
            )
        if sample.population_hash != _hash([c.id for c in eligible]):
            raise DomainError("The batch changed since the sample was drawn; draw a new sample.")
        return sample

    @staticmethod
    def sample_note(sample: BulkSample | None) -> str:
        if sample is None:
            return ""
        return (
            f" [bulk decision, sample #{sample.id}: {len(sample.items)} of {sample.population} "
            "inspected, none defective]"
        )

    @staticmethod
    def reject_defects(
        sample_id: int, actor, reauth_password: str | None, comment: str | None = None
    ) -> list[dict[str, Any]]:
        """Send back the codes of a sample that were found defective, with the note of the inspector
        as the reason; the sample is then closed and a new one is drawn from what is left. Only the
        decision steps can reject: a defect in a Draft is for its author."""
        from app.services.auth_service import AuthService

        sample = BulkService.get_sample(sample_id)
        if sample.drawn_by != actor.id:
            raise ForbiddenError("This is not your sample: the person who decides inspects.")
        if sample.step == "domain":
            raise DomainError("A defective Draft is corrected by its author.")
        if sample.status != "FAILED":
            raise DomainError("Only a sample with defects can be sent back.")
        AuthService.step_up(actor, reauth_password, f"BULK_{sample.step.upper()}_DECISION")
        results = []
        for item in sample.items:
            if item.verdict != "DEFECT":
                continue
            reason = " ".join(filter(None, [(comment or "").strip(), item.note]))
            try:
                if sample.step == "reviewer":
                    ChangeRequestService.reviewer_signoff(
                        item.change_request_id,
                        actor,
                        "REJECT",
                        reason,
                        reauth_password=reauth_password,
                    )
                elif sample.step == "admin":
                    ChangeRequestService.admin_signoff(
                        item.change_request_id,
                        actor,
                        "REJECT",
                        reason,
                        reauth_password=reauth_password,
                    )
                else:
                    ChangeRequestService.chief_engineer_decide(
                        item.change_request_id,
                        actor,
                        "REJECT",
                        reason,
                        reauth_password=reauth_password,
                    )
            except (DomainError, ValueError) as exc:
                db.session.rollback()
                results.append({"cr_id": item.change_request_id, "ok": False, "message": str(exc)})
            else:
                results.append(
                    {"cr_id": item.change_request_id, "ok": True, "message": "Sent back."}
                )
        sample = BulkService.get_sample(sample_id)
        sample.status = "VOID"
        AuditService.log(
            "BulkSample",
            sample.id,
            "BULK_SAMPLE_VOID",
            actor=actor,
            after={"sent_back": sum(1 for r in results if r["ok"]), "reason": "defects"},
        )
        db.session.commit()
        return results

    # ------------------------------------------------------------------ the bulk steps
    @staticmethod
    def _set(change_set_id: int) -> ChangeSet:
        change_set = db.session.get(ChangeSet, change_set_id)
        if change_set is None:
            raise NotFoundError("Change set not found")
        return change_set

    @staticmethod
    def domain_signoff(
        change_set_id: int,
        domain_code: str,
        actor,
        sample_id: int | None = None,
        cr_ids: list[int] | None = None,
    ) -> list[dict[str, Any]]:
        change_set = BulkService._set(change_set_id)
        eligible = BulkService.eligible(change_set, "domain", actor, domain_code, cr_ids)
        if not eligible:
            raise DomainError("No Draft of the set is waiting for the sign-off of this domain.")
        sample = BulkService.require_sample(
            sample_id, change_set, "domain", actor, eligible, domain_code
        )
        results = []
        for cr in eligible:
            try:
                DomainSignoffService.sign(cr, domain_code, actor)
            except (DomainError, ValueError) as exc:
                db.session.rollback()
                results.append({"cr_id": cr.id, "ok": False, "message": str(exc)})
            else:
                results.append({"cr_id": cr.id, "ok": True, "message": "Signed off."})
        BulkService._close(
            change_set, "BULK_DOMAIN_SIGNOFF", actor, results, sample, domain=domain_code
        )
        return results

    @staticmethod
    def submit(change_set_id: int, actor, cr_ids: list[int] | None = None) -> list[dict[str, Any]]:
        """Submit for review every Draft of the set that the actor wrote."""
        change_set = BulkService._set(change_set_id)
        wanted = set(cr_ids) if cr_ids else None
        results = []
        for cr in list(change_set.change_requests):
            if wanted is not None and cr.id not in wanted:
                continue
            if cr.revision.lifecycle_status != "DRAFT" or cr.requested_by != actor.id:
                continue
            try:
                ChangeRequestService.submit(cr.id, actor)
            except (DomainError, ValueError) as exc:
                db.session.rollback()
                results.append({"cr_id": cr.id, "ok": False, "message": str(exc)})
            else:
                results.append({"cr_id": cr.id, "ok": True, "message": "Submitted for review."})
        BulkService._close(change_set, "BULK_SUBMIT", actor, results, None)
        return results

    @staticmethod
    def edit(
        change_set_id: int,
        cr_ids: list[int] | None,
        changes: dict[str, Any],
        actor,
    ) -> list[dict[str, Any]]:
        """Set the same value on the Drafts the actor may edit: category, platforms, available group,
        the eight access levels. Each Draft goes through the ordinary save (concurrency, validation,
        its own audit entry)."""
        unknown = sorted(set(changes) - set(EDITABLE))
        if unknown:
            raise ValueError(f"These fields cannot be set in bulk: {', '.join(unknown)}.")
        if not changes:
            raise ValueError("Choose at least one value to set.")
        change_set = BulkService._set(change_set_id)
        wanted = set(cr_ids) if cr_ids else None
        results = []
        for cr in list(change_set.change_requests):
            if wanted is not None and cr.id not in wanted:
                continue
            revision = cr.revision
            if revision.lifecycle_status != "DRAFT":
                continue
            try:
                data = {**revision_to_data(revision), **changes}
                StatusCodeService.update_draft(revision.id, data, actor)
            except Exception as exc:  # noqa: BLE001 - reported per code
                db.session.rollback()
                message = getattr(exc, "field_errors", None) or str(exc)
                results.append({"cr_id": cr.id, "ok": False, "message": str(message)})
            else:
                results.append({"cr_id": cr.id, "ok": True, "message": "Saved."})
        BulkService._close(change_set, "BULK_EDIT", actor, results, None, fields=sorted(changes))
        return results

    @staticmethod
    def _close(
        change_set: ChangeSet,
        action: str,
        actor,
        results: list[dict[str, Any]],
        sample: BulkSample | None,
        **extra: Any,
    ) -> None:
        done = sum(1 for r in results if r["ok"])
        if sample is not None and done:
            sample.status, sample.used_at = "USED", utcnow_iso()
        AuditService.log(
            "ChangeSet",
            change_set.id,
            action,
            actor=actor,
            after={
                "done": done,
                "failed": len(results) - done,
                "sample_id": sample.id if sample else None,
                **extra,
            },
        )
        db.session.commit()

    # ------------------------------------------------------------------ what blocks a Draft
    @staticmethod
    def readiness(change_set_id: int) -> dict[str, Any]:
        """For each Draft of the set what still stops it from being submitted."""
        change_set = BulkService._set(change_set_id)
        rows = []
        tally = {"ready": 0, "blocked": 0}
        for cr in change_set.change_requests:
            revision = cr.revision
            if revision.lifecycle_status != "DRAFT":
                continue
            blockers: list[str] = []
            if not revision.platforms:
                blockers.append("no turbine platform")
            author_domains = frozenset(
                link.engineering_domain.code for link in cr.requester.engineering_domains
            )
            pending = sorted(DomainSignoffService.pending_domains(cr, author_domains))
            if pending:
                blockers.append("domain sign-off pending: " + ", ".join(pending))
            tally["blocked" if blockers else "ready"] += 1
            rows.append(
                {
                    "cr": cr,
                    "identifier": revision.status_code.status_code_identifier
                    or revision.status_code.reserved_identifier,
                    "title": revision.title,
                    "category": revision.status_category,
                    "blockers": blockers,
                    "pending_domains": pending,
                }
            )
        pending_by_domain: dict[str, int] = {}
        for row in rows:
            for code in row["pending_domains"]:
                pending_by_domain[code] = pending_by_domain.get(code, 0) + 1
        return {
            "rows": rows,
            "tally": tally,
            "pending_by_domain": dict(sorted(pending_by_domain.items())),
        }

    # ------------------------------------------------------------------ the dossier
    @staticmethod
    def dossier(change_set_id: int) -> bytes:
        """The change set in one XLSX for an audit: every code with its decisions, every sample with
        its verdicts, the audit entries of the set."""
        from openpyxl import Workbook

        change_set = BulkService._set(change_set_id)
        samples = BulkService.samples(change_set_id)
        sampled: dict[int, list[str]] = {}
        for sample in samples:
            for item in sample.items:
                sampled.setdefault(item.change_request_id, []).append(
                    f"#{sample.id} {sample.step}{':' + sample.domain_code if sample.domain_code else ''} "
                    f"{item.verdict or 'not checked'}"
                )
        workbook = Workbook()
        summary = workbook.active
        summary.title = "Change set"
        for row in (
            ("Change set", change_set.name),
            ("Status", change_set.status),
            ("Created", change_set.created_at),
            ("Codes", len(change_set.change_requests)),
            ("Samples", len(samples)),
            ("Generated (UTC)", utcnow_iso()),
        ):
            summary.append(row)
        codes = workbook.create_sheet("Codes")
        codes.append(
            ["Code", "Title", "State", "Author", "Domain sign-offs", "Reviewer", "Reviewer at",
             "Administrator", "Administrator at", "Chief Engineer", "Chief Engineer at", "Samples"]
        )  # fmt: skip
        for cr in change_set.change_requests:
            revision = cr.revision
            codes.append(
                [
                    revision.status_code.status_code_identifier
                    or revision.status_code.reserved_identifier,
                    revision.title,
                    revision.lifecycle_status,
                    cr.requester.full_name,
                    "; ".join(
                        f"{s.engineering_domain.code} {s.signed_off_at}" for s in cr.domain_signoffs
                    ),
                    _name(revision.reviewer_signoff_by),
                    revision.reviewer_signoff_at,
                    _name(revision.admin_signoff_by),
                    revision.admin_signoff_at,
                    _name(cr.chief_engineer_decided_by),
                    cr.chief_engineer_decided_at,
                    "; ".join(sampled.get(cr.id, [])),
                ]
            )
        sheet = workbook.create_sheet("Samples")
        sheet.append(
            ["Sample", "Step", "Domain", "Drawn by", "Drawn at", "Seed", "Rate %", "Population",
             "Sampled", "Status", "Used at"]
        )  # fmt: skip
        for sample in samples:
            sheet.append(
                [sample.id, sample.step, sample.domain_code, _name(sample.drawn_by), sample.drawn_at,
                 sample.seed, sample.rate_percent, sample.population, len(sample.items), sample.status,
                 sample.used_at]
            )  # fmt: skip
        items = workbook.create_sheet("Sample items")
        items.append(["Sample", "Code", "Verdict", "Note", "Checked at"])
        for sample in samples:
            for item in sample.items:
                revision = item.change_request.revision
                items.append(
                    [
                        sample.id,
                        revision.status_code.status_code_identifier
                        or revision.status_code.reserved_identifier,
                        item.verdict,
                        item.note,
                        item.checked_at,
                    ]
                )
        audit = workbook.create_sheet("Audit")
        audit.append(["When", "Action", "Actor", "Detail"])
        for entry in (
            db.session.query(AuditLogEntry)
            .filter(
                AuditLogEntry.entity_type == "ChangeSet", AuditLogEntry.entity_id == change_set.id
            )
            .order_by(AuditLogEntry.id)
        ):
            audit.append(
                [entry.occurred_at, entry.action, _name(entry.actor_id), entry.after_value]
            )
        buffer = io.BytesIO()
        workbook.save(buffer)
        return buffer.getvalue()


def _name(user_id: int | None) -> str | None:
    if user_id is None:
        return None
    from app.models.user import User

    user = db.session.get(User, user_id)
    return user.full_name if user else None

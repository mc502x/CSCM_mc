"""Duplicate and near-duplicate detection (I-12).

When a code is created or imported, show the existing codes of the same
Functional Subgroup whose title is the same or very similar ("did you mean to
revise StCd-01234?"). It is a warning, never a block: two codes may legitimately
share a title across platforms or conditions. Its purpose is to keep the
catalogue from bloating during the ~1,160-row legacy migration."""

import re
from difflib import SequenceMatcher

from app.extensions import db
from app.models.status_code import StatusCode, StatusCodeRevision

SIMILARITY_THRESHOLD = 0.82
_NON_ALNUM = re.compile(r"[^0-9a-zäöüß]+")


def normalize(text: str | None) -> str:
    return _NON_ALNUM.sub(" ", (text or "").lower()).strip()


def similarity(a: str | None, b: str | None) -> float:
    """0..1: the larger of character-level similarity and word-set overlap, on the
    normalised text, so word order and punctuation differences do not hide a duplicate."""
    na, nb = normalize(a), normalize(b)
    if not na or not nb:
        return 0.0
    if na == nb:
        return 1.0
    ratio = SequenceMatcher(None, na, nb).ratio()
    wa, wb = set(na.split()), set(nb.split())
    jaccard = len(wa & wb) / len(wa | wb) if wa | wb else 0.0
    return max(ratio, jaccard)


class DuplicateService:
    @staticmethod
    def find_similar(
        title: str,
        subgroup_id: int,
        exclude_status_code_id: int | None = None,
        limit: int = 5,
        threshold: float = SIMILARITY_THRESHOLD,
    ) -> list[dict]:
        rows = (
            db.session.query(StatusCodeRevision, StatusCode)
            .join(StatusCode, StatusCode.id == StatusCodeRevision.status_code_id)
            .filter(
                StatusCode.functional_subgroup_id == subgroup_id,
                StatusCode.is_sandbox == 0,
                StatusCodeRevision.is_current == 1,
            )
            .all()
        )
        scored = []
        for revision, code in rows:
            if exclude_status_code_id is not None and code.id == exclude_status_code_id:
                continue
            score = similarity(title, revision.title)
            if score >= threshold:
                scored.append(
                    {
                        "status_code_id": code.id,
                        "status_code_identifier": code.status_code_identifier,
                        "title": revision.title,
                        "lifecycle_status": revision.lifecycle_status,
                        "score": round(score, 2),
                    }
                )
        scored.sort(key=lambda d: (-d["score"], d["status_code_id"]))
        return scored[:limit]

    @staticmethod
    def warnings_for_revision(revision: StatusCodeRevision) -> list[dict]:
        """Only a brand-new code (revision 1) is compared; a later revision of a code is
        by definition not a duplicate of the code it revises."""
        if revision.revision_number != 1:
            return []
        code = revision.status_code
        warnings = []
        for hit in DuplicateService.find_similar(
            revision.title, code.functional_subgroup_id, exclude_status_code_id=code.id
        ):
            label = hit["status_code_identifier"] or f"draft #{hit['status_code_id']}"
            warnings.append(
                {
                    "type": "POSSIBLE_DUPLICATE",
                    "field": "title",
                    "message": f"Similar to {label} \"{hit['title']}\" "
                    f"({int(hit['score'] * 100)}% alike) in the same subgroup - "
                    "did you mean to revise that code instead?",
                    "status_code_id": hit["status_code_id"],
                    "score": hit["score"],
                }
            )
        return warnings

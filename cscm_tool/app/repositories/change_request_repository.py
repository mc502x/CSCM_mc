from app.extensions import db
from app.models.change_request import ChangeRequest, DomainSignoff, ReviewComment
from app.repositories.base import BaseRepository
from app.utils import utcnow_iso


class ChangeRequestRepository(BaseRepository[ChangeRequest]):
    model = ChangeRequest

    def add_comment(
        self, cr: ChangeRequest, author, text: str, decision: str | None
    ) -> ReviewComment:
        comment = ReviewComment(
            change_request_id=cr.id,
            author_id=author.id,
            comment_text=text,
            decision=decision,
            created_at=utcnow_iso(),
        )
        db.session.add(comment)
        return comment

    def clear_review_signoffs(self, revision) -> None:
        revision.reviewer_signoff_by = None
        revision.reviewer_signoff_at = None
        revision.admin_signoff_by = None
        revision.admin_signoff_at = None

    def delete_with_children(self, cr: ChangeRequest) -> None:
        """Used only by withdraw() on an abandoned CR — see
        app/services/change_request_service.py for why this is safe."""
        db.session.query(ReviewComment).filter(ReviewComment.change_request_id == cr.id).delete()
        db.session.query(DomainSignoff).filter(DomainSignoff.change_request_id == cr.id).delete()
        db.session.delete(cr)

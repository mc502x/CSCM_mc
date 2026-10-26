"""S42 Translations, S43 Translation review, S44 Translation decisions (docs/26-translations.md,
docs/03-srs.md FR-164). Native speakers check the interface translations of their language in the
browser; an Administrator or StCd Owner assigns them and decides on their proposals. The screens are
in English: the reviewer reads the English source, and the language under review is shown in the
cells (right to left where the language is)."""

from flask import (
    Response,
    abort,
    flash,
    redirect,
    render_template,
    request,
    url_for,
)

from app.auth.decorators import current_user, login_required_web
from app.domain.errors import DomainError, ForbiddenError, NotFoundError
from app.extensions import db
from app.models.user import User
from app.services.translation_review_service import TranslationReviewService as Reviews
from app.translation_catalogue import ENGLISH_NAMES, build_sheet, effective, is_rtl, label
from app.ui import ui_bp

_XLSX = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"


def _language(code: str) -> str:
    if code not in ENGLISH_NAMES or code == "en":
        abort(404)
    return code


def _filters() -> dict:
    return {
        "scope": (
            request.values.get("scope")
            if request.values.get("scope") in ("missing", "all")
            else "translated"
        ),
        "q": (request.values.get("q") or "").strip(),
        "screen": (request.values.get("screen") or "").strip(),
        "state": (request.values.get("state") or "").strip(),
        "page": request.values.get("page", type=int) or 1,
    }


def _back(language: str, **override):
    values = {
        k: v for k, v in {**_filters(), **override}.items() if v not in ("", None, 1, "translated")
    }
    return redirect(url_for("ui.translation_review", language=language, **values))


@ui_bp.route("/translations")
@login_required_web
def translations_overview():
    return render_template(
        "translations/overview.html",
        rows=Reviews.overview(current_user),
        manager=Reviews.is_manager(current_user),
        label=label,
        names=ENGLISH_NAMES,
    )


@ui_bp.route("/translations/<language>")
@login_required_web
def translation_review(language):
    language = _language(language)
    if not Reviews.can_review(current_user, language):
        if Reviews.is_manager(current_user):
            return redirect(url_for("ui.translation_decisions", language=language))
        abort(403)
    review = Reviews.start(language, current_user)
    filters = _filters()
    data = Reviews.page(review, **filters)
    return render_template(
        "translations/review.html",
        review=review,
        language=language,
        title=f"{label(language)} - {ENGLISH_NAMES[language]}",
        rtl=is_rtl(language),
        data=data,
        f=filters,
    )


@ui_bp.route("/translations/<language>/save", methods=["POST"])
@login_required_web
def translation_save(language):
    language = _language(language)
    try:
        review = Reviews.start(language, current_user)
    except ForbiddenError:
        abort(403)
    entries = [
        {
            "string_id": sid,
            "verdict": request.form.get(f"v_{sid}"),
            "proposal": request.form.get(f"p_{sid}"),
            "comment": request.form.get(f"c_{sid}"),
        }
        for sid in request.form.getlist("sid")
    ]
    result = Reviews.save(review.id, entries, current_user)
    if result["saved"]:
        flash(f"Saved {result['saved']} answer(s).", "success")
    for error in result["errors"][:5]:
        flash(f"{error['string_id']}: {error['message']}", "error")
    if request.form.get("go") == "next":
        return _back(language, page=(_filters()["page"] or 1) + 1)
    return _back(language)


@ui_bp.route("/translations/<language>/complete", methods=["POST"])
@login_required_web
def translation_complete(language):
    language = _language(language)
    try:
        review = Reviews.start(language, current_user)
        Reviews.complete(review.id, current_user)
    except ForbiddenError:
        abort(403)
    except (DomainError, ValueError) as exc:
        flash(str(exc), "error")
        return _back(language, state="unanswered")
    flash(
        "Review completed. Thank you - an Administrator or StCd Owner now decides on your "
        "proposals.",
        "success",
    )
    return redirect(url_for("ui.translations_overview"))


@ui_bp.route("/translations/<language>/upload", methods=["POST"])
@login_required_web
def translation_upload(language):
    language = _language(language)
    upload = request.files.get("sheet")
    if upload is None or not upload.filename:
        flash("Choose the completed sheet (.xlsx).", "error")
        return _back(language)
    try:
        review = Reviews.start(language, current_user)
        result = Reviews.import_sheet(review.id, upload.read(), current_user)
    except ForbiddenError:
        abort(403)
    except (DomainError, ValueError) as exc:
        flash(str(exc), "error")
        return _back(language)
    flash(
        f"Read {result['rows_read']} row(s) of the sheet, saved {result['saved']} answer(s).",
        "success",
    )
    for error in result["errors"][:5]:
        flash(f"{error['string_id']}: {error['message']}", "error")
    return _back(language)


@ui_bp.route("/translations/<language>/sheet.xlsx")
@login_required_web
def translation_sheet(language):
    language = _language(language)
    if not (Reviews.can_review(current_user, language) or Reviews.is_manager(current_user)):
        abort(403)
    return Response(
        build_sheet(language, effective(language)),
        mimetype=_XLSX,
        headers={"Content-Disposition": f"attachment; filename=translation-review-{language}.xlsx"},
    )


# ------------------------------------------------------------------ managers
def _manager(language: str) -> str:
    language = _language(language)
    if not Reviews.is_manager(current_user):
        abort(403)
    return language


@ui_bp.route("/translations/<language>/decisions")
@login_required_web
def translation_decisions(language):
    language = _manager(language)
    data = Reviews.decisions(language)
    assigned = {
        r["id"]
        for r in Reviews.overview(current_user)
        if r["code"] == language
        for r in r["reviewers"]
    }
    candidates = (
        db.session.query(User)
        .filter(User.is_active == 1, ~User.id.in_(assigned or {0}))
        .order_by(User.full_name)
        .all()
    )
    return render_template(
        "translations/decisions.html",
        language=language,
        title=f"{label(language)} - {ENGLISH_NAMES[language]}",
        rtl=is_rtl(language),
        data=data,
        reviewers=[r for r in Reviews.overview(current_user) if r["code"] == language][0][
            "reviewers"
        ],
        candidates=candidates,
        me=current_user.id,
    )


def _act(language: str, call, done: str):
    try:
        call()
    except ForbiddenError as exc:
        flash(str(exc), "error")
    except (NotFoundError, DomainError, ValueError) as exc:
        flash(str(exc), "error")
    else:
        flash(done, "success")
    return redirect(url_for("ui.translation_decisions", language=language))


@ui_bp.route("/translations/<language>/assign", methods=["POST"])
@login_required_web
def translation_assign(language):
    language = _manager(language)
    user_id = request.form.get("user_id", type=int)
    return _act(
        language, lambda: Reviews.assign(language, user_id or 0, current_user), "Reviewer assigned."
    )


@ui_bp.route("/translations/<language>/unassign", methods=["POST"])
@login_required_web
def translation_unassign(language):
    language = _manager(language)
    user_id = request.form.get("user_id", type=int)
    return _act(
        language,
        lambda: Reviews.unassign(language, user_id or 0, current_user),
        "Reviewer removed.",
    )


@ui_bp.route("/translations/<language>/decide/<int:item_id>", methods=["POST"])
@login_required_web
def translation_decide(language, item_id):
    language = _manager(language)
    action = request.form.get("action", "")
    text = request.form.get("text")
    return _act(
        language, lambda: Reviews.decide(item_id, action, current_user, text), "Decision saved."
    )


@ui_bp.route("/translations/<language>/override/<int:override_id>/remove", methods=["POST"])
@login_required_web
def translation_override_remove(language, override_id):
    language = _manager(language)
    return _act(
        language,
        lambda: Reviews.remove_override(override_id, current_user),
        "Override removed: the shipped text is shown again.",
    )

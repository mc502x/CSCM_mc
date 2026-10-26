"""S45 Terminology, S46 Terminology of one language, S47 Terminology check (docs/26-translations.md,
docs/03-srs.md FR-166). The technical nomenclature has its own section, apart from the interface
translations of S42 to S44: the technical staff translate the terms, a second person approves."""

from flask import Response, abort, flash, redirect, render_template, request, url_for

from app.auth.decorators import current_user, login_required_web
from app.domain.errors import DomainError, ForbiddenError, NotFoundError
from app.i18n import translate as _
from app.services.terminology_service import TerminologyService as Terms
from app.terminology_seed import CATEGORIES
from app.translation_catalogue import ENGLISH_NAMES, is_rtl, label
from app.ui import ui_bp

_XLSX = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"


def _language(code: str) -> str:
    if code not in ENGLISH_NAMES or code == "en":
        abort(404)
    return code


def _filters() -> dict:
    return {
        "category": request.values.get("category", ""),
        "q": (request.values.get("q") or "").strip(),
        "state": request.values.get("state", ""),
    }


def _act(call, done: str, target: str, **values):
    try:
        call()
    except ForbiddenError as exc:
        flash(_(str(exc)), "error")
    except (NotFoundError, DomainError, ValueError) as exc:
        flash(_(str(exc)), "error")
    else:
        flash(done, "success")
    return redirect(url_for(target, **values))


@ui_bp.route("/terminology")
@login_required_web
def terminology_index():
    f = _filters()
    return render_template(
        "terminology/index.html",
        coverage=Terms.coverage(),
        terms=Terms.terms(
            category=f["category"], q=f["q"], include_inactive=Terms.can_manage(current_user)
        ),
        categories=CATEGORIES,
        f=f,
        manage=Terms.can_manage(current_user),
        label=label,
        names=ENGLISH_NAMES,
    )


@ui_bp.route("/terminology/terms", methods=["POST"])
@login_required_web
def terminology_term_new():
    form = request.form
    return _act(
        lambda: Terms.create_term(
            code=form.get("code", ""),
            english=form.get("english", ""),
            category=form.get("category", ""),
            definition=form.get("definition", ""),
            keep_english=bool(form.get("keep_english")),
            actor=current_user,
        ),
        _("Term added."),
        "ui.terminology_index",
    )


@ui_bp.route("/terminology/terms/<int:term_id>", methods=["POST"])
@login_required_web
def terminology_term_update(term_id):
    form = request.form
    return _act(
        lambda: Terms.update_term(
            term_id,
            english=form.get("english", ""),
            category=form.get("category", ""),
            definition=form.get("definition", ""),
            keep_english=bool(form.get("keep_english")),
            is_active=bool(form.get("is_active")),
            actor=current_user,
        ),
        _("Term saved."),
        "ui.terminology_index",
    )


@ui_bp.route("/terminology/<language>")
@login_required_web
def terminology_language(language):
    language = _language(language)
    f = _filters()
    return render_template(
        "terminology/language.html",
        language=language,
        title=f"{label(language)} - {ENGLISH_NAMES[language]}",
        rtl=is_rtl(language),
        rows=Terms.worklist(language, category=f["category"], q=f["q"], state=f["state"]),
        categories=CATEGORIES,
        f=f,
        propose=Terms.can_propose(current_user),
        approve=Terms.can_approve(current_user),
        me=current_user.id,
    )


@ui_bp.route("/terminology/<language>/save", methods=["POST"])
@login_required_web
def terminology_save(language):
    language = _language(language)
    saved, problems = 0, []
    for term_id in request.form.getlist("term"):
        try:
            tid = int(term_id)
        except ValueError:
            continue
        text = request.form.get(f"t_{tid}", "")
        note = request.form.get(f"n_{tid}", "")
        if not text.strip():
            continue
        try:
            if Terms.propose(tid, language, text, note, current_user) is not None:
                saved += 1
        except ForbiddenError as exc:
            abort(403, str(exc))
        except (NotFoundError, DomainError, ValueError) as exc:
            problems.append(str(exc))
    if saved:
        flash(_("%(n)s translation(s) saved as drafts.", n=saved), "success")
    for problem in problems[:5]:
        flash(_(problem), "error")
    return redirect(url_for("ui.terminology_language", language=language, **_keep()))


def _keep() -> dict:
    return {k: v for k, v in _filters().items() if v}


@ui_bp.route("/terminology/translations/<int:translation_id>/approve", methods=["POST"])
@login_required_web
def terminology_approve(translation_id):
    language = request.form.get("language", "")
    return _act(
        lambda: Terms.approve(translation_id, current_user),
        _("Translation approved."),
        "ui.terminology_language",
        language=_language(language),
        **_keep(),
    )


@ui_bp.route("/terminology/translations/<int:translation_id>/reject", methods=["POST"])
@login_required_web
def terminology_reject(translation_id):
    language = request.form.get("language", "")
    return _act(
        lambda: Terms.reject(
            translation_id,
            request.form.get(f"n_{request.args.get('term', type=int)}"),
            current_user,
        ),
        _("Sent back to draft."),
        "ui.terminology_language",
        language=_language(language),
        **_keep(),
    )


@ui_bp.route("/terminology/<language>/approve-all", methods=["POST"])
@login_required_web
def terminology_approve_all(language):
    language = _language(language)
    try:
        done = Terms.approve_all(language, current_user)
    except ForbiddenError as exc:
        flash(_(str(exc)), "error")
    else:
        flash(_("%(n)s translation(s) approved.", n=done), "success")
    return redirect(url_for("ui.terminology_language", language=language))


@ui_bp.route("/terminology/<language>/check")
@login_required_web
def terminology_check(language):
    language = _language(language)
    return render_template(
        "terminology/check.html",
        language=language,
        title=f"{label(language)} - {ENGLISH_NAMES[language]}",
        rtl=is_rtl(language),
        findings=Terms.check(language),
    )


@ui_bp.route("/terminology/export.csv")
@ui_bp.route("/terminology/<language>/export.csv")
@login_required_web
def terminology_export_csv(language=None):
    if language:
        language = _language(language)
    name = f"terminology-{language}.csv" if language else "terminology.csv"
    return Response(
        Terms.export_csv(language),
        mimetype="text/csv",
        headers={"Content-Disposition": f"attachment; filename={name}"},
    )


@ui_bp.route("/terminology/export.xlsx")
@ui_bp.route("/terminology/<language>/export.xlsx")
@login_required_web
def terminology_export_xlsx(language=None):
    if language:
        language = _language(language)
    name = f"terminology-{language}.xlsx" if language else "terminology.xlsx"
    return Response(
        Terms.export_xlsx(language),
        mimetype=_XLSX,
        headers={"Content-Disposition": f"attachment; filename={name}"},
    )

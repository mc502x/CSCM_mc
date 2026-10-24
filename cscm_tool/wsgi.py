from app import create_app

app = create_app()


def _report_translation_impact() -> None:
    """A new version may have changed the interface text or the nomenclature: tell the StCd Owner
    (once per change; FR-178). Never stops the server from starting."""
    try:
        with app.app_context():
            from app.services.translation_impact_service import TranslationImpactService

            TranslationImpactService.notify_catalogue_changes()
    except Exception:  # noqa: BLE001
        app.logger.exception("translation impact could not be reported at start")


_report_translation_impact()

if __name__ == "__main__":
    app.run()

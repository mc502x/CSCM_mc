# 24. Test Report — CSCM Tool

> **Generated file — do not edit by hand.** Regenerate with `python cscm_tool/scripts/generate_test_report.py` after every software change (Definition of Done, 15-development-standards.md). It runs the complete pytest suite, measures coverage, runs the static quality gates, and appends the run to the history below.

## 1. Run summary

| | |
|---|---|
| **Verdict** | **PASS** |
| Generated (UTC) | 2026-10-23 23:47:17 |
| Branch / commit | `dev` @ `9f038bc` +uncommitted changes |
| Test order | `file` |
| Tests | **848** run — 848 passed, 0 failed, 0 skipped |
| Duration | 748.2 s |
| Line coverage (`app/`) | **93%** (10908 of 11764 statements) |
| Python / platform | 3.12.10 / Windows 11 |
| pytest summary line | `functional: 839 passed, 9 deselected, 1 warning in 710.71s (0:11:50)  |  performance: 9 passed, 1 warning in 49.44s` |

## 2. Results by suite

| Suite | Tests | Passed | Failed | Skipped | Time |
|---|---|---|---|---|---|
| unit | 74 | 74 | 0 | 0 | 3.1 s |
| integration | 570 | 570 | 0 | 0 | 505.3 s |
| system | 195 | 195 | 0 | 0 | 190.6 s |
| performance | 9 | 9 | 0 | 0 | 49.2 s |

## 3. Static quality and security gates

| Gate | Result | Detail |
|---|---|---|
| black --check | PASS | 232 files would be left unchanged. |
| ruff check | PASS | All checks passed! |
| mypy | PASS | Success: no issues found in 145 source files |
| bandit -r app | PASS | [tester]	WARNING	nosec encountered (B324), but no failed test on line 75 |
| pip-audit | PASS | runtime packages with advisories: none; dev-only advisories (accepted): black, pytest, starlette |

## 4. Measured performance (NFR-001, NFR-004, TC-024, TC-025)

| Test | Measured |
|---|---|
| `test_search_and_read_latency_at_20000_revisions` | read_p95_ms = 3.7, revisions = 20000, search_median_ms = 50.2, search_p95_ms = 65.1, speed_factor = 1.0 |
| `test_export_of_5000_records_within_target[csv-5]` | export_seconds = 0.63, limit_seconds = 5, records = 5000, speed_factor = 1.0 |
| `test_export_of_5000_records_within_target[json-5]` | export_seconds = 0.84, limit_seconds = 5, records = 5000, speed_factor = 1.0 |
| `test_export_of_5000_records_within_target[xlsx-15]` | export_seconds = 1.97, limit_seconds = 15, records = 5000, speed_factor = 1.0 |
| `test_export_of_5000_records_within_target[pdf-15]` | export_seconds = 5.54, limit_seconds = 15, records = 5000, speed_factor = 1.0 |
| `test_concurrent_identifier_allocation_in_one_group` | allocation_p95_ms = 109.8, speed_factor = 1.0, submissions = 64 |
| `test_fifty_concurrent_users_are_served_without_errors` | p95_ms_50_users = 79.4, speed_factor = 1.0 |
| `test_export_issues_a_constant_number_of_queries` | statements_for_two_500_row_exports = 27 |

Targets: search p95 ≤ 500 ms and single read p95 ≤ 200 ms at 20,000 revisions; CSV/JSON export of 5,000 records ≤ 5 s, XLSX/PDF ≤ 15 s; 50 concurrent users keep the 500 ms search target; identifier allocation under contention correct and gap-free.

## 5. Coverage by module

| Module | Statements | Missed | Coverage |
|---|---|---|---|
| `app/__init__.py` | 72 | 0 | 100% |
| `app/api/__init__.py` | 0 | 0 | 100% |
| `app/api/v1/__init__.py` | 3 | 0 | 100% |
| `app/api/v1/_errors.py` | 20 | 2 | 90% |
| `app/api/v1/audit_routes.py` | 12 | 0 | 100% |
| `app/api/v1/auth_routes.py` | 60 | 4 | 93% |
| `app/api/v1/change_request_routes.py` | 136 | 11 | 92% |
| `app/api/v1/domain_signoff_routes.py` | 60 | 3 | 95% |
| `app/api/v1/export_routes.py` | 74 | 3 | 96% |
| `app/api/v1/governance_routes.py` | 244 | 3 | 99% |
| `app/api/v1/health_routes.py` | 29 | 2 | 93% |
| `app/api/v1/import_routes.py` | 93 | 11 | 88% |
| `app/api/v1/lookup_routes.py` | 70 | 1 | 99% |
| `app/api/v1/operations_routes.py` | 165 | 0 | 100% |
| `app/api/v1/publication_routes.py` | 196 | 7 | 96% |
| `app/api/v1/release_routes.py` | 79 | 8 | 90% |
| `app/api/v1/revision_routes.py` | 26 | 3 | 88% |
| `app/api/v1/serializers.py` | 58 | 0 | 100% |
| `app/api/v1/st_import_routes.py` | 71 | 2 | 97% |
| `app/api/v1/status_code_routes.py` | 194 | 18 | 91% |
| `app/api/v1/user_routes.py` | 96 | 7 | 93% |
| `app/audit/__init__.py` | 0 | 0 | 100% |
| `app/audit_chain.py` | 134 | 7 | 95% |
| `app/audit_hash.py` | 10 | 0 | 100% |
| `app/auth/__init__.py` | 0 | 0 | 100% |
| `app/auth/decorators.py` | 122 | 3 | 98% |
| `app/auth/password.py` | 30 | 0 | 100% |
| `app/auth/providers.py` | 32 | 1 | 97% |
| `app/auth/rate_limit.py` | 34 | 0 | 100% |
| `app/auth/roles.py` | 27 | 0 | 100% |
| `app/auth/windows.py` | 43 | 2 | 95% |
| `app/cli.py` | 74 | 4 | 95% |
| `app/config.py` | 57 | 0 | 100% |
| `app/db_modes.py` | 15 | 0 | 100% |
| `app/domain/__init__.py` | 0 | 0 | 100% |
| `app/domain/authz.py` | 5 | 0 | 100% |
| `app/domain/errors.py` | 29 | 0 | 100% |
| `app/domain/lifecycle.py` | 19 | 0 | 100% |
| `app/errors.py` | 24 | 3 | 88% |
| `app/export/__init__.py` | 0 | 0 | 100% |
| `app/export/csv_exporter.py` | 17 | 0 | 100% |
| `app/export/full_database_exporter.py` | 22 | 1 | 95% |
| `app/export/json_exporter.py` | 3 | 0 | 100% |
| `app/export/offline_bundle.py` | 13 | 0 | 100% |
| `app/export/pdf_exporter.py` | 206 | 3 | 99% |
| `app/export/xlsx_exporter.py` | 20 | 0 | 100% |
| `app/extensions.py` | 9 | 0 | 100% |
| `app/help_content.py` | 6 | 0 | 100% |
| `app/i18n.py` | 46 | 2 | 96% |
| `app/i18n_ar.py` | 1 | 0 | 100% |
| `app/i18n_de.py` | 3 | 0 | 100% |
| `app/i18n_eu.py` | 4 | 0 | 100% |
| `app/i18n_extra.py` | 10 | 0 | 100% |
| `app/i18n_generated.py` | 13 | 0 | 100% |
| `app/i18n_in.py` | 4 | 0 | 100% |
| `app/i18n_messages.py` | 26 | 0 | 100% |
| `app/importers/__init__.py` | 0 | 0 | 100% |
| `app/importers/stcd.py` | 233 | 8 | 97% |
| `app/logging_config.py` | 45 | 0 | 100% |
| `app/models/__init__.py` | 11 | 0 | 100% |
| `app/models/audit.py` | 16 | 0 | 100% |
| `app/models/change_request.py` | 111 | 0 | 100% |
| `app/models/export_job.py` | 38 | 0 | 100% |
| `app/models/import_job.py` | 30 | 0 | 100% |
| `app/models/lookup.py` | 87 | 0 | 100% |
| `app/models/operations.py` | 121 | 0 | 100% |
| `app/models/release.py` | 30 | 0 | 100% |
| `app/models/status_code.py` | 144 | 0 | 100% |
| `app/models/terminology.py` | 25 | 0 | 100% |
| `app/models/translation.py` | 42 | 0 | 100% |
| `app/models/user.py` | 33 | 0 | 100% |
| `app/observability.py` | 102 | 12 | 88% |
| `app/repositories/__init__.py` | 0 | 0 | 100% |
| `app/repositories/audit_repository.py` | 22 | 1 | 95% |
| `app/repositories/base.py` | 20 | 1 | 95% |
| `app/repositories/change_request_repository.py` | 26 | 0 | 100% |
| `app/repositories/fts.py` | 35 | 2 | 94% |
| `app/repositories/release_repository.py` | 4 | 0 | 100% |
| `app/repositories/status_code_repository.py` | 82 | 3 | 96% |
| `app/repositories/user_repository.py` | 33 | 1 | 97% |
| `app/schema_sql.py` | 45 | 1 | 98% |
| `app/security_headers.py` | 15 | 0 | 100% |
| `app/services/__init__.py` | 0 | 0 | 100% |
| `app/services/attachment_service.py` | 106 | 11 | 90% |
| `app/services/audience_service.py` | 31 | 1 | 97% |
| `app/services/audit_service.py` | 23 | 0 | 100% |
| `app/services/auth_service.py` | 108 | 9 | 92% |
| `app/services/backup_service.py` | 131 | 7 | 95% |
| `app/services/change_request_service.py` | 264 | 13 | 95% |
| `app/services/change_set_service.py` | 120 | 15 | 88% |
| `app/services/delegation_service.py` | 86 | 6 | 93% |
| `app/services/domain_signoff_service.py` | 91 | 5 | 95% |
| `app/services/duplicate_service.py` | 41 | 1 | 98% |
| `app/services/export_profile_service.py` | 97 | 19 | 80% |
| `app/services/export_service.py` | 240 | 8 | 97% |
| `app/services/field_review_service.py` | 126 | 12 | 90% |
| `app/services/health_report_service.py` | 81 | 4 | 95% |
| `app/services/hub_consolidation_service.py` | 106 | 8 | 92% |
| `app/services/import_service.py` | 464 | 43 | 91% |
| `app/services/integration_service.py` | 192 | 7 | 96% |
| `app/services/kpi_service.py` | 72 | 7 | 90% |
| `app/services/legacy_mapping_service.py` | 70 | 6 | 91% |
| `app/services/lookup_admin_service.py` | 96 | 5 | 95% |
| `app/services/lookup_service.py` | 33 | 4 | 88% |
| `app/services/mail_service.py` | 30 | 3 | 90% |
| `app/services/manifest_service.py` | 46 | 1 | 98% |
| `app/services/notification_service.py` | 98 | 1 | 99% |
| `app/services/numbering_service.py` | 78 | 3 | 96% |
| `app/services/occurrence_service.py` | 88 | 7 | 92% |
| `app/services/reference_service.py` | 72 | 11 | 85% |
| `app/services/release_notes_service.py` | 115 | 9 | 92% |
| `app/services/release_service.py` | 133 | 6 | 95% |
| `app/services/revision_diff_service.py` | 35 | 0 | 100% |
| `app/services/saved_search_service.py` | 61 | 0 | 100% |
| `app/services/settings_service.py` | 69 | 7 | 90% |
| `app/services/sla_service.py` | 57 | 0 | 100% |
| `app/services/software_version_service.py` | 48 | 1 | 98% |
| `app/services/st_import_service.py` | 524 | 77 | 85% |
| `app/services/status_code_service.py` | 461 | 22 | 95% |
| `app/services/terminology_service.py` | 286 | 21 | 93% |
| `app/services/translation_review_service.py` | 292 | 31 | 89% |
| `app/services/translation_service.py` | 123 | 11 | 91% |
| `app/services/user_service.py` | 162 | 3 | 98% |
| `app/services/validation.py` | 77 | 9 | 88% |
| `app/status_code_fields.py` | 138 | 5 | 96% |
| `app/terminology_seed.py` | 14 | 1 | 93% |
| `app/terminology_seed_process.py` | 2 | 0 | 100% |
| `app/terminology_seed_product.py` | 1 | 0 | 100% |
| `app/translation_catalogue.py` | 116 | 0 | 100% |
| `app/ui/__init__.py` | 61 | 6 | 90% |
| `app/ui/admin_views.py` | 170 | 21 | 88% |
| `app/ui/auth_views.py` | 95 | 26 | 73% |
| `app/ui/change_request_views.py` | 192 | 22 | 89% |
| `app/ui/dashboard_views.py` | 34 | 0 | 100% |
| `app/ui/export_views.py` | 23 | 1 | 96% |
| `app/ui/governance_views.py` | 255 | 47 | 82% |
| `app/ui/import_views.py` | 133 | 16 | 88% |
| `app/ui/insight_views.py` | 118 | 17 | 86% |
| `app/ui/publication_views.py` | 175 | 47 | 73% |
| `app/ui/release_views.py` | 91 | 29 | 68% |
| `app/ui/status_code_views.py` | 286 | 55 | 81% |
| `app/ui/terminology_views.py` | 114 | 5 | 96% |
| `app/ui/translation_views.py` | 138 | 4 | 97% |
| `app/utils.py` | 9 | 0 | 100% |

## 6. Traceability evidence check

`docs/20-traceability-matrix.md` cites 543 test names / test files as evidence. **543 resolve** to a test that exists; **0 are stale**.

## 6a. Requirement coverage

The specification defines **220** requirement ids (FR, NFR, BR in `03-srs.md`, SEC in `11-security-architecture.md`, AUD in `12-audit-compliance.md`). **181** are cited by at least one test (module docstring, test docstring or test name); **38** more are marked covered, with the tests named, in `20-traceability-matrix.md`; **1** are marked there as out of scope or needing a person (`NFR-002`). **0 are not accounted for**.

## 7. Failures

None.

## 8. Complete test inventory

Every executed test, grouped by file, with its outcome, duration, and the requirement IDs it cites (module/test docstring or name). Parametrised cases appear individually.

### `tests/unit/test_lifecycle.py` — 52 tests, 52 passed

_TC-001 / TC-002 / BR-004: the 7-state lifecycle and its guard._

| Result | Test | Purpose | Requirements | Time |
|---|---|---|---|---|
| ✅ | `test_every_defined_transition_is_accepted[APPROVED-RELEASED]` |  | BR-004, TC-001, TC-002 | 0.00 s |
| ✅ | `test_every_defined_transition_is_accepted[DEPRECATED-ARCHIVED]` |  | BR-004, TC-001, TC-002 | 0.00 s |
| ✅ | `test_every_defined_transition_is_accepted[DEPRECATED-RELEASED]` |  | BR-004, TC-001, TC-002 | 0.00 s |
| ✅ | `test_every_defined_transition_is_accepted[DRAFT-REVIEW]` |  | BR-004, TC-001, TC-002 | 0.00 s |
| ✅ | `test_every_defined_transition_is_accepted[PENDING_APPROVAL-APPROVED]` |  | BR-004, TC-001, TC-002 | 0.00 s |
| ✅ | `test_every_defined_transition_is_accepted[PENDING_APPROVAL-DEPRECATED]` |  | BR-004, TC-001, TC-002 | 0.00 s |
| ✅ | `test_every_defined_transition_is_accepted[PENDING_APPROVAL-DRAFT]` |  | BR-004, TC-001, TC-002 | 0.00 s |
| ✅ | `test_every_defined_transition_is_accepted[REVIEW-DRAFT]` |  | BR-004, TC-001, TC-002 | 0.00 s |
| ✅ | `test_every_defined_transition_is_accepted[REVIEW-PENDING_APPROVAL]` |  | BR-004, TC-001, TC-002 | 0.00 s |
| ✅ | `test_every_other_pairwise_transition_is_rejected[APPROVED-APPROVED]` |  | BR-004, TC-001, TC-002 | 0.00 s |
| ✅ | `test_every_other_pairwise_transition_is_rejected[APPROVED-ARCHIVED]` |  | BR-004, TC-001, TC-002 | 0.00 s |
| ✅ | `test_every_other_pairwise_transition_is_rejected[APPROVED-DEPRECATED]` |  | BR-004, TC-001, TC-002 | 0.00 s |
| ✅ | `test_every_other_pairwise_transition_is_rejected[APPROVED-DRAFT]` |  | BR-004, TC-001, TC-002 | 0.00 s |
| ✅ | `test_every_other_pairwise_transition_is_rejected[APPROVED-PENDING_APPROVAL]` |  | BR-004, TC-001, TC-002 | 0.00 s |
| ✅ | `test_every_other_pairwise_transition_is_rejected[APPROVED-REVIEW]` |  | BR-004, TC-001, TC-002 | 0.00 s |
| ✅ | `test_every_other_pairwise_transition_is_rejected[ARCHIVED-APPROVED]` |  | BR-004, TC-001, TC-002 | 0.00 s |
| ✅ | `test_every_other_pairwise_transition_is_rejected[ARCHIVED-ARCHIVED]` |  | BR-004, TC-001, TC-002 | 0.00 s |
| ✅ | `test_every_other_pairwise_transition_is_rejected[ARCHIVED-DEPRECATED]` |  | BR-004, TC-001, TC-002 | 0.00 s |
| ✅ | `test_every_other_pairwise_transition_is_rejected[ARCHIVED-DRAFT]` |  | BR-004, TC-001, TC-002 | 0.00 s |
| ✅ | `test_every_other_pairwise_transition_is_rejected[ARCHIVED-PENDING_APPROVAL]` |  | BR-004, TC-001, TC-002 | 0.00 s |
| ✅ | `test_every_other_pairwise_transition_is_rejected[ARCHIVED-RELEASED]` |  | BR-004, TC-001, TC-002 | 0.00 s |
| ✅ | `test_every_other_pairwise_transition_is_rejected[ARCHIVED-REVIEW]` |  | BR-004, TC-001, TC-002 | 0.00 s |
| ✅ | `test_every_other_pairwise_transition_is_rejected[DEPRECATED-APPROVED]` |  | BR-004, TC-001, TC-002 | 0.00 s |
| ✅ | `test_every_other_pairwise_transition_is_rejected[DEPRECATED-DEPRECATED]` |  | BR-004, TC-001, TC-002 | 0.00 s |
| ✅ | `test_every_other_pairwise_transition_is_rejected[DEPRECATED-DRAFT]` |  | BR-004, TC-001, TC-002 | 0.00 s |
| ✅ | `test_every_other_pairwise_transition_is_rejected[DEPRECATED-PENDING_APPROVAL]` |  | BR-004, TC-001, TC-002 | 0.00 s |
| ✅ | `test_every_other_pairwise_transition_is_rejected[DEPRECATED-REVIEW]` |  | BR-004, TC-001, TC-002 | 0.00 s |
| ✅ | `test_every_other_pairwise_transition_is_rejected[DRAFT-APPROVED]` |  | BR-004, TC-001, TC-002 | 0.00 s |
| ✅ | `test_every_other_pairwise_transition_is_rejected[DRAFT-ARCHIVED]` |  | BR-004, TC-001, TC-002 | 0.00 s |
| ✅ | `test_every_other_pairwise_transition_is_rejected[DRAFT-DEPRECATED]` |  | BR-004, TC-001, TC-002 | 0.00 s |
| ✅ | `test_every_other_pairwise_transition_is_rejected[DRAFT-DRAFT]` |  | BR-004, TC-001, TC-002 | 0.00 s |
| ✅ | `test_every_other_pairwise_transition_is_rejected[DRAFT-PENDING_APPROVAL]` |  | BR-004, TC-001, TC-002 | 0.00 s |
| ✅ | `test_every_other_pairwise_transition_is_rejected[DRAFT-RELEASED]` |  | BR-004, TC-001, TC-002 | 0.00 s |
| ✅ | `test_every_other_pairwise_transition_is_rejected[PENDING_APPROVAL-ARCHIVED]` |  | BR-004, TC-001, TC-002 | 0.00 s |
| ✅ | `test_every_other_pairwise_transition_is_rejected[PENDING_APPROVAL-PENDING_APPROVAL]` |  | BR-004, TC-001, TC-002 | 0.00 s |
| ✅ | `test_every_other_pairwise_transition_is_rejected[PENDING_APPROVAL-RELEASED]` |  | BR-004, TC-001, TC-002 | 0.00 s |
| ✅ | `test_every_other_pairwise_transition_is_rejected[PENDING_APPROVAL-REVIEW]` |  | BR-004, TC-001, TC-002 | 0.00 s |
| ✅ | `test_every_other_pairwise_transition_is_rejected[RELEASED-APPROVED]` |  | BR-004, TC-001, TC-002 | 0.00 s |
| ✅ | `test_every_other_pairwise_transition_is_rejected[RELEASED-ARCHIVED]` |  | BR-004, TC-001, TC-002 | 0.00 s |
| ✅ | `test_every_other_pairwise_transition_is_rejected[RELEASED-DEPRECATED]` |  | BR-004, TC-001, TC-002 | 0.00 s |
| ✅ | `test_every_other_pairwise_transition_is_rejected[RELEASED-DRAFT]` |  | BR-004, TC-001, TC-002 | 0.00 s |
| ✅ | `test_every_other_pairwise_transition_is_rejected[RELEASED-PENDING_APPROVAL]` |  | BR-004, TC-001, TC-002 | 0.00 s |
| ✅ | `test_every_other_pairwise_transition_is_rejected[RELEASED-RELEASED]` |  | BR-004, TC-001, TC-002 | 0.00 s |
| ✅ | `test_every_other_pairwise_transition_is_rejected[RELEASED-REVIEW]` |  | BR-004, TC-001, TC-002 | 0.00 s |
| ✅ | `test_every_other_pairwise_transition_is_rejected[REVIEW-APPROVED]` |  | BR-004, TC-001, TC-002 | 0.00 s |
| ✅ | `test_every_other_pairwise_transition_is_rejected[REVIEW-ARCHIVED]` |  | BR-004, TC-001, TC-002 | 0.00 s |
| ✅ | `test_every_other_pairwise_transition_is_rejected[REVIEW-DEPRECATED]` |  | BR-004, TC-001, TC-002 | 0.00 s |
| ✅ | `test_every_other_pairwise_transition_is_rejected[REVIEW-RELEASED]` |  | BR-004, TC-001, TC-002 | 0.00 s |
| ✅ | `test_every_other_pairwise_transition_is_rejected[REVIEW-REVIEW]` |  | BR-004, TC-001, TC-002 | 0.00 s |
| ✅ | `test_orm_guard_blocks_an_illegal_status_assignment` |  | BR-004, TC-001, TC-002 | 0.64 s |
| ✅ | `test_terminal_and_gated_states_cannot_be_skipped` |  | BR-004, TC-001, TC-002 | 0.00 s |
| ✅ | `test_there_are_exactly_seven_states` |  | BR-004, TC-001, TC-002 | 0.01 s |

### `tests/unit/test_password.py` — 5 tests, 5 passed

| Result | Test | Purpose | Requirements | Time |
|---|---|---|---|---|
| ✅ | `test_hash_and_verify_round_trip` |  |  | 0.08 s |
| ✅ | `test_policy_accepts_reasonable_password` |  |  | 0.00 s |
| ✅ | `test_policy_rejects_blocklisted_password` |  |  | 0.00 s |
| ✅ | `test_policy_rejects_short_password` |  |  | 0.00 s |
| ✅ | `test_verify_rejects_wrong_password` |  |  | 0.08 s |

### `tests/unit/test_rate_limit.py` — 6 tests, 6 passed

_SEC-004 / I-20: the login rate limiter, backed by the database._

| Result | Test | Purpose | Requirements | Time |
|---|---|---|---|---|
| ✅ | `test_a_refused_attempt_is_not_recorded` |  | NFR-009, SEC-004, TC-050 | 0.29 s |
| ✅ | `test_allows_attempts_under_the_limit` |  | NFR-009, SEC-004, TC-050 | 0.75 s |
| ✅ | `test_attempts_age_out_of_the_window` |  | NFR-009, SEC-004, TC-050 | 0.27 s |
| ✅ | `test_blocks_after_five_username_attempts` |  | NFR-009, SEC-004, TC-050 | 0.27 s |
| ✅ | `test_blocks_after_ten_ip_attempts_across_usernames` |  | NFR-009, SEC-004, TC-050 | 0.31 s |
| ✅ | `test_username_limit_is_case_insensitive` |  | NFR-009, SEC-004, TC-050 | 0.28 s |

### `tests/unit/test_validation.py` — 11 tests, 11 passed

_FR-022, FR-027 field rules from docs/06-data-dictionary.md, v3_

| Result | Test | Purpose | Requirements | Time |
|---|---|---|---|---|
| ✅ | `test_description_too_short` |  | FR-022, FR-027 | 0.00 s |
| ✅ | `test_number_of_times_repeated_must_be_at_least_one` |  | FR-022, FR-027 | 0.00 s |
| ✅ | `test_repeated_over_the_course_format` |  | FR-022, FR-027 | 0.01 s |
| ✅ | `test_reset_delay_rejects_missing_unit` |  | FR-022, FR-027 | 0.00 s |
| ✅ | `test_set_delay_accepts_leading_star_and_units` |  | FR-022, FR-027 | 0.00 s |
| ✅ | `test_set_delay_rejects_missing_unit` |  | FR-022, FR-027 | 0.00 s |
| ✅ | `test_status_category_must_be_error_warning_or_info` |  | FR-022, FR-027 | 0.00 s |
| ✅ | `test_title_must_not_equal_description` |  | FR-022, FR-027 | 0.00 s |
| ✅ | `test_title_too_short` |  | FR-022, FR-027 | 0.00 s |
| ✅ | `test_turbine_platforms_required_when_provided_empty` |  | FR-022, FR-027 | 0.00 s |
| ✅ | `test_valid_data_has_no_errors` |  | FR-022, FR-027 | 0.00 s |

### `tests/integration/test_audit_chain_and_ops.py` — 27 tests, 27 passed

_I-18 tamper-evident audit log, I-09 verified backups, I-21 readiness / metrics / log file._

| Result | Test | Purpose | Requirements | Time |
|---|---|---|---|---|
| ✅ | `test_a_backup_is_written_verified_and_recorded` |  | AUD-072, AUD-073, AUD-074, AUD-075, BR-020, FR-150, FR-151, FR-152, FR-153, NFR-011, NFR-012, SEC-029, SEC-030, TC-044 | 0.66 s |
| ✅ | `test_a_configured_key_makes_the_chain_keyed` |  | AUD-072, AUD-073, AUD-074, AUD-075, BR-020, FR-150, FR-151, FR-152, FR-153, NFR-011, NFR-012, SEC-029, SEC-030, TC-044 | 0.62 s |
| ✅ | `test_a_corrupt_backup_fails_verification` |  | AUD-072, AUD-073, AUD-074, AUD-075, BR-020, FR-150, FR-151, FR-152, FR-153, NFR-011, NFR-012, SEC-029, SEC-030, TC-044 | 0.68 s |
| ✅ | `test_a_forged_row_cannot_be_repaired_without_the_key` |  | AUD-072, AUD-073, AUD-074, AUD-075, BR-020, FR-150, FR-151, FR-152, FR-153, NFR-011, NFR-012, SEC-029, SEC-030, TC-044 | 0.57 s |
| ✅ | `test_a_metrics_token_admits_an_address_outside_the_networks` |  | AUD-072, AUD-073, AUD-074, AUD-075, BR-020, FR-150, FR-151, FR-152, FR-153, NFR-011, NFR-012, SEC-029, SEC-030, TC-044 | 0.27 s |
| ✅ | `test_a_removed_row_breaks_the_link` |  | AUD-072, AUD-073, AUD-074, AUD-075, BR-020, FR-150, FR-151, FR-152, FR-153, NFR-011, NFR-012, SEC-029, SEC-030, TC-044 | 0.64 s |
| ✅ | `test_a_restored_backup_runs_the_application` | The restore drill from docs/14 §5 in miniature: back up, start an app on the copy, log in. | AUD-072, AUD-073, AUD-074, AUD-075, BR-020, FR-150, FR-151, FR-152, FR-153, NFR-011, NFR-012, SEC-029, SEC-030, TC-044 | 0.93 s |
| ✅ | `test_a_tampered_audit_log_inside_a_backup_is_flagged` |  | AUD-072, AUD-073, AUD-074, AUD-075, BR-020, FR-150, FR-151, FR-152, FR-153, NFR-011, NFR-012, SEC-029, SEC-030, TC-044 | 0.66 s |
| ✅ | `test_an_edited_row_is_found_and_named` |  | AUD-072, AUD-073, AUD-074, AUD-075, BR-020, FR-150, FR-151, FR-152, FR-153, NFR-011, NFR-012, SEC-029, SEC-030, TC-044 | 0.72 s |
| ✅ | `test_archive_exports_old_rows_with_a_hash_and_deletes_nothing` |  | AUD-072, AUD-073, AUD-074, AUD-075, BR-020, FR-150, FR-151, FR-152, FR-153, NFR-011, NFR-012, SEC-029, SEC-030, TC-044 | 0.77 s |
| ✅ | `test_archive_with_nothing_old_enough_does_nothing` |  | AUD-072, AUD-073, AUD-074, AUD-075, BR-020, FR-150, FR-151, FR-152, FR-153, NFR-011, NFR-012, SEC-029, SEC-030, TC-044 | 0.64 s |
| ✅ | `test_backup_needs_a_file_database` | An in-memory database cannot be backed up; built explicitly so the test also holds when | AUD-072, AUD-073, AUD-074, AUD-075, BR-020, FR-150, FR-151, FR-152, FR-153, NFR-011, NFR-012, SEC-029, SEC-030, TC-044 | 0.09 s |
| ✅ | `test_cli_audit_verify_fails_with_a_non_zero_exit_when_broken` |  | AUD-072, AUD-073, AUD-074, AUD-075, BR-020, FR-150, FR-151, FR-152, FR-153, NFR-011, NFR-012, SEC-029, SEC-030, TC-044 | 0.77 s |
| ✅ | `test_cli_backup_verify_and_audit_commands` |  | AUD-072, AUD-073, AUD-074, AUD-075, BR-020, FR-150, FR-151, FR-152, FR-153, NFR-011, NFR-012, SEC-029, SEC-030, TC-044 | 0.73 s |
| ✅ | `test_every_audit_row_is_chained_to_its_predecessor` |  | AUD-072, AUD-073, AUD-074, AUD-075, BR-020, FR-150, FR-151, FR-152, FR-153, NFR-011, NFR-012, SEC-029, SEC-030, TC-044 | 1.34 s |
| ✅ | `test_metrics_are_refused_outside_the_allowed_networks` |  | AUD-072, AUD-073, AUD-074, AUD-075, BR-020, FR-150, FR-151, FR-152, FR-153, NFR-011, NFR-012, SEC-029, SEC-030, TC-044 | 0.36 s |
| ✅ | `test_metrics_count_requests_and_hold_no_business_data` |  | AUD-072, AUD-073, AUD-074, AUD-075, BR-020, FR-150, FR-151, FR-152, FR-153, NFR-011, NFR-012, SEC-029, SEC-030, TC-044 | 0.64 s |
| ✅ | `test_only_the_newest_generations_are_kept` |  | AUD-072, AUD-073, AUD-074, AUD-075, BR-020, FR-150, FR-151, FR-152, FR-153, NFR-011, NFR-012, SEC-029, SEC-030, TC-044 | 0.85 s |
| ✅ | `test_ready_is_503_when_the_chain_is_broken_or_the_schema_outdated` |  | AUD-072, AUD-073, AUD-074, AUD-075, BR-020, FR-150, FR-151, FR-152, FR-153, NFR-011, NFR-012, SEC-029, SEC-030, TC-044 | 0.75 s |
| ✅ | `test_ready_needs_no_login_and_reveals_no_business_data` |  | AUD-072, AUD-073, AUD-074, AUD-075, BR-020, FR-150, FR-151, FR-152, FR-153, NFR-011, NFR-012, SEC-029, SEC-030, TC-044 | 0.31 s |
| ✅ | `test_ready_reports_ok_and_degraded_by_backup_state` |  | AUD-072, AUD-073, AUD-074, AUD-075, BR-020, FR-150, FR-151, FR-152, FR-153, NFR-011, NFR-012, SEC-029, SEC-030, TC-044 | 0.88 s |
| ✅ | `test_requests_are_logged_to_the_configured_file` |  | AUD-072, AUD-073, AUD-074, AUD-075, BR-020, FR-150, FR-151, FR-152, FR-153, NFR-011, NFR-012, SEC-029, SEC-030, TC-044 | 0.09 s |
| ✅ | `test_rows_without_hashes_before_the_chain_started_are_tolerated` |  | AUD-072, AUD-073, AUD-074, AUD-075, BR-020, FR-150, FR-151, FR-152, FR-153, NFR-011, NFR-012, SEC-029, SEC-030, TC-044 | 0.48 s |
| ✅ | `test_the_append_only_triggers_still_stop_edits_inside_the_application` |  | AUD-072, AUD-073, AUD-074, AUD-075, BR-020, FR-150, FR-151, FR-152, FR-153, NFR-011, NFR-012, SEC-029, SEC-030, TC-044 | 0.65 s |
| ✅ | `test_the_hash_is_reproducible_from_the_stored_fields` |  | AUD-072, AUD-073, AUD-074, AUD-075, BR-020, FR-150, FR-151, FR-152, FR-153, NFR-011, NFR-012, SEC-029, SEC-030, TC-044 | 0.65 s |
| ✅ | `test_truncating_the_tail_is_caught_by_the_anchor` |  | AUD-072, AUD-073, AUD-074, AUD-075, BR-020, FR-150, FR-151, FR-152, FR-153, NFR-011, NFR-012, SEC-029, SEC-030, TC-044 | 0.66 s |
| ✅ | `test_verify_tail_detects_recent_tampering_cheaply` |  | AUD-072, AUD-073, AUD-074, AUD-075, BR-020, FR-150, FR-151, FR-152, FR-153, NFR-011, NFR-012, SEC-029, SEC-030, TC-044 | 0.64 s |

### `tests/integration/test_audit_coverage.py` — 7 tests, 7 passed

_FR-056, FR-070, FR-072, FR-073, NFR-006, TC-015, TC-015a: the audit trail_

| Result | Test | Purpose | Requirements | Time |
|---|---|---|---|---|
| ✅ | `test_audit_log_entries_cannot_be_updated_or_deleted` | FR-072: append-only at the database layer, not just by omission. | FR-072 | 0.29 s |
| ✅ | `test_each_lifecycle_action_is_audited_exactly_once` | TC-015: one entry per state-changing action across the whole lifecycle. | TC-015 | 1.35 s |
| ✅ | `test_import_lifecycle_is_audited` |  | FR-056, FR-070, FR-072, FR-073, NFR-006, TC-015, TC-015a | 0.53 s |
| ✅ | `test_sandbox_delete_keeps_full_snapshot_and_creation_entry` | TC-015a / FR-056 / FR-073. | FR-056, FR-073, TC-015a | 0.66 s |
| ✅ | `test_subgroup_creation_is_audited_as_subgroup_create` |  | FR-056, FR-070, FR-072, FR-073, NFR-006, TC-015, TC-015a | 0.36 s |
| ✅ | `test_unexpected_import_failure_marks_job_failed_and_is_audited` |  | FR-056, FR-070, FR-072, FR-073, NFR-006, TC-015, TC-015a | 0.41 s |
| ✅ | `test_user_and_auth_events_are_audited` |  | FR-056, FR-070, FR-072, FR-073, NFR-006, TC-015, TC-015a | 0.42 s |

### `tests/integration/test_audit_log.py` — 4 tests, 4 passed

_FR-070-FR-071: audit log search, Administrator full access,_

| Result | Test | Purpose | Requirements | Time |
|---|---|---|---|---|
| ✅ | `test_admin_sees_all_entries` |  | FR-070, FR-071 | 0.52 s |
| ✅ | `test_engineer_cannot_view_audit_log` |  | FR-070, FR-071 | 0.36 s |
| ✅ | `test_filter_by_entity_type` |  | FR-070, FR-071 | 0.40 s |
| ✅ | `test_reviewer_only_sees_own_actions` |  | FR-070, FR-071 | 0.51 s |

### `tests/integration/test_auth.py` — 7 tests, 7 passed

_FR-001-FR-004, SEC-001-SEC-004._

| Result | Test | Purpose | Requirements | Time |
|---|---|---|---|---|
| ✅ | `test_deactivated_user_is_immediately_rejected` |  | FR-001, FR-004, SEC-001, SEC-004 | 0.35 s |
| ✅ | `test_five_failed_attempts_locks_the_account` | The 5th consecutive failure both locks the account (SEC-004) and | SEC-004 | 0.56 s |
| ✅ | `test_login_success_returns_user_and_sets_session` |  | FR-001, FR-004, SEC-001, SEC-004 | 0.36 s |
| ✅ | `test_logout_invalidates_session` |  | FR-001, FR-004, SEC-001, SEC-004 | 0.35 s |
| ✅ | `test_me_requires_login` |  | FR-001, FR-004, SEC-001, SEC-004 | 0.27 s |
| ✅ | `test_password_reset_invalidates_existing_session` |  | FR-001, FR-004, SEC-001, SEC-004 | 0.54 s |
| ✅ | `test_wrong_password_is_rejected` |  | FR-001, FR-004, SEC-001, SEC-004 | 0.47 s |

### `tests/integration/test_change_requests.py` — 11 tests, 11 passed

_FR-030-FR-039, FR-027-FR-029, BR-004/BR-005. Full submit -> dual-review ->_

| Result | Test | Purpose | Requirements | Time |
|---|---|---|---|---|
| ✅ | `test_author_cannot_sign_off_own_cr` |  | BR-004, BR-005, FR-027, FR-029, FR-030, FR-039 | 0.72 s |
| ✅ | `test_chief_engineer_cannot_be_a_prior_signer` |  | BR-004, BR-005, FR-027, FR-029, FR-030, FR-039 | 1.09 s |
| ✅ | `test_domain_signoff_rejects_user_without_that_domain` |  | BR-004, BR-005, FR-027, FR-029, FR-030, FR-039 | 0.48 s |
| ✅ | `test_dual_signoff_in_either_order_reaches_pending_approval` |  | BR-004, BR-005, FR-027, FR-029, FR-030, FR-039 | 0.93 s |
| ✅ | `test_full_happy_path_to_approved` |  | BR-004, BR-005, FR-027, FR-029, FR-030, FR-039 | 0.95 s |
| ✅ | `test_rejection_returns_to_draft_and_clears_signoffs` |  | BR-004, BR-005, FR-027, FR-029, FR-030, FR-039 | 0.67 s |
| ✅ | `test_reviewer_rejection_without_comment_is_rejected` |  | BR-004, BR-005, FR-027, FR-029, FR-030, FR-039 | 0.67 s |
| ✅ | `test_submit_blocked_until_domain_signoff_complete` |  | BR-004, BR-005, FR-027, FR-029, FR-030, FR-039 | 0.56 s |
| ✅ | `test_withdraw_forbidden_for_non_author` |  | BR-004, BR-005, FR-027, FR-029, FR-030, FR-039 | 0.60 s |
| ✅ | `test_withdraw_removes_abandoned_new_draft` |  | BR-004, BR-005, FR-027, FR-029, FR-030, FR-039 | 0.40 s |
| ✅ | `test_withdraw_revision_type_restores_prior_current_revision` | Regression test: withdrawing a REVISION-type CR must restore the | BR-004, BR-005, FR-027, FR-029, FR-030, FR-039 | 1.15 s |

### `tests/integration/test_content_integrity.py` — 16 tests, 16 passed

_I-01 optimistic concurrency, I-04 reference warnings and where-used, I-12 duplicate_

| Result | Test | Purpose | Requirements | Time |
|---|---|---|---|---|
| ✅ | `test_expected_updated_at_is_enforced_too` |  | BR-019, FR-090, FR-091, FR-092, FR-093, FR-094, FR-109, FR-131, FR-141, TC-039 | 0.77 s |
| ✅ | `test_next_available_reports_how_many_numbers_are_left` |  | BR-019, FR-090, FR-091, FR-092, FR-093, FR-094, FR-109, FR-131, FR-141, TC-039 | 1.29 s |
| ✅ | `test_planned_dates_are_administrator_set_audited_and_warn_at_publish` |  | BR-019, FR-090, FR-091, FR-092, FR-093, FR-094, FR-109, FR-131, FR-141, TC-039 | 1.21 s |
| ✅ | `test_platform_variant_copies_the_code_and_links_the_family` |  | BR-019, FR-090, FR-091, FR-092, FR-093, FR-094, FR-109, FR-131, FR-141, TC-039 | 1.25 s |
| ✅ | `test_reference_to_a_deprecated_code_warns` |  | BR-019, FR-090, FR-091, FR-092, FR-093, FR-094, FR-109, FR-131, FR-141, TC-039 | 1.98 s |
| ✅ | `test_related_codes_are_validated_and_checked` |  | BR-019, FR-090, FR-091, FR-092, FR-093, FR-094, FR-109, FR-131, FR-141, TC-039 | 0.78 s |
| ✅ | `test_remedy_text_length_is_validated` |  | BR-019, FR-090, FR-091, FR-092, FR-093, FR-094, FR-109, FR-131, FR-141, TC-039 | 0.77 s |
| ✅ | `test_save_without_a_version_still_works_for_old_clients` |  | BR-019, FR-090, FR-091, FR-092, FR-093, FR-094, FR-109, FR-131, FR-141, TC-039 | 0.67 s |
| ✅ | `test_similar_endpoint_supports_the_did_you_mean_hint` |  | BR-019, FR-090, FR-091, FR-092, FR-093, FR-094, FR-109, FR-131, FR-141, TC-039 | 0.64 s |
| ✅ | `test_similar_title_in_the_subgroup_is_flagged_not_blocked` |  | BR-019, FR-090, FR-091, FR-092, FR-093, FR-094, FR-109, FR-131, FR-141, TC-039 | 0.67 s |
| ✅ | `test_stale_save_is_refused_with_the_current_values` |  | BR-019, FR-090, FR-091, FR-092, FR-093, FR-094, FR-109, FR-131, FR-141, TC-039 | 0.74 s |
| ✅ | `test_troubleshooting_fields_round_trip_and_reach_the_export` |  | BR-019, FR-090, FR-091, FR-092, FR-093, FR-094, FR-109, FR-131, FR-141, TC-039 | 1.23 s |
| ✅ | `test_ui_stale_edit_keeps_the_users_entries_and_shows_the_conflict` |  | BR-019, FR-090, FR-091, FR-092, FR-093, FR-094, FR-109, FR-131, FR-141, TC-039 | 0.99 s |
| ✅ | `test_unknown_escalation_number_warns_but_does_not_block` |  | BR-019, FR-090, FR-091, FR-092, FR-093, FR-094, FR-109, FR-131, FR-141, TC-039 | 0.64 s |
| ✅ | `test_variant_needs_a_decided_source_and_an_engineer` |  | BR-019, FR-090, FR-091, FR-092, FR-093, FR-094, FR-109, FR-131, FR-141, TC-039 | 0.73 s |
| ✅ | `test_where_used_lists_dependants_and_deprecation_needs_acknowledgement` |  | BR-019, FR-090, FR-091, FR-092, FR-093, FR-094, FR-109, FR-131, FR-141, TC-039 | 1.27 s |

### `tests/integration/test_csrf.py` — 2 tests, 2 passed

_docs/11-security-architecture.md §5: CSRF synchronizer-token protection_

| Result | Test | Purpose | Requirements | Time |
|---|---|---|---|---|
| ✅ | `test_state_changing_request_with_csrf_token_succeeds` |  |  | 0.37 s |
| ✅ | `test_state_changing_request_without_csrf_token_is_rejected` |  |  | 0.35 s |

### `tests/integration/test_decision_trail.py` — 5 tests, 5 passed

_Where review comments live: the change-request page, the status-code_

| Result | Test | Purpose | Requirements | Time |
|---|---|---|---|---|
| ✅ | `test_audit_entries_carry_the_comment_text_and_id` |  |  | 1.12 s |
| ✅ | `test_audit_log_can_be_filtered_by_action_and_actor` |  |  | 1.17 s |
| ✅ | `test_status_code_page_lists_all_decisions_and_comments` |  |  | 1.28 s |
| ✅ | `test_viewers_cannot_see_the_review_discussion` |  |  | 0.90 s |
| ✅ | `test_withdrawing_keeps_the_discussion_in_the_audit_log` |  |  | 0.92 s |

### `tests/integration/test_deprecation.py` — 7 tests, 7 passed

_FR-050-FR-052, BR-006, docs/05-governance-handbook.md §5, §11._

| Result | Test | Purpose | Requirements | Time |
|---|---|---|---|---|
| ✅ | `test_archive_blocked_before_retention_period_elapses` |  | BR-006, FR-050, FR-052 | 1.29 s |
| ✅ | `test_archive_succeeds_after_retention_period` |  | BR-006, FR-050, FR-052 | 1.12 s |
| ✅ | `test_deprecation_requires_released_state` |  | BR-006, FR-050, FR-052 | 0.39 s |
| ✅ | `test_full_deprecation_cycle` |  | BR-006, FR-050, FR-052 | 1.53 s |
| ✅ | `test_non_admin_cannot_archive_or_reinstate` |  | BR-006, FR-050, FR-052 | 0.52 s |
| ✅ | `test_reinstate_deprecated_code` |  | BR-006, FR-050, FR-052 | 1.12 s |
| ✅ | `test_second_revision_does_not_violate_current_uniqueness` | Regression test: create_revision must flip the old current revision's | BR-006, FR-050, FR-052 | 1.14 s |

### `tests/integration/test_email_and_windows_signin.py` — 16 tests, 16 passed

_The e-mail address of a user is fixed, and the Windows sign-in that will replace the password in a_

| Result | Test | Purpose | Requirements | Time |
|---|---|---|---|---|
| ✅ | `test_a_domain_name_is_matched_through_the_mail_domain_or_the_user_name` |  | FR-001, FR-010, FR-162, FR-163, SEC-033, TC-058 | 0.60 s |
| ✅ | `test_a_header_from_an_address_that_is_not_a_trusted_proxy_is_not_believed` |  | FR-001, FR-010, FR-162, FR-163, SEC-033, TC-058 | 0.75 s |
| ✅ | `test_an_address_is_stored_trimmed_and_lower_case_and_must_be_valid_and_new` |  | FR-001, FR-010, FR-162, FR-163, SEC-033, TC-058 | 0.68 s |
| ✅ | `test_no_identity_an_unknown_one_and_a_deactivated_account_are_all_refused` |  | FR-001, FR-010, FR-162, FR-163, SEC-033, TC-058 | 0.63 s |
| ✅ | `test_production_never_starts_with_the_simulation_or_an_unknown_mode` |  | FR-001, FR-010, FR-162, FR-163, SEC-033, TC-058 | 0.08 s |
| ✅ | `test_the_address_of_a_user_cannot_be_changed` |  | FR-001, FR-010, FR-162, FR-163, SEC-033, TC-058 | 0.61 s |
| ✅ | `test_the_database_refuses_a_changed_address_too` |  | FR-001, FR-010, FR-162, FR-163, SEC-033, TC-058 | 0.57 s |
| ✅ | `test_the_development_defaults_are_the_simulation_next_to_the_password` |  | FR-001, FR-010, FR-162, FR-163, SEC-033, TC-058 | 0.16 s |
| ✅ | `test_the_gateways_identity_signs_the_matching_account_in_and_is_audited` |  | FR-001, FR-010, FR-162, FR-163, SEC-033, TC-058 | 0.58 s |
| ✅ | `test_the_screens_show_the_address_as_fixed` |  | FR-001, FR-010, FR-162, FR-163, SEC-033, TC-058 | 0.73 s |
| ✅ | `test_the_shipped_example_configuration_documents_the_settings` |  | FR-001, FR-010, FR-162, FR-163, SEC-033, TC-058 | 0.01 s |
| ✅ | `test_the_simulation_page_stands_in_for_the_gateway_and_signs_in_by_address` |  | FR-001, FR-010, FR-162, FR-163, SEC-033, TC-058 | 0.66 s |
| ✅ | `test_the_simulation_refuses_an_unknown_identity_and_is_off_by_default` |  | FR-001, FR-010, FR-162, FR-163, SEC-033, TC-058 | 0.80 s |
| ✅ | `test_with_both_modes_the_login_page_offers_the_button_and_the_form` |  | FR-001, FR-010, FR-162, FR-163, SEC-033, TC-058 | 0.31 s |
| ✅ | `test_with_passwords_only_the_windows_sign_in_is_not_there` |  | FR-001, FR-010, FR-162, FR-163, SEC-033, TC-058 | 0.64 s |
| ✅ | `test_with_windows_only_passwords_are_refused_and_the_login_page_says_so` |  | FR-001, FR-010, FR-162, FR-163, SEC-033, TC-058 | 0.62 s |

### `tests/integration/test_exports_and_diff.py` — 15 tests, 15 passed

_FR-032, FR-045, FR-046, FR-054, FR-064, BR-008, SEC-023, TC-023, TC-035:_

| Result | Test | Purpose | Requirements | Time |
|---|---|---|---|---|
| ✅ | `test_diff_card_renders_on_change_request_page` |  | BR-008, FR-032, FR-045, FR-046, FR-054, FR-064, SEC-023, TC-023, TC-035 | 0.88 s |
| ✅ | `test_diff_hidden_from_viewers_for_open_revisions_and_unknown_revisions` |  | BR-008, FR-032, FR-045, FR-046, FR-054, FR-064, SEC-023, TC-023, TC-035 | 1.45 s |
| ✅ | `test_export_file_names_carry_a_timestamp` | Every export file name ends with the generation time, YYYY-MM-DD_HH-MM (UTC). | BR-008, FR-032, FR-045, FR-046, FR-054, FR-064, SEC-023, TC-023, TC-035 | 1.55 s |
| ✅ | `test_exports_neutralise_formula_injection` |  | BR-008, FR-032, FR-045, FR-046, FR-054, FR-064, SEC-023, TC-023, TC-035 | 0.80 s |
| ✅ | `test_json_export_is_flat_rows` |  | BR-008, FR-032, FR-045, FR-046, FR-054, FR-064, SEC-023, TC-023, TC-035 | 1.48 s |
| ✅ | `test_new_code_diff_is_marked_new` |  | BR-008, FR-032, FR-045, FR-046, FR-054, FR-064, SEC-023, TC-023, TC-035 | 0.63 s |
| ✅ | `test_release_can_be_deleted_before_publish_only` |  | BR-008, FR-032, FR-045, FR-046, FR-054, FR-064, SEC-023, TC-023, TC-035 | 1.38 s |
| ✅ | `test_released_export_contains_only_released_non_sandbox_codes` |  | BR-008, FR-032, FR-045, FR-046, FR-054, FR-064, SEC-023, TC-023, TC-035 | 1.41 s |
| ✅ | `test_released_export_filters_and_formats` |  | BR-008, FR-032, FR-045, FR-046, FR-054, FR-064, SEC-023, TC-023, TC-035 | 1.66 s |
| ✅ | `test_revision_diff_endpoint_and_cr_baseline_diff` |  | BR-008, FR-032, FR-045, FR-046, FR-054, FR-064, SEC-023, TC-023, TC-035 | 1.35 s |
| ✅ | `test_working_set_filters_by_lifecycle_state` |  | BR-008, FR-032, FR-045, FR-046, FR-054, FR-064, SEC-023, TC-023, TC-035 | 0.81 s |
| ✅ | `test_working_set_is_labelled_and_excludes_sandbox` |  | BR-008, FR-032, FR-045, FR-046, FR-054, FR-064, SEC-023, TC-023, TC-035 | 0.86 s |
| ✅ | `test_working_set_not_available_to_viewers_or_anonymous` |  | BR-008, FR-032, FR-045, FR-046, FR-054, FR-064, SEC-023, TC-023, TC-035 | 0.67 s |
| ✅ | `test_working_set_pdf_and_xlsx_render` |  | BR-008, FR-032, FR-045, FR-046, FR-054, FR-064, SEC-023, TC-023, TC-035 | 1.00 s |
| ✅ | `test_xlsx_export_has_same_rows_as_csv` | TC-035. | TC-035 | 1.39 s |

### `tests/integration/test_generated_fields.py` — 18 tests, 18 passed

_The fields of the generated controller programs (schema v4.1, docs/06-data-dictionary.md sections_

| Result | Test | Purpose | Requirements | Time |
|---|---|---|---|---|
| ✅ | `test_a_field_of_the_other_controller_is_refused_and_the_rest_is_stored` |  | FR-025, FR-032, FR-048o, FR-168, TC-063 | 0.64 s |
| ✅ | `test_a_hub_program_import_keeps_its_hub_fields_and_nothing_of_the_main_ones` |  | FR-025, FR-032, FR-048o, FR-168, TC-063 | 0.69 s |
| ✅ | `test_a_main_program_import_keeps_every_field_of_the_program[StCd_1000.st]` |  | FR-025, FR-032, FR-048o, FR-168, TC-063 | 0.70 s |
| ✅ | `test_a_main_program_import_keeps_every_field_of_the_program[StCd_1001.st]` |  | FR-025, FR-032, FR-048o, FR-168, TC-063 | 0.67 s |
| ✅ | `test_a_main_program_import_keeps_every_field_of_the_program[StCd_1002.st]` |  | FR-025, FR-032, FR-048o, FR-168, TC-063 | 0.66 s |
| ✅ | `test_a_new_revision_carries_over_what_the_caller_does_not_send_and_the_diff_shows_changes` |  | FR-025, FR-032, FR-048o, FR-168, TC-063 | 1.09 s |
| ✅ | `test_a_rejected_form_keeps_what_was_typed` |  | FR-025, FR-032, FR-048o, FR-168, TC-063 | 0.77 s |
| ✅ | `test_the_form_stores_the_fields_and_the_pages_show_them` |  | FR-025, FR-032, FR-048o, FR-168, TC-063 | 1.13 s |
| ✅ | `test_the_levels_and_programs_are_internal_and_never_leave_in_an_audience_export` |  | FR-025, FR-032, FR-048o, FR-168, TC-063 | 1.09 s |
| ✅ | `test_the_two_zero_load_attributes_are_not_mixed_up` |  | FR-025, FR-032, FR-048o, FR-168, TC-063 | 0.84 s |
| ✅ | `test_values_out_of_range_are_refused[extra0]` |  | FR-025, FR-032, FR-048o, FR-168, TC-063 | 0.59 s |
| ✅ | `test_values_out_of_range_are_refused[extra1]` |  | FR-025, FR-032, FR-048o, FR-168, TC-063 | 0.59 s |
| ✅ | `test_values_out_of_range_are_refused[extra2]` |  | FR-025, FR-032, FR-048o, FR-168, TC-063 | 0.60 s |
| ✅ | `test_values_out_of_range_are_refused[extra3]` |  | FR-025, FR-032, FR-048o, FR-168, TC-063 | 0.78 s |
| ✅ | `test_values_out_of_range_are_refused[extra4]` |  | FR-025, FR-032, FR-048o, FR-168, TC-063 | 0.60 s |
| ✅ | `test_values_out_of_range_are_refused[extra5]` |  | FR-025, FR-032, FR-048o, FR-168, TC-063 | 0.59 s |
| ✅ | `test_values_out_of_range_are_refused[extra6]` |  | FR-025, FR-032, FR-048o, FR-168, TC-063 | 0.59 s |
| ✅ | `test_withdrawing_and_deleting_a_code_removes_its_levels` |  | FR-025, FR-032, FR-048o, FR-168, TC-063 | 0.63 s |

### `tests/integration/test_governance_extras.py` — 24 tests, 24 passed

_Remaining spec checks: SEC-010 service-layer authorization, FR-010/011/011a/014_

| Result | Test | Purpose | Requirements | Time |
|---|---|---|---|---|
| ✅ | `test_a_user_holds_exactly_one_role` |  | FR-005, FR-010, FR-021, FR-038, FR-048d, NFR-008, SEC-010 | 0.58 s |
| ✅ | `test_account_lock_and_password_events_are_audited` |  | FR-005, FR-010, FR-021, FR-038, FR-048d, NFR-008, SEC-010 | 0.72 s |
| ✅ | `test_auth_provider_seam_is_substitutable` | Callers depend on AuthenticatedUser only: a different provider returning | FR-005, FR-010, FR-021, FR-038, FR-048d, NFR-008, SEC-010 | 0.37 s |
| ✅ | `test_comment_leaves_state_and_signoffs_untouched` |  | FR-005, FR-010, FR-021, FR-038, FR-048d, NFR-008, SEC-010 | 1.08 s |
| ✅ | `test_import_preserves_legacy_reference_number` |  | FR-005, FR-010, FR-021, FR-038, FR-048d, NFR-008, SEC-010 | 0.64 s |
| ✅ | `test_next_available_preview_does_not_reserve_a_number` |  | FR-005, FR-010, FR-021, FR-038, FR-048d, NFR-008, SEC-010 | 0.83 s |
| ✅ | `test_services_enforce_roles_independently_of_route_decorators[<lambda>-ADMINISTRATOR]` |  | FR-005, FR-010, FR-021, FR-038, FR-048d, NFR-008, SEC-010 | 0.27 s |
| ✅ | `test_services_enforce_roles_independently_of_route_decorators[<lambda>-CHIEF_ENGINEER0]` |  | FR-005, FR-010, FR-021, FR-038, FR-048d, NFR-008, SEC-010 | 0.27 s |
| ✅ | `test_services_enforce_roles_independently_of_route_decorators[<lambda>-CHIEF_ENGINEER1]` |  | FR-005, FR-010, FR-021, FR-038, FR-048d, NFR-008, SEC-010 | 0.27 s |
| ✅ | `test_services_enforce_roles_independently_of_route_decorators[<lambda>-ENGINEER0]` |  | FR-005, FR-010, FR-021, FR-038, FR-048d, NFR-008, SEC-010 | 0.26 s |
| ✅ | `test_services_enforce_roles_independently_of_route_decorators[<lambda>-ENGINEER1]` |  | FR-005, FR-010, FR-021, FR-038, FR-048d, NFR-008, SEC-010 | 0.26 s |
| ✅ | `test_services_enforce_roles_independently_of_route_decorators[<lambda>-ENGINEER2]` |  | FR-005, FR-010, FR-021, FR-038, FR-048d, NFR-008, SEC-010 | 0.26 s |
| ✅ | `test_services_enforce_roles_independently_of_route_decorators[<lambda>-ENGINEER3]` |  | FR-005, FR-010, FR-021, FR-038, FR-048d, NFR-008, SEC-010 | 0.25 s |
| ✅ | `test_services_enforce_roles_independently_of_route_decorators[<lambda>-ENGINEER4]` |  | FR-005, FR-010, FR-021, FR-038, FR-048d, NFR-008, SEC-010 | 0.47 s |
| ✅ | `test_services_enforce_roles_independently_of_route_decorators[<lambda>-ENGINEER5]` |  | FR-005, FR-010, FR-021, FR-038, FR-048d, NFR-008, SEC-010 | 0.27 s |
| ✅ | `test_services_enforce_roles_independently_of_route_decorators[<lambda>-ENGINEER6]` |  | FR-005, FR-010, FR-021, FR-038, FR-048d, NFR-008, SEC-010 | 0.25 s |
| ✅ | `test_services_enforce_roles_independently_of_route_decorators[<lambda>-ENGINEER7]` |  | FR-005, FR-010, FR-021, FR-038, FR-048d, NFR-008, SEC-010 | 0.25 s |
| ✅ | `test_services_enforce_roles_independently_of_route_decorators[<lambda>-REVIEWER0]` |  | FR-005, FR-010, FR-021, FR-038, FR-048d, NFR-008, SEC-010 | 0.46 s |
| ✅ | `test_services_enforce_roles_independently_of_route_decorators[<lambda>-REVIEWER1]` |  | FR-005, FR-010, FR-021, FR-038, FR-048d, NFR-008, SEC-010 | 0.26 s |
| ✅ | `test_services_enforce_roles_independently_of_route_decorators[<lambda>-REVIEWER2]` |  | FR-005, FR-010, FR-021, FR-038, FR-048d, NFR-008, SEC-010 | 0.26 s |
| ✅ | `test_services_enforce_roles_independently_of_route_decorators[<lambda>-VIEWER0]` |  | FR-005, FR-010, FR-021, FR-038, FR-048d, NFR-008, SEC-010 | 0.26 s |
| ✅ | `test_services_enforce_roles_independently_of_route_decorators[<lambda>-VIEWER1]` |  | FR-005, FR-010, FR-021, FR-038, FR-048d, NFR-008, SEC-010 | 0.26 s |
| ✅ | `test_user_administration_events_are_audited` |  | FR-005, FR-010, FR-021, FR-038, FR-048d, NFR-008, SEC-010 | 0.54 s |
| ✅ | `test_whole_lifecycle_works_with_all_outbound_network_blocked` | The application must keep operating when it can reach nothing beyond | FR-005, FR-010, FR-021, FR-038, FR-048d, NFR-008, SEC-010 | 1.51 s |

### `tests/integration/test_import.py` — 7 tests, 7 passed

_FR-048a-d, EPIC-14: CSV/XLSX library import, still fully governed_

| Result | Test | Purpose | Requirements | Time |
|---|---|---|---|---|
| ✅ | `test_ambiguous_group_code_requires_range_hint` | WTUR is reused for a second, numerically distinct Hub Controller | FR-048a | 0.42 s |
| ✅ | `test_imported_row_becomes_import_type_draft_change_request` |  | FR-048a | 0.59 s |
| ✅ | `test_invalid_row_is_reported_and_creates_nothing` |  | FR-048a | 0.42 s |
| ✅ | `test_non_admin_engineer_can_upload_import` |  | FR-048a | 0.40 s |
| ✅ | `test_unknown_functional_system_group_code_reported_as_error` |  | FR-048a | 0.37 s |
| ✅ | `test_unsupported_file_extension_rejected` |  | FR-048a | 0.36 s |
| ✅ | `test_viewer_cannot_upload_import` |  | FR-048a | 0.36 s |

### `tests/integration/test_import_toolkit.py` — 20 tests, 20 passed

_The migration toolkit around the library import (docs/21-improvement-ideas.md): I-05 template, dry_

| Result | Test | Purpose | Requirements | Time |
|---|---|---|---|---|
| ✅ | `test_a_big_file_is_processed_in_the_background_with_progress` |  | BR-015, FR-048i, FR-048j, FR-048k, FR-048l, FR-048m, FR-048n, FR-093, TC-043 | 1.47 s |
| ✅ | `test_a_legacy_number_already_imported_is_refused_in_create_mode` |  | BR-015, FR-048i, FR-048j, FR-048k, FR-048l, FR-048m, FR-048n, FR-093, TC-043 | 0.69 s |
| ✅ | `test_dry_run_reports_every_problem_and_creates_nothing` |  | BR-015, FR-048i, FR-048j, FR-048k, FR-048l, FR-048m, FR-048n, FR-093, TC-043 | 0.38 s |
| ✅ | `test_dry_run_warns_about_a_possible_duplicate_without_blocking` |  | BR-015, FR-048i, FR-048j, FR-048k, FR-048l, FR-048m, FR-048n, FR-093, TC-043 | 0.41 s |
| ✅ | `test_error_report_has_row_column_value_and_a_fix_hint_as_csv_and_xlsx` |  | BR-015, FR-048i, FR-048j, FR-048k, FR-048l, FR-048m, FR-048n, FR-093, TC-043 | 0.44 s |
| ✅ | `test_files_above_the_threshold_go_to_the_background_automatically` |  | BR-015, FR-048i, FR-048j, FR-048k, FR-048l, FR-048m, FR-048n, FR-093, TC-043 | 0.41 s |
| ✅ | `test_formula_like_values_in_the_error_report_are_neutralised` |  | BR-015, FR-048i, FR-048j, FR-048k, FR-048l, FR-048m, FR-048n, FR-093, TC-043 | 0.40 s |
| ✅ | `test_import_ui_pages_render_and_the_validate_button_creates_nothing` |  | BR-015, FR-048i, FR-048j, FR-048k, FR-048l, FR-048m, FR-048n, FR-093, TC-043 | 0.63 s |
| ✅ | `test_missing_required_columns_are_named_up_front` |  | BR-015, FR-048i, FR-048j, FR-048k, FR-048l, FR-048m, FR-048n, FR-093, TC-043 | 0.35 s |
| ✅ | `test_new_content_columns_are_imported` |  | BR-015, FR-048i, FR-048j, FR-048k, FR-048l, FR-048m, FR-048n, FR-093, TC-043 | 0.40 s |
| ✅ | `test_reconciliation_counts_states_and_names_the_missing_numbers` |  | BR-015, FR-048i, FR-048j, FR-048k, FR-048l, FR-048m, FR-048n, FR-093, TC-043 | 1.47 s |
| ✅ | `test_similar_titles_are_reported_as_warnings` |  | BR-015, FR-048i, FR-048j, FR-048k, FR-048l, FR-048m, FR-048n, FR-093, TC-043 | 0.42 s |
| ✅ | `test_template_csv_and_xlsx_carry_the_exact_headers_and_lookup_codes` |  | BR-015, FR-048i, FR-048j, FR-048k, FR-048l, FR-048m, FR-048n, FR-093, TC-043 | 0.42 s |
| ✅ | `test_the_downloaded_template_imports_cleanly_as_is` |  | BR-015, FR-048i, FR-048j, FR-048k, FR-048l, FR-048m, FR-048n, FR-093, TC-043 | 0.61 s |
| ✅ | `test_the_same_legacy_number_in_another_group_is_a_different_code` |  | BR-015, FR-048i, FR-048j, FR-048k, FR-048l, FR-048m, FR-048n, FR-093, TC-043 | 0.41 s |
| ✅ | `test_update_mode_errors_are_specific` |  | BR-015, FR-048i, FR-048j, FR-048k, FR-048l, FR-048m, FR-048n, FR-093, TC-043 | 0.92 s |
| ✅ | `test_update_mode_opens_a_new_revision_of_a_released_code` |  | BR-015, FR-048i, FR-048j, FR-048k, FR-048l, FR-048m, FR-048n, FR-093, TC-043 | 1.25 s |
| ✅ | `test_update_mode_revises_the_open_draft_in_place` |  | BR-015, FR-048i, FR-048j, FR-048k, FR-048l, FR-048m, FR-048n, FR-093, TC-043 | 0.43 s |
| ✅ | `test_update_mode_skips_unchanged_rows_and_creates_missing_ones` |  | BR-015, FR-048i, FR-048j, FR-048k, FR-048l, FR-048m, FR-048n, FR-093, TC-043 | 0.64 s |
| ✅ | `test_update_of_someone_elses_draft_is_reported_on_the_row` |  | BR-015, FR-048i, FR-048j, FR-048k, FR-048l, FR-048m, FR-048n, FR-093, TC-043 | 0.53 s |

### `tests/integration/test_integrations_and_reports.py` — 32 tests, 32 passed

_I-29 API tokens, change feed and webhooks; I-26 saved searches; I-28 fleet occurrences;_

| Result | Test | Purpose | Requirements | Time |
|---|---|---|---|---|
| ✅ | `test_a_disabled_webhook_is_not_called` |  | FR-123, FR-140, FR-141, FR-142, FR-143, FR-144, FR-145, FR-146, FR-147, SEC-027, SEC-028, TC-046 | 1.67 s |
| ✅ | `test_a_failing_webhook_is_recorded_and_never_blocks_the_publish` |  | FR-123, FR-140, FR-141, FR-142, FR-143, FR-144, FR-145, FR-146, FR-147, SEC-027, SEC-028, TC-046 | 1.73 s |
| ✅ | `test_a_hub_code_is_carried_over_as_a_main_controller_draft` |  | FR-123, FR-140, FR-141, FR-142, FR-143, FR-144, FR-145, FR-146, FR-147, SEC-027, SEC-028, TC-046 | 1.14 s |
| ✅ | `test_a_publish_calls_the_webhook_with_a_verifiable_signature` |  | FR-123, FR-140, FR-141, FR-142, FR-143, FR-144, FR-145, FR-146, FR-147, SEC-027, SEC-028, TC-046 | 1.71 s |
| ✅ | `test_a_token_is_shown_once_and_stored_only_as_a_hash` |  | FR-123, FR-140, FR-141, FR-142, FR-143, FR-144, FR-145, FR-146, FR-147, SEC-027, SEC-028, TC-046 | 0.66 s |
| ✅ | `test_a_token_only_works_for_its_scope` |  | FR-123, FR-140, FR-141, FR-142, FR-143, FR-144, FR-145, FR-146, FR-147, SEC-027, SEC-028, TC-046 | 0.66 s |
| ✅ | `test_a_token_reads_released_data_only_and_never_writes` |  | FR-123, FR-140, FR-141, FR-142, FR-143, FR-144, FR-145, FR-146, FR-147, SEC-027, SEC-028, TC-046 | 1.64 s |
| ✅ | `test_an_unreachable_webhook_target_does_not_block_the_publish` |  | FR-123, FR-140, FR-141, FR-142, FR-143, FR-144, FR-145, FR-146, FR-147, SEC-027, SEC-028, TC-046 | 4.00 s |
| ✅ | `test_bulk_deprecation_is_for_administrators_and_hub_groups` |  | FR-123, FR-140, FR-141, FR-142, FR-143, FR-144, FR-145, FR-146, FR-147, SEC-027, SEC-028, TC-046 | 0.96 s |
| ✅ | `test_carry_over_is_refused_for_the_wrong_kind_of_code_or_target` |  | FR-123, FR-140, FR-141, FR-142, FR-143, FR-144, FR-145, FR-146, FR-147, SEC-027, SEC-028, TC-046 | 1.67 s |
| ✅ | `test_health_report_covers_capacity_missing_data_and_inconsistencies` |  | FR-123, FR-140, FR-141, FR-142, FR-143, FR-144, FR-145, FR-146, FR-147, SEC-027, SEC-028, TC-046 | 1.48 s |
| ✅ | `test_health_report_finds_an_info_code_with_an_alarm` |  | FR-123, FR-140, FR-141, FR-142, FR-143, FR-144, FR-145, FR-146, FR-147, SEC-027, SEC-028, TC-046 | 1.12 s |
| ✅ | `test_health_report_flags_a_nearly_full_band` |  | FR-123, FR-140, FR-141, FR-142, FR-143, FR-144, FR-145, FR-146, FR-147, SEC-027, SEC-028, TC-046 | 1.24 s |
| ✅ | `test_hub_consolidation_ui_page_renders` |  | FR-123, FR-140, FR-141, FR-142, FR-143, FR-144, FR-145, FR-146, FR-147, SEC-027, SEC-028, TC-046 | 1.18 s |
| ✅ | `test_kpis_have_the_documented_shape` |  | FR-123, FR-140, FR-141, FR-142, FR-143, FR-144, FR-145, FR-146, FR-147, SEC-027, SEC-028, TC-046 | 1.64 s |
| ✅ | `test_occurrence_import_validation_and_permissions` |  | FR-123, FR-140, FR-141, FR-142, FR-143, FR-144, FR-145, FR-146, FR-147, SEC-027, SEC-028, TC-046 | 0.71 s |
| ✅ | `test_occurrence_report_names_codes_that_never_fire_and_those_that_fire_most` |  | FR-123, FR-140, FR-141, FR-142, FR-143, FR-144, FR-145, FR-146, FR-147, SEC-027, SEC-028, TC-046 | 1.98 s |
| ✅ | `test_redirects_are_not_followed` |  | FR-123, FR-140, FR-141, FR-142, FR-143, FR-144, FR-145, FR-146, FR-147, SEC-027, SEC-028, TC-046 | 1.79 s |
| ✅ | `test_reports_are_limited_to_the_right_roles` |  | FR-123, FR-140, FR-141, FR-142, FR-143, FR-144, FR-145, FR-146, FR-147, SEC-027, SEC-028, TC-046 | 1.01 s |
| ✅ | `test_revoked_expired_unknown_and_orphaned_tokens_are_refused` |  | FR-123, FR-140, FR-141, FR-142, FR-143, FR-144, FR-145, FR-146, FR-147, SEC-027, SEC-028, TC-046 | 0.72 s |
| ✅ | `test_sandbox_activity_never_appears_in_the_feed` |  | FR-123, FR-140, FR-141, FR-142, FR-143, FR-144, FR-145, FR-146, FR-147, SEC-027, SEC-028, TC-046 | 0.67 s |
| ✅ | `test_saved_search_ui_save_and_delete` |  | FR-123, FR-140, FR-141, FR-142, FR-143, FR-144, FR-145, FR-146, FR-147, SEC-027, SEC-028, TC-046 | 0.79 s |
| ✅ | `test_saved_searches_are_private_to_their_owner` |  | FR-123, FR-140, FR-141, FR-142, FR-143, FR-144, FR-145, FR-146, FR-147, SEC-027, SEC-028, TC-046 | 0.78 s |
| ✅ | `test_saved_searches_round_trip_through_the_url` |  | FR-123, FR-140, FR-141, FR-142, FR-143, FR-144, FR-145, FR-146, FR-147, SEC-027, SEC-028, TC-046 | 1.07 s |
| ✅ | `test_saving_under_an_existing_name_replaces_it_and_validates_the_name` |  | FR-123, FR-140, FR-141, FR-142, FR-143, FR-144, FR-145, FR-146, FR-147, SEC-027, SEC-028, TC-046 | 0.70 s |
| ✅ | `test_the_capacity_table_colours_main_blue_and_hub_light_blue` |  | FR-123, FR-140, FR-141, FR-142, FR-143, FR-144, FR-145, FR-146, FR-147, SEC-027, SEC-028, TC-046 | 0.73 s |
| ✅ | `test_the_feed_lists_releases_in_order_with_a_cursor_and_an_etag` |  | FR-123, FR-140, FR-141, FR-142, FR-143, FR-144, FR-145, FR-146, FR-147, SEC-027, SEC-028, TC-046 | 2.59 s |
| ✅ | `test_the_feed_needs_authentication` |  | FR-123, FR-140, FR-141, FR-142, FR-143, FR-144, FR-145, FR-146, FR-147, SEC-027, SEC-028, TC-046 | 0.26 s |
| ✅ | `test_the_whole_consolidation_loop_ends_with_a_deprecation_request` |  | FR-123, FR-140, FR-141, FR-142, FR-143, FR-144, FR-145, FR-146, FR-147, SEC-027, SEC-028, TC-046 | 1.89 s |
| ✅ | `test_token_events_are_audited_without_the_secret` |  | FR-123, FR-140, FR-141, FR-142, FR-143, FR-144, FR-145, FR-146, FR-147, SEC-027, SEC-028, TC-046 | 0.67 s |
| ✅ | `test_token_management_is_for_administrators_and_validated` |  | FR-123, FR-140, FR-141, FR-142, FR-143, FR-144, FR-145, FR-146, FR-147, SEC-027, SEC-028, TC-046 | 0.68 s |
| ✅ | `test_webhook_targets_must_be_internal_and_inputs_valid` |  | FR-123, FR-140, FR-141, FR-142, FR-143, FR-144, FR-145, FR-146, FR-147, SEC-027, SEC-028, TC-046 | 0.77 s |

### `tests/integration/test_invariants.py` — 15 tests, 15 passed

_Business-rule and data-integrity checks: BR-001..BR-003, BR-009, FR-023a,_

| Result | Test | Purpose | Requirements | Time |
|---|---|---|---|---|
| ✅ | `test_draft_can_be_saved_repeatedly_without_workflow_transitions` |  | BR-001, BR-003, BR-009, FR-023a, FR-024, FR-060, FR-064, TC-004, TC-008, TC-010, TC-013 | 0.72 s |
| ✅ | `test_duplicate_identifier_rejected_by_database` |  | BR-001, BR-003, BR-009, FR-023a, FR-024, FR-060, FR-064, TC-004, TC-008, TC-010, TC-013 | 0.75 s |
| ✅ | `test_each_subgroup_sub_band_numbers_independently` |  | BR-001, BR-003, BR-009, FR-023a, FR-024, FR-060, FR-064, TC-004, TC-008, TC-010, TC-013 | 0.26 s |
| ✅ | `test_exactly_one_current_revision_per_code` | BR-002 / TC-011. | BR-002, TC-011 | 1.21 s |
| ✅ | `test_filters_sort_and_pagination` |  | BR-001, BR-003, BR-009, FR-023a, FR-024, FR-060, FR-064, TC-004, TC-008, TC-010, TC-013 | 0.94 s |
| ✅ | `test_full_text_search_matches_identifier_title_and_description` |  | BR-001, BR-003, BR-009, FR-023a, FR-024, FR-060, FR-064, TC-004, TC-008, TC-010, TC-013 | 0.89 s |
| ✅ | `test_identifier_formats` |  | BR-001, BR-003, BR-009, FR-023a, FR-024, FR-060, FR-064, TC-004, TC-008, TC-010, TC-013 | 0.80 s |
| ✅ | `test_identifier_never_changes_after_allocation` | BR-001: a rejected-and-resubmitted CR keeps its identifier. | BR-001 | 0.99 s |
| ✅ | `test_in_flight_revision_cannot_be_edited_in_place` | FR-025: Review and later states are locked. | FR-025 | 1.06 s |
| ✅ | `test_new_revision_of_a_released_code_keeps_its_identifier` | BR-001 / FR-021: the identifier is allocated once, not again per revision. | BR-001, FR-021 | 1.74 s |
| ✅ | `test_only_one_open_revision_per_code` | BR-003 / TC-012: a second revision cannot be opened while one is open. | BR-003, TC-012 | 1.46 s |
| ✅ | `test_released_code_stays_visible_to_viewers_while_a_new_revision_is_open` | BR-009: opening revision 2 (a Draft) must not make the Released revision 1 | BR-009 | 1.35 s |
| ✅ | `test_revision_history_visible_to_viewer_only_once_decided` | FR-064 / BR-009. | BR-009, FR-064 | 1.33 s |
| ✅ | `test_sequential_submits_in_two_subgroups_do_not_interfere` |  | BR-001, BR-003, BR-009, FR-023a, FR-024, FR-060, FR-064, TC-004, TC-008, TC-010, TC-013 | 1.25 s |
| ✅ | `test_submit_requires_a_turbine_platform` |  | BR-001, BR-003, BR-009, FR-023a, FR-024, FR-060, FR-064, TC-004, TC-008, TC-010, TC-013 | 0.63 s |

### `tests/integration/test_lookup_admin.py` — 9 tests, 9 passed

_US-091: Administrator manages controlled vocabularies. docs/05-governance-_

| Result | Test | Purpose | Requirements | Time |
|---|---|---|---|---|
| ✅ | `test_admin_can_add_turbine_platform` |  | US-091 | 0.36 s |
| ✅ | `test_admin_can_create_new_functional_system_group_in_free_range` | FR-048g: into any currently free range (10000-10999, 14000-14999, | FR-048g | 0.35 s |
| ✅ | `test_admin_can_deactivate_and_relabel_a_value` |  | US-091 | 0.37 s |
| ✅ | `test_create_functional_subgroup_with_range` |  | US-091 | 0.36 s |
| ✅ | `test_duplicate_code_rejected` |  | US-091 | 0.35 s |
| ✅ | `test_functional_subgroup_overlap_rejected` | FR-048f: rejected with 409, naming the conflicting subgroup. | FR-048f | 0.36 s |
| ✅ | `test_functional_system_group_not_creatable_via_generic_endpoint` | v3 (EPIC-16): creation moved to a dedicated, non-overlap-validated | US-091 | 0.35 s |
| ✅ | `test_new_functional_system_group_range_overlap_rejected` | FR-048h: rejected with 409, naming the conflicting group. | FR-048h | 0.61 s |
| ✅ | `test_non_admin_cannot_create_lookup_value` |  | US-091 | 0.37 s |

### `tests/integration/test_numbering.py` — 4 tests, 4 passed

_docs/07-database-design.md §7a: atomic Functional Group/Subgroup allocation._

| Result | Test | Purpose | Requirements | Time |
|---|---|---|---|---|
| ✅ | `test_allocation_increments_and_persists` |  |  | 0.32 s |
| ✅ | `test_capacity_exhaustion_raises` |  |  | 0.31 s |
| ✅ | `test_first_allocation_in_a_group_starts_at_range_start` |  |  | 0.25 s |
| ✅ | `test_sandbox_allocation_never_collides_with_real_range` |  |  | 0.51 s |

### `tests/integration/test_pdf_scripts.py` — 20 tests, 20 passed

_The PDF export prints every script of the languages the tool offers (docs/03-srs.md FR-165,_

| Result | Test | Purpose | Requirements | Time |
|---|---|---|---|---|
| ✅ | `test_a_large_export_stays_fast_for_latin_text` |  | FR-045, FR-157, FR-165, NFR-008, TC-060 | 6.55 s |
| ✅ | `test_a_plain_latin_export_loads_only_noto_sans` |  | FR-045, FR-157, FR-165, NFR-008, TC-060 | 0.03 s |
| ✅ | `test_a_script_gets_its_own_font[arabic-\u0631\u0645\u0632 \u0627\u0644\u062d\u0627\u0644\u0629 \u0648\u062d\u062f\u0629 \u0627\u0644\u062a\u062d\u0643\u0645 StCd-01000]` |  | FR-045, FR-157, FR-165, NFR-008, TC-060 | 0.00 s |
| ✅ | `test_a_script_gets_its_own_font[bengali-\u09b8\u09cd\u09a5\u09bf\u09a4\u09bf \u0995\u09cb\u09a1 \u09a8\u09bf\u09af\u09bc\u09a8\u09cd\u09a4\u09cd\u09b0\u0995 \u09aa\u09b0\u09c0\u0995\u09cd\u09b7\u09be]` |  | FR-045, FR-157, FR-165, NFR-008, TC-060 | 0.00 s |
| ✅ | `test_a_script_gets_its_own_font[devanagari-\u0938\u094d\u0925\u093f\u0924\u093f \u0915\u094b\u0921 \u0928\u093f\u092f\u0902\u0924\u094d\u0930\u0915 \u0915\u0940 \u091c\u093e\u0901\u091a]` |  | FR-045, FR-157, FR-165, NFR-008, TC-060 | 0.00 s |
| ✅ | `test_a_script_gets_its_own_font[georgian-\u10e1\u10e2\u10d0\u10e2\u10e3\u10e1\u10d8\u10e1 \u10d9\u10dd\u10d3\u10d8 \u10d9\u10dd\u10dc\u10e2\u10e0\u10dd\u10da\u10d4\u10e0\u10d8\u10e1 \u10e8\u10d4\u10db\u10dd\u10ec\u10db\u10d4\u10d1\u10d0]` |  | FR-045, FR-157, FR-165, NFR-008, TC-060 | 0.00 s |
| ✅ | `test_a_script_gets_its_own_font[gujarati-\u0ab8\u0acd\u0aa5\u0abf\u0aa4\u0abf \u0a95\u0acb\u0aa1 \u0aa8\u0abf\u0aaf\u0a82\u0aa4\u0acd\u0ab0\u0a95 \u0aa4\u0aaa\u0abe\u0ab8]` |  | FR-045, FR-157, FR-165, NFR-008, TC-060 | 0.00 s |
| ✅ | `test_a_script_gets_its_own_font[gurmukhi-\u0a38\u0a25\u0a3f\u0a24\u0a40 \u0a15\u0a4b\u0a21 \u0a15\u0a70\u0a1f\u0a30\u0a4b\u0a32\u0a30 \u0a1c\u0a3e\u0a02\u0a1a]` |  | FR-045, FR-157, FR-165, NFR-008, TC-060 | 0.00 s |
| ✅ | `test_a_script_gets_its_own_font[kannada-\u0cb8\u0ccd\u0ca5\u0cbf\u0ca4\u0cbf \u0c95\u0ccb\u0ca1\u0ccd \u0ca8\u0cbf\u0caf\u0c82\u0ca4\u0ccd\u0cb0\u0c95 \u0caa\u0cb0\u0cbf\u0cb6\u0cc0\u0cb2\u0ca8\u0cc6]` |  | FR-045, FR-157, FR-165, NFR-008, TC-060 | 0.00 s |
| ✅ | `test_a_script_gets_its_own_font[malayalam-\u0d38\u0d4d\u0d25\u0d3f\u0d24\u0d3f \u0d15\u0d4b\u0d21\u0d4d \u0d28\u0d3f\u0d2f\u0d28\u0d4d\u0d24\u0d4d\u0d30\u0d15\u0d02 \u0d2a\u0d30\u0d3f\u0d36\u0d4b\u0d27\u0d28]` |  | FR-045, FR-157, FR-165, NFR-008, TC-060 | 0.00 s |
| ✅ | `test_a_script_gets_its_own_font[odia-\u0b38\u0b4d\u0b25\u0b3f\u0b24\u0b3f \u0b15\u0b4b\u0b21\u0b4d \u0b28\u0b3f\u0b5f\u0b28\u0b4d\u0b24\u0b4d\u0b30\u0b15 \u0b2f\u0b3e\u0b1e\u0b4d\u0b1a]` |  | FR-045, FR-157, FR-165, NFR-008, TC-060 | 0.00 s |
| ✅ | `test_a_script_gets_its_own_font[tamil-\u0ba8\u0bbf\u0bb2\u0bc8 \u0b95\u0bc1\u0bb1\u0bbf\u0baf\u0bc0\u0b9f\u0bc1 \u0b95\u0b9f\u0bcd\u0b9f\u0bc1\u0baa\u0bcd\u0baa\u0b9f\u0bc1\u0ba4\u0bcd\u0ba4\u0bbf \u0b9a\u0bcb\u0ba4\u0ba9\u0bc8]` |  | FR-045, FR-157, FR-165, NFR-008, TC-060 | 0.00 s |
| ✅ | `test_a_script_gets_its_own_font[telugu-\u0c38\u0c4d\u0c25\u0c3f\u0c24\u0c3f \u0c15\u0c4b\u0c21\u0c4d \u0c28\u0c3f\u0c2f\u0c02\u0c24\u0c4d\u0c30\u0c3f\u0c15 \u0c24\u0c28\u0c3f\u0c16\u0c40]` |  | FR-045, FR-157, FR-165, NFR-008, TC-060 | 0.00 s |
| ✅ | `test_a_script_gets_its_own_font[urdu-\u0627\u0633\u0679\u06cc\u0679\u0633 \u06a9\u0648\u0688 \u06a9\u0646\u0679\u0631\u0648\u0644\u0631 \u06a9\u06cc \u062c\u0627\u0646\u0686]` |  | FR-045, FR-157, FR-165, NFR-008, TC-060 | 0.00 s |
| ✅ | `test_every_character_of_every_translation_is_drawn_by_a_bundled_font` |  | FR-045, FR-157, FR-165, NFR-008, TC-060 | 0.00 s |
| ✅ | `test_every_script_builds_a_pdf_with_its_font` |  | FR-045, FR-157, FR-165, NFR-008, TC-060 | 0.34 s |
| ✅ | `test_latin_text_needs_no_script_font_and_arabic_is_told_from_urdu` |  | FR-045, FR-157, FR-165, NFR-008, TC-060 | 0.00 s |
| ✅ | `test_shaping_is_switched_on_per_cell_only_where_a_script_needs_it` |  | FR-045, FR-157, FR-165, NFR-008, TC-060 | 0.04 s |
| ✅ | `test_the_fonts_and_their_licence_are_bundled_and_shaping_is_available` |  | FR-045, FR-157, FR-165, NFR-008, TC-060 | 0.01 s |
| ✅ | `test_the_title_page_and_notice_may_carry_any_script` |  | FR-045, FR-157, FR-165, NFR-008, TC-060 | 0.08 s |

### `tests/integration/test_prg_idx_and_user_groups.py` — 9 tests, 9 passed

_Schema v4.1 (migration c9e2a4b6d815): PrgIdx_GUi on the status code, the controller-specific_

| Result | Test | Purpose | Requirements | Time |
|---|---|---|---|---|
| ✅ | `test_default_levels_are_seeded_only_where_the_programs_agree` |  |  | 0.29 s |
| ✅ | `test_leaving_draft_without_prg_idx_is_blocked_only_once_the_switch_is_on` |  |  | 0.26 s |
| ✅ | `test_new_revision_columns_start_at_zero_or_not_captured` |  |  | 0.27 s |
| ✅ | `test_prg_idx_is_an_optional_uint_that_is_unique_among_real_codes` |  |  | 0.28 s |
| ✅ | `test_prg_idx_is_frozen_once_a_revision_was_released` |  |  | 0.26 s |
| ✅ | `test_the_locked_revision_trigger_covers_the_new_content_columns` |  |  | 0.27 s |
| ✅ | `test_the_migration_is_reversible_and_re_applies_cleanly` |  |  | 0.64 s |
| ✅ | `test_the_sixteen_user_group_slots_map_slots_one_to_eight_to_the_audiences` |  |  | 0.27 s |
| ✅ | `test_user_group_levels_are_bytes_and_unique_per_revision_and_slot` |  |  | 0.50 s |

### `tests/integration/test_publication.py` — 25 tests, 25 passed

_Publishing the catalogue (docs/21-improvement-ideas.md): I-02 profiles and wrapped PDF, I-03_

| Result | Test | Purpose | Requirements | Time |
|---|---|---|---|---|
| ✅ | `test_administrator_manages_profiles_as_data` |  | BR-016, BR-018, BR-021, FR-100, FR-101, FR-102, FR-103, FR-104, FR-105, FR-106, FR-107, FR-108, FR-110, FR-111, TC-042 | 0.67 s |
| ✅ | `test_applicability_matrix_and_changes_between_versions` |  | BR-016, BR-018, BR-021, FR-100, FR-101, FR-102, FR-103, FR-104, FR-105, FR-106, FR-107, FR-108, FR-110, FR-111, TC-042 | 2.47 s |
| ✅ | `test_audience_export_only_contains_codes_the_audience_may_see` |  | BR-016, BR-018, BR-021, FR-100, FR-101, FR-102, FR-103, FR-104, FR-105, FR-106, FR-107, FR-108, FR-110, FR-111, TC-042 | 2.16 s |
| ✅ | `test_bundle_contains_the_file_and_a_manifest_that_matches` |  | BR-016, BR-018, BR-021, FR-100, FR-101, FR-102, FR-103, FR-104, FR-105, FR-106, FR-107, FR-108, FR-110, FR-111, TC-042 | 1.21 s |
| ✅ | `test_covert_visibility_is_data_an_administrator_can_flip` |  | BR-016, BR-018, BR-021, FR-100, FR-101, FR-102, FR-103, FR-104, FR-105, FR-106, FR-107, FR-108, FR-110, FR-111, TC-042 | 1.24 s |
| ✅ | `test_customer_profile_applies_its_default_audience_and_working_set_refuses_audiences` |  | BR-016, BR-018, BR-021, FR-100, FR-101, FR-102, FR-103, FR-104, FR-105, FR-106, FR-107, FR-108, FR-110, FR-111, TC-042 | 2.02 s |
| ✅ | `test_draft_source_text_cannot_be_translated_yet` |  | BR-016, BR-018, BR-021, FR-100, FR-101, FR-102, FR-103, FR-104, FR-105, FR-106, FR-107, FR-108, FR-110, FR-111, TC-042 | 0.70 s |
| ✅ | `test_export_history_lists_hashes_per_release` |  | BR-016, BR-018, BR-021, FR-100, FR-101, FR-102, FR-103, FR-104, FR-105, FR-106, FR-107, FR-108, FR-110, FR-111, TC-042 | 1.71 s |
| ✅ | `test_export_profile_fields_match_the_export_row` |  | BR-016, BR-018, BR-021, FR-100, FR-101, FR-102, FR-103, FR-104, FR-105, FR-106, FR-107, FR-108, FR-110, FR-111, TC-042 | 1.16 s |
| ✅ | `test_offline_bundle_is_one_self_contained_page_with_the_data` |  | BR-016, BR-018, BR-021, FR-100, FR-101, FR-102, FR-103, FR-104, FR-105, FR-106, FR-107, FR-108, FR-110, FR-111, TC-042 | 1.33 s |
| ✅ | `test_offline_bundle_respects_audiences_and_needs_a_published_release` |  | BR-016, BR-018, BR-021, FR-100, FR-101, FR-102, FR-103, FR-104, FR-105, FR-106, FR-107, FR-108, FR-110, FR-111, TC-042 | 2.27 s |
| ✅ | `test_pdf_cells_are_wrapped_not_truncated` |  | BR-016, BR-018, BR-021, FR-100, FR-101, FR-102, FR-103, FR-104, FR-105, FR-106, FR-107, FR-108, FR-110, FR-111, TC-042 | 1.49 s |
| ✅ | `test_pdf_column_widths_fit_the_page` |  | BR-016, BR-018, BR-021, FR-100, FR-101, FR-102, FR-103, FR-104, FR-105, FR-106, FR-107, FR-108, FR-110, FR-111, TC-042 | 0.25 s |
| ✅ | `test_pdf_survives_characters_no_font_has` |  | BR-016, BR-018, BR-021, FR-100, FR-101, FR-102, FR-103, FR-104, FR-105, FR-106, FR-107, FR-108, FR-110, FR-111, TC-042 | 0.29 s |
| ✅ | `test_publication_ui_pages_render` |  | BR-016, BR-018, BR-021, FR-100, FR-101, FR-102, FR-103, FR-104, FR-105, FR-106, FR-107, FR-108, FR-110, FR-111, TC-042 | 1.56 s |
| ✅ | `test_release_notes_list_added_changed_and_deprecated` |  | BR-016, BR-018, BR-021, FR-100, FR-101, FR-102, FR-103, FR-104, FR-105, FR-106, FR-107, FR-108, FR-110, FR-111, TC-042 | 4.12 s |
| ✅ | `test_release_targets_limit_the_candidates_and_freeze_at_publish` |  | BR-016, BR-018, BR-021, FR-100, FR-101, FR-102, FR-103, FR-104, FR-105, FR-106, FR-107, FR-108, FR-110, FR-111, TC-042 | 1.86 s |
| ✅ | `test_signed_manifest_detects_edits_to_the_manifest_itself` |  | BR-016, BR-018, BR-021, FR-100, FR-101, FR-102, FR-103, FR-104, FR-105, FR-106, FR-107, FR-108, FR-110, FR-111, TC-042 | 1.20 s |
| ✅ | `test_three_profiles_are_seeded_and_shape_the_columns` |  | BR-016, BR-018, BR-021, FR-100, FR-101, FR-102, FR-103, FR-104, FR-105, FR-106, FR-107, FR-108, FR-110, FR-111, TC-042 | 1.21 s |
| ✅ | `test_translation_validation_worklist_and_carry_over` |  | BR-016, BR-018, BR-021, FR-100, FR-101, FR-102, FR-103, FR-104, FR-105, FR-106, FR-107, FR-108, FR-110, FR-111, TC-042 | 1.81 s |
| ✅ | `test_translation_workflow_with_light_review_and_language_exports` |  | BR-016, BR-018, BR-021, FR-100, FR-101, FR-102, FR-103, FR-104, FR-105, FR-106, FR-107, FR-108, FR-110, FR-111, TC-042 | 2.53 s |
| ✅ | `test_unpublished_release_notes_are_an_administrator_preview` |  | BR-016, BR-018, BR-021, FR-100, FR-101, FR-102, FR-103, FR-104, FR-105, FR-106, FR-107, FR-108, FR-110, FR-111, TC-042 | 1.27 s |
| ✅ | `test_verify_export_cli_works_without_the_database` |  | BR-016, BR-018, BR-021, FR-100, FR-101, FR-102, FR-103, FR-104, FR-105, FR-106, FR-107, FR-108, FR-110, FR-111, TC-042 | 1.25 s |
| ✅ | `test_verify_recognises_an_untouched_file_and_a_tampered_one` |  | BR-016, BR-018, BR-021, FR-100, FR-101, FR-102, FR-103, FR-104, FR-105, FR-106, FR-107, FR-108, FR-110, FR-111, TC-042 | 1.32 s |
| ✅ | `test_version_range_must_be_ordered_and_known` |  | BR-016, BR-018, BR-021, FR-100, FR-101, FR-102, FR-103, FR-104, FR-105, FR-106, FR-107, FR-108, FR-110, FR-111, TC-042 | 0.73 s |

### `tests/integration/test_releases.py` — 6 tests, 6 passed

_FR-040-FR-048, BR-006-BR-008._

| Result | Test | Purpose | Requirements | Time |
|---|---|---|---|---|
| ✅ | `test_cannot_change_items_after_publish` |  | BR-006, BR-008, FR-040, FR-048 | 1.08 s |
| ✅ | `test_csv_export_of_a_release` |  | BR-006, BR-008, FR-040, FR-048 | 1.07 s |
| ✅ | `test_full_database_export_requires_administrator` |  | BR-006, BR-008, FR-040, FR-048 | 0.52 s |
| ✅ | `test_full_release_lifecycle` |  | BR-006, BR-008, FR-040, FR-048 | 1.33 s |
| ✅ | `test_non_admin_cannot_create_release` |  | BR-006, BR-008, FR-040, FR-048 | 0.52 s |
| ✅ | `test_sandbox_revision_rejected_from_release_items` |  | BR-006, BR-008, FR-040, FR-048 | 0.39 s |

### `tests/integration/test_review_aids.py` — 17 tests, 17 passed

_I-23 field comments and review checklists, I-13 evidence attachments, I-11 change sets,_

| Result | Test | Purpose | Requirements | Time |
|---|---|---|---|---|
| ✅ | `test_attachment_permissions_and_removal_rules` |  | FR-124, FR-127, FR-128, FR-129, FR-130, SEC-024, TC-040 | 1.10 s |
| ✅ | `test_attachment_type_size_and_content_checks` |  | FR-124, FR-127, FR-128, FR-129, FR-130, SEC-024, TC-040 | 0.77 s |
| ✅ | `test_author_attaches_evidence_and_reviewers_download_it` |  | FR-124, FR-127, FR-128, FR-129, FR-130, SEC-024, TC-040 | 1.19 s |
| ✅ | `test_auto_assignment_on_submit_is_a_setting` |  | FR-124, FR-127, FR-128, FR-129, FR-130, SEC-024, TC-040 | 0.86 s |
| ✅ | `test_bulk_decision_needs_the_password_once_and_a_wrong_one_counts_once` |  | FR-124, FR-127, FR-128, FR-129, FR-130, SEC-024, TC-040 | 1.36 s |
| ✅ | `test_bulk_decision_skips_what_the_actor_may_not_decide` |  | FR-124, FR-127, FR-128, FR-129, FR-130, SEC-024, TC-040 | 1.11 s |
| ✅ | `test_change_set_groups_requests_and_bulk_decisions_stay_individual` |  | FR-124, FR-127, FR-128, FR-129, FR-130, SEC-024, TC-040 | 1.18 s |
| ✅ | `test_change_set_rules` |  | FR-124, FR-127, FR-128, FR-129, FR-130, SEC-024, TC-040 | 1.11 s |
| ✅ | `test_checklist_is_administrator_managed_and_inactive_items_are_not_required` |  | FR-124, FR-127, FR-128, FR-129, FR-130, SEC-024, TC-040 | 0.68 s |
| ✅ | `test_checklist_must_be_confirmed_to_approve_and_is_recorded` |  | FR-124, FR-127, FR-128, FR-129, FR-130, SEC-024, TC-040 | 0.95 s |
| ✅ | `test_field_comment_rules` |  | FR-124, FR-127, FR-128, FR-129, FR-130, SEC-024, TC-040 | 1.27 s |
| ✅ | `test_least_loaded_reviewer_is_suggested_and_assigned` |  | FR-124, FR-127, FR-128, FR-129, FR-130, SEC-024, TC-040 | 1.04 s |
| ✅ | `test_only_the_commenter_author_or_admin_can_resolve` |  | FR-124, FR-127, FR-128, FR-129, FR-130, SEC-024, TC-040 | 0.94 s |
| ✅ | `test_out_of_office_reviewers_are_not_auto_assigned` |  | FR-124, FR-127, FR-128, FR-129, FR-130, SEC-024, TC-040 | 0.90 s |
| ✅ | `test_rejection_does_not_need_the_checklist` |  | FR-124, FR-127, FR-128, FR-129, FR-130, SEC-024, TC-040 | 0.89 s |
| ✅ | `test_removing_a_draft_attachment_deletes_the_file_and_withdrawal_purges_all` |  | FR-124, FR-127, FR-128, FR-129, FR-130, SEC-024, TC-040 | 0.71 s |
| ✅ | `test_reviewer_comments_on_a_field_and_the_author_sees_and_resolves_it` |  | FR-124, FR-127, FR-128, FR-129, FR-130, SEC-024, TC-040 | 1.14 s |

### `tests/integration/test_roles_and_languages.py` — 40 tests, 40 passed

_The StCd Owner role, the role colours, who may create users and hand out roles, and the three_

| Result | Test | Purpose | Requirements | Time |
|---|---|---|---|---|
| ✅ | `test_a_string_missing_from_a_catalogue_shows_in_english` | Every language is complete (FR-167), but a string that is ever missing must still show. | FR-167 | 0.71 s |
| ✅ | `test_arabic_is_right_to_left_but_identifiers_codes_and_numbers_stay_as_they_are` |  | BR-024, FR-010, FR-012, FR-156, FR-157, SEC-032, TC-054 | 0.80 s |
| ✅ | `test_each_added_language_translates_the_login_page_and_falls_back_to_english[ar-\u062a\u0633\u062c\u064a\u0644 \u0627\u0644\u062f\u062e\u0648\u0644]` |  | BR-024, FR-010, FR-012, FR-156, FR-157, SEC-032, TC-054 | 0.32 s |
| ✅ | `test_each_added_language_translates_the_login_page_and_falls_back_to_english[bn-\u09b2\u0997 \u0987\u09a8]` |  | BR-024, FR-010, FR-012, FR-156, FR-157, SEC-032, TC-054 | 0.33 s |
| ✅ | `test_each_added_language_translates_the_login_page_and_falls_back_to_english[da-Log ind]` |  | BR-024, FR-010, FR-012, FR-156, FR-157, SEC-032, TC-054 | 0.31 s |
| ✅ | `test_each_added_language_translates_the_login_page_and_falls_back_to_english[es-Iniciar sesi\xf3n]` |  | BR-024, FR-010, FR-012, FR-156, FR-157, SEC-032, TC-054 | 0.32 s |
| ✅ | `test_each_added_language_translates_the_login_page_and_falls_back_to_english[fr-Se connecter]` |  | BR-024, FR-010, FR-012, FR-156, FR-157, SEC-032, TC-054 | 0.60 s |
| ✅ | `test_each_added_language_translates_the_login_page_and_falls_back_to_english[gu-\u0ab2\u0ac9\u0a97 \u0a87\u0aa8]` |  | BR-024, FR-010, FR-012, FR-156, FR-157, SEC-032, TC-054 | 0.34 s |
| ✅ | `test_each_added_language_translates_the_login_page_and_falls_back_to_english[hi-\u0932\u0949\u0917 \u0907\u0928 \u0915\u0930\u0947\u0902]` |  | BR-024, FR-010, FR-012, FR-156, FR-157, SEC-032, TC-054 | 0.33 s |
| ✅ | `test_each_added_language_translates_the_login_page_and_falls_back_to_english[it-Accedi]` |  | BR-024, FR-010, FR-012, FR-156, FR-157, SEC-032, TC-054 | 0.33 s |
| ✅ | `test_each_added_language_translates_the_login_page_and_falls_back_to_english[ka-\u10e8\u10d4\u10e1\u10d5\u10da\u10d0]` |  | BR-024, FR-010, FR-012, FR-156, FR-157, SEC-032, TC-054 | 0.32 s |
| ✅ | `test_each_added_language_translates_the_login_page_and_falls_back_to_english[kn-\u0cb2\u0cbe\u0c97\u0ccd \u0c87\u0ca8\u0ccd]` |  | BR-024, FR-010, FR-012, FR-156, FR-157, SEC-032, TC-054 | 0.63 s |
| ✅ | `test_each_added_language_translates_the_login_page_and_falls_back_to_english[ml-\u0d32\u0d4b\u0d17\u0d3f\u0d7b]` |  | BR-024, FR-010, FR-012, FR-156, FR-157, SEC-032, TC-054 | 0.31 s |
| ✅ | `test_each_added_language_translates_the_login_page_and_falls_back_to_english[mr-\u0932\u0949\u0917 \u0907\u0928]` |  | BR-024, FR-010, FR-012, FR-156, FR-157, SEC-032, TC-054 | 0.31 s |
| ✅ | `test_each_added_language_translates_the_login_page_and_falls_back_to_english[or-\u0b32\u0b17\u0b4d \u0b07\u0b28\u0b4d]` |  | BR-024, FR-010, FR-012, FR-156, FR-157, SEC-032, TC-054 | 0.31 s |
| ✅ | `test_each_added_language_translates_the_login_page_and_falls_back_to_english[pa-\u0a32\u0a3e\u0a17 \u0a07\u0a28]` |  | BR-024, FR-010, FR-012, FR-156, FR-157, SEC-032, TC-054 | 0.32 s |
| ✅ | `test_each_added_language_translates_the_login_page_and_falls_back_to_english[ta-\u0b89\u0bb3\u0bcd\u0ba8\u0bc1\u0bb4\u0bc8]` |  | BR-024, FR-010, FR-012, FR-156, FR-157, SEC-032, TC-054 | 0.33 s |
| ✅ | `test_each_added_language_translates_the_login_page_and_falls_back_to_english[te-\u0c32\u0c3e\u0c17\u0c3f\u0c28\u0c4d]` |  | BR-024, FR-010, FR-012, FR-156, FR-157, SEC-032, TC-054 | 0.32 s |
| ✅ | `test_each_added_language_translates_the_login_page_and_falls_back_to_english[ur-\u0644\u0627\u06af \u0627\u0646]` |  | BR-024, FR-010, FR-012, FR-156, FR-157, SEC-032, TC-054 | 0.32 s |
| ✅ | `test_only_an_administrator_creates_users` |  | BR-024, FR-010, FR-012, FR-156, FR-157, SEC-032, TC-054 | 1.18 s |
| ✅ | `test_other_roles_cannot_open_the_user_list` |  | BR-024, FR-010, FR-012, FR-156, FR-157, SEC-032, TC-054 | 0.83 s |
| ✅ | `test_the_administrator_still_gives_every_role` |  | BR-024, FR-010, FR-012, FR-156, FR-157, SEC-032, TC-054 | 0.95 s |
| ✅ | `test_the_catalogues_agree_and_only_translate_real_strings` |  | BR-024, FR-010, FR-012, FR-156, FR-157, SEC-032, TC-054 | 0.70 s |
| ✅ | `test_the_choice_of_an_added_language_is_remembered_for_the_user` |  | BR-024, FR-010, FR-012, FR-156, FR-157, SEC-032, TC-054 | 1.01 s |
| ✅ | `test_the_language_names_have_the_country_letters_left_and_the_flag_right` |  | BR-024, FR-010, FR-012, FR-156, FR-157, SEC-032, TC-054 | 0.26 s |
| ✅ | `test_the_last_administrator_is_still_protected` |  | BR-024, FR-010, FR-012, FR-156, FR-157, SEC-032, TC-054 | 0.65 s |
| ✅ | `test_the_levels_order_the_roles_and_red_is_the_highest` |  | BR-024, FR-010, FR-012, FR-156, FR-157, SEC-032, TC-054 | 0.00 s |
| ✅ | `test_the_menu_shows_letters_left_and_a_drawn_flag_right_for_every_language` |  | BR-024, FR-010, FR-012, FR-156, FR-157, SEC-032, TC-054 | 0.71 s |
| ✅ | `test_the_stcd_owner_cannot_reach_the_other_roles[admin-VIEWER]` |  | BR-024, FR-010, FR-012, FR-156, FR-157, SEC-032, TC-054 | 0.60 s |
| ✅ | `test_the_stcd_owner_cannot_reach_the_other_roles[chief_engineer-REVIEWER]` |  | BR-024, FR-010, FR-012, FR-156, FR-157, SEC-032, TC-054 | 0.61 s |
| ✅ | `test_the_stcd_owner_cannot_reach_the_other_roles[engineer-ADMINISTRATOR]` |  | BR-024, FR-010, FR-012, FR-156, FR-157, SEC-032, TC-054 | 0.63 s |
| ✅ | `test_the_stcd_owner_cannot_reach_the_other_roles[reviewer-STCD_OWNER]` |  | BR-024, FR-010, FR-012, FR-156, FR-157, SEC-032, TC-054 | 0.60 s |
| ✅ | `test_the_stcd_owner_cannot_reach_the_other_roles[stcd_owner-VIEWER]` |  | BR-024, FR-010, FR-012, FR-156, FR-157, SEC-032, TC-054 | 0.60 s |
| ✅ | `test_the_stcd_owner_cannot_reach_the_other_roles[viewer-CHIEF_ENGINEER]` |  | BR-024, FR-010, FR-012, FR-156, FR-157, SEC-032, TC-054 | 0.61 s |
| ✅ | `test_the_stcd_owner_changes_nothing_but_the_role` |  | BR-024, FR-010, FR-012, FR-156, FR-157, SEC-032, TC-054 | 0.61 s |
| ✅ | `test_the_stcd_owner_moves_users_between_viewer_engineer_and_reviewer` |  | BR-024, FR-010, FR-012, FR-156, FR-157, SEC-032, TC-054 | 0.63 s |
| ✅ | `test_the_stcd_owner_reads_the_workflow_but_changes_nothing_in_it` |  | BR-024, FR-010, FR-012, FR-156, FR-157, SEC-032, TC-054 | 0.82 s |
| ✅ | `test_the_stcd_owner_sees_the_list_without_the_administrator_forms` |  | BR-024, FR-010, FR-012, FR-156, FR-157, SEC-032, TC-054 | 0.80 s |
| ✅ | `test_the_user_page_colours_every_role_and_red_is_the_administrator` |  | BR-024, FR-010, FR-012, FR-156, FR-157, SEC-032, TC-054 | 0.77 s |
| ✅ | `test_who_may_change_which_role_to_which` |  | BR-024, FR-010, FR-012, FR-156, FR-157, SEC-032, TC-054 | 0.00 s |

### `tests/integration/test_schema_migration.py` — 14 tests, 14 passed

_US-003/US-004 acceptance criteria: fresh DB matches docs/artifacts/schema.sql_

| Result | Test | Purpose | Requirements | Time |
|---|---|---|---|---|
| ✅ | `test_all_documented_tables_exist` |  | US-003, US-004 | 0.27 s |
| ✅ | `test_first_subgroup_of_every_main_group_covers_the_first_200_numbers` | Rule of 2026-10-22: e.g. Tower 5000-5199, Generator 2000-2199; the next | US-003, US-004 | 0.26 s |
| ✅ | `test_foreign_keys_enforced` | SEC/BR data-integrity depends on FK enforcement being on for every | US-003, US-004 | 0.25 s |
| ✅ | `test_functional_system_group_code_is_reused_for_hub_controller` | WTUR and WROT are each intentionally reused for a second, | US-003, US-004 | 0.26 s |
| ✅ | `test_hub_sub_bands_are_aligned_to_the_hundreds_of_their_prefix` | docs/05-governance-handbook.md section 2: `123xx` owns 12300-12399; a band shorter than a | US-003, US-004 | 0.26 s |
| ✅ | `test_nineteen_languages_seeded_with_country_letters_left_and_the_flag_right` |  | US-003, US-004 | 0.54 s |
| ✅ | `test_no_placeholder_group_is_seeded` | Only the 12 real groups exist out of the box; free ranges stay free. | US-003, US-004 | 0.26 s |
| ✅ | `test_only_sandbox_status_codes_can_be_deleted` | Exercises trg_prevent_nonsandbox_delete from docs/artifacts/schema.sql. | US-003, US-004 | 0.26 s |
| ✅ | `test_second_migration_is_reversible_and_idempotent` | A database already at the earlier baseline is brought up to date by the | US-003, US-004 | 0.83 s |
| ✅ | `test_six_roles_seeded` |  | US-003, US-004 | 0.28 s |
| ✅ | `test_subgroup_codes_have_no_dash_and_no_letter_after_the_x` |  | US-003, US-004 | 0.55 s |
| ✅ | `test_thirty_eight_functional_subgroups_seeded` |  | US-003, US-004 | 0.26 s |
| ✅ | `test_three_turbine_platforms_seeded` |  | US-003, US-004 | 0.26 s |
| ✅ | `test_twelve_functional_system_groups_seeded` | 9 Main Controller groups + 3 Hub Controller groups (WTUR/WROT/WPPD | US-003, US-004 | 0.26 s |

### `tests/integration/test_schema_upgrade.py` — 16 tests, 16 passed

_Upgrading a database that was created by the previous release (Alembic d6f8b0c2e4a3, schema v3)_

| Result | Test | Purpose | Requirements | Time |
|---|---|---|---|---|
| ✅ | `test_a_second_upgrade_is_a_no_op_and_the_downgrade_returns_to_v3_with_the_data` |  | AUD-074, BR-016, FR-147, FR-148, TC-045 | 1.23 s |
| ✅ | `test_an_upgraded_database_has_the_same_shape_as_a_fresh_one` |  | AUD-074, BR-016, FR-147, FR-148, TC-045 | 0.94 s |
| ✅ | `test_covert_is_not_visible_and_the_other_audiences_still_are` |  | AUD-074, BR-016, FR-147, FR-148, TC-045 | 0.66 s |
| ✅ | `test_every_trigger_of_a_fresh_database_exists_after_the_upgrade` |  | AUD-074, BR-016, FR-147, FR-148, TC-045 | 1.24 s |
| ✅ | `test_existing_data_survives_the_upgrade` |  | AUD-074, BR-016, FR-147, FR-148, TC-045 | 0.67 s |
| ✅ | `test_hub_groups_become_hub_controller_groups` |  | AUD-074, BR-016, FR-147, FR-148, TC-045 | 0.65 s |
| ✅ | `test_hub_sub_bands_are_shifted_to_the_hundreds_by_the_upgrade` | The v3 database still has the legacy x001 bands; the upgrade aligns them. | AUD-074, BR-016, FR-147, FR-148, TC-045 | 0.66 s |
| ✅ | `test_import_job_is_rebuilt_for_programs_without_losing_rows_or_references` | v4.2: the CHECK of import_job.source_format has to widen to 'ST', which SQLite can only do by | AUD-074, BR-016, FR-147, FR-148, TC-045 | 17.31 s |
| ✅ | `test_new_columns_default_sensibly_on_old_rows` |  | AUD-074, BR-016, FR-147, FR-148, TC-045 | 0.64 s |
| ✅ | `test_old_audit_rows_are_chained_and_the_chain_verifies` |  | AUD-074, BR-016, FR-147, FR-148, TC-045 | 17.37 s |
| ✅ | `test_the_languages_and_export_profiles_are_seeded` |  | AUD-074, BR-016, FR-147, FR-148, TC-045 | 0.64 s |
| ✅ | `test_the_migrated_hash_equals_what_the_application_would_have_written` | Migration and application share one canonical form (app/audit_hash.py). | AUD-074, BR-016, FR-147, FR-148, TC-045 | 0.69 s |
| ✅ | `test_the_search_index_is_filled_with_the_old_codes` |  | AUD-074, BR-016, FR-147, FR-148, TC-045 | 0.65 s |
| ✅ | `test_the_subgroup_codes_lose_their_letters_and_dashes_in_the_upgrade` |  | AUD-074, BR-016, FR-147, FR-148, TC-045 | 0.67 s |
| ✅ | `test_the_table_rebuilds_leave_every_foreign_key_intact` | import_job (revision b3f5a7c9d124) and user (d4a6c8e0f236) are rebuilt to widen a CHECK; the | AUD-074, BR-016, FR-147, FR-148, TC-045 | 17.59 s |
| ✅ | `test_the_upgraded_database_works_for_a_whole_workflow` |  | AUD-074, BR-016, FR-147, FR-148, TC-045 | 0.78 s |

### `tests/integration/test_search_and_help.py` — 16 tests, 16 passed

_I-31 ranked, typo-tolerant search (with a substring fallback), I-35 in-app help content._

| Result | Test | Purpose | Requirements | Time |
|---|---|---|---|---|
| ✅ | `test_a_hit_in_the_title_outranks_a_hit_in_the_description` |  | FR-148, FR-154, TC-047 | 0.69 s |
| ✅ | `test_a_new_code_and_an_edit_are_reflected_without_a_rebuild` |  | FR-148, FR-154, TC-047 | 0.71 s |
| ✅ | `test_every_lifecycle_state_role_and_cr_state_has_help` |  | FR-148, FR-154, TC-047 | 0.00 s |
| ✅ | `test_help_texts_are_plain_sentences` |  | FR-148, FR-154, TC-047 | 0.00 s |
| ✅ | `test_new_terms_are_in_the_project_glossary` |  | FR-148, FR-154, TC-047 | 0.00 s |
| ✅ | `test_prefix_and_multi_word_search` |  | FR-148, FR-154, TC-047 | 0.70 s |
| ✅ | `test_search_ignores_fts_operators_and_punctuation` |  | FR-148, FR-154, TC-047 | 0.71 s |
| ✅ | `test_several_misspelt_words_are_all_tolerated_together` | Each word may expand to a group of close spellings; the groups must be joined with AND | FR-148, FR-154, TC-047 | 1.07 s |
| ✅ | `test_state_badges_carry_their_glossary_text_as_a_tooltip` |  | FR-148, FR-154, TC-047 | 0.76 s |
| ✅ | `test_the_change_request_screen_says_what_happens_next` |  | FR-148, FR-154, TC-047 | 0.84 s |
| ✅ | `test_the_help_page_shows_the_quick_start_of_the_signed_in_role` |  | FR-148, FR-154, TC-047 | 1.10 s |
| ✅ | `test_the_roles_and_states_are_named_in_the_project_glossary` |  | FR-148, FR-154, TC-047 | 0.00 s |
| ✅ | `test_the_search_box_works_on_the_ui_list` |  | FR-148, FR-154, TC-047 | 0.77 s |
| ✅ | `test_the_search_index_exists_on_a_fresh_database` |  | FR-148, FR-154, TC-047 | 16.97 s |
| ✅ | `test_typos_still_find_the_code` |  | FR-148, FR-154, TC-047 | 0.70 s |
| ✅ | `test_without_the_index_search_falls_back_to_substrings` |  | FR-148, FR-154, TC-047 | 0.80 s |

### `tests/integration/test_sla_and_notifications.py` — 16 tests, 16 passed

_I-08 SLA ages, stalled requests, in-app notices and reminders (docs/21-improvement-ideas.md),_

| Result | Test | Purpose | Requirements | Time |
|---|---|---|---|---|
| ✅ | `test_assigned_reviewer_only_and_pending_approval_goes_to_chief_engineers` |  | FR-120, FR-121, FR-122, FR-123, TC-041 | 1.07 s |
| ✅ | `test_business_days_skip_weekends` |  | FR-120, FR-121, FR-122, FR-123, TC-041 | 0.00 s |
| ✅ | `test_kpis_are_computed_from_stored_timestamps` |  | FR-120, FR-121, FR-122, FR-123, TC-041 | 1.36 s |
| ✅ | `test_kpis_flag_an_incomplete_audit_trail_and_an_ownerless_code` |  | FR-120, FR-121, FR-122, FR-123, TC-041 | 1.27 s |
| ✅ | `test_kpis_without_data_do_not_divide_by_zero` |  | FR-120, FR-121, FR-122, FR-123, TC-041 | 0.27 s |
| ✅ | `test_levels_follow_the_thresholds` |  | FR-120, FR-121, FR-122, FR-123, TC-041 | 0.83 s |
| ✅ | `test_mail_failure_never_breaks_the_reminder_job` |  | FR-120, FR-121, FR-122, FR-123, TC-041 | 0.79 s |
| ✅ | `test_mark_all_read` |  | FR-120, FR-121, FR-122, FR-123, TC-041 | 0.89 s |
| ✅ | `test_queues_show_the_waiting_time` |  | FR-120, FR-121, FR-122, FR-123, TC-041 | 0.89 s |
| ✅ | `test_reminders_also_reach_a_covering_delegate_and_can_be_mailed` |  | FR-120, FR-121, FR-122, FR-123, TC-041 | 0.90 s |
| ✅ | `test_reminders_go_to_whoever_holds_the_next_decision_once_a_day` |  | FR-120, FR-121, FR-122, FR-123, TC-041 | 1.03 s |
| ✅ | `test_send_reminders_cli` |  | FR-120, FR-121, FR-122, FR-123, TC-041 | 0.25 s |
| ✅ | `test_stalled_view_and_reassignment` |  | FR-120, FR-121, FR-122, FR-123, TC-041 | 1.24 s |
| ✅ | `test_the_default_thresholds_are_the_documented_ones` |  | FR-120, FR-121, FR-122, FR-123, TC-041 | 0.26 s |
| ✅ | `test_thresholds_are_configurable_and_validated` |  | FR-120, FR-121, FR-122, FR-123, TC-041 | 0.71 s |
| ✅ | `test_withdrawn_cr_notices_are_removed_with_it` |  | FR-120, FR-121, FR-122, FR-123, TC-041 | 1.14 s |

### `tests/integration/test_st_import.py` — 29 tests, 29 passed

_Status code import from the generated StCd_<n>.st programs and the legacy -> new mapping_

| Result | Test | Purpose | Requirements | Time |
|---|---|---|---|---|
| ✅ | `test_a_file_without_programs_or_too_large_is_refused_cleanly` |  | BR-023, FR-048o, FR-048p, FR-048q, FR-048r, FR-048s, FR-048t, FR-048u, FR-048v, FR-048w, SEC-031, TC-053 | 0.00 s |
| ✅ | `test_a_hub_program_keeps_its_legacy_number_and_gets_the_new_one_from_the_table` |  | BR-023, FR-048o, FR-048p, FR-048q, FR-048r, FR-048s, FR-048t, FR-048u, FR-048v, FR-048w, SEC-031, TC-053 | 0.01 s |
| ✅ | `test_a_legacy_hub_number_missing_from_the_table_leaves_no_identifier` |  | BR-023, FR-048o, FR-048p, FR-048q, FR-048r, FR-048s, FR-048t, FR-048u, FR-048v, FR-048w, SEC-031, TC-053 | 0.00 s |
| ✅ | `test_a_legacy_number_that_belongs_to_another_code_blocks_the_program` |  | BR-023, FR-048o, FR-048p, FR-048q, FR-048r, FR-048s, FR-048t, FR-048u, FR-048v, FR-048w, SEC-031, TC-053 | 0.43 s |
| ✅ | `test_a_number_defined_twice_in_one_upload_blocks_the_second` |  | BR-023, FR-048o, FR-048p, FR-048q, FR-048r, FR-048s, FR-048t, FR-048u, FR-048v, FR-048w, SEC-031, TC-053 | 0.38 s |
| ✅ | `test_a_preview_belongs_to_its_uploader_and_expires` |  | BR-023, FR-048o, FR-048p, FR-048q, FR-048r, FR-048s, FR-048t, FR-048u, FR-048v, FR-048w, SEC-031, TC-053 | 0.55 s |
| ✅ | `test_a_second_preview_shows_what_is_already_there_and_confirm_refuses_it` |  | BR-023, FR-048o, FR-048p, FR-048q, FR-048r, FR-048s, FR-048t, FR-048u, FR-048v, FR-048w, SEC-031, TC-053 | 0.58 s |
| ✅ | `test_a_used_prg_idx_is_a_warning_and_is_not_stored_twice` |  | BR-023, FR-048o, FR-048p, FR-048q, FR-048r, FR-048s, FR-048t, FR-048u, FR-048v, FR-048w, SEC-031, TC-053 | 0.47 s |
| ✅ | `test_a_zip_and_loose_files_are_read_alike_and_other_files_are_noted` |  | BR-023, FR-048o, FR-048p, FR-048q, FR-048r, FR-048s, FR-048t, FR-048u, FR-048v, FR-048w, SEC-031, TC-053 | 0.38 s |
| ✅ | `test_a_zip_that_unpacks_too_large_is_refused` |  | BR-023, FR-048o, FR-048p, FR-048q, FR-048r, FR-048s, FR-048t, FR-048u, FR-048v, FR-048w, SEC-031, TC-053 | 0.37 s |
| ✅ | `test_allocation_skips_a_reserved_number_and_a_manual_override_cannot_take_it` |  | BR-023, FR-048o, FR-048p, FR-048q, FR-048r, FR-048s, FR-048t, FR-048u, FR-048v, FR-048w, SEC-031, TC-053 | 0.44 s |
| ✅ | `test_an_administrator_cannot_override_a_reserved_identifier` |  | BR-023, FR-048o, FR-048p, FR-048q, FR-048r, FR-048s, FR-048t, FR-048u, FR-048v, FR-048w, SEC-031, TC-053 | 0.81 s |
| ✅ | `test_an_expired_preview_is_refused_and_removed` |  | BR-023, FR-048o, FR-048p, FR-048q, FR-048r, FR-048s, FR-048t, FR-048u, FR-048v, FR-048w, SEC-031, TC-053 | 0.40 s |
| ✅ | `test_confirm_creates_drafts_that_reserve_their_numbers_in_one_change_set` |  | BR-023, FR-048o, FR-048p, FR-048q, FR-048r, FR-048s, FR-048t, FR-048u, FR-048v, FR-048w, SEC-031, TC-053 | 0.48 s |
| ✅ | `test_confirming_without_a_selection_takes_every_ready_program` |  | BR-023, FR-048o, FR-048p, FR-048q, FR-048r, FR-048s, FR-048t, FR-048u, FR-048v, FR-048w, SEC-031, TC-053 | 0.46 s |
| ✅ | `test_nothing_usable_is_a_clear_error` |  | BR-023, FR-048o, FR-048p, FR-048q, FR-048r, FR-048s, FR-048t, FR-048u, FR-048v, FR-048w, SEC-031, TC-053 | 0.36 s |
| ✅ | `test_only_engineers_and_administrators_import` |  | BR-023, FR-048o, FR-048p, FR-048q, FR-048r, FR-048s, FR-048t, FR-048u, FR-048v, FR-048w, SEC-031, TC-053 | 0.36 s |
| ✅ | `test_proposal_two_places_the_hub_programs_inside_the_main_scheme` |  | BR-023, FR-048o, FR-048p, FR-048q, FR-048r, FR-048s, FR-048t, FR-048u, FR-048v, FR-048w, SEC-031, TC-053 | 0.37 s |
| ✅ | `test_submitting_issues_exactly_the_reserved_number` |  | BR-023, FR-048o, FR-048p, FR-048q, FR-048r, FR-048s, FR-048t, FR-048u, FR-048v, FR-048w, SEC-031, TC-053 | 1.10 s |
| ✅ | `test_the_bundled_hub_table_equals_the_workbook` |  | BR-023, FR-048o, FR-048p, FR-048q, FR-048r, FR-048s, FR-048t, FR-048u, FR-048v, FR-048w, SEC-031, TC-053 | 0.03 s |
| ✅ | `test_the_controller_can_be_forced_for_a_file` |  | BR-023, FR-048o, FR-048p, FR-048q, FR-048r, FR-048s, FR-048t, FR-048u, FR-048v, FR-048w, SEC-031, TC-053 | 0.35 s |
| ✅ | `test_the_database_refuses_a_second_reservation_of_a_number` |  | BR-023, FR-048o, FR-048p, FR-048q, FR-048r, FR-048s, FR-048t, FR-048u, FR-048v, FR-048w, SEC-031, TC-053 | 0.42 s |
| ✅ | `test_the_draft_carries_the_attributes_of_the_program` |  | BR-023, FR-048o, FR-048p, FR-048q, FR-048r, FR-048s, FR-048t, FR-048u, FR-048v, FR-048w, SEC-031, TC-053 | 0.77 s |
| ✅ | `test_the_mapping_exports_as_csv_and_xlsx` |  | BR-023, FR-048o, FR-048p, FR-048q, FR-048r, FR-048s, FR-048t, FR-048u, FR-048v, FR-048w, SEC-031, TC-053 | 0.48 s |
| ✅ | `test_the_mapping_is_not_for_viewers` |  | BR-023, FR-048o, FR-048p, FR-048q, FR-048r, FR-048s, FR-048t, FR-048u, FR-048v, FR-048w, SEC-031, TC-053 | 0.36 s |
| ✅ | `test_the_mapping_lists_legacy_to_new_and_counts_codes_without_a_legacy_number` |  | BR-023, FR-048o, FR-048p, FR-048q, FR-048r, FR-048s, FR-048t, FR-048u, FR-048v, FR-048w, SEC-031, TC-053 | 0.56 s |
| ✅ | `test_the_preview_lists_every_program_and_creates_nothing` |  | BR-023, FR-048o, FR-048p, FR-048q, FR-048r, FR-048s, FR-048t, FR-048u, FR-048v, FR-048w, SEC-031, TC-053 | 0.75 s |
| ✅ | `test_the_reader_takes_the_attributes_of_a_main_controller_program` |  | BR-023, FR-048o, FR-048p, FR-048q, FR-048r, FR-048s, FR-048t, FR-048u, FR-048v, FR-048w, SEC-031, TC-053 | 0.01 s |
| ✅ | `test_the_source_of_an_imported_code_can_be_read` |  | BR-023, FR-048o, FR-048p, FR-048q, FR-048r, FR-048s, FR-048t, FR-048u, FR-048v, FR-048w, SEC-031, TC-053 | 0.74 s |

### `tests/integration/test_status_codes.py` — 9 tests, 9 passed

_FR-020-FR-029, FR-053-FR-056, FR-060-FR-064._

| Result | Test | Purpose | Requirements | Time |
|---|---|---|---|---|
| ✅ | `test_admin_sandbox_gets_identifier_immediately` |  | FR-020, FR-029, FR-053, FR-056, FR-060, FR-064 | 0.70 s |
| ✅ | `test_create_rejects_invalid_fields` |  | FR-020, FR-029, FR-053, FR-056, FR-060, FR-064 | 0.38 s |
| ✅ | `test_create_rejects_missing_functional_subgroup` | BR-013: mandatory, never optional (corrected 2026-09-17). | BR-013 | 0.37 s |
| ✅ | `test_engineer_can_create_draft_with_no_identifier` |  | FR-020, FR-029, FR-053, FR-056, FR-060, FR-064 | 0.38 s |
| ✅ | `test_non_admin_cannot_create_sandbox` |  | FR-020, FR-029, FR-053, FR-056, FR-060, FR-064 | 0.39 s |
| ✅ | `test_sandbox_delete_requires_admin_and_sandbox_flag` |  | FR-020, FR-029, FR-053, FR-056, FR-060, FR-064 | 0.58 s |
| ✅ | `test_search_defaults_exclude_sandbox` |  | FR-020, FR-029, FR-053, FR-056, FR-060, FR-064 | 0.42 s |
| ✅ | `test_viewer_cannot_create_status_code` |  | FR-020, FR-029, FR-053, FR-056, FR-060, FR-064 | 0.35 s |
| ✅ | `test_viewer_cannot_see_draft_status_codes` |  | FR-020, FR-029, FR-053, FR-056, FR-060, FR-064 | 0.51 s |

### `tests/integration/test_step_up_and_delegation.py` — 16 tests, 16 passed

_I-17 step-up re-authentication (SEC-026) and I-16 delegation / out-of-office cover._

| Result | Test | Purpose | Requirements | Time |
|---|---|---|---|---|
| ✅ | `test_admin_signoff_chief_decision_publish_and_full_export_all_need_the_password` |  | BR-017, BR-022, FR-125, FR-126, SEC-011, SEC-026, TC-038 | 1.36 s |
| ✅ | `test_correct_password_lets_the_signoff_through_and_is_audited` |  | BR-017, BR-022, FR-125, FR-126, SEC-011, SEC-026, TC-038 | 1.22 s |
| ✅ | `test_deactivated_delegator_ends_the_delegation` |  | BR-017, BR-022, FR-125, FR-126, SEC-011, SEC-026, TC-038 | 1.29 s |
| ✅ | `test_delegate_can_sign_off_as_the_absent_reviewer_and_audit_shows_both` |  | BR-017, BR-022, FR-125, FR-126, SEC-011, SEC-026, TC-038 | 1.30 s |
| ✅ | `test_delegate_sees_the_review_queue_and_a_delegated_chief_engineer_can_approve` |  | BR-017, BR-022, FR-125, FR-126, SEC-011, SEC-026, TC-038 | 1.43 s |
| ✅ | `test_delegating_does_not_grant_other_privileges` |  | BR-017, BR-022, FR-125, FR-126, SEC-011, SEC-026, TC-038 | 0.45 s |
| ✅ | `test_delegation_does_not_lift_segregation_of_duties` | The delegate acts as themselves: the author cannot sign their own CR through a delegation. | BR-017, BR-022, FR-125, FR-126, SEC-011, SEC-026, TC-038 | 0.91 s |
| ✅ | `test_delegation_is_limited_to_its_period_and_can_be_revoked` |  | BR-017, BR-022, FR-125, FR-126, SEC-011, SEC-026, TC-038 | 1.00 s |
| ✅ | `test_delegation_validation_and_who_may_create_it` |  | BR-017, BR-022, FR-125, FR-126, SEC-011, SEC-026, TC-038 | 0.48 s |
| ✅ | `test_one_person_cannot_give_both_review_signoffs_through_a_delegation` |  | BR-017, BR-022, FR-125, FR-126, SEC-011, SEC-026, TC-038 | 1.01 s |
| ✅ | `test_repeated_wrong_passwords_lock_the_account` | The prompt must not be usable to guess a password (same lockout as login). | BR-017, BR-022, FR-125, FR-126, SEC-011, SEC-026, TC-038 | 1.13 s |
| ✅ | `test_reviewer_signoff_without_password_is_refused` |  | BR-017, BR-022, FR-125, FR-126, SEC-011, SEC-026, TC-038 | 0.89 s |
| ✅ | `test_step_up_can_be_switched_off_by_configuration` |  | BR-017, BR-022, FR-125, FR-126, SEC-011, SEC-026, TC-038 | 0.87 s |
| ✅ | `test_ui_decision_forms_carry_a_password_field` |  | BR-017, BR-022, FR-125, FR-126, SEC-011, SEC-026, TC-038 | 1.03 s |
| ✅ | `test_ui_signoff_without_password_shows_an_error` |  | BR-017, BR-022, FR-125, FR-126, SEC-011, SEC-026, TC-038 | 1.01 s |
| ✅ | `test_wrong_password_is_refused_and_audited` |  | BR-017, BR-022, FR-125, FR-126, SEC-011, SEC-026, TC-038 | 0.95 s |

### `tests/integration/test_terminology.py` — 13 tests, 13 passed

_The technical nomenclature: a vocabulary of its own, apart from the interface translations_

| Result | Test | Purpose | Requirements | Time |
|---|---|---|---|---|
| ✅ | `test_a_formula_in_a_cell_is_neutralised_in_the_csv` |  | AUD-077, BR-018, FR-166, SEC-010, TC-061 | 0.65 s |
| ✅ | `test_a_proposal_is_a_draft_until_another_person_approves_it` |  | AUD-077, BR-018, FR-166, SEC-010, TC-061 | 0.92 s |
| ✅ | `test_a_shipped_draft_can_be_approved_by_anybody_who_may_approve_and_all_at_once` |  | AUD-077, BR-018, FR-166, SEC-010, TC-061 | 0.89 s |
| ✅ | `test_an_interface_reviewer_has_no_say_in_the_terminology` |  | AUD-077, BR-018, FR-166, SEC-010, TC-061 | 0.67 s |
| ✅ | `test_everybody_reads_but_only_the_technical_roles_propose` |  | AUD-077, BR-018, FR-166, SEC-010, TC-061 | 1.62 s |
| ✅ | `test_only_the_managers_add_and_change_terms_and_a_new_english_reopens_approvals` |  | AUD-077, BR-018, FR-166, SEC-010, TC-061 | 1.40 s |
| ✅ | `test_send_back_needs_a_note_and_reopens_an_approved_translation` |  | AUD-077, BR-018, FR-166, SEC-010, TC-061 | 1.26 s |
| ✅ | `test_terms_that_are_never_translated_have_no_translation` |  | AUD-077, BR-018, FR-166, SEC-010, TC-061 | 0.27 s |
| ✅ | `test_the_check_finds_interface_strings_that_do_not_use_the_term` |  | AUD-077, BR-018, FR-166, SEC-010, TC-061 | 1.23 s |
| ✅ | `test_the_shipped_terms_agree_with_the_interface_catalogue_where_both_have_the_word` | Role names are interface strings and terms: they must be the same word. | AUD-077, BR-018, FR-166, SEC-010, TC-061 | 0.00 s |
| ✅ | `test_the_vocabulary_is_exported_per_language_and_for_all` |  | AUD-077, BR-018, FR-166, SEC-010, TC-061 | 0.69 s |
| ✅ | `test_the_vocabulary_ships_with_every_term_in_every_language_as_a_draft` |  | AUD-077, BR-018, FR-166, SEC-010, TC-061 | 0.27 s |
| ✅ | `test_validation_of_a_translation` |  | AUD-077, BR-018, FR-166, SEC-010, TC-061 | 0.73 s |

### `tests/integration/test_translation_review.py` — 14 tests, 14 passed

_Translation review in the application (docs/26-translations.md, docs/03-srs.md FR-164): native_

| Result | Test | Purpose | Requirements | Time |
|---|---|---|---|---|
| ✅ | `test_a_completed_review_shows_as_changed_after_a_later_acceptance` |  | AUD-077, BR-018, BR-025, FR-157, FR-161, FR-164, TC-059 | 1.40 s |
| ✅ | `test_a_missing_translation_can_be_proposed_and_accepted` |  | AUD-077, BR-018, BR-025, FR-157, FR-161, FR-164, TC-059 | 1.12 s |
| ✅ | `test_a_proposal_must_keep_the_placeholders_and_an_unclear_string_is_only_noted` |  | AUD-077, BR-018, BR-025, FR-157, FR-161, FR-164, TC-059 | 1.37 s |
| ✅ | `test_a_review_is_completed_only_when_every_string_has_a_verdict_and_is_recorded` |  | AUD-077, BR-018, BR-025, FR-157, FR-161, FR-164, TC-059 | 1.48 s |
| ✅ | `test_a_reviewer_answers_strings_and_is_told_what_is_wrong` |  | AUD-077, BR-018, BR-025, FR-157, FR-161, FR-164, TC-059 | 1.29 s |
| ✅ | `test_a_sheet_that_is_not_one_is_refused_clearly` |  | AUD-077, BR-018, BR-025, FR-157, FR-161, FR-164, TC-059 | 1.20 s |
| ✅ | `test_an_accepted_proposal_is_shown_at_once_and_can_be_taken_back` |  | AUD-077, BR-018, BR-025, FR-157, FR-161, FR-164, TC-059 | 1.43 s |
| ✅ | `test_an_account_that_reviews_has_history_in_the_usage_report` |  | AUD-077, BR-018, BR-025, FR-157, FR-161, FR-164, TC-059 | 0.92 s |
| ✅ | `test_an_unassigned_user_cannot_open_a_review_and_an_unknown_language_is_404` |  | AUD-077, BR-018, BR-025, FR-157, FR-161, FR-164, TC-059 | 0.69 s |
| ✅ | `test_nobody_decides_on_their_own_proposal_and_a_decision_is_final` |  | AUD-077, BR-018, BR-025, FR-157, FR-161, FR-164, TC-059 | 2.10 s |
| ✅ | `test_only_an_administrator_or_an_stcd_owner_assigns_reviewers_and_it_is_audited` |  | AUD-077, BR-018, BR-025, FR-157, FR-161, FR-164, TC-059 | 1.80 s |
| ✅ | `test_right_to_left_languages_are_shown_right_to_left_in_the_review` |  | AUD-077, BR-018, BR-025, FR-157, FR-161, FR-164, TC-059 | 1.34 s |
| ✅ | `test_the_overview_shows_a_reviewer_only_their_languages_and_a_manager_all` |  | AUD-077, BR-018, BR-025, FR-157, FR-161, FR-164, TC-059 | 1.55 s |
| ✅ | `test_the_sheet_can_be_downloaded_filled_in_offline_and_uploaded` |  | AUD-077, BR-018, BR-025, FR-157, FR-161, FR-164, TC-059 | 2.17 s |

### `tests/integration/test_ui_screens.py` — 18 tests, 18 passed

_S1–S19 server-rendered UI: every screen renders for the roles that can_

| Result | Test | Purpose | Requirements | Time |
|---|---|---|---|---|
| ✅ | `test_admin_signoff_form_offers_access_override_and_submit_override` |  | NFR-007a, TC-036, UAT-13 | 1.11 s |
| ✅ | `test_comments_api_validates_and_is_role_restricted` |  | NFR-007a, TC-036, UAT-13 | 0.84 s |
| ✅ | `test_cr_detail_shows_role_specific_controls` |  | NFR-007a, TC-036, UAT-13 | 0.91 s |
| ✅ | `test_default_role_for_new_user_is_viewer` | SEC-012. | SEC-012 | 0.43 s |
| ✅ | `test_draft_cr_page_says_it_must_still_be_submitted` |  | NFR-007a, TC-036, UAT-13 | 1.39 s |
| ✅ | `test_every_screen_renders_for_an_administrator` |  | NFR-007a, TC-036, UAT-13 | 1.64 s |
| ✅ | `test_failed_form_submission_keeps_every_entered_value` | NFR-007a / TC-036 / UAT-13. | NFR-007a, TC-036, UAT-13 | 0.83 s |
| ✅ | `test_lookup_description_is_editable_and_flows_to_form_and_api` |  | NFR-007a, TC-036, UAT-13 | 1.02 s |
| ✅ | `test_lookup_selects_carry_inline_help_hooks` | NFR-007b: each lookup-backed select has a help target and per-option text. | NFR-007b | 0.85 s |
| ✅ | `test_people_are_shown_by_name_and_lists_show_the_title` | Authors, signers and commenters appear as "Full Name (Role)", never "User #n"; | NFR-007a, TC-036, UAT-13 | 1.27 s |
| ✅ | `test_role_specific_screens_render[chief_engineer-/change-requests/approval-queue]` |  | NFR-007a, TC-036, UAT-13 | 0.68 s |
| ✅ | `test_role_specific_screens_render[engineer-/change-requests/mine]` |  | NFR-007a, TC-036, UAT-13 | 1.02 s |
| ✅ | `test_role_specific_screens_render[engineer-/exports]` |  | NFR-007a, TC-036, UAT-13 | 0.70 s |
| ✅ | `test_role_specific_screens_render[reviewer-/change-requests/review-queue]` |  | NFR-007a, TC-036, UAT-13 | 0.70 s |
| ✅ | `test_role_specific_screens_render[viewer-/exports]` |  | NFR-007a, TC-036, UAT-13 | 0.70 s |
| ✅ | `test_role_specific_screens_render[viewer-/status-codes]` |  | NFR-007a, TC-036, UAT-13 | 0.72 s |
| ✅ | `test_sign_off_request_listed_on_my_change_requests` |  | NFR-007a, TC-036, UAT-13 | 1.30 s |
| ✅ | `test_ui_comment_reviewer_assignment_and_override_flow` |  | NFR-007a, TC-036, UAT-13 | 1.33 s |

### `tests/integration/test_user_administration.py` — 10 tests, 10 passed

_Viewing, deactivating and deleting users (docs/03-srs.md FR-158, BR-025, SEC-032). An account that_

| Result | Test | Purpose | Requirements | Time |
|---|---|---|---|---|
| ✅ | `test_a_deactivated_account_can_be_activated_again` |  | AUD-076, BR-025, FR-012, FR-158, SEC-032, TC-055 | 0.62 s |
| ✅ | `test_an_account_that_was_never_used_can_be_deleted_and_the_deletion_is_audited` |  | AUD-076, BR-025, FR-012, FR-158, SEC-032, TC-055 | 0.74 s |
| ✅ | `test_an_account_with_history_is_erased_and_the_audit_log_is_untouched` |  | AUD-076, BR-025, FR-012, FR-158, SEC-032, TC-055 | 0.82 s |
| ✅ | `test_deleting_needs_the_administrators_password_and_an_administrator` |  | AUD-076, BR-025, FR-012, FR-158, SEC-032, TC-055 | 1.07 s |
| ✅ | `test_nobody_deletes_their_own_account` |  | AUD-076, BR-025, FR-012, FR-158, SEC-032, TC-055 | 0.61 s |
| ✅ | `test_the_buttons_deactivate_activate_and_delete_through_the_screens` |  | AUD-076, BR-025, FR-012, FR-158, SEC-032, TC-055 | 0.94 s |
| ✅ | `test_the_detail_page_shows_history_and_the_buttons_follow_it` |  | AUD-076, BR-025, FR-012, FR-158, SEC-032, TC-055 | 0.89 s |
| ✅ | `test_the_stcd_owner_sees_view_and_set_role_but_no_delete_or_deactivate` |  | AUD-076, BR-025, FR-012, FR-158, SEC-032, TC-055 | 0.73 s |
| ✅ | `test_the_user_list_offers_view_edit_deactivate_and_delete_to_an_administrator` |  | AUD-076, BR-025, FR-012, FR-158, SEC-032, TC-055 | 0.70 s |
| ✅ | `test_usage_is_open_to_the_user_list_roles_only` |  | AUD-076, BR-025, FR-012, FR-158, SEC-032, TC-055 | 1.14 s |

### `tests/integration/test_users.py` — 7 tests, 7 passed

_FR-010-FR-014, SEC-003 §3 permission matrix, US-009._

| Result | Test | Purpose | Requirements | Time |
|---|---|---|---|---|
| ✅ | `test_admin_can_force_reset_another_users_password` |  | FR-010, FR-014, SEC-003, US-009 | 0.52 s |
| ✅ | `test_admin_can_list_and_create_users` |  | FR-010, FR-014, SEC-003, US-009 | 0.40 s |
| ✅ | `test_can_deactivate_administrator_when_another_remains_active` |  | FR-010, FR-014, SEC-003, US-009 | 0.76 s |
| ✅ | `test_cannot_deactivate_last_active_administrator` |  | FR-010, FR-014, SEC-003, US-009 | 0.34 s |
| ✅ | `test_create_user_rejects_weak_password` |  | FR-010, FR-014, SEC-003, US-009 | 0.36 s |
| ✅ | `test_non_admin_cannot_list_users` |  | FR-010, FR-014, SEC-003, US-009 | 0.36 s |
| ✅ | `test_self_password_change` |  | FR-010, FR-014, SEC-003, US-009 | 0.57 s |

### `tests/integration/test_withdraw_and_reimport.py` — 11 tests, 11 passed

_Withdrawing change requests (several at once) and what a withdrawal does to a program that was_

| Result | Test | Purpose | Requirements | Time |
|---|---|---|---|---|
| ✅ | `test_a_change_request_of_somebody_else_is_refused_and_the_others_go_on` |  | BR-001, BR-026, FR-026, FR-048x, FR-159, FR-160, TC-056 | 0.77 s |
| ✅ | `test_a_changed_program_opens_a_new_revision_of_an_approved_code` |  | BR-001, BR-026, FR-026, FR-048x, FR-159, FR-160, TC-056 | 1.63 s |
| ✅ | `test_a_changed_program_updates_the_open_draft_when_it_is_ticked` |  | BR-001, BR-026, FR-026, FR-048x, FR-159, FR-160, TC-056 | 0.77 s |
| ✅ | `test_a_restored_code_is_no_shell_and_the_database_refuses_a_delete_around_the_service` |  | BR-001, BR-026, FR-026, FR-048x, FR-159, FR-160, TC-056 | 1.03 s |
| ✅ | `test_a_withdrawn_code_is_listed_and_an_administrator_deletes_it_and_imports_again` |  | BR-001, BR-026, FR-026, FR-048x, FR-159, FR-160, TC-056 | 1.13 s |
| ✅ | `test_a_withdrawn_code_that_has_its_identifier_keeps_it_and_can_be_restored` |  | BR-001, BR-026, FR-026, FR-048x, FR-159, FR-160, TC-056 | 0.91 s |
| ✅ | `test_a_withdrawn_import_draft_gives_its_number_and_legacy_number_back` |  | BR-001, BR-026, FR-026, FR-048x, FR-159, FR-160, TC-056 | 1.12 s |
| ✅ | `test_bulk_withdraw_needs_a_list_and_a_role_that_can_withdraw` |  | BR-001, BR-026, FR-026, FR-048x, FR-159, FR-160, TC-056 | 0.77 s |
| ✅ | `test_several_change_requests_are_withdrawn_in_one_go_and_each_is_reported` |  | BR-001, BR-026, FR-026, FR-048x, FR-159, FR-160, TC-056 | 0.69 s |
| ✅ | `test_the_list_has_tick_boxes_and_a_withdraw_selected_button` |  | BR-001, BR-026, FR-026, FR-048x, FR-159, FR-160, TC-056 | 0.84 s |
| ✅ | `test_the_preview_screen_lists_the_choices_and_leaves_changed_programs_unticked` |  | BR-001, BR-026, FR-026, FR-048x, FR-159, FR-160, TC-056 | 0.79 s |

### `tests/integration/test_workflow_gaps.py` — 18 tests, 18 passed

_Closes the gaps found in the spec-vs-code review (docs/20-traceability-matrix.md):_

| Result | Test | Purpose | Requirements | Time |
|---|---|---|---|---|
| ✅ | `test_admin_can_override_identifier_with_reason_and_it_is_audited` |  | BR-012, FR-021a, FR-025a, FR-028, FR-034, FR-039, SEC-013 | 0.81 s |
| ✅ | `test_admin_signoff_can_override_proposed_audience_access` |  | BR-012, FR-021a, FR-025a, FR-028, FR-034, FR-039, SEC-013 | 1.11 s |
| ✅ | `test_assigned_reviewer_only_may_sign_off` |  | BR-012, FR-021a, FR-025a, FR-028, FR-034, FR-039, SEC-013 | 1.05 s |
| ✅ | `test_cr_page_explains_when_no_engineer_holds_a_pending_domain` |  | BR-012, FR-021a, FR-025a, FR-028, FR-034, FR-039, SEC-013 | 0.62 s |
| ✅ | `test_domain_request_is_refused_when_nobody_holds_the_domain` | A request nobody could ever act on must not be silently accepted. | BR-012, FR-021a, FR-025a, FR-028, FR-034, FR-039, SEC-013 | 0.48 s |
| ✅ | `test_domain_signoff_request_surfaces_for_target_and_clears_once_signed` |  | BR-012, FR-021a, FR-025a, FR-028, FR-034, FR-039, SEC-013 | 1.35 s |
| ✅ | `test_domain_signoff_request_validation` |  | BR-012, FR-021a, FR-025a, FR-028, FR-034, FR-039, SEC-013 | 0.75 s |
| ✅ | `test_identifier_override_forbidden_for_engineer` |  | BR-012, FR-021a, FR-025a, FR-028, FR-034, FR-039, SEC-013 | 0.81 s |
| ✅ | `test_identifier_override_rejects_out_of_range_malformed_and_duplicate` |  | BR-012, FR-021a, FR-025a, FR-028, FR-034, FR-039, SEC-013 | 1.22 s |
| ✅ | `test_identifier_override_requires_reason` |  | BR-012, FR-021a, FR-025a, FR-028, FR-034, FR-039, SEC-013 | 0.78 s |
| ✅ | `test_no_reassignment_after_reviewer_signed_off` |  | BR-012, FR-021a, FR-025a, FR-028, FR-034, FR-039, SEC-013 | 0.98 s |
| ✅ | `test_only_administrator_endpoint_accepts_overrides` |  | BR-012, FR-021a, FR-025a, FR-028, FR-034, FR-039, SEC-013 | 0.80 s |
| ✅ | `test_rejection_ignores_access_overrides` |  | BR-012, FR-021a, FR-025a, FR-028, FR-034, FR-039, SEC-013 | 1.45 s |
| ✅ | `test_reviewer_assignment_validation_and_authorization` |  | BR-012, FR-021a, FR-025a, FR-028, FR-034, FR-039, SEC-013 | 0.85 s |
| ✅ | `test_reviewer_can_be_reassigned_and_unassigned` |  | BR-012, FR-021a, FR-025a, FR-028, FR-034, FR-039, SEC-013 | 1.12 s |
| ✅ | `test_unknown_access_override_field_is_rejected` |  | BR-012, FR-021a, FR-025a, FR-028, FR-034, FR-039, SEC-013 | 0.87 s |
| ✅ | `test_untargeted_domain_request_is_visible_to_every_domain_holder` |  | BR-012, FR-021a, FR-025a, FR-028, FR-034, FR-039, SEC-013 | 0.74 s |
| ✅ | `test_withdrawn_cr_removes_its_domain_requests` |  | BR-012, FR-021a, FR-025a, FR-028, FR-034, FR-039, SEC-013 | 0.76 s |

### `tests/system/test_accessibility.py` — 9 tests, 9 passed

_I-22 accessibility (WCAG 2.1 AA, docs/10-ui-ux-specification.md §12): colour contrast of the_

| Result | Test | Purpose | Requirements | Time |
|---|---|---|---|---|
| ✅ | `test_every_page_is_structurally_accessible[de]` |  | FR-155, NFR-010, TC-049 | 1.81 s |
| ✅ | `test_every_page_is_structurally_accessible[en]` |  | FR-155, NFR-010, TC-049 | 2.26 s |
| ✅ | `test_every_state_badge_meets_aa` |  | FR-155, NFR-010, TC-049 | 0.00 s |
| ✅ | `test_status_is_never_conveyed_by_colour_alone` | Every state badge carries the state as text, not only a colour. | FR-155, NFR-010, TC-049 | 0.82 s |
| ✅ | `test_text_tokens_meet_aa_on_their_backgrounds` |  | FR-155, NFR-010, TC-049 | 0.00 s |
| ✅ | `test_the_chief_engineers_queue_is_accessible` |  | FR-155, NFR-010, TC-049 | 0.70 s |
| ✅ | `test_the_contrast_helper_matches_the_wcag_reference_values` |  | FR-155, NFR-010, TC-049 | 0.01 s |
| ✅ | `test_the_login_page_is_accessible` |  | FR-155, NFR-010, TC-049 | 0.32 s |
| ✅ | `test_the_stylesheet_honours_user_preferences` |  | FR-155, NFR-010, TC-049 | 0.00 s |

### `tests/system/test_cli_create_admin.py` — 2 tests, 2 passed

| Result | Test | Purpose | Requirements | Time |
|---|---|---|---|---|
| ✅ | `test_create_admin_cli_command` |  |  | 0.71 s |
| ✅ | `test_create_admin_cli_rejects_weak_password` |  |  | 0.27 s |

### `tests/system/test_deploy_artifacts.py` — 22 tests, 22 passed

_I-33 / I-34: the packaging, installer, scheduler units and CI definitions are consistent with_

| Result | Test | Purpose | Requirements | Time |
|---|---|---|---|---|
| ✅ | `test_backup_runs_every_night_and_reminders_on_weekdays` |  | NFR-013, NFR-014, TC-051 | 0.00 s |
| ✅ | `test_ci_files_parse_and_run_the_ci_script` |  | NFR-013, NFR-014, TC-051 | 0.02 s |
| ✅ | `test_create_admin_can_take_its_answers_from_the_environment` |  | NFR-013, NFR-014, TC-051 | 0.32 s |
| ✅ | `test_each_timer_has_a_matching_oneshot_service` |  | NFR-013, NFR-014, TC-051 | 0.01 s |
| ✅ | `test_every_expected_artifact_is_shipped` |  | NFR-013, NFR-014, TC-051 | 0.01 s |
| ✅ | `test_every_pattern_in_the_scan_is_classified` |  | NFR-013, NFR-014, TC-051 | 0.00 s |
| ✅ | `test_every_setting_an_installer_writes_is_read_by_the_application` |  | NFR-013, NFR-014, TC-051 | 0.02 s |
| ✅ | `test_every_setting_in_the_example_file_is_read_by_the_application` |  | NFR-013, NFR-014, TC-051 | 0.01 s |
| ✅ | `test_linux_installer_parses_and_its_dry_run_changes_nothing` |  | NFR-013, NFR-014, TC-051 | 1.25 s |
| ✅ | `test_non_sqlite_connections_are_left_alone` | The engine listeners must not touch another driver's connection (docs/07 section 12). | NFR-013, NFR-014, TC-051 | 0.26 s |
| ✅ | `test_production_refuses_to_start_with_a_weak_key` |  | NFR-013, NFR-014, TC-051 | 3.58 s |
| ✅ | `test_serve_options_follow_the_environment` |  | NFR-013, NFR-014, TC-051 | 0.02 s |
| ✅ | `test_services_call_only_commands_that_exist` |  | NFR-013, NFR-014, TC-051 | 0.30 s |
| ✅ | `test_the_ci_script_documents_itself` |  | NFR-013, NFR-014, TC-051 | 1.01 s |
| ✅ | `test_the_postgres_ratchet_holds` |  | NFR-013, NFR-014, TC-051 | 4.25 s |
| ✅ | `test_the_production_entry_point_serves_and_reports_its_state` |  | NFR-013, NFR-014, TC-051 | 8.65 s |
| ✅ | `test_the_ratchet_notices_new_sqlite_specific_code` |  | NFR-013, NFR-014, TC-051 | 3.74 s |
| ✅ | `test_units_parse_and_have_the_required_sections` |  | NFR-013, NFR-014, TC-051 | 0.03 s |
| ✅ | `test_web_service_runs_the_production_entry_point_as_an_unprivileged_user` |  | NFR-013, NFR-014, TC-051 | 0.00 s |
| ✅ | `test_windows_installer_dry_run_lists_every_step_and_creates_nothing` |  | NFR-013, NFR-014, TC-051 | 1.33 s |
| ✅ | `test_windows_scripts_parse` |  | NFR-013, NFR-014, TC-051 | 0.47 s |
| ✅ | `test_write_paths_of_the_units_cover_what_the_jobs_write` |  | NFR-013, NFR-014, TC-051 | 0.01 s |

### `tests/system/test_docs_consistency.py` — 17 tests, 17 passed

_TC-052. The documents agree with the code and with each other: the generated endpoint table, the_

| Result | Test | Purpose | Requirements | Time |
|---|---|---|---|---|
| ✅ | `test_every_requirement_id_cited_in_a_document_is_defined` |  | TC-052 | 0.37 s |
| ✅ | `test_every_requirement_is_accounted_for_and_the_matrix_evidence_resolves` |  | TC-052 | 0.86 s |
| ✅ | `test_every_screen_path_in_the_ui_inventory_is_a_real_route` | docs/10 section 1 names the path of each v4 screen; each must exist as a UI route. | TC-052 | 0.26 s |
| ✅ | `test_every_test_case_id_cited_in_the_documents_exists` |  | TC-052 | 0.07 s |
| ✅ | `test_links_between_documents_point_at_existing_files_and_headings` |  | TC-052 | 0.12 s |
| ✅ | `test_paragraphs_in_documents_are_single_source_lines` | docs/15 §6: prose paragraphs are one continuous source line (tables, lists and code may span). | TC-052 | 0.05 s |
| ✅ | `test_section_references_between_documents_exist` |  | TC-052 | 0.16 s |
| ✅ | `test_the_audit_catalogue_lists_every_code_the_application_can_write` |  | TC-052 | 0.39 s |
| ✅ | `test_the_contract_version_and_operation_count_quoted_in_the_documents` |  | TC-052 | 0.43 s |
| ✅ | `test_the_decisions_and_assumptions_are_complete` |  | TC-052 | 0.03 s |
| ✅ | `test_the_document_set_version_is_current_and_the_report_is_generated` |  | TC-052 | 0.01 s |
| ✅ | `test_the_endpoint_table_of_the_api_document_is_the_generated_one` |  | TC-052 | 0.54 s |
| ✅ | `test_the_group_and_subgroup_counts_quoted_in_the_documents` |  | TC-052 | 0.00 s |
| ✅ | `test_the_screen_count_matches_the_inventory` |  | TC-052 | 0.03 s |
| ✅ | `test_the_table_and_trigger_counts_quoted_in_the_documents` |  | TC-052 | 0.03 s |
| ✅ | `test_the_test_suite_table_of_the_strategy_matches_the_test_files` | docs/13 section 8a quotes how many test functions each v4 module has. | TC-052 | 0.07 s |
| ✅ | `test_the_v4_tables_of_the_data_dictionary_name_real_columns` | docs/06 section 13 lists each v4 table with its fields; every named field must exist. | TC-052 | 0.01 s |

### `tests/system/test_health.py` — 1 tests, 1 passed

_US-001 acceptance criterion: app boots, health endpoint returns 200._

| Result | Test | Purpose | Requirements | Time |
|---|---|---|---|---|
| ✅ | `test_health_returns_ok` |  | US-001 | 0.26 s |

### `tests/system/test_i18n.py` — 30 tests, 30 passed

_I-22: the German interface. The catalogue must cover every string a template wraps in `_()`,_

| Result | Test | Purpose | Requirements | Time |
|---|---|---|---|---|
| ✅ | `test_every_language_translates_the_whole_interface_inventory` |  | FR-155, FR-167, TC-049 | 0.06 s |
| ✅ | `test_every_template_string_has_a_german_entry` |  | FR-155, FR-167, TC-049 | 0.16 s |
| ✅ | `test_main_pages_render_in_each_language_without_leaking_format_markers[ar]` |  | FR-155, FR-167, TC-049 | 0.89 s |
| ✅ | `test_main_pages_render_in_each_language_without_leaking_format_markers[bn]` |  | FR-155, FR-167, TC-049 | 1.18 s |
| ✅ | `test_main_pages_render_in_each_language_without_leaking_format_markers[da]` |  | FR-155, FR-167, TC-049 | 0.83 s |
| ✅ | `test_main_pages_render_in_each_language_without_leaking_format_markers[de]` |  | FR-155, FR-167, TC-049 | 0.85 s |
| ✅ | `test_main_pages_render_in_each_language_without_leaking_format_markers[en]` |  | FR-155, FR-167, TC-049 | 0.83 s |
| ✅ | `test_main_pages_render_in_each_language_without_leaking_format_markers[es]` |  | FR-155, FR-167, TC-049 | 0.87 s |
| ✅ | `test_main_pages_render_in_each_language_without_leaking_format_markers[fr]` |  | FR-155, FR-167, TC-049 | 0.84 s |
| ✅ | `test_main_pages_render_in_each_language_without_leaking_format_markers[gu]` |  | FR-155, FR-167, TC-049 | 1.21 s |
| ✅ | `test_main_pages_render_in_each_language_without_leaking_format_markers[hi]` |  | FR-155, FR-167, TC-049 | 0.87 s |
| ✅ | `test_main_pages_render_in_each_language_without_leaking_format_markers[it]` |  | FR-155, FR-167, TC-049 | 0.84 s |
| ✅ | `test_main_pages_render_in_each_language_without_leaking_format_markers[ka]` |  | FR-155, FR-167, TC-049 | 0.84 s |
| ✅ | `test_main_pages_render_in_each_language_without_leaking_format_markers[kn]` |  | FR-155, FR-167, TC-049 | 0.85 s |
| ✅ | `test_main_pages_render_in_each_language_without_leaking_format_markers[ml]` |  | FR-155, FR-167, TC-049 | 0.86 s |
| ✅ | `test_main_pages_render_in_each_language_without_leaking_format_markers[mr]` |  | FR-155, FR-167, TC-049 | 0.84 s |
| ✅ | `test_main_pages_render_in_each_language_without_leaking_format_markers[or]` |  | FR-155, FR-167, TC-049 | 1.25 s |
| ✅ | `test_main_pages_render_in_each_language_without_leaking_format_markers[pa]` |  | FR-155, FR-167, TC-049 | 0.84 s |
| ✅ | `test_main_pages_render_in_each_language_without_leaking_format_markers[ta]` |  | FR-155, FR-167, TC-049 | 0.84 s |
| ✅ | `test_main_pages_render_in_each_language_without_leaking_format_markers[te]` |  | FR-155, FR-167, TC-049 | 0.81 s |
| ✅ | `test_main_pages_render_in_each_language_without_leaking_format_markers[ur]` |  | FR-155, FR-167, TC-049 | 0.87 s |
| ✅ | `test_placeholders_survive_translation` |  | FR-155, FR-167, TC-049 | 0.00 s |
| ✅ | `test_the_browser_language_picks_the_login_page_language` |  | FR-155, FR-167, TC-049 | 0.32 s |
| ✅ | `test_the_catalogue_has_no_empty_or_identical_entries` |  | FR-155, FR-167, TC-049 | 0.00 s |
| ✅ | `test_the_choice_before_login_applies_to_the_login_page` |  | FR-155, FR-167, TC-049 | 0.32 s |
| ✅ | `test_the_german_login_page_keeps_english_credentials_hint_free_of_secrets` |  | FR-155, FR-167, TC-049 | 0.32 s |
| ✅ | `test_the_language_choice_is_remembered_for_the_user` |  | FR-155, FR-167, TC-049 | 0.51 s |
| ✅ | `test_the_user_preference_is_exposed_on_the_account_page` |  | FR-155, FR-167, TC-049 | 0.43 s |
| ✅ | `test_there_are_no_stale_german_entries_for_removed_template_strings` |  | FR-155, FR-167, TC-049 | 0.19 s |
| ✅ | `test_translate_falls_back_to_the_english_text` |  | FR-155, FR-167, TC-049 | 0.26 s |

### `tests/system/test_injection_and_session.py` — 8 tests, 8 passed

_TC-017, TC-026, TC-027, SEC-002, SEC-003, SEC-020-SEC-022: injection_

| Result | Test | Purpose | Requirements | Time |
|---|---|---|---|---|
| ✅ | `test_audit_log_filters_resist_injection` |  | SEC-002, SEC-003, SEC-020, SEC-022, TC-017, TC-026, TC-027 | 0.36 s |
| ✅ | `test_idle_session_expires_after_thirty_minutes` | TC-017 / FR-002 / SEC-003. | FR-002, SEC-003, TC-017 | 0.36 s |
| ✅ | `test_recent_activity_keeps_the_session_alive` |  | SEC-002, SEC-003, SEC-020, SEC-022, TC-017, TC-026, TC-027 | 0.35 s |
| ✅ | `test_server_side_validation_ignores_client_side_constraints` | SEC-020: every rule is enforced server-side, whatever the browser did. | SEC-020 | 0.60 s |
| ✅ | `test_session_cookie_attributes` | SEC-002 (the Secure flag is off only in the dev/test configs). | SEC-002 | 0.36 s |
| ✅ | `test_session_expires_at_the_absolute_lifetime` | SEC-003: 12 hours regardless of activity. | SEC-003 | 0.35 s |
| ✅ | `test_sql_injection_probes_have_no_effect` | TC-027 / SEC-021. | SEC-021, TC-027 | 0.89 s |
| ✅ | `test_user_supplied_text_is_escaped_everywhere_it_renders` | TC-026 / SEC-022. | SEC-022, TC-026 | 1.71 s |

### `tests/system/test_logging_and_passwords.py` — 8 tests, 8 passed

_Security policy details from 11-security-architecture.md: §4 password policy_

| Result | Test | Purpose | Requirements | Time |
|---|---|---|---|---|
| ✅ | `test_administrator_reset_also_honours_history` |  |  | 1.04 s |
| ✅ | `test_authenticated_requests_record_the_user_id` |  |  | 0.35 s |
| ✅ | `test_blocklist_ignores_comments_and_short_entries` |  |  | 0.00 s |
| ✅ | `test_last_five_passwords_cannot_be_reused` |  |  | 2.53 s |
| ✅ | `test_only_hashes_are_stored_in_the_history` |  |  | 0.41 s |
| ✅ | `test_policy_length_and_blocklist` |  |  | 0.00 s |
| ✅ | `test_requests_are_logged_as_json_without_credentials` |  |  | 0.35 s |
| ✅ | `test_unhandled_errors_are_logged_with_the_request_id` |  |  | 0.38 s |

### `tests/system/test_multiprocess.py` — 4 tests, 4 passed

_Two real server processes on one database file (docs/14-deployment-architecture.md §3):_

| Result | Test | Purpose | Requirements | Time |
|---|---|---|---|---|
| ✅ | `test_concurrent_writers_in_two_processes_all_succeed` |  | NFR-009, TC-050 | 13.36 s |
| ✅ | `test_the_ip_limit_is_shared_and_other_users_are_unaffected_until_it_is_reached` |  | NFR-009, TC-050 | 12.51 s |
| ✅ | `test_the_limit_survives_a_restart` |  | NFR-009, TC-050 | 12.65 s |
| ✅ | `test_the_username_limit_is_shared_by_both_processes` |  | NFR-009, TC-050 | 13.66 s |

### `tests/system/test_no_cloud.py` — 3 tests, 3 passed

_US-120 / TC-029: block cloud-SDK imports, cloud identity providers and_

| Result | Test | Purpose | Requirements | Time |
|---|---|---|---|---|
| ✅ | `test_no_cloud_sdk_imports_in_source` |  | TC-029, US-120 | 0.41 s |
| ✅ | `test_no_cloud_sdk_in_requirements` |  | TC-029, US-120 | 0.01 s |
| ✅ | `test_templates_and_static_reference_no_external_assets` |  | TC-029, US-120 | 0.17 s |

### `tests/system/test_openapi_conformance.py` — 5 tests, 5 passed

_EPIC-11 / FR-080: the code and docs/artifacts/openapi.yaml describe the_

| Result | Test | Purpose | Requirements | Time |
|---|---|---|---|---|
| ✅ | `test_every_documented_operation_is_implemented_and_vice_versa` |  | FR-080 | 0.28 s |
| ✅ | `test_live_payloads_only_use_declared_properties` |  | FR-080 | 0.81 s |
| ✅ | `test_lookup_and_domain_request_payloads_match_contract` |  | FR-080 | 0.70 s |
| ✅ | `test_revision_diff_payload_matches_contract` |  | FR-080 | 1.24 s |
| ✅ | `test_unauthenticated_requests_are_rejected_for_every_documented_operation` |  | FR-080 | 0.32 s |

### `tests/system/test_permission_grid.py` — 14 tests, 14 passed

_TC-018 / TC-018a / TC-018b / TC-019 / FR-081 / SEC-010: the full_

| Result | Test | Purpose | Requirements | Time |
|---|---|---|---|---|
| ✅ | `test_api_endpoints_require_authentication` |  | FR-081, SEC-010, TC-018, TC-018a, TC-018b, TC-019 | 1.09 s |
| ✅ | `test_api_permission_grid[ADMINISTRATOR]` |  | FR-081, SEC-010, TC-018, TC-018a, TC-018b, TC-019 | 1.05 s |
| ✅ | `test_api_permission_grid[CHIEF_ENGINEER]` |  | FR-081, SEC-010, TC-018, TC-018a, TC-018b, TC-019 | 0.97 s |
| ✅ | `test_api_permission_grid[ENGINEER]` |  | FR-081, SEC-010, TC-018, TC-018a, TC-018b, TC-019 | 0.93 s |
| ✅ | `test_api_permission_grid[REVIEWER]` |  | FR-081, SEC-010, TC-018, TC-018a, TC-018b, TC-019 | 1.37 s |
| ✅ | `test_api_permission_grid[STCD_OWNER]` |  | FR-081, SEC-010, TC-018, TC-018a, TC-018b, TC-019 | 0.87 s |
| ✅ | `test_api_permission_grid[VIEWER]` |  | FR-081, SEC-010, TC-018, TC-018a, TC-018b, TC-019 | 0.88 s |
| ✅ | `test_ui_permission_grid[ADMINISTRATOR]` |  | FR-081, SEC-010, TC-018, TC-018a, TC-018b, TC-019 | 1.55 s |
| ✅ | `test_ui_permission_grid[CHIEF_ENGINEER]` |  | FR-081, SEC-010, TC-018, TC-018a, TC-018b, TC-019 | 1.07 s |
| ✅ | `test_ui_permission_grid[ENGINEER]` |  | FR-081, SEC-010, TC-018, TC-018a, TC-018b, TC-019 | 1.07 s |
| ✅ | `test_ui_permission_grid[REVIEWER]` |  | FR-081, SEC-010, TC-018, TC-018a, TC-018b, TC-019 | 1.05 s |
| ✅ | `test_ui_permission_grid[STCD_OWNER]` |  | FR-081, SEC-010, TC-018, TC-018a, TC-018b, TC-019 | 1.34 s |
| ✅ | `test_ui_permission_grid[VIEWER]` |  | FR-081, SEC-010, TC-018, TC-018a, TC-018b, TC-019 | 0.74 s |
| ✅ | `test_ui_redirects_anonymous_users_to_login` |  | FR-081, SEC-010, TC-018, TC-018a, TC-018b, TC-019 | 0.67 s |

### `tests/system/test_production_config.py` — 7 tests, 7 passed

_SEC-002 / deployment hardening: a production instance must not start with a_

| Result | Test | Purpose | Requirements | Time |
|---|---|---|---|---|
| ✅ | `test_development_and_testing_still_start_with_the_default_key` |  | SEC-002 | 0.16 s |
| ✅ | `test_production_refuses_a_weak_secret_key[]` |  | SEC-002 | 0.00 s |
| ✅ | `test_production_refuses_a_weak_secret_key[change-me-in-every-real-environment]` |  | SEC-002 | 0.00 s |
| ✅ | `test_production_refuses_a_weak_secret_key[dev-secret-key-change-me]` |  | SEC-002 | 0.00 s |
| ✅ | `test_production_refuses_a_weak_secret_key[too-short]` |  | SEC-002 | 0.00 s |
| ✅ | `test_production_refuses_a_weak_secret_key[xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx]` |  | SEC-002 | 0.00 s |
| ✅ | `test_production_starts_with_a_strong_secret_key` |  | SEC-002 | 0.09 s |

### `tests/system/test_route_inventory.py` — 13 tests, 13 passed

_Every route is access-controlled, and the declared role lists are what is enforced._

| Result | Test | Purpose | Requirements | Time |
|---|---|---|---|---|
| ✅ | `test_a_tokenised_endpoint_is_always_a_get` | API tokens may only ever read (docs/11 §12): `allow_token` must never sit on a write. | FR-081, SEC-010, TC-018, TC-048 | 0.27 s |
| ✅ | `test_every_gated_route_refuses_anonymous_callers` |  | FR-081, SEC-010, TC-018, TC-048 | 0.40 s |
| ✅ | `test_every_route_declares_its_access_control` |  | FR-081, SEC-010, TC-018, TC-048 | 0.26 s |
| ✅ | `test_login_only_routes_are_reachable_by_every_role` |  | FR-081, SEC-010, TC-018, TC-048 | 3.98 s |
| ✅ | `test_login_page_credentials_still_work_for_the_ui_walk` |  | FR-081, SEC-010, TC-018, TC-048 | 0.36 s |
| ✅ | `test_role_lists_are_never_empty_and_only_name_real_roles` |  | FR-081, SEC-010, TC-018, TC-048 | 0.28 s |
| ✅ | `test_the_declared_role_list_is_what_each_role_gets[ADMINISTRATOR]` |  | FR-081, SEC-010, TC-018, TC-048 | 2.14 s |
| ✅ | `test_the_declared_role_list_is_what_each_role_gets[CHIEF_ENGINEER]` |  | FR-081, SEC-010, TC-018, TC-048 | 1.39 s |
| ✅ | `test_the_declared_role_list_is_what_each_role_gets[ENGINEER]` |  | FR-081, SEC-010, TC-018, TC-048 | 1.91 s |
| ✅ | `test_the_declared_role_list_is_what_each_role_gets[REVIEWER]` |  | FR-081, SEC-010, TC-018, TC-048 | 1.38 s |
| ✅ | `test_the_declared_role_list_is_what_each_role_gets[STCD_OWNER]` |  | FR-081, SEC-010, TC-018, TC-048 | 1.23 s |
| ✅ | `test_the_declared_role_list_is_what_each_role_gets[VIEWER]` |  | FR-081, SEC-010, TC-018, TC-048 | 1.07 s |
| ✅ | `test_the_public_list_is_exactly_the_routes_that_need_no_session` |  | FR-081, SEC-010, TC-018, TC-048 | 0.28 s |

### `tests/system/test_security_headers.py` — 4 tests, 4 passed

_SEC-025: standard security headers on every response._

| Result | Test | Purpose | Requirements | Time |
|---|---|---|---|---|
| ✅ | `test_api_response_has_security_headers` |  | SEC-025 | 0.26 s |
| ✅ | `test_hsts_sent_over_https` |  | SEC-025 | 0.26 s |
| ✅ | `test_templates_have_no_inline_script_or_handlers` | The CSP forbids inline script; guard against regressions. | SEC-025 | 0.04 s |
| ✅ | `test_ui_page_has_csp_and_no_hsts_over_plain_http` |  | SEC-025 | 0.31 s |

### `tests/system/test_translations_doc.py` — 27 tests, 27 passed

_The translation catalogue document and the review sheets for native speakers_

| Result | Test | Purpose | Requirements | Time |
|---|---|---|---|---|
| ✅ | `test_every_language_has_its_section_and_its_coverage_row` |  | FR-110, FR-111, FR-155, FR-157, FR-161, TC-057 | 0.10 s |
| ✅ | `test_right_to_left_languages_get_a_right_to_left_translation_column[ar-right]` |  | FR-110, FR-111, FR-155, FR-157, FR-161, TC-057 | 0.42 s |
| ✅ | `test_right_to_left_languages_get_a_right_to_left_translation_column[fr-left]` |  | FR-110, FR-111, FR-155, FR-157, FR-161, TC-057 | 0.43 s |
| ✅ | `test_right_to_left_languages_get_a_right_to_left_translation_column[ur-right]` |  | FR-110, FR-111, FR-155, FR-157, FR-161, TC-057 | 0.75 s |
| ✅ | `test_string_ids_are_stable_and_never_collide` |  | FR-110, FR-111, FR-155, FR-157, FR-161, TC-057 | 0.05 s |
| ✅ | `test_the_command_line_writes_one_sheet_per_language_and_refuses_unknown_ones` |  | FR-110, FR-111, FR-155, FR-157, FR-161, TC-057 | 6.71 s |
| ✅ | `test_the_concept_names_the_layers_the_checks_and_the_open_items` |  | FR-110, FR-111, FR-155, FR-157, FR-161, TC-057 | 0.01 s |
| ✅ | `test_the_document_is_exactly_what_the_generator_produces_from_the_code` |  | FR-110, FR-111, FR-155, FR-157, FR-161, TC-057 | 0.23 s |
| ✅ | `test_the_fingerprint_changes_when_one_translation_changes` |  | FR-110, FR-111, FR-155, FR-157, FR-161, TC-057 | 0.01 s |
| ✅ | `test_the_review_sheet_of_every_language_is_complete[ar]` |  | FR-110, FR-111, FR-155, FR-157, FR-161, TC-057 | 0.47 s |
| ✅ | `test_the_review_sheet_of_every_language_is_complete[bn]` |  | FR-110, FR-111, FR-155, FR-157, FR-161, TC-057 | 0.47 s |
| ✅ | `test_the_review_sheet_of_every_language_is_complete[da]` |  | FR-110, FR-111, FR-155, FR-157, FR-161, TC-057 | 0.48 s |
| ✅ | `test_the_review_sheet_of_every_language_is_complete[de]` |  | FR-110, FR-111, FR-155, FR-157, FR-161, TC-057 | 0.47 s |
| ✅ | `test_the_review_sheet_of_every_language_is_complete[es]` |  | FR-110, FR-111, FR-155, FR-157, FR-161, TC-057 | 0.78 s |
| ✅ | `test_the_review_sheet_of_every_language_is_complete[fr]` |  | FR-110, FR-111, FR-155, FR-157, FR-161, TC-057 | 0.88 s |
| ✅ | `test_the_review_sheet_of_every_language_is_complete[gu]` |  | FR-110, FR-111, FR-155, FR-157, FR-161, TC-057 | 0.47 s |
| ✅ | `test_the_review_sheet_of_every_language_is_complete[hi]` |  | FR-110, FR-111, FR-155, FR-157, FR-161, TC-057 | 0.48 s |
| ✅ | `test_the_review_sheet_of_every_language_is_complete[it]` |  | FR-110, FR-111, FR-155, FR-157, FR-161, TC-057 | 0.48 s |
| ✅ | `test_the_review_sheet_of_every_language_is_complete[ka]` |  | FR-110, FR-111, FR-155, FR-157, FR-161, TC-057 | 0.49 s |
| ✅ | `test_the_review_sheet_of_every_language_is_complete[kn]` |  | FR-110, FR-111, FR-155, FR-157, FR-161, TC-057 | 0.82 s |
| ✅ | `test_the_review_sheet_of_every_language_is_complete[ml]` |  | FR-110, FR-111, FR-155, FR-157, FR-161, TC-057 | 0.47 s |
| ✅ | `test_the_review_sheet_of_every_language_is_complete[mr]` |  | FR-110, FR-111, FR-155, FR-157, FR-161, TC-057 | 0.80 s |
| ✅ | `test_the_review_sheet_of_every_language_is_complete[or]` |  | FR-110, FR-111, FR-155, FR-157, FR-161, TC-057 | 0.47 s |
| ✅ | `test_the_review_sheet_of_every_language_is_complete[pa]` |  | FR-110, FR-111, FR-155, FR-157, FR-161, TC-057 | 0.47 s |
| ✅ | `test_the_review_sheet_of_every_language_is_complete[ta]` |  | FR-110, FR-111, FR-155, FR-157, FR-161, TC-057 | 0.47 s |
| ✅ | `test_the_review_sheet_of_every_language_is_complete[te]` |  | FR-110, FR-111, FR-155, FR-157, FR-161, TC-057 | 0.49 s |
| ✅ | `test_the_review_sheet_of_every_language_is_complete[ur]` |  | FR-110, FR-111, FR-155, FR-157, FR-161, TC-057 | 0.48 s |

### `tests/system/test_uat.py` — 14 tests, 14 passed

_TC-030: UAT-01 .. UAT-13 (docs/13-test-strategy.md §7) as scripted_

| Result | Test | Purpose | Requirements | Time |
|---|---|---|---|---|
| ✅ | `test_uat_01_new_code_has_no_identifier_until_submitted` |  | UAT-01 | 1.02 s |
| ✅ | `test_uat_02_either_signoff_order_reaches_pending_approval_automatically` |  | UAT-02 | 0.92 s |
| ✅ | `test_uat_03_chief_engineer_approval_visible_to_the_engineer` |  | UAT-03 | 1.21 s |
| ✅ | `test_uat_04_rejection_comment_visible_and_prior_signoff_cleared` |  | UAT-04 | 1.19 s |
| ✅ | `test_uat_05_cross_domain_signoff_unblocks_submit` |  | UAT-05 | 1.19 s |
| ✅ | `test_uat_06_release_build_excludes_unselected_and_sandbox` |  | UAT-06 | 1.68 s |
| ✅ | `test_uat_07_viewer_searches_and_exports_released_catalogue_for_one_group` |  | UAT-07 | 1.24 s |
| ✅ | `test_uat_08_sandbox_lifecycle_and_traceable_deletion` |  | UAT-08 | 0.65 s |
| ✅ | `test_uat_09_nobody_can_decide_their_own_submission` |  | UAT-09 | 0.97 s |
| ✅ | `test_uat_09b_chief_engineer_cannot_be_a_prior_signer_or_author` |  | TC-030, UAT-01, UAT-13 | 1.55 s |
| ✅ | `test_uat_10_full_database_export_is_administrator_only` |  | UAT-10 | 0.86 s |
| ✅ | `test_uat_11_import_creates_only_governed_drafts_and_an_error_report` |  | UAT-11 | 0.70 s |
| ✅ | `test_uat_12_subgroup_is_mandatory_and_overlaps_are_refused` |  | UAT-12 | 0.68 s |
| ✅ | `test_uat_13_failed_form_keeps_input_and_dropdowns_explain_themselves` |  | UAT-13 | 0.79 s |

### `tests/system/test_windows_gateway.py` — 7 tests, 7 passed

_The Windows sign-in against a real Windows identity (docs/03-srs.md FR-163, docs/11 SEC-033)._

| Result | Test | Purpose | Requirements | Time |
|---|---|---|---|---|
| ✅ | `test_a_header_the_client_sends_is_dropped_by_the_gateway` |  | FR-163, SEC-033, TC-062 | 0.86 s |
| ✅ | `test_a_request_without_credentials_gets_a_challenge_and_never_reaches_the_application` |  | FR-163, SEC-033, TC-062 | 0.82 s |
| ✅ | `test_an_unknown_windows_user_and_a_deactivated_account_are_refused` |  | FR-163, SEC-033, TC-062 | 0.93 s |
| ✅ | `test_sspi_names_the_windows_user_who_runs_the_process[NTLM]` |  | FR-163, SEC-033, TC-062 | 0.00 s |
| ✅ | `test_sspi_names_the_windows_user_who_runs_the_process[Negotiate]` |  | FR-163, SEC-033, TC-062 | 0.00 s |
| ✅ | `test_the_header_is_ignored_when_it_does_not_come_from_the_trusted_gateway` |  | FR-163, SEC-033, TC-062 | 1.34 s |
| ✅ | `test_the_whole_chain_signs_the_windows_user_in` |  | FR-163, SEC-033, TC-062 | 0.85 s |

### `tests/performance/test_performance.py` — 9 tests, 9 passed

_NFR-001, TC-024, TC-025, NFR-004: performance targets on a temp-file SQLite_

| Result | Test | Purpose | Requirements | Time |
|---|---|---|---|---|
| ✅ | `test_concurrent_identifier_allocation_in_one_group` | TC-025: parallel submissions in one popular group yield unique, gap-free | TC-025 | 0.76 s |
| ✅ | `test_export_issues_a_constant_number_of_queries` | Regression guard for the N+1 problem: exporting 500 revisions must not cost | NFR-001, NFR-004, TC-024, TC-025 | 0.73 s |
| ✅ | `test_export_of_5000_records_within_target[csv-5]` | NFR-001: CSV/JSON <= 5 s, PDF <= 15 s for 5,000 records (XLSX held to the PDF limit). | NFR-001 | 1.49 s |
| ✅ | `test_export_of_5000_records_within_target[json-5]` | NFR-001: CSV/JSON <= 5 s, PDF <= 15 s for 5,000 records (XLSX held to the PDF limit). | NFR-001 | 1.70 s |
| ✅ | `test_export_of_5000_records_within_target[pdf-15]` | NFR-001: CSV/JSON <= 5 s, PDF <= 15 s for 5,000 records (XLSX held to the PDF limit). | NFR-001 | 6.45 s |
| ✅ | `test_export_of_5000_records_within_target[xlsx-15]` | NFR-001: CSV/JSON <= 5 s, PDF <= 15 s for 5,000 records (XLSX held to the PDF limit). | NFR-001 | 2.82 s |
| ✅ | `test_fifty_concurrent_users_are_served_without_errors` | NFR-004: 50 concurrent named users (each searching every ~8 s — | NFR-004 | 28.20 s |
| ✅ | `test_reads_are_not_blocked_by_an_open_write_transaction` | WAL read concurrency: a reader proceeds while another connection holds | NFR-001, NFR-004, TC-024, TC-025 | 0.67 s |
| ✅ | `test_search_and_read_latency_at_20000_revisions` | TC-024. | TC-024 | 6.37 s |

## 9. Run history

| # | Date (UTC) | Commit | Order | Tests | Passed | Failed | Retried | Coverage | Gates | Duration |
|---|---|---|---|---|---|---|---|---|---|---|
| 1 | 2026-10-21 16:36 | `f23ef18*` | reverse | 318 | 318 | 0 | 1 | 88% | 5/5 pass | 232 s |
| 2 | 2026-10-21 16:42 | `f23ef18*` | shuffle:11 | 318 | 318 | 0 | 0 | 88% | 5/5 pass | 235 s |
| 3 | 2026-10-21 16:49 | `f23ef18*` | file | 318 | 318 | 0 | 1 | 88% | 5/5 pass | 237 s |
| 4 | 2026-10-21 16:57 | `f23ef18*` | file | 318 | 318 | 0 | 0 | 88% | 5/5 pass | 244 s |
| 5 | 2026-10-21 17:09 | `f23ef18*` | shuffle:23 | 319 | 319 | 0 | 0 | 88% | 5/5 pass | 242 s |
| 6 | 2026-10-21 17:15 | `f23ef18*` | file | 319 | 319 | 0 | 0 | 88% | 5/5 pass | 237 s |
| 7 | 2026-10-22 10:02 | `f23ef18*` | file | 329 | 329 | 0 | 0 | 89% | 5/5 pass | 150 s |
| 8 | 2026-10-23 06:16 | `c0aff94*` | file | 601 | 600 | 1 | 0 | 92% | 5/5 pass | 589 s |
| 9 | 2026-10-23 06:27 | `c0aff94*` | reverse | 601 | 600 | 1 | 0 | 92% | 5/5 pass | 526 s |
| 10 | 2026-10-23 06:38 | `c0aff94*` | shuffle:7 | 601 | 600 | 1 | 0 | 92% | 5/5 pass | 473 s |
| 11 | 2026-10-23 06:50 | `c0aff94*` | file | 602 | 602 | 0 | 0 | 92% | 5/5 pass | 472 s |
| 12 | 2026-10-23 06:59 | `c0aff94*` | reverse | 602 | 602 | 0 | 0 | 92% | 5/5 pass | 470 s |
| 13 | 2026-10-23 07:08 | `c0aff94*` | shuffle:7 | 602 | 602 | 0 | 0 | 92% | 5/5 pass | 469 s |
| 14 | 2026-10-23 07:18 | `c0aff94*` | file+filedb | 602 | 601 | 1 | 0 | 92% | 5/5 pass | 542 s |
| 15 | 2026-10-23 07:31 | `c0aff94*` | file+filedb | 602 | 602 | 0 | 0 | 92% | 5/5 pass | 590 s |
| 16 | 2026-10-23 07:41 | `c0aff94*` | file | 602 | 602 | 0 | 0 | 92% | 5/5 pass | 505 s |
| 17 | 2026-10-23 07:54 | `c0aff94*` | reverse | 607 | 607 | 0 | 0 | 92% | 5/5 pass | 459 s |
| 18 | 2026-10-23 08:04 | `c0aff94*` | shuffle:7 | 607 | 607 | 0 | 0 | 92% | 5/5 pass | 491 s |
| 19 | 2026-10-23 08:16 | `c0aff94*` | file+filedb | 607 | 607 | 0 | 0 | 92% | 5/5 pass | 628 s |
| 20 | 2026-10-23 08:25 | `c0aff94*` | file | 607 | 607 | 0 | 0 | 92% | 5/5 pass | 508 s |
| 21 | 2026-10-23 15:33 | `c0aff94*` | file | 807 | 807 | 0 | 0 | 92% | 5/5 pass | 685 s |
| 22 | 2026-10-23 19:53 | `3670346*` | file | 830 | 828 | 2 | 0 | 93% | 2/5 pass | 850 s |
| 23 | 2026-10-23 20:10 | `3670346*` | file | 830 | 830 | 0 | 0 | 93% | 5/5 pass | 728 s |
| 24 | 2026-10-23 23:30 | `9f038bc*` | file | 848 | 847 | 1 | 0 | 93% | 5/5 pass | 741 s |
| 25 | 2026-10-23 23:47 | `9f038bc*` | file | 848 | 848 | 0 | 0 | 93% | 5/5 pass | 748 s |


# 24. Test Report — CSCM Tool

> **Generated file — do not edit by hand.** Regenerate with `python cscm_tool/scripts/generate_test_report.py` after every software change (Definition of Done, 15-development-standards.md). It runs the complete pytest suite, measures coverage, runs the static quality gates, and appends the run to the history below.

## 1. Run summary

| | |
|---|---|
| **Verdict** | **PASS** |
| Generated (UTC) | 2026-10-22 10:02:21 |
| Branch / commit | `feature/v3-rework` @ `f23ef18` +uncommitted changes |
| Test order | `file` |
| Tests | **329** run — 329 passed, 0 failed, 0 skipped |
| Duration | 149.9 s |
| Line coverage (`app/`) | **89%** (3253 of 3672 statements) |
| Python / platform | 3.12.10 / Windows 11 |
| pytest summary line | `functional: 320 passed, 9 deselected, 1 warning in 118.84s (0:01:58)  |  performance: 9 passed, 1 warning in 39.66s` |

## 2. Results by suite

| Suite | Tests | Passed | Failed | Skipped | Time |
|---|---|---|---|---|---|
| unit | 72 | 72 | 0 | 0 | 0.6 s |
| integration | 184 | 184 | 0 | 0 | 82.1 s |
| system | 64 | 64 | 0 | 0 | 27.8 s |
| performance | 9 | 9 | 0 | 0 | 39.4 s |

## 3. Static quality and security gates

| Gate | Result | Detail |
|---|---|---|
| black --check | PASS | 125 files would be left unchanged. |
| ruff check | PASS | All checks passed! |
| mypy | PASS | Success: no issues found in 81 source files |
| bandit -r app | PASS |  |
| pip-audit | PASS | runtime packages with advisories: none; dev-only advisories (accepted): black, pytest, starlette |

## 4. Measured performance (NFR-001, NFR-004, TC-024, TC-025)

| Test | Measured |
|---|---|
| `test_search_and_read_latency_at_20000_revisions` | read_p95_ms = 2.4, revisions = 20000, search_median_ms = 44.6, search_p95_ms = 51.5, speed_factor = 1.0 |
| `test_export_of_5000_records_within_target[csv-5]` | export_seconds = 0.51, limit_seconds = 5, records = 5000, speed_factor = 1.0 |
| `test_export_of_5000_records_within_target[json-5]` | export_seconds = 0.49, limit_seconds = 5, records = 5000, speed_factor = 1.0 |
| `test_export_of_5000_records_within_target[xlsx-15]` | export_seconds = 1.42, limit_seconds = 15, records = 5000, speed_factor = 1.0 |
| `test_export_of_5000_records_within_target[pdf-15]` | export_seconds = 2.32, limit_seconds = 15, records = 5000, speed_factor = 1.0 |
| `test_concurrent_identifier_allocation_in_one_group` | allocation_p95_ms = 181.8, speed_factor = 1.0, submissions = 64 |
| `test_fifty_concurrent_users_are_served_without_errors` | p95_ms_50_users = 58.2, speed_factor = 1.0 |
| `test_export_issues_a_constant_number_of_queries` | statements_for_two_500_row_exports = 17 |

Targets: search p95 ≤ 500 ms and single read p95 ≤ 200 ms at 20,000 revisions; CSV/JSON export of 5,000 records ≤ 5 s, XLSX/PDF ≤ 15 s; 50 concurrent users keep the 500 ms search target; identifier allocation under contention correct and gap-free.

## 5. Coverage by module

| Module | Statements | Missed | Coverage |
|---|---|---|---|
| `app/__init__.py` | 50 | 0 | 100% |
| `app/api/__init__.py` | 0 | 0 | 100% |
| `app/api/v1/__init__.py` | 3 | 0 | 100% |
| `app/api/v1/audit_routes.py` | 12 | 0 | 100% |
| `app/api/v1/auth_routes.py` | 40 | 2 | 95% |
| `app/api/v1/change_request_routes.py` | 118 | 12 | 90% |
| `app/api/v1/domain_signoff_routes.py` | 59 | 4 | 93% |
| `app/api/v1/export_routes.py` | 56 | 3 | 95% |
| `app/api/v1/health_routes.py` | 5 | 0 | 100% |
| `app/api/v1/import_routes.py` | 37 | 5 | 86% |
| `app/api/v1/lookup_routes.py` | 70 | 6 | 91% |
| `app/api/v1/release_routes.py` | 70 | 8 | 89% |
| `app/api/v1/revision_routes.py` | 23 | 4 | 83% |
| `app/api/v1/serializers.py` | 29 | 0 | 100% |
| `app/api/v1/status_code_routes.py` | 127 | 15 | 88% |
| `app/api/v1/user_routes.py` | 71 | 7 | 90% |
| `app/audit/__init__.py` | 0 | 0 | 100% |
| `app/auth/__init__.py` | 0 | 0 | 100% |
| `app/auth/decorators.py` | 79 | 3 | 96% |
| `app/auth/password.py` | 30 | 0 | 100% |
| `app/auth/providers.py` | 27 | 1 | 96% |
| `app/auth/rate_limit.py` | 29 | 1 | 97% |
| `app/cli.py` | 20 | 2 | 90% |
| `app/config.py` | 29 | 0 | 100% |
| `app/db_modes.py` | 15 | 0 | 100% |
| `app/domain/__init__.py` | 0 | 0 | 100% |
| `app/domain/authz.py` | 5 | 0 | 100% |
| `app/domain/errors.py` | 20 | 0 | 100% |
| `app/domain/lifecycle.py` | 19 | 0 | 100% |
| `app/errors.py` | 24 | 3 | 88% |
| `app/export/__init__.py` | 0 | 0 | 100% |
| `app/export/csv_exporter.py` | 17 | 0 | 100% |
| `app/export/full_database_exporter.py` | 22 | 1 | 95% |
| `app/export/json_exporter.py` | 3 | 0 | 100% |
| `app/export/pdf_exporter.py` | 28 | 3 | 89% |
| `app/export/xlsx_exporter.py` | 20 | 0 | 100% |
| `app/extensions.py` | 9 | 0 | 100% |
| `app/logging_config.py` | 33 | 0 | 100% |
| `app/models/__init__.py` | 8 | 0 | 100% |
| `app/models/audit.py` | 14 | 0 | 100% |
| `app/models/change_request.py` | 56 | 0 | 100% |
| `app/models/export_job.py` | 15 | 0 | 100% |
| `app/models/import_job.py` | 14 | 0 | 100% |
| `app/models/lookup.py` | 79 | 0 | 100% |
| `app/models/release.py` | 23 | 0 | 100% |
| `app/models/status_code.py` | 87 | 0 | 100% |
| `app/models/user.py` | 31 | 0 | 100% |
| `app/repositories/__init__.py` | 0 | 0 | 100% |
| `app/repositories/audit_repository.py` | 22 | 1 | 95% |
| `app/repositories/base.py` | 20 | 1 | 95% |
| `app/repositories/change_request_repository.py` | 21 | 0 | 100% |
| `app/repositories/release_repository.py` | 4 | 0 | 100% |
| `app/repositories/status_code_repository.py` | 61 | 2 | 97% |
| `app/repositories/user_repository.py` | 25 | 1 | 96% |
| `app/security_headers.py` | 15 | 0 | 100% |
| `app/services/__init__.py` | 0 | 0 | 100% |
| `app/services/audit_service.py` | 23 | 0 | 100% |
| `app/services/auth_service.py` | 63 | 9 | 86% |
| `app/services/change_request_service.py` | 176 | 12 | 93% |
| `app/services/domain_signoff_service.py` | 90 | 5 | 94% |
| `app/services/export_service.py` | 66 | 1 | 98% |
| `app/services/import_service.py` | 147 | 20 | 86% |
| `app/services/lookup_admin_service.py` | 96 | 7 | 93% |
| `app/services/lookup_service.py` | 33 | 6 | 82% |
| `app/services/numbering_service.py` | 52 | 3 | 94% |
| `app/services/release_service.py` | 95 | 6 | 94% |
| `app/services/revision_diff_service.py` | 35 | 0 | 100% |
| `app/services/status_code_service.py` | 269 | 15 | 94% |
| `app/services/user_service.py` | 98 | 3 | 97% |
| `app/services/validation.py` | 43 | 6 | 86% |
| `app/ui/__init__.py` | 22 | 1 | 95% |
| `app/ui/admin_views.py` | 115 | 57 | 50% |
| `app/ui/auth_views.py` | 47 | 20 | 57% |
| `app/ui/change_request_views.py` | 164 | 38 | 77% |
| `app/ui/dashboard_views.py` | 24 | 1 | 96% |
| `app/ui/export_views.py` | 9 | 0 | 100% |
| `app/ui/import_views.py` | 33 | 18 | 45% |
| `app/ui/release_views.py` | 80 | 33 | 59% |
| `app/ui/status_code_views.py` | 189 | 73 | 61% |
| `app/utils.py` | 9 | 0 | 100% |

## 6. Traceability evidence check

`docs/20-traceability-matrix.md` cites 256 test names / test files as evidence. **256 resolve** to a test that exists; **0 are stale**.

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
| ✅ | `test_orm_guard_blocks_an_illegal_status_assignment` |  | BR-004, TC-001, TC-002 | 0.41 s |
| ✅ | `test_terminal_and_gated_states_cannot_be_skipped` |  | BR-004, TC-001, TC-002 | 0.00 s |
| ✅ | `test_there_are_exactly_seven_states` |  | BR-004, TC-001, TC-002 | 0.01 s |

### `tests/unit/test_password.py` — 5 tests, 5 passed

| Result | Test | Purpose | Requirements | Time |
|---|---|---|---|---|
| ✅ | `test_hash_and_verify_round_trip` |  |  | 0.10 s |
| ✅ | `test_policy_accepts_reasonable_password` |  |  | 0.00 s |
| ✅ | `test_policy_rejects_blocklisted_password` |  |  | 0.00 s |
| ✅ | `test_policy_rejects_short_password` |  |  | 0.00 s |
| ✅ | `test_verify_rejects_wrong_password` |  |  | 0.10 s |

### `tests/unit/test_rate_limit.py` — 4 tests, 4 passed

| Result | Test | Purpose | Requirements | Time |
|---|---|---|---|---|
| ✅ | `test_allows_attempts_under_the_limit` |  |  | 0.00 s |
| ✅ | `test_blocks_after_five_username_attempts` |  |  | 0.00 s |
| ✅ | `test_blocks_after_ten_ip_attempts_across_usernames` |  |  | 0.00 s |
| ✅ | `test_username_limit_is_case_insensitive` |  |  | 0.00 s |

### `tests/unit/test_validation.py` — 11 tests, 11 passed

_FR-022, FR-027 field rules from docs/06-data-dictionary.md, v3_

| Result | Test | Purpose | Requirements | Time |
|---|---|---|---|---|
| ✅ | `test_description_too_short` |  | FR-022, FR-027 | 0.00 s |
| ✅ | `test_number_of_times_repeated_must_be_at_least_one` |  | FR-022, FR-027 | 0.00 s |
| ✅ | `test_repeated_over_the_course_format` |  | FR-022, FR-027 | 0.00 s |
| ✅ | `test_reset_delay_rejects_missing_unit` |  | FR-022, FR-027 | 0.00 s |
| ✅ | `test_set_delay_accepts_leading_star_and_units` |  | FR-022, FR-027 | 0.00 s |
| ✅ | `test_set_delay_rejects_missing_unit` |  | FR-022, FR-027 | 0.00 s |
| ✅ | `test_status_category_must_be_error_warning_or_info` |  | FR-022, FR-027 | 0.00 s |
| ✅ | `test_title_must_not_equal_description` |  | FR-022, FR-027 | 0.00 s |
| ✅ | `test_title_too_short` |  | FR-022, FR-027 | 0.00 s |
| ✅ | `test_turbine_platforms_required_when_provided_empty` |  | FR-022, FR-027 | 0.00 s |
| ✅ | `test_valid_data_has_no_errors` |  | FR-022, FR-027 | 0.00 s |

### `tests/integration/test_audit_coverage.py` — 7 tests, 7 passed

_FR-056, FR-070, FR-072, FR-073, NFR-006, TC-015, TC-015a: the audit trail_

| Result | Test | Purpose | Requirements | Time |
|---|---|---|---|---|
| ✅ | `test_audit_log_entries_cannot_be_updated_or_deleted` | FR-072: append-only at the database layer, not just by omission. | FR-072 | 0.12 s |
| ✅ | `test_each_lifecycle_action_is_audited_exactly_once` | TC-015: one entry per state-changing action across the whole lifecycle. | TC-015 | 1.43 s |
| ✅ | `test_import_lifecycle_is_audited` |  | FR-056, FR-070, FR-072, FR-073, NFR-006, TC-015, TC-015a | 0.21 s |
| ✅ | `test_sandbox_delete_keeps_full_snapshot_and_creation_entry` | TC-015a / FR-056 / FR-073. | FR-056, FR-073, TC-015a | 0.44 s |
| ✅ | `test_subgroup_creation_is_audited_as_subgroup_create` |  | FR-056, FR-070, FR-072, FR-073, NFR-006, TC-015, TC-015a | 0.17 s |
| ✅ | `test_unexpected_import_failure_marks_job_failed_and_is_audited` |  | FR-056, FR-070, FR-072, FR-073, NFR-006, TC-015, TC-015a | 0.30 s |
| ✅ | `test_user_and_auth_events_are_audited` |  | FR-056, FR-070, FR-072, FR-073, NFR-006, TC-015, TC-015a | 0.23 s |

### `tests/integration/test_audit_log.py` — 4 tests, 4 passed

_FR-070-FR-071: audit log search, Administrator full access,_

| Result | Test | Purpose | Requirements | Time |
|---|---|---|---|---|
| ✅ | `test_admin_sees_all_entries` |  | FR-070, FR-071 | 0.22 s |
| ✅ | `test_engineer_cannot_view_audit_log` |  | FR-070, FR-071 | 0.17 s |
| ✅ | `test_filter_by_entity_type` |  | FR-070, FR-071 | 0.22 s |
| ✅ | `test_reviewer_only_sees_own_actions` |  | FR-070, FR-071 | 0.31 s |

### `tests/integration/test_auth.py` — 7 tests, 7 passed

_FR-001-FR-004, SEC-001-SEC-004._

| Result | Test | Purpose | Requirements | Time |
|---|---|---|---|---|
| ✅ | `test_deactivated_user_is_immediately_rejected` |  | FR-001, FR-004, SEC-001, SEC-004 | 0.17 s |
| ✅ | `test_five_failed_attempts_locks_the_account` | The 5th consecutive failure both locks the account (SEC-004) and | SEC-004 | 0.39 s |
| ✅ | `test_login_success_returns_user_and_sets_session` |  | FR-001, FR-004, SEC-001, SEC-004 | 0.17 s |
| ✅ | `test_logout_invalidates_session` |  | FR-001, FR-004, SEC-001, SEC-004 | 0.27 s |
| ✅ | `test_me_requires_login` |  | FR-001, FR-004, SEC-001, SEC-004 | 0.07 s |
| ✅ | `test_password_reset_invalidates_existing_session` |  | FR-001, FR-004, SEC-001, SEC-004 | 0.24 s |
| ✅ | `test_wrong_password_is_rejected` |  | FR-001, FR-004, SEC-001, SEC-004 | 0.17 s |

### `tests/integration/test_change_requests.py` — 11 tests, 11 passed

_FR-030-FR-039, FR-027-FR-029, BR-004/BR-005. Full submit -> dual-review ->_

| Result | Test | Purpose | Requirements | Time |
|---|---|---|---|---|
| ✅ | `test_author_cannot_sign_off_own_cr` |  | BR-004, BR-005, FR-027, FR-029, FR-030, FR-039 | 0.50 s |
| ✅ | `test_chief_engineer_cannot_be_a_prior_signer` |  | BR-004, BR-005, FR-027, FR-029, FR-030, FR-039 | 0.67 s |
| ✅ | `test_domain_signoff_rejects_user_without_that_domain` |  | BR-004, BR-005, FR-027, FR-029, FR-030, FR-039 | 0.28 s |
| ✅ | `test_dual_signoff_in_either_order_reaches_pending_approval` |  | BR-004, BR-005, FR-027, FR-029, FR-030, FR-039 | 0.59 s |
| ✅ | `test_full_happy_path_to_approved` |  | BR-004, BR-005, FR-027, FR-029, FR-030, FR-039 | 0.70 s |
| ✅ | `test_rejection_returns_to_draft_and_clears_signoffs` |  | BR-004, BR-005, FR-027, FR-029, FR-030, FR-039 | 0.59 s |
| ✅ | `test_reviewer_rejection_without_comment_is_rejected` |  | BR-004, BR-005, FR-027, FR-029, FR-030, FR-039 | 0.45 s |
| ✅ | `test_submit_blocked_until_domain_signoff_complete` |  | BR-004, BR-005, FR-027, FR-029, FR-030, FR-039 | 0.35 s |
| ✅ | `test_withdraw_forbidden_for_non_author` |  | BR-004, BR-005, FR-027, FR-029, FR-030, FR-039 | 0.29 s |
| ✅ | `test_withdraw_removes_abandoned_new_draft` |  | BR-004, BR-005, FR-027, FR-029, FR-030, FR-039 | 0.21 s |
| ✅ | `test_withdraw_revision_type_restores_prior_current_revision` | Regression test: withdrawing a REVISION-type CR must restore the | BR-004, BR-005, FR-027, FR-029, FR-030, FR-039 | 0.92 s |

### `tests/integration/test_csrf.py` — 2 tests, 2 passed

_docs/11-security-architecture.md §5: CSRF synchronizer-token protection_

| Result | Test | Purpose | Requirements | Time |
|---|---|---|---|---|
| ✅ | `test_state_changing_request_with_csrf_token_succeeds` |  |  | 0.20 s |
| ✅ | `test_state_changing_request_without_csrf_token_is_rejected` |  |  | 0.18 s |

### `tests/integration/test_decision_trail.py` — 5 tests, 5 passed

_Where review comments live: the change-request page, the status-code_

| Result | Test | Purpose | Requirements | Time |
|---|---|---|---|---|
| ✅ | `test_audit_entries_carry_the_comment_text_and_id` |  |  | 0.95 s |
| ✅ | `test_audit_log_can_be_filtered_by_action_and_actor` |  |  | 0.87 s |
| ✅ | `test_status_code_page_lists_all_decisions_and_comments` |  |  | 0.84 s |
| ✅ | `test_viewers_cannot_see_the_review_discussion` |  |  | 0.65 s |
| ✅ | `test_withdrawing_keeps_the_discussion_in_the_audit_log` |  |  | 0.68 s |

### `tests/integration/test_deprecation.py` — 7 tests, 7 passed

_FR-050-FR-052, BR-006, docs/05-governance-handbook.md §5, §11._

| Result | Test | Purpose | Requirements | Time |
|---|---|---|---|---|
| ✅ | `test_archive_blocked_before_retention_period_elapses` |  | BR-006, FR-050, FR-052 | 0.77 s |
| ✅ | `test_archive_succeeds_after_retention_period` |  | BR-006, FR-050, FR-052 | 0.98 s |
| ✅ | `test_deprecation_requires_released_state` |  | BR-006, FR-050, FR-052 | 0.20 s |
| ✅ | `test_full_deprecation_cycle` |  | BR-006, FR-050, FR-052 | 1.13 s |
| ✅ | `test_non_admin_cannot_archive_or_reinstate` |  | BR-006, FR-050, FR-052 | 0.22 s |
| ✅ | `test_reinstate_deprecated_code` |  | BR-006, FR-050, FR-052 | 0.86 s |
| ✅ | `test_second_revision_does_not_violate_current_uniqueness` | Regression test: create_revision must flip the old current revision's | BR-006, FR-050, FR-052 | 0.81 s |

### `tests/integration/test_exports_and_diff.py` — 15 tests, 15 passed

_FR-032, FR-045, FR-046, FR-054, FR-064, BR-008, SEC-023, TC-023, TC-035:_

| Result | Test | Purpose | Requirements | Time |
|---|---|---|---|---|
| ✅ | `test_diff_card_renders_on_change_request_page` |  | BR-008, FR-032, FR-045, FR-046, FR-054, FR-064, SEC-023, TC-023, TC-035 | 0.63 s |
| ✅ | `test_diff_hidden_from_viewers_for_open_revisions_and_unknown_revisions` |  | BR-008, FR-032, FR-045, FR-046, FR-054, FR-064, SEC-023, TC-023, TC-035 | 1.13 s |
| ✅ | `test_export_file_names_carry_a_timestamp` | Every export file name ends with the generation time, YYYY-MM-DD_HH-MM (UTC). | BR-008, FR-032, FR-045, FR-046, FR-054, FR-064, SEC-023, TC-023, TC-035 | 0.95 s |
| ✅ | `test_exports_neutralise_formula_injection` |  | BR-008, FR-032, FR-045, FR-046, FR-054, FR-064, SEC-023, TC-023, TC-035 | 0.54 s |
| ✅ | `test_json_export_is_flat_rows` |  | BR-008, FR-032, FR-045, FR-046, FR-054, FR-064, SEC-023, TC-023, TC-035 | 0.91 s |
| ✅ | `test_new_code_diff_is_marked_new` |  | BR-008, FR-032, FR-045, FR-046, FR-054, FR-064, SEC-023, TC-023, TC-035 | 0.43 s |
| ✅ | `test_release_can_be_deleted_before_publish_only` |  | BR-008, FR-032, FR-045, FR-046, FR-054, FR-064, SEC-023, TC-023, TC-035 | 1.03 s |
| ✅ | `test_released_export_contains_only_released_non_sandbox_codes` |  | BR-008, FR-032, FR-045, FR-046, FR-054, FR-064, SEC-023, TC-023, TC-035 | 1.03 s |
| ✅ | `test_released_export_filters_and_formats` |  | BR-008, FR-032, FR-045, FR-046, FR-054, FR-064, SEC-023, TC-023, TC-035 | 1.09 s |
| ✅ | `test_revision_diff_endpoint_and_cr_baseline_diff` |  | BR-008, FR-032, FR-045, FR-046, FR-054, FR-064, SEC-023, TC-023, TC-035 | 0.86 s |
| ✅ | `test_working_set_filters_by_lifecycle_state` |  | BR-008, FR-032, FR-045, FR-046, FR-054, FR-064, SEC-023, TC-023, TC-035 | 0.64 s |
| ✅ | `test_working_set_is_labelled_and_excludes_sandbox` |  | BR-008, FR-032, FR-045, FR-046, FR-054, FR-064, SEC-023, TC-023, TC-035 | 0.60 s |
| ✅ | `test_working_set_not_available_to_viewers_or_anonymous` |  | BR-008, FR-032, FR-045, FR-046, FR-054, FR-064, SEC-023, TC-023, TC-035 | 0.40 s |
| ✅ | `test_working_set_pdf_and_xlsx_render` |  | BR-008, FR-032, FR-045, FR-046, FR-054, FR-064, SEC-023, TC-023, TC-035 | 0.56 s |
| ✅ | `test_xlsx_export_has_same_rows_as_csv` | TC-035. | TC-035 | 0.89 s |

### `tests/integration/test_governance_extras.py` — 24 tests, 24 passed

_Remaining spec checks: SEC-010 service-layer authorization, FR-010/011/011a/014_

| Result | Test | Purpose | Requirements | Time |
|---|---|---|---|---|
| ✅ | `test_a_user_holds_exactly_one_role` |  | FR-005, FR-010, FR-021, FR-038, FR-048d, NFR-008, SEC-010 | 0.22 s |
| ✅ | `test_account_lock_and_password_events_are_audited` |  | FR-005, FR-010, FR-021, FR-038, FR-048d, NFR-008, SEC-010 | 0.63 s |
| ✅ | `test_auth_provider_seam_is_substitutable` | Callers depend on AuthenticatedUser only: a different provider returning | FR-005, FR-010, FR-021, FR-038, FR-048d, NFR-008, SEC-010 | 0.36 s |
| ✅ | `test_comment_leaves_state_and_signoffs_untouched` |  | FR-005, FR-010, FR-021, FR-038, FR-048d, NFR-008, SEC-010 | 0.68 s |
| ✅ | `test_import_preserves_legacy_reference_number` |  | FR-005, FR-010, FR-021, FR-038, FR-048d, NFR-008, SEC-010 | 0.45 s |
| ✅ | `test_next_available_preview_does_not_reserve_a_number` |  | FR-005, FR-010, FR-021, FR-038, FR-048d, NFR-008, SEC-010 | 0.69 s |
| ✅ | `test_services_enforce_roles_independently_of_route_decorators[<lambda>-ADMINISTRATOR]` |  | FR-005, FR-010, FR-021, FR-038, FR-048d, NFR-008, SEC-010 | 0.19 s |
| ✅ | `test_services_enforce_roles_independently_of_route_decorators[<lambda>-CHIEF_ENGINEER0]` |  | FR-005, FR-010, FR-021, FR-038, FR-048d, NFR-008, SEC-010 | 0.06 s |
| ✅ | `test_services_enforce_roles_independently_of_route_decorators[<lambda>-CHIEF_ENGINEER1]` |  | FR-005, FR-010, FR-021, FR-038, FR-048d, NFR-008, SEC-010 | 0.06 s |
| ✅ | `test_services_enforce_roles_independently_of_route_decorators[<lambda>-ENGINEER0]` |  | FR-005, FR-010, FR-021, FR-038, FR-048d, NFR-008, SEC-010 | 0.06 s |
| ✅ | `test_services_enforce_roles_independently_of_route_decorators[<lambda>-ENGINEER1]` |  | FR-005, FR-010, FR-021, FR-038, FR-048d, NFR-008, SEC-010 | 0.06 s |
| ✅ | `test_services_enforce_roles_independently_of_route_decorators[<lambda>-ENGINEER2]` |  | FR-005, FR-010, FR-021, FR-038, FR-048d, NFR-008, SEC-010 | 0.06 s |
| ✅ | `test_services_enforce_roles_independently_of_route_decorators[<lambda>-ENGINEER3]` |  | FR-005, FR-010, FR-021, FR-038, FR-048d, NFR-008, SEC-010 | 0.07 s |
| ✅ | `test_services_enforce_roles_independently_of_route_decorators[<lambda>-ENGINEER4]` |  | FR-005, FR-010, FR-021, FR-038, FR-048d, NFR-008, SEC-010 | 0.07 s |
| ✅ | `test_services_enforce_roles_independently_of_route_decorators[<lambda>-ENGINEER5]` |  | FR-005, FR-010, FR-021, FR-038, FR-048d, NFR-008, SEC-010 | 0.06 s |
| ✅ | `test_services_enforce_roles_independently_of_route_decorators[<lambda>-ENGINEER6]` |  | FR-005, FR-010, FR-021, FR-038, FR-048d, NFR-008, SEC-010 | 0.06 s |
| ✅ | `test_services_enforce_roles_independently_of_route_decorators[<lambda>-ENGINEER7]` |  | FR-005, FR-010, FR-021, FR-038, FR-048d, NFR-008, SEC-010 | 0.07 s |
| ✅ | `test_services_enforce_roles_independently_of_route_decorators[<lambda>-REVIEWER0]` |  | FR-005, FR-010, FR-021, FR-038, FR-048d, NFR-008, SEC-010 | 0.06 s |
| ✅ | `test_services_enforce_roles_independently_of_route_decorators[<lambda>-REVIEWER1]` |  | FR-005, FR-010, FR-021, FR-038, FR-048d, NFR-008, SEC-010 | 0.07 s |
| ✅ | `test_services_enforce_roles_independently_of_route_decorators[<lambda>-REVIEWER2]` |  | FR-005, FR-010, FR-021, FR-038, FR-048d, NFR-008, SEC-010 | 0.07 s |
| ✅ | `test_services_enforce_roles_independently_of_route_decorators[<lambda>-VIEWER0]` |  | FR-005, FR-010, FR-021, FR-038, FR-048d, NFR-008, SEC-010 | 0.06 s |
| ✅ | `test_services_enforce_roles_independently_of_route_decorators[<lambda>-VIEWER1]` |  | FR-005, FR-010, FR-021, FR-038, FR-048d, NFR-008, SEC-010 | 0.07 s |
| ✅ | `test_user_administration_events_are_audited` |  | FR-005, FR-010, FR-021, FR-038, FR-048d, NFR-008, SEC-010 | 0.41 s |
| ✅ | `test_whole_lifecycle_works_with_all_outbound_network_blocked` | The application must keep operating when it can reach nothing beyond | FR-005, FR-010, FR-021, FR-038, FR-048d, NFR-008, SEC-010 | 1.01 s |

### `tests/integration/test_import.py` — 7 tests, 7 passed

_FR-048a-d, EPIC-14: CSV/XLSX library import, still fully governed_

| Result | Test | Purpose | Requirements | Time |
|---|---|---|---|---|
| ✅ | `test_ambiguous_group_code_requires_range_hint` | WTUR is reused for a second, numerically distinct Hub Controller | FR-048a | 0.23 s |
| ✅ | `test_imported_row_becomes_import_type_draft_change_request` |  | FR-048a | 0.22 s |
| ✅ | `test_invalid_row_is_reported_and_creates_nothing` |  | FR-048a | 0.21 s |
| ✅ | `test_non_admin_engineer_can_upload_import` |  | FR-048a | 0.19 s |
| ✅ | `test_unknown_functional_system_group_code_reported_as_error` |  | FR-048a | 0.19 s |
| ✅ | `test_unsupported_file_extension_rejected` |  | FR-048a | 0.18 s |
| ✅ | `test_viewer_cannot_upload_import` |  | FR-048a | 0.28 s |

### `tests/integration/test_invariants.py` — 15 tests, 15 passed

_Business-rule and data-integrity checks: BR-001..BR-003, BR-009, FR-023a,_

| Result | Test | Purpose | Requirements | Time |
|---|---|---|---|---|
| ✅ | `test_draft_can_be_saved_repeatedly_without_workflow_transitions` |  | BR-001, BR-003, BR-009, FR-023a, FR-024, FR-060, FR-064, TC-004, TC-008, TC-010, TC-013 | 0.47 s |
| ✅ | `test_duplicate_identifier_rejected_by_database` |  | BR-001, BR-003, BR-009, FR-023a, FR-024, FR-060, FR-064, TC-004, TC-008, TC-010, TC-013 | 0.70 s |
| ✅ | `test_each_subgroup_sub_band_numbers_independently` |  | BR-001, BR-003, BR-009, FR-023a, FR-024, FR-060, FR-064, TC-004, TC-008, TC-010, TC-013 | 0.08 s |
| ✅ | `test_exactly_one_current_revision_per_code` | BR-002 / TC-011. | BR-002, TC-011 | 0.84 s |
| ✅ | `test_filters_sort_and_pagination` |  | BR-001, BR-003, BR-009, FR-023a, FR-024, FR-060, FR-064, TC-004, TC-008, TC-010, TC-013 | 0.70 s |
| ✅ | `test_full_text_search_matches_identifier_title_and_description` |  | BR-001, BR-003, BR-009, FR-023a, FR-024, FR-060, FR-064, TC-004, TC-008, TC-010, TC-013 | 0.69 s |
| ✅ | `test_identifier_formats` |  | BR-001, BR-003, BR-009, FR-023a, FR-024, FR-060, FR-064, TC-004, TC-008, TC-010, TC-013 | 0.62 s |
| ✅ | `test_identifier_never_changes_after_allocation` | BR-001: a rejected-and-resubmitted CR keeps its identifier. | BR-001 | 0.78 s |
| ✅ | `test_in_flight_revision_cannot_be_edited_in_place` | FR-025: Review and later states are locked. | FR-025 | 0.74 s |
| ✅ | `test_new_revision_of_a_released_code_keeps_its_identifier` | BR-001 / FR-021: the identifier is allocated once, not again per revision. | BR-001, FR-021 | 1.16 s |
| ✅ | `test_only_one_open_revision_per_code` | BR-003 / TC-012: a second revision cannot be opened while one is open. | BR-003, TC-012 | 0.81 s |
| ✅ | `test_released_code_stays_visible_to_viewers_while_a_new_revision_is_open` | BR-009: opening revision 2 (a Draft) must not make the Released revision 1 | BR-009 | 0.92 s |
| ✅ | `test_revision_history_visible_to_viewer_only_once_decided` | FR-064 / BR-009. | BR-009, FR-064 | 0.94 s |
| ✅ | `test_sequential_submits_in_two_subgroups_do_not_interfere` |  | BR-001, BR-003, BR-009, FR-023a, FR-024, FR-060, FR-064, TC-004, TC-008, TC-010, TC-013 | 1.04 s |
| ✅ | `test_submit_requires_a_turbine_platform` |  | BR-001, BR-003, BR-009, FR-023a, FR-024, FR-060, FR-064, TC-004, TC-008, TC-010, TC-013 | 0.40 s |

### `tests/integration/test_lookup_admin.py` — 9 tests, 9 passed

_US-091: Administrator manages controlled vocabularies. docs/05-governance-_

| Result | Test | Purpose | Requirements | Time |
|---|---|---|---|---|
| ✅ | `test_admin_can_add_turbine_platform` |  | US-091 | 0.18 s |
| ✅ | `test_admin_can_create_new_functional_system_group_in_free_range` | FR-048g: into any currently free range (10000-10999, 14000-14999, | FR-048g | 0.17 s |
| ✅ | `test_admin_can_deactivate_and_relabel_a_value` |  | US-091 | 0.17 s |
| ✅ | `test_create_functional_subgroup_with_range` |  | US-091 | 0.17 s |
| ✅ | `test_duplicate_code_rejected` |  | US-091 | 0.17 s |
| ✅ | `test_functional_subgroup_overlap_rejected` | FR-048f: rejected with 409, naming the conflicting subgroup. | FR-048f | 0.16 s |
| ✅ | `test_functional_system_group_not_creatable_via_generic_endpoint` | v3 (EPIC-16): creation moved to a dedicated, non-overlap-validated | US-091 | 0.17 s |
| ✅ | `test_new_functional_system_group_range_overlap_rejected` | FR-048h: rejected with 409, naming the conflicting group. | FR-048h | 0.17 s |
| ✅ | `test_non_admin_cannot_create_lookup_value` |  | US-091 | 0.17 s |

### `tests/integration/test_numbering.py` — 4 tests, 4 passed

_docs/07-database-design.md §7a: atomic Functional Group/Subgroup allocation._

| Result | Test | Purpose | Requirements | Time |
|---|---|---|---|---|
| ✅ | `test_allocation_increments_and_persists` |  |  | 0.27 s |
| ✅ | `test_capacity_exhaustion_raises` |  |  | 0.11 s |
| ✅ | `test_first_allocation_in_a_group_starts_at_range_start` |  |  | 0.06 s |
| ✅ | `test_sandbox_allocation_never_collides_with_real_range` |  |  | 0.06 s |

### `tests/integration/test_releases.py` — 6 tests, 6 passed

_FR-040-FR-048, BR-006-BR-008._

| Result | Test | Purpose | Requirements | Time |
|---|---|---|---|---|
| ✅ | `test_cannot_change_items_after_publish` |  | BR-006, BR-008, FR-040, FR-048 | 0.72 s |
| ✅ | `test_csv_export_of_a_release` |  | BR-006, BR-008, FR-040, FR-048 | 0.71 s |
| ✅ | `test_full_database_export_requires_administrator` |  | BR-006, BR-008, FR-040, FR-048 | 0.28 s |
| ✅ | `test_full_release_lifecycle` |  | BR-006, BR-008, FR-040, FR-048 | 0.76 s |
| ✅ | `test_non_admin_cannot_create_release` |  | BR-006, BR-008, FR-040, FR-048 | 0.37 s |
| ✅ | `test_sandbox_revision_rejected_from_release_items` |  | BR-006, BR-008, FR-040, FR-048 | 0.19 s |

### `tests/integration/test_schema_migration.py` — 9 tests, 9 passed

_US-003/US-004 acceptance criteria: fresh DB matches docs/artifacts/schema.sql_

| Result | Test | Purpose | Requirements | Time |
|---|---|---|---|---|
| ✅ | `test_all_documented_tables_exist` |  | US-003, US-004 | 0.06 s |
| ✅ | `test_five_roles_seeded` |  | US-003, US-004 | 0.07 s |
| ✅ | `test_foreign_keys_enforced` | SEC/BR data-integrity depends on FK enforcement being on for every | US-003, US-004 | 0.07 s |
| ✅ | `test_functional_system_group_code_is_reused_for_hub_controller` | WTUR and WROT are each intentionally reused for a second, | US-003, US-004 | 0.06 s |
| ✅ | `test_only_sandbox_status_codes_can_be_deleted` | Exercises trg_prevent_nonsandbox_delete from docs/artifacts/schema.sql. | US-003, US-004 | 0.07 s |
| ✅ | `test_second_migration_is_reversible_and_idempotent` | A database already at the earlier baseline is brought up to date by the | US-003, US-004 | 0.18 s |
| ✅ | `test_thirty_eight_functional_subgroups_seeded` |  | US-003, US-004 | 0.07 s |
| ✅ | `test_three_turbine_platforms_seeded` |  | US-003, US-004 | 0.07 s |
| ✅ | `test_twelve_functional_system_groups_seeded` | 9 Main Controller groups + 3 Hub Controller groups (WTUR/WROT/WPPD | US-003, US-004 | 0.22 s |

### `tests/integration/test_status_codes.py` — 9 tests, 9 passed

_FR-020-FR-029, FR-053-FR-056, FR-060-FR-064._

| Result | Test | Purpose | Requirements | Time |
|---|---|---|---|---|
| ✅ | `test_admin_sandbox_gets_identifier_immediately` |  | FR-020, FR-029, FR-053, FR-056, FR-060, FR-064 | 0.19 s |
| ✅ | `test_create_rejects_invalid_fields` |  | FR-020, FR-029, FR-053, FR-056, FR-060, FR-064 | 0.17 s |
| ✅ | `test_create_rejects_missing_functional_subgroup` | BR-013: mandatory, never optional (corrected 2026-09-17). | BR-013 | 0.16 s |
| ✅ | `test_engineer_can_create_draft_with_no_identifier` |  | FR-020, FR-029, FR-053, FR-056, FR-060, FR-064 | 0.18 s |
| ✅ | `test_non_admin_cannot_create_sandbox` |  | FR-020, FR-029, FR-053, FR-056, FR-060, FR-064 | 0.18 s |
| ✅ | `test_sandbox_delete_requires_admin_and_sandbox_flag` |  | FR-020, FR-029, FR-053, FR-056, FR-060, FR-064 | 0.53 s |
| ✅ | `test_search_defaults_exclude_sandbox` |  | FR-020, FR-029, FR-053, FR-056, FR-060, FR-064 | 0.21 s |
| ✅ | `test_viewer_cannot_create_status_code` |  | FR-020, FR-029, FR-053, FR-056, FR-060, FR-064 | 0.16 s |
| ✅ | `test_viewer_cannot_see_draft_status_codes` |  | FR-020, FR-029, FR-053, FR-056, FR-060, FR-064 | 0.29 s |

### `tests/integration/test_ui_screens.py` — 18 tests, 18 passed

_S1–S19 server-rendered UI: every screen renders for the roles that can_

| Result | Test | Purpose | Requirements | Time |
|---|---|---|---|---|
| ✅ | `test_admin_signoff_form_offers_access_override_and_submit_override` |  | NFR-007a, TC-036, UAT-13 | 0.77 s |
| ✅ | `test_comments_api_validates_and_is_role_restricted` |  | NFR-007a, TC-036, UAT-13 | 0.66 s |
| ✅ | `test_cr_detail_shows_role_specific_controls` |  | NFR-007a, TC-036, UAT-13 | 0.62 s |
| ✅ | `test_default_role_for_new_user_is_viewer` | SEC-012. | SEC-012 | 0.22 s |
| ✅ | `test_draft_cr_page_says_it_must_still_be_submitted` |  | NFR-007a, TC-036, UAT-13 | 0.71 s |
| ✅ | `test_every_screen_renders_for_an_administrator` |  | NFR-007a, TC-036, UAT-13 | 1.11 s |
| ✅ | `test_failed_form_submission_keeps_every_entered_value` | NFR-007a / TC-036 / UAT-13. | NFR-007a, TC-036, UAT-13 | 0.62 s |
| ✅ | `test_lookup_description_is_editable_and_flows_to_form_and_api` |  | NFR-007a, TC-036, UAT-13 | 0.65 s |
| ✅ | `test_lookup_selects_carry_inline_help_hooks` | NFR-007b: each lookup-backed select has a help target and per-option text. | NFR-007b | 0.45 s |
| ✅ | `test_people_are_shown_by_name_and_lists_show_the_title` | Authors, signers and commenters appear as "Full Name (Role)", never "User #n"; | NFR-007a, TC-036, UAT-13 | 0.95 s |
| ✅ | `test_role_specific_screens_render[chief_engineer-/change-requests/approval-queue]` |  | NFR-007a, TC-036, UAT-13 | 0.56 s |
| ✅ | `test_role_specific_screens_render[engineer-/change-requests/mine]` |  | NFR-007a, TC-036, UAT-13 | 0.45 s |
| ✅ | `test_role_specific_screens_render[engineer-/exports]` |  | NFR-007a, TC-036, UAT-13 | 0.44 s |
| ✅ | `test_role_specific_screens_render[reviewer-/change-requests/review-queue]` |  | NFR-007a, TC-036, UAT-13 | 0.43 s |
| ✅ | `test_role_specific_screens_render[viewer-/exports]` |  | NFR-007a, TC-036, UAT-13 | 0.46 s |
| ✅ | `test_role_specific_screens_render[viewer-/status-codes]` |  | NFR-007a, TC-036, UAT-13 | 0.46 s |
| ✅ | `test_sign_off_request_listed_on_my_change_requests` |  | NFR-007a, TC-036, UAT-13 | 0.60 s |
| ✅ | `test_ui_comment_reviewer_assignment_and_override_flow` |  | NFR-007a, TC-036, UAT-13 | 0.86 s |

### `tests/integration/test_users.py` — 7 tests, 7 passed

_FR-010-FR-014, SEC-003 §3 permission matrix, US-009._

| Result | Test | Purpose | Requirements | Time |
|---|---|---|---|---|
| ✅ | `test_admin_can_force_reset_another_users_password` |  | FR-010, FR-014, SEC-003, US-009 | 0.37 s |
| ✅ | `test_admin_can_list_and_create_users` |  | FR-010, FR-014, SEC-003, US-009 | 0.22 s |
| ✅ | `test_can_deactivate_administrator_when_another_remains_active` |  | FR-010, FR-014, SEC-003, US-009 | 0.36 s |
| ✅ | `test_cannot_deactivate_last_active_administrator` |  | FR-010, FR-014, SEC-003, US-009 | 0.16 s |
| ✅ | `test_create_user_rejects_weak_password` |  | FR-010, FR-014, SEC-003, US-009 | 0.17 s |
| ✅ | `test_non_admin_cannot_list_users` |  | FR-010, FR-014, SEC-003, US-009 | 0.17 s |
| ✅ | `test_self_password_change` |  | FR-010, FR-014, SEC-003, US-009 | 0.39 s |

### `tests/integration/test_workflow_gaps.py` — 18 tests, 18 passed

_Closes the gaps found in the spec-vs-code review (docs/20-traceability-matrix.md):_

| Result | Test | Purpose | Requirements | Time |
|---|---|---|---|---|
| ✅ | `test_admin_can_override_identifier_with_reason_and_it_is_audited` |  | BR-012, FR-021a, FR-025a, FR-028, FR-034, FR-039, SEC-013 | 0.56 s |
| ✅ | `test_admin_signoff_can_override_proposed_audience_access` |  | BR-012, FR-021a, FR-025a, FR-028, FR-034, FR-039, SEC-013 | 0.73 s |
| ✅ | `test_assigned_reviewer_only_may_sign_off` |  | BR-012, FR-021a, FR-025a, FR-028, FR-034, FR-039, SEC-013 | 0.77 s |
| ✅ | `test_cr_page_explains_when_no_engineer_holds_a_pending_domain` |  | BR-012, FR-021a, FR-025a, FR-028, FR-034, FR-039, SEC-013 | 0.32 s |
| ✅ | `test_domain_request_is_refused_when_nobody_holds_the_domain` | A request nobody could ever act on must not be silently accepted. | BR-012, FR-021a, FR-025a, FR-028, FR-034, FR-039, SEC-013 | 0.29 s |
| ✅ | `test_domain_signoff_request_surfaces_for_target_and_clears_once_signed` |  | BR-012, FR-021a, FR-025a, FR-028, FR-034, FR-039, SEC-013 | 0.73 s |
| ✅ | `test_domain_signoff_request_validation` |  | BR-012, FR-021a, FR-025a, FR-028, FR-034, FR-039, SEC-013 | 0.55 s |
| ✅ | `test_identifier_override_forbidden_for_engineer` |  | BR-012, FR-021a, FR-025a, FR-028, FR-034, FR-039, SEC-013 | 0.52 s |
| ✅ | `test_identifier_override_rejects_out_of_range_malformed_and_duplicate` |  | BR-012, FR-021a, FR-025a, FR-028, FR-034, FR-039, SEC-013 | 0.87 s |
| ✅ | `test_identifier_override_requires_reason` |  | BR-012, FR-021a, FR-025a, FR-028, FR-034, FR-039, SEC-013 | 0.56 s |
| ✅ | `test_no_reassignment_after_reviewer_signed_off` |  | BR-012, FR-021a, FR-025a, FR-028, FR-034, FR-039, SEC-013 | 0.72 s |
| ✅ | `test_only_administrator_endpoint_accepts_overrides` |  | BR-012, FR-021a, FR-025a, FR-028, FR-034, FR-039, SEC-013 | 0.61 s |
| ✅ | `test_rejection_ignores_access_overrides` |  | BR-012, FR-021a, FR-025a, FR-028, FR-034, FR-039, SEC-013 | 0.85 s |
| ✅ | `test_reviewer_assignment_validation_and_authorization` |  | BR-012, FR-021a, FR-025a, FR-028, FR-034, FR-039, SEC-013 | 0.66 s |
| ✅ | `test_reviewer_can_be_reassigned_and_unassigned` |  | BR-012, FR-021a, FR-025a, FR-028, FR-034, FR-039, SEC-013 | 0.78 s |
| ✅ | `test_unknown_access_override_field_is_rejected` |  | BR-012, FR-021a, FR-025a, FR-028, FR-034, FR-039, SEC-013 | 0.58 s |
| ✅ | `test_untargeted_domain_request_is_visible_to_every_domain_holder` |  | BR-012, FR-021a, FR-025a, FR-028, FR-034, FR-039, SEC-013 | 0.74 s |
| ✅ | `test_withdrawn_cr_removes_its_domain_requests` |  | BR-012, FR-021a, FR-025a, FR-028, FR-034, FR-039, SEC-013 | 0.56 s |

### `tests/system/test_cli_create_admin.py` — 2 tests, 2 passed

| Result | Test | Purpose | Requirements | Time |
|---|---|---|---|---|
| ✅ | `test_create_admin_cli_command` |  |  | 0.12 s |
| ✅ | `test_create_admin_cli_rejects_weak_password` |  |  | 0.07 s |

### `tests/system/test_health.py` — 1 tests, 1 passed

_US-001 acceptance criterion: app boots, health endpoint returns 200._

| Result | Test | Purpose | Requirements | Time |
|---|---|---|---|---|
| ✅ | `test_health_returns_ok` |  | US-001 | 0.07 s |

### `tests/system/test_injection_and_session.py` — 8 tests, 8 passed

_TC-017, TC-026, TC-027, SEC-002, SEC-003, SEC-020-SEC-022: injection_

| Result | Test | Purpose | Requirements | Time |
|---|---|---|---|---|
| ✅ | `test_audit_log_filters_resist_injection` |  | SEC-002, SEC-003, SEC-020, SEC-022, TC-017, TC-026, TC-027 | 0.17 s |
| ✅ | `test_idle_session_expires_after_thirty_minutes` | TC-017 / FR-002 / SEC-003. | FR-002, SEC-003, TC-017 | 0.16 s |
| ✅ | `test_recent_activity_keeps_the_session_alive` |  | SEC-002, SEC-003, SEC-020, SEC-022, TC-017, TC-026, TC-027 | 0.17 s |
| ✅ | `test_server_side_validation_ignores_client_side_constraints` | SEC-020: every rule is enforced server-side, whatever the browser did. | SEC-020 | 0.41 s |
| ✅ | `test_session_cookie_attributes` | SEC-002 (the Secure flag is off only in the dev/test configs). | SEC-002 | 0.16 s |
| ✅ | `test_session_expires_at_the_absolute_lifetime` | SEC-003: 12 hours regardless of activity. | SEC-003 | 0.16 s |
| ✅ | `test_sql_injection_probes_have_no_effect` | TC-027 / SEC-021. | SEC-021, TC-027 | 0.60 s |
| ✅ | `test_user_supplied_text_is_escaped_everywhere_it_renders` | TC-026 / SEC-022. | SEC-022, TC-026 | 0.94 s |

### `tests/system/test_logging_and_passwords.py` — 8 tests, 8 passed

_Security policy details from 11-security-architecture.md: §4 password policy_

| Result | Test | Purpose | Requirements | Time |
|---|---|---|---|---|
| ✅ | `test_administrator_reset_also_honours_history` |  |  | 0.51 s |
| ✅ | `test_authenticated_requests_record_the_user_id` |  |  | 0.16 s |
| ✅ | `test_blocklist_ignores_comments_and_short_entries` |  |  | 0.00 s |
| ✅ | `test_last_five_passwords_cannot_be_reused` |  |  | 2.78 s |
| ✅ | `test_only_hashes_are_stored_in_the_history` |  |  | 0.26 s |
| ✅ | `test_policy_length_and_blocklist` |  |  | 0.00 s |
| ✅ | `test_requests_are_logged_as_json_without_credentials` |  |  | 0.16 s |
| ✅ | `test_unhandled_errors_are_logged_with_the_request_id` |  |  | 0.37 s |

### `tests/system/test_no_cloud.py` — 3 tests, 3 passed

_US-120 / TC-029: block cloud-SDK imports, cloud identity providers and_

| Result | Test | Purpose | Requirements | Time |
|---|---|---|---|---|
| ✅ | `test_no_cloud_sdk_imports_in_source` |  | TC-029, US-120 | 0.36 s |
| ✅ | `test_no_cloud_sdk_in_requirements` |  | TC-029, US-120 | 0.00 s |
| ✅ | `test_templates_and_static_reference_no_external_assets` |  | TC-029, US-120 | 0.06 s |

### `tests/system/test_openapi_conformance.py` — 5 tests, 5 passed

_EPIC-11 / FR-080: the code and docs/artifacts/openapi.yaml describe the_

| Result | Test | Purpose | Requirements | Time |
|---|---|---|---|---|
| ✅ | `test_every_documented_operation_is_implemented_and_vice_versa` |  | FR-080 | 0.08 s |
| ✅ | `test_live_payloads_only_use_declared_properties` |  | FR-080 | 0.61 s |
| ✅ | `test_lookup_and_domain_request_payloads_match_contract` |  | FR-080 | 0.49 s |
| ✅ | `test_revision_diff_payload_matches_contract` |  | FR-080 | 0.62 s |
| ✅ | `test_unauthenticated_requests_are_rejected_for_every_documented_operation` |  | FR-080 | 0.10 s |

### `tests/system/test_permission_grid.py` — 12 tests, 12 passed

_TC-018 / TC-018a / TC-018b / TC-019 / FR-081 / SEC-010: the full_

| Result | Test | Purpose | Requirements | Time |
|---|---|---|---|---|
| ✅ | `test_api_endpoints_require_authentication` |  | FR-081, SEC-010, TC-018, TC-018a, TC-018b, TC-019 | 0.46 s |
| ✅ | `test_api_permission_grid[ADMINISTRATOR]` |  | FR-081, SEC-010, TC-018, TC-018a, TC-018b, TC-019 | 0.64 s |
| ✅ | `test_api_permission_grid[CHIEF_ENGINEER]` |  | FR-081, SEC-010, TC-018, TC-018a, TC-018b, TC-019 | 0.71 s |
| ✅ | `test_api_permission_grid[ENGINEER]` |  | FR-081, SEC-010, TC-018, TC-018a, TC-018b, TC-019 | 0.84 s |
| ✅ | `test_api_permission_grid[REVIEWER]` |  | FR-081, SEC-010, TC-018, TC-018a, TC-018b, TC-019 | 0.61 s |
| ✅ | `test_api_permission_grid[VIEWER]` |  | FR-081, SEC-010, TC-018, TC-018a, TC-018b, TC-019 | 0.61 s |
| ✅ | `test_ui_permission_grid[ADMINISTRATOR]` |  | FR-081, SEC-010, TC-018, TC-018a, TC-018b, TC-019 | 0.89 s |
| ✅ | `test_ui_permission_grid[CHIEF_ENGINEER]` |  | FR-081, SEC-010, TC-018, TC-018a, TC-018b, TC-019 | 0.61 s |
| ✅ | `test_ui_permission_grid[ENGINEER]` |  | FR-081, SEC-010, TC-018, TC-018a, TC-018b, TC-019 | 0.64 s |
| ✅ | `test_ui_permission_grid[REVIEWER]` |  | FR-081, SEC-010, TC-018, TC-018a, TC-018b, TC-019 | 0.64 s |
| ✅ | `test_ui_permission_grid[VIEWER]` |  | FR-081, SEC-010, TC-018, TC-018a, TC-018b, TC-019 | 0.53 s |
| ✅ | `test_ui_redirects_anonymous_users_to_login` |  | FR-081, SEC-010, TC-018, TC-018a, TC-018b, TC-019 | 0.44 s |

### `tests/system/test_production_config.py` — 7 tests, 7 passed

_SEC-002 / deployment hardening: a production instance must not start with a_

| Result | Test | Purpose | Requirements | Time |
|---|---|---|---|---|
| ✅ | `test_development_and_testing_still_start_with_the_default_key` |  | SEC-002 | 0.07 s |
| ✅ | `test_production_refuses_a_weak_secret_key[]` |  | SEC-002 | 0.00 s |
| ✅ | `test_production_refuses_a_weak_secret_key[change-me-in-every-real-environment]` |  | SEC-002 | 0.00 s |
| ✅ | `test_production_refuses_a_weak_secret_key[dev-secret-key-change-me]` |  | SEC-002 | 0.00 s |
| ✅ | `test_production_refuses_a_weak_secret_key[too-short]` |  | SEC-002 | 0.00 s |
| ✅ | `test_production_refuses_a_weak_secret_key[xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx]` |  | SEC-002 | 0.00 s |
| ✅ | `test_production_starts_with_a_strong_secret_key` |  | SEC-002 | 0.03 s |

### `tests/system/test_security_headers.py` — 4 tests, 4 passed

_SEC-025: standard security headers on every response._

| Result | Test | Purpose | Requirements | Time |
|---|---|---|---|---|
| ✅ | `test_api_response_has_security_headers` |  | SEC-025 | 0.07 s |
| ✅ | `test_hsts_sent_over_https` |  | SEC-025 | 0.07 s |
| ✅ | `test_templates_have_no_inline_script_or_handlers` | The CSP forbids inline script; guard against regressions. | SEC-025 | 0.03 s |
| ✅ | `test_ui_page_has_csp_and_no_hsts_over_plain_http` |  | SEC-025 | 0.10 s |

### `tests/system/test_uat.py` — 14 tests, 14 passed

_TC-030: UAT-01 .. UAT-13 (docs/13-test-strategy.md §7) as scripted_

| Result | Test | Purpose | Requirements | Time |
|---|---|---|---|---|
| ✅ | `test_uat_01_new_code_has_no_identifier_until_submitted` |  | UAT-01 | 0.90 s |
| ✅ | `test_uat_02_either_signoff_order_reaches_pending_approval_automatically` |  | UAT-02 | 0.65 s |
| ✅ | `test_uat_03_chief_engineer_approval_visible_to_the_engineer` |  | UAT-03 | 0.87 s |
| ✅ | `test_uat_04_rejection_comment_visible_and_prior_signoff_cleared` |  | UAT-04 | 0.84 s |
| ✅ | `test_uat_05_cross_domain_signoff_unblocks_submit` |  | UAT-05 | 0.61 s |
| ✅ | `test_uat_06_release_build_excludes_unselected_and_sandbox` |  | UAT-06 | 1.26 s |
| ✅ | `test_uat_07_viewer_searches_and_exports_released_catalogue_for_one_group` |  | UAT-07 | 1.01 s |
| ✅ | `test_uat_08_sandbox_lifecycle_and_traceable_deletion` |  | UAT-08 | 0.46 s |
| ✅ | `test_uat_09_nobody_can_decide_their_own_submission` |  | UAT-09 | 0.72 s |
| ✅ | `test_uat_09b_chief_engineer_cannot_be_a_prior_signer_or_author` |  | TC-030, UAT-01, UAT-13 | 0.82 s |
| ✅ | `test_uat_10_full_database_export_is_administrator_only` |  | UAT-10 | 0.63 s |
| ✅ | `test_uat_11_import_creates_only_governed_drafts_and_an_error_report` |  | UAT-11 | 0.49 s |
| ✅ | `test_uat_12_subgroup_is_mandatory_and_overlaps_are_refused` |  | UAT-12 | 0.48 s |
| ✅ | `test_uat_13_failed_form_keeps_input_and_dropdowns_explain_themselves` |  | UAT-13 | 0.46 s |

### `tests/performance/test_performance.py` — 9 tests, 9 passed

_NFR-001, TC-024, TC-025, NFR-004: performance targets on a temp-file SQLite_

| Result | Test | Purpose | Requirements | Time |
|---|---|---|---|---|
| ✅ | `test_concurrent_identifier_allocation_in_one_group` | TC-025: parallel submissions in one popular group yield unique, gap-free | TC-025 | 0.47 s |
| ✅ | `test_export_issues_a_constant_number_of_queries` | Regression guard for the N+1 problem: exporting 500 revisions must not cost | NFR-001, NFR-004, TC-024, TC-025 | 0.33 s |
| ✅ | `test_export_of_5000_records_within_target[csv-5]` | NFR-001: CSV/JSON <= 5 s, PDF <= 15 s for 5,000 records (XLSX held to the PDF limit). | NFR-001 | 0.82 s |
| ✅ | `test_export_of_5000_records_within_target[json-5]` | NFR-001: CSV/JSON <= 5 s, PDF <= 15 s for 5,000 records (XLSX held to the PDF limit). | NFR-001 | 0.81 s |
| ✅ | `test_export_of_5000_records_within_target[pdf-15]` | NFR-001: CSV/JSON <= 5 s, PDF <= 15 s for 5,000 records (XLSX held to the PDF limit). | NFR-001 | 2.66 s |
| ✅ | `test_export_of_5000_records_within_target[xlsx-15]` | NFR-001: CSV/JSON <= 5 s, PDF <= 15 s for 5,000 records (XLSX held to the PDF limit). | NFR-001 | 1.74 s |
| ✅ | `test_fifty_concurrent_users_are_served_without_errors` | NFR-004: 50 concurrent named users (each searching every ~8 s — | NFR-004 | 26.97 s |
| ✅ | `test_reads_are_not_blocked_by_an_open_write_transaction` | WAL read concurrency: a reader proceeds while another connection holds | NFR-001, NFR-004, TC-024, TC-025 | 0.36 s |
| ✅ | `test_search_and_read_latency_at_20000_revisions` | TC-024. | TC-024 | 5.22 s |

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


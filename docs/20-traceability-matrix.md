# 20. Traceability Matrix — Spec vs. Code vs. Tests

**Reviewed:** 2026-10-23 against branch `dev` (code in `cscm_tool/`), baseline v4.0. **607 automated tests pass** (598 functional + 9 load tests) in every final verification run (§7), in three different ways: file order, reversed and shuffled order, and the whole suite on a real SQLite file; line coverage is 92% overall; `black`, `ruff`, `mypy` and `bandit` are clean; `pip-audit` reports no vulnerability in any runtime dependency. The full per-test results, measurements, requirement accounting (§6a) and run history are in the generated [24-test-report.md](24-test-report.md).

**Legend:** ✅ implemented **and** covered by an automated test · ➖ out of MVP scope by design · 🧑 needs a human or the production environment (cannot be proven by the test suite — listed in §6).

A ✅ means "an automated test exercises it", not "a person signed it off". Test paths are under `cscm_tool/tests/`.

## 1. Summary

| Area | ✅ | ➖ | 🧑 |
|---|---|---|---|
| Functional requirements (FR) — 130 | 130 | 0 | 0 |
| Business rules (BR) — 23 | 23 | 0 | 0 |
| Security (SEC) — 24 | 24 | 0 | 0 (TLS termination and key custody are deployment checks, §6) |
| Audit (AUD) — 8 | 8 | 0 | 0 |
| Non-functional (NFR) — 14 | 12 | 1 (NFR-002 availability) | 1 (NFR-007 usability needs UAT) |
| Test matrix (every TC in 13-test-strategy.md §8 and §8a, TC-001 … TC-070) | all | 0 | TC-030: scripted ✅, human sign-off 🧑 |

## 1a. The v4 pass (2026-10-23)

The improvement pack of 21-improvement-ideas.md was implemented, specified (03-srs.md §1.10–§1.15), documented and verified three times (13-test-strategy.md §11). Rows for every new requirement are in §3a and §4; the new test cases are TC-038 … TC-052. **Defects found by the verification itself, all fixed and covered:**
1. **Fuzzy search crashed for queries with several words** (`fts5: syntax error near "("`): each word that expands to a group of close spellings must be joined with `AND`; found by the 20,000-revision load test, now `test_search_and_help::test_several_misspelt_words_are_all_tolerated_together`.
2. **A test assumed an in-memory suite database** and failed when the whole suite ran on a file (`test_backup_needs_a_file_database`); found by methodology 3.
3. **Test isolation:** a shared instance directory let one test's audit-chain anchor make another test's audit log look truncated; every test now has its own instance directory.
4. **Admin pages missed accessibility basics** (table header scope, unlabelled inputs) — found by `test_accessibility`.
5. **Hub sub-bands did not follow the handbook** (they counted from x001, e.g. `12-3xx` = 12301–12400 and `11-0xx` = 11000–11100; later renamed `123xx` and `110xx`, and `099xx-a` … `-f` became `0990x` … `0999x`, migration `f6c8e0a2b459`): aligned to the hundreds by migration `a1d4f6b8c203`, `test_schema_migration::test_hub_sub_bands_are_aligned_to_the_hundreds_of_their_prefix`, `test_schema_upgrade::test_hub_sub_bands_are_shifted_to_the_hundreds_by_the_upgrade`.
6. **Documentation errors** found by `test_docs_consistency` and two reading passes: dangling section references (a handbook §2a that did not exist), two wrong UI labels in the manual, a stale per-module test count, and statements about the old behaviour that the code had outgrown (for example the claim that no `controller_type` column exists).

## 2. Changes made in the v3 pass (2026-10-21)

The review found 10 missing features and 8 defects; all are fixed and tested.

**Features added** — restricted audience-access confirm/override at Administrator sign-off (FR-025a/034, BR-012, SEC-013); revision diff API + CR/history UI (FR-032/064); Administrator identifier override with reason (FR-021a); Reviewer assignment (FR-039); "all Released" and labelled working-set exports + XLSX in the UI (FR-045/046); domain sign-off requests surfaced on Dashboard / My Change Requests (FR-028); change-request comments endpoint + UI (FR-038); pre-publish Release delete (BR-008); `IMPORT_*`, `SUBGROUP_CREATE`, `DOMAIN_SIGNOFF_REQUEST`, `REVIEWER_ASSIGN`, `IDENTIFIER_OVERRIDE`, `RELEASE_DELETE` audit events; lookup `description` inline help (NFR-007b); default role Viewer (SEC-012); append-only audit triggers (FR-072).

**Defects found by the new tests and fixed**
1. A CR rejected back to Draft and resubmitted — and every new revision of an already-numbered code — **allocated a fresh identifier**, violating BR-001/FR-021. Now allocated once.
2. Every read took the SQLite write lock (`BEGIN IMMEDIATE` on all transactions), so 50 concurrent users produced `database is locked`. Reads now use a deferred transaction (WAL read concurrency); only writers take the lock (NFR-004).
3. `lifecycle_status` could be set to any value by any code path; the 7-state machine is now enforced centrally (`app/domain/lifecycle.py`, BR-004).
4. Role checks lived only in route decorators; every role-restricted service entry point now enforces them too (`app/domain/authz.py`, SEC-010).
5. Comments (FR-038) had a service method but no endpoint or screen.
6. Nine implemented API operations were missing from `openapi.yaml`, and four response schemas under-declared fields; the contract and code now match and a test keeps them in sync.
7. Response security headers / CSP absent (SEC-025; earlier in this branch).
8. Three runtime dependencies had published vulnerabilities (Flask 3.0.3, waitress 3.0.0, python-dotenv 1.0.1) — upgraded to 3.1.3 / 3.0.2 / 1.2.2.

**Second verification pass (same day)** — re-testing in detail, with the permission grid corrected to the API specification, found six more defects, all fixed and covered:
1. **Viewers could read change requests** (`GET /change-requests`, `/change-requests/{id}` and the matching UI pages), exposing Draft and in-review content that BR-009 reserves for the four working roles. The first grid had encoded the wrong expectation.
2. **A Released code vanished for Viewers** (detail view and search) as soon as anyone opened a new Draft revision of it, because the "current" revision was the invisible Draft. Viewers now always see the latest Approved/Released/Deprecated/Archived revision.
3. `GET /status-codes/next-available` was open to every role; the specification limits it to Engineers and Administrators.
4. A production instance would start with the built-in development `SECRET_KEY`, making session cookies forgeable. It now refuses to start with the default, the `.env.example` placeholder, or any key shorter than 32 characters.
5. The password policy of `11-security-architecture.md` §4 lacked the **last-5 reuse block** (new `user_password_history` table, migration `c5e7a9b1d3f2`) and had a 7-entry block-list; the list is now a data file (`seed_data/common_passwords.txt`) that can be replaced with an internal breach corpus.
6. The **structured JSON logging** of §11 did not exist; request and error logs now carry the request id and never credentials or query strings. (Running a migration also used to silence all existing loggers; fixed.)
7. **Exports issued ~13 SQL queries per row** (lazy-loaded relationships): a 5,000-row CSV took ~4 s. Eager loading brings it to ~1 s with a constant number of queries, and a test now guards it.
8. **Review comments were not traceable**: audit entries for decisions and comments carried no text, withdrawing a change request deleted its discussion, and the status-code page showed none of it. Audit entries now carry the comment id and text, `WITHDRAW` keeps a snapshot, a *Decisions & Comments* tab lists everything per code (working roles only), and the Audit Log can be filtered by action.
9. Export file names now carry the generation time (`cscm_<kind>_YYYY-MM-DD_HH-MM.<ext>`, UTC) — `test_exports_and_diff::test_export_file_names_carry_a_timestamp`.
10. **Subgroup bands:** the first subgroup of each Main Controller group now covers the group's first 200 numbers (e.g. Tower 5000–5199) via schema seed and migration `d6f8b0c2e4a3` — `test_schema_migration::test_first_subgroup_of_every_main_group_covers_the_first_200_numbers`; the unseeded placeholder group `WNEW` was removed from the dev database (`test_no_placeholder_group_is_seeded`).
Also: `record_property` measurements are now carried into the report (`junit_family = xunit1`), and the report generator itself cross-checks that every test cited in this matrix still exists.

**Schema** — baseline `schema.sql` plus follow-on migration `b4d2f6a8c0e1` (idempotent, reversible, tested): `change_request.assigned_reviewer_id`, `domain_signoff_request`, `trg_audit_no_update/delete`, `description` on all 13 lookup tables. **Existing databases must run `flask db upgrade`.**

## 3. Functional requirements

| ID | Status | Evidence |
|---|---|---|
| FR-001 | ✅ | `test_auth::test_login_success…`, `test_wrong_password…`; `test_injection_and_session::test_session_cookie_attributes` |
| FR-002 | ✅ | `test_injection_and_session::test_idle_session_expires_after_thirty_minutes`, `…recent_activity_keeps…` |
| FR-003 | ✅ | `test_auth::test_logout_invalidates_session` |
| FR-004 | ✅ | `test_auth::test_five_failed_attempts_locks_the_account`; `unit/test_rate_limit.py`; `test_governance_extras::test_account_lock_and_password_events_are_audited` |
| FR-005 | ✅ | `test_governance_extras::test_auth_provider_seam_is_substitutable` (SSO itself ➖, Phase 2) |
| FR-010 | ✅ | `test_users::test_admin_can_list_and_create_users`; `test_governance_extras::test_user_administration_events_are_audited` |
| FR-011 | ✅ | `test_governance_extras::test_a_user_holds_exactly_one_role`, `…user_administration_events…` (ROLE_CHANGE) |
| FR-011a | ✅ | `…user_administration_events…` (DOMAIN_TAG_CHANGE); domain sign-off tests |
| FR-012 | ✅ | `test_users::test_cannot_deactivate_last_active_administrator` |
| FR-013 | ✅ | `test_users::test_self_password_change`; `unit/test_password.py` |
| FR-014 | ✅ | `test_users::test_admin_can_force_reset…`; `test_auth::test_password_reset_invalidates…` |
| FR-020 | ✅ | `test_status_codes::test_engineer_can_create_draft…`, `…rejects_missing_functional_subgroup` |
| FR-021 | ✅ | `test_numbering.py`; `test_governance_extras::test_next_available_preview_does_not_reserve_a_number`; `test_invariants::test_identifier_never_changes…`, `…new_revision_of_a_released_code_keeps_its_identifier` |
| FR-021a | ✅ | `test_workflow_gaps::test_admin_can_override_identifier…`, `…requires_reason`, `…forbidden_for_engineer`, `…rejects_out_of_range_malformed_and_duplicate` |
| FR-022 | ✅ | `unit/test_validation.py`; `test_status_codes::test_create_rejects_invalid_fields`; `test_injection_and_session::test_server_side_validation…` |
| FR-023 | ✅ | `test_invariants::test_duplicate_identifier_rejected_by_database` |
| FR-023a | ✅ | `test_invariants::test_submit_requires_a_turbine_platform` |
| FR-024 | ✅ | `test_invariants::test_draft_can_be_saved_repeatedly…` |
| FR-025 | ✅ | `test_invariants::test_in_flight_revision_cannot_be_edited_in_place`; copy-on-write in `test_deprecation` |
| FR-025a | ✅ | `test_workflow_gaps::test_admin_signoff_can_override_proposed_audience_access`; `test_ui_screens::test_ui_comment_reviewer_assignment_and_override_flow` |
| FR-026 | ✅ | `test_change_requests::test_withdraw_*` |
| FR-027 | ✅ | `test_change_requests::test_submit_blocked_until_domain_signoff_complete` |
| FR-028 | ✅ | `test_workflow_gaps::test_domain_signoff_request_*` (4 tests); `test_ui_screens::test_sign_off_request_listed_on_my_change_requests`; `test_uat::test_uat_05…` |
| FR-029 | ✅ | `test_change_requests::test_domain_signoff_rejects_user_without_that_domain` |
| FR-030 | ✅ | CR created for every draft/revision/import/deprecation (`test_import`, `test_deprecation`) |
| FR-031 | ✅ | `test_uat::test_uat_01…` (review queue is the notification; see §5 note) |
| FR-032 | ✅ | `test_exports_and_diff::test_revision_diff_endpoint_and_cr_baseline_diff`, `…new_code_diff_is_marked_new`, `…diff_card_renders…` |
| FR-033 | ✅ | `test_change_requests::test_reviewer_rejection_without_comment…`, `…rejection_returns_to_draft…` |
| FR-034 | ✅ | `test_change_requests` admin paths; `test_workflow_gaps` override tests |
| FR-035 | ✅ | `test_change_requests::test_dual_signoff_in_either_order…`; `test_uat::test_uat_02…` |
| FR-036 | ✅ | `test_change_requests::test_full_happy_path_to_approved`; `test_uat::test_uat_03…` |
| FR-037 | ✅ | `test_change_requests::test_author_cannot_sign_off_own_cr`, `…chief_engineer_cannot_be_a_prior_signer`; `test_uat::test_uat_09*` |
| FR-038 | ✅ | `test_decision_trail::test_audit_entries_carry_the_comment_text_and_id`, `…status_code_page_lists_all_decisions_and_comments`, `…viewers_cannot_see_the_review_discussion`, `…withdrawing_keeps_the_discussion_in_the_audit_log`; | `test_ui_screens::test_comments_api_validates_and_is_role_restricted`; `test_governance_extras::test_comment_leaves_state_and_signoffs_untouched` |
| FR-039 | ✅ | `test_workflow_gaps::test_assigned_reviewer_only_may_sign_off`, `…reassigned_and_unassigned`, `…validation_and_authorization`, `…no_reassignment_after…` |
| FR-040 | ✅ | `test_releases::test_full_release_lifecycle`, `…non_admin_cannot_create_release` |
| FR-041 | ✅ | lifecycle test; `test_uat::test_uat_06…` |
| FR-042 | ✅ | `test_uat::test_uat_06…` (excluded candidate stays Approved) |
| FR-043 | ✅ | `test_releases::test_full_release_lifecycle` |
| FR-044 | ✅ | `test_releases::test_cannot_change_items_after_publish` |
| FR-045 | ✅ | `test_exports_and_diff::test_released_export_*`, `test_xlsx_export_has_same_rows_as_csv`, `test_json_export_is_flat_rows`; `test_releases::test_csv_export_of_a_release` |
| FR-046 | ✅ | `test_exports_and_diff::test_working_set_*` (4 tests) |
| FR-047 | ✅ | `test_releases::test_full_database_export_requires_administrator`; `test_uat::test_uat_10…` |
| FR-048 | ✅ | `test_releases::test_sandbox_revision_rejected_from_release_items` + `trg_prevent_sandbox_release` |
| FR-048a | ✅ | `test_import::test_non_admin_engineer_can_upload_import`, `…viewer_cannot…`, `…unsupported_file_extension…` |
| FR-048b | ✅ | `test_import::test_invalid_row_is_reported_and_creates_nothing`; `test_uat::test_uat_11…` |
| FR-048c | ✅ | `test_import::test_imported_row_becomes_import_type_draft_change_request` |
| FR-048d | ✅ | `test_governance_extras::test_import_preserves_legacy_reference_number` |
| FR-048e | ✅ | `test_lookup_admin::test_create_functional_subgroup_with_range` |
| FR-048f | ✅ | `test_lookup_admin::test_functional_subgroup_overlap_rejected` |
| FR-048g | ✅ | `test_lookup_admin::test_admin_can_create_new_functional_system_group_in_free_range`; `test_uat::test_uat_12…` |
| FR-048h | ✅ | `test_lookup_admin::test_new_functional_system_group_range_overlap_rejected` |
| FR-050 | ✅ | `test_deprecation::test_full_deprecation_cycle` |
| FR-051 | ✅ | `test_deprecation::test_archive_*` |
| FR-052 | ✅ | `test_schema_migration::test_only_sandbox_status_codes_can_be_deleted`; `test_status_codes::test_sandbox_delete_requires_admin_and_sandbox_flag` |
| FR-053 | ✅ | `test_status_codes::test_non_admin_cannot_create_sandbox`, `…admin_sandbox_gets_identifier_immediately` |
| FR-054 | ✅ | `test_status_codes::test_search_defaults_exclude_sandbox`; `test_exports_and_diff::test_released_export_contains_only…`, `test_working_set_is_labelled_and_excludes_sandbox` |
| FR-055 | ✅ | `test_status_codes::test_sandbox_delete_requires_admin_and_sandbox_flag` |
| FR-056 | ✅ | `test_audit_coverage::test_sandbox_delete_keeps_full_snapshot_and_creation_entry` |
| FR-060 | ✅ | `test_invariants::test_full_text_search_matches_identifier_title_and_description` |
| FR-061 | ✅ | `test_invariants::test_filters_sort_and_pagination` |
| FR-062 | ✅ | same (ascending and descending sort) |
| FR-063 | ✅ | same (page, page_size, cap at 200) |
| FR-064 | ✅ | `test_invariants::test_revision_history_visible_to_viewer_only_once_decided`; `test_exports_and_diff::test_diff_hidden_from_viewers…` |
| FR-070 | ✅ | `test_audit_coverage::test_each_lifecycle_action_is_audited_exactly_once`, `…import_lifecycle_is_audited`, `…subgroup_creation…`, `…user_and_auth_events…`; all 40 catalogue actions are emitted |
| FR-071 | ✅ | `test_audit_log.py`; `test_decision_trail::test_audit_log_can_be_filtered_by_action_and_actor` |
| FR-072 | ✅ | `test_audit_coverage::test_audit_log_entries_cannot_be_updated_or_deleted` (DB triggers) |
| FR-073 | ✅ | `test_audit_coverage::test_sandbox_delete_keeps_full_snapshot…` |
| FR-080 | ✅ | `test_openapi_conformance::test_every_documented_operation_is_implemented_and_vice_versa` |
| FR-081 | ✅ | `test_permission_grid.py` (5 roles × 46 API and 20 UI routes, plus anonymous access; expectations taken from the role column of `09-api-specification.md` §7) |
| FR-082 | ✅ | same pagination/filter/sort params as UI (`test_filters_sort_and_pagination`) |
| FR-083 | ✅ | `test_governance_extras::test_whole_lifecycle_works_with_all_outbound_network_blocked`; `test_no_cloud.py` |

## 3a. Functional requirements added in v4 (03-srs.md §1.10–§1.15)

| ID | Status | Evidence |
|---|---|---|
| FR-048i | ✅ | `test_import_toolkit::test_template_csv_and_xlsx_carry_the_exact_headers_and_lookup_codes`, `…the_downloaded_template_imports_cleanly_as_is` |
| FR-048j | ✅ | `test_import_toolkit::test_dry_run_reports_every_problem_and_creates_nothing`, `…dry_run_warns_about_a_possible_duplicate…`, `…missing_required_columns_are_named_up_front` |
| FR-048k | ✅ | `test_import_toolkit::test_update_mode_revises_the_open_draft_in_place`, `…skips_unchanged_rows_and_creates_missing_ones`, `…opens_a_new_revision_of_a_released_code`, `…update_mode_errors_are_specific`, `…update_of_someone_elses_draft…` |
| FR-048l | ✅ | `test_import_toolkit::test_reconciliation_counts_states_and_names_the_missing_numbers` |
| FR-048m | ✅ | `test_import_toolkit::test_error_report_has_row_column_value_and_a_fix_hint_as_csv_and_xlsx`, `…formula_like_values_in_the_error_report_are_neutralised` |
| FR-048n | ✅ | `test_import_toolkit::test_a_big_file_is_processed_in_the_background_with_progress`, `…files_above_the_threshold_go_to_the_background_automatically` |
| FR-048o | ✅ | `test_st_import::test_the_reader_takes_the_attributes_of_a_main_controller_program`, `test_st_import::test_a_zip_and_loose_files_are_read_alike_and_other_files_are_noted`, `test_st_import::test_a_file_without_programs_or_too_large_is_refused_cleanly`, `test_st_import::test_nothing_usable_is_a_clear_error` |
| FR-048p | ✅ | `test_st_import::test_the_preview_lists_every_program_and_creates_nothing`, `test_st_import::test_confirming_without_a_selection_takes_every_ready_program`, `test_st_import::test_the_controller_can_be_forced_for_a_file` |
| FR-048q | ✅ | `test_st_import::test_submitting_issues_exactly_the_reserved_number`, `test_st_import::test_an_administrator_cannot_override_a_reserved_identifier`, `test_st_import::test_allocation_skips_a_reserved_number_and_a_manual_override_cannot_take_it`, `test_st_import::test_the_database_refuses_a_second_reservation_of_a_number` |
| FR-048r | ✅ | `test_st_import::test_the_preview_lists_every_program_and_creates_nothing`, `test_st_import::test_the_controller_can_be_forced_for_a_file` |
| FR-048s | ✅ | `test_st_import::test_a_hub_program_keeps_its_legacy_number_and_gets_the_new_one_from_the_mapping`, `test_st_import::test_a_legacy_hub_number_missing_from_the_mapping_leaves_no_identifier`, `test_st_import::test_the_command_line_reads_the_hub_numbers_of_the_seed_workbook`, `test_st_import::test_the_new_number_of_a_hub_program_is_the_one_of_its_mapping_row` |
| FR-048t | ✅ | `test_st_import::test_confirm_creates_drafts_that_reserve_their_numbers_in_one_change_set`, `test_st_import::test_the_draft_carries_the_attributes_of_the_program` |
| FR-048u | ✅ | `test_st_import::test_the_mapping_lists_legacy_to_new_and_counts_codes_without_a_legacy_number`, `test_st_import::test_the_mapping_exports_as_csv_and_xlsx`, `test_st_import::test_the_mapping_is_not_for_viewers` |
| FR-048v | ✅ | `test_st_import::test_the_source_of_an_imported_code_can_be_read`, `test_st_import::test_confirm_creates_drafts_that_reserve_their_numbers_in_one_change_set`, `test_st_import::test_a_used_prg_idx_is_a_warning_and_is_not_stored_twice` |
| FR-048w | ✅ | `test_st_import::test_a_second_preview_shows_what_is_already_there_and_confirm_refuses_it`, `test_st_import::test_a_legacy_number_that_belongs_to_another_code_blocks_the_program`, `test_st_import::test_a_number_defined_twice_in_one_upload_blocks_the_second` |
| FR-048x | ✅ | `test_withdraw_and_reimport::test_a_changed_program_updates_the_open_draft_when_it_is_ticked`, `…a_changed_program_opens_a_new_revision_of_an_approved_code`, `…the_preview_screen_lists_the_choices_and_leaves_changed_programs_unticked`, `…a_withdrawn_code_that_has_its_identifier_keeps_it_and_can_be_restored` |
| FR-090 | ✅ | `test_content_integrity::test_stale_save_is_refused_with_the_current_values`, `…expected_updated_at_is_enforced_too`, `…save_without_a_version_still_works…`, `…ui_stale_edit_keeps_the_users_entries…` |
| FR-091 | ✅ | `test_content_integrity::test_unknown_escalation_number_warns_but_does_not_block`, `…reference_to_a_deprecated_code_warns`, `…related_codes_are_validated_and_checked` |
| FR-092 | ✅ | `test_content_integrity::test_where_used_lists_dependants_and_deprecation_needs_acknowledgement` |
| FR-093 | ✅ | `test_content_integrity::test_similar_title_in_the_subgroup_is_flagged_not_blocked`, `…similar_endpoint_supports_the_did_you_mean_hint`; `test_import_toolkit::test_similar_titles_are_reported_as_warnings` |
| FR-094 | ✅ | `test_content_integrity::test_platform_variant_copies_the_code_and_links_the_family`, `…variant_needs_a_decided_source_and_an_engineer` |
| FR-100 | ✅ | `test_publication::test_three_profiles_are_seeded_and_shape_the_columns`, `…administrator_manages_profiles_as_data`, `…export_profile_fields_match_the_export_row` |
| FR-101 | ✅ | `test_publication::test_pdf_cells_are_wrapped_not_truncated`, `…pdf_survives_characters_outside_latin_1`, `…pdf_column_widths_fit_the_page` |
| FR-102 | ✅ | `test_publication::test_audience_export_only_contains_codes_the_audience_may_see`, `…covert_visibility_is_data_an_administrator_can_flip`, `…customer_profile_applies_its_default_audience…` |
| FR-103 | ✅ | `test_publication::test_bundle_contains_the_file_and_a_manifest_that_matches`, `…signed_manifest_detects_edits_to_the_manifest_itself`, `…export_history_lists_hashes_per_release` |
| FR-104 | ✅ | `test_publication::test_verify_recognises_an_untouched_file_and_a_tampered_one`, `…verify_export_cli_works_without_the_database` |
| FR-105 | ✅ | `test_publication::test_release_notes_list_added_changed_and_deprecated`, `…unpublished_release_notes_are_an_administrator_preview` |
| FR-106 | ✅ | `test_publication::test_version_range_must_be_ordered_and_known`, `…release_targets_limit_the_candidates_and_freeze_at_publish` |
| FR-107 | ✅ | `test_publication::test_applicability_matrix_and_changes_between_versions` |
| FR-108 | ✅ | `test_publication::test_offline_bundle_is_one_self_contained_page_with_the_data`, `…offline_bundle_respects_audiences_and_needs_a_published_release` |
| FR-109 | ✅ | `test_content_integrity::test_planned_dates_are_administrator_set_audited_and_warn_at_publish` |
| FR-110 | ✅ | `test_publication::test_translation_workflow_with_light_review_and_language_exports`, `…translation_validation_worklist_and_carry_over`, `…draft_source_text_cannot_be_translated_yet` |
| FR-111 | ✅ | same (language exports use approved text; strict mode) |
| FR-120 | ✅ | `test_sla_and_notifications::test_business_days_skip_weekends`, `…levels_follow_the_thresholds`, `…queues_show_the_waiting_time`, `…thresholds_are_configurable_and_validated` |
| FR-121 | ✅ | `test_sla_and_notifications::test_reminders_go_to_whoever_holds_the_next_decision_once_a_day`, `…reminders_also_reach_a_covering_delegate_and_can_be_mailed`, `…mail_failure_never_breaks_the_reminder_job`, `…send_reminders_cli` |
| FR-122 | ✅ | `test_sla_and_notifications::test_stalled_view_and_reassignment` |
| FR-123 | ✅ | `test_sla_and_notifications::test_kpis_are_computed_from_stored_timestamps`, `…kpis_flag_an_incomplete_audit_trail…`; `test_integrations_and_reports::test_kpis_have_the_documented_shape` |
| FR-124 | ✅ | `test_review_aids::test_change_set_groups_requests_and_bulk_decisions_stay_individual`, `…bulk_decision_skips_what_the_actor_may_not_decide`, `…bulk_decision_needs_the_password_once…`, `…change_set_rules` |
| FR-125 | ✅ | `test_step_up_and_delegation::test_delegate_can_sign_off_as_the_absent_reviewer_and_audit_shows_both`, `…delegation_is_limited_to_its_period_and_can_be_revoked`, `…delegation_validation_and_who_may_create_it`, `…delegating_does_not_grant_other_privileges`, `…deactivated_delegator_ends_the_delegation` |
| FR-126 | ✅ | `test_step_up_and_delegation::test_reviewer_signoff_without_password_is_refused`, `…wrong_password_is_refused_and_audited`, `…admin_signoff_chief_decision_publish_and_full_export_all_need_the_password`, `…ui_decision_forms_carry_a_password_field` |
| FR-127 | ✅ | `test_review_aids::test_reviewer_comments_on_a_field_and_the_author_sees_and_resolves_it`, `…field_comment_rules`, `…only_the_commenter_author_or_admin_can_resolve` |
| FR-128 | ✅ | `test_review_aids::test_checklist_must_be_confirmed_to_approve_and_is_recorded`, `…checklist_is_administrator_managed…`, `…rejection_does_not_need_the_checklist` |
| FR-129 | ✅ | `test_review_aids::test_least_loaded_reviewer_is_suggested_and_assigned`, `…out_of_office_reviewers_are_not_auto_assigned`, `…auto_assignment_on_submit_is_a_setting` |
| FR-130 | ✅ | `test_review_aids::test_author_attaches_evidence_and_reviewers_download_it`, `…attachment_type_size_and_content_checks`, `…attachment_permissions_and_removal_rules`, `…removing_a_draft_attachment_deletes_the_file…` |
| FR-131 | ✅ | `test_content_integrity::test_troubleshooting_fields_round_trip_and_reach_the_export`, `…remedy_text_length_is_validated` |
| FR-140 | ✅ | `test_integrations_and_reports::test_health_report_covers_capacity_missing_data_and_inconsistencies`, `…health_report_finds_an_info_code_with_an_alarm`, `…reports_are_limited_to_the_right_roles` |
| FR-141 | ✅ | `test_integrations_and_reports::test_health_report_flags_a_nearly_full_band`, `…the_capacity_table_colours_main_blue_and_hub_light_blue`; `test_content_integrity::test_next_available_reports_how_many_numbers_are_left` |
| FR-142 | ✅ | `test_integrations_and_reports::test_saved_searches_round_trip_through_the_url`, `…saving_under_an_existing_name…`, `…saved_searches_are_private_to_their_owner`, `…saved_search_ui_save_and_delete` |
| FR-143 | ✅ | `test_integrations_and_reports::test_occurrence_report_names_codes_that_never_fire_and_those_that_fire_most`, `…occurrence_import_validation_and_permissions` |
| FR-144 | ✅ | `test_integrations_and_reports::test_a_token_is_shown_once_and_stored_only_as_a_hash`, `…a_token_reads_released_data_only_and_never_writes`, `…a_token_only_works_for_its_scope`, `…revoked_expired_unknown_and_orphaned_tokens_are_refused` |
| FR-145 | ✅ | `test_integrations_and_reports::test_the_feed_lists_releases_in_order_with_a_cursor_and_an_etag`, `…the_feed_needs_authentication`, `…sandbox_activity_never_appears_in_the_feed` |
| FR-146 | ✅ | `test_integrations_and_reports::test_a_publish_calls_the_webhook_with_a_verifiable_signature`, `…failing_webhook_is_recorded_and_never_blocks_the_publish`, `…redirects_are_not_followed`, `…webhook_targets_must_be_internal…` |
| FR-147 | ✅ | `test_integrations_and_reports::test_a_hub_code_is_carried_over_as_a_main_controller_draft`, `…the_whole_consolidation_loop_ends_with_a_deprecation_request`, `…bulk_deprecation_is_for_administrators_and_hub_groups` |
| FR-148 | ✅ | `test_search_and_help::test_prefix_and_multi_word_search`, `…a_hit_in_the_title_outranks_a_hit_in_the_description`, `…typos_still_find_the_code`, `…without_the_index_search_falls_back_to_substrings` |
| FR-150 | ✅ | `test_audit_chain_and_ops::test_a_backup_is_written_verified_and_recorded`, `…only_the_newest_generations_are_kept`, `…a_corrupt_backup_fails_verification`, `…a_restored_backup_runs_the_application`, `…cli_backup_verify_and_audit_commands` |
| FR-151 | ✅ | `test_audit_chain_and_ops::test_an_edited_row_is_found_and_named`, `…a_removed_row_breaks_the_link`, `…truncating_the_tail_is_caught_by_the_anchor`, `…archive_exports_old_rows_with_a_hash_and_deletes_nothing`; `test_schema_upgrade::test_old_audit_rows_are_chained_and_the_chain_verifies` |
| FR-152 | ✅ | `test_audit_chain_and_ops::test_ready_reports_ok_and_degraded_by_backup_state`, `…ready_is_503_when_the_chain_is_broken_or_the_schema_outdated`, `…ready_needs_no_login…` |
| FR-153 | ✅ | `test_audit_chain_and_ops::test_metrics_are_refused_outside_the_allowed_networks`, `…metrics_count_requests_and_hold_no_business_data`, `…requests_are_logged_to_the_configured_file` |
| FR-154 | ✅ | `test_search_and_help::test_every_lifecycle_state_role_and_cr_state_has_help`, `…the_help_page_shows_the_quick_start_of_the_signed_in_role`, `…state_badges_carry_their_glossary_text_as_a_tooltip`, `…the_change_request_screen_says_what_happens_next` |
| FR-155 | ✅ | `test_i18n::test_every_template_string_has_a_german_entry`, `…the_language_choice_is_remembered_for_the_user`, `…main_pages_render_in_each_language…`; `test_accessibility::test_every_page_is_structurally_accessible` |
| FR-156 | ✅ | `test_roles_and_languages::test_the_stcd_owner_moves_users_between_viewer_engineer_and_reviewer`, `…the_stcd_owner_cannot_reach_the_other_roles`, `…the_stcd_owner_changes_nothing_but_the_role`, `…the_user_page_colours_every_role_and_red_is_the_administrator`, `…the_stcd_owner_sees_the_list_without_the_administrator_forms`; `test_permission_grid::test_api_permission_grid`, `…test_ui_permission_grid` |
| FR-157 | ✅ | `test_roles_and_languages::test_the_language_names_have_the_country_letters_left_and_the_flag_right`, `…the_menu_shows_letters_left_and_a_drawn_flag_right_for_every_language`, `…arabic_is_right_to_left_but_identifiers_codes_and_numbers_stay_as_they_are`, `…each_added_language_translates_the_login_page_and_falls_back_to_english`, `…the_choice_of_an_added_language_is_remembered_for_the_user`, `…a_partly_translated_page_still_shows_every_string`, `…the_catalogues_agree_and_only_translate_real_strings`; `test_schema_migration::test_nineteen_languages_seeded_with_country_letters_left_and_the_flag_right`; `test_schema_upgrade::test_the_table_rebuilds_leave_every_foreign_key_intact` |
| FR-158 | ✅ | `test_user_administration::test_an_account_that_was_never_used_can_be_deleted_and_the_deletion_is_audited`, `…an_account_with_history_is_erased_and_the_audit_log_is_untouched`, `…a_deactivated_account_can_be_activated_again`, `…the_user_list_offers_view_edit_deactivate_and_delete_to_an_administrator`, `…the_detail_page_shows_history_and_the_buttons_follow_it`, `…the_buttons_deactivate_activate_and_delete_through_the_screens`, `…nobody_deletes_their_own_account` |
| FR-159 | ✅ | `test_withdraw_and_reimport::test_several_change_requests_are_withdrawn_in_one_go_and_each_is_reported`, `…a_change_request_of_somebody_else_is_refused_and_the_others_go_on`, `…bulk_withdraw_needs_a_list_and_a_role_that_can_withdraw`, `…the_list_has_tick_boxes_and_a_withdraw_selected_button` |
| FR-160 | ✅ | `test_withdraw_and_reimport::test_a_withdrawn_import_draft_gives_its_number_and_legacy_number_back`, `…a_withdrawn_code_that_has_its_identifier_keeps_it_and_can_be_restored` |
| FR-161 | ✅ | `test_translations_doc::test_the_document_is_exactly_what_the_generator_produces_from_the_code`, `…every_language_has_its_section_and_its_coverage_row`, `…string_ids_are_stable_and_never_collide`, `…the_fingerprint_changes_when_one_translation_changes`, `…the_review_sheet_of_every_language_is_complete`, `…right_to_left_languages_get_a_right_to_left_translation_column`, `…the_command_line_writes_one_sheet_per_language_and_refuses_unknown_ones`, `…the_concept_names_the_layers_the_checks_and_the_open_items` |
| FR-162 | ✅ | `test_email_and_windows_signin::test_an_address_is_stored_trimmed_and_lower_case_and_must_be_valid_and_new`, `…the_address_of_a_user_cannot_be_changed`, `…the_database_refuses_a_changed_address_too`, `…the_screens_show_the_address_as_fixed` |
| FR-163 | ✅ | `test_email_and_windows_signin::test_the_gateways_identity_signs_the_matching_account_in_and_is_audited`, `…no_identity_an_unknown_one_and_a_deactivated_account_are_all_refused`, `…a_domain_name_is_matched_through_the_mail_domain_or_the_user_name`, `…with_windows_only_passwords_are_refused_and_the_login_page_says_so`, `…with_both_modes_the_login_page_offers_the_button_and_the_form`, `…the_simulation_page_stands_in_for_the_gateway_and_signs_in_by_address`, `…the_simulation_refuses_an_unknown_identity_and_is_off_by_default`, `…the_development_defaults_are_the_simulation_next_to_the_password`, `…the_shipped_example_configuration_documents_the_settings` |
| FR-164 | ✅ | `test_translation_review::test_the_overview_shows_a_reviewer_only_their_languages_and_a_manager_all`, `…only_an_administrator_or_an_stcd_owner_assigns_reviewers_and_it_is_audited`, `…an_unassigned_user_cannot_open_a_review_and_an_unknown_language_is_404`, `…a_reviewer_answers_strings_and_is_told_what_is_wrong`, `…a_review_is_completed_only_when_every_string_has_a_verdict_and_is_recorded`, `…an_accepted_proposal_is_shown_at_once_and_can_be_taken_back`, `…nobody_decides_on_their_own_proposal_and_a_decision_is_final`, `…a_proposal_must_keep_the_placeholders_and_an_unclear_string_is_only_noted`, `…a_missing_translation_can_be_proposed_and_accepted`, `…a_completed_review_shows_as_changed_after_a_later_acceptance`, `…the_sheet_can_be_downloaded_filled_in_offline_and_uploaded`, `…a_sheet_that_is_not_one_is_refused_clearly`, `…right_to_left_languages_are_shown_right_to_left_in_the_review` |
| FR-165 | ✅ | `test_pdf_scripts::test_a_script_gets_its_own_font`, `…latin_text_needs_no_script_font_and_arabic_is_told_from_urdu`, `…every_script_builds_a_pdf_with_its_font`, `…the_title_page_and_notice_may_carry_any_script`, `…shaping_is_switched_on_per_cell_only_where_a_script_needs_it`, `…every_character_of_every_translation_is_drawn_by_a_bundled_font`, `…the_fonts_and_their_licence_are_bundled_and_shaping_is_available`, `…a_large_export_stays_fast_for_latin_text`; `test_publication::test_pdf_survives_characters_no_font_has` |
| FR-166 | ✅ | `test_terminology::test_the_vocabulary_ships_with_every_term_in_every_language_as_a_draft`, `…the_shipped_terms_agree_with_the_interface_catalogue_where_both_have_the_word`, `…terms_that_are_never_translated_have_no_translation`, `…everybody_reads_but_only_the_technical_roles_propose`, `…an_interface_reviewer_has_no_say_in_the_terminology`, `…a_proposal_is_a_draft_until_another_person_approves_it`, `…a_shipped_draft_can_be_approved_by_anybody_who_may_approve_and_all_at_once`, `…send_back_needs_a_note_and_reopens_an_approved_translation`, `…validation_of_a_translation`, `…only_the_managers_add_and_change_terms_and_a_new_english_reopens_approvals`, `…the_check_finds_interface_strings_that_do_not_use_the_term`, `…the_vocabulary_is_exported_per_language_and_for_all`, `…a_formula_in_a_cell_is_neutralised_in_the_csv` |
| FR-167 | ✅ | `test_i18n::test_every_language_translates_the_whole_interface_inventory`, `…every_template_string_has_a_german_entry`, `…placeholders_survive_translation`; `test_translations_doc::test_every_language_has_its_section_and_its_coverage_row` |
| FR-168 | ✅ | `test_generated_fields::test_a_main_program_import_keeps_every_field_of_the_program`, `…the_two_zero_load_attributes_are_not_mixed_up`, `…a_hub_program_import_keeps_its_hub_fields_and_nothing_of_the_main_ones`, `…a_field_of_the_other_controller_is_refused_and_the_rest_is_stored`, `…values_out_of_range_are_refused`, `…a_new_revision_carries_over_what_the_caller_does_not_send_and_the_diff_shows_changes`, `…the_form_stores_the_fields_and_the_pages_show_them`, `…a_rejected_form_keeps_what_was_typed`, `…the_levels_and_programs_are_internal_and_never_leave_in_an_audience_export`, `…withdrawing_and_deleting_a_code_removes_its_levels` |
| FR-169 | ✅ | `test_menu::test_a_viewer_sees_the_catalogue_and_nothing_to_work_with`, `…each_role_sees_the_links_of_its_work_and_no_other`, `…no_link_appears_twice_and_the_groups_are_the_planned_ones`, `…only_the_link_of_the_current_page_is_marked`, `…what_waits_for_the_user_is_counted_in_the_menu`, `…groups_can_be_closed_and_a_narrow_window_has_a_menu_button`, `…the_menu_is_translated_and_a_group_title_too` |
| FR-170 | ✅ | `test_menu::test_the_working_roles_see_every_language_and_the_unreviewed_ones_are_marked_beta`, `…a_review_removes_the_mark_and_a_changed_string_brings_it_back`, `…the_marker_can_be_switched_off_in_the_settings` |
| FR-171 | ✅ | `test_export_language::test_a_pdf_in_french_prints_its_own_words_in_french`, `…english_and_no_language_leave_the_text_as_it_is`, `…every_word_around_an_export_exists_in_every_language`, `…a_placeholder_survives_in_every_language` |
| FR-172 | ✅ | `test_menu::test_a_viewer_sees_only_the_reviewed_languages_and_nothing_marked`, `…a_viewer_cannot_choose_or_keep_a_language_nobody_has_reviewed`, `…a_viewer_who_reviews_a_language_sees_that_one`, `…the_login_page_offers_only_the_reviewed_languages`, `…the_working_roles_see_every_language_and_the_unreviewed_ones_are_marked_beta` |
| FR-173 | ✅ | `test_baseline_and_packages::test_the_baseline_of_a_release_holds_every_code_valid_at_that_release`, `…a_release_can_still_be_exported_as_only_its_own_changes`, `…the_baseline_narrows_to_a_platform`, `…the_baseline_narrows_to_a_controller`, `…the_summary_counts_the_baseline_by_controller_and_platform`, `…an_unpublished_release_previews_what_its_manual_will_contain`, `…the_title_page_names_the_scope`, `…the_readiness_check_shows_what_is_still_missing` |
| FR-174 | ✅ | `test_baseline_and_packages::test_a_package_holds_every_language_for_every_access_level`, `…the_manifest_vouches_for_every_file_and_reports_the_coverage`, `…a_package_can_be_narrowed_to_a_platform_and_a_controller`, `…everybody_may_download_what_is_released_and_only_owner_and_admin_what_is_not`, `…a_package_needs_a_published_release_and_valid_choices`, `…the_release_page_offers_the_baseline_and_the_package`, `…the_package_is_audited` |
| FR-175 | ✅ | `test_baseline_and_packages::test_everybody_may_download_what_is_released_and_only_owner_and_admin_what_is_not`, `test_exports_and_diff::test_working_set_not_available_to_viewers_or_anonymous`, `test_permission_grid` |
| FR-176 | ✅ | `test_translation_approval::test_a_reviewed_language_has_nothing_pending_until_a_string_changes`, `…a_viewer_reads_a_changed_string_in_english_until_it_is_approved`, `…a_language_never_reviewed_stays_hidden_from_a_viewer`, `…a_follow_up_review_covers_only_what_is_new_or_changed`, `…an_accepted_proposal_is_approved_and_an_undecided_one_is_not`, `test_translation_review::test_a_proposal_awaits_approval_until_it_is_decided` |
| FR-177 | ✅ | `test_translation_approval::test_the_colour_intervals_run_from_red_to_green`, `…the_overview_shows_the_confidence_of_every_language_in_colour`, `…the_record_holds_a_confidence_for_every_language_with_its_findings`, `…every_change_of_the_text_or_the_nomenclature_has_been_through_the_check`, `…a_changed_string_must_get_a_verdict_before_the_record_is_current`, `…a_change_of_the_nomenclature_needs_the_flag_as_well`, `…a_delta_read_one_by_one_can_lower_or_keep_the_confidence` |
| FR-178 | ✅ | `test_translation_impact::test_a_new_term_tells_the_stcd_owner_which_languages_need_attention`, `…the_reviewer_of_an_affected_language_is_told_too`, `…a_term_that_stays_in_english_touches_no_language`, `…a_changed_term_and_an_approved_translation_are_reported_again`, `…a_failing_notice_never_undoes_the_change`, `…the_notice_appears_on_the_notices_page_of_the_stcd_owner`, `…nothing_is_reported_while_the_confidence_check_is_current`, `…changed_shipped_text_is_reported_once_per_change`, `…a_changed_nomenclature_is_named_in_the_notice`, `…the_command_for_the_deployment_reports_and_notifies`, `…the_start_of_the_server_and_the_installers_run_the_check`, `test_translation_approval::test_every_change_of_the_text_or_the_nomenclature_has_been_through_the_check` |
| FR-179 | ✅ | `test_connections::test_a_negated_active_flag_is_a_cause_and_a_plain_one_a_precondition`, `…the_real_programs_name_their_cause_and_their_repeat_code`, `…one_code_shows_what_it_depends_on_and_what_depends_on_it`, `…the_hierarchy_puts_the_cause_on_top_with_what_it_suppresses_below`, `…escalation_targets_say_which_are_outside_the_catalogue`, `…what_looks_wrong_is_listed`, `…the_hub_and_main_controller_can_be_looked_at_separately`, `…the_code_page_and_the_overview_show_the_connections`, `…a_viewer_does_not_see_the_connections`, `…the_api_returns_the_connections_of_a_code_and_of_the_catalogue`, `…the_menu_offers_the_connections_to_the_working_roles_only`, `…an_imported_program_brings_its_cause_and_its_repeat_code` |
| FR-180 | ✅ | `test_bulk_workflow::test_the_size_of_the_sample_follows_the_settings`, `…the_sample_is_spread_over_the_subgroups_and_reproducible`, `…the_readiness_names_what_stops_each_draft`, `…bulk_edit_sets_the_same_value_on_every_draft_with_its_own_audit_entry`, `…bulk_edit_refuses_unknown_fields_and_other_peoples_drafts`, `…a_bulk_domain_signoff_needs_a_sample_and_every_code_gets_its_own_signoff`, `…a_domain_signoff_is_only_for_a_holder_of_the_domain`, `…a_small_batch_needs_no_sample`, `…a_defect_in_the_sample_blocks_the_decision_until_it_is_sent_back`, `…a_sample_cannot_be_borrowed_reused_or_kept_after_the_batch_changed`, `…a_defect_needs_a_note_and_a_verdict_must_be_ok_or_defect`, `…bulk_submit_sends_the_drafts_that_are_ready_and_reports_the_rest`, `…the_dossier_puts_the_codes_the_samples_and_the_audit_in_one_workbook`, `…viewers_see_nothing_of_the_bulk_workbench`, `…the_workbench_shows_the_batch_the_readiness_and_the_rule`, `…a_whole_domain_signoff_can_be_done_in_the_workbench`, `…a_decision_in_the_workbench_names_its_sample`, `…the_bulk_screens_are_translated`, `test_select_all::test_every_list_with_a_checkbox_per_row_can_be_selected_as_a_whole` |
| FR-181 | ✅ | superseded by FR-192: `test_st_category_and_draft_delete::test_a_category_chosen_in_the_request_changes_nothing`, `…the_pages_have_no_category_controls_any_more` |
| FR-182 | ✅ | `test_st_category_and_draft_delete::test_the_list_offers_tick_boxes_for_the_own_drafts_and_deletes_the_ticked`, `…all_own_drafts_of_a_filter_are_deleted_on_every_page`, `…somebody_elses_drafts_cannot_be_ticked_or_deleted` |
| FR-183 | ✅ | `test_dark_mode::test_the_dark_palette_meets_aa_on_its_backgrounds`, `…every_badge_and_sla_pill_meets_aa_in_the_dark_theme`, `…the_dark_theme_gives_every_light_tint_a_dark_value`, `…colours_are_only_written_out_where_the_dark_theme_cannot_matter`, `…the_dark_theme_is_for_the_screen_only`, `…theme_js_is_a_plain_file_that_follows_the_system_and_remembers_the_choice`, `…the_login_page_and_every_signed_in_page_offer_the_theme_choice`, `…the_theme_choice_is_translated` |
| FR-184 | ✅ | `test_version::test_the_version_is_a_release_number_and_pyproject_agrees`, `…the_health_endpoints_name_the_version`, `…the_login_page_and_the_menu_show_the_version`, `…the_api_contract_documents_the_version_in_both_health_answers` |
| FR-185 | ✅ | `test_docs_pdf::test_the_reader_finds_every_kind_of_block`, `…inline_markup_is_removed_and_kept_as_styles`, `…symbols_a_pdf_font_cannot_draw_become_words`, `…every_character_of_the_documents_can_be_drawn`, `…a_document_is_built_with_the_version_in_its_name`, `…the_full_documentation_has_a_contents_list_and_the_artefacts`, `…the_four_documents_have_their_file_names`, `…the_user_manual_is_built_from_the_real_document`, `…an_unknown_document_is_refused` |
| FR-186 | ✅ | `test_showcase::test_a_text_that_does_not_fit_stops_the_build`, `…both_decks_are_built_from_the_screenshots_and_every_picture_is_described`, `…the_decks_are_written_as_powerpoint_files`, `…the_demo_has_its_data_and_the_application_has_no_demo_routes`, `…the_browser_is_found_or_named` |
| FR-187 | ✅ | `test_branding::test_the_owner_the_long_name_and_the_logo_are_written_once`, `…the_guide_names_the_same_owner`, `…the_logo_files_exist_and_are_drawn`, `…the_menu_bar_and_the_login_page_show_the_logo`, `…every_title_page_carries_the_identity` |
| FR-188 | ✅ | `test_handover::test_a_clean_tree_passes_the_audit`, `…every_kind_of_finding_stops_the_handover`, `…the_export_is_one_commit_by_the_named_author_with_the_tag`, `…a_tag_that_does_not_exist_and_a_push_without_confirmation_are_refused`, `…the_repository_carries_its_team_files` |
| FR-189 | ✅ | `test_st_no_assumptions::test_a_delay_that_is_a_variable_stays_the_name_of_the_variable`, `…a_delay_the_program_does_not_have_says_so`, `…a_program_that_gives_everything_lists_only_what_no_program_carries`, `…the_preview_warns_with_the_name_of_the_parameter`, `…a_program_the_mapping_does_not_know_is_blocked_and_never_imported`, `…a_delay_may_be_the_name_of_a_parameter_but_not_a_malformed_time` |
| FR-190 | ✅ | `test_st_no_assumptions::test_the_named_access_levels_come_from_the_mapping`, `…a_level_the_mapping_leaves_empty_stays_empty_and_is_listed`, `…a_level_whose_numbers_differ_from_the_program_is_named_and_warned_about`, `…a_level_that_is_no_longer_active_is_not_guessed`
| FR-191 | ✅ | `test_mapping::test_the_seed_workbook_loads_into_an_empty_table_once`, `…the_seed_workbook_is_consistent`, `…a_bad_seed_workbook_is_refused_as_a_whole` |
| FR-192 | ✅ | `test_st_mapping_rules::test_cause_and_directive_become_the_remedy_text`, `…the_mapping_gives_the_value_of_a_delay_the_program_sets_with_a_parameter`, `…a_time_in_the_program_wins_over_the_mapping`, `…a_rejected_row_is_as_good_as_none`, `test_st_category_and_draft_delete::test_the_type_of_a_program_is_the_type_of_its_mapping_row`, `…a_row_without_a_type_blocks_the_program`, `test_mapping::test_a_number_a_code_of_the_catalogue_carries_cannot_change` |
| FR-193 | ✅ | `test_st_mapping_rules::test_the_legacy_number_of_the_header_must_be_the_one_of_the_row`, `…a_title_that_does_not_say_what_the_name_says_is_flagged`, `…a_hub_row_for_a_main_program_is_not_taken`, `…the_glossary_is_a_check_not_a_translation` |
| FR-194 | ✅ | `test_mapping::test_a_new_row_takes_effect_only_after_all_three_approvals`, `…one_rejection_closes_the_request_and_needs_a_reason`, `…only_the_three_roles_decide_and_each_only_once`, `…a_decision_asks_for_the_password_again`, `…the_requester_can_withdraw_and_nobody_else`, `…a_row_changed_in_between_makes_the_older_request_unusable` |
| FR-195 | ✅ | `test_mapping::test_a_row_that_does_not_pass_the_checks_makes_no_request`, `…numbers_stay_unique`, `…a_change_confirm_and_reject_work_on_stored_rows` |
| FR-196 | ✅ | `test_mapping::test_the_pages_show_the_mapping_the_requests_and_the_three_slots`, `…the_pages_make_requests_and_decide_with_the_form_posts`, `…the_menu_counts_the_requests_that_wait_for_a_decision`, `…a_viewer_neither_reads_nor_proposes`, `…show_all_puts_every_row_on_one_page_so_that_select_all_covers_them`, `…a_database_without_the_mapping_tables_says_what_to_run`, `…the_sign_off_of_a_domain_is_below_the_changes_and_the_status_above` |
| FR-197 | ✅ | `test_mapping::test_the_export_is_the_layout_the_upload_reads`, `…a_workbook_makes_one_request_with_the_new_and_the_different_rows`, `…a_workbook_with_a_wrong_row_names_it_and_requests_nothing`, `…the_export_never_starts_a_formula` |
| FR-198 | ✅ | `test_mapping::test_a_new_row_takes_effect_only_after_all_three_approvals` (audit), `test_docs_consistency::test_the_audit_catalogue_lists_every_code_the_application_can_write`, `test_openapi_conformance` |

## 4. Business rules, security, non-functional

| ID | Status | Evidence |
|---|---|---|
| BR-001 | ✅ | `test_invariants::test_identifier_never_changes_after_allocation`, `…new_revision_of_a_released_code_keeps…` |
| BR-002 | ✅ | `test_invariants::test_exactly_one_current_revision_per_code` |
| BR-003 | ✅ | `test_invariants::test_only_one_open_revision_per_code` (service 409 **and** DB index) |
| BR-004 | ✅ | `unit/test_lifecycle.py` (the 9 defined edges accepted, all 40 other state pairs rejected, ORM guard) |
| BR-005 | ✅ | SoD tests; `test_uat::test_uat_09*` |
| BR-006 | ✅ | `test_deprecation` |
| BR-007 | ✅ | `test_releases::test_cannot_change_items_after_publish` |
| BR-008 | ✅ | `test_exports_and_diff::test_release_can_be_deleted_before_publish_only`; `test_releases::test_non_admin_cannot_create_release` |
| BR-009 | ✅ | `test_status_codes::test_viewer_cannot_see_draft_status_codes`; `test_invariants::test_released_code_stays_visible_to_viewers_while_a_new_revision_is_open`; `test_permission_grid` (Viewers gated from change-request endpoints, API and UI); history/diff/working-set tests |
| BR-010 | ✅ | sandbox release + delete tests |
| BR-011 | ✅ | domain sign-off tests |
| BR-012 | ✅ | `test_workflow_gaps` override tests |
| BR-013 | ✅ | `test_status_codes::test_create_rejects_missing_functional_subgroup` |
| BR-014 | ✅ | `test_lookup_admin::test_functional_subgroup_overlap_rejected` |
| BR-015 | ✅ | import tests; `test_uat::test_uat_11…` |
| SEC-001 | ✅ | `unit/test_password.py` (Argon2id) |
| SEC-002 | ✅ | `test_injection_and_session::test_session_cookie_attributes`; `test_production_config::test_production_refuses_a_weak_secret_key`, `…starts_with_a_strong_secret_key` |
| SEC-003 | ✅ | idle and 12 h absolute expiry tests |
| SEC-004 | ✅ | lockout tests |
| SEC-005 | ✅ | `test_auth_provider_seam_is_substitutable` |
| SEC-006 | ✅ | own login/credential store (`test_auth.py`); visual-only integration |
| SEC-010 | ✅ | `test_governance_extras::test_services_enforce_roles_independently_of_route_decorators` (16 service entry points) |
| SEC-011 | ✅ | SoD tests at all three decision points |
| SEC-012 | ✅ | `test_ui_screens::test_default_role_for_new_user_is_viewer` |
| SEC-013 | ✅ | override tests; `access_confirmed` flag in the API |
| SEC-014 | ✅ | sandbox delete tests + trigger |
| SEC-015 | ✅ | `test_uat::test_uat_10…`; permission grid |
| SEC-020 | ✅ | `test_injection_and_session::test_server_side_validation_ignores_client_side_constraints` |
| SEC-021 | ✅ | `test_injection_and_session::test_sql_injection_probes_have_no_effect`, `…audit_log_filters_resist_injection`; `bandit` clean |
| SEC-022 | ✅ | `test_injection_and_session::test_user_supplied_text_is_escaped_everywhere_it_renders` |
| SEC-023 | ✅ | `test_exports_and_diff::test_exports_neutralise_formula_injection` (CSV and XLSX) |
| SEC-024 | ✅ | `test_import::test_unsupported_file_extension_rejected`; 20 MB cap |
| SEC-025 | ✅ | `test_security_headers.py` |
| CSRF | ✅ | `test_csrf.py` |
| Password policy (`11` §4) | ✅ | `test_logging_and_passwords::test_policy_length_and_blocklist`, `…last_five_passwords_cannot_be_reused`, `…administrator_reset_also_honours_history`, `…only_hashes_are_stored_in_the_history`; `unit/test_password.py` |
| Logging (`11` §11) | ✅ | `test_logging_and_passwords::test_requests_are_logged_as_json_without_credentials`, `…authenticated_requests_record_the_user_id`, `…unhandled_errors_are_logged_with_the_request_id` |
| NFR-001 | ✅ | `performance/`: search p95 ≈ 110 ms and read p95 ≈ 4 ms at 20,000 revisions; export of 5,000 rows: CSV ≈ 0.7 s, JSON ≈ 0.5 s, XLSX ≈ 1.7 s, PDF ≈ 3.1 s (current figures: 24-test-report.md §4); `test_export_issues_a_constant_number_of_queries` guards the eager loading that made exports ~4× faster |
| NFR-002 | ➖ | Operational availability target (deployment) |
| NFR-003 / 003a | ✅ | headers, CSRF, injection, hashing, `test_no_cloud.py`, `pip-audit` |
| NFR-004 | ✅ | `performance::test_fifty_concurrent_users_are_served_without_errors` (p95 ≈ 72 ms), `…reads_are_not_blocked_by_an_open_write_transaction`, `…concurrent_identifier_allocation_in_one_group` |
| NFR-005 | ✅ | every service module ≥ 82% line coverage; ruff, mypy, bandit clean |
| NFR-006 | ✅ | `test_each_lifecycle_action_is_audited_exactly_once` |
| NFR-007 | 🧑 | Responsive server-rendered UI, all screens render for every role (`test_ui_screens`); trained-user walkthrough is part of UAT |
| NFR-007a | ✅ | `test_ui_screens::test_failed_form_submission_keeps_every_entered_value`; `test_uat::test_uat_13…` |
| NFR-007b | ✅ | `test_ui_screens::test_lookup_selects_carry_inline_help_hooks`, `…lookup_description_is_editable_and_flows_to_form_and_api` (mechanism; wording is §6) |
| NFR-008 | ✅ | egress-blocked lifecycle test |
| NFR-009 | ✅ | `test_multiprocess::test_the_username_limit_is_shared_by_both_processes`, `…the_ip_limit_is_shared…`, `…the_limit_survives_a_restart`, `…concurrent_writers_in_two_processes_all_succeed`; `unit/test_rate_limit.py` |
| NFR-010 | ✅ | `test_accessibility::test_text_tokens_meet_aa_on_their_backgrounds`, `…every_state_badge_meets_aa`, `…every_page_is_structurally_accessible`, `…the_stylesheet_honours_user_preferences` (a manual screen-reader pass is §6) |
| NFR-011 | ✅ | `test_audit_chain_and_ops::test_requests_are_logged_to_the_configured_file`, `…metrics_count_requests…`, `…ready_reports_ok_and_degraded_by_backup_state` |
| NFR-012 | ✅ | `test_audit_chain_and_ops::test_a_backup_is_written_verified_and_recorded`, `…a_restored_backup_runs_the_application` (the quarterly restore drill on real hardware is §6) |
| NFR-013 | ✅ | `test_deploy_artifacts::test_linux_installer_parses_and_its_dry_run_changes_nothing`, `…windows_installer_dry_run_lists_every_step…`, `…units_parse_and_have_the_required_sections`, `…the_production_entry_point_serves_and_reports_its_state`, `…ci_files_parse_and_run_the_ci_script` (a real install is §6) |
| NFR-014 | ✅ | `test_deploy_artifacts::test_the_postgres_ratchet_holds`, `…the_ratchet_notices_new_sqlite_specific_code`, `…non_sqlite_connections_are_left_alone` (the port itself has not been done) |
| BR-015 | ✅ | `test_import::test_imported_row_becomes_import_type_draft_change_request`; update mode and Hub carry-over also create Drafts only: `test_import_toolkit::test_update_mode_opens_a_new_revision_of_a_released_code`, `test_integrations_and_reports::test_a_hub_code_is_carried_over_as_a_main_controller_draft` |
| BR-016 | ✅ | `test_publication::test_audience_export_only_contains_codes_the_audience_may_see`, `…covert_visibility_is_data_an_administrator_can_flip`; `test_schema_upgrade::test_covert_is_not_visible_and_the_other_audiences_still_are` |
| BR-017 | ✅ | `test_step_up_and_delegation::test_delegation_does_not_lift_segregation_of_duties`, `…one_person_cannot_give_both_review_signoffs_through_a_delegation`, `…delegating_does_not_grant_other_privileges` |
| BR-018 | ✅ | `test_publication::test_translation_workflow_with_light_review_and_language_exports` (approver differs from translator) |
| BR-019 | ✅ | `test_content_integrity::test_stale_save_is_refused_with_the_current_values` |
| BR-020 | ✅ | `test_audit_chain_and_ops::test_archive_exports_old_rows_with_a_hash_and_deletes_nothing`, `…the_append_only_triggers_still_stop_edits_inside_the_application` |
| BR-021 | ✅ | `test_publication::test_release_targets_limit_the_candidates_and_freeze_at_publish` |
| BR-022 | ✅ | `test_step_up_and_delegation::test_admin_signoff_chief_decision_publish_and_full_export_all_need_the_password`, `…step_up_can_be_switched_off_by_configuration` |
| BR-023 | ✅ | `test_st_import::test_submitting_issues_exactly_the_reserved_number`, `test_st_import::test_allocation_skips_a_reserved_number_and_a_manual_override_cannot_take_it`, `test_st_import::test_the_database_refuses_a_second_reservation_of_a_number` |
| BR-024 | ✅ | `test_roles_and_languages::test_who_may_change_which_role_to_which`, `…only_an_administrator_creates_users`, `…the_stcd_owner_cannot_reach_the_other_roles`, `…the_administrator_still_gives_every_role`, `…the_last_administrator_is_still_protected` |
| BR-025 | ✅ | `test_user_administration::test_an_account_with_history_is_erased_and_the_audit_log_is_untouched`, `…an_account_that_was_never_used_can_be_deleted_and_the_deletion_is_audited`, `…the_detail_page_shows_history_and_the_buttons_follow_it` |
| BR-026 | ✅ | `test_withdraw_and_reimport::test_a_withdrawn_import_draft_gives_its_number_and_legacy_number_back`, `…a_withdrawn_code_that_has_its_identifier_keeps_it_and_can_be_restored`, `…a_withdrawn_code_is_listed_and_an_administrator_deletes_it_and_imports_again`, `…a_restored_code_is_no_shell_and_the_database_refuses_a_delete_around_the_service` |
| FR-199 | ✅ | `test_multi_select::test_the_helpers_read_lists_repeats_and_comma_joined_strings`, `…the_status_filter_of_the_mapping_takes_several_values`, `…the_page_shows_a_panel_of_tick_boxes_with_the_chosen_ones_ticked`, `…the_requests_filter_takes_several_states`, `…the_status_code_list_takes_several_lifecycle_states_and_categories`, `…a_search_with_several_values_is_saved_and_comes_back`, `…the_legacy_mapping_page_and_api_take_several_values` |
| FR-200 | ✅ | `test_input_hardening::test_an_identifier_wider_than_the_database_is_not_found`, `…a_text_with_control_characters_is_refused_everywhere`, `…a_password_may_hold_anything`, `…a_worksheet_never_gets_a_character_it_cannot_hold`, `test_api_fuzz::test_no_operation_answers_with_a_server_error`, `…the_fuzz_is_really_signed_in` |
| FR-201 | ✅ | `test_corpus_report::test_every_program_of_a_folder_is_checked_and_nothing_is_created`, `…a_program_the_mapping_does_not_know_is_one_line_of_the_reasons`, `…the_report_is_a_workbook_with_one_row_per_program`, `…the_command_prints_the_summary_and_writes_the_report` |
| BR-027 | ✅ | `test_mapping::test_a_second_administrator_cannot_replace_the_first_and_the_requester_cannot_decide`, `…only_the_three_roles_decide_and_each_only_once`, `…a_new_row_takes_effect_only_after_all_three_approvals` |
| SEC-026 | ✅ | `test_step_up_and_delegation::test_wrong_password_is_refused_and_audited`, `…correct_password_lets_the_signoff_through_and_is_audited`, `…repeated_wrong_passwords_lock_the_account` |
| SEC-027 | ✅ | `test_integrations_and_reports::test_a_token_is_shown_once_and_stored_only_as_a_hash`, `…a_token_reads_released_data_only_and_never_writes`, `…token_management_is_for_administrators_and_validated`; `test_route_inventory::test_a_tokenised_endpoint_is_always_a_get` |
| SEC-028 | ✅ | `test_integrations_and_reports::test_webhook_targets_must_be_internal_and_inputs_valid`, `…redirects_are_not_followed`, `…a_publish_calls_the_webhook_with_a_verifiable_signature` |
| SEC-029 | ✅ | `test_audit_chain_and_ops::test_metrics_are_refused_outside_the_allowed_networks`, `…a_metrics_token_admits_an_address_outside_the_networks`, `…ready_needs_no_login_and_reveals_no_business_data` |
| SEC-030 | ✅ | `test_audit_chain_and_ops::test_a_configured_key_makes_the_chain_keyed`, `…a_forged_row_cannot_be_repaired_without_the_key`; `test_publication::test_signed_manifest_detects_edits_to_the_manifest_itself`; installers generate the keys: `test_deploy_artifacts::test_every_setting_an_installer_writes_is_read_by_the_application` |
| SEC-031 | ✅ | `test_st_import::test_a_preview_belongs_to_its_uploader_and_expires`, `test_st_import::test_an_expired_preview_is_refused_and_removed`, `test_st_import::test_a_zip_that_unpacks_too_large_is_refused`, `test_st_import::test_only_engineers_and_administrators_import`, `test_st_import::test_the_mapping_is_not_for_viewers` |
| SEC-032 | ✅ | `test_roles_and_languages::test_only_an_administrator_creates_users`, `…other_roles_cannot_open_the_user_list`, `…the_stcd_owner_reads_the_workflow_but_changes_nothing_in_it`, `…the_stcd_owner_changes_nothing_but_the_role`; `test_route_inventory::test_the_declared_role_list_is_what_each_role_gets`; `test_schema_upgrade::test_the_table_rebuilds_leave_every_foreign_key_intact` |
| SEC-033 | ✅ | `test_email_and_windows_signin::test_a_header_from_an_address_that_is_not_a_trusted_proxy_is_not_believed`, `…production_never_starts_with_the_simulation_or_an_unknown_mode`, `…with_passwords_only_the_windows_sign_in_is_not_there`, `…with_windows_only_passwords_are_refused_and_the_login_page_says_so` |
| AUD-001 | ✅ | `test_decision_trail` (complete trace per code), `test_audit_coverage::test_each_lifecycle_action_is_audited_exactly_once` |
| AUD-002 | ✅ | `test_releases::test_full_release_lifecycle` (items of a Release); `test_publication::test_export_history_lists_hashes_per_release` |
| AUD-003 | ✅ | `test_audit_log::test_admin_sees_all_entries`, `…reviewer_only_sees_own_actions`; `test_decision_trail::test_audit_log_can_be_filtered_by_action_and_actor` |
| AUD-004 | ✅ | `test_audit_coverage::test_sandbox_delete_keeps_full_snapshot…` |
| AUD-072 | ✅ | `test_audit_coverage::test_audit_log_entries_cannot_be_updated_or_deleted`; `test_audit_chain_and_ops::test_the_append_only_triggers_still_stop_edits_inside_the_application` |
| AUD-073 | ✅ | `test_audit_chain_and_ops::test_archive_exports_old_rows_with_a_hash_and_deletes_nothing`, `…archive_with_nothing_old_enough_does_nothing`, `…cli_backup_verify_and_audit_commands` |
| AUD-074 | ✅ | `test_audit_chain_and_ops::test_every_audit_row_is_chained_to_its_predecessor`, `…the_hash_is_reproducible_from_the_stored_fields`; `test_schema_upgrade::test_the_migrated_hash_equals_what_the_application_would_have_written` |
| AUD-075 | ✅ | `test_audit_chain_and_ops::test_an_edited_row_is_found_and_named`, `…verify_tail_detects_recent_tampering_cheaply`, `…a_tampered_audit_log_inside_a_backup_is_flagged`, `…cli_audit_verify_fails_with_a_non_zero_exit_when_broken` |
| AUD-076 | ✅ | `test_user_administration::test_an_account_that_was_never_used_can_be_deleted_and_the_deletion_is_audited`, `test_withdraw_and_reimport::test_a_withdrawn_import_draft_gives_its_number_and_legacy_number_back` |
| AUD-077 | ✅ | `test_translation_review::test_only_an_administrator_or_an_stcd_owner_assigns_reviewers_and_it_is_audited`, `…a_review_is_completed_only_when_every_string_has_a_verdict_and_is_recorded`, `…an_accepted_proposal_is_shown_at_once_and_can_be_taken_back` |

## 5. Test matrix (13-test-strategy.md §8)

| TC | Where |
|---|---|
| 001, 002 | `unit/test_lifecycle.py` |
| 003, 005, 006, 031 | `unit/test_validation.py`; `test_status_codes` |
| 004, 007, 008 | `test_invariants::test_identifier_formats`, `test_sequential_submits_in_two_subgroups…`; `test_numbering.py` |
| 009, 009a, 009b, 019 | `test_change_requests`; `test_uat::test_uat_09*`; permission grid |
| 010, 011, 012, 013 | `test_invariants`; `test_schema_migration` |
| 014, 014a | `test_releases` |
| 015, 015a | `test_audit_coverage` |
| 016, 017 | `test_auth`; `test_injection_and_session` |
| 018, 018a, 018b | `test_permission_grid.py` |
| 020, 021 | `test_change_requests` |
| 022 | `test_invariants::test_full_text_search_…` |
| 023 | `test_exports_and_diff` (released, release and working-set exports exclude sandbox) |
| 024, 025 | `performance/test_performance.py` |
| 026, 027, 028 | `test_injection_and_session`; `test_csrf.py` |
| 029 | `system/test_no_cloud.py` |
| 030 | `system/test_uat.py` — UAT-01 … UAT-13 scripted (human sign-off 🧑) |
| 032, 037 | `test_lookup_admin` (+ DB triggers) |
| 033, 034 | `test_import`; `test_uat::test_uat_11…` |
| 035 | `test_exports_and_diff::test_xlsx_export_has_same_rows_as_csv` |
| 036 | `test_ui_screens::test_failed_form_submission_keeps_every_entered_value` |
| 038 | `test_step_up_and_delegation` |
| 039 | `test_content_integrity` |
| 040 | `test_review_aids` |
| 041 | `test_sla_and_notifications` |
| 042 | `test_publication` |
| 043 | `test_import_toolkit` |
| 044 | `test_audit_chain_and_ops` |
| 045 | `test_schema_upgrade` |
| 046 | `test_integrations_and_reports` |
| 047 | `test_search_and_help` |
| 048 | `test_route_inventory` |
| 049 | `test_i18n`; `test_accessibility` |
| 050 | `test_multiprocess`; `unit/test_rate_limit.py` |
| 051 | `test_deploy_artifacts` |
| 052 | `test_docs_consistency` |

**Note on "notification" (FR-031):** the spec's notification is the Review Queue / Dashboard counters ("notification-style entries", 10-ui-ux-specification.md §6), not e-mail — an e-mail relay would be an external dependency the no-cloud principle avoids. That is what is built.

## 6. What still needs a person or the production environment

| Item | Why it cannot be closed by the test suite |
|---|---|
| **UAT sign-off** (UAT-01 … 13, 13-test-strategy.md §7, §10) | The scenarios run automatically, but the roadmap requires a business sign-off pass |
| **Technical Publications end-to-end** (16-mvp-roadmap.md exit criterion) | Needs the real consumer team |
| **Lookup wording** — descriptions for the 23 Available Group codes, the eight program-reference fields, and the meaning of `Covert` | Content owned by Controls Engineering; Administrators enter it in Lookup Administration (the inline-help mechanism is done) |
| **Deployment checks** — TLS 1.2+ termination, OS ACL on the SQLite file, egress actually blocked on the server, nightly backup job | Properties of the target server, not of the code |
| **Manual OWASP checklist** (US-121 / EPIC-12) | Requires a reviewer; automated parts below |
| **Open data question** — `software_version` on revision vs. release | Resolved for now by decision D-01 (range per revision plus Release targets, 03-srs.md §6); the business may still revise it |
| **Real installation** (v4) — the installers on a clean Windows Server and a clean Linux host, systemd's own unit verification, TLS and proxy headers | Needs the target servers; the suite proves syntax, dry runs and the production entry point only |
| **Restore drill and backup storage** (v4) — quarterly restore on real hardware, the second volume, off-host copy | Properties of the target environment (14-deployment-architecture.md §7) |
| **Screen-reader pass** (v4) — WCAG 2.1 AA beyond the automated checks | Needs a person with assistive technology |
| **Meaning of `Covert`, SMTP relay, languages of the manuals** (v4) | Business answers; safe defaults are in 03-srs.md §6 (D-02, D-03, D-04) |
| **PostgreSQL** (v4) | Only the inventory and ratchet exist (NFR-014); the port and its test run are Phase 3 |
| **Key custody** (v4) — keeping `AUDIT_HMAC_KEY` and `MANIFEST_SIGNING_KEY` in the password safe | Organisational procedure |
| **Dev-tooling advisories** — `pytest` 8.3.3, `black` 24.8.0, and `starlette` (via `schemathesis`) have advisories | Development-only packages, never deployed; upgrading `pytest`/`black` is a major-version change that would reformat the code base |

### No-cloud verification record (11-security-architecture.md §12, run 2026-10-21)

| Checklist item | Result | Evidence |
|---|---|---|
| No public-cloud SaaS/PaaS/IaaS dependency | Pass | `test_no_cloud_sdk_in_requirements`, `…imports_in_source` (AWS, Azure, GCP, OCI, IBM, Firebase, telemetry SDKs) |
| No cloud identity provider | Pass | only `SessionPasswordAuthProvider` exists; provider seam test |
| No cloud storage for exports/backups | Pass | exporters return bytes to the caller; full-database export is a local SQLite backup |
| No CDN / external script or style source | Pass | `test_templates_and_static_reference_no_external_assets`; CSP `default-src 'self'` (`test_security_headers.py`) |
| No telemetry/analytics SDK | Pass | forbidden-module list includes sentry/datadog/newrelic/segment/mixpanel |
| Runs with egress blocked | Pass | `test_whole_lifecycle_works_with_all_outbound_network_blocked` |
| Dependency vulnerabilities | Pass (runtime) | `pip-audit`: none in runtime packages after the upgrades above |

## 7. Verification runs

**v4 (2026-10-23).** The complete suite (607 tests: 598 functional, 9 load) with coverage and the five static gates was executed with three methodologies (13-test-strategy.md §11): (1) file order with the gates; (2) reversed order and a seeded shuffle (seed 7), including the `schemathesis` contract tests; (3) every test on a real SQLite file. Runs 8–16 of the history table of [24-test-report.md](24-test-report.md) §9 are the discovery runs that exposed the defects of §1a (each shows one failed test); the final runs, 17–20, are clean:

| Run | Methodology | Result |
|---|---|---|
| 17 | reversed order | **607 passed**, 0 failed, 5/5 gates |
| 18 | shuffled order (seed 7) | **607 passed**, 0 failed, 5/5 gates |
| 19 | whole suite on a SQLite file | **607 passed**, 0 failed, 5/5 gates |
| 20 (final) | file order | **607 passed**, 0 failed, 0 retries, 5/5 gates, 92% line coverage, all 428 test references in this matrix resolve |

**v3 (2026-10-21).** The complete suite (319 tests, plus coverage and the five static gates) was executed repeatedly, with the order changed on purpose to prove that no test depends on another. Every run of `python cscm_tool/scripts/generate_test_report.py` appends a line to the run history in [24-test-report.md](24-test-report.md) §9.

| Run | Order | Result |
|---|---|---|
| Baseline (before this pass) | file | 302 passed — it did not catch the defects in §2 because the permission grid then encoded the wrong expectation |
| Report run 1 | reverse | 318 passed, 5/5 gates; one timing test needed a retry |
| Report run 2 | shuffled (seed 11) | 318 passed, 5/5 gates |
| Report run 3 | file | 318 passed, 5/5 gates; one timing test needed a retry |
| Report run 4 | file | 318 passed, 5/5 gates, no retry |
| Report run 5 | shuffled (seed 23) | 319 passed, 5/5 gates, no retry — after the export speed-up and its query-count test were added |
| Report run 6 (final) | file | **319 passed, 0 failed, 0 retries, 5/5 gates**, 88% line coverage, all 249 test references in this matrix resolve |

What the repeated runs revealed about the tests themselves (all fixed): the load tests failed intermittently because they ran **inside the coverage-instrumented process**, which slows Python 2–3×; they now run in a separate process without coverage, scale their time limits to a measured host-speed factor (never below 1, capped at 3×), and the 50-user test was changed from a 4 s to an 8 s think time so it models named users rather than a saturating burst. A performance test that fails is re-run once alone and flagged "retry" in the report; any other failure is never retried.

Because the report is regenerated after every software change, **its history table, not this paragraph, is the authoritative record of which runs happened and what they returned.**

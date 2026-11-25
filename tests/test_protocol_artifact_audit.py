import csv
import copy
import json
import tempfile
import unittest
from types import SimpleNamespace
from unittest.mock import patch
from hashlib import sha256
from pathlib import Path

from scripts.audit_tdk_protocol_artifact import (
    ArtifactAuditError,
    LEGACY_AUDITED_PAIR_METRICS,
    PAIR_METRICS,
    _event_rows_sha256,
    _expected_metric_suffixes,
    _verify_declared_matrix,
    _verify_boundary,
    _verify_paired_comparisons,
    _verify_model_comparison,
    _verify_research_environment,
    _requires_bitemporal_contract,
    _verify_scenario_metrics,
    _verify_temporal_view_rows,
    _verify_truth_sidecars,
    audit_artifact,
)
from scripts.run_tdk_protocol_experiment import (
    _aggregate_rows,
    _paired_comparisons,
    _representation_control_contrasts,
    _robustness_slices,
)
from scripts.run_tdk_research_experiment import PROVENANCE_SOURCE_PATHS, _provenance
from src.research.independent_scenario_adapter import adapt_independent_world
from src.research.independent_scenarios import (
    generate_independent_world,
    independent_covering_scenario_matrix,
)
from src.services.anomaly_detection.protocol_evaluation import (
    evaluate_residual_model_comparison,
    exploratory_feature_representations,
)


def _complete_source_hashes() -> dict:
    """Build the COMPLETE required source-hash map at HEAD.

    The artifact auditor now enforces that provenance covers every required
    source path (finding R10), so fixtures must supply the full set rather than
    a single stand-in file.
    """
    import subprocess

    repo_root = Path.cwd()
    hashes = {}
    for path in PROVENANCE_SOURCE_PATHS:
        content = subprocess.run(
            ["git", "show", f"HEAD:{path}"],
            cwd=repo_root, capture_output=True,
        ).stdout
        hashes[path] = sha256(content).hexdigest()
    return hashes


def _environment_provenance_at_head() -> dict:
    import subprocess

    declaration_bytes = subprocess.run(
        ["git", "show", "HEAD:research-environment.json"],
        cwd=Path.cwd(),
        check=True,
        capture_output=True,
    ).stdout
    declaration = json.loads(declaration_bytes.decode("utf-8"))
    lock_file = declaration["lock_file"]
    lock_bytes = subprocess.run(
        ["git", "show", f"HEAD:{lock_file}"],
        cwd=Path.cwd(),
        check=True,
        capture_output=True,
    ).stdout
    packages = {}
    for raw_line in lock_bytes.decode("utf-8").splitlines():
        line = raw_line.strip()
        if line and not line.startswith("#"):
            package, package_version = line.split("==", 1)
            packages[package.casefold().replace("_", "-")] = package_version
    return {
        "python_version": declaration["python_version"] + " (fixture)",
        "packages": packages,
        "research_environment": {
            "expected_python_version": declaration["python_version"],
            "declaration_file": "research-environment.json",
            "declaration_sha256": sha256(declaration_bytes).hexdigest(),
            "lock_file": lock_file,
            "lock_sha256": sha256(lock_bytes).hexdigest(),
            "mismatches": [],
        },
    }


class ProtocolArtifactAuditTests(unittest.TestCase):
    def test_holdout_boundary_requires_matching_successful_ledger(self):
        gate = {
            "attempt_id": "attempt-1",
            "authorization_sha256": "a" * 64,
            "matrix_sha256": "b" * 64,
            "frozen_git_commit": "c" * 40,
        }
        metadata = {
            "run_purpose": "holdout",
            "holdout_accessed": True,
            "protocol_status": "frozen_independent_holdout",
            "holdout_gate": gate,
            "provenance": {"git_commit": gate["frozen_git_commit"]},
        }
        with tempfile.TemporaryDirectory() as directory:
            run_dir = Path(directory)
            ledger_path = run_dir / "holdout_execution_ledger.json"
            ledger_path.write_text(json.dumps({
                **gate,
                "state": "succeeded",
                "outcome": {"success": True},
            }), encoding="utf-8")

            with (
                patch(
                    "scripts.audit_tdk_protocol_artifact.parse_authorization_json",
                    return_value={},
                ),
                patch(
                    "scripts.audit_tdk_protocol_artifact.inspect_repository"
                ),
                patch(
                    "scripts.audit_tdk_protocol_artifact.validate_authorization",
                    return_value=gate["authorization_sha256"],
                ),
            ):
                result = _verify_boundary(
                    metadata,
                    run_dir,
                    Path.cwd(),
                    Path("external-authorization.json"),
                    ledger_path,
                )

            self.assertTrue(result["verified"])
            tampered = json.loads(ledger_path.read_text(encoding="utf-8"))
            tampered["matrix_sha256"] = "d" * 64
            ledger_path.write_text(json.dumps(tampered), encoding="utf-8")
            with self.assertRaisesRegex(ArtifactAuditError, "matrix_sha256"):
                _verify_boundary(
                    metadata,
                    run_dir,
                    Path.cwd(),
                    Path("external-authorization.json"),
                    ledger_path,
                )

    def test_holdout_boundary_rejects_missing_or_failed_ledger(self):
        metadata = {
            "run_purpose": "holdout",
            "holdout_accessed": True,
            "protocol_status": "frozen_independent_holdout",
            "holdout_gate": {
                "attempt_id": "attempt-1",
                "authorization_sha256": "a" * 64,
                "matrix_sha256": "b" * 64,
                "frozen_git_commit": "c" * 40,
            },
            "provenance": {"git_commit": "c" * 40},
        }
        with self.assertRaisesRegex(ArtifactAuditError, "requires"):
            _verify_boundary(metadata)
        with tempfile.TemporaryDirectory() as directory:
            run_dir = Path(directory)
            ledger_path = run_dir / "holdout_execution_ledger.json"
            ledger_path.write_text(json.dumps({
                **metadata["holdout_gate"],
                "state": "failed",
                "outcome": {"success": False},
            }), encoding="utf-8")
            with self.assertRaisesRegex(ArtifactAuditError, "not successfully"):
                _verify_boundary(
                    metadata,
                    run_dir,
                    Path.cwd(),
                    Path("external-authorization.json"),
                    ledger_path,
                )

    def test_provenance_covers_analysis_and_audit_sources(self):
        self.assertIn(
            "src/research/condition_statistics.py",
            PROVENANCE_SOURCE_PATHS,
        )
        self.assertIn(
            "scripts/combine_tdk_independent_shards.py",
            PROVENANCE_SOURCE_PATHS,
        )
        self.assertIn(
            "scripts/audit_tdk_protocol_artifact.py",
            PROVENANCE_SOURCE_PATHS,
        )

    def test_schema_eight_environment_provenance_matches_locked_revision(self):
        declaration_bytes = (
            b'{"python_version":"3.13.5",'
            b'"lock_file":"requirements-research-lock.txt"}\n'
        )
        lock_bytes = b"numpy==2.5.4\nscipy==1.18.1\n"
        metadata = {
            "artifact_schema_version": 8,
            "provenance": {
                "git_commit": "revision",
                "python_version": "3.13.5 (main, test)",
                "packages": {"numpy": "2.5.4", "scipy": "1.18.1"},
                "research_environment": {
                    "expected_python_version": "3.13.5",
                    "declaration_file": "research-environment.json",
                    "declaration_sha256": sha256(declaration_bytes).hexdigest(),
                    "lock_file": "requirements-research-lock.txt",
                    "lock_sha256": sha256(lock_bytes).hexdigest(),
                    "mismatches": [],
                },
            },
        }

        with patch(
            "scripts.audit_tdk_protocol_artifact.subprocess.run",
            side_effect=(
                SimpleNamespace(returncode=0, stdout=declaration_bytes),
                SimpleNamespace(returncode=0, stdout=lock_bytes),
            ),
        ):
            _verify_research_environment(metadata, Path.cwd())

    def test_environment_provenance_rejects_forged_metadata(self):
        declaration_bytes = (
            b'{"python_version":"3.13.5",'
            b'"lock_file":"requirements-research-lock.txt"}\n'
        )
        lock_bytes = b"numpy==2.5.4\n"
        base = {
            "artifact_schema_version": 8,
            "provenance": {
                "git_commit": "revision",
                "python_version": "3.13.5 (main, test)",
                "packages": {"numpy": "2.5.4"},
                "research_environment": {
                    "expected_python_version": "3.13.5",
                    "declaration_file": "research-environment.json",
                    "declaration_sha256": sha256(declaration_bytes).hexdigest(),
                    "lock_file": "requirements-research-lock.txt",
                    "lock_sha256": sha256(lock_bytes).hexdigest(),
                    "mismatches": [],
                },
            },
        }
        mutations = (
            lambda value: value["provenance"]["research_environment"].update(
                expected_python_version="3.12.0"
            ),
            lambda value: value["provenance"]["research_environment"].update(
                declaration_sha256="forged"
            ),
            lambda value: value["provenance"]["research_environment"].update(
                lock_sha256="forged"
            ),
            lambda value: value["provenance"]["packages"].update(numpy="0.0"),
        )
        for mutate in mutations:
            metadata = copy.deepcopy(base)
            mutate(metadata)
            with self.subTest(metadata=metadata), patch(
                "scripts.audit_tdk_protocol_artifact.subprocess.run",
                side_effect=(
                    SimpleNamespace(returncode=0, stdout=declaration_bytes),
                    SimpleNamespace(returncode=0, stdout=lock_bytes),
                ),
            ):
                with self.assertRaises(ArtifactAuditError):
                    _verify_research_environment(metadata, Path.cwd())

    def test_schema_downgrade_cannot_bypass_new_revision_checks(self):
        declaration_bytes = b'{"python_version":"3.13.5","lock_file":"requirements-research-lock.txt"}\n'
        metadata = {
            "artifact_schema_version": 7,
            "provenance": {"git_commit": "new-revision"},
        }

        with patch(
            "scripts.audit_tdk_protocol_artifact.subprocess.run",
            return_value=SimpleNamespace(returncode=0, stdout=declaration_bytes),
        ):
            with self.assertRaisesRegex(ArtifactAuditError, "provenance is missing"):
                _verify_research_environment(metadata, Path.cwd())

    def test_schema_eight_environment_provenance_rejects_drift(self):
        declaration_bytes = (
            b'{"python_version":"3.13.5",'
            b'"lock_file":"requirements-research-lock.txt"}\n'
        )
        metadata = {
            "artifact_schema_version": 8,
            "provenance": {
                "git_commit": "revision",
                "research_environment": {"mismatches": ["numpy drift"]},
            },
        }

        with patch(
            "scripts.audit_tdk_protocol_artifact.subprocess.run",
            return_value=SimpleNamespace(returncode=0, stdout=declaration_bytes),
        ):
            with self.assertRaisesRegex(ArtifactAuditError, "environment drift"):
                _verify_research_environment(metadata, Path.cwd())

    def test_legacy_environment_provenance_remains_optional(self):
        import subprocess

        with tempfile.TemporaryDirectory() as directory:
            repo = Path(directory)
            subprocess.run(["git", "init", "-q"], cwd=repo, check=True)
            subprocess.run(
                ["git", "config", "user.email", "fixture@example.test"],
                cwd=repo,
                check=True,
            )
            subprocess.run(
                ["git", "config", "user.name", "Fixture"],
                cwd=repo,
                check=True,
            )
            (repo / "historical.txt").write_text("legacy\n", encoding="utf-8")
            subprocess.run(["git", "add", "historical.txt"], cwd=repo, check=True)
            subprocess.run(
                ["git", "commit", "-qm", "Historical fixture"],
                cwd=repo,
                check=True,
            )
            revision = subprocess.run(
                ["git", "rev-parse", "HEAD"],
                cwd=repo,
                check=True,
                capture_output=True,
                text=True,
            ).stdout.strip()

            _verify_research_environment(
                {
                    "artifact_schema_version": 7,
                    "provenance": {"git_commit": revision},
                },
                repo,
            )

    def test_current_independent_protocol_requires_bitemporal_contract(self):
        self.assertTrue(_requires_bitemporal_contract(
            "independent-scenarios-v3-2026-11-19",
            7,
        ))
        self.assertTrue(_requires_bitemporal_contract(
            "independent-development-v2-2026-10-29",
            5,
        ))
        self.assertTrue(_requires_bitemporal_contract(
            "myhr-tdk-holdout-v2",
            8,
        ))
        self.assertFalse(_requires_bitemporal_contract(
            "independent-scenarios-v3-2026-11-19",
            4,
        ))

    def test_provenance_dirty_flag_is_scoped_to_tracked_files(self):
        calls = []

        def fake_git_output(*arguments):
            calls.append(arguments)
            return "revision" if arguments[0] == "rev-parse" else ""

        with patch(
            "scripts.run_tdk_research_experiment._git_output",
            side_effect=fake_git_output,
        ), patch(
            "scripts.run_tdk_research_experiment._git_object_bytes",
            return_value=b"tracked source",
        ), patch(
            "scripts.verify_research_environment.environment_report",
            return_value={
                "expected_python_version": "3.13.5",
                "declaration_file": "research-environment.json",
                "declaration_sha256": "declaration-hash",
                "lock_file": "requirements-research-lock.txt",
                "lock_sha256": "lock-hash",
                "mismatches": [],
                "packages": {"numpy": "test-version"},
            },
        ):
            provenance = _provenance()

        self.assertFalse(provenance["git_dirty"])
        self.assertEqual(provenance["git_dirty_scope"], "tracked_files_only")
        self.assertIn(
            ("status", "--porcelain", "--untracked-files=no"),
            calls,
        )

    def test_provenance_rejects_environment_drift(self):
        with patch(
            "scripts.verify_research_environment.environment_report",
            return_value={"mismatches": ["python drift"]},
        ):
            with self.assertRaisesRegex(RuntimeError, "python drift"):
                _provenance()

    def test_model_comparison_is_independently_verified(self):
        for run_purpose in (
            "independent_development",
            "independent_validation",
        ):
            with self.subTest(run_purpose=run_purpose):
                spec = independent_covering_scenario_matrix(
                    run_purpose,
                    employee_count=120,
                )[0]
                scenario = adapt_independent_world(generate_independent_world(spec))
                evaluation = evaluate_residual_model_comparison(scenario)
                metrics = list(evaluation.metric_rows)
                predictions = list(evaluation.prediction_rows)

                with tempfile.TemporaryDirectory() as directory:
                    run_dir = Path(directory)
                    self._write_csv(run_dir / "model_comparison_metrics.csv", metrics)
                    self._write_csv(
                        run_dir / "model_comparison_predictions.csv",
                        predictions,
                    )
                    self._write_csv(
                        run_dir / "model_comparison_aggregates.csv",
                        _aggregate_rows(metrics),
                    )
                    self._write_csv(
                        run_dir / "model_comparison_paired.csv",
                        _paired_comparisons(metrics),
                    )
                    self._write_csv(
                        run_dir / "model_comparison_control_contrasts.csv",
                        _representation_control_contrasts(metrics),
                    )
                    self._write_csv(
                        run_dir / "model_comparison_robustness.csv",
                        _robustness_slices(metrics),
                    )

                    result = _verify_model_comparison(
                        run_dir,
                        {
                            "model_comparison_included": True,
                            "run_purpose": run_purpose,
                        },
                    )

                self.assertTrue(result["present"])
                self.assertEqual(result["scenario_count"], 1)
                self.assertEqual(result["metric_rows"], 25)

    def test_raw_rate_control_is_policy_free_and_dimension_matched(self):
        representations = {
            item.name: item for item in exploratory_feature_representations()
        }
        control = representations["raw_rate_control"]
        policy = representations["policy_matched"]

        self.assertEqual(len(control.feature_names), len(policy.feature_names))
        self.assertEqual(control.policy_mode, "raw_rates")
        self.assertTrue(all(not name.startswith("policy_") for name in control.feature_names))

    def test_required_truth_sidecars_cannot_all_be_removed(self):
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaisesRegex(ArtifactAuditError, "required truth sidecars"):
                _verify_truth_sidecars(Path(directory), [], required=True)

    def test_schema_five_requires_event_linked_entitlement_for_grandfathering(self):
        with tempfile.TemporaryDirectory() as directory:
            run_dir = Path(directory)
            truth = {
                "scenario_id": "s1", "employee_id": "E1", "split": "test",
                "truth_category": "rare_legitimate",
                "evaluation_eligible": True,
                "nominal_anomaly_mechanism": "approval_bypass",
                "nominal_rare_pattern": "grandfathered_policy",
                "realized_mechanism": "grandfathered_policy",
                "employment_track": "progression", "current_level": "L6",
                "department": "Operations", "role": "Officer",
                "date_of_birth": "1990-01-01", "hire_date": "2020-01-01",
                "event_count": 1, "causal_evidence": "Entitled.",
            }
            event = {
                "scenario_id": "s1", "employee_id": "E1", "event_id": "P1",
                "event_kind": "promotion", "policy_id": "legacy",
                "policy_version": "1.0",
                "effective_date": "2023-06-01", "recorded_date": "2023-06-02",
                "approval_reference": "AR-1", "approval_status": "approved",
                "correction_of_event_id": "", "retry_of_event_id": "",
                "recognized_service_months": "0",
                "jurisdiction": "organization-wide",
                "level_before": "L7", "level_after": "L6", "category": "",
                "resolved_date": "",
            }
            truth["event_ledger_sha256"] = _event_rows_sha256([event])
            truth["causal_events_json"] = json.dumps([{
                "event_id": "P1", "kind": "promotion", "policy_id": "legacy",
                "policy_version": "1.0",
                "effective_date": "2023-06-01", "recorded_date": "2023-06-02",
                "category": None, "resolved_date": None,
                "approval_reference": "AR-1", "approval_status": "approved",
                "correction_of_event_id": None, "retry_of_event_id": None,
                "recognized_service_months": 0,
                "jurisdiction": "organization-wide",
                "level_before": "L7", "level_after": "L6",
                "ledger_status": "observed",
            }])
            policy = {
                "scenario_id": "s1", "policy_id": "legacy",
                "policy_version": "1.0", "effective_from": "2010-01-01",
                "effective_to": "2022-12-31", "recorded_at": "2009-12-01",
                "jurisdiction": "organization-wide",
                "service_months_by_level_json": json.dumps({"L7": 30}),
                "grandfather_previous_policy": True,
            }
            entitlement = {
                "scenario_id": "s1", "entitlement_id": "ENT-1",
                "employee_id": "E1", "policy_id": "legacy",
                "policy_version": "1.0", "relevant_event_id": "P1",
                "evidence_reference": "GF-E1-P1", "recorded_at": "2023-05-01",
            }
            self._write_csv(run_dir / "record_truth.csv", [truth])
            self._write_csv(run_dir / "administrative_events.csv", [event])
            self._write_csv(run_dir / "policy_epochs.csv", [policy])
            self._write_csv(run_dir / "entitlement_evidence.csv", [entitlement])

            result = _verify_truth_sidecars(
                run_dir,
                [{"scenario_id": "s1", "employee_id": "E1"}],
                required=True,
                protocol_version="independent-development-v2-2026-10-29",
                artifact_schema_version=5,
            )
            self.assertTrue(result["present"])

            mismatched = dict(entitlement, policy_version="2.0")
            self._write_csv(
                run_dir / "entitlement_evidence.csv",
                [mismatched],
            )
            with self.assertRaisesRegex(
                ArtifactAuditError,
                "unknown policy version",
            ):
                _verify_truth_sidecars(
                    run_dir,
                    [{"scenario_id": "s1", "employee_id": "E1"}],
                    required=True,
                    protocol_version="independent-development-v2-2026-10-29",
                    artifact_schema_version=5,
                )

            (run_dir / "entitlement_evidence.csv").write_text(
                ",".join(entitlement) + "\n",
                encoding="utf-8",
            )
            with self.assertRaisesRegex(
                ArtifactAuditError,
                "lacks event-linked entitlement",
            ):
                _verify_truth_sidecars(
                    run_dir,
                    [{"scenario_id": "s1", "employee_id": "E1"}],
                    required=True,
                    protocol_version="independent-development-v2-2026-10-29",
                    artifact_schema_version=5,
                )

    def test_temporal_sidecar_rejects_later_knowledge_in_known_then(self):
        events = {
            ("s1", "E1", "P1"): {
                "scenario_id": "s1", "employee_id": "E1", "event_id": "P1",
                "event_kind": "promotion", "effective_date": "2022-01-01",
                "recorded_date": "2022-01-01",
            },
            ("s1", "E1", "C1"): {
                "scenario_id": "s1", "employee_id": "E1", "event_id": "C1",
                "event_kind": "promotion", "effective_date": "2022-01-01",
                "recorded_date": "2025-01-01",
            },
        }
        by_employee = {("s1", "E1"): list(events.values())}
        base = {
            "scenario_id": "s1", "employee_id": "E1",
            "decision_event_id": "P1", "decision_effective_date": "2022-01-01",
            "effective_through": "2022-01-01",
            "promotion_assessment_count": "1",
            "total_service_deficit_months": "0",
        }
        rows = [
            {
                **base,
                "view_identifier": "known_then",
                "recorded_through": "2022-01-01",
                "visible_event_ids_json": json.dumps(["P1"]),
                "visible_event_count": "1",
                "effective_event_ids_json": json.dumps(["P1"]),
                "effective_event_count": "1",
            },
            {
                **base,
                "view_identifier": "later_review",
                "recorded_through": "2026-12-31",
                "visible_event_ids_json": json.dumps(["P1", "C1"]),
                "visible_event_count": "2",
                "effective_event_ids_json": json.dumps(["C1"]),
                "effective_event_count": "1",
            },
        ]
        _verify_temporal_view_rows(rows, events, by_employee)

        rows[0]["visible_event_ids_json"] = json.dumps(["P1", "C1"])
        rows[0]["visible_event_count"] = "2"
        with self.assertRaisesRegex(ArtifactAuditError, "later knowledge leaked"):
            _verify_temporal_view_rows(rows, events, by_employee)

    def test_audit_recomputes_counts_and_rates(self):
        with tempfile.TemporaryDirectory() as directory:
            run_dir = Path(directory)
            self._write_fixture(run_dir)

            result = audit_artifact(run_dir, Path.cwd())

            self.assertEqual(result["status"], "verified")
            self.assertEqual(result["scenario_count"], 1)
            self.assertEqual(result["prediction_rows"], 2)

    def test_audit_rejects_tampered_artifact(self):
        with tempfile.TemporaryDirectory() as directory:
            run_dir = Path(directory)
            self._write_fixture(run_dir)
            (run_dir / "record_predictions.csv").write_text("tampered\n", encoding="utf-8")

            with self.assertRaisesRegex(ArtifactAuditError, "checksum mismatch"):
                audit_artifact(run_dir, Path.cwd())

    def test_audit_recomputes_average_precision_from_scores(self):
        with tempfile.TemporaryDirectory() as directory:
            run_dir = Path(directory)
            self._write_fixture(run_dir)
            with (run_dir / "record_predictions.csv").open(
                newline="", encoding="utf-8"
            ) as handle:
                predictions = list(csv.DictReader(handle))
            for row in predictions:
                row["score"] = "0.0"
            self._write_csv(run_dir / "record_predictions.csv", predictions)
            self._rewrite_manifest(run_dir)

            with self.assertRaisesRegex(ArtifactAuditError, "average_precision mismatch"):
                audit_artifact(run_dir, Path.cwd())

    def test_truth_sidecars_preserve_joinable_causal_provenance(self):
        with tempfile.TemporaryDirectory() as directory:
            run_dir = Path(directory)
            ledger_event = {
                "scenario_id": "s1",
                "employee_id": "E1",
                "event_id": "EV-1",
                "event_kind": "promotion",
                "policy_id": "legacy-2018",
                "effective_date": "2022-01-01",
                "recorded_date": "2022-01-02",
                "approval_reference": "AR-1",
                "correction_of_event_id": "",
                "level_before": "L7",
                "level_after": "L6",
                "category": "",
                "resolved_date": "",
            }
            self._write_csv(run_dir / "record_truth.csv", [{
                "scenario_id": "s1",
                "employee_id": "E1",
                "split": "test",
                "truth_category": "rare_legitimate",
                "nominal_anomaly_mechanism": "approval_bypass",
                "nominal_rare_pattern": "grandfathered_policy",
                "realized_mechanism": "grandfathered_policy",
                "employment_track": "progression",
                "current_level": "L6",
                "department": "Operations",
                "role": "Officer",
                "date_of_birth": "1990-01-01",
                "hire_date": "2020-01-01",
                "event_count": 1,
                "event_ledger_sha256": _event_rows_sha256([ledger_event]),
                "causal_evidence": "Grandfathered service requirement.",
                "causal_events_json": json.dumps([{
                    "event_id": "EV-1",
                    "kind": "promotion",
                    "policy_id": "legacy-2018",
                    "effective_date": "2022-01-01",
                    "recorded_date": "2022-01-02",
                    "category": None,
                    "resolved_date": None,
                    "approval_reference": "AR-1",
                    "correction_of_event_id": None,
                    "level_before": "L7",
                    "level_after": "L6",
                    "ledger_status": "observed",
                }]),
            }])
            self._write_csv(run_dir / "administrative_events.csv", [ledger_event])
            self._write_csv(run_dir / "policy_epochs.csv", [{
                "scenario_id": "s1",
                "policy_id": "legacy-2018",
                "effective_from": "2018-01-01",
                "service_months_by_level_json": json.dumps({"L7": 30}),
                "grandfather_previous_policy": True,
            }])
            result = _verify_truth_sidecars(run_dir, [{
                "scenario_id": "s1",
                "employee_id": "E1",
            }])

            self.assertTrue(result["present"])
            self.assertEqual(result["record_truth_rows"], 1)

            with (run_dir / "record_truth.csv").open(
                newline="", encoding="utf-8"
            ) as handle:
                truth_rows = list(csv.DictReader(handle))
            causal = json.loads(truth_rows[0]["causal_events_json"])
            causal[0]["kind"] = "sanction"
            truth_rows[0]["causal_events_json"] = json.dumps(causal)
            self._write_csv(run_dir / "record_truth.csv", truth_rows)
            with self.assertRaisesRegex(ArtifactAuditError, "does not match event ledger"):
                _verify_truth_sidecars(run_dir, [{
                    "scenario_id": "s1",
                    "employee_id": "E1",
                }])

    def test_truth_sidecars_validate_omitted_causal_events(self):
        with tempfile.TemporaryDirectory() as directory:
            run_dir = Path(directory)
            causal = {
                "event_id": "EV-REMOVED",
                "kind": "salary_increment",
                "policy_id": "legacy-2018",
                "effective_date": "2022-01-01",
                "recorded_date": "2022-01-02",
                "category": None,
                "resolved_date": None,
                "approval_reference": None,
                "correction_of_event_id": None,
                "level_before": None,
                "level_after": None,
                "ledger_status": "omitted",
            }
            ledger_event = {
                "scenario_id": "s1", "employee_id": "E1", "event_id": "EV-OBSERVED",
                "event_kind": "hire", "policy_id": "legacy-2018",
                "effective_date": "2020-01-01", "recorded_date": "2020-01-01",
                "approval_reference": "", "correction_of_event_id": "",
                "level_before": "", "level_after": "L7", "category": "",
                "resolved_date": "",
            }
            self._write_csv(run_dir / "record_truth.csv", [{
                "scenario_id": "s1", "employee_id": "E1", "split": "test",
                "truth_category": "confirmed_recording_error",
                "nominal_anomaly_mechanism": "missing_increment_import",
                "nominal_rare_pattern": "grandfathered_policy",
                "realized_mechanism": "missing_increment_import",
                "employment_track": "progression", "current_level": "L7",
                "department": "Operations", "role": "Officer",
                "date_of_birth": "1990-01-01", "hire_date": "2020-01-01",
                "event_count": 1,
                "event_ledger_sha256": _event_rows_sha256([ledger_event]),
                "causal_evidence": "omitted",
                "causal_events_json": json.dumps([causal]),
            }])
            self._write_csv(run_dir / "administrative_events.csv", [ledger_event])
            self._write_csv(run_dir / "policy_epochs.csv", [{
                "scenario_id": "s1", "policy_id": "legacy-2018",
                "effective_from": "2018-01-01",
                "service_months_by_level_json": json.dumps({"L7": 30}),
                "grandfather_previous_policy": True,
            }])
            prediction = [{"scenario_id": "s1", "employee_id": "E1"}]
            self.assertTrue(_verify_truth_sidecars(run_dir, prediction)["present"])

            changed_ledger = dict(ledger_event, event_kind="promotion")
            self._write_csv(run_dir / "administrative_events.csv", [changed_ledger])
            with self.assertRaisesRegex(ArtifactAuditError, "event ledger checksum mismatch"):
                _verify_truth_sidecars(run_dir, prediction)
            self._write_csv(run_dir / "administrative_events.csv", [ledger_event])

            causal["ledger_status"] = "observed"
            with (run_dir / "record_truth.csv").open(
                newline="", encoding="utf-8"
            ) as handle:
                rows = list(csv.DictReader(handle))
            rows[0]["causal_events_json"] = json.dumps([causal])
            self._write_csv(run_dir / "record_truth.csv", rows)
            with self.assertRaisesRegex(ArtifactAuditError, "missing from event ledger"):
                _verify_truth_sidecars(run_dir, prediction)

    def test_audit_recomputes_paired_inference_and_holm_values(self):
        metrics = []
        for scenario_index, scenario_id in enumerate(("s1", "s2"), start=1):
            for representation, offset in (("raw_matched", 0.0), ("policy_matched", 0.05)):
                row = {
                    "scenario_id": scenario_id,
                    "method": "isolation_forest_residual",
                    "representation": representation,
                    "operating_point": "fixed_review_budget",
                }
                for metric_index, metric in enumerate(PAIR_METRICS, start=1):
                    row[metric] = 0.1 * scenario_index + 0.001 * metric_index + offset
                metrics.append(row)
        paired = _paired_comparisons(metrics)

        self.assertEqual(paired[0]["scenario_count"], 2)
        self.assertAlmostEqual(paired[0]["average_precision_delta_mean"], 0.05)
        self.assertAlmostEqual(paired[0]["average_precision_delta_median"], 0.05)
        self.assertAlmostEqual(paired[0]["average_precision_delta_std"], 0.0)
        self.assertAlmostEqual(paired[0]["average_precision_delta_ci95_low"], 0.05)
        self.assertAlmostEqual(paired[0]["average_precision_delta_ci95_high"], 0.05)
        self.assertAlmostEqual(paired[0]["average_precision_delta_sign_flip_p"], 0.5)
        self.assertAlmostEqual(paired[0]["average_precision_delta_holm_all_p"], 1.0)
        _verify_paired_comparisons(metrics, paired)
        paired[0]["average_precision_delta_ci95_high"] = (
            float(paired[0]["average_precision_delta_ci95_high"]) + 0.1
        )
        with self.assertRaisesRegex(ArtifactAuditError, "paired .* mismatch"):
            _verify_paired_comparisons(metrics, paired)

    def test_audit_rejects_tampered_declared_secondary_holm_family(self):
        metrics = []
        for scenario_id in ("s1", "s2"):
            for representation, offset in (
                ("raw_matched", 0.0),
                ("policy_matched", 0.05),
            ):
                metrics.append({
                    "scenario_id": scenario_id,
                    "method": "rule_negative_isolation_forest",
                    "representation": representation,
                    "operating_point": "fixed_review_budget",
                    **{name: 0.4 + offset for name in PAIR_METRICS},
                })
        paired = _paired_comparisons(metrics)
        primary = paired[0]
        self.assertEqual(primary["secondary_family_declared_size"], 3)
        primary["average_precision_delta_holm_secondary_p"] = 0.123

        with self.assertRaisesRegex(ArtifactAuditError, "paired .* mismatch"):
            _verify_paired_comparisons(metrics, paired)

    def test_legacy_paired_schema_is_audited_without_inventing_new_metrics(self):
        metrics = []
        for scenario_id in ("s1", "s2"):
            for representation, offset in (
                ("raw_matched", 0.0),
                ("policy_matched", 0.05),
            ):
                metrics.append({
                    "scenario_id": scenario_id,
                    "method": "isolation_forest_residual",
                    "representation": representation,
                    "operating_point": "fixed_review_budget",
                    **{
                        name: 0.4 + offset
                        for name in LEGACY_AUDITED_PAIR_METRICS
                    },
                })
        paired = _paired_comparisons(metrics)
        for row in paired:
            for metric in set(PAIR_METRICS) - set(LEGACY_AUDITED_PAIR_METRICS):
                for column in list(row):
                    if column.startswith(f"{metric}_"):
                        row.pop(column)

        result = _verify_paired_comparisons(metrics, paired)

        self.assertEqual(
            result["audited_metrics"],
            list(LEGACY_AUDITED_PAIR_METRICS),
        )
        self.assertIn(
            "false_positives",
            result["unavailable_newer_metrics"],
        )

    def test_declared_matrix_verifies_seed_replicate_provenance(self):
        configs = []
        metrics = []
        for condition_index in (1, 2):
            for replicate in (1, 2, 3):
                scenario_id = f"c{condition_index}-seed-{replicate:02d}"
                configs.append({
                    "scenario_id": scenario_id,
                    "condition_id": f"c{condition_index}",
                    "seed_replicate": str(replicate),
                    "seed": str(100 * condition_index + replicate),
                    "split_seed": str(200 * condition_index + replicate),
                    "model_seed": str(300 * condition_index + replicate),
                })
                metrics.append({"scenario_id": scenario_id})
        metadata = {
            "protocol_version": "seed-provenance-test",
            "scenario_count": 6,
            "condition_count": 2,
            "seeds_per_condition": 3,
        }

        _verify_declared_matrix(metadata, configs, metrics)
        configs[-1]["seed_replicate"] = "2"
        with self.assertRaisesRegex(ArtifactAuditError, "replicates are incomplete"):
            _verify_declared_matrix(metadata, configs, metrics)

    def test_declared_matrix_accepts_explicit_shard_replicate_range(self):
        configs = [{
            "scenario_id": f"c1-seed-{replicate:02d}",
            "condition_id": "c1",
            "seed_replicate": str(replicate),
            "seed": str(100 + replicate),
            "split_seed": str(200 + replicate),
            "model_seed": str(300 + replicate),
        } for replicate in (7, 8)]
        metrics = [{"scenario_id": row["scenario_id"]} for row in configs]
        metadata = {
            "protocol_version": "seed-provenance-test",
            "scenario_count": 2,
            "condition_count": 1,
            "seeds_per_condition": 2,
            "seed_replicate_start": 7,
        }

        _verify_declared_matrix(metadata, configs, metrics)

    def test_v2_matrix_requires_generation_attempt_provenance(self):
        configs = [{
            "scenario_id": "c1-seed-01",
            "condition_id": "c1",
            "seed_replicate": "1",
            "seed": "1",
            "split_seed": "2",
            "model_seed": "3",
            "generation_attempt": "1",
        }]
        metrics = [{"scenario_id": "c1-seed-01"}]
        metadata = {
            "protocol_version": "myhr-tdk-holdout-v2",
            "scenario_count": 1,
            "condition_count": 1,
            "seeds_per_condition": 1,
        }

        _verify_declared_matrix(metadata, configs, metrics)
        configs[0].pop("generation_attempt")
        with self.assertRaisesRegex(ArtifactAuditError, "generation-attempt"):
            _verify_declared_matrix(metadata, configs, metrics)

    def test_audit_rejects_duplicate_metric_keys_and_incomplete_pairs(self):
        prediction = {
            "scenario_id": "s1", "employee_id": "E1", "method": "m",
            "representation": "raw_matched", "operating_point": "budget",
        }
        metric = {key: value for key, value in prediction.items() if key != "employee_id"}
        with self.assertRaisesRegex(ArtifactAuditError, "duplicate scenario metric"):
            _verify_scenario_metrics([metric, dict(metric)], [prediction])

        paired_metric = {
            "scenario_id": "s1", "method": "isolation_forest_residual",
            "representation": "raw_matched", "operating_point": "fixed_review_budget",
            **{name: 0.5 for name in PAIR_METRICS},
        }
        with self.assertRaisesRegex(ArtifactAuditError, "incomplete raw/policy pair"):
            _verify_paired_comparisons([paired_metric], [])

    def test_declared_matrix_rejects_coordinated_metric_group_deletion(self):
        protocol = "independent-development-v1-2026-10-16"
        expected = _expected_metric_suffixes(protocol)
        self.assertIsNotNone(expected)
        self.assertEqual(len(expected), 74)
        rows = [{
            "scenario_id": "s1", "method": method,
            "representation": representation, "operating_point": operating_point,
        } for method, representation, operating_point in expected]
        metadata = {"protocol_version": protocol, "scenario_count": 1}
        configs = [{"scenario_id": "s1"}]

        _verify_declared_matrix(metadata, configs, rows)
        with self.assertRaisesRegex(ArtifactAuditError, "metric matrix is incomplete"):
            _verify_declared_matrix(metadata, configs, rows[:-1])

    def test_v2_matrix_includes_every_residual_control(self):
        expected = _expected_metric_suffixes(
            "independent-development-v2-2026-10-29"
        )
        self.assertIsNotNone(expected)
        self.assertEqual(len(expected), 75)
        residual_representations = {
            representation
            for method, representation, point in expected
            if method == "rule_negative_isolation_forest"
            and point == "fixed_review_budget"
        }
        self.assertEqual(
            residual_representations,
            {
                "raw_matched",
                "policy_matched",
                "policy_deficit_months_ablation",
                "policy_deficit_ratio_ablation",
                "policy_unexplained_ablation",
                "raw_interval_ablation",
                "raw_without_commendation",
                "shuffled_policy_control",
                "wrong_policy_control",
            },
        )

    @staticmethod
    def _write_fixture(run_dir: Path) -> None:
        environment = _environment_provenance_at_head()
        metadata = {
            "artifact_id": "fixture",
            "artifact_schema_version": 8,
            "holdout_accessed": False,
            "protocol_status": "draft_validation_holdout_locked",
            "protocol_version": "fixture",
            "run_purpose": "validation",
            "scenario_count": 1,
            "provenance": {
                "git_commit": "HEAD",
                "git_dirty": False,
                "source_sha256": _complete_source_hashes(),
                **environment,
            },
        }
        (run_dir / "metadata.json").write_text(
            json.dumps(metadata, indent=2) + "\n", encoding="utf-8"
        )
        (run_dir / "README.md").write_text("fixture\n", encoding="utf-8")
        predictions = [
            {
                "scenario_id": "s1",
                "employee_id": "E1",
                "method": "deterministic_policy_rules",
                "representation": "true_policy_checks",
                "operating_point": "rules_fixed",
                "score": "1.0",
                "predicted_anomaly": "True",
                "ground_truth_anomaly": "True",
                "labels": "inconsistent_dates",
            },
            {
                "scenario_id": "s1",
                "employee_id": "E2",
                "method": "deterministic_policy_rules",
                "representation": "true_policy_checks",
                "operating_point": "rules_fixed",
                "score": "0.0",
                "predicted_anomaly": "False",
                "ground_truth_anomaly": "False",
                "labels": "clean",
            },
        ]
        ProtocolArtifactAuditTests._write_csv(run_dir / "record_predictions.csv", predictions)
        metrics = [{
            "scenario_id": "s1",
            "method": "deterministic_policy_rules",
            "representation": "true_policy_checks",
            "operating_point": "rules_fixed",
            "evaluation_count": 2,
            "positive_count": 1,
            "negative_count": 1,
            "alert_count": 1,
            "true_positives": 1,
            "false_positives": 0,
            "true_negatives": 1,
            "false_negatives": 0,
            "precision": 1.0,
            "recall": 1.0,
            "f1": 1.0,
            "false_positive_rate": 0.0,
            "alert_rate": 0.5,
            "rare_legitimate_count": 0,
            "rare_legitimate_flagged": 0,
            "rare_legitimate_flagged_rate": 0.0,
            "ordinary_clean_count": 1,
            "ordinary_clean_flagged": 0,
            "ordinary_clean_flagged_rate": 0.0,
            "average_precision": 1.0,
            "anomalies_found_per_100_reviews": 100.0,
            "rare_legitimate_reviews_per_1000_employees": 0.0,
            "missed_anomalies_per_1000_employees": 0.0,
        }]
        ProtocolArtifactAuditTests._write_csv(run_dir / "scenario_metrics.csv", metrics)
        aggregate = [{
            "method": "deterministic_policy_rules",
            "representation": "true_policy_checks",
            "operating_point": "rules_fixed",
            "scenario_count": 1,
            **{f"{column}_total": metrics[0][column] for column in (
                "evaluation_count", "positive_count", "negative_count", "alert_count",
                "true_positives", "false_positives", "true_negatives", "false_negatives",
                "rare_legitimate_count", "rare_legitimate_flagged",
                "ordinary_clean_count", "ordinary_clean_flagged",
            )},
            **{f"{column}_mean": metrics[0][column] for column in (
                "precision", "recall", "f1", "false_positive_rate", "alert_rate",
                "rare_legitimate_flagged_rate", "ordinary_clean_flagged_rate",
                "anomalies_found_per_100_reviews",
                "rare_legitimate_reviews_per_1000_employees",
                "missed_anomalies_per_1000_employees",
            )},
            "average_precision_mean": 1.0,
        }]
        ProtocolArtifactAuditTests._write_csv(run_dir / "aggregate_metrics.csv", aggregate)
        ProtocolArtifactAuditTests._write_csv(
            run_dir / "scenario_configs.csv", [{"scenario_id": "s1"}]
        )
        for name in ("paired_comparisons.csv", "robustness_slices.csv", "utility_sensitivity.csv"):
            (run_dir / name).write_text("fixture\n", encoding="utf-8")
        ProtocolArtifactAuditTests._rewrite_manifest(run_dir)

    @staticmethod
    def _rewrite_manifest(run_dir: Path) -> None:
        files = {
            path.name: sha256(path.read_bytes()).hexdigest()
            for path in run_dir.iterdir()
            if path.is_file() and path.name != "manifest.json"
        }
        (run_dir / "manifest.json").write_text(
            json.dumps({"algorithm": "sha256", "files": files}, indent=2) + "\n",
            encoding="utf-8",
        )

    @staticmethod
    def _write_csv(path: Path, rows: list[dict[str, object]]) -> None:
        with path.open("w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
            writer.writeheader()
            writer.writerows(rows)


if __name__ == "__main__":
    unittest.main()

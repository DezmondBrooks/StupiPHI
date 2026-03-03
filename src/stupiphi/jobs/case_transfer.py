"""Case-based DB-to-DB sanitized slice transfer orchestration."""
from __future__ import annotations

import json
import os
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any, Callable, Dict, List, Optional

from stupiphi.connectors.postgres import get_prod_client, get_dev_client, PostgresClient
from stupiphi.slice.extract_case_slice import extract_case_slice
from stupiphi.slice.map_to_canonical import case_slice_to_canonical_records
from stupiphi.slice.replay_case_slice import replay_case_slice
from stupiphi.sanitizer.pipeline import PipelineConfig, SanitizationPipeline, SanitizeResult
from stupiphi.verification.db_verify import DEFAULT_TABLES, verify_dev_db


class VerificationFailedError(Exception):
    """Raised when --fail-on-verification is set and one or more records failed verification.

    Message is safe (counts only, no PHI).
    """


class DBVerificationFailedError(Exception):
    """Raised when --fail-on-db-verify is set and dev DB verification found residual patterns.

    Message is safe (counts only, no PHI).
    """


_TRANSFER_ALLOW_ENV = "STUPIPHI_ALLOW_PROD_TO_DEV"


def _ensure_transfer_allowed() -> None:
    """Guardrail: require explicit opt-in before running transfer-case.

    This is a coarse-grained safety check to avoid accidentally running
    prod-to-dev transfers in the wrong environment. To allow transfers,
    set environment variable STUPIPHI_ALLOW_PROD_TO_DEV=true (or 1/yes).
    """
    val = os.getenv(_TRANSFER_ALLOW_ENV, "")
    if val.lower() not in {"1", "true", "yes"}:
        raise RuntimeError(
            "Prod-to-dev transfer is disabled by default. To enable, set "
            f"{_TRANSFER_ALLOW_ENV}=true in the environment where you run transfer-case."
        )


def _now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


@dataclass(frozen=True)
class TransferReport:
    case_id: int
    rows_extracted: Dict[str, int]
    rows_inserted: Dict[str, int]
    verification_failures: int
    audit_events: int
    replay_skipped: bool = False
    replay_skip_reason: Optional[str] = None  # "dry_run" | "verification_failed"
    started_at: Optional[str] = None
    finished_at: Optional[str] = None
    config_path: Optional[str] = None  # safe: path only, no contents
    db_verification_ok: bool = True
    db_findings_count: int = 0
    db_findings_by_table: Dict[str, int] = field(default_factory=dict)
    db_findings_by_column: Dict[str, int] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, object]:
        """JSON-serializable dict; no PHI. Datetimes as ISO strings."""
        d = asdict(self)
        return d

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), indent=2)


def _write_report(report: TransferReport, path: str) -> None:
    with open(path, "w", encoding="utf-8") as f:
        f.write(report.to_json())


def _rows_extracted_from_slice(slice_dict: object) -> Dict[str, int]:
    if not isinstance(slice_dict, dict):
        return {}
    return {
        "patients": 1 if slice_dict.get("patient_row") else 0,
        "cases": 1 if slice_dict.get("case_row") else 0,
        "appointments": len(slice_dict.get("appointments_rows", []) or []),
        "therapists": len(slice_dict.get("therapist_rows", []) or []),
        "payments": len(slice_dict.get("payments_rows", []) or []),
    }


def run_case_transfer(
    case_id: int,
    config_path: Optional[str] = None,
    dry_run: bool = False,
    report_out: Optional[str] = None,
    audit_sink: Optional[Callable[[Dict[str, Any]], None]] = None,
    fail_on_verification: bool = False,
    verify_dev: bool = True,
    fail_on_db_verify: bool = False,
) -> TransferReport:
    """Run extract → sanitize → [replay unless dry_run or verification gating] → [verify dev DB if verify_dev].

    Does not log or return raw PHI. Audit data is only passed to the optional audit_sink
    (the tool does not store it). When fail_on_verification is True and any record fails
    verification, raises VerificationFailedError after optionally writing report. When
    fail_on_db_verify is True and dev DB verification finds patterns, raises DBVerificationFailedError.
    """
    _ensure_transfer_allowed()
    started_at = _now_iso()
    if config_path:
        pipeline = SanitizationPipeline.from_yaml(config_path)
    else:
        pipeline = SanitizationPipeline(PipelineConfig())

    prod_client: PostgresClient = get_prod_client()
    dev_client: PostgresClient = get_dev_client()

    try:
        slice_dict = extract_case_slice(case_id, prod_client)
        records = case_slice_to_canonical_records(slice_dict)

        sanitized_results: List[SanitizeResult] = []
        verification_failures = 0

        for rec in records:
            res = pipeline.sanitize_record(rec, audit_sink=audit_sink)
            sanitized_results.append(res)
            if not res.verification_ok:
                verification_failures += 1

        rows_extracted = _rows_extracted_from_slice(slice_dict)

        # Verification gating: abort before replay, still write artifacts if requested
        if fail_on_verification and verification_failures > 0:
            report = TransferReport(
                case_id=case_id,
                rows_extracted=rows_extracted,
                rows_inserted={k: 0 for k in rows_extracted},
                verification_failures=verification_failures,
                audit_events=len(sanitized_results),
                replay_skipped=True,
                replay_skip_reason="verification_failed",
                started_at=started_at,
                finished_at=_now_iso(),
                config_path=config_path,
                db_verification_ok=True,
                db_findings_count=0,
                db_findings_by_table={},
                db_findings_by_column={},
            )
            if report_out:
                _write_report(report, report_out)
            raise VerificationFailedError(
                f"Verification failed for {verification_failures} record(s); replay skipped."
            )

        # Dry-run: skip replay, write artifacts if requested
        if dry_run:
            report = TransferReport(
                case_id=case_id,
                rows_extracted=rows_extracted,
                rows_inserted={k: 0 for k in rows_extracted},
                verification_failures=verification_failures,
                audit_events=len(sanitized_results),
                replay_skipped=True,
                replay_skip_reason="dry_run",
                started_at=started_at,
                finished_at=_now_iso(),
                config_path=config_path,
                db_verification_ok=True,
                db_findings_count=0,
                db_findings_by_table={},
                db_findings_by_column={},
            )
            if report_out:
                _write_report(report, report_out)
            return report

        replay_case_slice(
            case_id,
            dev_client,
            sanitized_results,
            slice_dict,
            database_policy=getattr(pipeline.cfg, "database_policy", None),
            pseudonym_salt=pipeline.cfg.pseudonym_salt,
            placeholders=getattr(pipeline.cfg, "database_policy_placeholders", None),
        )

        db_ok = True
        db_findings_count = 0
        db_findings_by_table: Dict[str, int] = {}
        db_findings_by_column: Dict[str, int] = {}
        if verify_dev:
            db_result = verify_dev_db(dev_client, tables=DEFAULT_TABLES)
            db_ok = db_result.ok
            db_findings_count = db_result.findings_count
            db_findings_by_table = db_result.findings_by_table
            db_findings_by_column = db_result.findings_by_column
            if fail_on_db_verify and not db_ok:
                report = TransferReport(
                    case_id=case_id,
                    rows_extracted=rows_extracted,
                    rows_inserted=dict(rows_extracted),
                    verification_failures=verification_failures,
                    audit_events=len(sanitized_results),
                    replay_skipped=False,
                    replay_skip_reason=None,
                    started_at=started_at,
                    finished_at=_now_iso(),
                    config_path=config_path,
                    db_verification_ok=db_ok,
                    db_findings_count=db_findings_count,
                    db_findings_by_table=db_findings_by_table,
                    db_findings_by_column=db_findings_by_column,
                )
                if report_out:
                    _write_report(report, report_out)
                raise DBVerificationFailedError(
                    f"DB verification found {db_findings_count} finding(s) in dev DB; failing."
                )

        report = TransferReport(
            case_id=case_id,
            rows_extracted=rows_extracted,
            rows_inserted=dict(rows_extracted),
            verification_failures=verification_failures,
            audit_events=len(sanitized_results),
            replay_skipped=False,
            replay_skip_reason=None,
            started_at=started_at,
            finished_at=_now_iso(),
            config_path=config_path,
            db_verification_ok=db_ok,
            db_findings_count=db_findings_count,
            db_findings_by_table=db_findings_by_table,
            db_findings_by_column=db_findings_by_column,
        )
        if report_out:
            _write_report(report, report_out)
        return report
    finally:
        prod_client.close()
        dev_client.close()


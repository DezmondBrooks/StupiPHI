"""Case-based DB-to-DB sanitized slice transfer orchestration."""
from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Dict, List, Optional

from stupiphi.audit.audit_log import to_dict as audit_to_dict
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


def _write_audit_jsonl(sanitized_results: List[SanitizeResult], path: str) -> None:
    """Write one JSON object per line: audit event + record_id, verification_ok, verification_issues (generic only)."""
    with open(path, "w", encoding="utf-8") as f:
        for res in sanitized_results:
            obj = {
                **audit_to_dict(res.audit_event),
                "record_id": res.record.record_id,
                "verification_ok": res.verification_ok,
                "verification_issues": list(res.verification_issues),
            }
            f.write(json.dumps(obj, ensure_ascii=False) + "\n")


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
    audit_out: Optional[str] = None,
    fail_on_verification: bool = False,
    verify_dev: bool = True,
    fail_on_db_verify: bool = False,
) -> TransferReport:
    """Run extract → sanitize → [replay unless dry_run or verification gating] → [verify dev DB if verify_dev].

    Does not log or return raw PHI. When fail_on_verification is True and
    any record fails verification, raises VerificationFailedError after
    optionally writing report/audit artifacts. When fail_on_db_verify is True
    and dev DB verification finds patterns, raises DBVerificationFailedError.
    """
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
            res = pipeline.sanitize_record(rec)
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
            if audit_out:
                _write_audit_jsonl(sanitized_results, audit_out)
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
            if audit_out:
                _write_audit_jsonl(sanitized_results, audit_out)
            return report

        replay_case_slice(
            case_id,
            dev_client,
            sanitized_results,
            slice_dict,
            database_policy=getattr(pipeline.cfg, "database_policy", None),
            pseudonym_salt=pipeline.cfg.pseudonym_salt,
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
                if audit_out:
                    _write_audit_jsonl(sanitized_results, audit_out)
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
        if audit_out:
            _write_audit_jsonl(sanitized_results, audit_out)
        return report
    finally:
        prod_client.close()
        dev_client.close()


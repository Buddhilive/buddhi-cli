"""Intent promoter: drains queues, executes 6-gate validation, lands files, writes evidence and accounts."""

from __future__ import annotations

import hashlib
import json
import time
from pathlib import Path

from buddhi.scripts.autoharness.atomic import atomic_write_text
from buddhi.scripts.autoharness.intent_queue import clear_queue, read_intents
from buddhi.scripts.autoharness.layer import (
    resolve_autoharness_dir,
    resolve_layer_root,
    resolve_skills_dir,
)
from buddhi.scripts.autoharness.ledger import append_ledger
from buddhi.scripts.autoharness.lock import file_lock
from buddhi.scripts.autoharness.models import RunAccount, SidecarData
from buddhi.scripts.autoharness.redact import redact_text
from buddhi.scripts.autoharness.sidecar import (
    is_agent_created,
    read_sidecar,
    write_sidecar,
)
from buddhi.scripts.autoharness.skill_store import (
    apply_delta,
    archive_skill,
    exists,
    read_body,
    remove_subfile,
    sweep_orphans,
    write_body,
    write_subfile,
)
from buddhi.scripts.autoharness.validate import validate_skill_candidate


def materialize_evidence(evidence_text: str) -> tuple[str, str]:
    """Redact evidence and return (relative_subfile_path, redacted_content)."""
    redacted = redact_text(evidence_text).strip() + "\n"
    sha = hashlib.sha256(redacted.encode("utf-8")).hexdigest()
    rel_path = f"references/evidence-{sha}.md"
    return rel_path, redacted


def drain_and_promote(
    layer: str = "project",
    run_id: str = "interactive",
    project_root: Path | None = None,
) -> RunAccount:
    """Drain queued intents, validate through 6 gates, land mutations atomically, and write run account."""
    layer_root = resolve_layer_root(layer, project_root)
    skills_dir = resolve_skills_dir(layer, project_root)
    autoharness_dir = resolve_autoharness_dir(layer, project_root)
    drain_lock_file = autoharness_dir / "drain.lock"

    account = RunAccount(
        run_id=run_id,
        timestamp=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    )

    with file_lock(drain_lock_file, timeout_seconds=15.0):
        sweep_orphans(skills_dir)
        intents = read_intents(layer, run_id, project_root)
        if not intents:
            clear_queue(layer, run_id, project_root)
            return account

        for intent in intents:
            skill_dir = skills_dir / intent.name
            target_exists = exists(skills_dir, intent.name)
            target_agent_created = (
                is_agent_created(skill_dir) if target_exists else False
            )

            # Assemble candidate body for validation
            candidate_body: str | None = None
            if intent.action in ("create", "update"):
                candidate_body = intent.body
            elif intent.action == "patch":
                curr_body = read_body(skills_dir, intent.name)
                if (
                    curr_body is not None
                    and intent.old_string is not None
                    and intent.new_string is not None
                ):
                    try:
                        candidate_body = apply_delta(
                            curr_body, intent.old_string, intent.new_string
                        )
                    except ValueError as exc:
                        account.rejected.append(
                            {"name": intent.name, "reason": str(exc), "gate": "patch"}
                        )
                        continue
                else:
                    account.rejected.append(
                        {
                            "name": intent.name,
                            "reason": "Missing body or patch string",
                            "gate": "patch",
                        }
                    )
                    continue
            elif intent.action == "remove_file":
                candidate_body = read_body(skills_dir, intent.name)

            # Materialize evidence subfile
            evidence_rel_path: str = ""
            if intent.action != "delete" and intent.evidence:
                evidence_rel_path, evidence_content = materialize_evidence(
                    intent.evidence
                )
                intent.files[evidence_rel_path] = evidence_content

            # Validate through 6 gates
            val_res = validate_skill_candidate(
                intent=intent,
                assembled_body=candidate_body,
                target_is_agent_created=target_agent_created,
                target_exists=target_exists,
                layer_root=layer_root,
            )

            if not val_res.valid:
                first_finding = val_res.findings[0]
                account.rejected.append(
                    {
                        "name": intent.name,
                        "gate": first_finding.gate,
                        "code": first_finding.code,
                        "reason": first_finding.message,
                    }
                )
                continue

            # Land mutations
            if intent.action == "delete":
                archive_skill(skills_dir, intent.name)
                append_ledger(
                    skill_dir,
                    "delete",
                    intent.reason,
                    "",
                    absorbed_into=intent.absorbed_into,
                )
                account.landed.append(intent.name)
                continue

            if intent.action == "create":
                write_body(skills_dir, intent.name, candidate_body or "")
                for rel_p, sub_content in intent.files.items():
                    write_subfile(skill_dir, rel_p, sub_content)

                write_sidecar(
                    skill_dir,
                    SidecarData(
                        created_by="agent",
                        use=0,
                        view=0,
                        patch=0,
                        anchor=int(time.time()),
                    ),
                )
                append_ledger(skill_dir, "create", intent.reason, evidence_rel_path)
                account.landed.append(intent.name)

            elif intent.action in ("update", "patch"):
                write_body(skills_dir, intent.name, candidate_body or "")
                for rel_p, sub_content in intent.files.items():
                    write_subfile(skill_dir, rel_p, sub_content)

                sidecar = read_sidecar(skill_dir) or SidecarData(created_by="agent")
                sidecar.patch += 1
                write_sidecar(skill_dir, sidecar)
                append_ledger(
                    skill_dir, intent.action, intent.reason, evidence_rel_path
                )
                account.landed.append(intent.name)

            elif intent.action == "remove_file":
                for rel_p in intent.files:
                    remove_subfile(skill_dir, rel_p)

                sidecar = read_sidecar(skill_dir) or SidecarData(created_by="agent")
                sidecar.patch += 1
                write_sidecar(skill_dir, sidecar)
                append_ledger(
                    skill_dir, "remove_file", intent.reason, evidence_rel_path
                )
                account.landed.append(intent.name)

        clear_queue(layer, run_id, project_root)

        # Write run account files
        runs_dir = autoharness_dir / "runs"
        runs_dir.mkdir(parents=True, exist_ok=True)
        run_file = runs_dir / f"{run_id}.json"
        last_run_file = autoharness_dir / "last_run.json"

        run_payload = {
            "run_id": account.run_id,
            "timestamp": account.timestamp,
            "landed": account.landed,
            "rejected": account.rejected,
            "spawn_error": account.spawn_error,
        }
        raw_run = json.dumps(run_payload, indent=2)
        atomic_write_text(run_file, raw_run)
        atomic_write_text(last_run_file, raw_run)

    return account

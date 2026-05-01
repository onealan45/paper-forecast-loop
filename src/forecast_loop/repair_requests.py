from __future__ import annotations

from dataclasses import replace
from datetime import datetime

from forecast_loop.models import RepairRequest
from forecast_loop.storage import ArtifactRepository


FINAL_REPAIR_REQUEST_STATUSES = {"resolved", "ignored"}


def update_repair_request_status(
    *,
    repository: ArtifactRepository,
    repair_request_id: str,
    status: str,
    reason: str,
    updated_at: datetime,
) -> RepairRequest:
    normalized_status = status.lower()
    if normalized_status not in FINAL_REPAIR_REQUEST_STATUSES:
        allowed = ", ".join(sorted(FINAL_REPAIR_REQUEST_STATUSES))
        raise ValueError(f"unsupported repair request status: {status}. Supported statuses: {allowed}.")
    if not reason.strip():
        raise ValueError("repair request status reason is required")

    repair_requests = repository.load_repair_requests()
    updated_requests: list[RepairRequest] = []
    updated: RepairRequest | None = None
    for request in repair_requests:
        if request.repair_request_id == repair_request_id:
            updated = replace(
                request,
                status=normalized_status,
                status_updated_at=updated_at,
                status_reason=reason.strip(),
            )
            updated_requests.append(updated)
        else:
            updated_requests.append(request)

    if updated is None:
        raise ValueError(f"repair request not found: {repair_request_id}")

    repository.replace_repair_requests(updated_requests)
    return updated

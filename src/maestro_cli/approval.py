"""
Approval Manager - Human-in-the-loop validation system for Maestro CLI.
"""

from typing import Dict, Any, Optional
from datetime import datetime
from enum import Enum
import dataclasses
import uuid
import time


class ApprovalStatus(str, Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    SKIPPED = "skipped"


@dataclasses.dataclass
class ApprovalRequest:
    request_id: str
    step_name: str
    action: str
    description: str
    status: ApprovalStatus = ApprovalStatus.PENDING
    approved_by: Optional[str] = None
    rejection_reason: Optional[str] = None


class ApprovalManager:
    """Manages human-in-the-loop approval requests before executing critical operations."""

    def __init__(self):
        self.requests: Dict[str, ApprovalRequest] = {}

    def create_request(self, step_name: str, action: str, description: str) -> ApprovalRequest:
        req_id = f"approval_{int(time.time())}_{uuid.uuid4().hex[:6]}"
        req = ApprovalRequest(
            request_id=req_id,
            step_name=step_name,
            action=action,
            description=description
        )
        self.requests[req_id] = req
        return req

    def approve(self, request_id: str, approved_by: str = "user") -> bool:
        if request_id in self.requests:
            self.requests[request_id].status = ApprovalStatus.APPROVED
            self.requests[request_id].approved_by = approved_by
            return True
        return False

    def reject(self, request_id: str, reason: str = "Rejected by user") -> bool:
        if request_id in self.requests:
            self.requests[request_id].status = ApprovalStatus.REJECTED
            self.requests[request_id].rejection_reason = reason
            return True
        return False

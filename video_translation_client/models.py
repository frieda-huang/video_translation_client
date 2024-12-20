from enum import Enum
from pydantic import BaseModel


class JobStatus(str, Enum):
    pending = "pending"
    completed = "completed"
    error = "error"


class StatusResponse(BaseModel):
    status: JobStatus
    raw_response: dict
    elapsed_time: float


class StatusPollingConfig(BaseModel):
    initial_delay: float = 1.0
    max_delay: float = 32.0
    backoff_factor: float = 2.0
    max_attempts: int = 10
    timeout: float = 300.0  # 5 minutes
    jitter: bool = True

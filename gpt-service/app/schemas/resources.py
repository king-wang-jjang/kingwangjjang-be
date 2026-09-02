from datetime import datetime
from typing import Literal

from pydantic import BaseModel

from app.schemas.nodes import AINodeResponse


ResourceStatus = Literal["healthy", "busy", "overloaded", "unavailable"]
CapabilityStatus = Literal["healthy", "busy", "saturated", "unavailable"]


class AIResourceCapacityResponse(BaseModel):
    configured_capacity: int
    effective_capacity: int
    active_requests: int
    available_capacity: int
    utilization_percent: float
    peak_in_flight: int


class AIResourceTrafficResponse(BaseModel):
    total_requests: int
    successful_requests: int
    failed_requests: int
    capacity_rejected_requests: int
    spillover_requests: int
    recent_requests: int
    recent_successes: int
    recent_failures: int
    recent_capacity_rejections: int
    recent_spillovers: int


class AICapabilityResourceResponse(BaseModel):
    capability: Literal["analysis", "chat", "vision"]
    enabled_nodes: int
    effective_capacity: int
    active_requests: int
    available_capacity: int
    status: CapabilityStatus


class AINodeRuntimeResponse(BaseModel):
    in_flight: int
    configured_capacity: int
    effective_capacity: int
    available_capacity: int
    utilization_percent: float
    saturated: bool
    attempts: int
    successful_attempts: int
    failed_attempts: int
    request_rejections: int
    capacity_rejections: int
    peak_in_flight: int


class AIResourceNodeResponse(AINodeResponse):
    runtime: AINodeRuntimeResponse


class AIResourceOverviewResponse(BaseModel):
    generated_at: datetime
    metrics_started_at: datetime
    status: ResourceStatus
    is_overloaded: bool
    window_seconds: int
    capacity: AIResourceCapacityResponse
    traffic: AIResourceTrafficResponse
    capabilities: list[AICapabilityResourceResponse]
    nodes: list[AIResourceNodeResponse]

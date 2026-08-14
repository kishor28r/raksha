"""
RAKSHA: AI-Powered Emergency Response & Resource Allocation System
Data Models and Pydantic Schemas
"""

from enum import Enum
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field
import time
import uuid


class IncidentType(str, Enum):
    FIRE = "FIRE"
    FLOOD = "FLOOD"
    ACCIDENT = "ACCIDENT"
    MEDICAL_TRAUMA = "MEDICAL_TRAUMA"
    BUILDING_COLLAPSE = "BUILDING_COLLAPSE"
    GAS_LEAK = "GAS_LEAK"
    HAZMAT = "HAZMAT"


class UnitType(str, Enum):
    AMBULANCE = "AMBULANCE"
    FIRE_TRUCK = "FIRE_TRUCK"
    RESCUE_SQUAD = "RESCUE_SQUAD"
    POLICE_PATROL = "POLICE_PATROL"
    MULTI_HAZARD = "MULTI_HAZARD"


class UnitStatus(str, Enum):
    AVAILABLE = "AVAILABLE"
    EN_ROUTE = "EN_ROUTE"
    ON_SCENE = "ON_SCENE"
    RETURNING = "RETURNING"


class SeverityLevel(str, Enum):
    CRITICAL = "CRITICAL"    # 0.75 - 1.00
    HIGH = "HIGH"            # 0.55 - 0.74
    MEDIUM = "MEDIUM"        # 0.35 - 0.54
    LOW = "LOW"              # 0.00 - 0.34


class IncidentSource(str, Enum):
    CITIZEN_SOS = "CITIZEN_SOS"
    CCTV_AI_DETECTION = "CCTV_AI_DETECTION"
    IOT_SENSOR = "IOT_SENSOR"
    BYSTANDER_CALL_112 = "BYSTANDER_CALL_112"


class IncidentStatus(str, Enum):
    REPORTED = "REPORTED"
    ASSIGNED = "ASSIGNED"
    IN_PROGRESS = "IN_PROGRESS"
    RESOLVED = "RESOLVED"


class Location(BaseModel):
    lat: float
    lng: float
    address: Optional[str] = ""


class SeverityBreakdown(BaseModel):
    life_threat_score: float = Field(..., description="Score for direct threat to life (0-1)")
    casualty_score: float = Field(..., description="Score based on casualty scale (0-1)")
    vulnerability_score: float = Field(..., description="Score for high-risk demographics/locations (0-1)")
    time_urgency_score: float = Field(..., description="Score based on time sensitivity and escalation (0-1)")
    final_score: float = Field(..., description="Weighted composite score (0-1)")
    level: SeverityLevel = Field(..., description="Category label")
    explanation: str = Field(..., description="Human-readable explanation of the score calculation")
    extracted_casualties: int = Field(default=0, description="Casualties extracted from NLP analysis")
    vulnerable_groups_found: List[str] = Field(default_factory=list, description="List of detected vulnerable keywords")


class IncidentCreate(BaseModel):
    title: str = Field(..., example="Commercial Complex Fire with Trapped People")
    type: IncidentType = Field(..., example=IncidentType.FIRE)
    description: str = Field(..., example="Massive fire on 3rd floor. Smoke spreading rapidly. 4 people trapped including 1 elderly person.")
    location: Location
    source: IncidentSource = IncidentSource.CITIZEN_SOS
    reported_casualties: Optional[int] = None
    has_vulnerable_groups: Optional[bool] = None


class Incident(BaseModel):
    id: str = Field(default_factory=lambda: f"INC-{uuid.uuid4().hex[:6].upper()}")
    title: str
    type: IncidentType
    description: str
    location: Location
    source: IncidentSource = IncidentSource.CITIZEN_SOS
    status: IncidentStatus = IncidentStatus.REPORTED
    severity: SeverityBreakdown
    created_at: float = Field(default_factory=time.time)
    assigned_unit_id: Optional[str] = None
    assigned_at: Optional[float] = None
    resolved_at: Optional[float] = None


class Unit(BaseModel):
    id: str = Field(default_factory=lambda: f"UNT-{uuid.uuid4().hex[:4].upper()}")
    name: str = Field(..., example="Ambulance-Alpha-101")
    type: UnitType = Field(..., example=UnitType.AMBULANCE)
    status: UnitStatus = Field(default=UnitStatus.AVAILABLE)
    location: Location
    base_location: Location
    target_location: Optional[Location] = None
    speed_kmh: float = Field(default=50.0, description="Average response vehicle speed in km/h")
    capacity: int = Field(default=2, description="Patient/victim carriage or squad capacity")
    assigned_incident_id: Optional[str] = None
    dispatched_at: Optional[float] = None


class AllocationRecommendation(BaseModel):
    incident_id: str
    incident_title: str
    severity_level: SeverityLevel
    severity_score: float
    unit_id: str
    unit_name: str
    unit_type: UnitType
    distance_km: float
    eta_minutes: float
    cost_score: float
    match_confidence_pct: int
    reasoning: str


class OptimizationResult(BaseModel):
    allocations: List[AllocationRecommendation]
    unassigned_incidents: List[str]
    available_units_remaining: List[str]
    total_estimated_response_time_min: float
    algorithm_used: str = "Hungarian Algorithm (Linear Sum Assignment) + Priority Cost Matrix"
    timestamp: float = Field(default_factory=time.time)


class DispatchOverrideRequest(BaseModel):
    incident_id: str
    unit_id: str
    reason: Optional[str] = "Dispatcher Manual Override"

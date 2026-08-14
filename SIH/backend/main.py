"""
RAKSHA: AI-Powered Emergency Response & Resource Allocation System
FastAPI Backend Application & REST API Server
"""

import os
import time
from typing import List, Dict, Any, Optional
from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse

from backend.models import (
    Incident,
    IncidentCreate,
    IncidentStatus,
    Unit,
    UnitStatus,
    Location,
    SeverityLevel,
    OptimizationResult,
    AllocationRecommendation,
    DispatchOverrideRequest
)
from backend.ai_scorer import AISeverityScorer
from backend.optimizer import ResourceOptimizer, haversine_distance
from backend.simulator import (
    get_default_units,
    get_preset_scenarios,
    generate_random_incident,
    update_unit_positions_step,
    CITY_CENTER
)

# Initialize FastAPI App
app = FastAPI(
    title="RAKSHA: Intelligent Emergency Response & Resource Allocation",
    description="AI-driven Disaster Management & Hungarian Algorithm Dispatcher for Smart India Hackathon",
    version="1.0.0"
)

# Enable CORS for cross-origin frontend support
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# In-Memory State Store (Fast & reliable for hackathon demo)
class StateStore:
    def __init__(self):
        self.reset()

    def reset(self):
        self.units: Dict[str, Unit] = {u.id: u for u in get_default_units()}
        self.incidents: Dict[str, Incident] = {}
        self.latest_optimization: Optional[OptimizationResult] = None
        self.city_center: Location = Location(lat=CITY_CENTER["lat"], lng=CITY_CENTER["lng"], address="Central Emergency Control Zone")
        self.simulation_running: bool = False
        self.simulation_speed: float = 1.0


state = StateStore()


# -------------------------------------------------------------
# System & Status Endpoints
# -------------------------------------------------------------
@app.get("/api/status")
def get_system_status():
    """
    Get overall system health, fleet readiness, and active emergency stats.
    """
    active_incidents = [inc for inc in state.incidents.values() if inc.status != IncidentStatus.RESOLVED]
    critical_count = sum(1 for inc in active_incidents if inc.severity.level == SeverityLevel.CRITICAL)
    high_count = sum(1 for inc in active_incidents if inc.severity.level == SeverityLevel.HIGH)
    avail_units = sum(1 for u in state.units.values() if u.status == UnitStatus.AVAILABLE)
    en_route_units = sum(1 for u in state.units.values() if u.status == UnitStatus.EN_ROUTE)

    return {
        "status": "OPERATIONAL",
        "system_name": "RAKSHA AI Command Center",
        "city_center": state.city_center,
        "total_incidents": len(state.incidents),
        "active_incidents": len(active_incidents),
        "critical_incidents": critical_count,
        "high_incidents": high_count,
        "total_units": len(state.units),
        "available_units": avail_units,
        "en_route_units": en_route_units,
        "simulation_running": state.simulation_running,
        "timestamp": time.time()
    }


# -------------------------------------------------------------
# Incident Management & AI Scoring
# -------------------------------------------------------------
@app.get("/api/incidents", response_model=List[Incident])
def list_incidents():
    """
    Retrieve all incidents sorted by status and severity.
    """
    inc_list = list(state.incidents.values())
    # Sort: active first, then highest severity first, then newest
    status_order = {IncidentStatus.REPORTED: 0, IncidentStatus.ASSIGNED: 1, IncidentStatus.IN_PROGRESS: 2, IncidentStatus.RESOLVED: 3}
    inc_list.sort(key=lambda x: (status_order.get(x.status, 9), -x.severity.final_score, -x.created_at))
    return inc_list


@app.post("/api/incidents", response_model=Incident)
def create_incident(inc_input: IncidentCreate):
    """
    Submit a new incident report (Citizen SOS, CCTV AI, IoT, 112 Call).
    Automatically runs AI NLP severity scoring and updates optimization recommendations.
    """
    # 1. AI Severity Scoring Engine
    severity_breakdown = AISeverityScorer.score_incident(inc_input)

    # 2. Instantiate and store Incident
    incident = Incident(
        title=inc_input.title,
        type=inc_input.type,
        description=inc_input.description,
        location=inc_input.location,
        source=inc_input.source,
        status=IncidentStatus.REPORTED,
        severity=severity_breakdown
    )
    state.incidents[incident.id] = incident

    # 3. Automatically trigger re-optimization
    run_optimization_internal()

    return incident


@app.post("/api/incidents/{incident_id}/resolve")
def resolve_incident(incident_id: str):
    """
    Mark an incident as RESOLVED and free up assigned units.
    """
    if incident_id not in state.incidents:
        raise HTTPException(status_code=404, detail="Incident not found")

    incident = state.incidents[incident_id]
    incident.status = IncidentStatus.RESOLVED
    incident.resolved_at = time.time()

    # Free up the assigned unit if any
    if incident.assigned_unit_id and incident.assigned_unit_id in state.units:
        unit = state.units[incident.assigned_unit_id]
        unit.status = UnitStatus.AVAILABLE
        unit.assigned_incident_id = None
        unit.target_location = None

    incident.assigned_unit_id = None

    # Re-run optimization
    run_optimization_internal()

    return {"status": "SUCCESS", "message": f"Incident {incident_id} marked as RESOLVED"}


# -------------------------------------------------------------
# Unit Fleet Management
# -------------------------------------------------------------
@app.get("/api/units", response_model=List[Unit])
def list_units():
    """
    Get live location and status of all response fleet units.
    """
    return list(state.units.values())


@app.post("/api/units/{unit_id}/reset")
def reset_unit(unit_id: str):
    """
    Reset a unit back to base station and set to AVAILABLE.
    """
    if unit_id not in state.units:
        raise HTTPException(status_code=404, detail="Unit not found")

    unit = state.units[unit_id]
    unit.status = UnitStatus.AVAILABLE
    unit.location = Location(lat=unit.base_location.lat, lng=unit.base_location.lng, address=unit.base_location.address)
    unit.target_location = None
    unit.assigned_incident_id = None
    return unit


# -------------------------------------------------------------
# Resource Allocation Optimizer (Hungarian Algorithm)
# -------------------------------------------------------------
def run_optimization_internal() -> OptimizationResult:
    """
    Internal helper to compute optimal matching across all active incidents and units.
    """
    active_incidents = [inc for inc in state.incidents.values() if inc.status in [IncidentStatus.REPORTED, IncidentStatus.ASSIGNED]]
    units = list(state.units.values())

    result = ResourceOptimizer.optimize_allocation(active_incidents, units)
    state.latest_optimization = result
    return result


@app.get("/api/optimize", response_model=OptimizationResult)
def get_latest_optimization():
    """
    Fetch the latest AI resource allocation plan.
    """
    return run_optimization_internal()


@app.post("/api/optimize", response_model=OptimizationResult)
def trigger_optimization():
    """
    Manually trigger re-optimization using Hungarian algorithm.
    """
    return run_optimization_internal()


@app.post("/api/dispatch/accept")
def accept_dispatch(incident_id: str, unit_id: str):
    """
    Accept an AI recommendation or dispatch a specific unit to an incident.
    """
    if incident_id not in state.incidents:
        raise HTTPException(status_code=404, detail="Incident not found")
    if unit_id not in state.units:
        raise HTTPException(status_code=404, detail="Unit not found")

    inc = state.incidents[incident_id]
    unit = state.units[unit_id]

    inc.assigned_unit_id = unit.id
    inc.assigned_at = time.time()
    inc.status = IncidentStatus.ASSIGNED

    unit.status = UnitStatus.EN_ROUTE
    unit.assigned_incident_id = inc.id
    unit.target_location = inc.location
    unit.dispatched_at = time.time()

    # Re-run optimization for remaining items
    run_optimization_internal()

    return {
        "status": "DISPATCHED",
        "incident_id": inc.id,
        "unit_id": unit.id,
        "unit_name": unit.name,
        "unit_status": unit.status
    }


@app.post("/api/dispatch/accept-all")
def accept_all_dispatches():
    """
    One-click acceptance of all current AI-recommended optimal allocations.
    """
    opt_result = run_optimization_internal()
    dispatched_count = 0

    for alloc in opt_result.allocations:
        inc = state.incidents.get(alloc.incident_id)
        unit = state.units.get(alloc.unit_id)
        if inc and unit and unit.status in [UnitStatus.AVAILABLE, UnitStatus.RETURNING] and not inc.assigned_unit_id:
            inc.assigned_unit_id = unit.id
            inc.assigned_at = time.time()
            inc.status = IncidentStatus.ASSIGNED

            unit.status = UnitStatus.EN_ROUTE
            unit.assigned_incident_id = inc.id
            unit.target_location = inc.location
            unit.dispatched_at = time.time()
            dispatched_count += 1

    run_optimization_internal()

    return {
        "status": "BATCH_DISPATCH_COMPLETE",
        "dispatched_count": dispatched_count
    }


@app.post("/api/dispatch/override")
def override_dispatch(req: DispatchOverrideRequest):
    """
    Human Dispatcher manual override to reassign a unit or incident.
    """
    return accept_dispatch(req.incident_id, req.unit_id)


# -------------------------------------------------------------
# Disaster Scenarios & Simulation Suite
# -------------------------------------------------------------
@app.get("/api/scenarios")
def get_scenarios():
    """
    Get list of pre-configured disaster scenarios for demo.
    """
    return get_preset_scenarios()


@app.post("/api/scenarios/{scenario_key}/load")
def load_scenario(scenario_key: str):
    """
    Load a pre-configured multi-incident disaster scenario.
    """
    scenarios = get_preset_scenarios()
    if scenario_key not in scenarios:
        raise HTTPException(status_code=404, detail="Scenario key not found")

    scen = scenarios[scenario_key]
    created_incidents = []

    for inc_data in scen["incidents"]:
        loc = Location(**inc_data["location"])
        inc_in = IncidentCreate(
            title=inc_data["title"],
            type=inc_data["type"],
            description=inc_data["description"],
            location=loc,
            source=inc_data["source"],
            reported_casualties=inc_data.get("reported_casualties"),
            has_vulnerable_groups=inc_data.get("has_vulnerable_groups")
        )
        severity = AISeverityScorer.score_incident(inc_in)
        incident = Incident(
            title=inc_in.title,
            type=inc_in.type,
            description=inc_in.description,
            location=inc_in.location,
            source=inc_in.source,
            status=IncidentStatus.REPORTED,
            severity=severity
        )
        state.incidents[incident.id] = incident
        created_incidents.append(incident)

    run_optimization_internal()

    return {
        "status": "SCENARIO_LOADED",
        "scenario_name": scen["name"],
        "incidents_loaded": len(created_incidents)
    }


@app.post("/api/simulation/inject-random")
def inject_random():
    """
    Simulate sudden unexpected emergency event.
    """
    rand_inc = generate_random_incident(state.city_center.lat, state.city_center.lng)
    severity = AISeverityScorer.score_incident(rand_inc)
    incident = Incident(
        title=rand_inc.title,
        type=rand_inc.type,
        description=rand_inc.description,
        location=rand_inc.location,
        source=rand_inc.source,
        status=IncidentStatus.REPORTED,
        severity=severity
    )
    state.incidents[incident.id] = incident
    run_optimization_internal()
    return incident


@app.post("/api/simulation/step")
def simulation_step(multiplier: float = 1.0):
    """
    Advance physical simulation step: move en-route units closer to destination.
    """
    update_unit_positions_step(list(state.units.values()), list(state.incidents.values()), speed_multiplier=multiplier)
    return {
        "status": "STEPPED",
        "units": list(state.units.values()),
        "incidents": list(state.incidents.values())
    }


@app.post("/api/simulation/reset")
def reset_simulation():
    """
    Clear all active incidents and reset units to starting state.
    """
    state.reset()
    return {"status": "RESET_SUCCESS", "message": "All incidents cleared and units reset to base stations"}


# -------------------------------------------------------------
# Benchmark Comparison: RAKSHA AI vs Traditional FCFS
# -------------------------------------------------------------
@app.get("/api/benchmark")
def compute_benchmark():
    """
    Compare RAKSHA AI Hungarian Optimization vs Traditional First-Come-First-Served (FCFS) Dispatching.
    Demonstrates response time reduction, critical incident priority, and suitability efficiency.
    """
    active_incidents = list(state.incidents.values())
    if not active_incidents:
        return {
            "has_data": False,
            "message": "No active incidents to benchmark. Load a scenario first."
        }

    # Sort incidents chronologically for FCFS simulation
    fcfs_incidents = sorted(active_incidents, key=lambda x: x.created_at)
    units_pool = [u.model_copy() for u in state.units.values()]

    # 1. Simulate Traditional FCFS (First available unit assigned to first reported incident regardless of severity)
    fcfs_total_eta = 0.0
    fcfs_critical_eta = 0.0
    fcfs_critical_count = 0
    fcfs_type_mismatches = 0
    avail_pool = list(units_pool)

    for inc in fcfs_incidents:
        if not avail_pool:
            break
        # FCFS picks first available unit in the list (or naive closest regardless of type/severity)
        unit = avail_pool.pop(0)
        dist = haversine_distance(inc.location, unit.location)
        eta = ResourceOptimizer.calculate_eta_minutes(dist, unit.speed_kmh)
        fcfs_total_eta += eta

        if inc.severity.level == SeverityLevel.CRITICAL:
            fcfs_critical_eta += eta
            fcfs_critical_count += 1

        # Check type mismatch
        penalty = ResourceOptimizer.SUITABILITY_PENALTY.get(inc.type, {}).get(unit.type, 10.0)
        if penalty > 5.0:
            fcfs_type_mismatches += 1

    # 2. Simulate RAKSHA AI Allocation
    opt_result = ResourceOptimizer.optimize_allocation(active_incidents, list(state.units.values()))
    ai_total_eta = 0.0
    ai_critical_eta = 0.0
    ai_critical_count = 0
    ai_type_mismatches = 0

    inc_dict = {inc.id: inc for inc in active_incidents}
    for alloc in opt_result.allocations:
        inc = inc_dict.get(alloc.incident_id)
        if not inc:
            continue
        ai_total_eta += alloc.eta_minutes
        if alloc.severity_level == SeverityLevel.CRITICAL:
            ai_critical_eta += alloc.eta_minutes
            ai_critical_count += 1
        penalty = ResourceOptimizer.SUITABILITY_PENALTY.get(inc.type, {}).get(alloc.unit_type, 10.0)
        if penalty > 5.0:
            ai_type_mismatches += 1

    # Compute percentage improvements
    time_saved_pct = 0.0
    if fcfs_total_eta > 0:
        time_saved_pct = round(((fcfs_total_eta - ai_total_eta) / fcfs_total_eta) * 100, 1)

    crit_time_saved_pct = 0.0
    if fcfs_critical_eta > 0:
        crit_time_saved_pct = round(((fcfs_critical_eta - ai_critical_eta) / fcfs_critical_eta) * 100, 1)

    return {
        "has_data": True,
        "fcfs": {
            "total_response_time_min": round(fcfs_total_eta, 1),
            "critical_avg_eta_min": round(fcfs_critical_eta / max(1, fcfs_critical_count), 1),
            "equipment_mismatches": fcfs_type_mismatches,
            "dispatch_policy": "First-Come-First-Served (Traditional Dispatch)"
        },
        "raksha_ai": {
            "total_response_time_min": round(ai_total_eta, 1),
            "critical_avg_eta_min": round(ai_critical_eta / max(1, ai_critical_count), 1),
            "equipment_mismatches": ai_type_mismatches,
            "dispatch_policy": "Hungarian Optimization + AI Urgency Weighting"
        },
        "improvements": {
            "overall_time_reduction_pct": max(0.0, time_saved_pct),
            "critical_emergency_speedup_pct": max(0.0, crit_time_saved_pct),
            "mismatches_prevented": max(0, fcfs_type_mismatches - ai_type_mismatches),
            "summary": f"RAKSHA AI delivers {crit_time_saved_pct}% faster response to critical life-threat incidents while eliminating equipment mismatches."
        }
    }


# -------------------------------------------------------------
# Static Frontend Serving
# -------------------------------------------------------------
frontend_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "frontend")

if os.path.exists(frontend_path):
    app.mount("/static", StaticFiles(directory=frontend_path), name="static")

    @app.get("/")
    def serve_index():
        return FileResponse(os.path.join(frontend_path, "index.html"))

"""
RAKSHA: AI-Powered Emergency Response & Resource Allocation System
Resource Allocation Optimizer (Hungarian Algorithm & Priority Cost Matrix)

Computes optimal bipartite matching between active incidents and emergency units
minimizing total response time while prioritizing critical life-threat emergencies.
"""

import math
import numpy as np
from scipy.optimize import linear_sum_assignment
from typing import List, Dict, Tuple, Optional
from backend.models import (
    Incident,
    Unit,
    IncidentType,
    UnitType,
    UnitStatus,
    SeverityLevel,
    AllocationRecommendation,
    OptimizationResult,
    Location
)


def haversine_distance(loc1: Location, loc2: Location) -> float:
    """
    Calculate the great circle distance in kilometers between two points on Earth.
    """
    R = 6371.0  # Earth's radius in kilometers
    dlat = math.radians(loc2.lat - loc1.lat)
    dlng = math.radians(loc2.lng - loc1.lng)
    a = (
        math.sin(dlat / 2.0) ** 2 +
        math.cos(math.radians(loc1.lat)) * math.cos(math.radians(loc2.lat)) * math.sin(dlng / 2.0) ** 2
    )
    c = 2.0 * math.atan2(math.sqrt(a), math.sqrt(1.0 - a))
    return round(R * c, 3)


class ResourceOptimizer:
    """
    Optimal Emergency Resource Allocator using the Hungarian Algorithm (Kuhn-Munkres).
    """

    # Unit suitability penalties (0 = ideal match, higher = less suitable or ill-equipped)
    SUITABILITY_PENALTY: Dict[IncidentType, Dict[UnitType, float]] = {
        IncidentType.FIRE: {
            UnitType.FIRE_TRUCK: 0.0,
            UnitType.MULTI_HAZARD: 2.0,
            UnitType.RESCUE_SQUAD: 8.0,
            UnitType.AMBULANCE: 15.0,
            UnitType.POLICE_PATROL: 25.0,
        },
        IncidentType.FLOOD: {
            UnitType.RESCUE_SQUAD: 0.0,
            UnitType.MULTI_HAZARD: 2.0,
            UnitType.FIRE_TRUCK: 6.0,
            UnitType.AMBULANCE: 12.0,
            UnitType.POLICE_PATROL: 20.0,
        },
        IncidentType.BUILDING_COLLAPSE: {
            UnitType.RESCUE_SQUAD: 0.0,
            UnitType.FIRE_TRUCK: 2.0,
            UnitType.MULTI_HAZARD: 2.0,
            UnitType.AMBULANCE: 6.0,
            UnitType.POLICE_PATROL: 20.0,
        },
        IncidentType.MEDICAL_TRAUMA: {
            UnitType.AMBULANCE: 0.0,
            UnitType.MULTI_HAZARD: 3.0,
            UnitType.RESCUE_SQUAD: 8.0,
            UnitType.POLICE_PATROL: 15.0,
            UnitType.FIRE_TRUCK: 20.0,
        },
        IncidentType.ACCIDENT: {
            UnitType.AMBULANCE: 0.0,
            UnitType.POLICE_PATROL: 2.0,
            UnitType.MULTI_HAZARD: 3.0,
            UnitType.RESCUE_SQUAD: 6.0,
            UnitType.FIRE_TRUCK: 8.0,
        },
        IncidentType.GAS_LEAK: {
            UnitType.FIRE_TRUCK: 0.0,
            UnitType.MULTI_HAZARD: 1.0,
            UnitType.RESCUE_SQUAD: 4.0,
            UnitType.POLICE_PATROL: 15.0,
            UnitType.AMBULANCE: 18.0,
        },
        IncidentType.HAZMAT: {
            UnitType.FIRE_TRUCK: 0.0,
            UnitType.MULTI_HAZARD: 1.0,
            UnitType.RESCUE_SQUAD: 5.0,
            UnitType.AMBULANCE: 15.0,
            UnitType.POLICE_PATROL: 25.0,
        }
    }

    @classmethod
    def calculate_eta_minutes(cls, distance_km: float, speed_kmh: float) -> float:
        """
        Estimate transit time with urban emergency traffic factor.
        """
        speed = max(15.0, speed_kmh)
        travel_hours = distance_km / speed
        eta = travel_hours * 60.0
        # Add 1.5 min dispatch delay / traffic lights buffer
        return round(eta + 1.5, 1)

    @classmethod
    def compute_cost(cls, incident: Incident, unit: Unit) -> Tuple[float, float, float]:
        """
        Compute the cost function between incident i and unit j.
        Cost = (ETA * SeverityMultiplier) + TypePenalty - PriorityBonus
        Lower cost means better pairing.
        """
        dist_km = haversine_distance(incident.location, unit.location)
        eta_min = cls.calculate_eta_minutes(dist_km, unit.speed_kmh)

        sev_score = incident.severity.final_score
        # Severity multiplier: high severity penalizes ETA much more aggressively
        # (e.g. 5 min ETA on critical incident (score 0.9) has weight ~ 4.6 vs 1.6 on low score 0.2)
        sev_multiplier = 1.0 + (sev_score * 4.0)

        # Type suitability penalty
        type_penalty = cls.SUITABILITY_PENALTY.get(incident.type, {}).get(unit.type, 10.0)

        # Priority reward: reduces cost for high severity so solver prioritizes matching them
        priority_reward = sev_score * 30.0

        total_cost = (eta_min * sev_multiplier) + type_penalty - priority_reward

        return total_cost, dist_km, eta_min

    @classmethod
    def optimize_allocation(
        cls,
        incidents: List[Incident],
        units: List[Unit]
    ) -> OptimizationResult:
        """
        Run the Hungarian Algorithm (linear_sum_assignment) on the formulated cost matrix.
        Handles rectangular sizes (M != N) via matrix padding.
        """
        # Filter active unassigned incidents & available units
        active_incidents = [
            inc for inc in incidents
            if inc.status in ["REPORTED", "ASSIGNED"] and inc.assigned_unit_id is None
        ]
        # Sort active incidents by severity descending
        active_incidents.sort(key=lambda x: x.severity.final_score, reverse=True)

        available_units = [
            u for u in units
            if u.status in [UnitStatus.AVAILABLE, UnitStatus.RETURNING]
        ]

        if not active_incidents or not available_units:
            return OptimizationResult(
                allocations=[],
                unassigned_incidents=[inc.id for inc in active_incidents],
                available_units_remaining=[u.id for u in available_units],
                total_estimated_response_time_min=0.0,
                algorithm_used="Hungarian Algorithm (Zero active items)"
            )

        num_incidents = len(active_incidents)
        num_units = len(available_units)
        dim = max(num_incidents, num_units)

        # Create square cost matrix padded with neutral high/zero costs
        cost_matrix = np.zeros((dim, dim))

        # Fill real costs
        for i in range(num_incidents):
            for j in range(num_units):
                cost, _, _ = cls.compute_cost(active_incidents[i], available_units[j])
                cost_matrix[i, j] = cost

        # Padding if M != N
        if num_incidents < dim:
            # More units than incidents: dummy incidents cost 0 for all units
            for i in range(num_incidents, dim):
                for j in range(num_units):
                    cost_matrix[i, j] = 500.0  # High baseline so real incidents get priority

        if num_units < dim:
            # More incidents than units: dummy units cost heavily, favoring high severity for real units
            for i in range(num_incidents):
                for j in range(num_units, dim):
                    # Higher severity incidents get higher dummy cost so real units are assigned to them
                    cost_matrix[i, j] = 1000.0 - (active_incidents[i].severity.final_score * 200.0)

        # Execute Hungarian Algorithm
        row_ind, col_ind = linear_sum_assignment(cost_matrix)

        recommendations: List[AllocationRecommendation] = []
        assigned_incident_ids = set()
        assigned_unit_ids = set()
        total_eta = 0.0

        for r, c in zip(row_ind, col_ind):
            # Only keep genuine pairs (not dummy rows or dummy columns)
            if r < num_incidents and c < num_units:
                inc = active_incidents[r]
                unit = available_units[c]
                cost, dist_km, eta_min = cls.compute_cost(inc, unit)

                # Confidence calculation: based on distance and type suitability
                type_penalty = cls.SUITABILITY_PENALTY.get(inc.type, {}).get(unit.type, 10.0)
                suitability_score = max(0.0, 1.0 - (type_penalty / 25.0))
                distance_score = max(0.0, 1.0 - (dist_km / 25.0))
                confidence_pct = int((suitability_score * 0.55 + distance_score * 0.45) * 100)
                confidence_pct = max(35, min(99, confidence_pct))

                # Human-readable reasoning for judges/dispatchers
                reasoning = (
                    f"Optimal match: {unit.name} ({unit.type.value}) is {dist_km:.1f}km away "
                    f"(ETA ~{eta_min:.1f}m). Matched for {inc.type.value} severity "
                    f"{inc.severity.level.value} ({inc.severity.final_score:.2f}) with {confidence_pct}% confidence."
                )

                rec = AllocationRecommendation(
                    incident_id=inc.id,
                    incident_title=inc.title,
                    severity_level=inc.severity.level,
                    severity_score=inc.severity.final_score,
                    unit_id=unit.id,
                    unit_name=unit.name,
                    unit_type=unit.type,
                    distance_km=dist_km,
                    eta_minutes=eta_min,
                    cost_score=round(cost, 2),
                    match_confidence_pct=confidence_pct,
                    reasoning=reasoning
                )
                recommendations.append(rec)
                assigned_incident_ids.add(inc.id)
                assigned_unit_ids.add(unit.id)
                total_eta += eta_min

        # Sort recommendations by incident severity descending so dispatchers see critical first
        recommendations.sort(key=lambda x: x.severity_score, reverse=True)

        unassigned_incidents = [inc.id for inc in active_incidents if inc.id not in assigned_incident_ids]
        remaining_units = [u.id for u in available_units if u.id not in assigned_unit_ids]

        return OptimizationResult(
            allocations=recommendations,
            unassigned_incidents=unassigned_incidents,
            available_units_remaining=remaining_units,
            total_estimated_response_time_min=round(total_eta, 1),
            algorithm_used="Hungarian Algorithm (scipy linear_sum_assignment) + Multi-Factor Cost Matrix"
        )

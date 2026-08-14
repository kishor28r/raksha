"""
RAKSHA: AI-Powered Emergency Response & Resource Allocation System
Unit Tests for Backend Models, AI Severity Scorer, and Hungarian Optimizer
"""

import sys
import os

# Add parent directory to sys.path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.models import (
    IncidentCreate,
    Incident,
    Unit,
    IncidentType,
    UnitType,
    UnitStatus,
    SeverityLevel,
    IncidentSource,
    Location
)
from backend.ai_scorer import AISeverityScorer
from backend.optimizer import ResourceOptimizer, haversine_distance
from backend.simulator import get_default_units, get_preset_scenarios


def test_ai_severity_scorer():
    print("Testing AI Severity Scorer...")

    # Test Case 1: Critical High-Rise Fire
    inc1 = IncidentCreate(
        title="Commercial High-Rise Fire on 5th Floor",
        type=IncidentType.FIRE,
        description="Massive fire broke out in commercial complex. Heavy black smoke spreading rapidly. 6 office workers trapped including 1 pregnant woman and 1 elderly manager.",
        location=Location(lat=28.6315, lng=77.2185),
        source=IncidentSource.CITIZEN_SOS
    )
    score1 = AISeverityScorer.score_incident(inc1)
    print(f"  Incident 1: {score1.level.value} (Score: {score1.final_score:.2f})")
    assert score1.final_score >= 0.70, f"Expected critical score >= 0.70, got {score1.final_score}"
    assert score1.extracted_casualties == 6, f"Expected 6 casualties, got {score1.extracted_casualties}"
    assert len(score1.vulnerable_groups_found) >= 2, f"Expected detected vulnerable groups, got {score1.vulnerable_groups_found}"

    # Test Case 2: Minor Incident (Low Severity)
    inc2 = IncidentCreate(
        title="Minor Road Surface Waterlogging",
        type=IncidentType.FLOOD,
        description="6 inches water logging on side road. One car tyre stuck. No injuries, driver safe on footpath.",
        location=Location(lat=28.6050, lng=77.2100),
        source=IncidentSource.CITIZEN_SOS,
        reported_casualties=0,
        has_vulnerable_groups=False
    )
    score2 = AISeverityScorer.score_incident(inc2)
    print(f"  Incident 2: {score2.level.value} (Score: {score2.final_score:.2f})")
    assert score2.final_score < 0.50, f"Expected low score < 0.50, got {score2.final_score}"

    # Test Case 3: Casualty count regex extraction
    assert AISeverityScorer.extract_casualties("There are 12 people trapped in the building") == 12
    assert AISeverityScorer.extract_casualties("Found a family of 4 stranded") == 4
    assert AISeverityScorer.extract_casualties("No injuries reported") == 0

    print("AI Severity Scorer Tests Passed!\n")


def test_haversine_distance():
    print("Testing Haversine Distance Calculation...")
    # Distance between AIIMS (28.5672, 77.2100) and Connaught Place (28.6328, 77.2197) ~ 7.3 km
    loc1 = Location(lat=28.5672, lng=77.2100)
    loc2 = Location(lat=28.6328, lng=77.2197)
    d = haversine_distance(loc1, loc2)
    print(f"  Distance AIIMS -> CP: {d:.2f} km")
    assert 6.0 <= d <= 8.5, f"Expected distance between 6 and 8.5 km, got {d}"
    print("Haversine Distance Tests Passed!\n")


def test_resource_optimizer():
    print("Testing Hungarian Algorithm Resource Allocation Optimizer...")
    units = get_default_units()

    # Create 2 test incidents (1 critical fire, 1 severe flood)
    inc1 = Incident(
        id="INC-001",
        title="Severe Chemical Plant Fire",
        type=IncidentType.FIRE,
        description="Massive blaze with toxic smoke and 5 trapped workers",
        location=Location(lat=28.6350, lng=77.2250),  # Right near Connaught Fire HQ
        severity=AISeverityScorer.score_incident(IncidentCreate(
            title="Severe Chemical Plant Fire",
            type=IncidentType.FIRE,
            description="Massive blaze with toxic smoke and 5 trapped workers",
            location=Location(lat=28.6350, lng=77.2250)
        ))
    )

    inc2 = Incident(
        id="INC-002",
        title="Submerged Bus Rescue",
        type=IncidentType.FLOOD,
        description="Bus submerged under bridge with 10 passengers",
        location=Location(lat=28.6100, lng=77.2300),  # Right near Pragati Maidan NDRF Hub
        severity=AISeverityScorer.score_incident(IncidentCreate(
            title="Submerged Bus Rescue",
            type=IncidentType.FLOOD,
            description="Bus submerged under bridge with 10 passengers",
            location=Location(lat=28.6100, lng=77.2300)
        ))
    )

    result = ResourceOptimizer.optimize_allocation([inc1, inc2], units)
    print(f"  Algorithm: {result.algorithm_used}")
    print(f"  Allocations Generated: {len(result.allocations)}")
    for alloc in result.allocations:
        print(f"    -> Incident {alloc.incident_id} [{alloc.severity_level.value}] matched to {alloc.unit_name} ({alloc.unit_type.value}) - ETA: {alloc.eta_minutes:.1f}m, Confidence: {alloc.match_confidence_pct}%")

    assert len(result.allocations) == 2, f"Expected 2 allocations, got {len(result.allocations)}"
    # Verify Fire incident got a FIRE_TRUCK or MULTI_HAZARD
    fire_alloc = next(a for a in result.allocations if a.incident_id == "INC-001")
    assert fire_alloc.unit_type in [UnitType.FIRE_TRUCK, UnitType.MULTI_HAZARD]

    # Verify Flood incident got RESCUE_SQUAD or MULTI_HAZARD
    flood_alloc = next(a for a in result.allocations if a.incident_id == "INC-002")
    assert flood_alloc.unit_type in [UnitType.RESCUE_SQUAD, UnitType.MULTI_HAZARD]

    print("Resource Optimizer Tests Passed!\n")


def test_preset_scenarios():
    print("Testing Preset Scenario Loading...")
    scenarios = get_preset_scenarios()
    assert "multi_hazard_crisis" in scenarios
    assert "industrial_hazmat_disaster" in scenarios
    assert "earthquake_building_collapse" in scenarios
    print(f"  Verified {len(scenarios)} disaster scenarios available.")
    print("Preset Scenario Tests Passed!\n")


if __name__ == "__main__":
    print("=" * 60)
    print("RAKSHA AI BACKEND TEST SUITE")
    print("=" * 60)
    test_ai_severity_scorer()
    test_haversine_distance()
    test_resource_optimizer()
    test_preset_scenarios()
    print("=" * 60)
    print("ALL TESTS PASSED SUCCESSFULLY! BACKEND IS READY.")
    print("=" * 60)

"""
RAKSHA: AI-Powered Emergency Response & Resource Allocation System
Simulation Suite & City Scenario Generator

Provides realistic multi-hazard disaster scenarios, IoT/CCTV event injectors,
and dynamic vehicle movement simulation across city coordinates.
"""

import time
import random
import math
from typing import List, Dict, Any, Optional
from backend.models import (
    Incident,
    Unit,
    IncidentCreate,
    IncidentType,
    UnitType,
    UnitStatus,
    IncidentStatus,
    IncidentSource,
    Location
)
from backend.ai_scorer import AISeverityScorer


# City Center Coordinates (Default: Delhi NCR, customizable)
CITY_CENTER = {"lat": 28.6139, "lng": 77.2090}


def get_default_units() -> List[Unit]:
    """
    Generate initial emergency response fleet stationed across strategic city hubs.
    """
    unit_configs = [
        # Ambulances (Advanced Life Support & Basic)
        {"name": "ALS-Ambulance Alpha-01", "type": UnitType.AMBULANCE, "lat": 28.5672, "lng": 77.2100, "address": "AIIMS Trauma Center Base", "speed": 55.0, "cap": 2},
        {"name": "BLS-Ambulance Beta-02", "type": UnitType.AMBULANCE, "lat": 28.6328, "lng": 77.2197, "address": "Connaught Place Medical Station", "speed": 50.0, "cap": 2},
        {"name": "ALS-Ambulance Gamma-03", "type": UnitType.AMBULANCE, "lat": 28.6515, "lng": 77.1906, "address": "Karol Bagh Emergency Post", "speed": 52.0, "cap": 2},
        {"name": "ALS-Ambulance Delta-04", "type": UnitType.AMBULANCE, "lat": 28.5700, "lng": 77.2400, "address": "Lajpat Nagar South Hub", "speed": 54.0, "cap": 2},

        # Fire Trucks & Heavy Water Tenders
        {"name": "Fire Tender Vulcan-01", "type": UnitType.FIRE_TRUCK, "lat": 28.6350, "lng": 77.2250, "address": "Connaught Fire HQ", "speed": 45.0, "cap": 6},
        {"name": "Fire Tender Vulcan-02", "type": UnitType.FIRE_TRUCK, "lat": 28.6700, "lng": 77.1200, "address": "West Delhi Industrial Fire Station", "speed": 46.0, "cap": 6},
        {"name": "Hydraulic Ladder Truck-03", "type": UnitType.FIRE_TRUCK, "lat": 28.5355, "lng": 77.2410, "address": "Nehru Place High-Rise Fire Post", "speed": 40.0, "cap": 5},

        # NDRF / SDRF Disaster Rescue Squads
        {"name": "NDRF Rescue Squad Falcon-01", "type": UnitType.RESCUE_SQUAD, "lat": 28.6100, "lng": 77.2300, "address": "Pragati Maidan Disaster Hub", "speed": 48.0, "cap": 10},
        {"name": "SDRF Flood Rescue Squad-02", "type": UnitType.RESCUE_SQUAD, "lat": 28.6900, "lng": 77.2100, "address": "Yamuna Riverfront Post", "speed": 45.0, "cap": 8},

        # Police Interceptors / Quick Response Teams
        {"name": "Police QRT Eagle-01", "type": UnitType.POLICE_PATROL, "lat": 28.6250, "lng": 77.2150, "address": "Central District Patrol", "speed": 60.0, "cap": 4},
        {"name": "Police QRT Eagle-02", "type": UnitType.POLICE_PATROL, "lat": 28.5800, "lng": 77.2300, "address": "South District Patrol", "speed": 60.0, "cap": 4},

        # Multi-Hazard Rapid Response
        {"name": "Multi-Hazard Mobile Command-01", "type": UnitType.MULTI_HAZARD, "lat": 28.6150, "lng": 77.2050, "address": "State Disaster Command Center", "speed": 50.0, "cap": 6},
    ]

    units = []
    for cfg in unit_configs:
        loc = Location(lat=cfg["lat"], lng=cfg["lng"], address=cfg["address"])
        u = Unit(
            name=cfg["name"],
            type=cfg["type"],
            status=UnitStatus.AVAILABLE,
            location=loc,
            base_location=loc,
            speed_kmh=cfg["speed"],
            capacity=cfg["cap"]
        )
        units.append(u)
    return units


def get_preset_scenarios() -> Dict[str, Dict[str, Any]]:
    """
    Pre-configured disaster scenarios for live hackathon presentation.
    """
    return {
        "multi_hazard_crisis": {
            "name": "Scenario 1: Urban Multi-Hazard Crisis (Fire, Flood, Pileup)",
            "description": "Simultaneous structural fire, monsoon underpass flash flood, and expressway pileup testing multi-unit priority dispatch.",
            "incidents": [
                {
                    "title": "Commercial High-Rise Fire on 5th Floor",
                    "type": IncidentType.FIRE,
                    "description": "Massive fire broke out in commercial complex. Heavy black smoke spreading rapidly. 6 office workers trapped on terrace including 1 pregnant woman and 1 elderly manager.",
                    "location": {"lat": 28.6315, "lng": 77.2185, "address": "Barakhamba Road, Connaught Place"},
                    "source": IncidentSource.CCTV_AI_DETECTION,
                    "reported_casualties": 6,
                    "has_vulnerable_groups": True
                },
                {
                    "title": "Minto Bridge Underpass Flash Flood Inundation",
                    "type": IncidentType.FLOOD,
                    "description": "Severe waterlogging 6 feet deep underpass due to cloudburst. DTC bus with 15 passengers submerged. Water rising urgently.",
                    "location": {"lat": 28.6385, "lng": 77.2270, "address": "Minto Bridge Underpass, Central Delhi"},
                    "source": IncidentSource.IOT_SENSOR,
                    "reported_casualties": 15,
                    "has_vulnerable_groups": True
                },
                {
                    "title": "Ring Road Multi-Vehicle Collision Pileup",
                    "type": IncidentType.ACCIDENT,
                    "description": "3 cars and 1 truck collided at high speed. 4 victims seriously injured with fractures and profuse bleeding. Immediate ambulance required.",
                    "location": {"lat": 28.5680, "lng": 77.2450, "address": "Ring Road near Lajpat Nagar Flyover"},
                    "source": IncidentSource.CITIZEN_SOS,
                    "reported_casualties": 4,
                    "has_vulnerable_groups": False
                },
                {
                    "title": "Residential LPG Cylinder Leak & Fire Threat",
                    "type": IncidentType.GAS_LEAK,
                    "description": "Strong gas smell leaking from 2 cylinders in crowded residential alley. Sparks visible from transformer.",
                    "location": {"lat": 28.6500, "lng": 77.1950, "address": "Padam Singh Road, Karol Bagh"},
                    "source": IncidentSource.BYSTANDER_CALL_112,
                    "reported_casualties": 0,
                    "has_vulnerable_groups": False
                },
                {
                    "title": "Minor Road Surface Waterlogging & Stalled Car",
                    "type": IncidentType.FLOOD,
                    "description": "6 inches water logging on side road. One car tyre stuck. No injuries, driver safe on footpath.",
                    "location": {"lat": 28.6050, "lng": 77.2100, "address": "Lodhi Road Sector 3"},
                    "source": IncidentSource.CITIZEN_SOS,
                    "reported_casualties": 0,
                    "has_vulnerable_groups": False
                }
            ]
        },
        "industrial_hazmat_disaster": {
            "name": "Scenario 2: Industrial Hazmat Explosion & Chemical Cloud",
            "description": "Chemical manufacturing plant blast emitting toxic fumes near residential colony.",
            "incidents": [
                {
                    "title": "Chemical Reactor Explosion & Toxic Chlorine Leak",
                    "type": IncidentType.HAZMAT,
                    "description": "Industrial reactor blast in chemical unit. Highly toxic yellow chlorine gas escaping into atmosphere. 8 workers unconscious, burning eyes and asphyxiation.",
                    "location": {"lat": 28.6750, "lng": 77.1250, "address": "Mayapuri Industrial Area Phase-2"},
                    "source": IncidentSource.IOT_SENSOR,
                    "reported_casualties": 8,
                    "has_vulnerable_groups": True
                },
                {
                    "title": "Adjoining Daycare School Smoke Inhalation Alert",
                    "type": IncidentType.MEDICAL_TRAUMA,
                    "description": "Toxic chemical smoke entered nearby daycare center. 12 toddlers and infants coughing severely and suffocating. Urgent pediatric triage needed!",
                    "location": {"lat": 28.6720, "lng": 77.1290, "address": "Little Angels Daycare, Mayapuri Border"},
                    "source": IncidentSource.BYSTANDER_CALL_112,
                    "reported_casualties": 12,
                    "has_vulnerable_groups": True
                },
                {
                    "title": "Secondary Transformer Fire at Factory Gate",
                    "type": IncidentType.FIRE,
                    "description": "Oil transformer ignited due to blast vibrations. Threatening adjacent fuel storage tank.",
                    "location": {"lat": 28.6760, "lng": 77.1220, "address": "Factory Gate 4, Mayapuri"},
                    "source": IncidentSource.CCTV_AI_DETECTION,
                    "reported_casualties": 1,
                    "has_vulnerable_groups": False
                }
            ]
        },
        "earthquake_building_collapse": {
            "name": "Scenario 3: Structural Collapse & Mass Casualty Incident",
            "description": "Old 4-storey residential building collapse following seismic tremors.",
            "incidents": [
                {
                    "title": "4-Storey Building Partial Collapse with People Trapped",
                    "type": IncidentType.BUILDING_COLLAPSE,
                    "description": "Old residential building caved in. 10 people trapped under concrete debris. Screams heard. Multiple severe head injuries and crushed limbs.",
                    "location": {"lat": 28.6540, "lng": 77.2310, "address": "Chandni Chowk Old Haveli Ward"},
                    "source": IncidentSource.CITIZEN_SOS,
                    "reported_casualties": 10,
                    "has_vulnerable_groups": True
                },
                {
                    "title": "Live High-Voltage Power Line Snapped on Street",
                    "type": IncidentType.ACCIDENT,
                    "description": "Snapped 11kV electrical wire sparking on wet pavement. 2 pedestrians suffered electric shock.",
                    "location": {"lat": 28.6570, "lng": 77.2280, "address": "Main Bazaar Gate, Old Delhi"},
                    "source": IncidentSource.CCTV_AI_DETECTION,
                    "reported_casualties": 2,
                    "has_vulnerable_groups": False
                }
            ]
        }
    }


def generate_random_incident(center_lat: float = 28.6139, center_lng: float = 77.2090) -> IncidentCreate:
    """
    Generate an unexpected randomized live emergency report for demo simulation.
    """
    templates = [
        {
            "title": "Metro Station Escalator Stampede & Fall",
            "type": IncidentType.MEDICAL_TRAUMA,
            "description": "Sudden stop on crowded escalator caused 5 people to fall. 2 elderly persons have severe hip fractures and head cuts.",
            "casualties": 5,
            "vulnerable": True,
            "source": IncidentSource.CCTV_AI_DETECTION
        },
        {
            "title": "School Bus Collision with Dump Truck",
            "type": IncidentType.ACCIDENT,
            "description": "Heavy collision between school transport van and truck. 7 school children injured, driver pinned behind steering wheel.",
            "casualties": 7,
            "vulnerable": True,
            "source": IncidentSource.BYSTANDER_CALL_112
        },
        {
            "title": "Basement Transformer Explosion & Dark Smoke",
            "type": IncidentType.FIRE,
            "description": "Electrical transformer explosion in commercial basement. Smoke suffocating guards, fire spreading to parked vehicles.",
            "casualties": 2,
            "vulnerable": False,
            "source": IncidentSource.IOT_SENSOR
        },
        {
            "title": "Water Tank Structural Rupture in Residential Block",
            "type": IncidentType.FLOOD,
            "description": "Overhead 50,000L water tank cracked and collapsed. Water gushing through stairs, 3 families trapped on 2nd floor.",
            "casualties": 4,
            "vulnerable": True,
            "source": IncidentSource.CITIZEN_SOS
        }
    ]

    chosen = random.choice(templates)
    # Jitter within 6 km radius
    lat_offset = (random.random() - 0.5) * 0.08
    lng_offset = (random.random() - 0.5) * 0.08

    loc = Location(
        lat=round(center_lat + lat_offset, 5),
        lng=round(center_lng + lng_offset, 5),
        address=f"Live Incident Zone ({round(center_lat + lat_offset, 4)}, {round(center_lng + lng_offset, 4)})"
    )

    return IncidentCreate(
        title=chosen["title"],
        type=chosen["type"],
        description=chosen["description"],
        location=loc,
        source=chosen["source"],
        reported_casualties=chosen["casualties"],
        has_vulnerable_groups=chosen["vulnerable"]
    )


def update_unit_positions_step(units: List[Unit], incidents: List[Incident], speed_multiplier: float = 1.0) -> None:
    """
    Step-by-step physical movement simulation of dispatched units towards their assigned incidents.
    """
    incident_map = {inc.id: inc for inc in incidents}

    for unit in units:
        if unit.status == UnitStatus.EN_ROUTE and unit.assigned_incident_id:
            target_inc = incident_map.get(unit.assigned_incident_id)
            if not target_inc:
                continue

            target_lat = target_inc.location.lat
            target_lng = target_inc.location.lng

            dlat = target_lat - unit.location.lat
            dlng = target_lng - unit.location.lng
            dist = math.sqrt(dlat**2 + dlng**2)

            # Move unit proportionally towards destination (simulating real transit)
            step_size = 0.003 * speed_multiplier

            if dist <= step_size:
                # Arrived on scene!
                unit.location.lat = target_lat
                unit.location.lng = target_lng
                unit.status = UnitStatus.ON_SCENE
                target_inc.status = IncidentStatus.IN_PROGRESS
            else:
                unit.location.lat += (dlat / dist) * step_size
                unit.location.lng += (dlng / dist) * step_size
                unit.location.lat = round(unit.location.lat, 5)
                unit.location.lng = round(unit.location.lng, 5)

"""
RAKSHA: AI-Powered Emergency Response & Resource Allocation System
AI Severity Scoring Engine (NLP Multi-Factor Urgency Classifier)

Computes explainable, multi-factor urgency scores for emergency incidents
based on text descriptions, casualty extraction, vulnerability, and incident type.
"""

import re
import time
from typing import Tuple, List, Dict, Any, Optional
from backend.models import (
    IncidentType,
    SeverityLevel,
    SeverityBreakdown,
    IncidentCreate
)


class AISeverityScorer:
    """
    NLP & Rule-Weighted Multi-Factor Emergency Urgency Evaluator.
    Produces an explainable urgency score S ∈ [0.0, 1.0] and categorization.
    """

    # Weights for the 4 core dimensions
    W_LIFE_THREAT = 0.40
    W_CASUALTIES = 0.25
    W_VULNERABILITY = 0.20
    W_TIME_URGENCY = 0.15

    # Base priors by incident type
    INCIDENT_TYPE_PRIORS = {
        IncidentType.BUILDING_COLLAPSE: 0.85,
        IncidentType.HAZMAT: 0.80,
        IncidentType.GAS_LEAK: 0.75,
        IncidentType.FIRE: 0.70,
        IncidentType.MEDICAL_TRAUMA: 0.70,
        IncidentType.FLOOD: 0.65,
        IncidentType.ACCIDENT: 0.50,
    }

    # Keyword Lexicons with severity weights
    CRITICAL_THREAT_TERMS = [
        "trapped", "collapse", "collapsed", "explosion", "blast", "unconscious",
        "cardiac arrest", "heart attack", "heavy bleeding", "profuse bleeding",
        "suffocating", "asphyxiation", "crushed", "submerged", "drowning",
        "severe burns", "toxic gas", "amputation", "head injury", "not breathing",
        "structural failure", "screaming for help", "caved in"
    ]

    HIGH_THREAT_TERMS = [
        "spreading", "smoke", "fire", "fracture", "broken bone", "bleeding",
        "electric shock", "chemical leak", "short circuit", "water rising",
        "injured", "gas smell", "spill", "overturned", "pileup", "panic",
        "flash flood", "burns", "choking"
    ]

    MODERATE_THREAT_TERMS = [
        "minor injury", "fender bender", "waterlogging", "tree fallen",
        "minor leak", "scratch", "bruise", "traffic stall", "smoke smell",
        "small fire", "shallow water"
    ]

    VULNERABILITY_TERMS = {
        "infant": "Infants/Babies",
        "baby": "Infants/Babies",
        "toddler": "Infants/Babies",
        "child": "Children",
        "children": "Children",
        "kid": "Children",
        "kids": "Children",
        "elderly": "Elderly Citizens",
        "senior": "Senior Citizens",
        "old age": "Elderly Citizens",
        "grandfather": "Elderly Citizens",
        "grandmother": "Elderly Citizens",
        "pregnant": "Pregnant Women",
        "pregnancy": "Pregnant Women",
        "disabled": "Persons with Disabilities",
        "handicapped": "Persons with Disabilities",
        "wheelchair": "Wheelchair Bound",
        "bedridden": "Bedridden Patients",
        "school": "Educational Institution",
        "kindergarten": "Daycare/School",
        "hospital": "Medical Facility",
        "icu": "ICU/Critical Care",
        "nursing home": "Nursing Home",
        "orphanage": "Orphanage"
    }

    INTENSITY_AMPLIFIERS = [
        "massively", "rapidly", "urgently", "immediately", "catastrophic",
        "uncontrolled", "huge", "severe", "critical", "desperate", "fast",
        "life-threatening", "emergency"
    ]

    @classmethod
    def extract_casualties(cls, text: str, reported: Optional[int] = None) -> int:
        """
        Extract count of casualties/affected individuals from free-text descriptions.
        """
        if reported is not None and reported > 0:
            return reported

        text_lower = text.lower()
        casualties = 0

        # Pattern 1: Numbers with intermediate descriptors e.g. "6 office workers trapped", "5 people injured", "3 trapped"
        pattern1 = r'(\d+)\s+(?:[\w-]+\s+)?(?:people|persons|victims|injured|trapped|casualties|patients|children|kids|workers|passengers|residents|citizens|staff|civilians|individuals|students)'
        matches1 = re.findall(pattern1, text_lower)
        if matches1:
            casualties = max(casualties, max(int(m) for m in matches1))

        # Pattern 2: Action first e.g. "trapped 6 workers", "injuring 4", "evacuating 10"
        pattern2 = r'(?:trapped|injured|injuring|affected|evacuated|suffocating|stranded|submerged)\s+(?:about|around|over|at least)?\s*(\d+)'
        matches2 = re.findall(pattern2, text_lower)
        if matches2:
            casualties = max(casualties, max(int(m) for m in matches2))

        # Pattern 3: "family of 4"
        pattern3 = r'family\s+of\s+(\d+)'
        matches3 = re.findall(pattern3, text_lower)
        if matches3:
            casualties = max(casualties, max(int(m) for m in matches3))

        # Pattern 4: Word numbers "two people", "three trapped", "six office workers"
        word_map = {
            "one": 1, "two": 2, "three": 3, "four": 4, "five": 5,
            "six": 6, "seven": 7, "eight": 8, "nine": 9, "ten": 10,
            "dozen": 12, "dozens": 24, "several": 4, "many": 6, "multiple": 5
        }
        for word, val in word_map.items():
            if re.search(rf'\b{word}\b\s+(?:[\w-]+\s+)?(?:people|persons|victims|injured|trapped|casualties|patients|workers)', text_lower):
                casualties = max(casualties, val)

        return casualties

    @classmethod
    def evaluate_vulnerability(cls, text: str, has_flag: Optional[bool] = None) -> Tuple[float, List[str]]:
        """
        Detect presence of high-risk demographics and critical infrastructure.
        """
        text_lower = text.lower()
        found_groups = []

        for term, label in cls.VULNERABILITY_TERMS.items():
            if re.search(rf'\b{re.escape(term)}\b', text_lower):
                if label not in found_groups:
                    found_groups.append(label)

        if has_flag is True and not found_groups:
            found_groups.append("High-Risk Demographics Flagged")

        # Score based on number and type of vulnerable targets
        if len(found_groups) >= 3:
            v_score = 0.95
        elif len(found_groups) == 2:
            v_score = 0.80
        elif len(found_groups) == 1:
            v_score = 0.65
        elif has_flag:
            v_score = 0.60
        else:
            v_score = 0.15

        return round(v_score, 2), found_groups

    @classmethod
    def evaluate_life_threat(cls, text: str, inc_type: IncidentType) -> Tuple[float, List[str]]:
        """
        Analyze life-threat intensity using domain lexicons, modifiers, and incident priors.
        """
        text_lower = text.lower()
        detected_threats = []

        threat_score = cls.INCIDENT_TYPE_PRIORS.get(inc_type, 0.50)

        # Check critical threat terms
        critical_matches = [w for w in cls.CRITICAL_THREAT_TERMS if re.search(rf'\b{re.escape(w)}\b', text_lower)]
        if critical_matches:
            threat_score = max(threat_score, 0.85)
            detected_threats.extend(critical_matches)

        # Check high threat terms
        high_matches = [w for w in cls.HIGH_THREAT_TERMS if re.search(rf'\b{re.escape(w)}\b', text_lower)]
        if high_matches:
            threat_score = max(threat_score, 0.65)
            detected_threats.extend([w for w in high_matches if w not in detected_threats])

        # Check moderate threat terms if no higher matches
        if not critical_matches and not high_matches:
            mod_matches = [w for w in cls.MODERATE_THREAT_TERMS if re.search(rf'\b{re.escape(w)}\b', text_lower)]
            if mod_matches:
                threat_score = min(threat_score, 0.40)
                detected_threats.extend(mod_matches)

        # Check intensity amplifiers
        amplifier_matches = [w for w in cls.INTENSITY_AMPLIFIERS if re.search(rf'\b{re.escape(w)}\b', text_lower)]
        if amplifier_matches:
            threat_score = min(1.0, threat_score + 0.10 * len(amplifier_matches))

        return round(min(1.0, max(0.1, threat_score)), 2), detected_threats

    @classmethod
    def evaluate_casualty_score(cls, count: int) -> float:
        """
        Non-linear mapping from casualty count to normalized score.
        """
        if count <= 0:
            return 0.10
        elif count == 1:
            return 0.45
        elif count == 2:
            return 0.60
        elif count <= 5:
            return 0.78
        elif count <= 10:
            return 0.90
        else:
            return 1.00

    @classmethod
    def evaluate_time_urgency(cls, text: str, elapsed_seconds: float = 0) -> float:
        """
        Urgency based on time keywords and elapsed wait time.
        """
        text_lower = text.lower()
        urgency = 0.50

        urgent_words = ["immediately", "urgent", "fast", "right now", "seconds", "asap", "hurry", "spreading quickly"]
        if any(w in text_lower for w in urgent_words):
            urgency += 0.25

        # Escalation over time: after 10 minutes (600s), urgency climbs
        if elapsed_seconds > 0:
            time_boost = min(0.25, (elapsed_seconds / 600.0) * 0.25)
            urgency += time_boost

        return round(min(1.0, urgency), 2)

    @classmethod
    def score_incident(cls, inc_input: IncidentCreate, elapsed_seconds: float = 0) -> SeverityBreakdown:
        """
        Full AI pipeline: multi-factor scoring with transparent breakdown.
        """
        full_text = f"{inc_input.title} {inc_input.description}"

        # 1. Life Threat
        life_threat, detected_terms = cls.evaluate_life_threat(full_text, inc_input.type)

        # 2. Casualties
        casualties = cls.extract_casualties(full_text, inc_input.reported_casualties)
        casualty_score = cls.evaluate_casualty_score(casualties)

        # 3. Vulnerability
        vulnerability_score, vuln_groups = cls.evaluate_vulnerability(full_text, inc_input.has_vulnerable_groups)

        # 4. Time Urgency
        time_score = cls.evaluate_time_urgency(full_text, elapsed_seconds)

        # Composite Weighted Score S ∈ [0, 1]
        final_score = (
            cls.W_LIFE_THREAT * life_threat +
            cls.W_CASUALTIES * casualty_score +
            cls.W_VULNERABILITY * vulnerability_score +
            cls.W_TIME_URGENCY * time_score
        )
        final_score = round(min(1.0, max(0.05, final_score)), 2)

        # Determine Category Level
        if final_score >= 0.75:
            level = SeverityLevel.CRITICAL
        elif final_score >= 0.55:
            level = SeverityLevel.HIGH
        elif final_score >= 0.35:
            level = SeverityLevel.MEDIUM
        else:
            level = SeverityLevel.LOW

        # Generate Explainability String
        terms_str = f", terms: [{', '.join(detected_terms[:3])}]" if detected_terms else ""
        vuln_str = f", vulnerable: [{', '.join(vuln_groups)}]" if vuln_groups else ""
        cas_str = f", estimated casualties: {casualties}" if casualties > 0 else ""

        explanation = (
            f"AI Severity: {level.value} (Score {final_score:.2f}). "
            f"Factors: Threat={life_threat:.2f}{terms_str} | "
            f"Casualties={casualty_score:.2f}{cas_str} | "
            f"Vulnerability={vulnerability_score:.2f}{vuln_str} | "
            f"Urgency={time_score:.2f}"
        )

        return SeverityBreakdown(
            life_threat_score=life_threat,
            casualty_score=casualty_score,
            vulnerability_score=vulnerability_score,
            time_urgency_score=time_score,
            final_score=final_score,
            level=level,
            explanation=explanation,
            extracted_casualties=casualties,
            vulnerable_groups_found=vuln_groups
        )

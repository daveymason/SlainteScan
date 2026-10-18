"""Deterministic Manchester Triage System (MTS) Rules Engine.

Calculates Manchester Triage System (MTS) acuity category 1 through 5
based strictly on mathematical physiological thresholds and emergency discriminators.
No LLM inference or probabilistic decisions are allowed in clinical scoring.
"""
from typing import Dict, Any, Optional

MTS_METADATA = {
    1: {
        "category": 1,
        "name": "Immediate",
        "color": "Red",
        "badge_class": "danger",
        "target_time_minutes": 0,
        "clinical_urgency": "Immediate life-saving intervention required"
    },
    2: {
        "category": 2,
        "name": "Very Urgent",
        "color": "Orange",
        "badge_class": "warning",
        "target_time_minutes": 10,
        "clinical_urgency": "Very urgent emergency care required within 10 minutes"
    },
    3: {
        "category": 3,
        "name": "Urgent",
        "color": "Yellow",
        "badge_class": "info",
        "target_time_minutes": 60,
        "clinical_urgency": "Urgent care required within 60 minutes"
    },
    4: {
        "category": 4,
        "name": "Standard",
        "color": "Green",
        "badge_class": "primary",
        "target_time_minutes": 120,
        "clinical_urgency": "Standard care required within 120 minutes"
    },
    5: {
        "category": 5,
        "name": "Non-Urgent",
        "color": "Blue",
        "badge_class": "secondary",
        "target_time_minutes": 240,
        "clinical_urgency": "Non-urgent presentation, review within 240 minutes"
    }
}

def calculate_mts_category(vitals: Dict[str, Any]) -> int:
    """
    Deterministic Manchester Triage System (MTS) evaluation.
    Evaluates physiological parameters strictly from highest urgency (1) to lowest (5).
    """
    def _to_float(v) -> Optional[float]:
        if v is None:
            return None
        try:
            return float(v)
        except (ValueError, TypeError):
            return None

    sys_bp = _to_float(vitals.get("systolic_bp"))
    spo2 = _to_float(vitals.get("spo2"))
    hr = _to_float(vitals.get("heart_rate"))
    rr = _to_float(vitals.get("respiratory_rate"))
    temp = _to_float(vitals.get("temperature"))
    pain = _to_float(vitals.get("pain"))
    complaint = str(vitals.get("complaint") or "").lower()

    # -------------------------------------------------------------
    # Category 1: Immediate (Red)
    # Severe airway compromise, critical shock, profound desaturation
    # -------------------------------------------------------------
    if (sys_bp is not None and sys_bp < 90) or \
       (spo2 is not None and spo2 < 90) or \
       (hr is not None and hr > 140) or \
       (rr is not None and (rr > 35 or rr < 8)) or \
       any(k in complaint for k in ["cardiac arrest", "unresponsive", "apnea", "anaphylaxis", "severe shock"]):
        return 1

    # -------------------------------------------------------------
    # Category 2: Very Urgent (Orange)
    # Severe pain (8-10), acute chest pain, SpO2 < 92%, extreme vitals
    # -------------------------------------------------------------
    if (spo2 is not None and spo2 < 92) or \
       (pain is not None and pain >= 8) or \
       (hr is not None and (hr > 125 or hr < 40)) or \
       (sys_bp is not None and sys_bp > 200) or \
       (rr is not None and rr > 30) or \
       (temp is not None and temp >= 40.0) or \
       any(k in complaint for k in ["crushing chest pain", "acute stroke", "severe dyspnea", "stridor"]):
        return 2

    # -------------------------------------------------------------
    # Category 3: Urgent (Yellow)
    # Moderate pain (4-7), moderate tachycardia/fever/hypertension
    # -------------------------------------------------------------
    if (pain is not None and pain >= 4) or \
       (hr is not None and hr > 105) or \
       (sys_bp is not None and sys_bp >= 160) or \
       (temp is not None and temp >= 38.5) or \
       (rr is not None and rr >= 24) or \
       (spo2 is not None and spo2 < 95) or \
       any(k in complaint for k in ["moderate pain", "fracture", "asthma", "persistent vomiting"]):
        return 3

    # -------------------------------------------------------------
    # Category 4: Standard (Green)
    # Mild pain (1-3), mild vitals deviations, minor injury
    # -------------------------------------------------------------
    if (pain is not None and pain >= 1) or \
       (temp is not None and temp >= 37.8) or \
       (hr is not None and hr > 100) or \
       any(k in complaint for k in ["minor trauma", "mild pain", "sprain", "laceration", "rash"]):
        return 4

    # -------------------------------------------------------------
    # Category 5: Non-Urgent (Blue)
    # Routine clinic, no physiological distress, pain = 0
    # -------------------------------------------------------------
    return 5

def get_mts_details(category: int) -> Dict[str, Any]:
    """Returns the clinical metadata and targets for an MTS category."""
    cat = int(category) if category in (1, 2, 3, 4, 5) else 3
    return MTS_METADATA.get(cat, MTS_METADATA[3])

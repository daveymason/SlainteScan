"""Deterministic Manchester Triage System (MTS) Rules Engine.

Calculates Manchester Triage System (MTS) acuity category 1 through 5
based strictly on mathematical physiological thresholds and emergency discriminators.
No LLM inference or probabilistic decisions are allowed in clinical scoring.
"""
from typing import Dict, Any, Optional, List

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


def calculate_news2_score(vitals: Dict[str, Any]) -> Dict[str, Any]:
    """
    Deterministic Royal College of Physicians National Early Warning Score 2 (NEWS2).
    Evaluates 7 physiological parameters to calculate clinical deterioration score (0-20),
    clinical risk level, and monitoring frequency target. Zero hallucinations.
    """
    def _to_float(v) -> Optional[float]:
        if v is None:
            return None
        try:
            return float(str(v).split()[0].replace('%', ''))
        except (ValueError, TypeError, IndexError):
            return None

    rr = _to_float(vitals.get("respiratory_rate") or vitals.get("resp_rate") or vitals.get("rr"))
    spo2 = _to_float(vitals.get("spo2") or vitals.get("o2_sat"))
    spo2_scale = int(vitals.get("spo2_scale") or 1)
    on_o2 = bool(vitals.get("supplemental_o2") or vitals.get("on_o2") or str(vitals.get("on_supplemental_o2", "")).lower() in ("true", "yes", "1"))
    sbp = _to_float(vitals.get("systolic_bp") or vitals.get("systolic") or vitals.get("sys_bp"))
    hr = _to_float(vitals.get("heart_rate") or vitals.get("hr"))
    temp = _to_float(vitals.get("temperature") or vitals.get("temp") or vitals.get("temp_c"))
    
    cvpu_raw = str(vitals.get("consciousness") or vitals.get("avpu") or vitals.get("cvpu") or "").strip().upper()
    gcs = _to_float(vitals.get("gcs"))
    is_cvpu = False
    if cvpu_raw:
        is_cvpu = cvpu_raw in ("C", "V", "P", "U", "VOICE", "PAIN", "UNRESPONSIVE", "CONFUSION")
    elif gcs is not None:
        is_cvpu = (gcs < 15.0)

    breakdown: Dict[str, int] = {}

    # 1. Respiration Rate (/min)
    if rr is not None:
        if rr <= 8:
            breakdown["RR"] = 3
        elif 9 <= rr <= 11:
            breakdown["RR"] = 1
        elif 12 <= rr <= 20:
            breakdown["RR"] = 0
        elif 21 <= rr <= 24:
            breakdown["RR"] = 2
        else:
            breakdown["RR"] = 3
    else:
        breakdown["RR"] = 0

    # 2. SpO2 (%) Scale 1 vs Scale 2
    if spo2 is not None:
        if spo2_scale == 2:
            if spo2 <= 83:
                breakdown["SpO2"] = 3
            elif 84 <= spo2 <= 85:
                breakdown["SpO2"] = 2
            elif 86 <= spo2 <= 87:
                breakdown["SpO2"] = 1
            elif 88 <= spo2 <= 92:
                breakdown["SpO2"] = 0
            elif 93 <= spo2 <= 94:
                breakdown["SpO2"] = 1 if on_o2 else 0
            elif 95 <= spo2 <= 96:
                breakdown["SpO2"] = 2 if on_o2 else 0
            else:
                breakdown["SpO2"] = 3 if on_o2 else 0
        else:
            if spo2 <= 91:
                breakdown["SpO2"] = 3
            elif 92 <= spo2 <= 93:
                breakdown["SpO2"] = 2
            elif 94 <= spo2 <= 95:
                breakdown["SpO2"] = 1
            else:
                breakdown["SpO2"] = 0
    else:
        breakdown["SpO2"] = 0

    # 3. Supplemental Oxygen
    breakdown["Supplemental_O2"] = 2 if on_o2 else 0

    # 4. Systolic Blood Pressure (mmHg)
    if sbp is not None:
        if sbp <= 90:
            breakdown["SBP"] = 3
        elif 91 <= sbp <= 100:
            breakdown["SBP"] = 2
        elif 101 <= sbp <= 110:
            breakdown["SBP"] = 1
        elif 111 <= sbp <= 219:
            breakdown["SBP"] = 0
        else:
            breakdown["SBP"] = 3
    else:
        breakdown["SBP"] = 0

    # 5. Heart Rate (/min)
    if hr is not None:
        if hr <= 40:
            breakdown["HR"] = 3
        elif 41 <= hr <= 50:
            breakdown["HR"] = 1
        elif 51 <= hr <= 90:
            breakdown["HR"] = 0
        elif 91 <= hr <= 110:
            breakdown["HR"] = 1
        elif 111 <= hr <= 130:
            breakdown["HR"] = 2
        else:
            breakdown["HR"] = 3
    else:
        breakdown["HR"] = 0

    # 6. Consciousness (Alert vs CVPU)
    breakdown["CVPU"] = 3 if is_cvpu else 0

    # 7. Temperature (°C)
    if temp is not None:
        if temp <= 35.0:
            breakdown["Temp"] = 3
        elif 35.1 <= temp <= 36.0:
            breakdown["Temp"] = 1
        elif 36.1 <= temp <= 38.0:
            breakdown["Temp"] = 0
        elif 38.1 <= temp <= 39.0:
            breakdown["Temp"] = 1
        else:
            breakdown["Temp"] = 2
    else:
        breakdown["Temp"] = 0

    total_score = sum(breakdown.values())

    # Clinical Risk Level & Monitoring Frequency Target
    if total_score >= 7:
        risk_level = "High"
        monitoring_target = "Continuous physiological monitoring; immediate emergency review by critical care / senior clinician."
    elif total_score >= 5:
        risk_level = "Medium"
        monitoring_target = "Urgent clinical review; minimum 1-hourly vital monitoring."
    elif any(v == 3 for v in breakdown.values()):
        risk_level = "Low-Medium"
        monitoring_target = "Urgent ward-based medical review; minimum 4-hourly vital monitoring."
    else:
        risk_level = "Low"
        monitoring_target = "Routine clinical care; 4-12 hourly vital monitoring."

    return {
        "news2_score": total_score,
        "risk_level": risk_level,
        "monitoring_frequency": monitoring_target,
        "breakdown": breakdown
    }


def check_drug_allergy_contraindications(patient_allergies: List[Any], candidate_medications: List[Any]) -> List[Dict[str, Any]]:
    """
    Deterministic clinical safety gate: cross-checks candidate medications against
    documented patient allergies to detect severe contraindications and anaphylaxis risks.
    """
    CROSS_REACTIVITY_MATRIX = {
        'penicillin': {
            'synonyms': ['penicillin', 'penicillin v', 'penicillin g', 'amoxicillin', 'ampicillin', 'piperacillin', 'flucloxacillin', 'beta-lactam', '91936005', '764146007'],
            'contraindicated_meds': ['co-amoxiclav', 'amoxicillin', 'ampicillin', 'augmentin', 'piperacillin', 'tazocin', 'flucloxacillin', 'benzylpenicillin', '617296', '372687004'],
            'precaution_meds': ['cephalexin', 'cefuroxime', 'ceftriaxone', 'cefotaxime', 'cephalosporin'],
            'severity': 'CRITICAL',
            'reason': 'Direct cross-reactivity with beta-lactam core: high risk of fatal anaphylaxis.'
        },
        'nsaid': {
            'synonyms': ['nsaid', 'aspirin', 'ibuprofen', 'naproxen', 'diclofenac', 'ketorolac', 'mefenamic acid'],
            'contraindicated_meds': ['aspirin', 'ibuprofen', 'naproxen', 'diclofenac', 'ketorolac', 'celecoxib'],
            'precaution_meds': ['paracetamol'],
            'severity': 'HIGH',
            'reason': 'Cross-reactivity via COX-1 inhibition: risk of acute bronchospasm and severe angioedema.'
        },
        'sulfa': {
            'synonyms': ['sulfa', 'sulfonamide', 'sulfamethoxazole', 'bactrim', 'septra', 'co-trimoxazole'],
            'contraindicated_meds': ['trimethoprim-sulfamethoxazole', 'co-trimoxazole', 'sulfamethoxazole', 'sulfadiazine', 'sulfasalazine'],
            'precaution_meds': [],
            'severity': 'HIGH',
            'reason': 'Sulfonamide arylamine cross-reactivity: risk of Stevens-Johnson syndrome or anaphylaxis.'
        }
    }

    alerts: List[Dict[str, Any]] = []

    norm_allergies: List[str] = []
    for a in patient_allergies or []:
        if isinstance(a, str):
            norm_allergies.append(a.lower())
        elif isinstance(a, dict):
            text = (a.get('text') or a.get('name') or a.get('display') or '').lower()
            code = (a.get('code') or '').lower()
            norm_allergies.extend([text, code])
            for coding in a.get('coding', []):
                norm_allergies.append((coding.get('code') or '').lower())
                norm_allergies.append((coding.get('display') or '').lower())

    norm_meds: List[str] = []
    for m in candidate_medications or []:
        if isinstance(m, str):
            norm_meds.append(m.lower())
        elif isinstance(m, dict):
            text = (m.get('text') or m.get('display') or m.get('name') or '').lower()
            code = (m.get('code') or '').lower()
            norm_meds.extend([text, code])
            for coding in m.get('coding', []):
                norm_meds.append((coding.get('code') or '').lower())
                norm_meds.append((coding.get('display') or '').lower())

    for group_key, rule in CROSS_REACTIVITY_MATRIX.items():
        matched_allergy = None
        for syn in rule['synonyms']:
            if any(syn in a for a in norm_allergies if a):
                matched_allergy = syn
                break

        if matched_allergy:
            for med in norm_meds:
                if not med:
                    continue
                for c_med in rule['contraindicated_meds']:
                    if c_med in med:
                        alerts.append({
                            'severity': rule['severity'],
                            'allergen': matched_allergy.capitalize(),
                            'medication': med.capitalize(),
                            'alert_type': 'CONTRAINDICATION',
                            'message': f"CDS GATE INTERCEPTED: Documented allergy to '{matched_allergy}' contraindicates candidate medication '{med}'. {rule['reason']}"
                        })
                        break
                for p_med in rule['precaution_meds']:
                    if p_med in med:
                        alerts.append({
                            'severity': 'WARNING',
                            'allergen': matched_allergy.capitalize(),
                            'medication': med.capitalize(),
                            'alert_type': 'PRECAUTION',
                            'message': f"CDS WARNING: Documented allergy to '{matched_allergy}' warrants high caution with related drug '{med}'."
                        })
                        break

    return alerts


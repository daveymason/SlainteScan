"""Deterministic Terminology Resolution for Slainte-Scan-MCP.

Maps clinical terms to SNOMED-CT codes and vital signs/observations to LOINC codes.
Enforces strict deterministic coding without LLM hallucination.
"""
from typing import Dict, Any, Optional

# Standard LOINC Mappings for Vital Signs & Triage Observations
LOINC_MAP: Dict[str, Dict[str, str]] = {
    "systolic_bp": {
        "code": "8480-6",
        "system": "http://loinc.org",
        "display": "Systolic blood pressure",
        "unit": "mmHg"
    },
    "diastolic_bp": {
        "code": "8462-4",
        "system": "http://loinc.org",
        "display": "Diastolic blood pressure",
        "unit": "mmHg"
    },
    "blood_pressure_panel": {
        "code": "85354-9",
        "system": "http://loinc.org",
        "display": "Blood pressure panel with all children optional",
        "unit": "mmHg"
    },
    "heart_rate": {
        "code": "8867-4",
        "system": "http://loinc.org",
        "display": "Heart rate",
        "unit": "bpm"
    },
    "spo2": {
        "code": "59408-5",
        "system": "http://loinc.org",
        "display": "Oxygen saturation in Arterial blood by Pulse oximetry",
        "unit": "%"
    },
    "respiratory_rate": {
        "code": "9279-1",
        "system": "http://loinc.org",
        "display": "Respiratory rate",
        "unit": "/min"
    },
    "temperature": {
        "code": "8310-5",
        "system": "http://loinc.org",
        "display": "Body temperature",
        "unit": "Cel"
    },
    "pain": {
        "code": "72514-3",
        "system": "http://loinc.org",
        "display": "Pain severity - 0-10 verbal numeric rating [Score] - Reported",
        "unit": "{score}"
    },
    "triage_category": {
        "code": "75540-5",
        "system": "http://loinc.org",
        "display": "Manchester Triage System acuity score",
        "unit": "category"
    }
}

# Standard SNOMED-CT Mappings for Emergency Presentations & Complaints
SNOMED_MAP: Dict[str, Dict[str, str]] = {
    "chest pain": {"code": "29857009", "system": "http://snomed.info/sct", "display": "Chest pain"},
    "angina": {"code": "194828000", "system": "http://snomed.info/sct", "display": "Angina pectoris"},
    "shortness of breath": {"code": "267036007", "system": "http://snomed.info/sct", "display": "Dyspnea"},
    "sob": {"code": "267036007", "system": "http://snomed.info/sct", "display": "Dyspnea"},
    "dyspnea": {"code": "267036007", "system": "http://snomed.info/sct", "display": "Dyspnea"},
    "asthma attack": {"code": "281239006", "system": "http://snomed.info/sct", "display": "Asthma exacerbation"},
    "fever": {"code": "386661006", "system": "http://snomed.info/sct", "display": "Fever"},
    "pyrexia": {"code": "386661006", "system": "http://snomed.info/sct", "display": "Fever"},
    "abdominal pain": {"code": "21522000", "system": "http://snomed.info/sct", "display": "Abdominal pain"},
    "stomach pain": {"code": "21522000", "system": "http://snomed.info/sct", "display": "Abdominal pain"},
    "headache": {"code": "25064002", "system": "http://snomed.info/sct", "display": "Headache"},
    "severe headache": {"code": "25064002", "system": "http://snomed.info/sct", "display": "Headache"},
    "cough": {"code": "49727002", "system": "http://snomed.info/sct", "display": "Cough"},
    "tachycardia": {"code": "3424008", "system": "http://snomed.info/sct", "display": "Tachycardia"},
    "bradycardia": {"code": "48867003", "system": "http://snomed.info/sct", "display": "Bradycardia"},
    "hypotension": {"code": "45007003", "system": "http://snomed.info/sct", "display": "Hypotension"},
    "hypertension": {"code": "38341003", "system": "http://snomed.info/sct", "display": "Hypertension"},
    "syncope": {"code": "271594007", "system": "http://snomed.info/sct", "display": "Syncope"},
    "fainting": {"code": "271594007", "system": "http://snomed.info/sct", "display": "Syncope"},
    "dizziness": {"code": "404640003", "system": "http://snomed.info/sct", "display": "Dizziness"},
    "nausea": {"code": "422400008", "system": "http://snomed.info/sct", "display": "Nausea"},
    "vomiting": {"code": "422400008", "system": "http://snomed.info/sct", "display": "Nausea and vomiting"},
    "trauma": {"code": "417746004", "system": "http://snomed.info/sct", "display": "Traumatic injury"},
    "laceration": {"code": "312608009", "system": "http://snomed.info/sct", "display": "Laceration"},
    "fracture": {"code": "125605004", "system": "http://snomed.info/sct", "display": "Fracture of bone"},
    "burn": {"code": "125666000", "system": "http://snomed.info/sct", "display": "Burn injury"},
    "allergic reaction": {"code": "418363000", "system": "http://snomed.info/sct", "display": "Allergic reaction"},
    "anaphylaxis": {"code": "39579001", "system": "http://snomed.info/sct", "display": "Anaphylaxis"},
    "altered mental status": {"code": "419284004", "system": "http://snomed.info/sct", "display": "Altered mental state"},
    "confusion": {"code": "40917007", "system": "http://snomed.info/sct", "display": "Clouded consciousness"},
    "seizure": {"code": "91175000", "system": "http://snomed.info/sct", "display": "Seizure"},
    "stroke symptoms": {"code": "230690007", "system": "http://snomed.info/sct", "display": "Stroke"},
}

def resolve_terminology(term_type: str, query: str) -> Dict[str, Any]:
    """
    Deterministically resolves a query to its official standard terminology.
    - term_type: 'vital' (returns LOINC) or 'clinical'/'condition' (returns SNOMED-CT).
    """
    clean_query = query.strip().lower()
    
    if term_type.lower() in ("vital", "observation", "loinc"):
        # Match LOINC
        # Try direct key
        if clean_query in LOINC_MAP:
            return {"found": True, "type": "LOINC", **LOINC_MAP[clean_query]}
        # Try alias lookup
        aliases = {
            "systolic": "systolic_bp",
            "sys_bp": "systolic_bp",
            "sbp": "systolic_bp",
            "diastolic": "diastolic_bp",
            "dia_bp": "diastolic_bp",
            "dbp": "diastolic_bp",
            "bp": "blood_pressure_panel",
            "pulse": "heart_rate",
            "hr": "heart_rate",
            "oxygen": "spo2",
            "o2": "spo2",
            "sat": "spo2",
            "rr": "respiratory_rate",
            "resp": "respiratory_rate",
            "temp": "temperature",
            "pain_score": "pain",
            "mts": "triage_category"
        }
        for alias, target in aliases.items():
            if alias in clean_query:
                return {"found": True, "type": "LOINC", **LOINC_MAP[target]}
        return {
            "found": False,
            "type": "LOINC",
            "query": query,
            "error": f"No deterministic LOINC mapping found for vital: '{query}'"
        }

    # Otherwise clinical condition / complaint (SNOMED-CT)
    # Direct match
    if clean_query in SNOMED_MAP:
        return {"found": True, "type": "SNOMED-CT", **SNOMED_MAP[clean_query]}
    
    # Substring search
    for key, mapping in SNOMED_MAP.items():
        if key in clean_query or clean_query in key:
            return {"found": True, "type": "SNOMED-CT", **mapping}
            
    # Default fallback clinical finding
    return {
        "found": True,
        "type": "SNOMED-CT",
        "code": "404684003",
        "system": "http://snomed.info/sct",
        "display": f"Clinical finding: {query}",
        "fallback": True
    }

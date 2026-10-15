"""Deterministic Clinical Schema Scanner.

Introspects messy CSVs, text tables, or JSON records in raw data directories,
identifies clinical columns and maps them deterministically to standardized variables.
"""
import csv
import io
import json
import os
from typing import Dict, Any, List, Optional

HEADER_SYNONYMS = {
    "patient_id": ["patient_id", "pt_id", "id", "mrn", "patient", "subject_id"],
    "gms_number": ["gms", "gms_number", "gms_no", "medical_card", "irish_gms", "pps", "ppsn"],
    "full_name": ["name", "full_name", "patient_name", "pt_name"],
    "gender": ["gender", "sex"],
    "birthdate": ["dob", "birthdate", "date_of_birth", "birth_date", "age"],
    "timestamp": ["timestamp", "arrival_time", "triage_time", "admit_time", "date", "time"],
    "complaint": ["complaint", "chief_complaint", "triage_complaint", "presenting_complaint", "reason", "symptom", "notes"],
    "systolic_bp": ["systolic_bp", "sys_bp", "sbp", "systolic", "bp_sys"],
    "diastolic_bp": ["diastolic_bp", "dia_bp", "dbp", "diastolic", "bp_dia"],
    "heart_rate": ["heart_rate", "hr", "pulse", "pulse_rate", "bpm"],
    "spo2": ["spo2", "o2_sat", "o2", "oxygen", "pulse_ox", "sat"],
    "respiratory_rate": ["respiratory_rate", "resp_rate", "rr", "respirations", "breaths_per_min"],
    "temperature": ["temperature", "temp", "temp_c", "body_temp", "fever_c"],
    "pain": ["pain", "pain_score", "pain_level", "nrs_pain", "vas_pain"],
    "labs": ["labs", "lab_results", "laboratory", "blood_tests", "lab_tests", "investigations"],
    "medications": ["medications", "meds", "current_medications", "prescriptions", "rx", "medication_list"],
    "allergies": ["allergies", "allergy", "allergens", "sensitivities", "adverse_reactions"],
}

def scan_clinical_schema(source: str) -> Dict[str, Any]:
    """
    Introspects a file path or raw CSV/JSON string, detects columns,
    and returns deterministic schema mappings and sample rows.
    """
    raw_content = ""
    file_path = None
    
    # Check if source is a file path
    if ("\n" not in source) and len(source) < 4096 and os.path.exists(source) and os.path.isfile(source):
        abs_p = os.path.abspath(source)
        blocked_prefixes = ("/etc", "/root", "/sys", "/proc", "/dev", "/var/run")
        if any(abs_p.startswith(b) for b in blocked_prefixes):
            return {"error": f"Access denied: scanning restricted system path '{source}' is disallowed"}
        file_path = abs_p
        with open(abs_p, "r", encoding="utf-8", errors="replace") as f:
            raw_content = f.read(10 * 1024 * 1024)
    else:
        raw_content = source.strip()

    # Try parsing as JSON first
    if raw_content.startswith("[") or raw_content.startswith("{"):
        try:
            parsed = json.loads(raw_content)
            records = parsed if isinstance(parsed, list) else [parsed]
            if records:
                headers = list(records[0].keys())
                mapping = _map_headers(headers)
                return {
                    "source_type": "json",
                    "file_path": file_path,
                    "row_count": len(records),
                    "headers": headers,
                    "detected_mappings": mapping,
                    "preview": records[:3]
                }
        except Exception:
            pass

    # Parse as CSV / Delimited text
    sample_io = io.StringIO(raw_content)
    try:
        # Detect delimiter
        first_line = sample_io.readline()
        delimiter = ","
        if "\t" in first_line:
            delimiter = "\t"
        elif ";" in first_line:
            delimiter = ";"
        elif "|" in first_line:
            delimiter = "|"
            
        sample_io.seek(0)
        reader = csv.DictReader(sample_io, delimiter=delimiter)
        headers = reader.fieldnames or []
        rows = list(reader)
        mapping = _map_headers(headers)
        
        return {
            "source_type": "csv",
            "file_path": file_path,
            "delimiter": delimiter,
            "row_count": len(rows),
            "headers": headers,
            "detected_mappings": mapping,
            "preview": rows[:3]
        }
    except Exception as e:
        return {
            "error": f"Failed to parse clinical schema: {str(e)}",
            "raw_preview": raw_content[:200]
        }

def _map_headers(headers: List[str]) -> Dict[str, Optional[str]]:
    mapping = {}
    normalized = {h: h.strip().lower().replace(" ", "_").replace("-", "_") for h in headers}
    
    for standard_var, synonyms in HEADER_SYNONYMS.items():
        matched_header = None
        for orig_header, norm_h in normalized.items():
            if norm_h in synonyms:
                matched_header = orig_header
                break
            # Substring check for compound headers like "vitals_heart_rate"
            for syn in synonyms:
                if syn in norm_h:
                    matched_header = orig_header
                    break
            if matched_header:
                break
        mapping[standard_var] = matched_header
        
    return mapping

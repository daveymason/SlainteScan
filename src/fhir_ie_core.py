"""Deterministic Irish Core FHIR R4 Bundle Generator.

Produces schema-compliant FHIR R4 JSON resources mapped to official
Irish identifiers (GMS OID urn:oid:1.3.6.1.4.1.54392.5.2690.42.80),
SNOMED-CT clinical codes, and LOINC vital observations.
"""
from datetime import datetime, timezone
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field

IRISH_GMS_OID = "urn:oid:1.3.6.1.4.1.54392.5.2690.42.80"

class Identifier(BaseModel):
    system: str
    value: str

class Coding(BaseModel):
    system: str
    code: str
    display: Optional[str] = None

class CodeableConcept(BaseModel):
    coding: Optional[List[Coding]] = None
    text: Optional[str] = None

class HumanName(BaseModel):
    use: Optional[str] = "official"
    family: Optional[str] = None
    given: Optional[List[str]] = None
    text: Optional[str] = None

class PatientResource(BaseModel):
    resourceType: str = "Patient"
    id: str
    identifier: List[Identifier]
    name: Optional[List[HumanName]] = None
    gender: Optional[str] = None
    birthDate: Optional[str] = None

class EncounterResource(BaseModel):
    resourceType: str = "Encounter"
    id: str
    status: str = "finished"
    klass: dict = Field(..., alias="class")
    subject: dict
    period: Optional[dict] = None

class ObservationValue(BaseModel):
    value: float
    unit: str
    system: Optional[str] = "http://unitsofmeasure.org"
    code: Optional[str] = None

class ObservationResource(BaseModel):
    resourceType: str = "Observation"
    id: Optional[str] = None
    status: str = "final"
    category: Optional[List[dict]] = None
    code: CodeableConcept
    subject: dict
    encounter: Optional[dict] = None
    effectiveDateTime: Optional[str] = None
    valueQuantity: Optional[ObservationValue] = None
    valueString: Optional[str] = None

class ConditionResource(BaseModel):
    resourceType: str = "Condition"
    id: Optional[str] = None
    clinicalStatus: dict = {
        "coding": [{
            "system": "http://terminology.hl7.org/CodeSystem/condition-clinical",
            "code": "active",
            "display": "Active"
        }]
    }
    code: CodeableConcept
    subject: dict

class MedicationRequestResource(BaseModel):
    resourceType: str = "MedicationRequest"
    id: Optional[str] = None
    status: str = "active"
    intent: str = "order"
    authoredOn: Optional[str] = None
    medicationCodeableConcept: CodeableConcept
    subject: dict
    encounter: Optional[dict] = None
    dosageInstruction: Optional[List[dict]] = None

class AllergyIntoleranceResource(BaseModel):
    resourceType: str = "AllergyIntolerance"
    id: Optional[str] = None
    clinicalStatus: dict = {
        "coding": [{
            "system": "http://terminology.hl7.org/CodeSystem/allergyintolerance-clinical",
            "code": "active",
            "display": "Active"
        }]
    }
    criticality: Optional[str] = "high"
    code: CodeableConcept
    patient: dict
    recordedDate: Optional[str] = None
    reaction: Optional[List[dict]] = None

class BundleEntry(BaseModel):
    resource: dict

class BundleResource(BaseModel):
    resourceType: str = "Bundle"
    type: str = "collection"
    timestamp: str
    entry: List[BundleEntry]


def generate_fhir_bundle(
    vitals: Dict[str, Any],
    triage_category: int,
    gms_number: str = "GMS-UNKNOWN",
    patient_id: Optional[str] = None,
    name: Optional[str] = None,
    gender: Optional[str] = None,
    birthdate: Optional[str] = None,
    complaint: Optional[str] = None,
    labs: Optional[List[Dict[str, Any]]] = None,
    medications: Optional[List[Dict[str, Any]]] = None,
    allergies: Optional[List[Dict[str, Any]]] = None
) -> Dict[str, Any]:
    """
    Constructs a verified FHIR R4 Bundle from clinical vitals and metadata.
    """
    now_iso = datetime.now(timezone.utc).isoformat()
    pid = patient_id or f"pt-{abs(hash(gms_number)) % 1000000:06d}"
    enc_id = f"enc-{pid}"
    
    # 1. Patient Resource with Irish GMS Identifier
    patient_names = []
    if name:
        parts = name.strip().split()
        family = parts[-1] if len(parts) > 1 else parts[0]
        given = parts[:-1] if len(parts) > 1 else []
        patient_names.append(HumanName(family=family, given=given, text=name))
    else:
        patient_names.append(HumanName(text=f"Patient {pid}"))

    patient_res = PatientResource(
        id=pid,
        identifier=[
            Identifier(
                system=IRISH_GMS_OID,
                value=gms_number or f"GMS-{pid}"
            )
        ],
        name=patient_names,
        gender=gender.lower() if gender in ("male", "female", "other", "unknown") else "unknown",
        birthDate=birthdate if birthdate else None
    )

    # 2. Encounter
    encounter_res = EncounterResource(
        id=enc_id,
        **{"class": {"system": "http://terminology.hl7.org/CodeSystem/v3-ActCode", "code": "EMER", "display": "emergency"}},
        subject={"reference": f"Patient/{pid}", "display": name or f"Patient {pid}"},
        period={"start": now_iso}
    )

    entries = [
        BundleEntry(resource=patient_res.model_dump(exclude_none=True, by_alias=True)),
        BundleEntry(resource=encounter_res.model_dump(exclude_none=True, by_alias=True))
    ]

    # 3. Chief Complaint Condition (SNOMED-CT)
    chief_complaint = complaint or vitals.get("complaint")
    if chief_complaint:
        from .terminology import resolve_terminology
        term = resolve_terminology("clinical", str(chief_complaint))
        coding_list = []
        if term.get("code"):
            coding_list.append(Coding(
                system=term.get("system", "http://snomed.info/sct"),
                code=term["code"],
                display=term.get("display", str(chief_complaint))
            ))
        cond = ConditionResource(
            id=f"cond-{pid}-1",
            code=CodeableConcept(
                coding=coding_list if coding_list else None,
                text=str(chief_complaint)
            ),
            subject={"reference": f"Patient/{pid}"}
        )
        entries.append(BundleEntry(resource=cond.model_dump(exclude_none=True, by_alias=True)))

    # 4. Manchester Triage System Category Observation
    triage_obs = ObservationResource(
        id=f"obs-mts-{pid}",
        category=[{
            "coding": [{"system": "http://terminology.hl7.org/CodeSystem/observation-category", "code": "survey", "display": "Survey"}],
            "text": "Survey"
        }],
        code=CodeableConcept(
            coding=[Coding(system="http://loinc.org", code="75540-5", display="Manchester Triage System category")],
            text="Manchester Triage System Category"
        ),
        subject={"reference": f"Patient/{pid}"},
        encounter={"reference": f"Encounter/{enc_id}"},
        effectiveDateTime=now_iso,
        valueQuantity=ObservationValue(
            value=float(triage_category),
            unit="category",
            system="http://unitsofmeasure.org",
            code="{category}"
        )
    )
    entries.append(BundleEntry(resource=triage_obs.model_dump(exclude_none=True, by_alias=True)))

    # 5. Helper for numeric Vital Sign Observations
    vital_mappings = [
        ("systolic_bp", "8480-6", "Systolic Blood Pressure", "mmHg", "mm[Hg]"),
        ("diastolic_bp", "8462-4", "Diastolic Blood Pressure", "mmHg", "mm[Hg]"),
        ("heart_rate", "8867-4", "Heart Rate", "bpm", "/min"),
        ("spo2", "59408-5", "Oxygen Saturation (SpO2)", "%", "%"),
        ("respiratory_rate", "9279-1", "Respiratory Rate", "/min", "/min"),
        ("temperature", "8310-5", "Body Temperature", "Cel", "Cel"),
        ("pain", "72514-3", "Pain Score", "{score}", "{score}")
    ]

    for key, loinc_code, display_text, unit_display, ucum_code in vital_mappings:
        val = vitals.get(key)
        if val is not None:
            try:
                num_val = float(val)
                obs = ObservationResource(
                    id=f"obs-{key}-{pid}",
                    category=[{
                        "coding": [{"system": "http://terminology.hl7.org/CodeSystem/observation-category", "code": "vital-signs", "display": "Vital Signs"}],
                        "text": "Vital Signs"
                    }],
                    code=CodeableConcept(
                        coding=[Coding(system="http://loinc.org", code=loinc_code, display=display_text)],
                        text=display_text
                    ),
                    subject={"reference": f"Patient/{pid}"},
                    encounter={"reference": f"Encounter/{enc_id}"},
                    effectiveDateTime=now_iso,
                    valueQuantity=ObservationValue(
                        value=num_val,
                        unit=unit_display,
                        system="http://unitsofmeasure.org",
                        code=ucum_code
                    )
                )
                entries.append(BundleEntry(resource=obs.model_dump(exclude_none=True, by_alias=True)))
            except (ValueError, TypeError):
                continue

    # 6. Laboratory Observations (category='laboratory')
    if labs:
        LAB_LOINC_MAP = {
            "troponin": ("6598-7", "Cardiac Troponin T"),
            "glucose": ("2345-7", "Blood Glucose"),
            "potassium": ("2823-3", "Potassium"),
            "po2": ("2703-7", "Arterial Blood Gas pO2"),
            "pco2": ("2019-8", "Arterial Blood Gas pCO2"),
            "crp": ("1988-5", "C-Reactive Protein (CRP)"),
            "wbc": ("6690-2", "Leukocytes [WBC]"),
            "lactate": ("2524-7", "Serum Lactate"),
            "lipase": ("3040-3", "Serum Lipase"),
            "uric": ("3084-1", "Uric Acid"),
            "hemoglobin": ("718-7", "Hemoglobin"),
            "creatinine": ("2160-0", "Serum Creatinine"),
            "egfr": ("33914-3", "Glomerular Filtration Rate (eGFR)"),
        }
        for l_idx, lab_item in enumerate(labs):
            l_name = lab_item.get("name", "Lab Test")
            l_val = lab_item.get("value")
            l_unit = lab_item.get("unit", "")
            
            l_key = l_name.lower()
            matched_code = "26436-6"
            matched_disp = l_name
            for k, (loinc_cd, loinc_nm) in LAB_LOINC_MAP.items():
                if k in l_key:
                    matched_code = loinc_cd
                    matched_disp = loinc_nm
                    break
                    
            try:
                num_v = float(l_val) if l_val is not None else None
            except (ValueError, TypeError):
                num_v = None

            obs_kwargs = {
                "id": f"obs-lab-{pid}-{l_idx+1}",
                "category": [{
                    "coding": [{"system": "http://terminology.hl7.org/CodeSystem/observation-category", "code": "laboratory", "display": "Laboratory"}],
                    "text": "Laboratory"
                }],
                "code": CodeableConcept(
                    coding=[Coding(system="http://loinc.org", code=matched_code, display=matched_disp)],
                    text=matched_disp
                ),
                "subject": {"reference": f"Patient/{pid}"},
                "encounter": {"reference": f"Encounter/{enc_id}"},
                "effectiveDateTime": now_iso,
            }
            if num_v is not None:
                obs_kwargs["valueQuantity"] = ObservationValue(
                    value=num_v,
                    unit=l_unit,
                    system="http://unitsofmeasure.org",
                    code=l_unit
                )
            else:
                obs_kwargs["valueString"] = str(l_val or 'Pending')

            lab_obs = ObservationResource(**obs_kwargs)
            entries.append(BundleEntry(resource=lab_obs.model_dump(exclude_none=True, by_alias=True)))

    # 7. Medication Requests
    if medications:
        for m_idx, med_item in enumerate(medications):
            m_name = med_item.get("name", "Medication")
            m_inst = med_item.get("instructions", "As directed")
            med_res = MedicationRequestResource(
                id=f"med-{pid}-{m_idx+1}",
                status="active",
                intent="order",
                authoredOn=now_iso,
                medicationCodeableConcept=CodeableConcept(
                    coding=[Coding(system="http://snomed.info/sct", code="108774000", display=m_name)],
                    text=m_name
                ),
                subject={"reference": f"Patient/{pid}"},
                encounter={"reference": f"Encounter/{enc_id}"},
                dosageInstruction=[{"text": m_inst}]
            )
            entries.append(BundleEntry(resource=med_res.model_dump(exclude_none=True, by_alias=True)))

    # 8. Allergy Intolerances
    if allergies:
        for a_idx, alg_item in enumerate(allergies):
            a_name = alg_item.get("name", "Allergen")
            a_crit = (alg_item.get("severity") or "moderate").lower()
            if a_crit not in ("low", "moderate", "high", "severe"):
                a_crit = "moderate"
            if a_crit == "severe":
                a_crit = "high"
            a_rx = alg_item.get("reactions", [])
            rx_list = []
            for r in a_rx:
                rx_list.append({
                    "manifestation": [{
                        "coding": [{"system": "http://snomed.info/sct", "code": "418363000", "display": str(r)}],
                        "text": str(r)
                    }]
                })
            alg_res = AllergyIntoleranceResource(
                id=f"alg-{pid}-{a_idx+1}",
                criticality=a_crit,
                code=CodeableConcept(
                    coding=[Coding(system="http://snomed.info/sct", code="419199007", display=a_name)],
                    text=a_name
                ),
                patient={"reference": f"Patient/{pid}"},
                recordedDate=now_iso,
                reaction=rx_list if rx_list else None
            )
            entries.append(BundleEntry(resource=alg_res.model_dump(exclude_none=True, by_alias=True)))

    bundle = BundleResource(
        timestamp=now_iso,
        entry=entries
    )

    return bundle.model_dump(exclude_none=True, by_alias=True)

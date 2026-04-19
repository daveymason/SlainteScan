from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, Field

class Identifier(BaseModel):
    system: str
    value: str

class CodeableConcept(BaseModel):
    text: str

class Patient(BaseModel):
    resourceType: str = "Patient"
    id: str
    identifier: List[Identifier]
    
    @classmethod
    def create_irish_patient(cls, gms_number: str, patient_id: str = "1"):
        """
        The Patient identifier must map the GMS (Medical Card) number 
        to the official Irish OID: urn:oid:1.3.6.1.4.1.54392.5.2690.42.80.
        """
        return cls(
            id=patient_id,
            identifier=[
                Identifier(
                    system="urn:oid:1.3.6.1.4.1.54392.5.2690.42.80",
                    value=gms_number
                )
            ]
        )

class Encounter(BaseModel):
    resourceType: str = "Encounter"
    id: str
    status: str = "finished"
    klass: dict = Field(..., alias="class") # 'class' is reserved in python
    subject: dict # Reference to Patient

class ObservationValue(BaseModel):
    value: float
    unit: str

class Observation(BaseModel):
    resourceType: str = "Observation"
    status: str = "final"
    code: CodeableConcept
    subject: dict
    valueQuantity: Optional[ObservationValue] = None

class BundleEntry(BaseModel):
    resource: BaseModel 

class Bundle(BaseModel):
    resourceType: str = "Bundle"
    type: str = "collection"
    entry: List[BundleEntry]

def generate_fhir_bundle(vitals: dict, category: int, gms_number: str = "GMS-UNKNOWN") -> dict:
    """
    Maps dict + category to valid IE Core FHIR Bundle.
    """
    patient = Patient.create_irish_patient(gms_number)
    
    encounter = Encounter(
        id="enc-1",
        **{"class": {"system": "http://terminology.hl7.org/CodeSystem/v3-ActCode", "code": "EMER"}},
        subject={"reference": f"Patient/{patient.id}"}
    )
    
    entries = [
        BundleEntry(resource=patient),
        BundleEntry(resource=encounter)
    ]
    
    # Map Triage Category Observation
    triage_obs = Observation(
        code=CodeableConcept(text="Manchester Triage System Category"),
        subject={"reference": f"Patient/{patient.id}"},
        valueQuantity=ObservationValue(value=category, unit="category")
    )
    entries.append(BundleEntry(resource=triage_obs))
    
    # Map available vitals
    if vitals.get("systolic_bp") is not None:
        entries.append(BundleEntry(resource=Observation(
            code=CodeableConcept(text="Systolic Blood Pressure"),
            subject={"reference": f"Patient/{patient.id}"},
            valueQuantity=ObservationValue(value=vitals["systolic_bp"], unit="mmHg")
        )))
    if vitals.get("spo2") is not None:
        entries.append(BundleEntry(resource=Observation(
            code=CodeableConcept(text="Oxygen Saturation (SpO2)"),
            subject={"reference": f"Patient/{patient.id}"},
            valueQuantity=ObservationValue(value=vitals["spo2"], unit="%")
        )))
    if vitals.get("heart_rate") is not None:
        entries.append(BundleEntry(resource=Observation(
            code=CodeableConcept(text="Heart Rate"),
            subject={"reference": f"Patient/{patient.id}"},
            valueQuantity=ObservationValue(value=vitals["heart_rate"], unit="bpm")
        )))
        
    bundle = Bundle(entry=entries)
    
    # Return as primitive dict
    return bundle.model_dump(exclude_none=True, by_alias=True)

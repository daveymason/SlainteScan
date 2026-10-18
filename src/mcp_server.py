"""Slainte-Scan-MCP: Model Context Protocol Server for Clinical Interoperability.

Exposes deterministic clinical tooling:
- scan_clinical_schema: Introspects messy CSVs / raw clinical files.
- resolve_terminology: Maps conditions to SNOMED-CT and vitals to LOINC.
- calculate_mts_category: Deterministic Manchester Triage System rules.
- validate_fhir_resource: Strict FHIR R4 schema and semantic validator.
- generate_fhir_bundle: Mathematical Irish Core FHIR R4 bundle compiler.
- ingest_handwritten_note: Handwritten note OCR + multimodal extraction.
"""
import os
import sys
import logging
from typing import Dict, Any, Optional, Union, List
from fastmcp import FastMCP

from .extract_engine import extract_vitals_and_symptoms
from .clinical_rules import calculate_mts_category as _calc_mts, get_mts_details
from .fhir_ie_core import generate_fhir_bundle as _gen_bundle
from .terminology import resolve_terminology as _resolve_term
from .schema_scanner import scan_clinical_schema as _scan_schema
from .fhir_validator import validate_fhir_resource as _validate_fhir

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("Slainte-Scan-MCP")

# Initialize FastMCP Server
mcp = FastMCP("Slainte-Scan-MCP")

@mcp.tool()
def scan_clinical_schema(source: str) -> Dict[str, Any]:
    """
    Introspects raw clinical data files (CSV, JSON, or path in /data/raw/).
    Identifies column headers, normalizes clinical variables, and detects
    patient identifiers, vital signs, complaints, and dates.
    """
    logger.info(f"Scanning clinical schema for: {source[:80]}...")
    return _scan_schema(source)

@mcp.tool()
def resolve_terminology(term_type: str, query: str) -> Dict[str, Any]:
    """
    Deterministically resolves clinical terms without hallucinations:
    - term_type 'vital': Resolves to LOINC code, system, display, and standard unit.
    - term_type 'clinical': Resolves to SNOMED-CT code, system, and display.
    """
    logger.info(f"Resolving terminology ({term_type}): {query}")
    return _resolve_term(term_type, query)

@mcp.tool()
def calculate_mts_category(vitals: Dict[str, Any]) -> Dict[str, Any]:
    """
    Deterministically evaluates Manchester Triage System (MTS) category 1-5.
    Returns category number (1: Immediate to 5: Non-Urgent) and clinical targets.
    """
    logger.info("Calculating MTS category based on vitals.")
    cat = _calc_mts(vitals)
    details = get_mts_details(cat)
    return {
        "category": cat,
        **details
    }

@mcp.tool()
def validate_fhir_resource(resource: Union[Dict[str, Any], str]) -> Dict[str, Any]:
    """
    Validates a FHIR R4 resource or Bundle against strict schema and semantic rules.
    Verifies resourceType, required fields, Irish GMS OID, CodeableConcepts,
    and Observation quantities. Guarantees zero hallucinations.
    """
    logger.info("Validating FHIR R4 resource integrity.")
    return _validate_fhir(resource)

@mcp.tool()
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
    Compiles a valid FHIR R4 collection Bundle with Irish GMS Patient,
    Emergency Encounter, SNOMED-CT Condition, LOINC Observations,
    MedicationRequests, and AllergyIntolerances.
    """
    logger.info(f"Generating FHIR Bundle for patient: {patient_id or gms_number}")
    bundle = _gen_bundle(
        vitals=vitals,
        triage_category=triage_category,
        gms_number=gms_number,
        patient_id=patient_id,
        name=name,
        gender=gender,
        birthdate=birthdate,
        complaint=complaint,
        labs=labs,
        medications=medications,
        allergies=allergies
    )
    # Auto-validate to assure zero-defect output
    val = _validate_fhir(bundle)
    return {
        "bundle": bundle,
        "validation": val
    }

@mcp.tool()
async def ingest_handwritten_note(image_bytes: bytes) -> Dict[str, Any]:
    """
    Processes raw visual capture of a clinical triage note.
    - Extracts vitals and symptoms via OCR & bounded NLP.
    - Calculates MTS category deterministically.
    - Compiles verified FHIR R4 Bundle.
    """
    logger.info("Executing ingest_handwritten_note.")
    vitals = await extract_vitals_and_symptoms(image_bytes)
    triage_cat = _calc_mts(vitals)
    gms_num = vitals.get("gms_number", "UNKNOWN")
    bundle = _gen_bundle(vitals, triage_cat, gms_num)
    validation = _validate_fhir(bundle)
    return {
        "vitals_extracted": vitals,
        "assigned_triage_category": triage_cat,
        "fhir_bundle": bundle,
        "validation": validation,
        "requires_human_approval": True
    }

if __name__ == "__main__":
    transport = os.environ.get("MCP_TRANSPORT", "sse").lower()
    port = int(os.environ.get("PORT", "8081"))
    if transport == "stdio":
        logger.info("Starting Slainte-Scan-MCP via STDIO transport.")
        mcp.run(transport="stdio")
    else:
        logger.info(f"Starting Slainte-Scan-MCP via SSE on 0.0.0.0:{port}")
        mcp.run(transport="sse", host="0.0.0.0", port=port)

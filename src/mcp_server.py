import os
import logging
from fastmcp import FastMCP
from .extract_engine import extract_vitals_and_symptoms
from .clinical_rules import calculate_mts_category
from .fhir_ie_core import generate_fhir_bundle

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Construct FastMCP application
mcp = FastMCP("Slainte-Scan-MCP")

@mcp.tool()
async def ingest_handwritten_note(image_bytes: bytes) -> dict:
    """
    Processes raw visual capture of a clinical triage note.
    - Extracts context into variables without using inference for clinical decisions.
    - Utilises deterministic equations for category allocation.
    - Generates corresponding FHIR schemas bundle.
    """
    logger.info("Executing `ingest_handwritten_note` tool.")

    # 1. Extract data purely using OCR & bounded NLP wrappers
    vitals_dict = await extract_vitals_and_symptoms(image_bytes)
    
    # 2. Determine triage score strictly via non-LLM math rules
    triage_category = calculate_mts_category(vitals_dict)
    
    # Determine Patient Identifier
    gms_num = vitals_dict.get("gms_number", "UNKNOWN")
    
    # 3. Render payload to IE Core FHIR standards natively
    fhir_bundle = generate_fhir_bundle(vitals_dict, triage_category, gms_num)
    
    # 4. Mandatory Review Enforcement Payload
    return {
        "fhir_bundle": fhir_bundle,
        "assigned_triage_category": triage_category,
        "requires_human_approval": True,
        "message": "Please review and approve the extracted vitals and assigned Triage Category before saving to EHR."
    }

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    logger.info(f"Starting server on port {port} using SSE HTTP transport")
    mcp.run(transport='sse', host="0.0.0.0", port=port)

import os
import logging
from types import MethodType
from fastmcp import FastMCP
import mcp.types as mt
from starlette.middleware import Middleware
from starlette.responses import JSONResponse
from .extract_engine import extract_vitals_and_symptoms
from .clinical_rules import calculate_mts_category
from .fhir_ie_core import generate_fhir_bundle

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Construct FastMCP application
mcp = FastMCP("Slainte-Scan-MCP")

PROMPTOPINION_FHIR_EXTENSION_ID = "ai.promptopinion/fhir-context"
PROMPTOPINION_FHIR_SCOPES = []


def _get_capabilities_with_promptopinion(
    _server,
    notification_options,
    experimental_capabilities,
) -> mt.ServerCapabilities:
    capabilities = _original_get_capabilities(
        notification_options,
        experimental_capabilities,
    )
    existing_extensions = dict(
        (capabilities.model_extra or {}).get("extensions", {})
    )
    return capabilities.model_copy(
        update={
            "extensions": {
                **existing_extensions,
                PROMPTOPINION_FHIR_EXTENSION_ID: {
                    "scopes": PROMPTOPINION_FHIR_SCOPES,
                },
            }
        }
    )


_original_get_capabilities = mcp._mcp_server.get_capabilities
mcp._mcp_server.get_capabilities = MethodType(
    _get_capabilities_with_promptopinion,
    mcp._mcp_server,
)


class APIKeyMiddleware:
    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        expected_api_key = os.environ.get("SLAINTE_API_KEY")
        headers = {
            key.decode("latin-1").lower(): value.decode("latin-1")
            for key, value in scope.get("headers", [])
        }
        provided_api_key = headers.get("x-api-key")

        if not expected_api_key or provided_api_key != expected_api_key:
            response = JSONResponse(
                {"detail": "Unauthorized"},
                status_code=401,
            )
            await response(scope, receive, send)
            return

        await self.app(scope, receive, send)

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
    mcp.run(
        transport="sse",
        host="0.0.0.0",
        port=port,
        middleware=[Middleware(APIKeyMiddleware)],
    )

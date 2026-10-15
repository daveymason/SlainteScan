import os
import json
import base64
import logging
from google.cloud import documentai
from google import genai
from google.genai import types

logger = logging.getLogger(__name__)

async def extract_vitals_and_symptoms(image_bytes: bytes) -> dict:
    """
    1. Uses Document AI for extracting raw text from the handwriting (if processor set).
    2. Uses Vertex AI (Gemini) strictly to parse the text into clinical variables.
    """
    # Bulletproof network decoding: handle str, or bytes containing base64
    if isinstance(image_bytes, str):
        image_bytes = base64.b64decode(image_bytes)
    elif isinstance(image_bytes, bytes):
        # If the bytes themselves are base64 string bytes, decode them
        if image_bytes.startswith(b"/9j/") or image_bytes.startswith(b"iVBORw0KGgo") or image_bytes.startswith(b"JVBERi"):
            image_bytes = base64.b64decode(image_bytes)
            
    # Auto-detect correct mime-type for strict Google validation
    if image_bytes.startswith(b"\xff\xd8"):
        detected_mime_type = "image/jpeg"
    elif image_bytes.startswith(b"\x89PNG"):
        detected_mime_type = "image/png"
    elif image_bytes.startswith(b"%PDF"):
        detected_mime_type = "application/pdf"
    else:
        detected_mime_type = "application/pdf" # Fallback safely for his chat upload
        
    project_id = os.environ.get("GOOGLE_CLOUD_PROJECT") or os.environ.get("GCP_PROJECT")
    if not project_id:
        project_id = "slainte-scan-mcp-99021"
    location = os.environ.get("GCP_LOCATION", "eu") 
    processor_id = os.environ.get("DOC_AI_PROCESSOR_ID")
    
    if not processor_id:
        logger.info("No DOC_AI_PROCESSOR_ID provided. Executing unified OCR + Extraction native via Gemini Multimodal.")
        
        # Initialize Google GenAI Client with explicit API Key
        gemini_api_key = os.environ.get("GEMINI_API_KEY")
        if not gemini_api_key:
            logger.error("GEMINI_API_KEY is not set in environment.")
            return {}
        client = genai.Client(api_key=gemini_api_key)
        
        # Construct multimodal payload
        image_part = types.Part.from_bytes(data=image_bytes, mime_type=detected_mime_type)
        
        prompt = """
        You are purely a data extraction parser acting as a legal medical component. 
        Do NOT make clinical inferences. Read the handwritten note image and extract the requested variables.
        
        Output strictly as a valid JSON object matching this schema. Use null if a value is absent.
        {
          "systolic_bp": integer,
          "spo2": integer,
          "heart_rate": integer,
          "pain": integer,
          "gms_number": string
        }
        """
        
        # Force the LLM to reply purely in JSON so it never breaks our deterministic engine format
        response = client.models.generate_content(
            model="gemini-3.1-pro-preview",
            contents=[image_part, prompt],
            config=types.GenerateContentConfig(response_mime_type="application/json")
        )
        
        try:
            return json.loads(response.text)
        except Exception as e:
            logger.error(f"Failed to parse Gemini output: {e}. Raw Text: {response.text}")
            return {}

    else:
        logger.info("Executing split pipeline (Document AI -> Gemini).")
        # 1. Document AI OCR
        docai_client = documentai.DocumentProcessorServiceClient()
        name = docai_client.processor_path(project_id, location, processor_id)
        
        raw_document = documentai.RawDocument(content=image_bytes, mime_type=detected_mime_type)
        request = documentai.ProcessRequest(name=name, raw_document=raw_document)
        result = docai_client.process_document(request=request)
        ocr_text = result.document.text
        
        # 2. Google AI Studio Semantic Extraction
        gemini_api_key = os.environ.get("GEMINI_API_KEY")
        if not gemini_api_key:
            logger.error("GEMINI_API_KEY is not set in environment.")
            return {}
        client = genai.Client(api_key=gemini_api_key)
        
        prompt = f"""
        You are a data extraction parser. Strip the variables from the following raw OCR text.
        Output strictly as JSON.
        {{
          "systolic_bp": integer,
          "spo2": integer,
          "heart_rate": integer,
          "pain": integer,
          "gms_number": string
        }}
        
        OCR Text:
        {ocr_text}
        """
        
        response = client.models.generate_content(
            model="gemini-3.1-pro-preview",
            contents=prompt,
            config=types.GenerateContentConfig(response_mime_type="application/json")
        )
        
        try:
            return json.loads(response.text)
        except Exception as e:
            logger.error(f"Failed to parse Split-Pipeline Gemini output: {e}")
            return {}

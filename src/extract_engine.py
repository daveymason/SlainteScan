import os
import json
import logging
from google.cloud import documentai
import vertexai
from vertexai.generative_models import GenerativeModel, GenerationConfig, Part

logger = logging.getLogger(__name__)

async def extract_vitals_and_symptoms(image_bytes: bytes) -> dict:
    """
    1. Uses Document AI for extracting raw text from the handwriting (if processor set).
    2. Uses Vertex AI (Gemini) strictly to parse the text into clinical variables.
    """
    project_id = os.environ.get("GOOGLE_CLOUD_PROJECT", "demodayz")
    location = os.environ.get("GCP_LOCATION", "eu") 
    processor_id = os.environ.get("DOC_AI_PROCESSOR_ID")
    
    if not processor_id:
        logger.info("No DOC_AI_PROCESSOR_ID provided. Executing unified OCR + Extraction native via Gemini Multimodal.")
        
        # Initialize Vertex AI for the local Google Cloud project
        # Using europe-west1 as a standard for Irish/EU deployments
        vertexai.init(project=project_id, location="europe-west1")
        
        # Construct multimodal payload
        image_part = Part.from_data(data=image_bytes, mime_type="image/jpeg") 
        model = GenerativeModel("gemini-1.5-pro-001")
        
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
        response = model.generate_content(
            [image_part, prompt],
            generation_config=GenerationConfig(response_mime_type="application/json")
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
        
        raw_document = documentai.RawDocument(content=image_bytes, mime_type="image/jpeg")
        request = documentai.ProcessRequest(name=name, raw_document=raw_document)
        result = docai_client.process_document(request=request)
        ocr_text = result.document.text
        
        # 2. Vertex AI Semantic Extraction
        vertexai.init(project=project_id, location="europe-west1")
        model = GenerativeModel("gemini-1.5-pro-001")
        
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
        
        response = model.generate_content(
            prompt,
            generation_config=GenerationConfig(response_mime_type="application/json")
        )
        
        try:
            return json.loads(response.text)
        except Exception as e:
            logger.error(f"Failed to parse Split-Pipeline Gemini output: {e}")
            return {}

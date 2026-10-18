import os
import base64
from google import genai
from google.genai import types

api_key = os.environ.get("GEMINI_API_KEY")
if not api_key:
    raise RuntimeError("GEMINI_API_KEY environment variable is required.")
client = genai.Client(api_key=api_key)

with open("/home/adman-voids/.gemini/antigravity/brain/3a373fd7-9f46-4de4-b461-27d42a9d0a6e/handwritten_note_1779552079844.png", "rb") as f:
    img_bytes = f.read()

image_part = types.Part.from_bytes(data=img_bytes, mime_type="image/png")

try:
    response = client.models.generate_content(
        model="gemini-3.1-pro-preview",
        contents=[image_part, "What is this?"]
    )
    print("SUCCESS:", response.text)
except Exception as e:
    print("FAILED:", str(e))

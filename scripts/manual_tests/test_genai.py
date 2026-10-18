import os
from google import genai

project_id = "slainte-scan-mcp-99021"
location = "europe-west1"

client = genai.Client(vertexai=True, project=project_id, location=location)

response = client.models.generate_content(
    model="gemini-3.1-pro-preview",
    contents=["Hello, are you working?"]
)

print(response.text)

# Sláinte-Scan MCP (Clinical Support Edition)

A Model Context Protocol (MCP) server designed to act as a secure, legally-compliant interface bridging messy physical clinical notes and interoperable Electronic Health Records (EHR) infrastructure. Engineered specifically for Irish healthcare standards and EU MDR Class IIa regulatory hurdles.

## Technical & Clinical Architecture
- **Language / Framework:** FastMCP & Python 3.11+
- **Infrastructure:** Google Cloud Run (Serverless, public ingress for hackathon testing with app-level API key enforcement).
- **Core Principle - "Intelligence out of the Loop":** Data extraction utilizes GCP Document AI + Vertex AI strictly for identifying numerical values. Clinical triage outcomes are determined via isolated pure-Python code reflecting deterministic logic tables.
- **FHIR Standards:** Hardened Pydantic mappings producing compliant FHIR R4 standard structures with active targeting toward specific native Irish OIDs (`urn:oid:1.3.6.1.4.1.54392.5.2690.42.80` for GMS ID assignments).

## Project Scaffolding
- `src/mcp_server.py`: Houses the FastMCP application and the `@mcp.tool()` hook.
- `src/extract_engine.py`: Stub connections meant for GCP APIs parsing images to deterministic dictionaries.
- `src/clinical_rules.py`: The `if/elif` pure logic block driving Manchester Triage System (MTS) evaluation. No AI models operate here.
- `src/fhir_ie_core.py`: Pydantic configurations defining Patient, Encounter, and Observations rendering `.model_dump()` to JSON standard output.

## Deployment Mechanics (Hackathon Access Mode)

### Google Cloud Deploy
For hackathon testing, Cloud Run can allow unauthenticated ingress while the MCP app enforces an `X-API-Key` header against the `SLAINTE_API_KEY` environment variable.

```bash
gcloud run deploy slainte-scan-mcp \\
  --source . \\
  --region europe-west1 \\
  --port 8080 \\
  --allow-unauthenticated \\
  --set-env-vars SLAINTE_API_KEY=slainte-hackathon-2026
```
*(Ensure you modify `--region` to suit your project infrastructure location appropriately)*

### Verified Deployment Status
Last verified on 2026-04-22.

- Service: `slainte-scan-mcp`
- Region: `europe-west1`
- Live URL: `https://slainte-scan-mcp-316076462477.europe-west1.run.app`
- Access mode: unauthenticated ingress with app-level `X-API-Key` enforcement

Quick connectivity checks:

```bash
curl -i --max-time 5 \
  -H "X-API-Key: slainte-hackathon-2026" \
  https://slainte-scan-mcp-316076462477.europe-west1.run.app/sse
```

Expected result: the SSE endpoint returns `HTTP/2 200` and begins streaming event data.

Missing or incorrect API keys should return `HTTP/2 401`.

### Access Strategy from Client Interfaces
Agents attempting to initiate JSON-RPC communication via FastMCP's SSE wrapper interface must send the shared `X-API-Key` header configured in the Prompt Opinion portal.

Prompt Opinion configuration:

```bash
API Key Header Name: X-API-Key
API Key Header Value: slainte-hackathon-2026
```

Pass this header with every request so traffic can reach the FastMCP app and be accepted by the middleware.

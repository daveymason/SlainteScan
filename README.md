# Sláinte-Scan MCP (Clinical Support Edition)

A Model Context Protocol (MCP) server designed to act as a secure, legally-compliant interface bridging messy physical clinical notes and interoperable Electronic Health Records (EHR) infrastructure. Engineered specifically for Irish healthcare standards and EU MDR Class IIa regulatory hurdles.

## Technical & Clinical Architecture
- **Language / Framework:** FastMCP & Python 3.11+
- **Infrastructure:** Google Cloud Run (Serverless, fully IAM restricted).
- **Core Principle - "Intelligence out of the Loop":** Data extraction utilizes GCP Document AI + Vertex AI strictly for identifying numerical values. Clinical triage outcomes are determined via isolated pure-Python code reflecting deterministic logic tables.
- **FHIR Standards:** Hardened Pydantic mappings producing compliant FHIR R4 standard structures with active targeting toward specific native Irish OIDs (`urn:oid:1.3.6.1.4.1.54392.5.2690.42.80` for GMS ID assignments).

## Project Scaffolding
- `src/mcp_server.py`: Houses the FastMCP application and the `@mcp.tool()` hook.
- `src/extract_engine.py`: Stub connections meant for GCP APIs parsing images to deterministic dictionaries.
- `src/clinical_rules.py`: The `if/elif` pure logic block driving Manchester Triage System (MTS) evaluation. No AI models operate here.
- `src/fhir_ie_core.py`: Pydantic configurations defining Patient, Encounter, and Observations rendering `.model_dump()` to JSON standard output.

## Deployment Mechanics (Security First Focus)

### Google Cloud Deploy
Because of the sensitivity regarding Protected Health Information (PHI) crossing bounds via this service, all traffic is locked out by default.

Initiate the deployment with standard `gcloud` invocations explicitly carrying the `--no-allow-unauthenticated` parameter footprint.

```bash
gcloud run deploy slainte-scan-mcp \\
  --source . \\
  --region europe-west1 \\
  --port 8080 \\
  --no-allow-unauthenticated
```
*(Ensure you modify `--region` to suit your project infrastructure location appropriately)*

### Verified Deployment Status
Last verified on 2026-04-19.

- Service: `slainte-scan-mcp`
- Region: `europe-west1`
- Live URL: `https://slainte-scan-mcp-pu3yqiqtga-ew.a.run.app`
- Access mode: authenticated only

Quick authenticated connectivity check:

```bash
TOKEN=$(gcloud auth print-identity-token)
curl -i --max-time 5 \
  -H "Authorization: Bearer $TOKEN" \
  https://slainte-scan-mcp-pu3yqiqtga-ew.a.run.app/sse
```

Expected result: the SSE endpoint returns `HTTP/2 200` and begins streaming event data.

### Access Strategy from Client Interfaces
Agents attempting to initiate JSON-RPC communication via FastMCP's SSE wrapper interface will fail unless carrying corresponding bearer payloads verified against Google Workspace Service Accounts.

You, or your orchestration agent pipeline toolset, must supply an Identity token generated against an authorized principal:

```bash
gcloud auth print-identity-token
```

Pass this as the `Authorization: Bearer <TOKEN>` header natively inside the context-connecting configurations mapped across on the Prompt Opinion environment interface to bridge calls up toward the tool boundary.

from fastapi import FastAPI, UploadFile, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import uvicorn

# Import your existing backend code
from backend.parse_hl7 import parse_hl7_file
from backend.to_fhir import convert_parsed_hl7_to_fhir
from backend.summarize import (
    summarize_fhir_bundle,
    summarize_fhir_human,
)

app = FastAPI(title="Clinical Converter API")

# Allow frontend to call the API (Next.js on Vercel)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # For production, you can restrict this
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------------------------------
# Models
# ---------------------------------------

class HL7Text(BaseModel):
    hl7: str

class FHIRBundleModel(BaseModel):
    bundle: dict


# ---------------------------------------
# Endpoints
# ---------------------------------------

@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/convert")
def convert_hl7(data: HL7Text):
    """Convert HL7 text → parsed dict → FHIR bundle + deterministic summary"""
    try:
        # Write to a temp file for your existing parser (which expects a file path)
        with open("temp.hl7", "w") as tmp:
            tmp.write(data.hl7)

        parsed = parse_hl7_file("temp.hl7")
        bundle = convert_parsed_hl7_to_fhir(parsed)
        summary = summarize_fhir_bundle(bundle)

        return {
            "parsed": parsed,
            "fhir": bundle,
            "summary_deterministic": summary,
        }

    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/summary-llm")
def llm_summary(data: FHIRBundleModel):
    """Generate LLM-based narrative summary."""
    try:
        text = summarize_fhir_human(data.bundle)
        return {"summary_llm": text}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


from backend.hl7_generate import generate_hl7_message

class GenerateRequest(BaseModel):
    type: str = "adt_random"
    count: int = 1

@app.post("/generate")
def generate_hl7(req: GenerateRequest):
    try:
        messages = []
        for _ in range(req.count):
            msg = generate_hl7_message(req.type)
            messages.append(msg)
        return {"messages": messages}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

# Dev server entrypoint
if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)

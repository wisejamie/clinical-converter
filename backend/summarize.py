import json
from backend.openai_client import client

def summarize_fhir_bundle(bundle: dict, debug: bool = False) -> str:
    """
    Incremental Phase 3 Step 1:
    - Receives a FHIR dict
    - Returns placeholder summary
    - No LLM call yet
    """

    if debug:
        print("\n[DEBUG] summarize_fhir_bundle() called with FHIR bundle:")
        print(json.dumps(bundle, indent=2))

    # Extract what we *can* deterministically (preview)
    patient = bundle["entry"][0]["resource"]
    observations = [
        e["resource"] for e in bundle["entry"]
        if e["resource"]["resourceType"] == "Observation"
    ]

    name = patient["name"][0]["given"][0] + " " + patient["name"][0]["family"]
    dob = patient.get("birthDate", "Not provided")
    sex = patient.get("gender", "Not provided")

    # Basic deterministic text – this will be replaced by LLM in next step
    summary = [
        f"Patient: {name}, DOB: {dob}, Sex: {sex}",
        "",
        "Lab Observations:"
    ]

    for obs in observations:
        code = obs["code"]["coding"][0]["code"]
        text = obs["code"]["coding"][0]["display"]
        value = obs.get("valueQuantity", {}).get("value", "N/A")
        unit = obs.get("valueQuantity", {}).get("unit", "")
        summary.append(f"- {text} ({code}): {value} {unit}")

    return "\n".join(summary)


def summarize_fhir_human(bundle: dict, debug: bool = False) -> str:
    """
    Generate a neutral, human-readable clinical summary from FHIR.
    Uses gpt-4.1-nano for extremely cheap summarization.
    """

    if debug:
        print("\n[DEBUG] summarize_fhir_human() called with FHIR bundle:")
        print(json.dumps(bundle, indent=2))

    # LLM prompt: safe + non-interpretive + neutral
    prompt = f"""
        You are a clinical summarization assistant.

        You will be given a FHIR Bundle in JSON. 
        Your job is to produce a **neutral, factual, non-interpretive** summary of the contained information.
        You MUST NOT:
        - diagnose anything
        - give medical advice
        - explain significance of lab values
        - infer meaning
        - state whether something is normal, abnormal, high, or low

        You MUST:
        - state the facts contained in the FHIR bundle
        - describe the patient (name, sex, birthdate)
        - list each observation (test name, code, value, unit, reference range if available)
        - write clearly and concisely for a human reader
        - avoid all medical interpretation

        Here is the FHIR Bundle:

        {json.dumps(bundle, indent=2)}

        Now produce the neutral summary.
        """

    response = client.chat.completions.create(
        model="gpt-4.1-nano",
        messages=[{"role": "user", "content": prompt}],
    )

    return response.choices[0].message.content
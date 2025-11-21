import json

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

import json
from backend.parse_hl7 import parse_hl7_file
from backend.to_fhir import convert_parsed_hl7_to_fhir

def test_fhir_conversion():
    parsed = parse_hl7_file("samples/hl7/glucose.hl7")
    bundle = convert_parsed_hl7_to_fhir(parsed)

    # Basic checks
    assert bundle["resourceType"] == "Bundle"
    assert len(bundle["entry"]) == 2  # Patient + 1 Observation

    patient = bundle["entry"][0]["resource"]
    obs = bundle["entry"][1]["resource"]

    assert patient["resourceType"] == "Patient"
    assert obs["resourceType"] == "Observation"

    print("\nFHIR BUNDLE:\n", json.dumps(bundle, indent=2))

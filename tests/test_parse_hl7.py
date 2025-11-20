import json
from backend.parse_hl7 import parse_hl7_file

def test_parse_glucose():
    parsed = parse_hl7_file("samples/hl7/glucose.hl7")
    print("\n--- Parsed HL7 ---")
    print(json.dumps(parsed, indent=2))

    assert parsed["patient"]["family"] == "Smith"
    assert len(parsed["observations"]) == 1


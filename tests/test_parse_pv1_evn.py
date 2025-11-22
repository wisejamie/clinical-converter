from backend.parse_hl7 import parse_hl7_file

HL7_SAMPLE = """
MSH|^~\\&|HOSP|GH||DEST|20250101120000||ADT^A01|12345|P|2.3
EVN|A01|20250101120000|^^|||20250101115900
PID|1||123456^^^HOSP^MR||Doe^Jane||19800101|F
PV1|1|O|AMB^^^GeneralHospital||||12345^Smith^John|||||||||||9876543||||||||||||||||||20250101115900|20250101143000
"""

def test_parse_pv1_and_evn(tmp_path):
    hl7_path = tmp_path / "sample.hl7"
    hl7_path.write_text(HL7_SAMPLE.strip())

    parsed = parse_hl7_file(str(hl7_path))

    # PV1
    enc = parsed.get("encounter")
    assert enc is not None
    assert enc["patient_class"] == "O"
    assert enc["location"].startswith("AMB")
    assert enc["attending_doctor"].startswith("12345^Smith")
    assert enc["visit_number"] == "9876543"
    assert enc["admit_time"] == "20250101115900"
    assert enc["discharge_time"] == "20250101143000"

    # EVN
    evn = parsed.get("event")
    assert evn is not None
    assert evn["event_type"] == "A01"
    assert evn["recorded_time"] == "20250101120000"
    assert evn["event_occurred_time"] == "20250101115900"

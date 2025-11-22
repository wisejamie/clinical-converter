# backend/to_fhir.py

import uuid
import json
from typing import Dict, List, Any


# -------------------------------------------------------
# PUBLIC API
# -------------------------------------------------------

def convert_parsed_hl7_to_fhir(parsed: dict, debug: bool = False) -> dict:
    """
    Takes the parsed HL7 dictionary from Phase 1 and converts it to a FHIR R4 Bundle.
    If debug=True, prints detailed step-by-step logs.
    """

    if debug:
        print("\n====== PHASE 2: FHIR CONVERSION START ======")
        print("[DEBUG] Parsed HL7 data:\n", json.dumps(parsed, indent=2))

    # Convert patient
    if debug:
        print("\n[DEBUG] Converting PID → FHIR Patient...")

    patient_fhir = patient_to_fhir(parsed["patient"], debug=debug)

    # Convert observations
    if debug:
        print("\n[DEBUG] Converting OBX segments → FHIR Observations...")

    # Convert encounter (PV1/EVN)
    if debug:
        print("\n[DEBUG] Converting PV1/EVN → FHIR Encounter...")

    encounter_fhir = None
    if parsed.get("encounter"):
        encounter_fhir = encounter_to_fhir(
            parsed.get("encounter"),
            parsed.get("event"),
            patient_fhir["id"],
            debug=debug
        )


    encounter_id = encounter_fhir["id"] if encounter_fhir else None
    obs_fhir = [
        obx_to_fhir(o, patient_fhir["id"], encounter_id)
        for o in parsed["observations"]
    ]

    # Construct bundle
    if debug:
        print("\n[DEBUG] Building final FHIR Bundle...")

    bundle = make_fhir_bundle(patient_fhir, encounter_fhir, obs_fhir)

    if debug:
        print("\n====== FHIR BUNDLE OUTPUT ======")
        print(json.dumps(bundle, indent=2))
        print("====== PHASE 2 COMPLETE ======\n")

    return bundle


# -------------------------------------------------------
# PATIENT
# -------------------------------------------------------

def patient_to_fhir(p: Dict[str, Any], debug: bool = False) -> dict:
    patient_id = f"patient-{uuid.uuid5(uuid.NAMESPACE_DNS, p['mrn'])}"

    if debug:
        print(f"[DEBUG] Creating Patient resource: id={patient_id}")
        print("[DEBUG] PID fields:", p)

    resource = {
        "resourceType": "Patient",
        "id": patient_id,
        "identifier": [
            {
                "system": "http://hospital.example.org/mrn",
                "value": p["mrn"]
            }
        ],
        "name": [
            {
                "family": p["family"],
                "given": [p["given"]],
            }
        ],
        "gender": "female" if p["sex"] == "F" else "male",
        "birthDate": f"{p['dob'][:4]}-{p['dob'][4:6]}-{p['dob'][6:8]}",
    }

    if debug:
        print("[DEBUG] Patient resource created:")
        print(json.dumps(resource, indent=2))

    return resource

# -------------------------------------------------------
# ENCOUNTER
# -------------------------------------------------------

def encounter_to_fhir(pv1: Dict[str, Any],
                      evn: Dict[str, Any] | None,
                      patient_id: str,
                      debug: bool = False) -> dict:

    enc_id = f"enc-{uuid.uuid4()}"
    if debug:
        print(f"[DEBUG] Creating Encounter resource id={enc_id}")
        print("[DEBUG] PV1 fields:", pv1)
        print("[DEBUG] EVN fields:", evn)

    # Class mapping (HL7 → FHIR)
    class_code = pv1.get("patient_class") or "O"
    class_map = {
        "I": "IMP",   # inpatient
        "O": "AMB",   # outpatient
        "E": "EMER",  # emergency
    }
    fhir_class = class_map.get(class_code, "AMB")

    # Encounter period
    start = pv1.get("admit_time")
    end = pv1.get("discharge_time")

    def fmt(ts: str | None):
        if not ts:
            return None
        return f"{ts[:4]}-{ts[4:6]}-{ts[6:8]}T{ts[8:10]}:{ts[10:12]}:{ts[12:14] if len(ts) >= 14 else '00'}"

    resource = {
        "resourceType": "Encounter",
        "id": enc_id,
        "status": "finished" if end else "in-progress",
        "class": {
            "system": "http://terminology.hl7.org/CodeSystem/v3-ActCode",
            "code": fhir_class,
        },
        "subject": {"reference": f"Patient/{patient_id}"},
        "period": {}
    }

    if start:
        resource["period"]["start"] = fmt(start)
    if end:
        resource["period"]["end"] = fmt(end)

    # Location
    if pv1.get("location"):
        resource["location"] = [{
            "location": {"display": pv1["location"]}
        }]

    # Attending doctor
    if pv1.get("attending_doctor"):
        resource["participant"] = [{
            "individual": {
                "display": pv1["attending_doctor"]
            }
        }]

    # EVN → Encounter.type
    if evn and evn.get("event_type"):
        resource["type"] = [{
            "coding": [{
                "system": "http://hl7.org/fhir/v2/0003",
                "code": evn["event_type"],
            }]
        }]

    if debug:
        print("[DEBUG] Encounter resource created:")
        print(json.dumps(resource, indent=2))

    return resource


# -------------------------------------------------------
# OBSERVATION
# -------------------------------------------------------

def obx_to_fhir(obx: Dict[str, Any],
                patient_id: str,
                encounter_id: str | None,
                debug: bool = False) -> dict:
    obs_id = f"obs-{uuid.uuid4()}"

    if debug:
        print(f"\n[DEBUG] Converting OBX → Observation: id={obs_id}")
        print("[DEBUG] OBX fields:", obx)

    low, high = parse_range(obx.get("ref_range"), debug=debug)

    resource = {
        "resourceType": "Observation",
        "id": obs_id,
        "status": "final",
        "code": {
            "coding": [
                {
                    "system": "http://loinc.org",
                    "code": obx["code"],
                    "display": obx["text"],
                }
            ]
        },
        "subject": {"reference": f"Patient/{patient_id}"},
        "encounter": {"reference": f"Encounter/{encounter_id}"} if encounter_id else None,
    }

    # Value section
    if obx["value_type"] == "NM" and obx["value"] is not None:
        if debug:
            print("[DEBUG] OBX value is numeric → using valueQuantity")
        resource["valueQuantity"] = {
            "value": float(obx["value"]),
            "unit": obx["unit"] or "",
        }
    else:
        if debug:
            print("[DEBUG] OBX value is text → using valueString")
        resource["valueString"] = obx["value"] or ""

    # Reference range
    if low is not None and high is not None:
        if debug:
            print(f"[DEBUG] Adding reference range: low={low}, high={high}")
        resource["referenceRange"] = [
            {"low": {"value": low}, "high": {"value": high}}
        ]

    # Abnormal flag (interpretation)
    if obx["flag"]:
        if debug:
            print(f"[DEBUG] Adding abnormal flag: {obx['flag']}")
        resource["interpretation"] = [
            {
                "coding": [
                    {
                        "system": "http://terminology.hl7.org/CodeSystem/v3-ObservationInterpretation",
                        "code": obx["flag"],
                    }
                ]
            }
        ]

    if debug:
        print("[DEBUG] Observation resource created:")
        print(json.dumps(resource, indent=2))

    return resource


# -------------------------------------------------------
# BUNDLE
# -------------------------------------------------------

def make_fhir_bundle(patient: dict,
                     encounter: dict | None,
                     observations: List[dict]) -> dict:

    entries = [{"resource": patient}]
    if encounter:
        entries.append({"resource": encounter})
    entries.extend({"resource": o} for o in observations)

    return {
        "resourceType": "Bundle",
        "type": "collection",
        "entry": entries
    }

# -------------------------------------------------------
# Helpers
# -------------------------------------------------------

def parse_range(range_str: str | None, debug: bool = False):
    if not range_str:
        if debug:
            print("[DEBUG] No reference range provided.")
        return None, None

    if "-" not in range_str:
        if debug:
            print(f"[DEBUG] Could not parse reference range: {range_str}")
        return None, None

    try:
        low, high = range_str.split("-")
        return float(low), float(high)
    except ValueError:
        if debug:
            print(f"[DEBUG] Reference range malformed: {range_str}")
        return None, None

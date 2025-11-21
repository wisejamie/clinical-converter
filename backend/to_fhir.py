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

    obs_fhir = [
        obx_to_fhir(o, patient_fhir["id"], debug=debug)
        for o in parsed["observations"]
    ]

    # Construct bundle
    if debug:
        print("\n[DEBUG] Building final FHIR Bundle...")

    bundle = make_fhir_bundle(patient_fhir, obs_fhir)

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
# OBSERVATION
# -------------------------------------------------------

def obx_to_fhir(obx: Dict[str, Any], patient_id: str, debug: bool = False) -> dict:
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

def make_fhir_bundle(patient: dict, observations: List[dict]) -> dict:
    return {
        "resourceType": "Bundle",
        "type": "collection",
        "entry": [{"resource": patient}] +
                 [{"resource": o} for o in observations]
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

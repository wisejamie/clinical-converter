from typing import List, Dict, Any


def parse_hl7_file(path: str, debug: bool = False) -> dict:
    """
    Very simple HL7 v2 parser for ORU^R01-style messages.
    Pass debug=True to print parsed intermediate values.
    """
    with open(path, "r") as f:
        raw = f.read()

    if debug:
        print("\n[DEBUG] --- RAW HL7 TEXT ---")
        print(raw)

    lines = _split_hl7_lines(raw)

    if debug:
        print("\n[DEBUG] --- NORMALIZED HL7 LINES ---")
        for line in lines:
            print("  ", repr(line))

    # Track first OBR (order) if present
    obr = None

    parsed = {
        "msh": None,
        "patient": None,
        "encounter": None,
        "event": None,
        "orders": [],
        "observations": []
    }


    for line in lines:
        if not line.strip():
            continue
        fields = line.split("|")
        seg = fields[0]

        if debug:
            print(f"\n[DEBUG] Processing segment: {seg}")

        if seg == "PID":
            parsed["patient"] = _parse_pid(fields)
            if debug:
                print("[DEBUG] PID parsed as:", parsed["patient"])

        elif seg == "OBR" and obr is None:
            obr = _parse_obr(fields)
            parsed["orders"].append(obr)
            if debug:
                print("[DEBUG] OBR parsed as:", obr)

        elif seg == "OBX":
            obx = _parse_obx(fields)
            parsed["observations"].append(obx)
            if debug:
                print("[DEBUG] OBX parsed as:", obx)

        elif seg == "PV1":
            parsed["encounter"] = _parse_pv1(fields)

        elif seg == "EVN":
            parsed["event"] = _parse_evn(fields)

    if parsed["patient"] is None:
        raise ValueError("No PID segment found in HL7 message")

    if debug:
        print("\n[DEBUG] --- FINAL PARSED STRUCTURE ---")
        print(parsed)

    return parsed


# -------------------------------------------------
# Line handling
# -------------------------------------------------

def _split_hl7_lines(text: str) -> List[str]:
    """
    Normalize HL7 segment breaks into a list of lines.
    """
    text = text.lstrip("\ufeff")
    text = text.replace("\r\n", "\r").replace("\n", "\r")
    text = text.strip("\r")
    return text.split("\r")


# -------------------------------------------------
# PID
# -------------------------------------------------

def _parse_pid(fields: List[str]) -> Dict[str, Any]:
    mrn = _safe_index(fields, 3)
    name_field = _safe_index(fields, 5)

    family = None
    given = None
    if name_field:
        parts = name_field.split("^")
        family = parts[0] if len(parts) > 0 else None
        given = parts[1] if len(parts) > 1 else None

    dob = _safe_index(fields, 7)
    sex = _safe_index(fields, 8)

    return {
        "mrn": mrn,
        "family": family,
        "given": given,
        "dob": dob,
        "sex": sex,
    }


# -------------------------------------------------
# OBR
# -------------------------------------------------

def _parse_obr(fields: List[str]) -> Dict[str, Any]:
    placer_order = _safe_index(fields, 2)
    filler_order = _safe_index(fields, 3)

    id_field = _safe_index(fields, 4)
    test_name = None
    test_code = None
    if id_field:
        parts = id_field.split("^")
        test_name = parts[0] if len(parts) > 0 else None
        test_code = parts[1] if len(parts) > 1 else None

    specimen_time = _safe_index(fields, 5)
    result_time = _safe_index(fields, 6)
    ordering_provider = _safe_index(fields, 13)

    return {
        "placer_order_number": placer_order,
        "filler_order_number": filler_order,
        "test_code": test_code,
        "test_name": test_name,
        "specimen_time": specimen_time,
        "result_time": result_time,
        "ordering_provider": ordering_provider,
    }


# -------------------------------------------------
# OBX
# -------------------------------------------------

def _parse_obx(fields: List[str]) -> Dict[str, Any]:
    value_type = _safe_index(fields, 2)

    id_field = _safe_index(fields, 3)
    code = None
    text = None
    if id_field:
        parts = id_field.split("^")
        code = parts[0] if len(parts) > 0 else None
        text = parts[1] if len(parts) > 1 else None

    value = _safe_index(fields, 5)
    unit = _safe_index(fields, 6)
    ref_range = _safe_index(fields, 7)
    flag = _safe_index(fields, 8)

    return {
        "code": code,
        "text": text,
        "value_type": value_type,
        "value": value,
        "unit": unit,
        "ref_range": ref_range,
        "flag": flag,
    }

def _parse_pv1(fields: List[str]) -> Dict[str, Any]:
    # Get last two non-empty fields (admit/discharge)
    nonempty = [f for f in fields if f not in ("", None)]

    admit = None
    discharge = None

    if len(nonempty) >= 2:
        admit = nonempty[-2]
        discharge = nonempty[-1]

    return {
        "set_id": _safe_index(fields, 1),
        "patient_class": _safe_index(fields, 2),
        "location": _safe_index(fields, 3),
        "attending_doctor": _safe_index(fields, 7),
        "hospital_service": _safe_index(fields, 10),
        "visit_number": _safe_index(fields, 18),
        "admit_time": admit,
        "discharge_time": discharge,
    }

def _parse_evn(fields: List[str]) -> Dict[str, Any]:
    """
    Parse EVN (Event Type) segment.
    HL7: EVN|A03|20250101083000|...
    """
    return {
        "event_type": _safe_index(fields, 1),             # EVN-1 e.g., A01, A03
        "recorded_time": _safe_index(fields, 2),          # EVN-2 timestamp
        "event_occurred_time": _safe_index(fields, 6),    # EVN-6
    }


# -------------------------------------------------
# Helpers
# -------------------------------------------------

def _safe_index(lst: List[str], idx: int) -> str | None:
    if idx < len(lst) and lst[idx] not in ("", None):
        return lst[idx]
    return None

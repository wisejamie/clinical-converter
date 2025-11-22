from typing import List
import re

# Allowed: Z-segments
SEGMENT_NAME_RE = re.compile(r"^[A-Z][A-Z0-9]{1,2}$") 


def validate_hl7_lines(lines: List[str]) -> List[str]:
    """
    Validate HL7 v2.x structure.
    Returns a list of error messages (empty if valid).
    """

    errors = []

    # Basic segment presence checks
    segment_order = [line.split("|", 1)[0].strip() for line in lines]
    seg_set = set(segment_order)

    is_adt = False
    for i, line in enumerate(lines):
        if line.startswith("MSH"):
            parts = line.split("|")
            if len(parts) > 8 and parts[8].startswith("ADT"):
                is_adt = True
            break

    # Required: MSH, PID
    if "MSH" not in seg_set:
        errors.append("Missing required segment: MSH")

    if "PID" not in seg_set:
        errors.append("Missing required segment: PID")

    if is_adt:
        if "PV1" not in seg_set:
            errors.append("ADT message missing required segment: PV1")

        if "EVN" not in seg_set:
            errors.append("ADT message missing recommended segment: EVN (timestamps may be incomplete)")

    # If OBX exists, require OBR
    if "OBX" in seg_set and "OBR" not in seg_set:
        errors.append("OBX exists but OBR segment is missing")

    # Order rules
    try:
        if segment_order.index("PID") < segment_order.index("MSH"):
            errors.append("PID appears before MSH (invalid order)")
    except ValueError:
        pass

    if "OBR" in seg_set and "PID" in seg_set:
        if segment_order.index("OBR") < segment_order.index("PID"):
            errors.append("OBR appears before PID (invalid order)")

    if "OBX" in seg_set and "OBR" in seg_set:
        if segment_order.index("OBX") < segment_order.index("OBR"):
            errors.append("OBX appears before OBR (invalid order)")

    # PV1 should come after PID and before OBR/OBX
    if "PV1" in seg_set and "PID" in seg_set:
        if segment_order.index("PV1") < segment_order.index("PID"):
            errors.append("PV1 appears before PID (invalid order)")

    # PV1 must appear before OBR/OBX if present
    if "PV1" in seg_set and "OBR" in seg_set:
        if segment_order.index("PV1") > segment_order.index("OBR"):
            errors.append("PV1 appears after OBR (invalid order)")

    # Line-level validation
    for i, line in enumerate(lines):
        if not line.strip():
            errors.append(f"Line {i+1}: Empty or whitespace-only line")
            continue

        parts = line.split("|")
        seg = parts[0].strip()

        # Validate segment name
        if not SEGMENT_NAME_RE.match(seg) and not seg.startswith("Z"):
            errors.append(f"Line {i+1}: Invalid segment name '{seg}'")

        # Required pipe check
        if "|" not in line:
            errors.append(f"Line {i+1}: Segment '{seg}' contains no field separators '|'")


        # Required field checks
        if seg == "MSH":
            # MSH-9 message type
            if len(parts) < 9 or not parts[8].strip():
                errors.append("MSH-9 (message type) is missing or empty")

        if seg == "PID":
            # PID-3: patient identifier
            if len(parts) < 4 or not parts[3].strip():
                errors.append("PID-3 (patient identifier) is missing or empty")
            # PID-5: patient name
            if len(parts) < 6 or not parts[5].strip():
                errors.append("PID-5 (patient name) is missing or empty")

        if seg == "OBR":
            # OBR-4: universal service ID (test code/name)
            if len(parts) < 5 or not parts[4].strip():
                errors.append("OBR-4 (test code) is missing or empty")

        if seg == "OBX":
            # OBX-3: observation identifier
            if len(parts) < 4 or not parts[3].strip():
                errors.append("OBX-3 (observation code) is missing or empty")
            # OBX-5: value
            if len(parts) < 6 or not parts[5].strip():
                errors.append("OBX-5 (observation value) is missing or empty")

        if seg == "PV1":
            # PV1-2 patient class (should be single char)
            if len(parts) < 3 or not parts[2].strip():
                errors.append("PV1-2 (patient class) is missing or empty")
            elif len(parts[2].strip()) > 1:
                errors.append("PV1-2 (patient class) should be a 1-character code")

            # PV1-19 visit number recommended
            if len(parts) >= 20 and parts[19].strip():
                if not re.match(r"^[A-Za-z0-9\-]+$", parts[19].strip()):
                    errors.append("PV1-19 (visit number) contains invalid characters")

            # PV1-44 / PV1-45 datetime format check
            for idx, label in [(44, "admit"), (45, "discharge")]:
                if len(parts) > idx and parts[idx].strip():
                    ts = parts[idx].strip()
                    if not re.match(r"^\d{12,14}$", ts):
                        errors.append(f"PV1-{idx} ({label} datetime) must be 12–14 digit HL7 timestamp")

        if seg == "EVN":
            # EVN-1 event type (e.g., A01, A03)
            if len(parts) < 2 or not parts[1].strip():
                errors.append("EVN-1 (event type) is missing or empty")

            # EVN-2 timestamp format
            if len(parts) >= 3 and parts[2].strip():
                ts = parts[2].strip()
                if not re.match(r"^\d{12,14}$", ts):
                    errors.append("EVN-2 (recorded time) must be a 12–14 digit HL7 timestamp")

    return errors

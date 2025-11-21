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

    # Required: MSH, PID
    if "MSH" not in seg_set:
        errors.append("Missing required segment: MSH")

    if "PID" not in seg_set:
        errors.append("Missing required segment: PID")

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

    return errors

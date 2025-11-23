"""
Simple-but-realistic HL7 v2.x ADT message generator.

We generate ADT^A01, ADT^A04, ADT^A03 messages with:
- MSH
- EVN
- PID
- NK1 (optional)
- PV1

This is NOT a full HL7 implementation, but it's structurally realistic
enough to stress-test the HL7 parser & converter.
"""

import random
import datetime
from typing import Literal

# Some small but realistic value pools; easy to expand later.
FIRST_NAMES = [
    "John", "Jane", "Michael", "Sarah", "David", "Emily", "Robert", "Olivia",
    "Daniel", "Sophia", "Liam", "Noah", "Emma", "Ava"
]
LAST_NAMES = [
    "Smith", "Johnson", "Brown", "Williams", "Jones", "Garcia", "Miller",
    "Davis", "Martinez", "Wilson", "Anderson"
]
STREETS = [
    "Main St", "Elm St", "Highland Ave", "Maple Rd", "Queen St", "King St",
    "Lakeview Blvd"
]
CITIES = ["Montreal", "Toronto", "Vancouver", "Calgary", "Ottawa"]
PROVINCES = ["QC", "ON", "BC", "AB"]
POSTAL_CODES = ["H3Z2Y7", "M5V2T6", "V5K0A1", "T2P1J9", "K1P5G4"]
PHYSICIANS = [
    "12345^Taylor^Rebecca^J",
    "67890^Lee^Michael^K",
    "24680^Patel^Anita^R",
]

FACILITIES = ["GeneralHospital", "CityHospital", "CommunityClinic"]
APPS = ["ClinicEMR", "InpatientSys", "EDReg"]

LAB_PANELS = [
    {
        "code": "DIABPANEL",
        "text": "Diabetes panel",
        "tests": [
            {
                "code": "2345-7",
                "text": "Glucose",
                "unit": "mmol/L",
                "low": 3.6,
                "high": 7.7,
            },
            {
                "code": "4548-4",
                "text": "Hemoglobin A1c",
                "unit": "%",
                "low": 4.0,
                "high": 5.6,
            },
        ],
    },
    {
        "code": "CBC",
        "text": "Complete blood count",
        "tests": [
            {
                "code": "6690-2",
                "text": "WBC",
                "unit": "10^9/L",
                "low": 4.0,
                "high": 11.0,
            },
            {
                "code": "789-8",
                "text": "Hemoglobin",
                "unit": "g/L",
                "low": 120.0,
                "high": 150.0,
            },
        ],
    },
]


def _random_date(start_year: int = 1940, end_year: int = 2025) -> datetime.date:
    """Random date between start_year and end_year."""
    year = random.randint(start_year, end_year)
    month = random.randint(1, 12)
    # simple safe day selection
    day = random.randint(1, 28)
    return datetime.date(year, month, day)


def _format_hl7_ts(dt: datetime.datetime) -> str:
    """Format datetime as HL7 TS: YYYYMMDDHHMMSS."""
    return dt.strftime("%Y%m%d%H%M%S")


def _random_phone() -> str:
    return f"514{random.randint(1000000, 9999999)}"


def _random_mrn() -> str:
    return str(random.randint(10000000, 99999999))


def _random_visit_number() -> str:
    return str(random.randint(100000, 999999))


def _random_patient() -> dict:
    first = random.choice(FIRST_NAMES)
    last = random.choice(LAST_NAMES)
    dob = _random_date(1940, 2015)
    sex = random.choice(["M", "F"])
    street_num = random.randint(1, 999)
    address = f"{street_num} {random.choice(STREETS)}"
    city = random.choice(CITIES)
    prov = random.choice(PROVINCES)
    postal = random.choice(POSTAL_CODES)
    phone = _random_phone()
    mrn = _random_mrn()

    return {
        "first": first,
        "last": last,
        "dob": dob,
        "sex": sex,
        "address": address,
        "city": city,
        "province": prov,
        "postal": postal,
        "phone": phone,
        "mrn": mrn,
    }


def _build_msh(msg_type: str, trigger: str) -> str:
    """
    Build MSH segment.
    Example: MSH|^~\&|ClinicEMR|GeneralHospital|...
    """
    sending_app = random.choice(APPS)
    sending_fac = random.choice(FACILITIES)
    receiving_app = "DownstreamSys"
    receiving_fac = "DestFacility"
    ts = _format_hl7_ts(datetime.datetime.now())
    msg_control_id = str(random.randint(10000000, 99999999))
    hl7_version = "2.3.1"

    # Field separators and encoding characters: |^~\&
    # MSH-9 = MSGTYPE^TRIGGER
    fields = [
        "MSH",
        "^~\\&",
        sending_app,
        sending_fac,
        receiving_app,
        receiving_fac,
        ts,
        "",
        f"{msg_type}^{trigger}",
        msg_control_id,
        "P",
        hl7_version,
    ]
    return "|".join(fields)


def _build_evn(trigger: str) -> str:
    """
    Build EVN segment with event type and datetime.
    """
    ts = _format_hl7_ts(datetime.datetime.now())
    fields = [
        "EVN",
        trigger,
        ts,
        "",
        "",
        "",
    ]
    return "|".join(fields)


def _build_pid(patient: dict) -> str:
    """
    Build PID segment from patient dict.
    We keep it fairly simple but realistic.
    """
    name_comp = f"{patient['last']}^{patient['first']}^"
    addr_comp = f"{patient['address']}^^{patient['city']}^{patient['province']}^{patient['postal']}"
    dob_str = patient["dob"].strftime("%Y%m%d")
    fields = [
        "PID",
        "1",
        "",
        f"{patient['mrn']}^^^HOSP^MR",
        "",
        name_comp,
        "",
        dob_str,
        patient["sex"],
        "",
        "2106-3",  # race/ethnicity code placeholder
        addr_comp,
        "",
        patient["phone"],
        "",
        "",
        "M",  # marital status placeholder
    ]
    return "|".join(fields)


def _build_nk1(patient: dict) -> str:
    """
    Build NK1 (next-of-kin) segment occasionally.
    We just fake a relative with same last name.
    """
    rel_first = random.choice(FIRST_NAMES)
    rel_name = f"{patient['last']}^{rel_first}"
    phone = _random_phone()
    fields = [
        "NK1",
        "1",
        rel_name,
        "SPO^Spouse",
        "",
        phone,
    ]
    return "|".join(fields)


def _build_pv1(trigger: str) -> str:
    """
    Build PV1 segment.
    We keep visit info generic (outpatient/ambulatory).
    """
    visit_num = _random_visit_number()
    attending = random.choice(PHYSICIANS)
    # PV1-2: Patient class (O = outpatient)
    # PV1-3: Assigned patient location (simplified)
    fields = [
        "PV1",
        "1",
        "O",
        "AMB^^^" + random.choice(FACILITIES),
        "",
        "",
        attending,
        "",
        "",
        "MED",
        "",
        "",
        "",
        "1",
        "A0",
        "",
        "",
        "",
        "",
        "",
        "",
        visit_num,
    ]
    return "|".join(fields)

def _random_value_in_range(low: float, high: float, allow_abnormal: bool = True) -> tuple[float, str]:
    """
    Pick a random value around the reference range.
    Sometimes push slightly outside to generate H/L flags.
    Returns (value, flag) where flag is '', 'H', or 'L'.
    """
    # 70% chance normal, 30% chance abnormal
    if allow_abnormal and random.random() < 0.3:
        # Decide high or low
        if random.random() < 0.5:
            # Slightly low
            value = low - (low - 0) * 0.1 if low > 0 else low - 0.5
            flag = "L"
        else:
            # Slightly high
            span = high - low if high > low else 1.0
            value = high + span * 0.1
            flag = "H"
    else:
        # Normal value in range
        value = random.uniform(low, high)
        flag = ""

    return value, flag


def _build_obr_for_panel(panel: dict) -> str:
    """
    Build a simple OBR segment that represents the entire lab panel.
    We reuse the same physician pool as for PV1.
    """
    ordering_provider = random.choice(PHYSICIANS)
    # OBR-4: universal service identifier → PANELCODE^Panel text
    id_field = f"{panel['code']}^{panel['text']}"
    fields = [
        "OBR",
        "1",           # Set ID
        "",            # Placer order number
        "",            # Filler order number
        id_field,      # Test code/name
        "",            # OBR-5
        "",            # OBR-6
        "",            # OBR-7
        "",            # OBR-8
        "",            # OBR-9
        "",            # OBR-10
        "",            # OBR-11
        "",            # OBR-12
        ordering_provider,  # OBR-13 ordering provider
    ]
    return "|".join(fields)


def _build_obx_for_panel_tests(panel: dict) -> list[str]:
    """
    Given a panel definition, build a list of OBX strings.
    Each test is one OBX segment.
    """
    obx_segments: list[str] = []
    set_id = 1

    for test in panel["tests"]:
        value, flag = _random_value_in_range(test["low"], test["high"])
        range_str = f"{test['low']}-{test['high']}"

        id_field = f"{test['code']}^{test['text']}^LN"
        fields = [
            "OBX",
            str(set_id),
            "NM",                  # Numeric value
            id_field,              # OBX-3: code^text^coding system
            "",                    # OBX-4
            f"{value:.1f}",        # OBX-5: value
            test["unit"],          # OBX-6: units
            range_str,             # OBX-7: reference range
            flag,                  # OBX-8: abnormal flag (H/L or empty)
        ]
        obx_segments.append("|".join(fields))
        set_id += 1

    return obx_segments



def generate_adt(
    trigger: Literal["A01", "A03", "A04"] = "A01",
    include_nk1: bool = True,
    include_labs: bool = True,
) -> str:
    """
    Generate a single HL7 ADT message with the given trigger event.
    Returns an HL7 string with \r between segments.
    """
    patient = _random_patient()
    msg_type = "ADT"

    msh = _build_msh(msg_type, trigger)
    evn = _build_evn(trigger)
    pid = _build_pid(patient)
    segments = [msh, evn, pid]

    if include_nk1 and random.random() < 0.7:
        segments.append(_build_nk1(patient))

    pv1 = _build_pv1(trigger)
    segments.append(pv1)

    if include_labs and LAB_PANELS:
        panel = random.choice(LAB_PANELS)
        obr = _build_obr_for_panel(panel)
        obxs = _build_obx_for_panel_tests(panel)
        segments.append(obr)
        segments.extend(obxs)

    # HL7 segments are delimited by \r (carriage return)
    hl7_message = "\r".join(segments) + "\r"
    return hl7_message


def generate_random_adt(include_labs: bool = True) -> str:
    """
    Pick a random ADT trigger type (A01, A03, A04).
    Optionally include lab panels.
    """
    trigger = random.choice(["A01", "A03", "A04"])
    return generate_adt(trigger=trigger, include_labs=include_labs)

def generate_hl7_message(message_type: str = "adt_random") -> str:
    """
    Unified entry point for HL7 generation used by the API.
    """
    if message_type == "adt_random":
        return generate_random_adt()
    if message_type in ("A01", "A03", "A04"):
        return generate_adt(trigger=message_type)

    raise ValueError(f"Unsupported message_type: {message_type}")

import json
from typing import Any, Dict, List, Tuple, Optional

from backend.openai_client import client


# -------------------------------------------------------
# Helpers: extract resources from Bundle
# -------------------------------------------------------

def _extract_resources(bundle: dict) -> Tuple[Optional[dict], Optional[dict], List[dict]]:
    """
    Given a FHIR Bundle, return (patient, encounter, observations).
    We don't rely on ordering; we scan entry[].resource.
    """
    patient = None
    encounter = None
    observations: List[dict] = []
    related_persons = []
    allergies = []

    for entry in bundle.get("entry", []):
        res = entry.get("resource") or {}
        rtype = res.get("resourceType")
        if rtype == "Patient" and patient is None:
            patient = res
        elif rtype == "Encounter" and encounter is None:
            encounter = res
        elif rtype == "Observation":
            observations.append(res)
        elif rtype == "RelatedPerson":
            related_persons.append(res)
        elif rtype == "AllergyIntolerance":
            allergies.append(res)

    return patient, encounter, observations, related_persons, allergies


def _format_patient(patient: dict) -> str:
    if not patient:
        return "Patient: (not available)"

    # Identifier (MRN-like)
    mrn = None
    for ident in patient.get("identifier", []):
        if ident.get("system") == "http://hospital.example.org/mrn":
            mrn = ident.get("value")
            break
    if mrn is None and patient.get("identifier"):
        mrn = patient["identifier"][0].get("value")

    name_part = ""
    names = patient.get("name") or []
    if names:
        n0 = names[0]
        family = n0.get("family")
        given = (n0.get("given") or [None])[0]
        if family or given:
            name_part = f"{given or ''} {family or ''}".strip()

    gender = patient.get("gender")
    dob = patient.get("birthDate")

    pieces = []
    if name_part:
        pieces.append(name_part)
    if gender:
        pieces.append(f"gender: {gender}")
    if dob:
        pieces.append(f"DOB: {dob}")
    if mrn:
        pieces.append(f"identifier: {mrn}")

    if not pieces:
        return "Patient: (no demographic fields found)"

    return "Patient: " + ", ".join(pieces)


def _format_encounter(encounter: Optional[dict]) -> str:
    if not encounter:
        return "Encounter: (not available)"

    status = encounter.get("status")
    enc_class = (encounter.get("class") or {}).get("code")
    start = (encounter.get("period") or {}).get("start")
    end = (encounter.get("period") or {}).get("end")

    enc_type_code = None
    if encounter.get("type"):
        coding = (encounter["type"][0].get("coding") or [])
        if coding:
            enc_type_code = coding[0].get("code")

    location_display = None
    if encounter.get("location"):
        location_display = (
            encounter["location"][0]
            .get("location", {})
            .get("display")
        )

    attending = None
    if encounter.get("participant"):
        attending = (
            encounter["participant"][0]
            .get("individual", {})
            .get("display")
        )

    pieces = []
    if enc_type_code:
        pieces.append(f"type: {enc_type_code}")
    if status:
        pieces.append(f"status: {status}")
    if enc_class:
        pieces.append(f"class: {enc_class}")
    if start:
        pieces.append(f"start: {start}")
    if end:
        pieces.append(f"end: {end}")
    if location_display:
        pieces.append(f"location: {location_display}")
    if attending:
        pieces.append(f"attending: {attending}")

    if not pieces:
        return "Encounter: (no encounter details found)"

    return "Encounter: " + ", ".join(pieces)


def _format_observation(obs: dict) -> str:
    # Code display / text
    display = None
    if obs.get("code"):
        coding = (obs["code"].get("coding") or [])
        if coding:
            display = coding[0].get("display") or coding[0].get("code")
    if not display:
        display = "Unnamed observation"

    # Value
    value_str = "no value"
    if "valueQuantity" in obs:
        vq = obs["valueQuantity"]
        v = vq.get("value")
        unit = vq.get("unit") or ""
        if v is not None:
            value_str = f"{v} {unit}".strip()
    elif "valueString" in obs:
        vs = obs.get("valueString")
        if vs:
            value_str = vs

    # Interpretation flag (e.g., H/L)
    flag = None
    interp = obs.get("interpretation")
    if interp:
        coding = (interp[0].get("coding") or [])
        if coding:
            flag = coding[0].get("code")

    if flag:
        return f"- {display}: {value_str} (flag: {flag})"
    else:
        return f"- {display}: {value_str}"


# -------------------------------------------------------
# Deterministic summary (no LLM)
# -------------------------------------------------------

def summarize_fhir_bundle(bundle: dict, debug: bool = False) -> str:
    """
    Deterministic summary:
    - Extracts facts from Patient, Encounter, and Observations
    - No model calls, zero interpretation
    """

    if debug:
        print("\n[DEBUG] summarize_fhir_bundle() called with FHIR bundle:")
        print(json.dumps(bundle, indent=2))

    patient, encounter, observations, related, allergies = _extract_resources(bundle)

    patient_line = _format_patient(patient)
    encounter_line = _format_encounter(encounter)

    obs_lines = []
    for obs in observations:
        obs_lines.append(_format_observation(obs))

    lines = [
        patient_line,
        encounter_line,
        "",
        "Observations:",
    ]

    if obs_lines:
        lines.extend(obs_lines)
    else:
        lines.append("- (no observations found)")

    related_lines = []
    for rp in related:
        name = None
        if "name" in rp and rp["name"]:
            part = rp["name"][0]
            if "family" in part or "given" in part:
                family = part.get("family", "")
                given = " ".join(part.get("given", []))
                name = f"{given} {family}".strip()
            else:
                name = part.get("text")
        rel = None
        if "relationship" in rp and rp["relationship"]:
            rc = rp["relationship"][0].get("coding", [])
            if rc:
                rel = rc[0].get("code")
        phone = None
        if "telecom" in rp and rp["telecom"]:
            phone = rp["telecom"][0].get("value")

        related_lines.append(
            f"- {name or 'Unknown'}"
            f"{f' ({rel})' if rel else ''}"
            f"{f', phone: {phone}' if phone else ''}"
        )

    if related_lines:
        lines.append("")
        lines.append("Related Persons:")
        lines.extend(related_lines)

    allergy_lines = []
    for allergy in allergies:
        substance = None
        if "code" in allergy:
            coding = (allergy["code"].get("coding") or [])
            if coding:
                substance = coding[0].get("display") or coding[0].get("code")
        clinical_status = None
        if "clinicalStatus" in allergy:
            cs_coding = (allergy["clinicalStatus"].get("coding") or [])
            if cs_coding:
                clinical_status = cs_coding[0].get("code")
        allergy_lines.append(
            f"- {substance or 'Unknown substance'}"
            f"{f' (status: {clinical_status})' if clinical_status else ''}"
        )
    if allergy_lines:
        lines.append("")
        lines.append("Allergies:")
        lines.extend(allergy_lines)

    # Make it explicit that this contains no clinical interpretation
    lines.append("")
    lines.append(
        "Note: This summary contains only structured facts from the FHIR Bundle and "
        "intentionally avoids any clinical interpretation or recommendations."
    )

    deterministic = "\n".join(lines)

    if debug:
        print("\n[DEBUG] Deterministic summary:")
        print(deterministic)

    return deterministic


# -------------------------------------------------------
# LLM-generated human summary (neutral prose)
# -------------------------------------------------------

def summarize_fhir_human(bundle: dict, debug: bool = False) -> str:
    """
    Uses GPT-4.1-nano to turn the deterministic facts into a short,
    neutral, human-readable clinical-style summary.
    """

    # First, get the deterministic facts
    facts = summarize_fhir_bundle(bundle, debug=debug)

    if debug:
        print("\n[DEBUG] Using deterministic facts as input to LLM:")
        print(facts)

    prompt = f"""
        You are a neutral clinical documentation assistant.

        Task:
        Rewrite the structured clinical facts below into a short, clear, neutral
        summary suitable for a clinician reviewing this encounter.

        Requirements:
        - Do NOT invent any new facts that are not present in the data.
        - Do NOT add clinical judgment, diagnoses, or treatment recommendations.
        - Do NOT speculate about severity, risk, prognosis, or causality.
        - Do NOT address the patient directly (no "you"); write in third person.
        - Focus on the encounter context and key observations.
        - Keep the summary concise and factual.

        Here are the structured facts extracted deterministically:

        {facts}

        If needed only for field names and context, you may also refer to the raw
        FHIR Bundle below. Do not add any new facts beyond what is explicitly present.

        FHIR Bundle:
        {json.dumps(bundle, indent=2)}

        Now write the neutral summary.
        """

    response = client.chat.completions.create(
        model="gpt-4.1-nano",
        messages=[{"role": "user", "content": prompt}],
    )

    return response.choices[0].message.content
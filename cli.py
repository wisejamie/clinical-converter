#!/usr/bin/env python3

import argparse
import json
from pathlib import Path

from backend.parse_hl7 import parse_hl7_file
from backend.to_fhir import convert_parsed_hl7_to_fhir


def main():
    parser = argparse.ArgumentParser(
        description="HL7 → FHIR Convertor"
    )

    parser.add_argument(
        "input_file",
        type=str,
        help="Path to the HL7 file",
    )

    parser.add_argument(
        "--out",
        "-o",
        type=str,
        default=None,
        help="Optional output path for FHIR JSON bundle",
    )

    parser.add_argument(
        "--debug",
        action="store_true",
        help="Print detailed debugging information",
    )

    args = parser.parse_args()

    input_path = Path(args.input_file)

    if not input_path.exists():
        print(f"ERROR: File not found: {input_path}")
        return

    # === Parse HL7 ===
    if args.debug:
        print("\n=== STEP 1: Parsing HL7 ===\n")

    parsed = parse_hl7_file(str(input_path), debug=args.debug)

    # === Convert to FHIR ===
    if args.debug:
        print("\n=== STEP 2: Converting to FHIR ===\n")

    fhir_bundle = convert_parsed_hl7_to_fhir(parsed, debug=args.debug)

    # === Output ===
    if args.out:
        output_path = Path(args.out)
        output_path.write_text(json.dumps(fhir_bundle, indent=2))
        print(f"\nSaved FHIR JSON to: {output_path}\n")
    else:
        print(json.dumps(fhir_bundle, indent=2))


if __name__ == "__main__":
    main()
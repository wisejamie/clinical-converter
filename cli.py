#!/usr/bin/env python3

import argparse
import json
import sys
from pathlib import Path

# Import backend converters
from backend.parse_hl7 import parse_hl7_file
from backend.to_fhir import convert_parsed_hl7_to_fhir


def load_hl7_file(path: Path):
    if not path.exists():
        raise FileNotFoundError(f"Input file does not exist: {path}")

    text = path.read_text()
    return text


def run_cli():
    parser = argparse.ArgumentParser(
        description="HL7 → FHIR conversion tool"
    )

    parser.add_argument(
        "-i", "--input",
        type=str,
        required=True,
        help="Path to HL7 file"
    )

    parser.add_argument(
        "-o", "--output",
        type=str,
        help="Optional output file for FHIR JSON"
    )

    parser.add_argument(
        "--pretty",
        action="store_true",
        help="Pretty-print JSON output"
    )

    parser.add_argument(
        "--raw",
        action="store_true",
        help="Output parsed HL7 JSON instead of FHIR"
    )

    parser.add_argument(
        "--debug",
        action="store_true",
        help="Enable debug logging"
    )

    parser.add_argument(
        "--version",
        action="store_true",
        help="Show version and exit"
    )

    args = parser.parse_args()

    # Handle version flag
    if args.version:
        print("hl7-to-fhir version 0.1.0")
        sys.exit(0)

    input_path = Path(args.input)

    # === STEP 1 — Load HL7 File ===
    try:
        hl7_text = load_hl7_file(input_path)
    except Exception as e:
        print(f"[ERROR] Cannot load input file: {e}", file=sys.stderr)
        sys.exit(1)

    if args.debug:
        print("====== DEBUG: Loading HL7 File ======")
        print(hl7_text)
        print("=====================================")

    # === STEP 2 — Parse HL7 ===
    try:
        parsed = parse_hl7_file(str(input_path), debug=args.debug)
    except Exception as e:
        print(f"[ERROR] Failed to parse HL7: {e}", file=sys.stderr)
        sys.exit(2)

    if args.raw:
        output_json = parsed
    else:
        # === STEP 3 — Convert to FHIR ===
        try:
            fhir_bundle = convert_parsed_hl7_to_fhir(parsed, debug=args.debug)
            output_json = fhir_bundle
        except Exception as e:
            print(f"[ERROR] Failed to convert to FHIR: {e}", file=sys.stderr)
            sys.exit(3)

    # === STEP 4 — Format output ===
    if args.pretty:
        json_str = json.dumps(output_json, indent=2)
    else:
        json_str = json.dumps(output_json)

    # === STEP 5 — Print or save ===
    if args.output:
        try:
            Path(args.output).write_text(json_str)
            if args.debug:
                print(f"[DEBUG] Output written to {args.output}")
        except Exception as e:
            print(f"[ERROR] Failed to write output: {e}", file=sys.stderr)
            sys.exit(4)
    else:
        print(json_str)


if __name__ == "__main__":
    run_cli()

#!/usr/bin/env python3

import argparse
import json
import sys
from pathlib import Path
from colorama import init, Fore, Style

# Initialize colorama for cross-platform colour output
init(autoreset=True)

# backend imports
from backend.parse_hl7 import parse_hl7_file
from backend.to_fhir import convert_parsed_hl7_to_fhir
from backend.validate_hl7 import validate_hl7_lines


def load_hl7_file(path: Path):
    if not path.exists():
        raise FileNotFoundError(f"Input file does not exist: {path}")
    return path.read_text()


def colour_error(msg):
    return f"{Fore.RED}❌ {msg}{Style.RESET_ALL}"


def colour_ok(msg):
    return f"{Fore.GREEN}✔ {msg}{Style.RESET_ALL}"


def run_cli():
    parser = argparse.ArgumentParser(description="HL7 → FHIR conversion tool")

    parser.add_argument(
        "-i", "--input",
        type=str,
        required=True,
        help="Path to HL7 file"
    )

    parser.add_argument(
        "-o", "--output",
        type=str,
        help="Optional output file"
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
        "--validate",
        action="store_true",
        help="Validate HL7 before converting"
    )

    parser.add_argument(
        "--validate-only",
        action="store_true",
        help="Validate HL7 and exit without converting"
    )

    parser.add_argument(
        "--version",
        action="store_true",
        help="Show version"
    )

    parser.add_argument(
        "--summary",
        action="store_true",
        help="Generate a clinical summary using the FHIR output."
    )

    args = parser.parse_args()

    if args.version:
        print("hl7-to-fhir version 0.2.0")
        sys.exit(0)

    input_path = Path(args.input)

    # === LOAD HL7 ===
    try:
        hl7_raw = load_hl7_file(input_path)
    except Exception as e:
        print(colour_error(f"Error loading HL7 file: {e}"), file=sys.stderr)
        sys.exit(1)

    # Normalize lines for validation
    normalized = hl7_raw.replace("\r\n", "\n").replace("\r", "\n").strip().split("\n")

    # === VALIDATION ===
    if args.validate or args.validate_only:
        errors = validate_hl7_lines(normalized)

        if errors:
            print(colour_error("HL7 Validation Failed:\n"))
            for err in errors:
                print(colour_error(f"  - {err}"))
            print()
            print(colour_error(f"Validation failed with {len(errors)} error(s)."))
            sys.exit(5)
        else:
            print(colour_ok("HL7 validation passed."))

        if args.validate_only:
            sys.exit(0)

    # === PARSE HL7 → Python dict ===
    try:
        parsed = parse_hl7_file(str(input_path), debug=args.debug)
    except Exception as e:
        print(colour_error(f"Failed to parse HL7: {e}"), file=sys.stderr)
        sys.exit(2)

    # === RAW MODE ===
    if args.raw:
        bundle = parsed
    else:
        # === FHIR CONVERSION ===
        try:
            bundle = convert_parsed_hl7_to_fhir(parsed, debug=args.debug)
        except Exception as e:
            print(colour_error(f"Failed to convert to FHIR: {e}"), file=sys.stderr)
            sys.exit(3)

    # === JSON OUTPUT ===
    json_str = json.dumps(bundle, indent=2 if args.pretty else None)

    if args.output:
        try:
            Path(args.output).write_text(json_str)
            print(colour_ok(f"Wrote output to {args.output}"))
        except Exception as e:
            print(colour_error(f"Failed to write output: {e}"), file=sys.stderr)
            sys.exit(4)
    else:
        print(json_str)

    # After bundle is printed/generated:
    if args.summary:
        from backend.summarize import summarize_fhir_bundle
        print("\n===== CLINICAL SUMMARY =====\n")
        summary = summarize_fhir_bundle(bundle, debug=args.debug)
        print(summary)


if __name__ == "__main__":
    run_cli()

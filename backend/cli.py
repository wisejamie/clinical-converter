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

    # NOTE: input file is NOT always required (HL7 generator mode)
    parser.add_argument(
        "-i", "--input",
        type=str,
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
        "--summary-deterministic",
        action="store_true",
        help="Generate a deterministic clinical summary."
    )

    parser.add_argument(
        "--summary-llm",
        action="store_true",
        help="Generate a neutral human-readable summary using GPT."
    )

    # HL7 GENERATION MODE
    parser.add_argument(
        "--generate-hl7",
        choices=["adt_a01", "adt_a03", "adt_a04", "adt_random"],
        help="Generate synthetic HL7 ADT messages."
    )

    parser.add_argument(
        "-n", "--count",
        type=int,
        default=1,
        help="Number of HL7 messages to generate (default: 1)"
    )

    parser.add_argument(
        "-O", "--out-hl7",
        help="Directory to write generated HL7 messages (only for --generate-hl7)"
    )

    args = parser.parse_args()

    if args.version:
        print("hl7-to-fhir version 0.2.0")
        sys.exit(0)

    # ==========================================================
    # HL7 GENERATION MODE (NO INPUT REQUIRED)
    # ==========================================================
    if args.generate_hl7:
        from backend.hl7_generate import generate_adt, generate_random_adt

        if args.generate_hl7 == "adt_random":
            generator = generate_random_adt
            label = "RANDOM"
        else:
            mapping = {
                "adt_a01": "A01",
                "adt_a03": "A03",
                "adt_a04": "A04",
            }
            trigger = mapping[args.generate_hl7]
            generator = lambda: generate_adt(trigger=trigger)
            label = trigger

        messages = [generator() for _ in range(args.count)]

        if args.out_hl7:
            out_dir = Path(args.out_hl7)
            out_dir.mkdir(parents=True, exist_ok=True)
            for idx, msg in enumerate(messages, 1):
                fname = out_dir / f"{args.generate_hl7}_{idx:03d}.hl7"
                fname.write_text(msg)
            print(colour_ok(
                f"Generated {args.count} {label} message(s) → {args.out_hl7}"
            ))
        else:
            for idx, msg in enumerate(messages, 1):
                if args.count > 1:
                    print(f"\n----- MESSAGE {idx} -----\n")
                print(msg, end="")

        return  # IMPORTANT: skip conversion mode entirely

    # ==========================================================
    # CONVERSION MODE REQUIRES INPUT FILE
    # ==========================================================
    if not args.input:
        print(colour_error("You must provide -i/--input unless using --generate-hl7"))
        sys.exit(1)

    input_path = Path(args.input)

    # === LOAD HL7 ===
    try:
        hl7_raw = load_hl7_file(input_path)
    except Exception as e:
        print(colour_error(f"Error loading HL7 file: {e}"), file=sys.stderr)
        sys.exit(1)

    # Normalize for validation
    normalized = hl7_raw.replace("\r\n", "\n").replace("\r", "\n").strip().split("\n")

    # === VALIDATION ===
    if args.validate or args.validate_only:
        errors = validate_hl7_lines(normalized)

        if errors:
            print(colour_error("HL7 Validation Failed:\n"))
            for err in errors:
                print(colour_error(f"  - {err}"))
            sys.exit(5)
        else:
            print(colour_ok("HL7 validation passed."))

        if args.validate_only:
            sys.exit(0)

    # === PARSE HL7 ===
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
            print(colour_error(f"Failed to write output: {e}"))
            sys.exit(4)
    else:
        print(json_str)

    # === SUMMARIES ===
    if args.summary_deterministic:
        from backend.summarize import summarize_fhir_bundle
        print("\n===== CLINICAL SUMMARY =====\n")
        print(summarize_fhir_bundle(bundle, debug=args.debug))

    if args.summary_llm:
        from backend.summarize import summarize_fhir_human
        print("\n===== LLM SUMMARY =====\n")
        print(summarize_fhir_human(bundle, debug=args.debug))


if __name__ == "__main__":
    run_cli()

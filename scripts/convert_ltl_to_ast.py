#!/usr/bin/env python3
"""
convert_ltl_csv.py

For each row in the CSV, writes to the real inp_file:
    print_python
    <ltl_formula>

Then runs: dune exec ./bin/main.exe < inp_file
Captures stdout and stores it as a new column "AST" in the output CSV.

Usage:
    python3 convert_ltl_csv.py input.csv                  # output: input_ast.csv
    python3 convert_ltl_csv.py input.csv output.csv
    python3 convert_ltl_csv.py input.csv --project-dir /path/to/ltlutils
    export LTL_PROJECT_DIR=/path/to/ltlutils
"""

import csv
import subprocess
import sys
import os
import argparse


# Default: run from inside the ltlutils directory, or set via env var
DEFAULT_PROJECT_DIR = os.environ.get("LTL_PROJECT_DIR", ".")


def run_formula(formula: str, project_dir: str) -> tuple[str, str]:
    """
    1. Writes to <project_dir>/inp_file:
           print_python
           <formula>
    2. Runs: dune exec ./bin/main.exe < inp_file
    3. Returns (stdout, stderr)
    """
    inp_file = os.path.join(project_dir, "inp_file")

    # Write the inp_file exactly as the tool expects
    with open(inp_file, "w", encoding="utf-8") as f:
        f.write("print_python\n")
        f.write(formula.strip() + "\n")

    try:
        with open(inp_file, "r", encoding="utf-8") as stdin_f:
            result = subprocess.run(
                ["dune", "exec", "./bin/main.exe"],
                stdin=stdin_f,
                capture_output=True,
                text=True,
                cwd=project_dir,
                timeout=30,
            )
        return result.stdout.strip(), result.stderr.strip()

    except subprocess.TimeoutExpired:
        return "", "ERROR: timeout after 30s"
    except FileNotFoundError:
        return "", "ERROR: 'dune' not found — is it on your PATH?"


def process_csv(input_path: str, output_path: str, project_dir: str):
    rows_in = []
    with open(input_path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        fieldnames = list(reader.fieldnames or [])
        for row in reader:
            rows_in.append(row)

    if not rows_in:
        print("No rows found in input CSV.")
        return

    # Validate expected columns
    required = {"Natural Language", "Atomic Proposition", "Ground Truth"}
    missing = required - set(fieldnames)
    if missing:
        print(f"ERROR: CSV is missing columns: {missing}")
        sys.exit(1)

    out_fieldnames = fieldnames + ["AST", "stderr"]
    total = len(rows_in)

    print(f"Processing {total} rows from : {input_path}")
    print(f"Project dir                  : {os.path.abspath(project_dir)}")
    print(f"inp_file                     : {os.path.join(os.path.abspath(project_dir), 'inp_file')}")
    print()

    with open(output_path, "w", newline="", encoding="utf-8") as out_f:
        writer = csv.DictWriter(out_f, fieldnames=out_fieldnames)
        writer.writeheader()

        for i, row in enumerate(rows_in, 1):
            formula = row["Ground Truth"].strip()
            short = formula[:60] + ("..." if len(formula) > 60 else "")
            print(f"[{i}/{total}] {short}")

            ast, err = run_formula(formula, project_dir)

            if err and not ast:
                print(f"         ERROR  : {err}")
            elif err:
                print(f"         STDERR : {err}")
            print(f"         AST    : {ast[:80]}{'...' if len(ast) > 80 else ''}\n")

            out_row = dict(row)
            out_row["AST"] = ast
            out_row["stderr"] = err
            writer.writerow(out_row)

    print(f"Done. Output written to: {output_path}")


def main():
    parser = argparse.ArgumentParser(
        description="Run print_python via dune exec for each LTL formula in a CSV."
    )
    parser.add_argument("input_csv", help="Path to input CSV file")
    parser.add_argument(
        "output_csv",
        nargs="?",
        help="Path to output CSV (default: <input>_ast.csv)",
    )
    parser.add_argument(
        "--project-dir",
        default=DEFAULT_PROJECT_DIR,
        help="Path to ltlutils dune project directory (default: . or $LTL_PROJECT_DIR)",
    )
    args = parser.parse_args()

    if not os.path.isfile(args.input_csv):
        print(f"ERROR: Input file not found: {args.input_csv}")
        sys.exit(1)

    if args.output_csv:
        output_path = args.output_csv
    else:
        base, ext = os.path.splitext(args.input_csv)
        output_path = f"{base}_ast{ext or '.csv'}"

    project_dir = args.project_dir
    if not os.path.isdir(project_dir):
        print(f"ERROR: Project directory not found: {project_dir}")
        print("Set via --project-dir or $LTL_PROJECT_DIR")
        sys.exit(1)

    process_csv(args.input_csv, output_path, project_dir)


if __name__ == "__main__":
    main()
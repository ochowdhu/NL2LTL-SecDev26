#!/usr/bin/env python3
import csv
import subprocess
from pathlib import Path
import sys
import tempfile
import os
import shutil
from scripts.ltl_extractor import convert_python_ast_to_ltl


# Get paths relative to current script
script_dir = Path(__file__).parent
project_root = script_dir.parent
print(f"Project root directory: {project_root}")
experiment_name = sys.argv[1] if len(sys.argv) > 1 else "nl2futureltl"

experiment_dir = project_root / "output" / experiment_name

INPUT_CSV = experiment_dir / "nl2ltl_summary_results.csv"
OUTPUT_CSV = experiment_dir / "semantic_equiv_entail_results.csv"

PROJECT_ROOT = Path(__file__).resolve().parents[1]
LTL_DIR = PROJECT_ROOT / "LTL"

assert LTL_DIR.exists(), f"LTL directory not found at: {LTL_DIR}"
print("Using LTL directory:", LTL_DIR)

NUSMV_PATH = "/usr/local/bin/nusmv"

import re

def get_model_columns(header):
    """Return model prediction column names from a CSV header.

    Excludes the standard 'Ground Truth' and 'Natural Language' columns.
    """
    if not header:
        return []
    # header may be a list of fieldnames or a CSV header row; filter out known non-model columns
    return [h for h in header if h not in ("Ground Truth", "Natural Language")]

def sanitize_formula(formula: str) -> str:
    if not formula:
        return ""

    f = str(formula).strip().strip('"').strip("'")

    # fix spacing around operators
    f = re.sub(r"<\s*-\s*>", "<->", f)
    f = re.sub(r"-\s*>", "->", f)
    f = re.sub(r"\s+", " ", f)
    f = f.replace(",", "")

    # ── ADD: ensure spaces around binary operators ─────────────
    # U operator: (xUy) → (x U y)
    f = re.sub(r'([a-zA-Z0-9\)])\s*U\s*([a-zA-Z0-9\(])', r'\1 U \2', f)
    # -> operator
    f = re.sub(r'\s*->\s*', ' -> ', f)
    # <-> operator  
    f = re.sub(r'\s*<->\s*', ' <-> ', f)
    # & operator
    f = re.sub(r'\s*&\s*', ' & ', f)
    # | operator
    f = re.sub(r'\s*\|\s*', ' | ', f)
    # S operator: (xSy) → (x S y)
    f = re.sub(r'([a-zA-Z0-9\)])\s*S\s*([a-zA-Z0-9\(])', r'\1 S \2', f)

    # collapse multiple spaces
    f = re.sub(r'\s+', ' ', f).strip()

    # reject non-LTL artifacts
    INVALID = ["LOr","LAnd","LEquiv","LImplies","LNot","AtomicProposition"]
    if any(tok in f for tok in INVALID):
        print("INVALID NON-LTL:", f)
        return ""

    return f

def run_ocaml(formula1: str, formula2: str = "", cmd_type: str = "equiv") -> str:
    formula1 = sanitize_formula(formula1)
    formula2 = sanitize_formula(formula2)

    if not formula1:
        return "NOT_MEANINGFUL"
    if cmd_type in ("equiv", "check_entailment") and not formula2:
        return "NOT_MEANINGFUL"

    input_str = f"{cmd_type}\n{formula1}"
    if formula2:
        input_str += f"\n{formula2}"
    input_str += "\n"

    env = os.environ.copy()
    env["NUSMVBINPATH"] = "/usr/local/bin"

    try:
        result = subprocess.run(
            ["dune", "exec", "./bin/main.exe"],
            input=input_str.encode(),
            capture_output=True,
            cwd=LTL_DIR / "corrected_version" / "ltlutils",
            env=env
        )

        stdout = result.stdout.decode().strip()
        stderr = result.stderr.decode().strip()

        # ── debug: show when stdout is empty ──────────────────
        if not stdout:
            print(f"  EMPTY STDOUT [{cmd_type}]")
            print(f"  INPUT : {repr(input_str)}")
            print(f"  STDERR: {stderr[:200]}")
            # check if stderr contains the actual result
            # OCaml sometimes prints to stderr instead of stdout
            if "NOT_MEANINGFUL" in stderr:
                return "NOT_MEANINGFUL"
            if "EQUIVALENT" in stderr:
                return "EQUIVALENT"
            if "NOT_EQUIVALENT" in stderr:
                return "NOT_EQUIVALENT"
            if "Yes" in stderr:
                return "Yes"
            if "No" in stderr:
                return "No"
            return "NOT_MEANINGFUL"  # blank = variables don't overlap

        return stdout

    except Exception as e:
        print(f"OCaml failure: {e}")
        return "ERROR"
    
def setup_environment():
    """Configure the environment and compile the project."""
    compile_script = LTL_DIR / "corrected_version" / "ltlutils" / "compile-project"

    if not compile_script.exists():
        print(f"Warning: Compile script not found at {compile_script}")
        return

    try:
        with open(compile_script, 'r+') as f:
            content = f.read()
            f.seek(0)
            f.write(content.replace("NUSMV_HOME=/path/to/NuSMV", f"NUSMV_HOME={NUSMV_PATH}"))
            f.truncate()
        compile_script.chmod(0o755)

        subprocess.run(["./compile-project"],
                       cwd=LTL_DIR / "corrected_version" / "ltlutils",
                       check=True)
    except Exception as e:
        print(f"Error setting up environment: {e}")
        print("Continuing without compilation...")

def process_csv(input_csv, output_csv):
    input_csv = Path(input_csv)
    output_csv = Path(output_csv)

    if not input_csv.exists():
        print(f"Error: Input CSV not found at {input_csv}")
        return

    with open(input_csv, newline='', encoding='utf-8') as f_in:
        reader = csv.DictReader(f_in)
        header = reader.fieldnames
        model_cols = get_model_columns(header)

        print(f"Ground truth column : Ground Truth")
        print(f"Model columns found : {model_cols}")

        # Only GT vs each model — not model vs model
        out_header = list(header)
        for col in model_cols:
            out_header.append(f"Eq_Ground Truth_vs_{col}")
        for col in model_cols:
            out_header.append(f"En_Ground Truth_to_{col}")
            out_header.append(f"En_{col}_to_Ground Truth")
        for col in model_cols:
            out_header.append(f"Syntax_{col}")

        with open(output_csv, 'w', newline='', encoding='utf-8') as f_out:
            writer = csv.DictWriter(f_out, fieldnames=out_header)
            writer.writeheader()

            for row_num, row in enumerate(reader, 1):
                print(f"Processing row {row_num}: {row.get('Natural Language', '')[:60]}")
                gt = sanitize_formula(row.get("Ground Truth", ""))
                out_row = dict(row)

                for col in model_cols:
                    pred = sanitize_formula(row.get(col, ""))
                    print(f"  [{col}] GT: {gt[:40]} | PRED: {pred[:40]}")

                    out_row[f"Eq_Ground Truth_vs_{col}"] = run_ocaml(gt, pred, "equiv")
                    out_row[f"En_Ground Truth_to_{col}"] = run_ocaml(gt, pred, "check_entailment")
                    out_row[f"En_{col}_to_Ground Truth"] = run_ocaml(pred, gt, "check_entailment")
                    out_row[f"Syntax_{col}"] = run_ocaml(pred, "", "print_formula")
                    # syntax check — only care about OK/ERROR, not the formula text
                    raw_syntax = run_ocaml(pred, "", "print_formula")
                    if raw_syntax.startswith("OK"):
                        out_row[f"Syntax_{col}"] = "OK"
                    elif raw_syntax == "NOT_MEANINGFUL":
                        out_row[f"Syntax_{col}"] = "NOT_MEANINGFUL"
                    else:
                        out_row[f"Syntax_{col}"] = "ERROR"
                    
                writer.writerow(out_row)

    print(f"Results saved to {output_csv}")



def main():
    print("Setting up environment...")
    setup_environment()

    print(f"Processing {INPUT_CSV}...")
    process_csv(INPUT_CSV, OUTPUT_CSV)

    print(f"Results saved to {OUTPUT_CSV}")


if __name__ == "__main__":
    main()
import csv
from pathlib import Path
import subprocess

from pathlib import Path
import pandas as pd
import subprocess
import logging
import csv

def check_trace(input_csv: Path, output_csv: Path, ltl_utils_dir: Path) -> None:
    """Check trace satisfaction for all generated traces."""
    print(f"Starting trace check...")
    print(f"Input CSV: {input_csv}")
    print(f"LTL Utils Dir: {ltl_utils_dir}")

    # Compile project
    try:
        compile_script = ltl_utils_dir / "compile-project"
        print(f"Compiling project using: {compile_script}")
        subprocess.run(str(compile_script), check=True, cwd=ltl_utils_dir)
        print("Project compiled successfully")
    except subprocess.CalledProcessError as e:
        print(f"Compilation failed: {e}")
        return

    # Read and process input CSV
    results = []
    input_data = []
    
    print("Reading input CSV...")
    with open(input_csv, 'r') as csvfile:
        csv_reader = csv.DictReader(csvfile)
        for row in csv_reader:
            formula = row['LTL Formula']
            positive_trace = format_trace(row['Positive Trace'])
            negative_trace = format_trace(row['Negative Trace'])
            
            print(f"\nProcessing formula: {formula}")
            positive_result = run_trace_check(formula, positive_trace, ltl_utils_dir)
            negative_result = run_trace_check(formula, negative_trace, ltl_utils_dir)
            
            # Store results with model and approach information
            results.append({
                "Model": row['Model'],
                "Approach": row['Approach'],
                "LTL Formula": formula,
                "Positive Trace": positive_trace,
                "Positive Result": positive_result,
                "Negative Trace": negative_trace,
                "Negative Result": negative_result
            })
            print(f"Results - Positive: {positive_result}, Negative: {negative_result}")

    # Write results
    print(f"\nWriting results to {output_csv}")
    with open(output_csv, 'w', newline='') as csvfile:
        fieldnames = [
            "Model",
            "Approach",
            "LTL Formula",
            "Positive Trace",
            "Positive Result",
            "Negative Trace",
            "Negative Result"
        ]
        csv_writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        csv_writer.writeheader()
        csv_writer.writerows(results)
    
    print("Trace checking completed!")

# def format_trace(trace: str) -> str:
#     """Format trace for the checker."""
#     trace = trace.strip()
#     if not trace:
#         return ""
#     # Remove "..." if present at the end
#     if trace.endswith("..."):
#         trace = trace[:-3]
#     return trace

def format_trace(trace):
    """Format trace string properly."""
    trace = trace.replace('"', '')
    if trace.endswith("...") and not trace.endswith(";..."):
        trace = trace[:-3] + ";..."
    return trace

def run_trace_check(formula: str, trace: str, ltl_utils_dir: Path) -> str:
    """Run single trace check."""
    if not trace:
        return "ERROR: Empty trace"
    
    # Create temporary files in the output directory
    temp_input = ltl_utils_dir / "temp_input.txt"
    temp_output = ltl_utils_dir / "temp_output.txt"
    temp_error = ltl_utils_dir / "temp_error.txt"

    try:
        # Write input
        with open(temp_input, "w") as f:
            f.write("check_trace_satisfaction\n")
            f.write(f"{formula}\n")
            f.write(f"{trace}\n")

        # Run the command
        command = f"dune exec ./bin/main.exe < {temp_input} 1> {temp_output} 2> {temp_error}"
        subprocess.run(
            command, 
            shell=True, 
            check=True,
            cwd=ltl_utils_dir,
            stderr=subprocess.PIPE,
            text=True
        )
        
        # Read result
        with open(temp_output, 'r') as f:
            result = f.read().strip()
            return result if result in ["FALSIFIED", "SATISFIED"] else "ERROR"
            
    except subprocess.CalledProcessError as e:
        print(f"Execution failed for formula: {formula}")
        print(f"Error message: {e.stderr}")
        return f"ERROR: {e.stderr}"
        
    finally:
        # Cleanup
        for file in [temp_input, temp_output, temp_error]:
            if file.exists():
                file.unlink()

def main():
    # Define paths
    base_dir = Path(__file__).resolve().parents[1]  # Adjust level if needed

    ltl_utils_dir = base_dir / "LTL" / "corrected_version" / "ltlutils"

    input_csv = base_dir / "llm_LTL" / "output" / "trace_generation" / "trace_generation_detailed.csv"
    output_csv = base_dir / "llm_LTL" / "output" / "trace_generation" / "trace_generation_satisfaction_results.csv"
    
    # Run trace checker
    check_trace(input_csv, output_csv, ltl_utils_dir)

if __name__ == "__main__":
    main()
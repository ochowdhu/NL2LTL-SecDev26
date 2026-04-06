import pandas as pd
import sys
import os
import logging
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from collections import defaultdict
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
import csv
from pathlib import Path
import argparse
import importlib
import csv
import os
import pandas as pd
from pathlib import Path
from collections import defaultdict
from parse_prompt import send_request, MODEL_SETS, LEARNING_APPROACHES
from scripts.semantic_checker import process_csv
from scripts.entail_equiv_analyzer import run_full_analysis


def get_generate_prompt_function(experiment_type):
    """Dynamically load the prompt generator function"""
    module_path = f"prompts.{experiment_type}.ltl_future_prompt_template"
    module = importlib.import_module(module_path)
    return module.generate_prompt

def get_extractor_function(experiment_type):
    """Dynamically load the appropriate extractor function based on experiment type"""
    try:
        from scripts.ltl_extractor import get_appropriate_extractor
        return get_appropriate_extractor(experiment_type)
    except ImportError:
        print(f"Warning: Could not import ltl_extractor, using default")
        return extract_ltl_formula_default
    
def extract_ltl_formula_default(response_text):
    """
    Default LTL formula extractor for minimal and detailed experiments.
    """
    if not response_text or response_text.strip() == "Error":
        return "No LTL formula extracted"
    
    # Remove common prefixes and clean the response
    response = response_text.strip()
    if response.startswith("LTL Formula:"):
        response = response.replace("LTL Formula:", "").strip()
    
    return response

def parse_args():
    """Parse command line arguments with comprehensive options"""
    parser = argparse.ArgumentParser(
        description="Run WFF characterization experiment with configurable parameters.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter
    )
    
    # Required arguments
    parser.add_argument("--dataset", type=str, required=True,
                        help="Path to the dataset CSV file.")
    parser.add_argument("--experiment_type", required=True, 
                        choices=["minimal", "detailed", "python", "python_no_ap"],
                        help="Experiment type: minimal, detailed, or python")
    
    # Optional model and approach selection
    parser.add_argument("--models", nargs="+", 
                        help="Specific models to run (optional). If not specified, uses default models for experiment type.")
    parser.add_argument("--approaches", nargs="+", 
                        help="Specific approaches to run (optional). If not specified, uses default approaches for experiment type.")
    
    # Output configuration
    parser.add_argument("--output_dir", type=str, default="",
                        help="Base output directory for results")
    parser.add_argument("--experiment_name", type=str,
                        help="Custom experiment name (defaults to experiment_type)")
    
    # Processing options
    parser.add_argument("--sample_size", type=int,
                        help="Number of samples to process (optional, processes all if not specified)")
    parser.add_argument("--skip_generation", action="store_true",
                        help="Skip raw response generation and only process existing responses")
    parser.add_argument("--force_regenerate", action="store_true",
                        help="Force regeneration of raw responses even if file exists")
    
    return parser.parse_args()

def write_detailed_results(filename, results):
    if not results:
        print(f"No results to write to {filename}")
        return
    with open(filename, 'w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=results[0].keys())
        writer.writeheader()
        writer.writerows(results)
        
def format_nl2ltl_results_for_csv(results, output_file):
    # Create a dictionary to store the data
    data = defaultdict(lambda: defaultdict(str))
    
    # Column headers
    headers = ['Natural Language', 'Ground Truth']
    model_approaches = set()

    # Process the results
    for result in results:
        nl = result['Natural Language']
        gt = result['Ground Truth']
        model_approach = f"{result['Model']}_{result['Approach']}"
        extract_ltl = result['LLM Response']

        data[nl]['Ground Truth'] = gt
        data[nl][model_approach] = extract_ltl
        model_approaches.add(model_approach)

    # Sort the model_approaches and add them to headers
    headers.extend(sorted(model_approaches))

    # Write to CSV
    with open(output_file, 'w', newline='', encoding='utf-8') as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=headers)
        writer.writeheader()

        for nl, row_data in data.items():
            row = {'Natural Language': nl}
            row.update(row_data)
            writer.writerow(row)

def save_raw_responses_to_csv(filename, data):
    """Save raw responses to a CSV file."""
    df = pd.DataFrame(data)
    file_exists = os.path.exists(filename)
    df.to_csv(filename, index=False, mode='a', header=not file_exists)

def read_saved_responses_from_csv(filename):
    """Read previously saved raw responses from a CSV file."""
    if os.path.exists(filename):
        return pd.read_csv(filename)
    else:
        print(f"{filename} does not exist. Run the initial response generation first.")
        return pd.DataFrame()

def generate_raw_responses(nl2ltl_dataset, models, learning_approaches,
                           raw_responses_file, generate_prompt_func,
                           force_regenerate=False, experiment_type="python"):
    """Generate and save raw responses from different models and approaches."""
    if os.path.exists(raw_responses_file) and not force_regenerate:
        print(f"{raw_responses_file} already exists. Skipping generation.")
        return
    
    # If force_regenerate is True, remove existing file
    if force_regenerate and os.path.exists(raw_responses_file):
        os.remove(raw_responses_file)
        print(f"Removed existing {raw_responses_file} for regeneration.")
    
    raw_responses = []
    total_combinations = len(models) * len(learning_approaches) * len(nl2ltl_dataset)
    current_count = 0
    
    for model in models:
        for approach in learning_approaches:
            print(f"Generating responses for {model} with {approach} approach...")
            for _, row in nl2ltl_dataset.iterrows():
                current_count += 1
                print(f"Processing {current_count}/{total_combinations}")
                
                response = process_single_response(model, approach, row, generate_prompt_func, experiment_type)
                raw_responses.append(response)
                
                # Save periodically to avoid losing data
                if len(raw_responses) % 50 == 0:
                    save_raw_responses_to_csv(raw_responses_file, raw_responses[-50:])
    
    # Save any remaining responses
    if raw_responses:
        save_raw_responses_to_csv(raw_responses_file, raw_responses)
    print(f"Raw responses saved to {raw_responses_file}")

def process_single_response(model, approach, row, generate_prompt_func, experiment_type):
    natural_language    = row['Natural Language']
    ground_truth        = row['Ground Truth']
    atomic_propositions = row['Atomic Proposition']

    try:
        initial_prompt   = generate_prompt_func(natural_language, atomic_propositions, approach)
        initial_response = send_request(initial_prompt, model)
    except Exception as e:
        print(f"ERROR calling API for '{natural_language[:50]}': {e}")
        import traceback
        traceback.print_exc()  
        initial_response = "Error"



    # ── Extract AP from response for no-AP experiments ──────────
    extracted_ap = ""
    if experiment_type in ("python_no_ap",):
        from scripts.ltl_extractor import extract_ap_from_response
        extracted_ap = extract_ap_from_response(initial_response)

    if approach != "zero_shot_self_refine":
        return {
            'Model':               model,
            'Approach':            approach,
            'Natural Language':    natural_language,
            'Atomic Proposition':  atomic_propositions,
            'Ground Truth':        ground_truth,
            'Extracted AP':        extracted_ap,
            'Initial Response':    initial_response,
            'Refined Response':    None,
        }

    try:
        refined_prompt   = generate_prompt_func(
            natural_language, atomic_propositions, approach, initial_response)
        refined_response = send_request(refined_prompt, model)
        if experiment_type in ("python_no_ap",):
            from scripts.ltl_extractor import extract_ap_from_response
            extracted_ap = extract_ap_from_response(refined_response)
    except Exception as e:
        print(f"Error during refinement for {natural_language}: {e}")
        refined_response = "Error"

    # extract AP block if present in response
    from scripts.ltl_extractor import extract_ap_from_response
    extracted_ap = extract_ap_from_response(
        refined_response if approach == "zero_shot_self_refine" 
        and refined_response != "Error" 
        else initial_response
    )

    return {
        'Model':              model,
        'Approach':           approach,
        'Natural Language':   natural_language,
        'Atomic Proposition': atomic_propositions,   # GT
        'Extracted AP':       extracted_ap,           # ← LLM's own APs
        'Ground Truth':       ground_truth,
        'Initial Response':   initial_response,
        'Refined Response':   refined_response if approach == "zero_shot_self_refine" else None,
    }

def process_responses(raw_responses_df, detailed_results_file, summary_results_file, extractor_func, experiment_type):
    """Process raw responses and generate detailed and summary results."""
    if raw_responses_df.empty:
        return
    
    nl2ltl_detailed_results = []
    nl2ltl_summary_results = {}
    
    for _, row in raw_responses_df.iterrows():
        detailed_result, summary_result = process_single_result(row, extractor_func, experiment_type)
        nl2ltl_detailed_results.append(detailed_result)
        
        key = f"{row['Model']}_{row['Approach']}"
        if key not in nl2ltl_summary_results:
            nl2ltl_summary_results[key] = []
        nl2ltl_summary_results[key].append(summary_result)
    
    write_detailed_results(detailed_results_file, nl2ltl_detailed_results)
    format_nl2ltl_results_for_csv(nl2ltl_detailed_results, summary_results_file)
    print(f"Detailed results saved to {detailed_results_file}")
    print(f"Summary results saved to {summary_results_file}")

def process_single_result(row, extractor_func, experiment_type):
    """Process a single result row and return detailed and summary results."""
    # Handle the response based on approach
    if row['Approach'] == "zero_shot_self_refine" and pd.notna(row['Refined Response']):
        generated_response = f"Initial: {row['Initial Response']}\nRefined: {row['Refined Response']}"
        extract_ltl = extractor_func(row['Refined Response'])
    else:
        generated_response = row['Initial Response']
        extract_ltl = extractor_func(row['Initial Response'])
    
    if not extract_ltl:
        extract_ltl = "No LTL formula extracted"
    
    # For python experiment, convert AST ground truth to standard LTL
    ground_truth = row['Ground Truth']
    if experiment_type in ("python", "python_no_ap") and 'AST' in row:
        # Use the AST column as the original ground truth and convert it
        ast_ground_truth = row['AST']
        if pd.notna(ast_ground_truth):
            from scripts.ltl_extractor import convert_ast_ground_truth_to_ltl
            ground_truth = convert_ast_ground_truth_to_ltl(ast_ground_truth)
    
    detailed_result = {
        'Model': row['Model'],
        'Approach': row['Approach'],
        'Natural Language': row['Natural Language'],
        'Atomic Proposition': row['Atomic Proposition'],
        "Ground Truth": ground_truth,
        'Generated Response': generated_response,
        "LLM Response": extract_ltl
    }
    
    # For python experiment, include both AST and converted LTL
    if experiment_type in ("python", "python_no_ap") and 'AST' in row:
        detailed_result['AST Ground Truth'] = row['AST']
    
    summary_result = {
        'Natural Language': row['Natural Language'],
        'Atomic Proposition': row['Atomic Proposition'],
        "Ground Truth": ground_truth,
        'Extracted LTL': extract_ltl
    }
    
    return detailed_result, summary_result


def main():
    """Main function to coordinate the LTL processing pipeline."""
    args = parse_args()
    
    pd.options.display.float_format = "{:,.2f}".format

    # Load dataset
    nl2ltl_dataset = pd.read_csv(args.dataset)
    
    # Apply sampling if specified
    if args.sample_size:
        nl2ltl_dataset = nl2ltl_dataset.sample(n=min(args.sample_size, len(nl2ltl_dataset)))
        print(f"Using sample of {len(nl2ltl_dataset)} rows")

    # Setup models and approaches
    models = args.models if args.models else list(MODEL_SETS.keys())
    learning_approaches = args.approaches if args.approaches else LEARNING_APPROACHES
    print(f"Using models: {models}")
    print(f"Using approaches: {learning_approaches}")

    # Set experiment output directory
    experiment_name = args.experiment_name or args.experiment_type
    output_dir = Path("data") / "output_data" / args.experiment_type / "nl2ltl"
    output_dir.mkdir(parents=True, exist_ok=True)

    # File paths
    file_paths = {
        "raw_responses_file": output_dir / "nl2ltl_raw_responses.csv",
        "detailed_results_file": output_dir / "nl2ltl_detailed_results.csv",
        "summary_results_file": output_dir / "nl2ltl_summary_results.csv",
        "model_checking_file": output_dir / "semantic_equiv_entail_results.csv",
        "analysis_output_dir": output_dir

    }

    # Load appropriate functions based on experiment type
    generate_prompt_func = get_generate_prompt_function(args.experiment_type)
    extractor_func = get_extractor_function(args.experiment_type)
    
    print(f"Loaded prompt generator for {args.experiment_type} experiment")
    print(f"Loaded extractor for {args.experiment_type} experiment")

    # Phase 1: Generate raw responses (unless skipped)
    if not args.skip_generation:
        print("Phase 1: Generating raw responses...")
        generate_raw_responses(
            nl2ltl_dataset, 
            models, 
            learning_approaches, 
            file_paths["raw_responses_file"],
            generate_prompt_func,
            force_regenerate=args.force_regenerate,
            experiment_type=args.experiment_type 
        )
    else:
        print("Skipping raw response generation as requested")

    # Phase 2: Process responses
    print("Phase 2: Processing responses...")
    raw_responses = read_saved_responses_from_csv(file_paths["raw_responses_file"])
    
    if not raw_responses.empty:
        process_responses(
            raw_responses, 
            file_paths["detailed_results_file"], 
            file_paths["summary_results_file"],
            extractor_func,
            args.experiment_type
        )
        print("Processing complete!")
    else:
        print("No raw responses found to process.")
    process_csv(file_paths["summary_results_file"], file_paths["model_checking_file"])
    run_full_analysis(file_paths["model_checking_file"], file_paths["analysis_output_dir"])

if __name__ == "__main__":
    main()
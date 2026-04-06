from concurrent.futures import ThreadPoolExecutor
import pandas as pd
import time
import os
from concurrent.futures import ThreadPoolExecutor
from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score
import re
from Levenshtein import distance as levenshtein_distance
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import importlib
from pathlib import Path
from parse_prompt import send_request
import argparse
from parse_prompt import MODEL_SETS, LEARNING_APPROACHES

def get_generate_prompt_function(experiment_type):
    """Dynamically load the prompt generator function"""
    module_path = f"prompts.{experiment_type}.nl2pl_prompt_template"
    module = importlib.import_module(module_path)
    return module.generate_prompt

def parse_args():
    """Parse command line arguments with comprehensive options"""
    parser = argparse.ArgumentParser(
        description="Run Natural Language to Atomic Proposition Extraction experiment with configurable parameters.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter
    )
    
    # Required arguments
    parser.add_argument("--dataset", type=str, required=True,
                        help="Path to the dataset CSV file.")
    parser.add_argument("--experiment_type", required=True, 
                        choices=["minimal", "detailed", "python"],
                        help="Experiment type: minimal, detailed, or python")
    
    # Optional model and approach selection
    parser.add_argument("--models", nargs="+", 
                        help="Specific models to run (optional). If not specified, uses default models for experiment type.")
    parser.add_argument("--approaches", nargs="+", 
                        help="Specific approaches to run (optional). If not specified, uses default approaches for experiment type.")
    
    # Output configuration
    parser.add_argument("--base_output_dir", type=str,
                        default="data/output_data",
                        help="Base directory for output files. The full path will include experiment_type.")
    parser.add_argument("--raw_responses_file", type=str, default=None,
                        help="Custom filename for raw responses (without extension)")
    parser.add_argument("--detailed_results_file", type=str, default=None,
                        help="Custom filename for detailed results (without extension)")
    parser.add_argument("--aggregated_results_file", type=str, default=None,
                        help="Custom filename for aggregated results (without extension)")
    
    # Processing configuration
    parser.add_argument("--max_workers", type=int, default=4,
                        help="Maximum number of worker threads for parallel processing")
    parser.add_argument("--max_retries", type=int, default=5,
                        help="Maximum number of retries for API calls")
    parser.add_argument("--initial_delay", type=float, default=5.0,
                        help="Initial delay in seconds for retry backoff")
    parser.add_argument("--shuffle_dataset", action="store_true",
                        help="Randomize the order of dataset processing")
    
    # Execution control
    parser.add_argument("--skip_generation", action="store_true",
                        help="Skip response generation and only run evaluation on existing results")
    parser.add_argument("--c", type=str, default=None,
                        help="Path to existing raw responses file (for evaluation only)")
    parser.add_argument("--dry_run", action="store_true",
                        help="Print configuration and exit without running experiment")
    
    # Evaluation configuration
    parser.add_argument("--evaluation_only", action="store_true",
                        help="Run only evaluation on existing raw responses")
    parser.add_argument("--save_intermediate", action="store_true",
                        help="Save intermediate results during processing")
    
    parser.add_argument("--verbose", "-v", action="store_true",
                        help="Enable verbose output")
    parser.add_argument("--quiet", "-q", action="store_true",
                        help="Suppress non-essential output")
    
    return parser.parse_args()

def setup_output_paths(args):
    """Setup output file paths based on arguments"""
    full_output_dir = Path(args.base_output_dir) / args.experiment_type / "nl2pl"

    # 2. Create the output directory if it doesn't exist
    full_output_dir.mkdir(parents=True, exist_ok=True)

    # 3. Create default filenames if custom ones are not provided
    file_base_name = f"nl2pl_{args.experiment_type}"

    paths = {
        # Use full_output_dir (a Path object) and the / operator for clean joining
        'raw_responses': full_output_dir / f"{args.raw_responses_file or file_base_name}_raw_responses.csv",
        'detailed_results': full_output_dir / f"{args.detailed_results_file or file_base_name}_detailed_evaluation_results.csv",
        'aggregated_results': full_output_dir / f"{args.aggregated_results_file or file_base_name}_aggregated_results.csv"
    }
    return paths

def send_request_with_retries(prompt, model, max_retries=5, initial_delay=5, verbose=False):
    """Wrapper to retry API calls with exponential backoff."""
    retries = 0
    delay = initial_delay
    
    while retries < max_retries:
        try:
            return send_request(prompt, model)
        except Exception as e:
            retries += 1
            if verbose or retries == max_retries:
                print(f"Error encountered: {e}. Retry {retries}/{max_retries} in {delay} seconds...")
            if retries < max_retries:
                time.sleep(delay)
                delay *= 2  # Exponential backoff
    
    raise Exception(f"Failed after {max_retries} retries for model {model}.")

def generate_response(nl_statement, approach, model, max_retries, initial_delay, verbose, generate_prompt):
    """Generate response with configurable retry parameters"""
    prompt = generate_prompt(nl_statement, approach)
    return send_request_with_retries(prompt, model, max_retries, initial_delay, verbose)

def parse_ground_truth(ground_truth_str):
    """Parse ground truth string into dictionary"""
    ground_truth = {}
    
    # Pattern to match "key": value or key: value
    pattern = r'(?:"([^"]+)"|([^:]+))\s*:\s*(\w+)'
    
    matches = re.findall(pattern, ground_truth_str)
    
    for match in matches:
        key = match[0] if match[0] else match[1] 
        value = match[2]
        ground_truth[key.strip()] = value.strip()
    
    return ground_truth

def save_raw_responses(nl_statement, model, approach, response, formula, output_file, verbose=False):
    """Save raw API responses to CSV before evaluation."""
    row = {
        'Natural Language': nl_statement,
        'Model': model,
        'Approach': approach,
        'Ground Truth': approach,
        'Formula': formula,
        'Raw Response': response,
    }
    
    df = pd.DataFrame([row])
    df.to_csv(output_file, mode='a', header=not os.path.exists(output_file), 
              float_format="%.2f", index=False)
    
    if verbose:
        print(f"Saved response for {model}-{approach}: {nl_statement[:50]}...")

def load_raw_responses(input_file, verbose=False):
    """Load previously saved raw responses."""
    if os.path.exists(input_file):
        df = pd.read_csv(input_file)
        if verbose:
            print(f"Loaded {len(df)} raw responses from {input_file}")
        return df
    
    if verbose:
        print(f"No existing raw responses found at {input_file}")
    return pd.DataFrame()

def extract_gt_mappings(text):
    """Extract mappings from text and return them as a dictionary."""
    mappings = {}
    
    if not text or not isinstance(text, str):
        return mappings
        
    text = text.replace('\n', ';')
    
    pairs = text.split(";")
    
    for pair in pairs:
        pair = pair.strip()
        if ":" in pair:
            key, value = pair.split(":", 1)
            key = key.strip().strip('"').lower() 
            value = value.strip().lower()
            if key and value: 
                mappings[key] = value
            
    return mappings

def extract_predicted_mappings(text):
    """Extract variable-description mappings from predicted response, robustly."""
    mappings = {}
    
    if not text or not isinstance(text, str):
        return mappings

    # Attempt to extract section labeled 'Predicted Atomic Propositions', otherwise use whole text
    match = re.search(r'Predicted Atomic Propositions:\s*(.*)', text, re.IGNORECASE | re.DOTALL)
    ap_text = match.group(1).strip() if match else text.strip()

    # Split by newlines, semicolons, or <br>
    parts = re.split(r'<br>|[\n;]', ap_text)

    for part in parts:
        part = part.strip()

        # Skip empty lines or lines like `!H`, `!France_2006_World_Cup`
        if not part or part.startswith("!") or ":" not in part:
            continue

        try:
            # Allow: H : Mary owns a house
            # Or: H: "Mary owns a house"
            var_desc = part.split(":", 1)
            var = var_desc[0].strip()
            desc = var_desc[1].strip().strip('"').strip().lower()

            if var and desc:
                mappings[desc] = var
        except Exception:
            continue

    return mappings

def calculate_jaccard_similarity(str1, str2):
    """Calculate Jaccard similarity between two strings."""
    set1 = set(str1.lower().split())
    set2 = set(str2.lower().split())
    
    intersection = len(set1.intersection(set2))
    union = len(set1.union(set2))
    
    return intersection / union if union > 0 else 0

def evaluate(raw_responses, verbose=False):
    """
    Evaluate raw responses against the ground truth with additional similarity metrics.
    """
    detailed_results = []
    total_rows = len(raw_responses)

    for idx, (_, row) in enumerate(raw_responses.iterrows()):
        if verbose and idx % 10 == 0:
            print(f"Evaluating row {idx + 1}/{total_rows}")
            
        try:
            nl_statement = str(row['Natural Language'])
            ground_truth_str = str(row['Ground Truth'])
            formula_str = str(row['Formula'])
            raw_response_str = str(row['Raw Response'])

            gt_mappings = extract_gt_mappings(ground_truth_str)
            pred_mappings = extract_predicted_mappings(raw_response_str)

            gt_phrases = set(gt_mappings.keys())
            pred_phrases = set(pred_mappings.keys())
            all_phrases = list(gt_phrases.union(pred_phrases))
            
            gt_labels_phrases = [1 if phrase in gt_phrases else 0 for phrase in all_phrases]
            pred_labels_phrases = [1 if phrase in pred_phrases else 0 for phrase in all_phrases]

            phrase_similarities = []
            levenshtein_distances = []
            
            for gt_phrase in gt_phrases:
                phrase_max_jaccard = 0
                phrase_min_levenshtein = float('inf')
                
                for pred_phrase in pred_phrases:
                    jaccard = calculate_jaccard_similarity(gt_phrase, pred_phrase)
                    phrase_max_jaccard = max(phrase_max_jaccard, jaccard)
                    
                    lev_dist = levenshtein_distance(gt_phrase.lower(), pred_phrase.lower())
                    phrase_min_levenshtein = min(phrase_min_levenshtein, lev_dist)
                
                if pred_phrases: 
                    phrase_similarities.append(phrase_max_jaccard)
                    levenshtein_distances.append(phrase_min_levenshtein)

            avg_jaccard = sum(phrase_similarities) / len(phrase_similarities) if phrase_similarities else 0
            avg_levenshtein = sum(levenshtein_distances) / len(levenshtein_distances) if levenshtein_distances else 0

            gt_props = set(gt_mappings.values())
            pred_props = set(pred_mappings.values())
            all_props = list(gt_props.union(pred_props))
            
            gt_labels_props = [1 if prop in gt_props else 0 for prop in all_props]
            pred_labels_props = [1 if prop in pred_props else 0 for prop in all_props]

            phrase_metrics = {
                'accuracy': accuracy_score(gt_labels_phrases, pred_labels_phrases) if all_phrases else 0,
                'precision': precision_score(gt_labels_phrases, pred_labels_phrases, zero_division=0) if all_phrases else 0,
                'recall': recall_score(gt_labels_phrases, pred_labels_phrases, zero_division=0) if all_phrases else 0,
                'f1': f1_score(gt_labels_phrases, pred_labels_phrases, zero_division=0) if all_phrases else 0
            }

            result = {
                'Natural Language': nl_statement,
                'Ground Truth': ground_truth_str,
                'Raw Response': formula_str,
                'Raw Response': raw_response_str,
                "Extracted Predicted Mapping": pred_mappings,
                "Ground Truth Phrase": gt_phrases,
                "Predicted Phrase": pred_phrases,
                "All Phrases": all_phrases,
                "Ground Truth Label": gt_labels_phrases,
                "Predicted Label": pred_labels_phrases,
                'Accuracy': phrase_metrics['accuracy']*100,
                'Precision': phrase_metrics['precision']*100,
                'Recall': phrase_metrics['recall']*100,
                'F1': phrase_metrics['f1']*100,
                'Jaccard': avg_jaccard,
                'Levenshtein': avg_levenshtein,
            }
            detailed_results.append(result)
            
        except Exception as e:
            if verbose:
                print(f"Error processing row {idx}: {str(e)}")
            continue

    return pd.DataFrame(detailed_results)

def aggregate_evaluation(data, verbose=False):
    """Aggregate evaluation metrics grouped by Model and Approach."""
    # First evaluate all responses
    evaluated_data = evaluate(data, verbose)
    
    # Then group and aggregate
    metrics_to_agg = [
        'Accuracy', 'Precision', 'Recall', 'F1',
        'Jaccard', 'Levenshtein',
    ]
    
    # Group by Model and Approach
    aggregated = data.groupby(['Model', 'Approach']).agg({
        'Natural Language': 'count'
    }).reset_index()
    
    aggregated = aggregated.rename(columns={'Natural Language': 'Total_Samples'})
    
    for metric in metrics_to_agg:
        avg_name = f'{metric.replace(" ", "_")}'
        aggregated[avg_name] = evaluated_data.groupby([data['Model'], data['Approach']])[metric].mean().values
    
    if verbose:
        print(f"Aggregated results for {len(aggregated)} model-approach combinations")
    
    return aggregated

def save_results(file_path, results, verbose=False):
    """Save results to CSV with configurable verbosity"""
    df = pd.DataFrame(results)
    df.to_csv(file_path, index=False, float_format="%.3f", encoding='utf-8')
    
    if verbose:
        print(f"Saved {len(df)} results to {file_path}")

def generate_and_save_raw_results(input_file, output_file, models, learning_approaches, 
                                args, generate_prompt):
    """Generate and save raw results with configurable parameters"""
    dataset = pd.read_csv(input_file)
    
    if args.shuffle_dataset:
        dataset = dataset.sample(frac=1).reset_index(drop=True)
        if args.verbose:
            print("Dataset shuffled")
    
    def process_row(row):
        results = []
        
        for model in models:
            for approach in learning_approaches:
                try:
                    if args.verbose:
                        print(f"Running {model} with {approach} approach...")
                    
                    nl_statement = row['Natural Language']
                    ground_truth = row['Ground Truth']
                    formula = row['Formula']
                    raw_response = generate_response(
                        nl_statement, approach, model, 
                        args.max_retries, args.initial_delay, 
                        args.verbose, generate_prompt
                    )
             
                    result = {
                        'Model': model,
                        'Approach': approach,
                        'Natural Language': nl_statement,
                        'Ground Truth': ground_truth,
                        'Formula':formula,
                        'Raw Response': raw_response,
                    }
                    results.append(result)
                    
                    if args.save_intermediate:
                        save_raw_responses(nl_statement, model, approach,  formula,raw_response,
                                         output_file, args.verbose)
                        
                except Exception as e:
                    if not args.quiet:
                        print(f"Skipping formula {nl_statement[:50]}... due to error: {e}")
        return results

    if args.verbose:
        print(f"Processing {len(dataset)} rows with {args.max_workers} workers")

    with ThreadPoolExecutor(max_workers=args.max_workers) as executor:
        all_results = list(executor.map(process_row, [row for _, row in dataset.iterrows()]))

    raw_results = [item for sublist in all_results for item in sublist]
    
    if not args.save_intermediate:  # Only save once if not saving intermediate results
        save_results(output_file, raw_results, args.verbose)
    
    if not args.quiet:
        print(f"Generated {len(raw_results)} raw responses")
    
    return raw_results

def print_configuration(args, models, learning_approaches, paths):
    """Print current configuration"""
    print("=== Experiment Configuration ===")
    print(f"Experiment Type: {args.experiment_type}")
    print(f"Dataset: {args.dataset}")
    print(f"Models: {models}")
    print(f"Approaches: {learning_approaches}")
    print(f"Output Directory: {args.output_dir}")
    print(f"Max Workers: {args.max_workers}")
    print(f"Max Retries: {args.max_retries}")
    print(f"Initial Delay: {args.initial_delay}s")
    print(f"Shuffle Dataset: {args.shuffle_dataset}")
    print(f"Skip Generation: {args.skip_generation}")
    print(f"Evaluation Only: {args.evaluation_only}")
    print("=== Output Files ===")
    for key, path in paths.items():
        print(f"{key.replace('_', ' ').title()}: {path}")
    print("===============================")


def main():
    args = parse_args()
    
    # Setup paths
    paths = setup_output_paths(args)
    models = args.models if args.models else list(MODEL_SETS.keys())
    learning_approaches = args.approaches if args.approaches else LEARNING_APPROACHES
    print(f"Models: {models}")
    print(f"Approaches: {learning_approaches}")

    # Print configuration
    if args.verbose or args.dry_run:
        print_configuration(args, models, learning_approaches, paths)
    
    if args.dry_run:
        print("Dry run completed. Exiting without running experiment.")
        return
    
    # Dynamically load the prompt generator
    generate_prompt = get_generate_prompt_function(args.experiment_type)
    
    # Handle different execution modes
    if args.evaluation_only or args.skip_generation:
        # Load existing raw responses
        input_file = args.raw_responses_file or paths['raw_responses']
        raw_responses = load_raw_responses(input_file, args.verbose)
        
        if raw_responses.empty:
            print(f"No raw responses found at {input_file}. Cannot perform evaluation.")
            return
    else:
        # Generate new responses
        if not args.quiet:
            print("Generating raw responses...")
        
        generate_and_save_raw_results(
            args.dataset, paths['raw_responses'], models, learning_approaches, 
            args, generate_prompt
        )
        raw_responses = load_raw_responses(paths['raw_responses'], args.verbose)

    # Perform evaluation
    if not args.quiet:
        print("Evaluating responses...")
    
    detailed_results = evaluate(raw_responses, args.verbose)
    
    if not args.quiet:
        print("Detailed Evaluation Results generated")

    # Save detailed results
    detailed_results_df = pd.DataFrame(detailed_results)
    detailed_results_df.to_csv(paths['detailed_results'], float_format="%.2f", index=False)
    
    if not args.quiet:
        print(f"Detailed evaluation results saved to '{paths['detailed_results']}'")

    # Generate and save aggregated results
    aggregated_results = aggregate_evaluation(raw_responses, args.verbose)
    
    if args.verbose:
        print("\nAggregated Evaluation Results:")
        print(aggregated_results.to_string(index=False))

    aggregated_results.to_csv(paths['aggregated_results'], float_format="%.2f", index=False)
    
    if not args.quiet:
        print(f"Aggregated results saved to '{paths['aggregated_results']}'")
        print("Experiment completed successfully!")

if __name__ == "__main__":
    main()
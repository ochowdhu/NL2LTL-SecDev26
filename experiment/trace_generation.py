import csv
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from parse_prompt import send_request
from scripts.save_results import write_detailed_results
from scripts.trace_satisfaction import check_trace
import matplotlib.pyplot as plt
import seaborn as sns
sns.set_theme()
import csv
from pathlib import Path
from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score, confusion_matrix
import pandas as pd
import re
from typing import Tuple
from parse_prompt import send_request, MODEL_SETS, LEARNING_APPROACHES

from scripts.trace_satisfaction import check_trace
import argparse
import importlib

def get_generate_prompt_function(experiment_type):
    """Dynamically load the prompt generator function"""
    module_path = f"prompts.{experiment_type}.trace_generation_prompt"
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

def parse_args():
    """Parse command line arguments with comprehensive options"""
    parser = argparse.ArgumentParser(
        description="Run trace generation experiment with configurable parameters.",
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
    return parser.parse_args()

def get_formula_from_row(row, experiment_type):
    """Extract the appropriate formula based on experiment type"""
    if experiment_type == "python":
        return row["AST"]  # Use AST column for python experiments
    else:
        return row["Ground Truth"]  # Use Ground Truth column for minimal/detailed

def get_ltl_formula_from_row(row, experiment_type):
    """Get the standard LTL formula (not AST) for output"""
    return row["Ground Truth"]  # Always use Ground Truth for LTL Formula column in output

def extract_satisfying_falsifying_traces(response: str) -> Tuple[str, str]:
    satisfying_trace = ""
    falsifying_trace = ""
    
    # Handle both formats: SATISFYING/FALSIFYING and Positive/Negative Trace
    
    # First try SATISFYING/FALSIFYING format
    satisfying_match = re.search(r'SATISFYING:\s*(.+?)(?=\s*FALSIFYING:|$)', response, re.DOTALL)
    if satisfying_match:
        satisfying_trace = satisfying_match.group(1).strip()
    else:
        # Fallback to Positive Trace format
        positive_match = re.search(r'Positive [Tt]race:\s*(.+?)(?=\s*Negative [Tt]race:|$)', response, re.DOTALL)
        if positive_match:
            satisfying_trace = positive_match.group(1).strip()
    
    # Try FALSIFYING format
    falsifying_match = re.search(r'FALSIFYING:\s*(.+?)(?=\s*SATISFYING:|$)', response, re.DOTALL)
    if falsifying_match:
        falsifying_trace = falsifying_match.group(1).strip()
    else:
        # Fallback to Negative Trace format
        negative_match = re.search(r'Negative [Tt]race:\s*(.+?)(?=\s*Positive [Tt]race:|$)', response, re.DOTALL)
        if negative_match:
            falsifying_trace = negative_match.group(1).strip()
    
    # Clean up the traces by removing trailing semicolons and extra whitespace
    satisfying_trace = re.sub(r';\s*$', '', satisfying_trace)
    falsifying_trace = re.sub(r';\s*$', '', falsifying_trace)
    
    return satisfying_trace, falsifying_trace

def extract_positive_negative_trace(response: str) -> Tuple[str, str]:
    """Alias for extract_satisfying_falsifying_traces for backwards compatibility"""
    return extract_satisfying_falsifying_traces(response)

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

def extract_traces_flexible(response: str) -> Tuple[str, str]:
    """
    More flexible trace extraction that handles various formats
    """
    satisfying_trace = ""
    falsifying_trace = ""
    
    # List of possible positive trace indicators
    positive_patterns = [
        r'SATISFYING:\s*(.+?)(?=\s*(?:FALSIFYING|Negative|$))',
        r'Positive [Tt]race:\s*(.+?)(?=\s*(?:Negative|FALSIFYING|$))',
        r'Satisfying [Tt]race:\s*(.+?)(?=\s*(?:Negative|Falsifying|FALSIFYING|$))',
    ]
    
    # List of possible negative trace indicators  
    negative_patterns = [
        r'FALSIFYING:\s*(.+?)(?=\s*(?:SATISFYING|Positive|$))',
        r'Negative [Tt]race:\s*(.+?)(?=\s*(?:Positive|SATISFYING|$))',
        r'Falsifying [Tt]race:\s*(.+?)(?=\s*(?:Positive|Satisfying|SATISFYING|$))',
    ]
    
    # Try each positive pattern
    for pattern in positive_patterns:
        match = re.search(pattern, response, re.DOTALL | re.IGNORECASE)
        if match:
            satisfying_trace = match.group(1).strip()
            break
    
    # Try each negative pattern
    for pattern in negative_patterns:
        match = re.search(pattern, response, re.DOTALL | re.IGNORECASE)
        if match:
            falsifying_trace = match.group(1).strip()
            break
    
    # Clean up traces
    satisfying_trace = re.sub(r'[;\s]*$', '', satisfying_trace)
    falsifying_trace = re.sub(r'[;\s]*$', '', falsifying_trace)
    
    return satisfying_trace, falsifying_trace

def process_stored_responses(raw_responses_csv, output_dir, experiment_type):
    """Process stored responses from CSV"""
    
    # Initialize results dictionaries
    trace_generation_summary_results = {}
    generated_traces_results = []
    
    # Read the raw responses
    raw_df = pd.read_csv(raw_responses_csv)
    
    for _, row in raw_df.iterrows():
        model = row["model"]
        approach = row["approach"]
        formula = row["formula"]
        initial_response = row["initial_response"]
        
        key = f"{model}_{approach}"
        if key not in trace_generation_summary_results:
            trace_generation_summary_results[key] = []
        
        # Process based on approach
        if approach == "zero_shot_self_refine":
            refined_response = row["refined_response"]
            positive_trace, negative_trace = extract_positive_negative_trace(refined_response)
            llm_response = format_llm_response(initial_response, refined_response)
        else:
            positive_trace, negative_trace = extract_positive_negative_trace(initial_response)
            llm_response = format_llm_response(initial_response)
        
        # For output, we want the standard LTL formula (Ground Truth), not AST
        # The formula variable here contains either Ground Truth or AST depending on experiment_type
        # We need to get the Ground Truth for the output
        ltl_formula = formula  # This should be handled in query_and_store_raw_responses
        
        # Store processed results
        generated_traces_results.append({
            "Model": model,
            "Approach": approach,
            "LTL Formula": ltl_formula,
            "LLM Response": llm_response,
            "Positive Trace": positive_trace,
            "Negative Trace": negative_trace
        })
        
        trace_generation_summary_results[key].append({
            "LTL Formula": ltl_formula,
            "Positive Trace": positive_trace,
            "Negative Trace": negative_trace
        })
    
    # Save processed results
    write_detailed_results(output_dir / 'trace_generation_detailed.csv', generated_traces_results)
    
    # Custom summary writing for the specific format needed
    write_custom_summary_results(output_dir / 'trace_generation_summary.csv', trace_generation_summary_results)

def write_custom_summary_results(output_file, summary_results):
    """Write summary results in the specific format: LTL Formula, {MODEL}_{APPROACH}_Positive, {MODEL}_{APPROACH}_Negative"""
    
    # Collect all unique formulas and model_approach combinations
    all_formulas = set()
    model_approach_combinations = list(summary_results.keys())
    
    for results_list in summary_results.values():
        for result in results_list:
            all_formulas.add(result["LTL Formula"])
    
    all_formulas = sorted(list(all_formulas))
    
    # Create headers
    headers = ["LTL Formula"]
    for combo in model_approach_combinations:
        headers.extend([f"{combo}_Positive Trace", f"{combo}_Negative Trace"])
    
    # Write to CSV
    with open(output_file, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=headers)
        writer.writeheader()
        
        for formula in all_formulas:
            row = {"LTL Formula": formula}
            
            for combo in model_approach_combinations:
                # Find the result for this formula and combination
                positive_trace = ""
                negative_trace = ""
                
                for result in summary_results[combo]:
                    if result["LTL Formula"] == formula:
                        positive_trace = result["Positive Trace"]
                        negative_trace = result["Negative Trace"]
                        break
                
                row[f"{combo}_Positive Trace"] = positive_trace
                row[f"{combo}_Negative Trace"] = negative_trace
            
            writer.writerow(row)

def save_raw_responses(model, approach, formula, response_data, output_dir):
    """Save individual raw responses to files for reference"""
    raw_dir = output_dir / 'raw_responses' / model / approach
    raw_dir.mkdir(parents=True, exist_ok=True)
    
    # Create a safe filename from the formula
    safe_formula = "".join(c if c.isalnum() else "_" for c in formula)
    if len(safe_formula) > 50:
        safe_formula = safe_formula[:50]
    
    with open(raw_dir / f"{safe_formula}.txt", 'w', encoding='utf-8') as f:
        f.write(f"Formula: {formula}\n\n")
        f.write(f"Initial Response:\n{response_data['initial_response']}\n\n")
        
        if approach == "zero_shot_self_refine":
            f.write(f"Refined Response:\n{response_data['refined_response']}\n\n")

def query_and_store_raw_responses(dataset, models, approaches, output_csv, experiment_type, generate_prompt_func):
    """Query LLMs and store raw responses to CSV"""
    
    # Create CSV file with headers
    headers = [
        "formula", "ltl_formula", "model", "approach", 
        "initial_response", "refined_response"
    ]
    
    with open(output_csv, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=headers)
        writer.writeheader()
        
        for model in models:
            for approach in approaches:
                print(f"Querying {model} with {approach} approach...")
                
                for _, row in dataset.iterrows():
                    # Get the formula to send to the prompt (AST for python, Ground Truth for others)
                    formula_for_prompt = get_formula_from_row(row, experiment_type)
                    # Get the standard LTL formula for output
                    ltl_formula = get_ltl_formula_from_row(row, experiment_type)
                    
                    response_data = {
                        "formula": formula_for_prompt,
                        "ltl_formula": ltl_formula,
                        "model": model,
                        "approach": approach,
                        "refined_response": ""
                    }

                    if approach == "zero_shot_self_refine":
                        # Step 1: generate initial prompt & response
                        base_prompt = generate_prompt_func(formula_for_prompt, "zero_shot")
                        initial_response = send_request(base_prompt, model)

                        # Step 2: generate refined prompt based on that response
                        refined_prompt = generate_prompt_func(formula_for_prompt, "zero_shot_self_refine", initial_response)
                        refined_response = send_request(refined_prompt, model)

                        # Save both responses
                        response_data["initial_response"] = initial_response
                        response_data["refined_response"] = refined_response
                    
                    else:
                        # Regular zero-shot or few-shot
                        initial_prompt = generate_prompt_func(formula_for_prompt, approach)
                        initial_response = send_request(initial_prompt, model)
                        response_data["initial_response"] = initial_response

                    writer.writerow(response_data)

def process_stored_responses_fixed(raw_responses_csv, output_dir, experiment_type):
    """Process stored responses from CSV with fixed LTL formula handling"""
    
    # Initialize results dictionaries
    trace_generation_summary_results = {}
    generated_traces_results = []
    
    # Read the raw responses
    raw_df = pd.read_csv(raw_responses_csv)
    
    for _, row in raw_df.iterrows():
        model = row["model"]
        approach = row["approach"]
        formula_for_prompt = row["formula"]  # This was used for the prompt (AST or Ground Truth)
        ltl_formula = row["ltl_formula"]     # This is always the standard LTL formula
        initial_response = row["initial_response"]
        
        key = f"{model}_{approach}"
        if key not in trace_generation_summary_results:
            trace_generation_summary_results[key] = []
        
        # Process based on approach
        if approach == "zero_shot_self_refine":
            refined_response = row["refined_response"]
            positive_trace, negative_trace = extract_positive_negative_trace(refined_response)
            llm_response = format_llm_response(initial_response, refined_response)
        else:
            positive_trace, negative_trace = extract_positive_negative_trace(initial_response)
            llm_response = format_llm_response(initial_response)
        
        # Store processed results using the standard LTL formula
        generated_traces_results.append({
            "Model": model,
            "Approach": approach,
            "LTL Formula": ltl_formula,  # Always use the standard LTL formula
            "LLM Response": llm_response,
            "Positive Trace": positive_trace,
            "Negative Trace": negative_trace
        })
        
        trace_generation_summary_results[key].append({
            "LTL Formula": ltl_formula,  # Always use the standard LTL formula
            "Positive Trace": positive_trace,
            "Negative Trace": negative_trace
        })
    
    # Save processed results
    write_detailed_results(output_dir / 'trace_generation_detailed.csv', generated_traces_results)
    write_custom_summary_results(output_dir / 'trace_generation_summary.csv', trace_generation_summary_results)

def format_llm_response(initial_response: str, refined_response: str = None) -> str:
    """Format LLM response combining initial and refined responses if available."""
    if refined_response:
        return f"Initial Response:\n{initial_response}\n\nRefined Response:\n{refined_response}"
    return initial_response

def analyze_results(results_file: str, metrics_output_file: str) -> None:
    """Analyze trace satisfiability results and save metrics to CSV."""
    df = pd.read_csv(results_file)
    
    # Initialize metrics storage
    all_metrics = []
    
    # Calculate metrics for each model and approach combination
    for model in df['Model'].unique():
        for approach in df['Approach'].unique():
            model_approach_df = df[(df['Model'] == model) & (df['Approach'] == approach)]
            
            if len(model_approach_df) == 0:
                continue
                
            # Convert results to binary format
            y_true = []
            y_pred = []
            
            # Positive traces should be SATISFIED
            positive_true = [1] * len(model_approach_df)
            positive_pred = [1 if result == 'SATISFIED' else 0 
                           for result in model_approach_df['Positive Result']]
            
            # Negative traces should be FALSIFIED
            negative_true = [0] * len(model_approach_df)
            negative_pred = [0 if result == 'FALSIFIED' else 1 
                           for result in model_approach_df['Negative Result']]
            
            y_true.extend(positive_true + negative_true)
            y_pred.extend(positive_pred + negative_pred)
            
            metrics = {
                'Model': model,
                'Approach': approach,
                'Accuracy': accuracy_score(y_true, y_pred),
                'Precision': precision_score(y_true, y_pred, zero_division=0),
                'Recall': recall_score(y_true, y_pred, zero_division=0),
                'F1': f1_score(y_true, y_pred, zero_division=0),
                'Total_Traces': len(model_approach_df) * 2,  # Both positive and negative
                'Satisfied_Positive': sum(positive_pred),
                'Falsified_Negative': sum([1 - p for p in negative_pred]),
                'Errors': (
                    model_approach_df['Positive Result'].str.contains('ERROR', na=False).sum() +
                    model_approach_df['Negative Result'].str.contains('ERROR', na=False).sum()
                ),
                'Satisfied_Rate': sum(positive_pred) / len(model_approach_df) if len(model_approach_df) > 0 else 0,
                'Falsified_Rate': sum([1 - p for p in negative_pred]) / len(model_approach_df) if len(model_approach_df) > 0 else 0,
                'Error_Rate': (
                    (model_approach_df['Positive Result'].str.contains('ERROR', na=False).sum() +
                     model_approach_df['Negative Result'].str.contains('ERROR', na=False).sum()) /
                    (len(model_approach_df) * 2)
                ) if len(model_approach_df) > 0 else 0
            }
            
            all_metrics.append(metrics)
    
    # Create DataFrame and save to CSV
    metrics_df = pd.DataFrame(all_metrics)
    
    # Round numeric columns to 4 decimal places
    numeric_columns = metrics_df.select_dtypes(include=['float64']).columns
    metrics_df[numeric_columns] = metrics_df[numeric_columns].round(4)
    
    # Sort by F1 score (or any other metric you prefer)
    metrics_df = metrics_df.sort_values('F1', ascending=False)
    
    # Save to CSV
    metrics_df.to_csv(metrics_output_file, index=False, float_format="%.2f")
    
    # Print summary
    print("\nMetrics Summary:")
    print(metrics_df)
    
    # Calculate and print overall metrics
    if len(metrics_df) > 0:
        print("\nOverall Metrics:")
        for metric in ['Accuracy', 'Precision', 'Recall', 'F1']:
            mean_value = metrics_df[metric].mean()
            std_value = metrics_df[metric].std()
            print(f"Average {metric}: {mean_value:.4f} (±{std_value:.4f})")

def calculate_and_visualize_metrics(results_file: str, output_dir: Path):
    """Calculate metrics and create visualizations."""
    # Read results
    df = pd.read_csv(results_file)
    
    # Calculate metrics for each model-approach combination
    metrics_data = []
    
    for model in df['Model'].unique():
        for approach in df['Approach'].unique():
            model_approach_data = df[(df['Model'] == model) & (df['Approach'] == approach)]
            
            if len(model_approach_data) == 0:
                continue
            
            # Count total traces
            total_traces = len(model_approach_data) * 2  # Both positive and negative
            
            # Calculate various metrics
            positive_satisfaction = (model_approach_data['Positive Result'] == 'SATISFIED').sum()
            negative_falsification = (model_approach_data['Negative Result'] == 'FALSIFIED').sum()
            
            positive_errors = model_approach_data['Positive Result'].str.contains('ERROR', na=False).sum()
            negative_errors = model_approach_data['Negative Result'].str.contains('ERROR', na=False).sum()
            
            # Calculate accuracy metrics
            true_positives = positive_satisfaction
            true_negatives = negative_falsification
            false_positives = len(model_approach_data) - negative_falsification
            false_negatives = len(model_approach_data) - positive_satisfaction
            
            total_correct = true_positives + true_negatives
            
            metrics_data.append({
                'Model': model,
                'Approach': approach,
                'Total_Traces': total_traces,
                'Accuracy': (total_correct / total_traces) * 100 if total_traces > 0 else 0,
                'Precision': (true_positives / (true_positives + false_positives)) * 100 if (true_positives + false_positives) > 0 else 0,
                'Recall': (true_positives / (true_positives + false_negatives)) * 100 if (true_positives + false_negatives) > 0 else 0,
                'F1_Score': (2 * true_positives / (2 * true_positives + false_positives + false_negatives)) * 100 if (2 * true_positives + false_positives + false_negatives) > 0 else 0,
                'Positive_Satisfaction_Rate': (positive_satisfaction / len(model_approach_data)) * 100 if len(model_approach_data) > 0 else 0,
                'Negative_Falsification_Rate': (negative_falsification / len(model_approach_data)) * 100 if len(model_approach_data) > 0 else 0,
                'Error_Rate': ((positive_errors + negative_errors) / total_traces) * 100 if total_traces > 0 else 0,
                'Positive_Satisfaction_Count': positive_satisfaction,
                'Negative_Falsification_Count': negative_falsification,
                'Positive_Errors': positive_errors,
                'Negative_Errors': negative_errors
            })
    
    # Create metrics DataFrame
    metrics_df = pd.DataFrame(metrics_data)
    
    if len(metrics_df) > 0:
        # Save metrics to CSV
        metrics_csv = output_dir / 'detailed_metrics.csv'
        metrics_df.to_csv(metrics_csv, index=False, float_format="%.2f")
        
        # Create visualizations
        create_visualizations(metrics_df, output_dir)

def create_visualizations(metrics_df: pd.DataFrame, output_dir: Path):
    """Create various visualizations of the metrics."""
    # Set style
    plt.style.use('seaborn-v0_8')
    
    # 1. Main Metrics Comparison
    metrics_to_plot = ['Accuracy', 'Precision', 'Recall', 'F1_Score']
    plot_data = pd.melt(metrics_df, 
                        id_vars=['Model', 'Approach'],
                        value_vars=metrics_to_plot,
                        var_name='Metric',
                        value_name='Score')
    
    plt.figure(figsize=(15, 8))
    sns.barplot(data=plot_data, x='Model', y='Score', hue='Metric')
    plt.title('Performance Metrics by Model')
    plt.xticks(rotation=45)
    plt.ylabel('Score (%)')
    plt.legend(bbox_to_anchor=(1.05, 1), loc='upper left')
    plt.tight_layout()
    plt.savefig(output_dir / 'performance_metrics.png', dpi=300, bbox_inches='tight')
    plt.close()
    
    # 2. Approach Comparison
    plt.figure(figsize=(15, 8))
    for i, metric in enumerate(metrics_to_plot):
        plt.subplot(2, 2, i + 1)
        sns.barplot(data=metrics_df, x='Approach', y=metric, hue='Model')
        plt.title(f'{metric} by Approach')
        plt.xticks(rotation=45)
        plt.ylabel('Score (%)')
        if i == 0:  # Only show legend for first subplot
            plt.legend(bbox_to_anchor=(1.05, 1), loc='upper left')
        else:
            plt.legend().remove()
    plt.tight_layout()
    plt.savefig(output_dir / 'approach_comparison.png', dpi=300, bbox_inches='tight')
    plt.close()
    
    # 3. Error Analysis
    error_data = pd.melt(metrics_df,
                        id_vars=['Model', 'Approach'],
                        value_vars=['Positive_Errors', 'Negative_Errors'],
                        var_name='Error_Type',
                        value_name='Count')
    
    plt.figure(figsize=(12, 6))
    sns.barplot(data=error_data, x='Model', y='Count', hue='Error_Type')
    plt.title('Error Analysis by Model')
    plt.xticks(rotation=45)
    plt.ylabel('Number of Errors')
    plt.legend(bbox_to_anchor=(1.05, 1), loc='upper left')
    plt.tight_layout()
    plt.savefig(output_dir / 'error_analysis.png', dpi=300, bbox_inches='tight')
    plt.close()
    
    # 4. Success Rate Analysis
    success_data = pd.melt(metrics_df,
                          id_vars=['Model', 'Approach'],
                          value_vars=['Positive_Satisfaction_Rate', 'Negative_Falsification_Rate'],
                          var_name='Success_Type',
                          value_name='Rate')
    
    plt.figure(figsize=(12, 6))
    sns.barplot(data=success_data, x='Model', y='Rate', hue='Success_Type')
    plt.title('Success Rates by Model')
    plt.xticks(rotation=45)
    plt.ylabel('Success Rate (%)')
    plt.legend(bbox_to_anchor=(1.05, 1), loc='upper left')
    plt.tight_layout()
    plt.savefig(output_dir / 'success_rates.png', dpi=300, bbox_inches='tight')
    plt.close()
    
    # 5. Heatmap of all metrics
    plt.figure(figsize=(15, 10))
    metrics_for_heatmap = metrics_df.select_dtypes(include=['float64', 'int64'])
    if len(metrics_for_heatmap.columns) > 1:
        sns.heatmap(metrics_for_heatmap.corr(), annot=True, cmap='coolwarm', center=0)
        plt.title('Correlation between Metrics')
        plt.tight_layout()
        plt.savefig(output_dir / 'metrics_correlation.png', dpi=300, bbox_inches='tight')
    plt.close()

def main():
    # Parse arguments
    args = parse_args()
    experiment_type = args.experiment_type
    
    # Get models and approaches
    models = args.models if args.models else MODEL_SETS[experiment_type]
    models= ["gpt-3.5-turbo", "gpt-4o-mini", "gpt-4o"]
    # models= ["gemini-1.5-pro", "gemini-1.5-flash", "gemini-2.5-flash","claude-3.5-sonnet"]
    learning_approaches = args.approaches if args.approaches else LEARNING_APPROACHES[experiment_type]
    # learning_approaches = ["few_shot"]
    # Get the prompt generation function
    generate_prompt_func = get_generate_prompt_function(experiment_type)
    
    # Create output directory
    output_dir = Path(f'data/output_data/{experiment_type}/trace_generation')
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Load dataset
    nl2ltl_dataset = pd.read_csv(args.dataset)
    
    # File to store raw responses
    raw_responses_csv = output_dir / 'raw_llm_responses.csv'
    
    # Phase 1: Query LLMs and store raw responses
    if not os.path.exists(raw_responses_csv):
        print("Phase 1: Querying LLMs and storing raw responses...")
        query_and_store_raw_responses(nl2ltl_dataset, models, learning_approaches, raw_responses_csv, experiment_type, generate_prompt_func)
    else:
        print(f"Raw responses file {raw_responses_csv} already exists. Skipping query phase.")
    
    # Phase 2: Process stored responses
    print("Phase 2: Processing stored responses...")
    process_stored_responses_fixed(raw_responses_csv, output_dir, experiment_type)

    PROJECT_ROOT = Path(__file__).resolve().parents[1] 
    ltl_utils_dir = PROJECT_ROOT / "LTL" / "corrected_version" / "ltlutils"

    assert ltl_utils_dir.exists(), f"ltlutils dir does not exist at: {ltl_utils_dir}"

    # Check trace satisfiability with correct parameters
    print("Phase 3: Checking trace satisfiability...")
    check_trace(
        input_csv=output_dir / 'trace_generation_detailed.csv',
        output_csv=output_dir / 'llm_trace_satisfaction_results.csv',
        ltl_utils_dir=ltl_utils_dir
    )
    
    # Define paths for analysis
    output_csv = output_dir / "llm_trace_satisfaction_results.csv"
    metrics_csv = output_dir / "metrics_results.csv"
    
    # Analyze results and save metrics to CSV
    print("Phase 4: Analyzing results...")
    analyze_results(output_csv, metrics_csv)
    
    print("Phase 5: Creating visualizations...")
    calculate_and_visualize_metrics(output_csv, output_dir)
    
    print("Trace generation experiment completed successfully!")

if __name__ == "__main__":
    main()

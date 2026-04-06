import csv
import os
import json
import re
import importlib
from typing import List, Dict, Tuple
import pandas as pd
import matplotlib.pyplot as plt
from sklearn.metrics import (
    accuracy_score, confusion_matrix, precision_recall_fscore_support
)
import sys
import argparse
from pathlib import Path
from tqdm import tqdm

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import your modules (adjust these imports based on your actual module structure)
from parse_prompt import send_request, MODEL_SETS, LEARNING_APPROACHES

def get_generate_prompt_function(experiment_type):
    """Dynamically load the prompt generator function"""
    try:
        module_path = f"prompts.{experiment_type}.trace_characterization_prompt"
        module = importlib.import_module(module_path)
        return module.generate_prompt
    except ImportError as e:
        print(f"Error importing prompt module for {experiment_type}: {e}")
        sys.exit(1)

def parse_args():
    """Parse command line arguments"""
    parser = argparse.ArgumentParser(description="Run trace characterization experiment.")
    parser.add_argument("--dataset", type=str, required=True, 
                       help="Path to the dataset CSV file.")
    parser.add_argument("--experiment_type", required=True, 
                       choices=["minimal", "detailed", "python"],
                       help="Experiment type: minimal, detailed, or python")
    parser.add_argument("--models", nargs="+", 
                       help="Specific models to run (optional)")
    parser.add_argument("--approaches", nargs="+", 
                       help="Specific approaches to run (optional)")
    parser.add_argument("--output_dir", type=str, 
                       help="Custom output directory (optional)")
    parser.add_argument("--skip_generation", action="store_true",
                        help="Skip raw response generation and only process existing responses")
    parser.add_argument("--force_regenerate", action="store_true",
                        help="Force regeneration of raw responses even if file exists")
    return parser.parse_args()

def transform_csv(df: pd.DataFrame, output_file: str, experiment_type: str) -> pd.DataFrame:
    """Transform the input DataFrame into a format with separate rows for positive and negative traces."""
    new_rows = []
    
    if experiment_type == "python":
        # For python experiment, the CSV already has Type column and AST column
        # We just need to ensure we have the right columns
        required_columns = ['LTL Formula', 'Trace', 'Type', 'AST']
        missing_columns = [col for col in required_columns if col not in df.columns]
        
        if missing_columns:
            raise ValueError(f"Missing required columns for python experiment: {missing_columns}")
        
        # Use the data as-is for python experiment type
        new_df = df[required_columns].copy()
        
    else:
        # For minimal/detailed experiments, transform as before
        for _, row in df.iterrows():
            for trace_type in ['Positive', 'Negative']:
                trace_column = f'Cleaned_{trace_type}_Trace'
                if trace_column in row and pd.notna(row[trace_column]):
                    new_rows.append({
                        'LTL Formula': row['LTL Formula'],
                        'Trace': row[trace_column],
                        'Type': trace_type,
                        'AST': None  # No AST for non-python experiments
                    })
        
        new_df = pd.DataFrame(new_rows)
    
    os.makedirs(os.path.dirname(output_file), exist_ok=True)
    new_df.to_csv(output_file, index=False, float_format="%.2f")
    return new_df

def extract_trace_response(response: str) -> str:
    """Extract the final 'Positive' or 'Negative' decision from the LLM's response."""
    if not response:
        return None
        
    positive_match = re.search(r"\bPositive\b", response, re.IGNORECASE)
    negative_match = re.search(r"\bNegative\b", response, re.IGNORECASE)
    
    if positive_match and negative_match:
        return "Positive" if positive_match.end() > negative_match.end() else "Negative"
    elif positive_match:
        return "Positive"
    elif negative_match:
        return "Negative"
    return None

def save_raw_response(model: str, approach: str, formula: str, trace: str, 
                     response: str, output_dir: str) -> None:
    """Save raw LLM response to CSV with overwrite capability for existing entries."""
    output_file = os.path.join(output_dir, "raw_responses.csv")
    os.makedirs(os.path.dirname(output_file), exist_ok=True)
    
    # Create new row
    new_row = {
        'model': model,
        'approach': approach,
        'formula': formula,
        'trace': trace,
        'response': response
    }
    
    try:
        # Read existing CSV if it exists
        if os.path.exists(output_file):
            df = pd.read_csv(output_file)
            
            # Check if entry exists
            mask = (
                (df['model'] == model) & 
                (df['approach'] == approach) & 
                (df['formula'] == formula) & 
                (df['trace'] == trace)
            )
            
            if mask.any():
                # Update existing entry
                df.loc[mask, 'response'] = response
            else:
                # Append new entry
                df = pd.concat([df, pd.DataFrame([new_row])], ignore_index=True)
        else:
            # Create new DataFrame if file doesn't exist
            df = pd.DataFrame([new_row])
        
        # Save back to CSV
        df.to_csv(output_file, index=False)
        
    except Exception as e:
        print(f"Error saving response: {e}")
        # Fallback to simple append if there's an error
        with open(output_file, 'a', newline='') as f:
            writer = csv.writer(f)
            if not os.path.exists(output_file) or os.path.getsize(output_file) == 0:
                writer.writerow(['model', 'approach', 'formula', 'trace', 'response'])
            writer.writerow([model, approach, formula, trace, response])

def ltl_to_python_ast(ltl_formula: str) -> str:
    """Convert LTL formula to Python AST format.
    
    This is a basic converter - you may need to expand this based on your specific LTL syntax.
    """
    # Basic mapping of LTL operators to Python AST format
    conversions = {
        'F': 'Eventually',
        'G': 'Always', 
        'X': 'Next',
        'U': 'Until',
        '->': 'LImplies',
        '&': 'LAnd',
        '|': 'LOr',
        '!': 'LNot'
    }
    
  
    result = ltl_formula
    
    # Handle atomic propositions (variables like x1, x2)
    import re
    variables = re.findall(r'\b[a-zA-Z_][a-zA-Z0-9_]*\b', ltl_formula)
    for var in set(variables):
        if var not in conversions:
            result = result.replace(var, f'AtomicProposition("{var}")')
    
    # Handle operators (this is very basic - you may need more sophisticated parsing)
    for ltl_op, ast_op in conversions.items():
        if ltl_op in ['F', 'G', 'X']:
            # Unary operators
            result = re.sub(f'{ltl_op}\(([^)]+)\)', f'{ast_op}(\\1)', result)
        elif ltl_op in ['->', '&', '|']:
            # Binary operators  
            result = result.replace(ltl_op, f',{ast_op},')
    
    return result

def get_formula_for_experiment(row: pd.Series, experiment_type: str) -> str:
    """Get the appropriate formula representation based on experiment type."""
    if experiment_type == "python":
        # Use AST column if available, otherwise convert LTL formula
        if 'AST' in row and pd.notna(row['AST']):
            return row['AST']
        else:
            return ltl_to_python_ast(row['LTL Formula'])
    else:
        return row['LTL Formula']
    

def calculate_metrics(y_true: List[str], y_pred: List[str]) -> Dict:
    """Calculate evaluation metrics for a set of predictions."""
    if not y_true or not y_pred:
        return {}
        
    try:
        accuracy = accuracy_score(y_true, y_pred)
        precision, recall, f1, _ = precision_recall_fscore_support(
            y_true, y_pred, average='weighted', zero_division=0
        )
        
        return {
            "Accuracy": round(accuracy * 100, 2),
            "Precision": round(precision * 100, 2),
            "Recall": round(recall * 100, 2),
            "F1": round(f1 * 100, 2),
            "Sample_Count": len(y_true),
            "Error_Count": sum(1 for t, p in zip(y_true, y_pred) if t != p)
        }
    except Exception as e:
        print(f"Error calculating metrics: {e}")
        return {}

def process_single_case(model: str, approach: str, formula: str, trace: str, 
                       true_type: str, generate_prompt_func, output_dir: str, experiment_type: str = "minimal") -> Dict:
    """Process a single test case and save raw response immediately."""
    try:
        # Use appropriate formula format based on experiment type
        if experiment_type == "python":
            # For python experiments, the formula should already be in AST format
            prompt_formula = formula
        else:
            # For minimal/detailed, use the LTL formula as-is
            prompt_formula = formula
            
        # Generate initial prompt and get API response
        initial_prompt = generate_prompt_func(prompt_formula, trace, "zero_shot")
        initial_response = send_request(initial_prompt, model)
        
        # Save raw response immediately
        save_raw_response(model, approach, formula, trace, initial_response, output_dir)
        
        # Handle zero-shot self-refine case
        if approach == "zero_shot_self_refine" and initial_response:
            # Generate refined prompt based on initial response
            refined_prompt = generate_prompt_func(prompt_formula, trace, approach, initial_response)
            refined_response = send_request(refined_prompt, model)
            
            # Save refined response
            save_raw_response(model, f"{approach}_refined", formula, trace, refined_response, output_dir)
            
            # Extract final response from refined response
            extracted_response = extract_trace_response(refined_response)
            full_response = f"Initial: {initial_response}\nRefined: {refined_response}"
        else:
            # Extract final response for non-refined cases
            extracted_response = extract_trace_response(initial_response)
            full_response = initial_response
            
        # Return structured result for analysis
        return {
            "Model": model,
            "Approach": approach,
            "LTL Formula": formula,
            "Trace": trace,
            "Ground Truth": true_type,
            "Raw Response": full_response,
            "LLM Response": extracted_response
        }
        
    except Exception as e:
        print(f"Error processing case: {e}")
        return None

def run_analysis(dataset: pd.DataFrame, models: List[str], approaches: List[str], 
                generate_prompt_func, output_dir: str, experiment_type: str) -> Tuple[List[Dict], pd.DataFrame]:
    """Run the complete analysis pipeline."""
    results = []
    metrics_data = []
    
    # Process each combination of model and approach
    for model in models:
        for approach in approaches:
            print(f"\nProcessing {model} with {approach} approach...")
            true_labels, predicted_labels = [], []
            
            # Process each row in dataset
            for _, row in tqdm(dataset.iterrows(), total=len(dataset)):
                # Get the appropriate formula based on experiment type
                if experiment_type == "python":
                    # Use AST if available, otherwise convert LTL
                    formula = get_formula_for_experiment(row, experiment_type)
                else:
                    # Use LTL Formula for minimal/detailed
                    formula = row["LTL Formula"]
                
                result = process_single_case(
                    model=model,
                    approach=approach,
                    formula=formula,
                    trace=row["Trace"],
                    true_type=row["Type"],
                    generate_prompt_func=generate_prompt_func,
                    output_dir=output_dir,
                    experiment_type=experiment_type
                )
                
                if result:
                    results.append(result)
                    if result["Ground Truth"] and result["LLM Response"]:
                        true_labels.append(result["Ground Truth"])
                        predicted_labels.append(result["LLM Response"])
            
            # Calculate metrics for this combination
            if true_labels and predicted_labels:
                metrics = calculate_metrics(true_labels, predicted_labels)
                metrics["Model"] = model
                metrics["Approach"] = approach
                metrics_data.append(metrics)
    
    # Convert metrics to DataFrame
    metrics_df = pd.DataFrame(metrics_data)
    return results, metrics_df

def save_results(results: List[Dict], metrics_df: pd.DataFrame, output_dir: str) -> None:
    """Save both detailed results and summary metrics to files."""
    # Create directories if they don't exist
    metrics_dir = os.path.join(output_dir, "metrics")
    os.makedirs(metrics_dir, exist_ok=True)
    
    # 1. Save detailed results
    if results:
        detailed_results_df = pd.DataFrame(results)
        detailed_results_df.to_csv(
            os.path.join(output_dir, "processed_results.csv"), 
            index=False
        )
    
    # 2. Save combined metrics
    if not metrics_df.empty:
        metrics_df.to_csv(
            os.path.join(metrics_dir, "combined_metrics.csv"),
            index=False,
            float_format="%.2f"
        )
        
        # 3. Save aggregated metrics
        # Model-wise metrics
        if 'Model' in metrics_df.columns:
            model_metrics = metrics_df.groupby('Model').mean(numeric_only=True).reset_index()
            model_metrics.to_csv(
                os.path.join(metrics_dir, "model_metrics.csv"),
                index=False,
                float_format="%.2f"
            )
        
        # Approach-wise metrics
        if 'Approach' in metrics_df.columns:
            approach_metrics = metrics_df.groupby('Approach').mean(numeric_only=True).reset_index()
            approach_metrics.to_csv(
                os.path.join(metrics_dir, "approach_metrics.csv"),
                index=False,
                float_format="%.2f"
            )
    
    # 4. Save confusion matrices
    if results:
        confusion_matrices = []
        results_df = pd.DataFrame(results)
        
        for model in results_df['Model'].unique():
            for approach in results_df['Approach'].unique():
                mask = (results_df['Model'] == model) & (results_df['Approach'] == approach)
                subset = results_df[mask]
                
                if len(subset) > 0:
                    y_true = subset['Ground Truth'].dropna()
                    y_pred = subset['LLM Response'].dropna()
                    
                    # Align the series
                    common_idx = y_true.index.intersection(y_pred.index)
                    y_true_aligned = y_true.loc[common_idx]
                    y_pred_aligned = y_pred.loc[common_idx]
                    
                    if len(y_true_aligned) > 0 and len(y_pred_aligned) > 0:
                        cm = confusion_matrix(y_true_aligned, y_pred_aligned)
                        confusion_matrices.append({
                            'Model': model,
                            'Approach': approach,
                            'Confusion_Matrix': cm.tolist(),
                            'Labels': sorted(y_true_aligned.unique())
                        })
        
        if confusion_matrices:
            with open(os.path.join(metrics_dir, "confusion_matrices.json"), 'w') as f:
                json.dump(confusion_matrices, f, indent=2)

def evaluate_and_save_metrics(results_df: pd.DataFrame, 
                            metrics_output_dir: str) -> Tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """Calculate and save detailed evaluation metrics."""
    os.makedirs(metrics_output_dir, exist_ok=True)
    
    combined_metrics = []
    confusion_matrices = []
    
    for model in results_df['Model'].unique():
        for approach in results_df['Approach'].unique():
            mask = (results_df['Model'] == model) & (results_df['Approach'] == approach)
            subset = results_df[mask]
            
            if len(subset) == 0:
                continue
                
            y_true = subset['Ground Truth']
            y_pred = subset['LLM Response']
            
            # Filter NaN values row-wise instead of skipping entire combinations
            valid_mask = ~(y_true.isna() | y_pred.isna())
            y_true_clean = y_true[valid_mask]
            y_pred_clean = y_pred[valid_mask]
            
            # Only skip if NO valid data remains
            if len(y_true_clean) == 0:
                print(f"Warning: No valid data for {model} - {approach}")
                continue
                
            accuracy = accuracy_score(y_true_clean, y_pred_clean)
            precision, recall, f1, _ = precision_recall_fscore_support(
                y_true_clean, y_pred_clean, average='weighted', zero_division=0
            )
            
            cm = confusion_matrix(y_true_clean, y_pred_clean)
            confusion_matrices.append({
                'Model': model,
                'Approach': approach,
                'Confusion_Matrix': cm.tolist(),
                'Labels': sorted(y_true_clean.unique())
            })
            
            combined_metrics.append({
                'Model': model,
                'Approach': approach,
                "Accuracy": round(accuracy * 100, 2),
                "Precision": round(precision * 100, 2),
                "F1": round(f1 * 100, 2),
                'Sample_Count': len(y_true_clean),
                'Error_Count': sum(y_true_clean != y_pred_clean)
            })
    
    combined_df = pd.DataFrame(combined_metrics)
    
    # Aggregate metrics
    model_metrics = pd.DataFrame()
    approach_metrics = pd.DataFrame()
    
    if not combined_df.empty:
        if 'Model' in combined_df.columns:
            model_metrics = combined_df.groupby('Model').agg({
                'Accuracy': 'mean',
                'Precision': 'mean',
                'F1': 'mean',
                'Sample_Count': 'sum',
                'Error_Count': 'sum'
            }).reset_index()
        
        if 'Approach' in combined_df.columns:
            approach_metrics = combined_df.groupby('Approach').agg({
                'Accuracy': 'mean',
                'Precision': 'mean',
                'F1': 'mean',
                'Sample_Count': 'sum',
                'Error_Count': 'sum'
            }).reset_index()
    
    # Save metrics
    for name, df in [('combined_metrics', combined_df), 
                    ('model_metrics', model_metrics), 
                    ('approach_metrics', approach_metrics)]:
        if not df.empty:
            df.to_csv(f'{metrics_output_dir}/{name}.csv', index=False, float_format="%.2f")
    
    if confusion_matrices:
        with open(f'{metrics_output_dir}/confusion_matrices.json', 'w') as f:
            json.dump(confusion_matrices, f, indent=2)
    
    print(f"Metrics saved to {metrics_output_dir}")
    print(f"Combined metrics shape: {combined_df.shape}")
    
    return model_metrics, approach_metrics, combined_df

def main():
    """Main execution function."""
    # Parse command line arguments
    args = parse_args()
    
    # Set up output directory
    if args.output_dir:
        output_dir = args.output_dir
    else:
        output_dir = f"data/output_data/{args.experiment_type}/trace_characterization"
    
    os.makedirs(output_dir, exist_ok=True)
    
    # Get the prompt generation function
    generate_prompt = get_generate_prompt_function(args.experiment_type)
    
    # Determine models and approaches to use
    models = args.models if args.models else MODEL_SETS[args.experiment_type]
    models= ["gemini-1.5-pro", "claude-3.5-sonnet"]
    approaches = args.approaches if args.approaches else LEARNING_APPROACHES[args.experiment_type]
    
    print(f"Running experiment with:")
    print(f"Dataset: {args.dataset}")
    print(f"Experiment type: {args.experiment_type}")
    print(f"Models: {models}")
    print(f"Approaches: {approaches}")
    print(f"Output directory: {output_dir}")
    
    # Load dataset
    if not os.path.exists(args.dataset):
        print(f"Error: Dataset file {args.dataset} not found.")
        sys.exit(1)
    
    try:
        nl2ltl_dataset = pd.read_csv(args.dataset)
        print(f"Loaded dataset with {len(nl2ltl_dataset)} rows")
    except Exception as e:
        print(f"Error loading dataset: {e}")
        sys.exit(1)
    
    # Transform data
    transformed_file = os.path.join(output_dir, 'randomized_positive_negative_trace.csv')
    randomized_dataset = transform_csv(nl2ltl_dataset, transformed_file, args.experiment_type)
    print(f"Transformed dataset has {len(randomized_dataset)} rows")
    
    # Run analysis pipeline
    print("Starting analysis...")
    results, summary_results = run_analysis(
        randomized_dataset, models, approaches, generate_prompt, output_dir, args.experiment_type
    )
    
    # Save results
    print("Saving results...")
    save_results(results, summary_results, output_dir)
    
    # Calculate detailed metrics if we have results
    if results:
        processed_results_file = os.path.join(output_dir, "processed_results.csv")
        if os.path.exists(processed_results_file):
            processed_df = pd.read_csv(processed_results_file)
            
            # Calculate metrics and analyze
            metrics_output_dir = os.path.join(output_dir, 'metrics')
            model_metrics, approach_metrics, combined_metrics = evaluate_and_save_metrics(
                processed_df, metrics_output_dir
            )
            
            # Display results
            print("\nCombined Metrics:")
            if not combined_metrics.empty:
                print(combined_metrics.to_string(index=False))
            else:
                print("No metrics computed.")
            
            # Try to run enhanced evaluation if available
            try:
                from scripts.trace_characterization_eval import enhance_evaluation
                advanced_metrics, confidence_intervals = enhance_evaluation(
                    processed_df,
                    os.path.join(output_dir, 'advanced_analysis')
                )
                print("Enhanced evaluation completed.")
            except ImportError:
                print("Enhanced evaluation module not available, skipping.")
    
    print(f"Analysis complete. Results saved in {output_dir}")

if __name__ == "__main__":
    main()



# import csv
# import os
# import json
# import re
# import importlib
# from typing import List, Dict, Tuple
# import pandas as pd
# import matplotlib.pyplot as plt
# from sklearn.metrics import (
#     accuracy_score, confusion_matrix, precision_recall_fscore_support
# )
# import sys
# import argparse
# from pathlib import Path
# from tqdm import tqdm

# # Add parent directory to path for imports
# sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# # Import your modules (adjust these imports based on your actual module structure)
# from parse_prompt import send_request, MODEL_SETS, LEARNING_APPROACHES

# def get_generate_prompt_function(experiment_type):
#     """Dynamically load the prompt generator function"""
#     try:
#         module_path = f"prompts.{experiment_type}.trace_characterization_prompt"
#         module = importlib.import_module(module_path)
#         return module.generate_prompt
#     except ImportError as e:
#         print(f"Error importing prompt module for {experiment_type}: {e}")
#         sys.exit(1)

# def parse_args():
#     """Parse command line arguments"""
#     parser = argparse.ArgumentParser(description="Run trace characterization experiment.")
#     parser.add_argument("--dataset", type=str, required=True, 
#                        help="Path to the dataset CSV file.")
#     parser.add_argument("--experiment_type", required=True, 
#                        choices=["minimal", "detailed", "python"],
#                        help="Experiment type: minimal, detailed, or python")
#     parser.add_argument("--models", nargs="+", 
#                        help="Specific models to run (optional)")
#     parser.add_argument("--approaches", nargs="+", 
#                        help="Specific approaches to run (optional)")
#     parser.add_argument("--output_dir", type=str, 
#                        help="Custom output directory (optional)")
#     return parser.parse_args()

# def transform_csv(df: pd.DataFrame, output_file: str) -> pd.DataFrame:
#     """Transform the input DataFrame into a format with separate rows for positive and negative traces."""
#     new_rows = []
    
#     for _, row in df.iterrows():
#         for trace_type in ['Positive', 'Negative']:
#             trace_column = f'Cleaned_{trace_type}_Trace'
#             if trace_column in row and pd.notna(row[trace_column]):
#                 new_rows.append({
#                     'LTL Formula': row['LTL Formula'],
#                     'Trace': row[trace_column],
#                     'Type': trace_type
#                 })
    
#     new_df = pd.DataFrame(new_rows)
#     os.makedirs(os.path.dirname(output_file), exist_ok=True)
#     new_df.to_csv(output_file, index=False, float_format="%.2f")
#     return new_df

# def extract_trace_response(response: str) -> str:
#     """Extract the final 'Positive' or 'Negative' decision from the LLM's response."""
#     if not response:
#         return None
        
#     positive_match = re.search(r"\bPositive\b", response, re.IGNORECASE)
#     negative_match = re.search(r"\bNegative\b", response, re.IGNORECASE)
    
#     if positive_match and negative_match:
#         return "Positive" if positive_match.end() > negative_match.end() else "Negative"
#     elif positive_match:
#         return "Positive"
#     elif negative_match:
#         return "Negative"
#     return None

# def save_raw_response(model: str, approach: str, formula: str, trace: str, 
#                      response: str, output_dir: str) -> None:
#     """Save raw LLM response to CSV with overwrite capability for existing entries."""
#     output_file = os.path.join(output_dir, "raw_responses.csv")
#     os.makedirs(os.path.dirname(output_file), exist_ok=True)
    
#     # Create new row
#     new_row = {
#         'model': model,
#         'approach': approach,
#         'formula': formula,
#         'trace': trace,
#         'response': response
#     }
    
#     try:
#         # Read existing CSV if it exists
#         if os.path.exists(output_file):
#             df = pd.read_csv(output_file)
            
#             # Check if entry exists
#             mask = (
#                 (df['model'] == model) & 
#                 (df['approach'] == approach) & 
#                 (df['formula'] == formula) & 
#                 (df['trace'] == trace)
#             )
            
#             if mask.any():
#                 # Update existing entry
#                 df.loc[mask, 'response'] = response
#             else:
#                 # Append new entry
#                 df = pd.concat([df, pd.DataFrame([new_row])], ignore_index=True)
#         else:
#             # Create new DataFrame if file doesn't exist
#             df = pd.DataFrame([new_row])
        
#         # Save back to CSV
#         df.to_csv(output_file, index=False)
        
#     except Exception as e:
#         print(f"Error saving response: {e}")
#         # Fallback to simple append if there's an error
#         with open(output_file, 'a', newline='') as f:
#             writer = csv.writer(f)
#             if not os.path.exists(output_file) or os.path.getsize(output_file) == 0:
#                 writer.writerow(['model', 'approach', 'formula', 'trace', 'response'])
#             writer.writerow([model, approach, formula, trace, response])

# def calculate_metrics(y_true: List[str], y_pred: List[str]) -> Dict:
#     """Calculate evaluation metrics for a set of predictions."""
#     if not y_true or not y_pred:
#         return {}
        
#     try:
#         accuracy = accuracy_score(y_true, y_pred)
#         precision, recall, f1, _ = precision_recall_fscore_support(
#             y_true, y_pred, average='weighted', zero_division=0
#         )
        
#         return {
#             "Accuracy": round(accuracy * 100, 2),
#             "Precision": round(precision * 100, 2),
#             "Recall": round(recall * 100, 2),
#             "F1": round(f1 * 100, 2),
#             "Sample_Count": len(y_true),
#             "Error_Count": sum(1 for t, p in zip(y_true, y_pred) if t != p)
#         }
#     except Exception as e:
#         print(f"Error calculating metrics: {e}")
#         return {}

# def process_single_case(model: str, approach: str, formula: str, trace: str, 
#                        true_type: str, generate_prompt_func, output_dir: str) -> Dict:
#     """Process a single test case and save raw response immediately."""
#     try:
#         # Generate initial prompt and get API response
#         initial_prompt = generate_prompt_func(formula, trace, "zero_shot")
#         initial_response = send_request(initial_prompt, model)
        
#         # Save raw response immediately
#         save_raw_response(model, approach, formula, trace, initial_response, output_dir)
        
#         # Handle zero-shot self-refine case
#         if approach == "zero_shot_self_refine" and initial_response:
#             # Generate refined prompt based on initial response
#             refined_prompt = generate_prompt_func(formula, trace, approach, initial_response)
#             refined_response = send_request(refined_prompt, model)
            
#             # Save refined response
#             save_raw_response(model, f"{approach}_refined", formula, trace, refined_response, output_dir)
            
#             # Extract final response from refined response
#             extracted_response = extract_trace_response(refined_response)
#             full_response = f"Initial: {initial_response}\nRefined: {refined_response}"
#         else:
#             # Extract final response for non-refined cases
#             extracted_response = extract_trace_response(initial_response)
#             full_response = initial_response
            
#         # Return structured result for analysis
#         return {
#             "Model": model,
#             "Approach": approach,
#             "LTL Formula": formula,
#             "Trace": trace,
#             "Ground Truth": true_type,
#             "Raw Response": full_response,
#             "LLM Response": extracted_response
#         }
        
#     except Exception as e:
#         print(f"Error processing case: {e}")
#         return None

# def run_analysis(dataset: pd.DataFrame, models: List[str], approaches: List[str], 
#                 generate_prompt_func, output_dir: str) -> Tuple[List[Dict], pd.DataFrame]:
#     """Run the complete analysis pipeline."""
#     results = []
#     metrics_data = []
    
#     # Process each combination of model and approach
#     for model in models:
#         for approach in approaches:
#             print(f"\nProcessing {model} with {approach} approach...")
#             true_labels, predicted_labels = [], []
            
#             # Process each row in dataset
#             for _, row in tqdm(dataset.iterrows(), total=len(dataset)):
#                 result = process_single_case(
#                     model=model,
#                     approach=approach,
#                     formula=row["LTL Formula"],
#                     trace=row["Trace"],
#                     true_type=row["Type"],
#                     generate_prompt_func=generate_prompt_func,
#                     output_dir=output_dir
#                 )
                
#                 if result:
#                     results.append(result)
#                     if result["Ground Truth"] and result["LLM Response"]:
#                         true_labels.append(result["Ground Truth"])
#                         predicted_labels.append(result["LLM Response"])
            
#             # Calculate metrics for this combination
#             if true_labels and predicted_labels:
#                 metrics = calculate_metrics(true_labels, predicted_labels)
#                 metrics["Model"] = model
#                 metrics["Approach"] = approach
#                 metrics_data.append(metrics)
    
#     # Convert metrics to DataFrame
#     metrics_df = pd.DataFrame(metrics_data)
#     return results, metrics_df

# def save_results(results: List[Dict], metrics_df: pd.DataFrame, output_dir: str) -> None:
#     """Save both detailed results and summary metrics to files."""
#     # Create directories if they don't exist
#     metrics_dir = os.path.join(output_dir, "metrics")
#     os.makedirs(metrics_dir, exist_ok=True)
    
#     # 1. Save detailed results
#     if results:
#         detailed_results_df = pd.DataFrame(results)
#         detailed_results_df.to_csv(
#             os.path.join(output_dir, "processed_results.csv"), 
#             index=False
#         )
    
#     # 2. Save combined metrics
#     if not metrics_df.empty:
#         metrics_df.to_csv(
#             os.path.join(metrics_dir, "combined_metrics.csv"),
#             index=False,
#             float_format="%.2f"
#         )
        
#         # 3. Save aggregated metrics
#         # Model-wise metrics
#         if 'Model' in metrics_df.columns:
#             model_metrics = metrics_df.groupby('Model').mean(numeric_only=True).reset_index()
#             model_metrics.to_csv(
#                 os.path.join(metrics_dir, "model_metrics.csv"),
#                 index=False,
#                 float_format="%.2f"
#             )
        
#         # Approach-wise metrics
#         if 'Approach' in metrics_df.columns:
#             approach_metrics = metrics_df.groupby('Approach').mean(numeric_only=True).reset_index()
#             approach_metrics.to_csv(
#                 os.path.join(metrics_dir, "approach_metrics.csv"),
#                 index=False,
#                 float_format="%.2f"
#             )
    
#     # 4. Save confusion matrices
#     if results:
#         confusion_matrices = []
#         results_df = pd.DataFrame(results)
        
#         for model in results_df['Model'].unique():
#             for approach in results_df['Approach'].unique():
#                 mask = (results_df['Model'] == model) & (results_df['Approach'] == approach)
#                 subset = results_df[mask]
                
#                 if len(subset) > 0:
#                     y_true = subset['Ground Truth'].dropna()
#                     y_pred = subset['LLM Response'].dropna()
                    
#                     # Align the series
#                     common_idx = y_true.index.intersection(y_pred.index)
#                     y_true_aligned = y_true.loc[common_idx]
#                     y_pred_aligned = y_pred.loc[common_idx]
                    
#                     if len(y_true_aligned) > 0 and len(y_pred_aligned) > 0:
#                         cm = confusion_matrix(y_true_aligned, y_pred_aligned)
#                         confusion_matrices.append({
#                             'Model': model,
#                             'Approach': approach,
#                             'Confusion_Matrix': cm.tolist(),
#                             'Labels': sorted(y_true_aligned.unique())
#                         })
        
#         if confusion_matrices:
#             with open(os.path.join(metrics_dir, "confusion_matrices.json"), 'w') as f:
#                 json.dump(confusion_matrices, f, indent=2)

# def evaluate_and_save_metrics(results_df: pd.DataFrame, 
#                             metrics_output_dir: str) -> Tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
#     """Calculate and save detailed evaluation metrics."""
#     os.makedirs(metrics_output_dir, exist_ok=True)
    
#     combined_metrics = []
#     confusion_matrices = []
    
#     for model in results_df['Model'].unique():
#         for approach in results_df['Approach'].unique():
#             mask = (results_df['Model'] == model) & (results_df['Approach'] == approach)
#             subset = results_df[mask]
            
#             if len(subset) == 0:
#                 continue
                
#             y_true = subset['Ground Truth']
#             y_pred = subset['LLM Response']
            
#             # Filter NaN values row-wise instead of skipping entire combinations
#             valid_mask = ~(y_true.isna() | y_pred.isna())
#             y_true_clean = y_true[valid_mask]
#             y_pred_clean = y_pred[valid_mask]
            
#             # Only skip if NO valid data remains
#             if len(y_true_clean) == 0:
#                 print(f"Warning: No valid data for {model} - {approach}")
#                 continue
                
#             accuracy = accuracy_score(y_true_clean, y_pred_clean)
#             precision, recall, f1, _ = precision_recall_fscore_support(
#                 y_true_clean, y_pred_clean, average='weighted', zero_division=0
#             )
            
#             cm = confusion_matrix(y_true_clean, y_pred_clean)
#             confusion_matrices.append({
#                 'Model': model,
#                 'Approach': approach,
#                 'Confusion_Matrix': cm.tolist(),
#                 'Labels': sorted(y_true_clean.unique())
#             })
            
#             combined_metrics.append({
#                 'Model': model,
#                 'Approach': approach,
#                 "Accuracy": round(accuracy * 100, 2),
#                 "Precision": round(precision * 100, 2),
#                 "F1": round(f1 * 100, 2),
#                 'Sample_Count': len(y_true_clean),
#                 'Error_Count': sum(y_true_clean != y_pred_clean)
#             })
    
#     combined_df = pd.DataFrame(combined_metrics)
    
#     # Aggregate metrics
#     model_metrics = pd.DataFrame()
#     approach_metrics = pd.DataFrame()
    
#     if not combined_df.empty:
#         if 'Model' in combined_df.columns:
#             model_metrics = combined_df.groupby('Model').agg({
#                 'Accuracy': 'mean',
#                 'Precision': 'mean',
#                 'F1': 'mean',
#                 'Sample_Count': 'sum',
#                 'Error_Count': 'sum'
#             }).reset_index()
        
#         if 'Approach' in combined_df.columns:
#             approach_metrics = combined_df.groupby('Approach').agg({
#                 'Accuracy': 'mean',
#                 'Precision': 'mean',
#                 'F1': 'mean',
#                 'Sample_Count': 'sum',
#                 'Error_Count': 'sum'
#             }).reset_index()
    
#     # Save metrics
#     for name, df in [('combined_metrics', combined_df), 
#                     ('model_metrics', model_metrics), 
#                     ('approach_metrics', approach_metrics)]:
#         if not df.empty:
#             df.to_csv(f'{metrics_output_dir}/{name}.csv', index=False, float_format="%.2f")
    
#     if confusion_matrices:
#         with open(f'{metrics_output_dir}/confusion_matrices.json', 'w') as f:
#             json.dump(confusion_matrices, f, indent=2)
    
#     print(f"Metrics saved to {metrics_output_dir}")
#     print(f"Combined metrics shape: {combined_df.shape}")
    
#     return model_metrics, approach_metrics, combined_df

# def main():
#     """Main execution function."""
#     # Parse command line arguments
#     args = parse_args()
    
#     # Set up output directory
#     if args.output_dir:
#         output_dir = args.output_dir
#     else:
#         output_dir = f"data/output_data/{args.experiment_type}/trace_characterization"
    
#     os.makedirs(output_dir, exist_ok=True)
    
#     # Get the prompt generation function
#     generate_prompt = get_generate_prompt_function(args.experiment_type)
    

#     models = args.models if args.models else MODEL_SETS[args.experiment_type]
#     # models= ["gemini-1.5-pro", "claude-3.5-sonnet"]
#     approaches = args.approaches if args.approaches else LEARNING_APPROACHES[args.experiment_type]
    
#     print(f"Running experiment with:")
#     print(f"Dataset: {args.dataset}")
#     print(f"Experiment type: {args.experiment_type}")
#     print(f"Models: {models}")
#     print(f"Approaches: {approaches}")
#     print(f"Output directory: {output_dir}")
    
#     # Load dataset
#     if not os.path.exists(args.dataset):
#         print(f"Error: Dataset file {args.dataset} not found.")
#         sys.exit(1)
    
#     try:
#         nl2ltl_dataset = pd.read_csv(args.dataset)
#         print(f"Loaded dataset with {len(nl2ltl_dataset)} rows")
#     except Exception as e:
#         print(f"Error loading dataset: {e}")
#         sys.exit(1)
    
#     # Transform data
#     transformed_file = os.path.join(output_dir, 'randomized_positive_negative_trace.csv')
#     randomized_dataset = transform_csv(nl2ltl_dataset, transformed_file)
#     print(f"Transformed dataset has {len(randomized_dataset)} rows")
    
#     # Run analysis pipeline
#     print("Starting analysis...")
#     results, summary_results = run_analysis(
#         randomized_dataset, models, approaches, generate_prompt, output_dir
#     )
    
#     # Save results
#     print("Saving results...")
#     save_results(results, summary_results, output_dir)
    
#     # Calculate detailed metrics if we have results
#     if results:
#         processed_results_file = os.path.join(output_dir, "processed_results.csv")
#         if os.path.exists(processed_results_file):
#             processed_df = pd.read_csv(processed_results_file)
            
#             # Calculate metrics and analyze
#             metrics_output_dir = os.path.join(output_dir, 'metrics')
#             model_metrics, approach_metrics, combined_metrics = evaluate_and_save_metrics(
#                 processed_df, metrics_output_dir
#             )
            
#             # Display results
#             print("\nCombined Metrics:")
#             if not combined_metrics.empty:
#                 print(combined_metrics.to_string(index=False))
#             else:
#                 print("No metrics computed.")
            
#             # Try to run enhanced evaluation if available
#             try:
#                 from scripts.trace_characterization_eval import enhance_evaluation
#                 advanced_metrics, confidence_intervals = enhance_evaluation(
#                     processed_df,
#                     os.path.join(output_dir, 'advanced_analysis')
#                 )
#                 print("Enhanced evaluation completed.")
#             except ImportError:
#                 print("Enhanced evaluation module not available, skipping.")
    
#     print(f"Analysis complete. Results saved in {output_dir}")

# if __name__ == "__main__":
#     main()
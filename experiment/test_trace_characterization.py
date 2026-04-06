import csv
import os
import json
import re
from typing import List, Dict, Tuple
import pandas as pd
import seaborn as sns
import matplotlib.pyplot as plt
from sklearn.metrics import (
    accuracy_score,confusion_matrix,precision_recall_fscore_support
)
from trace_characterization_eval import enhance_evaluation
from load_data import load_data
from parse_request import send_request
from trace_characterization_prompt_template import generate_prompt
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import List, Dict, Tuple
from tqdm import tqdm
from collections import defaultdict

# Constants
LEARNING_APPROACHES = ["zero_shot", "zero_shot_self_refine", "few_shot"]
MODELS = ["gpt-3.5-turbo", "gpt-4o-mini", "gpt-4o", "claude-sonnet", "gemini"]
OUTPUT_DIR = "output/trace_characterization"

def transform_csv(df: pd.DataFrame, output_file: str = f'{OUTPUT_DIR}/randomized_positive_negative_trace.csv') -> pd.DataFrame:
    """Transform the input DataFrame into a format with separate rows for positive and negative traces."""
    new_rows = []
    
    for _, row in df.iterrows():
        for trace_type in ['Positive', 'Negative']:
            new_rows.append({
                'LTL Formula': row['LTL Formula'],
                'Trace': row[f'Cleaned_{trace_type}_Trace'],
                'Type': trace_type
            })
    
    new_df = pd.DataFrame(new_rows)
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

def save_llm_response(model: str, approach: str, formula: str, trace: str, 
                     response: str, output_file: str = f'{OUTPUT_DIR}/raw_llm_responses.csv') -> None:
    """Save raw LLM response with experiment metadata."""
    os.makedirs(os.path.dirname(output_file), exist_ok=True)
    
    if not os.path.exists(output_file):
        with open(output_file, 'w', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(['model', 'approach', 'formula', 'trace', 'response'])
    
    with open(output_file, 'a', newline='') as f:
        writer = csv.writer(f)
        writer.writerow([model, approach, formula, trace, response, pd.Timestamp.now()])

def calculate_metrics(y_true: List[str], y_pred: List[str]) -> Dict:
    """Calculate evaluation metrics for a set of predictions."""
    if not y_true or not y_pred:
        return {}
        
    try:
        accuracy = accuracy_score(y_true, y_pred)
        precision, recall, f1, _ = precision_recall_fscore_support(y_true, y_pred, average='weighted')
        
        return {
            "Accuracy": round(accuracy * 100, 1),
            "Precision": round(precision * 100, 1),
            "Recall": round(recall * 100, 1),
            "F1": round(f1 * 100, 1),
            "Sample_Count": len(y_true),
            "Error_Count": sum(1 for t, p in zip(y_true, y_pred) if t != p)
        }
    except Exception as e:
        print(f"Error calculating metrics: {e}")
        return {}

def process_single_case(model: str, approach: str, formula: str, trace: str, true_type: str) -> Dict:
    """Process a single test case and save raw response immediately."""
    try:
        # 1. Generate initial prompt and get API response
        initial_prompt = generate_prompt(formula, trace, approach)
        initial_response = send_request(initial_prompt, model)
        
        # 2. Save raw response immediately
        save_raw_response(model, approach, formula, trace, initial_response)
        
        # Handle zero-shot self-refine case only if we haven't already refined
        if approach == "zero_shot_self_refine" and initial_response:
            # Generate refined prompt based on initial response
            refined_prompt = generate_prompt(formula, trace, approach, initial_response)
            refined_response = send_request(refined_prompt, model)
            
            # Save refined response
            save_raw_response(model, f"{approach}_refined", formula, trace, refined_response)
            
            # 3. Extract final response from refined response
            extracted_response = extract_trace_response(refined_response)
            full_response = f"Initial: {initial_response}\nRefined: {refined_response}"
        else:
            # 3. Extract final response for non-refined cases
            extracted_response = extract_trace_response(initial_response)
            full_response = initial_response
            
        # 4. Return structured result for analysis
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

def save_raw_response(model: str, approach: str, formula: str, trace: str, response: str) -> None:
    """Save raw LLM response to CSV with overwrite capability for existing entries."""
    output_file = os.path.join("output", "trace_characterization", "raw_responses.csv")
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
            if os.path.getsize(output_file) == 0:
                writer.writerow(['model', 'approach', 'formula', 'trace', 'response'])
            writer.writerow([model, approach, formula, trace, response])

def run_analysis(dataset: pd.DataFrame, models: List[str], approaches: List[str]) -> Tuple[List[Dict], pd.DataFrame]:
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
                result = process_single_case(
                    model=model,
                    approach=approach,
                    formula=row["LTL Formula"],
                    trace=row["Trace"],
                    true_type=row["Type"]
                )
                
                if result:
                    results.append(result)
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
    detailed_results_df = pd.DataFrame(results)
    detailed_results_df.to_csv(
        os.path.join(output_dir, "processed_results.csv"), 
        index=False
    )
    
    # 2. Save combined metrics
    metrics_df.to_csv(
        os.path.join(metrics_dir, "combined_metrics.csv"),
        index=False,
        float_format="%.2f"
    )
    
    # 3. Save aggregated metrics
    # Model-wise metrics
    model_metrics = metrics_df.groupby('Model').mean(numeric_only=True).reset_index()
    model_metrics.to_csv(
        os.path.join(metrics_dir, "model_metrics.csv"),
        index=False,
        float_format="%.2f"
    )
    
    # Approach-wise metrics
    approach_metrics = metrics_df.groupby('Approach').mean(numeric_only=True).reset_index()
    approach_metrics.to_csv(
        os.path.join(metrics_dir, "approach_metrics.csv"),
        index=False,
        float_format="%.2f"
    )
    
    # 4. Save confusion matrices
    confusion_matrices = []
    for model in metrics_df['Model'].unique():
        for approach in metrics_df['Approach'].unique():
            mask = (pd.DataFrame(results)['Model'] == model) & \
                   (pd.DataFrame(results)['Approach'] == approach)
            subset = pd.DataFrame(results)[mask]
            
            if len(subset) > 0:
                y_true = subset['Ground Truth']
                y_pred = subset['LLM Response']
                
                if not (y_true.isna().any() or y_pred.isna().any()):
                    cm = confusion_matrix(y_true, y_pred)
                    confusion_matrices.append({
                        'Model': model,
                        'Approach': approach,
                        'Confusion_Matrix': cm.tolist(),
                        'Labels': sorted(subset['Ground Truth'].unique())
                    })
    
    with open(os.path.join(metrics_dir, "confusion_matrices.json"), 'w') as f:
        json.dump(confusion_matrices, f, indent=2)

def evaluate_and_save_metrics(results_df: pd.DataFrame, 
                            OUTPUT_DIR: str = f'{OUTPUT_DIR}/metrics') -> Tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """Calculate and save detailed evaluation metrics."""
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    
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
            
            if y_true.isna().any() or y_pred.isna().any():
                continue
                
            accuracy = accuracy_score(y_true, y_pred)
            precision, recall, f1, _ = precision_recall_fscore_support(y_true, y_pred, average='weighted')
            
            cm = confusion_matrix(y_true, y_pred)
            confusion_matrices.append({
                'Model': model,
                'Approach': approach,
                'Confusion_Matrix': cm.tolist(),
                'Labels': sorted(subset['Ground Truth'].unique())
            })
            
            combined_metrics.append({
                'Model': model,
                'Approach': approach,
                "Accuracy": round(accuracy * 100, 1),
                "Precision": round(precision * 100, 1),
                # "Recall": round(recall * 100, 2),
                "F1": round(f1 * 100, 1),
                'Sample_Count': len(subset),
                'Error_Count': sum(y_true != y_pred)
            })
    
    combined_df = pd.DataFrame(combined_metrics)
    
    # Aggregate metrics
    model_metrics = combined_df.groupby('Model').agg({
        'Accuracy': 'mean',
        'Precision': 'mean',
        # 'Recall': 'mean',
        'F1': 'mean',
        'Sample_Count': 'sum',
        'Error_Count': 'sum'
    }).reset_index()
    
    approach_metrics = combined_df.groupby('Approach').agg({
        'Accuracy': 'mean',
        'Precision': 'mean',
        # 'Recall': 'mean',
        'F1': 'mean',
        'Sample_Count': 'sum',
        'Error_Count': 'sum'
    }).reset_index()
    
    # Save metrics
    for name, df in [('combined_metrics', combined_df), 
                    ('model_metrics', model_metrics), 
                    ('approach_metrics', approach_metrics)]:
        df.to_csv(f'{OUTPUT_DIR}/{name}.csv', index=False, float_format="%.2f")
    
    with open(f'{OUTPUT_DIR}/confusion_matrices.json', 'w') as f:
        json.dump(confusion_matrices, f, indent=2)
    
    return model_metrics, approach_metrics, combined_df

def main():
    """Main execution function."""
    # Create output directories
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    
    # Load and transform data
    # input_file = f'{OUTPUT_DIR}/positive_negative_traces.csv'
    # nl2ltl_dataset = load_data(input_file)
    
    # if nl2ltl_dataset is None:
    #     print("Failed to load dataset. Please check the file path and contents.")
    #     return
    # randomized_dataset = transform_csv(nl2ltl_dataset)
    
    # # Run analysis pipeline
    # results, summary_results = run_analysis(randomized_dataset, MODELS, LEARNING_APPROACHES)
    
    # # Save results
    # save_results(results, summary_results, OUTPUT_DIR)
    
    processed_df = pd.read_csv("output/trace_characterization/processed_results.csv")
    # Calculate metrics and analyze
    model_metrics, approach_metrics, combined_metrics = evaluate_and_save_metrics(processed_df)
    advanced_metrics, confidence_intervals = enhance_evaluation(
        processed_df,
        f'{OUTPUT_DIR}/advanced_analysis'
    )
    print("Analysis complete. Results saved in output directory.")

if __name__ == "__main__":
    main()
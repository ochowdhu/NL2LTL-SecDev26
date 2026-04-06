import pandas as pd
import re
import time
from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score
pd.options.display.float_format = "{:,.2f}".format
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
# from prompts.minimal.wff_prompt_template import generate_prompt
import importlib

from parse_prompt import send_request
import argparse
from parse_prompt import MODEL_SETS, LEARNING_APPROACHES

def get_generate_prompt_function(experiment_type):
    """Dynamically load the prompt generator function"""
    module_path = f"prompts.{experiment_type}.wff_prompt_template"
    module = importlib.import_module(module_path)
    return module.generate_prompt

def parse_args():
    """Parse command line arguments"""
    parser = argparse.ArgumentParser(description="Run WFF characterization experiment.")
    parser.add_argument("--dataset", type=str, required=True, help="Path to the dataset CSV file.")
    parser.add_argument("--experiment_type", required=True, choices=["minimal", "detailed", "python"],
                        help="Experiment type: minimal, detailed, or python")
    parser.add_argument("--models", nargs="+", help="Specific models to run (optional)")
    parser.add_argument("--approaches", nargs="+", help="Specific approaches to run (optional)")
    return parser.parse_args()
args = parse_args()

#FOR TESTING
# learning_approaches = ["zero_shot_self_refine"]
# # learning_approaches = ["zero_shot", "zero_shot_self_refine", "few_shot"]
# # models = ["gpt-3.5-turbo", "gpt-4o-mini", "gpt-4o", "claude-3.5-sonnet", "gemini-1.5-pro"]
# models=["claude-3.5-sonnet"]

models = args.models if args.models else MODEL_SETS[args.experiment_type]
learning_approaches = args.approaches if args.approaches else LEARNING_APPROACHES[args.experiment_type]
    
print(f"Models: {models}")
print(f"Approaches: {learning_approaches}")

def characterize_wff(ltl_formula, approach, model, generate_prompt):
    """
    Characterize WFF with proper raw response handling
    """
    if approach == "zero_shot_self_refine":
        # Step 1: First get initial response with zero_shot approach
        initial_prompt = generate_prompt(ltl_formula, "zero_shot")
        initial_response = send_request(initial_prompt, model)
        
        # Step 2: Generate the refinement prompt using the initial response
        refinement_prompt = handle_self_refinement(initial_prompt, initial_response)
        
        # Step 3: Send the refinement request
        refined_response = send_request(refinement_prompt, model)
        
        # Return the RAW refined response
        return refined_response
    
    else:
        # Step 1: Generate the prompt for zero_shot or few_shot
        prompt = generate_prompt(ltl_formula, approach)
        
        # Step 2: Send the request
        response = send_request(prompt, model)
        
        # Return the RAW response
        return response

def handle_self_refinement(base_prompt, initial_response):
    """Generate refinement prompt for self-refinement approach"""
    refinement_prompt = f"""{base_prompt}

Your initial answer was: {initial_response}

Now, please carefully reconsider your answer. Think step by step:
1. Check if all parentheses are properly balanced
2. Verify that all operators have the correct number of operands
3. Ensure all propositional variables follow the naming convention [a-zA-Z][a-zA-Z0-9]*
4. Check that temporal operators are used correctly
5. Verify the overall syntactic structure matches the BNF grammar

After this careful analysis, what is your final answer?

I just need a Yes or No answer. No explanation is needed."""

    return refinement_prompt

def extract_llm_response(raw_response):
    """
    Extract Yes/No from raw model response - used only in detailed processing
    """
    if not isinstance(raw_response, str):
        return "No"
    
    # Handle None or empty responses
    if not raw_response or raw_response.strip() == "":
        return "No"
    
    # Clean the response
    cleaned_response = raw_response.strip()

    yes_patterns = [
        r'\bYes\b',
        r'\bTRUE\b',
        r'\bCorrect\b',
        r'\bValid\b',
        r'is\s+well[- ]formed',
        r'is\s+a\s+well[- ]formed'
    ]
    
    no_patterns = [
        r'\bNo\b',
        r'\bFALSE\b',
        r'\bIncorrect\b',
        r'\bInvalid\b',
        r'not\s+well[- ]formed',
        r'is\s+not\s+a\s+well[- ]formed'
    ]
    
    # Check for Yes patterns first
    for pattern in yes_patterns:
        if re.search(pattern, cleaned_response, re.IGNORECASE):
            return "Yes"
    
    # Check for No patterns
    for pattern in no_patterns:
        if re.search(pattern, cleaned_response, re.IGNORECASE):
            return "No"
    
    # If no clear pattern found, default to No
    return "No"

def characterize_with_retries(ltl_formula, approach, model, generate_prompt, max_retries=3, delay=2):
    """
    Enhanced retry function - returns only raw response
    """
    retries = 0
    last_error = None
    
    while retries < max_retries:
        try:
            raw_response = characterize_wff(ltl_formula, approach, model, generate_prompt)
            
            # Validate that we got a proper response
            if raw_response is None or str(raw_response).strip() == "":
                raise ValueError("Empty response received from model")
                
            return raw_response
            
        except Exception as e:
            last_error = e
            retries += 1
            print(f"Error: {e}. Retry {retries}/{max_retries} in {delay} seconds...")
            if retries < max_retries:
                time.sleep(delay)
                delay *= 2
    
    # If all retries failed, return a default response
    print(f"All retries failed for formula '{ltl_formula}' with approach '{approach}'. Last error: {last_error}")
    return f"ERROR: All retries failed. Last error: {last_error}"

def process_row(row, models, learning_approaches, generate_prompt):
    """
    Process row - save RAW responses, extract predictions in detailed analysis
    """
    ltl_formula = row['LTL Formula']
    ground_truth = row['Ground Truth']
    results = []
    
    for model in models:
        for approach in learning_approaches:
            try:
                print(f"Processing: {model} with {approach} approach...")
                
                raw_response = characterize_with_retries(ltl_formula, approach, model, generate_prompt)
                
                result = {
                    'Model': model,
                    'Approach': approach,
                    'LTL Formula': ltl_formula,
                    'Ground Truth': ground_truth,
                    'Raw Response': raw_response,  # This is the actual model output
                }
                
                results.append(result)
                print(f"✓ Completed: {model}-{approach}")
                
            except Exception as e:
                print(f"✗ Failed: {model}-{approach} for formula {ltl_formula[:50]}... Error: {e}")
                
                # Add a failed result entry
                results.append({
                    'Model': model,
                    'Approach': approach,
                    'LTL Formula': ltl_formula,
                    'Ground Truth': ground_truth,
                    'Raw Response': f"PROCESSING_ERROR: {str(e)}",
                })
    
    return results

def save_raw_results(file_path, results):
    """
    Save raw results with actual model responses
    """
    # Create directory if it doesn't exist
    os.makedirs(os.path.dirname(file_path), exist_ok=True)
    
    df = pd.DataFrame(results)
    df.to_csv(file_path, index=False, encoding='utf-8')
    print(f"Raw results (with actual model responses) saved to {file_path}")

def evaluate_detailed_results(raw_results_df):
    """
    Enhanced evaluation that extracts predictions from raw responses
    """
    detailed_results = raw_results_df.copy()
    
    detailed_results['LLM Prediction'] = detailed_results['Raw Response'].apply(extract_llm_response)
    
    detailed_results['Well-Formed'] = detailed_results['LLM Prediction'].apply(lambda x: x == "Yes")
    detailed_results['Correct'] = (detailed_results['Ground Truth'] == detailed_results['LLM Prediction']).astype(int)
    
    detailed_results['Prediction_Category'] = detailed_results.apply(
        lambda row: 'True Positive' if row['Ground Truth'] == 'Yes' and row['LLM Prediction'] == 'Yes'
        else 'True Negative' if row['Ground Truth'] == 'No' and row['LLM Prediction'] == 'No'
        else 'False Positive' if row['Ground Truth'] == 'No' and row['LLM Prediction'] == 'Yes'
        else 'False Negative', axis=1
    )
    
    # Calculate aggregate metrics
    aggregate_metrics = []
    for (model, approach), group in detailed_results.groupby(['Model', 'Approach']):
        ground_truths = group['Ground Truth']
        predictions = group['LLM Prediction']
        
        tp = sum((ground_truths == 'Yes') & (predictions == 'Yes'))
        tn = sum((ground_truths == 'No') & (predictions == 'No'))
        fp = sum((ground_truths == 'No') & (predictions == 'Yes'))
        fn = sum((ground_truths == 'Yes') & (predictions == 'No'))
        
        metrics = {
            'Model': model,
            'Approach': approach,
            'Total_Samples': len(group),
            'Yes_Samples': sum(ground_truths == 'Yes'),
            'No_Samples': sum(ground_truths == 'No'),
            'True_Positives': tp,
            'True_Negatives': tn,
            'False_Positives': fp,
            'False_Negatives': fn,
            'Accuracy': accuracy_score(ground_truths, predictions)*100,
            'Precision': precision_score(ground_truths, predictions, pos_label="Yes", zero_division=0)*100,
            'Recall': recall_score(ground_truths, predictions, pos_label="Yes", zero_division=0)*100,
            'F1_Score': f1_score(ground_truths, predictions, pos_label="Yes", zero_division=0)*100
        }
        aggregate_metrics.append(metrics)
    
    return detailed_results, pd.DataFrame(aggregate_metrics)

def generate_and_save_raw_results(input_file, output_file, generate_prompt):
    """
    Generate and save results with RAW model responses
    """
    dataset = pd.read_csv(input_file)
    randomized_dataset = dataset.sample(frac=1).reset_index(drop=True)
    
    print(f"Processing {len(randomized_dataset)} formulas with {len(models)} models and {len(learning_approaches)} approaches")
    
    # Process rows
    all_results = []
    
    for idx, (_, row) in enumerate(randomized_dataset.iterrows()):
        print(f"\n--- Processing row {idx + 1}/{len(randomized_dataset)} ---")
        try:
            row_results = process_row(row, models, learning_approaches, generate_prompt)
            all_results.extend(row_results)
            
            # Save intermediate results every 10 rows
            if (idx + 1) % 10 == 0:
                temp_df = pd.DataFrame(all_results)
                temp_file = output_file.replace('.csv', f'_temp_{idx+1}.csv')
                # Create directory if it doesn't exist
                os.makedirs(os.path.dirname(temp_file), exist_ok=True)
                temp_df.to_csv(temp_file, index=False, encoding='utf-8')
                print(f"Intermediate results saved to {temp_file}")
                
        except Exception as e:
            print(f"Error processing row {idx + 1}: {e}")
            continue
    
    # Final save - RAW responses only
    save_raw_results(output_file, all_results)
    print(f"Total results generated: {len(all_results)}")
    
    return all_results

def evaluate_from_saved_results(raw_results_file, detailed_output_file, aggregate_output_file):
    """
    Load raw results and generate detailed analysis with extracted predictions
    """
    try:
        print(f"Loading raw results from {raw_results_file}")
        raw_results_df = pd.read_csv(raw_results_file)
        
        print("Extracting predictions from raw responses and calculating metrics...")
        detailed_results, aggregate_metrics = evaluate_detailed_results(raw_results_df)
        
        # Save detailed results (with extracted predictions)
        os.makedirs(os.path.dirname(detailed_output_file), exist_ok=True)
        detailed_results.to_csv(detailed_output_file, float_format="%.2f", index=False)
        print(f"Detailed results (with extracted predictions) saved to {detailed_output_file}")
        
        # Save aggregate metrics
        os.makedirs(os.path.dirname(aggregate_output_file), exist_ok=True)
        aggregate_metrics.to_csv(aggregate_output_file, float_format="%.2f", index=False)
        print(f"Aggregate metrics saved to {aggregate_output_file}")
        
        # Print summaries
        print("\nExtraction Summary by Approach:")
        extraction_summary = detailed_results.groupby(['Approach', 'LLM Prediction']).size().unstack(fill_value=0)
        print(extraction_summary)
        
        print("\nSample Raw Responses for Self-Refinement:")
        self_refine_samples = detailed_results[detailed_results['Approach'] == 'zero_shot_self_refine']['Raw Response'].head(3)
        for i, response in enumerate(self_refine_samples, 1):
            print(f"\nSample {i}:")
            print(f"Raw: {str(response)[:200]}...")
            print(f"Extracted: {extract_llm_response(response)}")
        
        return detailed_results, aggregate_metrics
        
    except Exception as e:
        print(f"Error during evaluation: {e}")
        raise

def main():
    experiment_type = args.experiment_type
    dataset_file = args.dataset
    
    # Dynamically load the prompt generator
    generate_prompt = get_generate_prompt_function(experiment_type)

    pd.options.display.float_format = "{:,.2f}".format
    
    # Define output file paths
    raw_results_file = f'data/output_data/{experiment_type}/wff/wff_raw_results.csv'
    detailed_output_file = f'data/output_data/{experiment_type}/wff/wff_detailed_results.csv'
    aggregate_output_file = f'data/output_data/{experiment_type}/wff/wff_aggregate_metrics.csv'

    try:
        print("=== PHASE 1: Generating Raw Results ===")
        raw_results = generate_and_save_raw_results(
            dataset_file, raw_results_file, generate_prompt
        )

        print("\n=== PHASE 2: Processing Raw Results ===")
        detailed_results, aggregate_metrics = evaluate_from_saved_results(
            raw_results_file,
            detailed_output_file,
            aggregate_output_file
        )

        print("\n=== PROCESS COMPLETE ===")
        print(f"Raw responses saved to: {raw_results_file}")
        print(f"Detailed analysis saved to: {detailed_output_file}")
        print(f"Aggregate metrics saved to: {aggregate_output_file}")

    except Exception as e:
        print(f"Error in main execution: {e}")
        raise

if __name__ == "__main__":
    main()
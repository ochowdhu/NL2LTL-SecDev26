import csv
import pandas as pd
from collections import defaultdict
import random 

def summarize_detailed(file):
    # Load your dataset
    try:
        df = pd.read_csv(file)  # Ensure the file path is correct
    except FileNotFoundError:
        print(f"Error: The file {file} was not found.")
        return

    # Group by Model and Approach, then calculate mean metrics
    summary = df.groupby(['Model', 'Approach']).agg({
        'Phrase Accuracy': 'mean',
        'Phrase Precision': 'mean',
        'Phrase Recall': 'mean',
        'Phrase F1 score': 'mean',
        'Proposition Accuracy': 'mean',
        'Proposition Precision': 'mean',
        'Proposition Recall': 'mean',
        'Proposition F1 score': 'mean'
    }).reset_index()

    # Save summary to CSV
    output_file = 'output/nl2pl_model_approach_summary.csv'
    summary.to_csv(output_file, index=False)
    
    print(f"Summary saved to {output_file}")
    return summary

def format_nl2prop_metrics_for_csv(results, output_file):
    # Create a dictionary to store the data
    data = defaultdict(lambda: defaultdict(str))
    
    # Column headers
    headers = ['Natural Language', 'Ground Truth']
    model_approach_metrics = set()

    # Process the results
    for result in results:
        nl = result['Natural Language']
        gt = result['Ground Truth']
        model = result['Model']
        approach = result['Approach']

        data[nl]['Ground Truth'] = gt

        # Handle metrics
        for metric, value in result.items():
            if metric not in ['Model', 'Approach', 'Natural Language', 'Ground Truth', 'LLM Response', 'Derived Propositions']:
                column_name = f"{model}_{approach}_{metric}"
                data[nl][column_name] = value
                model_approach_metrics.add(column_name)

    # Sort the model_approach_metrics and add them to headers
    headers.extend(sorted(model_approach_metrics))

    # Write to CSV
    with open(output_file, 'w', newline='', encoding='utf-8') as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=headers)
        writer.writeheader()

        for nl, row_data in data.items():
            row = {'Natural Language': nl}
            row.update(row_data)
            writer.writerow(row)

def format_nl2pl_results_for_csv(results, output_file):
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
        extract_ltl = result['Derived Propositions']

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

def summarize_wff_detailed(file):
    # Load your dataset
    try:
        df = pd.read_csv(file)  # Ensure the file path is correct
    except FileNotFoundError:
        print(f"Error: The file {file} was not found.")
        return

    # Group by Model and Approach, then calculate mean metrics
    summary = df.groupby(['Model', 'Approach']).agg({
        'Accuracy': 'mean',
        'Precision': 'mean',
        'Recall': 'mean',
        'F1 Score': 'mean'
    }).reset_index()

    # Save summary to CSV
    output_file = 'output/wff_model_approach_summary.csv'
    summary.to_csv(output_file, index=False)
    
    print(f"Summary saved to {output_file}")
    return summary

def format_wff_metrics_for_csv(results, output_file):
    # Create a dictionary to store the data
    data = defaultdict(lambda: defaultdict(str))
    
    # Column headers
    headers = ['LTL Formula']
    model_approach_metrics = set()

    # Process the results
    for result in results:
        ltl_formula = result['LTL Formula']
        model = result['Model']
        approach = result['Approach']

        # Handle metrics
        for key, value in result.items():
            if key not in ['Model', 'Approach', 'LTL Formula', 'Ground Truth', 'LLM Prediction', 'Raw response',"Well Formed Check"]:
                column_name = f"{model}*{approach}*{key}"
                data[ltl_formula][column_name] = value
                model_approach_metrics.add(column_name)

    # Sort the model_approach_metrics and add them to headers
    headers.extend(sorted(model_approach_metrics))

    # Write to CSV
    with open(output_file, 'w', newline='', encoding='utf-8') as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=headers)
        writer.writeheader()

        for ltl_formula, row_data in data.items():
            row = {'LTL Formula': ltl_formula}
            row.update(row_data)
            writer.writerow(row)

def format_wff_results_for_csv(results, output_file):
    # Create a dictionary to store the data
    data = defaultdict(lambda: defaultdict(str))
    
    # Column headers
    headers = ['LTL Formula', 'Ground Truth']
    model_approaches = set()

    # Process the results
    for result in results:
        ltl = result['LTL Formula']
        gt = result['Ground Truth']
        model_approach = f"{result['Model']}_{result['Approach']}"
        extract_ltl = result['LLM Prediction']
        is_wff = result['Well Formed Check']

        data[ltl]['Ground Truth'] = gt
        data[ltl][model_approach] = extract_ltl
        data[ltl][model_approach] = is_wff
        model_approaches.add(model_approach)

    # Sort the model_approaches and add them to headers
    headers.extend(sorted(model_approaches))

    # Write to CSV
    with open(output_file, 'w', newline='', encoding='utf-8') as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=headers)
        writer.writeheader()

        for ltl, row_data in data.items():
            row = {'LTL Formula': ltl}
            row.update(row_data)
            writer.writerow(row)

def format_generated_traces_for_csv(results, output_file):
    # Create a dictionary to store the data
    data = defaultdict(lambda: defaultdict(str))
    
    # Column headers
    headers = ['LTL Formula']
    model_approach_traces = set()

    # Process the results
    for result in results:
        ltl_formula = result['LTL Formula']
        model = result['Model']
        approach = result['Approach']
        positive_trace = result['Positive Trace']
        negative_trace = result['Negative Trace']

        positive_column = f"{model}_{approach}_PositiveTrace"
        negative_column = f"{model}_{approach}_NegativeTrace"

        data[ltl_formula][positive_column] = positive_trace
        data[ltl_formula][negative_column] = negative_trace

        model_approach_traces.add(positive_column)
        model_approach_traces.add(negative_column)

    # Sort and add the model_approach_traces to headers
    headers.extend(sorted(model_approach_traces))

    # Write to CSV
    with open(output_file, 'w', newline='', encoding='utf-8') as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=headers)
        writer.writeheader()

        for ltl_formula, row_data in data.items():
            row = {'LTL Formula': ltl_formula}
            row.update(row_data)
            writer.writerow(row)


def randomize_traces_and_save(traces_results, output_path):
    randomized_results = []

    # Iterate over each key (model_approach combination) and its traces
    for key, traces in traces_results.items():
        for result in traces:
            formula = result['LTL Formula']
            positive_trace = result['Positive Trace']
            negative_trace = result['Negative Trace']

            # Create trace entries for both Positive and Negative
            trace_entries = [
                {"LTL Formula": formula, "Trace": positive_trace, "Type": "Positive"},
                {"LTL Formula": formula, "Trace": negative_trace, "Type": "Negative"}
            ]

            # Randomize the order of traces
            random.shuffle(trace_entries)

            # Append randomized traces to the result list
            randomized_results.extend(trace_entries)

    # Write the randomized traces to a new CSV file
    with open(output_path, 'w', newline='') as csvfile:
        fieldnames = ["LTL Formula", "Trace", "Type"]
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)

        writer.writeheader()
        for row in randomized_results:
            writer.writerow(row)

    print(f"Randomized trace dataset saved to {output_path}")



def store_detailed_results(detailed_nl_to_prop_results, detailed_wff_results, nl2ltl_results):
    # Save detailed results for NL to Propositional Logic
    with open('nl_to_atomic_proposition_results_detailed.csv', 'w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=detailed_nl_to_prop_results[0].keys())
        writer.writeheader()
        writer.writerows(detailed_nl_to_prop_results)

    # Save detailed WFF characterization results
    with open('wff_characterization_results_detailed.csv', 'w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=detailed_wff_results[0].keys())
        writer.writeheader()
        writer.writerows(detailed_wff_results)

    # Save LTL generation results
    with open("ltl_generation_results.csv", 'w', newline='', encoding='utf-8') as csvfile:
        fieldnames = ['Model', 'Approach', 'Natural Language', 'Atomic Proposition', 'Ground Truth', 'Generated Response', 'Extracted LTL']
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()
        for result in nl2ltl_results:
            writer.writerow(result)
    
    print("Detailed results saved.")

def store_summarized_results(results, wff_results, summary_results, models, learning_approaches, nl2pl_dataset, nl2ltl_dataset, wff_dataset):
    # Save aggregated results for NL to Propositional Logic
    with open('nl_to_atomic_proposition_results_summary.csv', 'w', newline='') as f:
        writer = csv.writer(f)
        metrics_headers = list(next(iter(results.values())).values())[0].keys()
        writer.writerow(['Model', 'Approach'] + list(metrics_headers))
        for model in results:
            for approach in results[model]:
                writer.writerow([model, approach] + list(results[model][approach].values()))

    # Save combined results without extra columns
    with open('nl_to_atomic_proposition_combined_results.csv', 'w', newline='') as f:
        writer = csv.writer(f)
        header = ['Natural Language', 'Ground Truth', 'Phrase Accuracy', 'Proposition Accuracy']
        for model in models:
            for approach in learning_approaches:
                header.extend([f'{model}_{approach}_{metric}' for metric in ['Accuracy', 'Precision', 'Recall', 'F1 Score']])
        writer.writerow(header)

        for i, data in enumerate(nl2pl_dataset):
            row = [data['Natural Language'], data['Ground Truth']]
            first_model = models[0]
            first_approach = learning_approaches[0]
            first_result = results[first_model][first_approach]
            row.extend([first_result['Phrase Accuracy'], first_result['Proposition Accuracy']])
            for model in models:
                for approach in learning_approaches:
                    result = results[model][approach]
                    row.extend([result.get('Accuracy', ''), result.get('Precision', ''), result.get('Recall', ''), result.get('F1 Score', '')])
            writer.writerow(row)

    # Save summarized WFF characterization results
    with open('wff_characterization_results_summary.csv', 'w', newline='') as f:
        writer = csv.writer(f)
        metrics_headers = list(next(iter(wff_results.values())).values())[0].keys()
        writer.writerow(['Model', 'Approach'] + list(metrics_headers))
        for model in wff_results:
            for approach in wff_results[model]:
                writer.writerow([model, approach] + list(wff_results[model][approach].values()))

    # Save summarized LTL generation results
    with open("ltl_generation_summary.csv", 'w', newline='', encoding='utf-8') as csvfile:
        fieldnames = ['Model_Approach', 'Natural Language', 'Atomic Proposition', 'Ground Truth', 'Extracted LTL']
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()
        for key, results in summary_results.items():
            for result in results:
                row = {'Model_Approach': key, **result}
                writer.writerow(row)

    print("Summarized results saved.")

def save_detailed_results_to_csv(file_path, fieldnames, detailed_results):
    """Save detailed results to a CSV file."""
    with open(file_path, 'w', newline='', encoding='utf-8') as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(detailed_results)
    print(f"Detailed results saved to {file_path}")

def save_summary_results_to_csv(file_path, fieldnames, summary_results):
    """Save summarized results to a CSV file."""
    with open(file_path, 'w', newline='', encoding='utf-8') as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()
        for key, results in summary_results.items():
            for result in results:
                row = {'Model_Approach': key, **result}
                writer.writerow(row)
    print(f"Summary results saved to {file_path}")
def save_summary_results_to_csv(file_path, summary_results):
    """Save summarized results to a CSV file with dynamic column headers based on model, approach, and evaluation metric."""
    # Create dynamic fieldnames based on model, approach, and evaluation metrics
    fieldnames = []
    first_entry = next(iter(summary_results.values()))  # Get first entry to extract metrics

    for result in first_entry:
        for metric in result:
            # Construct column header as {model}_{approach}_{metric}
            model_approach = result.get('Model_Approach', '')
            if model_approach and metric not in fieldnames:
                fieldnames.append(f"{model_approach}_{metric}")
    
    # Save results to CSV
    with open(file_path, 'w', newline='', encoding='utf-8') as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()
        for key, results in summary_results.items():
            row = {}
            for result in results:
                model_approach = result.get('Model_Approach', key)
                for metric, value in result.items():
                    # Combine model, approach, and metric into one field
                    row[f"{model_approach}_{metric}"] = value
            writer.writerow(row)
    print(f"Summary results saved to {file_path}")

            
def write_summary_results(filename, results, metrics):
    """
    Write the summary results dynamically based on the provided metrics.

    Args:
    - filename (str): The file to save the results.
    - results (dict): The evaluation results for various model_approach combinations.
    - metrics (list): The list of evaluation metrics to include in the summary.
    """
    if not results:
        print(f"No results to write to {filename}")
        return
    
    with open(filename, 'w', newline='') as f:
        writer = csv.writer(f)

        # Get all unique model_approach combinations
        model_approaches = list(results.keys())

        # Build the dynamic headers based on the model_approach and metrics
        headers = ['LTL Formula']
        for model_approach in model_approaches:
            for metric in metrics:
                headers.append(f"{model_approach}_{{{metric}}}")
        
        # Write the header row
        writer.writerow(headers)
        
        # Prepare data rows
        max_entries = max(len(entries) for entries in results.values())

        # Prepare data rows
        for i in range(max_entries):
            row = []

            # Add the LTL Formula from the first model_approach (assuming it's consistent across models)
            first_model_approach = next(iter(results))
            if i < len(results[first_model_approach]):
                row.append(results[first_model_approach][i].get('LTL Formula', ''))
            else:
                row.append('')

            # Add the metrics for each model_approach dynamically
            for model_approach in model_approaches:
                for metric in metrics:
                    if i < len(results[model_approach]):
                        row.append(results[model_approach][i].get(metric, ''))
                    else:
                        row.append('')  # Empty value if no data for this metric
            
            writer.writerow(row)

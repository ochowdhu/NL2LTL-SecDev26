import pandas as pd
import numpy as np
from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score, confusion_matrix
from pathlib import Path
import sys

script_dir = Path(__file__).parent
project_root = script_dir.parent  # Assumes script is in experiments/
experiment_name = sys.argv[1] if len(sys.argv) > 1 else "nl2futureltl"

experiment_dir = project_root / "output_data" / experiment_name

def read_data(filepath):
    """Read the CSV data with error handling"""
    try:
        return pd.read_csv(filepath)
    except Exception as e:
        print(f"Error reading file: {e}")
        return None

def extract_columns(df):
    models = ["claude-sonnet", "gemini-2.5-flash", "gemini-2.5-pro", "gpt-4.1", "gpt-4o"]
    prompt_types = ['few_shot', 'zero_shot', 'zero_shot_self_refine']

    model_cols = [col for col in df.columns if any(model in col for model in models)
                  and not col.startswith(('Eq_', 'En_', 'Syntax_'))]
    eq_cols = [col for col in df.columns if col.startswith('Eq_')]
    en_cols = [col for col in df.columns if col.startswith('En_')]
    syntax_cols = [col for col in df.columns if col.startswith('Syntax_')]

    return model_cols, eq_cols, en_cols, syntax_cols, models, prompt_types
    
def analyze_pairwise_comparisons(df, eq_cols, en_cols):
    """Analyze pairwise model comparisons"""
    equiv_results = []
    entail_results = []
    
    # Equivalence analysis
    for col in eq_cols:
        if '_vs_' not in col:
            continue
            
        parts = col.replace('Eq_', '').split('_vs_')
        if len(parts) != 2:
            continue
            
        model1, model2 = parts[0], parts[1]
        
        valid_rows = (df[col] != 'NOT_MEANINGFUL') & (df[col] != 'ERROR')
        if valid_rows.sum() == 0:
            continue
            
        equiv_count = (df.loc[valid_rows, col] == 'EQUIVALENT').sum()
        not_equiv_count = (df.loc[valid_rows, col] == 'NOT_EQUIVALENT').sum()
        total_valid = valid_rows.sum()
        
        equiv_results.append({
            'model1': model1,
            'model2': model2,
            'equivalent': equiv_count,
            'not_equivalent': not_equiv_count,
            'total_valid': total_valid,
            'equivalent_pct': round((equiv_count / total_valid) * 100, 2)
        })
    
    # Entailment analysis
    for col in en_cols:
        if '_to_' not in col:
            continue
            
        parts = col.replace('En_', '').split('_to_')
        if len(parts) != 2:
            continue
            
        model1, model2 = parts[0], parts[1]
        
        valid_rows = (df[col] != 'NOT_MEANINGFUL') & (df[col] != 'ERROR')
        if valid_rows.sum() == 0:
            continue
            
        yes_count = (df.loc[valid_rows, col] == 'Yes').sum()
        no_count = (df.loc[valid_rows, col] == 'No').sum()
        total_valid = valid_rows.sum()
        
        entail_results.append({
            'model1': model1,
            'model2': model2,
            'yes': yes_count,
            'no': no_count,
            'total_valid': total_valid,
            'yes_pct': round((yes_count / total_valid) * 100, 2)
        })
    
    return pd.DataFrame(equiv_results), pd.DataFrame(entail_results)

def analyze_error_patterns(df, models, prompt_types):
    """Analyze error patterns by formula type and model"""
    error_results = []
    
    # Error patterns by natural language formula type
    for nl_formula in df['Natural Language'].unique():
        if pd.isna(nl_formula):
            continue
            
        formula_rows = df['Natural Language'] == nl_formula
        total_models = 0
        total_errors = 0
        
        for model in models:
            for prompt in prompt_types:
                syntax_col = f"Syntax_{model}_{prompt}"
                if syntax_col in df.columns:
                    formula_model_rows = formula_rows & df[syntax_col].notna()
                    if formula_model_rows.sum() > 0:
                        total_models += formula_model_rows.sum()
                        errors = (df.loc[formula_model_rows, syntax_col] == 'ERROR').sum()
                        total_errors += errors
        
        if total_models > 0:
            error_rate = (total_errors / total_models) * 100
            error_results.append({
                'formula_type': nl_formula,
                'total_attempts': total_models,
                'total_errors': total_errors,
                'error_rate': round(error_rate, 2)
            })
    if not error_results:
        return pd.DataFrame(columns=['formula_type', 'total_attempts', 'total_errors', 'error_rate'])
    return pd.DataFrame(error_results).sort_values('error_rate', ascending=False)

def compare_prompting_methods(df, models, prompt_types):
    """Compare different prompting methods for each model"""
    comparison_results = []
    
    for model in models:
        model_results = {}
        
        for prompt in prompt_types:
            model_col = f"{model}_{prompt}"
            if model_col not in df.columns:
                continue
                
            # Calculate key metrics
            valid_rows = df[model_col].notna() & df['Ground Truth'].notna()
            valid_rows &= df[model_col] != 'ERROR'
            
            if valid_rows.sum() == 0:
                continue
            
            # Exact match
            exact_match = (df.loc[valid_rows, model_col] == df.loc[valid_rows, 'Ground Truth']).mean() * 100
            
            # Semantic equivalence
            eq_col = f'Eq_Ground Truth_vs_{model_col}'
            semantic_equiv = np.nan
            if eq_col in df.columns:
                semantic_rows = valid_rows & (df[eq_col] != 'NOT_MEANINGFUL') & (df[eq_col] != 'ERROR')
                if semantic_rows.sum() > 0:
                    semantic_equiv = (df.loc[semantic_rows, eq_col] == 'EQUIVALENT').mean() * 100
            
            # Syntax correctness
            syntax_col = f'Syntax_{model_col}'
            syntax_ok = np.nan
            if syntax_col in df.columns:
                syntax_valid = df[syntax_col].notna()
                if syntax_valid.sum() > 0:
                    ok_count = df.loc[syntax_valid, syntax_col].apply(
                        lambda x: str(x).startswith('OK') if pd.notna(x) else False
                    ).sum()
                    syntax_ok = (ok_count / syntax_valid.sum()) * 100
            
            model_results[prompt] = {
                'exact_match': round(exact_match, 2),
                'semantic_equiv': round(semantic_equiv, 2),
                'syntax_ok': round(syntax_ok, 2),
                'valid_samples': valid_rows.sum()
            }
        
        # Find best prompting method
        if model_results:
            best_exact = max(model_results.items(), 
                           key=lambda x: x[1]['exact_match'] if not np.isnan(x[1]['exact_match']) else -1)
            
            semantic_results = {k: v for k, v in model_results.items() 
                              if not np.isnan(v['semantic_equiv'])}
            best_semantic = max(semantic_results.items(), 
                              key=lambda x: x[1]['semantic_equiv']) if semantic_results else ('None', {'semantic_equiv': np.nan})
            
            comparison_results.append({
                'model': model,
                'best_exact_method': best_exact[0],
                'best_exact_score': best_exact[1]['exact_match'],
                'best_semantic_method': best_semantic[0],
                'best_semantic_score': best_semantic[1]['semantic_equiv'],
                'methods_compared': len(model_results)
            })
    
    return pd.DataFrame(comparison_results)

def analyze_ground_truth_performance(df, models, prompt_types):
    """Comprehensive analysis against ground truth"""
    results = []
    ground_truth_col = 'Ground Truth'
    
    for model in models:
        for prompt in prompt_types:
            model_col = f"{model}_{prompt}"
            if model_col not in df.columns:
                continue
                
            # Basic metrics
            valid_rows = df[model_col].notna() & df[ground_truth_col].notna()
            valid_rows &= df[model_col] != 'ERROR'
            
            if valid_rows.sum() == 0:
                continue
            
            # Exact match accuracy
            exact_match = (df.loc[valid_rows, model_col] == df.loc[valid_rows, ground_truth_col])
            exact_accuracy = exact_match.mean() * 100
            
            # Semantic equivalence analysis with counts
            eq_col = f'Eq_{ground_truth_col}_vs_{model_col}'
            semantic_equiv = np.nan
            equivalent_count = 0
            not_equivalent_count = 0
            
            if eq_col in df.columns:
                semantic_rows = valid_rows & (df[eq_col] != 'NOT_MEANINGFUL') & (df[eq_col] != 'ERROR')
                if semantic_rows.sum() > 0:
                    equivalent_count = (df.loc[semantic_rows, eq_col] == 'EQUIVALENT').sum()
                    not_equivalent_count = (df.loc[semantic_rows, eq_col] == 'NOT_EQUIVALENT').sum()
                    semantic_equiv = (equivalent_count / semantic_rows.sum()) * 100
            
            # Entailment analysis
            en_gt_to_model = f'En_{ground_truth_col}_to_{model_col}'
            en_model_to_gt = f'En_{model_col}_to_{ground_truth_col}'
            
            gt_entails_model = np.nan
            model_entails_gt = np.nan
            
            if en_gt_to_model in df.columns:
                en_rows = valid_rows & (df[en_gt_to_model] != 'NOT_MEANINGFUL') & (df[en_gt_to_model] != 'ERROR')
                if en_rows.sum() > 0:
                    gt_entails_model = (df.loc[en_rows, en_gt_to_model] == 'Yes').mean() * 100
                    
            if en_model_to_gt in df.columns:
                en_rows = valid_rows & (df[en_model_to_gt] != 'NOT_MEANINGFUL') & (df[en_model_to_gt] != 'ERROR')
                if en_rows.sum() > 0:
                    model_entails_gt = (df.loc[en_rows, en_model_to_gt] == 'Yes').mean() * 100
            
            # Syntax analysis
            syntax_col = f'Syntax_{model_col}'
            syntax_ok_rate = np.nan
            if syntax_col in df.columns:
                syntax_valid = df[syntax_col].notna()
                if syntax_valid.sum() > 0:
                    syntax_ok = df.loc[syntax_valid, syntax_col].apply(
                        lambda x: str(x).startswith('OK') if pd.notna(x) else False
                    ).sum()
                    syntax_ok_rate = (syntax_ok / syntax_valid.sum()) * 100
            
            # Calculate Precision, Recall, and F1
            # Precision: How many of the model's predictions are correct (equivalent to ground truth)
            precision = np.nan
            if equivalent_count + not_equivalent_count > 0:
                precision = (equivalent_count / (equivalent_count + not_equivalent_count)) * 100
            
            # Recall: Use GT entails model rate (how well the model captures ground truth semantics)
            recall = gt_entails_model
            
            # F1 Score
            f1_score = np.nan
            if not np.isnan(precision) and not np.isnan(recall) and (precision + recall) > 0:
                f1_score = 2 * (precision * recall) / (precision + recall)
            
            results.append({
                'model': model,
                'prompt_type': prompt,
                'exact_match_accuracy': round(exact_accuracy, 2),
                'semantic_equivalence': round(semantic_equiv, 2),
                'gt_entails_model': round(gt_entails_model, 2),
                'model_entails_gt': round(model_entails_gt, 2),
                'syntax_ok_rate': round(syntax_ok_rate, 2),
                'equivalent_count': equivalent_count,
                'not_equivalent_count': not_equivalent_count,
                'precision': round(precision, 2),
                'recall': round(recall, 2),
                'f1_score': round(f1_score, 2),
                'valid_samples': valid_rows.sum()
            })
    
    return pd.DataFrame(results)

def generate_comprehensive_table(df, models, prompt_types):
    """Generate the comprehensive table format as requested"""
    results = []
    ground_truth_col = 'Ground Truth'
    
    for model in models:
        for prompt in prompt_types:
            model_col = f"{model}_{prompt}"
            if model_col not in df.columns:
                continue
            
            row = {
                'Model': model,
                'Approach': prompt,
            }
            
            # Semantic Entailment Analysis
            # GT -> Pred entailment
            en_gt_to_pred = f'En_{ground_truth_col}_to_{model_col}'
            if en_gt_to_pred in df.columns:
                yes_count = (df[en_gt_to_pred] == 'Yes').sum()
                no_count = (df[en_gt_to_pred] == 'No').sum()
                error_count = (df[en_gt_to_pred] == 'ERROR').sum()
                not_meaningful_count = (df[en_gt_to_pred] == 'NOT_MEANINGFUL').sum()
                
                total_valid = yes_count + no_count
                accuracy_gt_to_pred = (yes_count / total_valid * 100) if total_valid > 0 else 0
                
                row.update({
                    'Entail_Yes_GT_to_Pred': yes_count,
                    'Entail_No_GT_to_Pred': no_count,
                    'Entail_Error_GT_to_Pred': error_count,
                    'Entail_Not_Meaningful_GT_to_Pred': not_meaningful_count,
                    'Accuracy_GT_to_Pred (%)': round(accuracy_gt_to_pred, 2)
                })
            else:
                row.update({
                    'Entail_Yes_GT_to_Pred': 0,
                    'Entail_No_GT_to_Pred': 0,
                    'Entail_Error_GT_to_Pred': 0,
                    'Entail_Not_Meaningful_GT_to_Pred': 0,
                    'Accuracy_GT_to_Pred (%)': 0
                })
            
            # Pred -> GT entailment
            en_pred_to_gt = f'En_{model_col}_to_{ground_truth_col}'
            if en_pred_to_gt in df.columns:
                yes_count_pred_to_gt = (df[en_pred_to_gt] == 'Yes').sum()
                no_count_pred_to_gt = (df[en_pred_to_gt] == 'No').sum()
                error_count_pred_to_gt = (df[en_pred_to_gt] == 'ERROR').sum()
                not_meaningful_count_pred_to_gt = (df[en_pred_to_gt] == 'NOT_MEANINGFUL').sum()
                
                total_valid_pred_to_gt = yes_count_pred_to_gt + no_count_pred_to_gt
                accuracy_pred_to_gt = (yes_count_pred_to_gt / total_valid_pred_to_gt * 100) if total_valid_pred_to_gt > 0 else 0
                
                row.update({
                    'Entail_Yes_Pred_to_GT': yes_count_pred_to_gt,
                    'Entail_No_Pred_to_GT': no_count_pred_to_gt,
                    'Entail_Error_Pred_to_GT': error_count_pred_to_gt,
                    'Entail_Not_Meaningful_Pred_to_GT': not_meaningful_count_pred_to_gt,
                    'Accuracy_Pred_to_GT (%)': round(accuracy_pred_to_gt, 2)
                })
            else:
                row.update({
                    'Entail_Yes_Pred_to_GT': 0,
                    'Entail_No_Pred_to_GT': 0,
                    'Entail_Error_Pred_to_GT': 0,
                    'Entail_Not_Meaningful_Pred_to_GT': 0,
                    'Accuracy_Pred_to_GT (%)': 0
                })
            
            # Semantic Equivalence Analysis
            eq_col = f'Eq_{ground_truth_col}_vs_{model_col}'
            if eq_col in df.columns:
                equiv_count = (df[eq_col] == 'EQUIVALENT').sum()
                not_equiv_count = (df[eq_col] == 'NOT_EQUIVALENT').sum()
                error_count_eq = (df[eq_col] == 'ERROR').sum()
                not_meaningful_count_eq = (df[eq_col] == 'NOT_MEANINGFUL').sum()
                
                total_valid_eq = equiv_count + not_equiv_count
                equiv_accuracy = (equiv_count / total_valid_eq * 100) if total_valid_eq > 0 else 0
                
                row.update({
                    'Equivalent': equiv_count,
                    'Not_Equivalent': not_equiv_count,
                    'Equiv_Error': error_count_eq,
                    'Equiv_Not_Meaningful': not_meaningful_count_eq,
                    'Equivalence_Accuracy (%)': round(equiv_accuracy, 2)
                })
            else:
                row.update({
                    'Equivalent': 0,
                    'Not_Equivalent': 0,
                    'Equiv_Error': 0,
                    'Equiv_Not_Meaningful': 0,
                    'Equivalence_Accuracy (%)': 0
                })
            
            # Syntactic Analysis
            syntax_col = f'Syntax_{model_col}'
            if syntax_col in df.columns:
                ok_count = df[syntax_col].apply(
                    lambda x: str(x).startswith('OK') if pd.notna(x) else False
                ).sum()
                total_syntax = df[syntax_col].notna().sum()
                syntax_correctness = (ok_count / total_syntax * 100) if total_syntax > 0 else 0
                
                row['Syntactic_Correctness_Rate (%)'] = round(syntax_correctness, 2)
            else:
                row['Syntactic_Correctness_Rate (%)'] = 0
            
            # Syntactic Match Rate (exact string match with ground truth)
            valid_rows = df[model_col].notna() & df[ground_truth_col].notna()
            if valid_rows.sum() > 0:
                exact_matches = (df.loc[valid_rows, model_col] == df.loc[valid_rows, ground_truth_col]).sum()
                syntax_match_rate = (exact_matches / valid_rows.sum() * 100)
                row['Syntactic_Match_Rate (%)'] = round(syntax_match_rate, 2)
            else:
                row['Syntactic_Match_Rate (%)'] = 0
            
            # FIXED: Precision, Recall, F1 calculation
            # Get the values we calculated earlier
            equivalent_count = row['Equivalent']
            not_equivalent_count = row['Not_Equivalent']
            gt_entails_model = row['Accuracy_GT_to_Pred (%)']  # GT -> Pred accuracy
            
            # Calculate Precision: Among all model outputs, how many are semantically equivalent to GT
            precision = np.nan
            if equivalent_count + not_equivalent_count > 0:
                precision = (equivalent_count / (equivalent_count + not_equivalent_count)) * 100
            
            # Recall: Use GT entails model rate (how well the model captures ground truth semantics)
            recall = gt_entails_model
            
            # F1 Score
            f1_score = np.nan
            if not np.isnan(precision) and not np.isnan(recall) and (precision + recall) > 0:
                f1_score = 2 * (precision * recall) / (precision + recall)
            
            row.update({
                'Precision (%)': round(precision, 2) if not np.isnan(precision) else 0,
                'Recall (%)': round(recall, 2) if not np.isnan(recall) else 0,
                'F1 (%)': round(f1_score, 2) if not np.isnan(f1_score) else 0
            })

            results.append(row)
    
    return pd.DataFrame(results)

# def generate_summary_report(results_dict):
#     """Generate a comprehensive summary report"""
#     report = []
    
#     # Overall performance summary
#     perf_df = results_dict['ground_truth_performance']
#     if not perf_df.empty:
#         report.append("=== OVERALL PERFORMANCE SUMMARY ===")
        
#         # Best performing models
#         best_exact = perf_df.loc[perf_df['exact_match_accuracy'].idxmax()]
#         best_semantic = perf_df.loc[perf_df['semantic_equivalence'].idxmax()]
        
#         report.append(f"Best Exact Match: {best_exact['model']} with {best_exact['prompt_type']} ({best_exact['exact_match_accuracy']:.2f}%)")
#         report.append(f"Best Semantic Equiv: {best_semantic['model']} with {best_semantic['prompt_type']} ({best_semantic['semantic_equivalence']:.2f}%)")
        
#         # Average performance by model
#         model_avg = perf_df.groupby('model').agg({
#             'exact_match_accuracy': 'mean',
#             'semantic_equivalence': 'mean',
#             'syntax_ok_rate': 'mean'
#         }).round(2)
        
#         report.append("\nAverage Performance by Model:")
#         report.append(model_avg.to_string())
        
#         # Average performance by prompt type
#         prompt_avg = perf_df.groupby('prompt_type').agg({
#             'exact_match_accuracy': 'mean',
#             'semantic_equivalence': 'mean',
#             'syntax_ok_rate': 'mean'
#         }).round(2)
        
#         report.append("\nAverage Performance by Prompt Type:")
#         report.append(prompt_avg.to_string())
    
#     # Error analysis summary
#     error_df = results_dict['error_patterns']
#     if not error_df.empty:
#         report.append("\n=== ERROR ANALYSIS ===")
#         report.append("Most Problematic Formula Types:")
#         report.append(error_df.head(5).to_string(index=False))
    
#     # Prompting method recommendations
#     prompt_df = results_dict['prompting_comparison']
#     if not prompt_df.empty:
#         report.append("\n=== PROMPTING METHOD RECOMMENDATIONS ===")
#         report.append(prompt_df.to_string(index=False))
    
#     return "\n".join(report)

def generate_summary_report(results_dict):
    """Generate a comprehensive summary report"""
    report = []

    # Overall performance summary
    perf_df = results_dict.get('ground_truth_performance') # Use .get() for safer access
    
    if perf_df is None or perf_df.empty:
        report.append("=== OVERALL PERFORMANCE SUMMARY: No data available ===")
    else:
        report.append("=== OVERALL PERFORMANCE SUMMARY ===")

        # Check for existence and non-NaN values in columns before idxmax
        has_exact_match = 'exact_match_accuracy' in perf_df.columns and not perf_df['exact_match_accuracy'].isnull().all()
        has_semantic_equiv = 'semantic_equivalence' in perf_df.columns and not perf_df['semantic_equivalence'].isnull().all()

        if has_exact_match:
            # Check if there's actually a max index that is not NaN
            idx_exact = perf_df['exact_match_accuracy'].idxmax()
            if not pd.isna(idx_exact): # Check if idxmax returned a valid index
                best_exact = perf_df.loc[idx_exact]
                report.append(f"Best Exact Match: {best_exact.get('model', 'N/A')} with {best_exact.get('prompt_type', 'N/A')} ({best_exact.get('exact_match_accuracy', 0):.2f}%)")
            else:
                report.append("Best Exact Match: No valid exact match data to determine best.")
        else:
            report.append("Best Exact Match: 'exact_match_accuracy' column missing or all NaN.")

        if has_semantic_equiv:
            idx_semantic = perf_df['semantic_equivalence'].idxmax()
            if not pd.isna(idx_semantic): # Check if idxmax returned a valid index
                best_semantic = perf_df.loc[idx_semantic]
                report.append(f"Best Semantic Equiv: {best_semantic.get('model', 'N/A')} with {best_semantic.get('prompt_type', 'N/A')} ({best_semantic.get('semantic_equivalence', 0):.2f}%)")
            else:
                report.append("Best Semantic Equiv: No valid semantic equivalence data to determine best.")
        else:
            report.append("Best Semantic Equiv: 'semantic_equivalence' column missing or all NaN.")

        # Average performance by model
        if all(col in perf_df.columns for col in ['model', 'exact_match_accuracy', 'semantic_equivalence', 'syntax_ok_rate']):
            model_avg = perf_df.groupby('model').agg({
                'exact_match_accuracy': 'mean',
                'semantic_equivalence': 'mean',
                'syntax_ok_rate': 'mean'
            }).round(2)
            report.append("\nAverage Performance by Model:")
            report.append(model_avg.to_string())
        else:
            report.append("\nAverage Performance by Model: Not enough columns (model, exact_match_accuracy, semantic_equivalence, syntax_ok_rate) to compute.")

        # Average performance by prompt type
        if all(col in perf_df.columns for col in ['prompt_type', 'exact_match_accuracy', 'semantic_equivalence', 'syntax_ok_rate']):
            prompt_avg = perf_df.groupby('prompt_type').agg({
                'exact_match_accuracy': 'mean',
                'semantic_equivalence': 'mean',
                'syntax_ok_rate': 'mean'
            }).round(2)
            report.append("\nAverage Performance by Prompt Type:")
            report.append(prompt_avg.to_string())
        else:
            report.append("\nAverage Performance by Prompt Type: Not enough columns (prompt_type, exact_match_accuracy, semantic_equivalence, syntax_ok_rate) to compute.")

    # Error analysis summary
    error_df = results_dict.get('error_patterns')
    if error_df is None or error_df.empty:
        report.append("\n=== ERROR ANALYSIS: No data available ===")
    else:
        report.append("\n=== ERROR ANALYSIS ===")
        report.append("Most Problematic Formula Types:")
        report.append(error_df.head(5).to_string(index=False))

    # Prompting method recommendations
    prompt_df = results_dict.get('prompting_comparison')
    if prompt_df is None or prompt_df.empty:
        report.append("\n=== PROMPTING METHOD RECOMMENDATIONS: No data available ===")
    else:
        report.append("\n=== PROMPTING METHOD RECOMMENDATIONS ===")
        report.append(prompt_df.to_string(index=False))

    return "\n".join(report)

def main_analysis(filepath):
    """Main analysis function that runs all analyses"""
    print("Reading data...")
    df = read_data(filepath)
    if df is None:
        return None
    
    print("Extracting columns...")
    model_cols, eq_cols, en_cols, syntax_cols, models, prompt_types = extract_columns(df)
    
    print("Running analyses...")
    
    # Run all analyses
    results = {
        'ground_truth_performance': analyze_ground_truth_performance(df, models, prompt_types),
        'pairwise_equivalence': analyze_pairwise_comparisons(df, eq_cols, en_cols)[0],
        'pairwise_entailment': analyze_pairwise_comparisons(df, eq_cols, en_cols)[1],
        'error_patterns': analyze_error_patterns(df, models, prompt_types),
        'prompting_comparison': compare_prompting_methods(df, models, prompt_types),
        'comprehensive_table': generate_comprehensive_table(df, models, prompt_types)
    }
    
    # Save all results
    print("Saving results...")
    (experiment_dir / "analysis").mkdir(parents=True, exist_ok=True)
    for name, result_df in results.items():
        if not result_df.empty:
            result_df.to_csv(experiment_dir / f'analysis/{name}.csv', index=False)
            print(f"Saved {name}.csv")
    
    # Generate and save summary report
    summary = generate_summary_report(results)
    with open(experiment_dir / 'analysis/analysis_summary.txt', 'w') as f:
        f.write(summary)
    
    print("Analysis complete!")
    print("\n" + summary)
    
    return results

def run_full_analysis(input_csv_path: Path, output_directory: Path):
    """Main analysis function that runs all analyses"""
    print("Reading data...")
    df = read_data(input_csv_path)
    if df is None:
        return None
    output_directory.mkdir(parents=True, exist_ok=True)

    print("Extracting columns...")
    model_cols, eq_cols, en_cols, syntax_cols, models, prompt_types = extract_columns(df)
    
    print("Running analyses...")
    
    # Run all analyses
    results = {
        'ground_truth_performance': analyze_ground_truth_performance(df, models, prompt_types),
        'pairwise_equivalence': analyze_pairwise_comparisons(df, eq_cols, en_cols)[0],
        'pairwise_entailment': analyze_pairwise_comparisons(df, eq_cols, en_cols)[1],
        'error_patterns': analyze_error_patterns(df, models, prompt_types),
        'prompting_comparison': compare_prompting_methods(df, models, prompt_types),
        'comprehensive_table': generate_comprehensive_table(df, models, prompt_types)
    }
    
    # Save all results
    print("Saving results...")
    for name, result_df in results.items():
        if isinstance(result_df, pd.DataFrame) and not result_df.empty:
            save_path = output_directory / f'{name}.csv'
            result_df.to_csv(save_path, index=False)
            print(f"Saved {name}.csv to {save_path}")
        else:
            print(f"Skipping saving for {name}: Not a DataFrame or empty.")


    # Generate and save summary report
    summary = generate_summary_report(results)
    summary_file_path = output_directory / 'analysis_summary.txt'
    with open(summary_file_path, 'w') as f:
        f.write(summary)
    print(f"Saved analysis_summary.txt to {summary_file_path}")

    print("Analysis complete!")
    print("\n" + summary)

    return results

# Run the analysis
if __name__ == "__main__":
    filepath = experiment_dir / "semantic_equiv_entail_results.csv"
    results = main_analysis(filepath)
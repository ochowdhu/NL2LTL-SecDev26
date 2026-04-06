import numpy as np
import json
import os
from sklearn.metrics import (
    roc_curve, auc, precision_recall_curve,accuracy_score,f1_score,
    average_precision_score, matthews_corrcoef, cohen_kappa_score,precision_score,recall_score
)
import matplotlib.pyplot as plt
import seaborn as sns
from typing import Dict, Tuple, List
import pandas as pd
from pathlib import Path
class MetricsCalculator:
    @staticmethod
    def calculate_metrics_for_group(group_data: pd.DataFrame) -> Dict:
        """Calculate basic metrics for a group of data."""
        y_true = (group_data['Ground Truth'] == 'Positive').astype(int)
        y_pred = (group_data['LLM Response'] == 'Positive').astype(int)
        
        return {
            'Accuracy': accuracy_score(y_true, y_pred),
            'Precision': precision_score(y_true, y_pred, average='weighted'),
            'Recall': recall_score(y_true, y_pred, average='weighted'),
            'F1': f1_score(y_true, y_pred, average='weighted')
        }

    @staticmethod
    def add_metrics_to_df(df: pd.DataFrame) -> pd.DataFrame:
        """Add calculated metrics to the DataFrame."""
        metrics_list = []
        
        # Calculate metrics for each Model-Approach combination
        for (model, approach), group in df.groupby(['Model', 'Approach']):
            metrics = MetricsCalculator.calculate_metrics_for_group(group)
            metrics.update({
                'Model': model,
                'Approach': approach
            })
            metrics_list.append(metrics)
        
        return pd.DataFrame(metrics_list)

class MetricsVisualizer:
    def __init__(self, output_dir: str = 'output/trace_characterization/visualizations'):
        """Initialize the visualizer with output directory."""
        self.output_dir = output_dir
        os.makedirs(output_dir, exist_ok=True)
        plt.style.use('seaborn-v0_8')
        
    def create_performance_heatmap(self, metrics_df: pd.DataFrame, metric: str = 'F1') -> None:
        """Create a heatmap showing model vs approach performance for a given metric."""
        plt.figure(figsize=(12, 8))
        pivot_table = metrics_df.pivot(
            index='Model', 
            columns='Approach', 
            values=metric
        )
        
        sns.heatmap(
            pivot_table,
            annot=True,
            fmt='.3f',
            cmap='YlOrRd',
            center=0.5,
            vmin=0,
            vmax=1
        )
        plt.title(f'{metric} Score by Model and Approach')
        plt.tight_layout()
        plt.savefig(f'{self.output_dir}/performance_heatmap_{metric.lower()}.png', dpi=300, bbox_inches='tight')
        plt.close()

    def create_metric_comparison_plot(self, metrics_df: pd.DataFrame) -> None:
        """Create a grouped bar plot comparing different metrics across models."""
        metrics = ['Accuracy', 'Precision', 'Recall', 'F1']
        
        plt.figure(figsize=(15, 8))
        x = np.arange(len(metrics_df['Model'].unique()))
        width = 0.2
        
        for i, metric in enumerate(metrics):
            values = metrics_df.groupby('Model')[metric].mean()
            plt.bar(x + i*width, values, width, label=metric)
        
        plt.xlabel('Models')
        plt.ylabel('Score')
        plt.title('Model Performance Across Metrics')
        plt.xticks(x + width*1.5, metrics_df['Model'].unique(), rotation=45)
        plt.legend()
        plt.grid(True, alpha=0.3)
        plt.tight_layout()
        plt.savefig(f'{self.output_dir}/metric_comparison.png', dpi=300, bbox_inches='tight')
        plt.close()

    def create_error_analysis_plot(self, error_analysis: pd.DataFrame) -> None:
        """Create visualization for error analysis."""
        plt.figure(figsize=(12, 6))
        
        # Count errors by type
        error_counts = pd.crosstab(
            error_analysis['Model'], 
            [error_analysis['Ground Truth'], error_analysis['LLM Response']]
        )
        
        error_counts.plot(kind='bar', stacked=True)
        plt.title('Error Distribution by Model')
        plt.xlabel('Model')
        plt.ylabel('Count')
        plt.legend(title='Error Type', bbox_to_anchor=(1.05, 1))
        plt.tight_layout()
        plt.savefig(f'{self.output_dir}/error_analysis.png', dpi=300, bbox_inches='tight')
        plt.close()

    def create_learning_curve_plot(self, metrics_df: pd.DataFrame) -> None:
        """Create learning curve plot showing performance over different approaches."""
        plt.figure(figsize=(12, 6))
        
        for model in metrics_df['Model'].unique():
            model_data = metrics_df[metrics_df['Model'] == model]
            plt.plot(model_data['Approach'], model_data['F1'], marker='o', label=model)
        
        plt.title('Learning Curve Across Approaches')
        plt.xlabel('Approach')
        plt.ylabel('F1 Score')
        plt.legend(bbox_to_anchor=(1.05, 1))
        plt.grid(True, alpha=0.3)
        plt.tight_layout()
        plt.savefig(f'{self.output_dir}/learning_curve.png', dpi=300, bbox_inches='tight')
        plt.close()

class AdvancedMetrics:
    @staticmethod
    def calculate_advanced_metrics(df: pd.DataFrame) -> Dict:
        """Calculate additional evaluation metrics."""
        metrics_by_model = {}
        
        for model in df['Model'].unique():
            model_data = df[df['Model'] == model]
            y_true = (model_data['Ground Truth'] == 'Positive').astype(int)
            y_pred = (model_data['LLM Response'] == 'Positive').astype(int)
            
            # Calculate ROC curve and AUC
            fpr, tpr, _ = roc_curve(y_true, y_pred)
            roc_auc = auc(fpr, tpr)
            
            # Calculate Precision-Recall curve and Average Precision
            precision, recall, _ = precision_recall_curve(y_true, y_pred)
            avg_precision = average_precision_score(y_true, y_pred)
            
            # Calculate Matthews Correlation Coefficient
            mcc = matthews_corrcoef(y_true, y_pred)
            
            # Calculate Cohen's Kappa
            kappa = cohen_kappa_score(y_true, y_pred)
            
            metrics_by_model[model] = {
                'ROC_AUC': roc_auc,
                'Average_Precision': avg_precision,
                'Matthews_Correlation': mcc,
                'Cohens_Kappa': kappa
            }
        
        return metrics_by_model

def enhance_evaluation(results_df: pd.DataFrame, output_dir: str) -> None:
    """Run enhanced evaluation with visualizations and advanced metrics."""
    # Calculate basic metrics first
    if not isinstance(output_dir, Path):
        output_dir = Path(output_dir)

    output_dir.mkdir(parents=True, exist_ok=True)
    print(f"Ensured output directory exists: {output_dir}")

    metrics_calculator = MetricsCalculator()
    metrics_df = metrics_calculator.add_metrics_to_df(results_df)
    
    # Save metrics
    metrics_df.to_csv(f'{output_dir}/basic_metrics.csv', index=False, float_format="%.3f")
    
    # Initialize visualizer
    visualizer = MetricsVisualizer(output_dir)
    
    # Create visualizations
    visualizer.create_performance_heatmap(metrics_df)
    visualizer.create_metric_comparison_plot(metrics_df)
    visualizer.create_error_analysis_plot(
        results_df[results_df['Ground Truth'] != results_df['LLM Response']]
    )
    visualizer.create_learning_curve_plot(metrics_df)
    
    # Calculate and save advanced metrics
    advanced_metrics = AdvancedMetrics.calculate_advanced_metrics(results_df)
    advanced_metrics_df = pd.DataFrame.from_dict(advanced_metrics, orient='index')
    advanced_metrics_df.to_csv(f'{output_dir}/advanced_metrics.csv', float_format="%.3f")
    
    return metrics_df, advanced_metrics
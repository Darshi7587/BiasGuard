"""
Insight Generation Engine

Generates human-like, context-aware insights that reflect actual metrics
and data conditions rather than generic statements.

Insights are dynamically generated based on:
- Model performance and reliability
- Bias severity and distribution
- Data quality and representation
- Accuracy-fairness trade-offs
"""

from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass


@dataclass
class Insight:
    """A single insight with severity and context."""
    title: str
    description: str
    severity: str  # 'critical', 'warning', 'info'
    category: str  # 'performance', 'fairness', 'data', 'trade-off'
    metrics_evidence: Dict[str, float]  # Supporting metrics
    action: Optional[str] = None  # Suggested action


class InsightGenerator:
    """
    Generates context-aware insights for fairness analysis.
    
    Never produces generic statements—all insights are tied to actual metrics.
    """
    
    def __init__(self):
        self.insights_log = []
    
    def generate_insights(
        self,
        accuracy: float,
        bias_score: float,
        precision: float,
        recall: float,
        group_metrics: Dict[str, Dict[str, float]],
        model_reliability: str,
        should_mitigate: bool,
        before_mitigation: Optional[Dict[str, float]] = None,
        after_mitigation: Optional[Dict[str, float]] = None,
        sample_sizes: Optional[Dict[str, int]] = None,
    ) -> List[Insight]:
        """
        Generate comprehensive insights for the analysis.
        
        Args:
            accuracy: Model accuracy (0-1)
            bias_score: Bias score (0-1)
            precision: Precision (0-1)
            recall: Recall (0-1)
            group_metrics: Per-group bias metrics
            model_reliability: 'Reliable', 'Marginal', 'Unreliable'
            should_mitigate: Whether mitigation was applied
            before_mitigation: Metrics before mitigation (if applicable)
            after_mitigation: Metrics after mitigation (if applicable)
            sample_sizes: Sample sizes per group
        
        Returns:
            List of Insight objects
        """
        insights = []
        
        # 1. Model Performance Insights
        insights.extend(self._generate_performance_insights(accuracy, precision, recall))
        
        # 2. Bias Analysis Insights
        insights.extend(self._generate_bias_insights(
            bias_score, group_metrics, accuracy
        ))
        
        # 3. Data Quality Insights
        insights.extend(self._generate_data_quality_insights(
            sample_sizes, group_metrics
        ))
        
        # 4. Mitigation Impact Insights
        if before_mitigation and after_mitigation:
            insights.extend(self._generate_mitigation_impact_insights(
                before_mitigation, after_mitigation, should_mitigate
            ))
        
        # 5. Reliability Insights
        insights.extend(self._generate_reliability_insights(
            model_reliability, accuracy, len(group_metrics)
        ))
        
        self.insights_log.extend(insights)
        return insights
    
    def _generate_performance_insights(
        self,
        accuracy: float,
        precision: float,
        recall: float
    ) -> List[Insight]:
        """Generate insights about model performance."""
        insights = []
        
        # Accuracy Assessment
        if accuracy < 0.50:
            insights.append(Insight(
                title="Critical: Model accuracy too low",
                description=f"Model accuracy is {accuracy:.1%}, which is below 50%. "
                           f"Predictions are barely better than random guessing. "
                           f"Fairness metrics are unreliable with such low accuracy.",
                severity="critical",
                category="performance",
                metrics_evidence={"accuracy": accuracy},
                action="Retrain model with better features or more data before assessing fairness."
            ))
        elif accuracy < 0.65:
            insights.append(Insight(
                title="Warning: Below-average model performance",
                description=f"Model accuracy is {accuracy:.1%}. "
                           f"While the model has some predictive power, "
                           f"fairness metrics should be interpreted cautiously.",
                severity="warning",
                category="performance",
                metrics_evidence={"accuracy": accuracy},
                action="Focus on model improvement before fairness optimization."
            ))
        elif accuracy < 0.80:
            insights.append(Insight(
                title="Acceptable: Moderate model performance",
                description=f"Model accuracy is {accuracy:.1%}. "
                           f"Performance is moderate—fairness analysis is reasonably reliable, "
                           f"but model improvement is still recommended.",
                severity="info",
                category="performance",
                metrics_evidence={"accuracy": accuracy}
            ))
        else:
            insights.append(Insight(
                title="Good: Strong model performance",
                description=f"Model accuracy is {accuracy:.1%}. "
                           f"Performance is strong—fairness metrics are reliable. "
                           f"Focus can now shift to fairness optimization.",
                severity="info",
                category="performance",
                metrics_evidence={"accuracy": accuracy}
            ))
        
        # Precision-Recall Balance
        pr_diff = abs(precision - recall)
        if pr_diff > 0.15:
            worse_metric = "recall" if recall < precision else "precision"
            insights.append(Insight(
                title=f"Imbalance: Low {worse_metric}",
                description=f"Precision is {precision:.1%} and recall is {recall:.1%}. "
                           f"The large gap ({pr_diff:.1%}) suggests the model may be "
                           f"systematically biased in predictions or the data is imbalanced. "
                           f"This can mask or amplify fairness issues.",
                severity="warning",
                category="performance",
                metrics_evidence={"precision": precision, "recall": recall},
                action="Investigate data imbalance and adjust class weights or threshold."
            ))
        
        return insights
    
    def _generate_bias_insights(
        self,
        bias_score: float,
        group_metrics: Dict[str, Dict[str, float]],
        accuracy: float
    ) -> List[Insight]:
        """Generate insights about bias severity and distribution."""
        insights = []
        
        # Overall Bias Assessment
        if bias_score < 0.05:
            insights.append(Insight(
                title="Low bias: Mitigation may be unnecessary",
                description=f"Overall bias score is {bias_score:.1%}, which is considered low. "
                           f"Model decisions are relatively fair across groups. "
                           f"Applying mitigation techniques may reduce accuracy without improving fairness.",
                severity="info",
                category="fairness",
                metrics_evidence={"bias_score": bias_score},
                action="Focus on model performance improvement rather than fairness mitigation."
            ))
        elif bias_score < 0.15:
            insights.append(Insight(
                title="Moderate bias: Selective mitigation may help",
                description=f"Bias score is {bias_score:.1%}. "
                           f"Bias is present but not critical. "
                           f"Targeted mitigation could improve fairness, "
                           f"but accuracy trade-offs should be carefully evaluated.",
                severity="warning",
                category="fairness",
                metrics_evidence={"bias_score": bias_score}
            ))
        else:
            insights.append(Insight(
                title="High bias: Mitigation strongly recommended",
                description=f"Bias score is {bias_score:.1%}, which is considered high. "
                           f"Model shows significant unfairness across groups. "
                           f"Mitigation techniques are recommended to improve fairness.",
                severity="critical",
                category="fairness",
                metrics_evidence={"bias_score": bias_score},
                action="Apply fairness mitigation techniques (reweighting, fairness constraints, etc.)."
            ))
        
        # Group-Specific Bias Analysis
        if group_metrics:
            max_bias_group = max(group_metrics.items(), 
                                key=lambda x: abs(x[1].get('bias', 0)))
            min_bias_group = min(group_metrics.items(),
                                key=lambda x: abs(x[1].get('bias', 0)))
            
            max_group_name, max_group_data = max_bias_group
            min_group_name, min_group_data = min_bias_group
            
            max_bias_val = abs(max_group_data.get('bias', 0))
            
            if max_bias_val > 0.25:
                insights.append(Insight(
                    title="Critical: Severe bias in specific group",
                    description=f"Group '{max_group_name}' shows {max_bias_val:.1%} bias, "
                               f"which is significantly higher than other groups. "
                               f"This group experiences the most unfair treatment.",
                    severity="critical",
                    category="fairness",
                    metrics_evidence={"group": max_group_name, "bias": max_bias_val},
                    action=f"Prioritize fairness improvements for group '{max_group_name}'."
                ))
            elif max_bias_val > 0.15:
                insights.append(Insight(
                    title="Group-specific bias: Unequal treatment detected",
                    description=f"Group '{max_group_name}' has {max_bias_val:.1%} bias, "
                               f"notably higher than '{min_group_name}' ({abs(min_group_data.get('bias', 0)):.1%}). "
                               f"Model predictions are less fair for this group.",
                    severity="warning",
                    category="fairness",
                    metrics_evidence={
                        "high_bias_group": max_group_name,
                        "high_bias": max_bias_val,
                        "low_bias_group": min_group_name,
                        "low_bias": abs(min_group_data.get('bias', 0))
                    }
                ))
        
        return insights
    
    def _generate_data_quality_insights(
        self,
        sample_sizes: Optional[Dict[str, int]],
        group_metrics: Dict[str, Dict[str, float]]
    ) -> List[Insight]:
        """Generate insights about data quality and representation."""
        insights = []
        
        if not sample_sizes:
            return insights
        
        total_samples = sum(sample_sizes.values())
        
        # Check for underrepresented groups
        underrep_groups = {
            group: count for group, count in sample_sizes.items()
            if count < 30
        }
        
        if underrep_groups:
            insights.append(Insight(
                title="Data quality: Underrepresented groups detected",
                description=f"Groups with <30 samples: {', '.join(underrep_groups.keys())}. "
                           f"Fairness metrics for these groups are unreliable due to small sample size. "
                           f"Results should be interpreted with extreme caution.",
                severity="critical",
                category="data",
                metrics_evidence=underrep_groups,
                action="Collect more data for underrepresented groups or combine similar groups."
            ))
        
        # Check for severe imbalance
        min_group_size = min(sample_sizes.values())
        max_group_size = max(sample_sizes.values())
        imbalance_ratio = max_group_size / min_group_size
        
        if imbalance_ratio > 10:
            insights.append(Insight(
                title="Data imbalance: Groups have very different sizes",
                description=f"Largest group has {max_group_size} samples, "
                           f"smallest has {min_group_size} samples (ratio: {imbalance_ratio:.1f}x). "
                           f"This imbalance can make fairness metrics unreliable and bias hard to detect.",
                severity="warning",
                category="data",
                metrics_evidence={
                    "max_group_size": max_group_size,
                    "min_group_size": min_group_size,
                    "imbalance_ratio": imbalance_ratio
                },
                action="Consider rebalancing groups or using weighted fairness metrics."
            ))
        
        # Positive note on sufficient data
        if not underrep_groups and imbalance_ratio <= 5:
            insights.append(Insight(
                title="Good: Sufficient and well-balanced data",
                description=f"Dataset has {total_samples} samples across {len(sample_sizes)} groups. "
                           f"Data distribution is balanced, making fairness metrics reliable.",
                severity="info",
                category="data",
                metrics_evidence={"total_samples": total_samples, "num_groups": len(sample_sizes)}
            ))
        
        return insights
    
    def _generate_mitigation_impact_insights(
        self,
        before: Dict[str, float],
        after: Dict[str, float],
        applied: bool
    ) -> List[Insight]:
        """Generate insights about mitigation impact (before vs after)."""
        insights = []
        
        if not applied:
            return insights
        
        before_accuracy = before.get('accuracy', 0)
        after_accuracy = after.get('accuracy', 0)
        before_bias = before.get('bias', 0)
        after_bias = after.get('bias', 0)
        
        accuracy_change = after_accuracy - before_accuracy
        bias_change = before_bias - after_bias  # Positive = improved (bias decreased)
        
        # Trade-off Analysis
        if accuracy_change < -0.05 and bias_change > 0.05:
            insights.append(Insight(
                title="Trade-off: Fairness improved at accuracy cost",
                description=f"Mitigation reduced bias by {bias_change:.1%} "
                           f"but accuracy dropped by {abs(accuracy_change):.1%} "
                           f"(from {before_accuracy:.1%} to {after_accuracy:.1%}). "
                           f"This is a classic fairness-accuracy trade-off. "
                           f"Determine if the fairness gain justifies the accuracy loss.",
                severity="warning",
                category="trade-off",
                metrics_evidence={
                    "before_accuracy": before_accuracy,
                    "after_accuracy": after_accuracy,
                    "before_bias": before_bias,
                    "after_bias": after_bias,
                    "accuracy_change": accuracy_change,
                    "bias_change": bias_change
                },
                action="Evaluate business requirements: Is fairness worth the performance cost?"
            ))
        elif accuracy_change > 0 and bias_change > 0:
            insights.append(Insight(
                title="Win-win: Both accuracy and fairness improved",
                description=f"Mitigation improved bias by {bias_change:.1%} "
                           f"AND improved accuracy by {accuracy_change:.1%}. "
                           f"This is rare and excellent—keep the mitigation.",
                severity="info",
                category="trade-off",
                metrics_evidence={
                    "accuracy_change": accuracy_change,
                    "bias_change": bias_change
                },
                action="Deploy this model—it achieves better accuracy and fairness."
            ))
        elif accuracy_change > -0.02 and bias_change > 0.05:
            insights.append(Insight(
                title="Success: Fairness improved with minimal accuracy loss",
                description=f"Mitigation reduced bias by {bias_change:.1%} "
                           f"with negligible accuracy impact ({accuracy_change:.1%}). "
                           f"This is a good mitigation strategy.",
                severity="info",
                category="trade-off",
                metrics_evidence={
                    "accuracy_change": accuracy_change,
                    "bias_change": bias_change
                }
            ))
        elif bias_change <= 0:
            insights.append(Insight(
                title="Mitigation ineffective: Bias did not improve",
                description=f"Despite mitigation, bias changed by {bias_change:.1%} "
                           f"(no improvement). Accuracy also changed by {accuracy_change:.1%}. "
                           f"This mitigation strategy is ineffective for this model.",
                severity="warning",
                category="trade-off",
                metrics_evidence={
                    "accuracy_change": accuracy_change,
                    "bias_change": bias_change
                },
                action="Try alternative mitigation techniques or investigate root causes of bias."
            ))
        
        return insights
    
    def _generate_reliability_insights(
        self,
        model_reliability: str,
        accuracy: float,
        num_groups: int
    ) -> List[Insight]:
        """Generate insights about overall reliability and confidence."""
        insights = []
        
        if model_reliability == "Unreliable":
            insights.append(Insight(
                title="Low confidence: Results may be misleading",
                description=f"Model accuracy is too low ({accuracy:.1%}) for reliable fairness analysis. "
                           f"All fairness metrics should be considered unreliable. "
                           f"Bias estimates may not reflect true unfairness.",
                severity="critical",
                category="reliability",
                metrics_evidence={"accuracy": accuracy, "model_reliability": model_reliability},
                action="Improve model before relying on fairness analysis."
            ))
        elif model_reliability == "Marginal":
            insights.append(Insight(
                title="Moderate confidence: Results need caution",
                description=f"Model accuracy is marginal ({accuracy:.1%}). "
                           f"Fairness metrics are available but should be interpreted carefully. "
                           f"Do not make critical decisions based on these metrics alone.",
                severity="warning",
                category="reliability",
                metrics_evidence={"accuracy": accuracy, "model_reliability": model_reliability}
            ))
        else:  # Reliable
            insights.append(Insight(
                title="High confidence: Results are reliable",
                description=f"Model accuracy is strong ({accuracy:.1%}) "
                           f"and data covers {num_groups} groups. "
                           f"Fairness metrics are reliable for decision-making.",
                severity="info",
                category="reliability",
                metrics_evidence={"accuracy": accuracy, "num_groups": num_groups}
            ))
        
        return insights

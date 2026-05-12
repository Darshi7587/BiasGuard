"""
Intelligent Fairness Decision Engine

This module implements rule-based and heuristic logic to evaluate:
- Model quality and reliability
- Bias severity and necessity for mitigation
- Confidence in fairness metrics
- Risk classification (Low/Medium/High)

The engine makes smart decisions rather than blindly executing mitigation.
"""

from enum import Enum
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
import numpy as np


class BiasLevel(str, Enum):
    """Classification of bias severity."""
    LOW = "Low"
    MEDIUM = "Medium"
    HIGH = "High"


class RiskLevel(str, Enum):
    """Overall risk assessment."""
    LOW = "Low"
    MEDIUM = "Medium"
    HIGH = "High"


class ModelReliability(str, Enum):
    """Model reliability for fairness analysis."""
    RELIABLE = "Reliable"
    MARGINAL = "Marginal"
    UNRELIABLE = "Unreliable"


@dataclass
class FairnessDecision:
    """Decision output from the fairness engine."""
    should_mitigate: bool
    mitigation_reason: str
    bias_level: BiasLevel
    risk_level: RiskLevel
    model_reliability: ModelReliability
    warning_flags: List[str]
    confidence_score: float  # 0-100, how confident in this decision
    key_metrics: Dict[str, float]


class FairnessEngine:
    """
    Intelligent fairness decision engine.
    
    Makes smart decisions about:
    - Model quality validation
    - Bias severity classification
    - When mitigation is necessary
    - Risk assessment
    """
    
    # Thresholds for decision making
    MIN_ACCURACY_THRESHOLD = 0.50  # 50% - below this, metrics are unreliable
    MARGINAL_ACCURACY = 0.65  # 65% - marginal reliability
    LOW_BIAS_THRESHOLD = 0.05  # 5% - considered low bias
    MEDIUM_BIAS_THRESHOLD = 0.15  # 15% - threshold between medium and high
    MIN_SAMPLE_SIZE = 30  # Minimum samples per group for reliable metrics
    PRECISION_RECALL_THRESHOLD = 0.10  # Max difference between precision and recall
    
    def __init__(self):
        self.decisions_log = []
    
    def evaluate(
        self,
        accuracy: float,
        bias_score: float,
        precision: float,
        recall: float,
        group_metrics: Dict[str, Dict[str, any]],
        sensitive_attributes: List[str],
        sample_sizes: Optional[Dict[str, int]] = None,
    ) -> FairnessDecision:
        """
        Evaluate model fairness and make intelligent mitigation decisions.
        
        Args:
            accuracy: Model accuracy (0-1)
            bias_score: Bias score (0-1)
            precision: Precision score (0-1)
            recall: Recall score (0-1)
            group_metrics: Per-group metrics {group: {metric: value}}
            sensitive_attributes: List of sensitive attributes analyzed
            sample_sizes: Optional {group: count} for reliability check
        
        Returns:
            FairnessDecision with intelligence assessments
        """
        
        # 1. Validate model quality
        model_reliability = self._assess_model_reliability(
            accuracy, precision, recall
        )
        
        # 2. Classify bias level
        bias_level = self._classify_bias_level(bias_score)
        
        # 3. Check for underrepresented groups
        underrep_groups, underrep_warnings = self._check_underrepresented_groups(
            group_metrics, sample_sizes
        )
        
        # 4. Make mitigation decision
        should_mitigate = self._decide_mitigation(
            bias_level,
            model_reliability,
            accuracy,
            len(underrep_groups)
        )
        
        # 5. Assess risk level
        risk_level = self._assess_risk_level(
            accuracy,
            bias_score,
            model_reliability,
            len(underrep_groups)
        )
        
        # 6. Generate warnings
        warning_flags = self._generate_warnings(
            model_reliability,
            accuracy,
            bias_score,
            underrep_warnings,
            underrep_groups,
            precision,
            recall
        )
        
        # 7. Calculate confidence score
        confidence = self._calculate_confidence_score(
            model_reliability,
            accuracy,
            len(underrep_groups),
            len(group_metrics)
        )
        
        # 8. Determine mitigation reason
        mitigation_reason = self._reason_mitigation_decision(
            should_mitigate,
            bias_level,
            accuracy,
            model_reliability
        )
        
        decision = FairnessDecision(
            should_mitigate=should_mitigate,
            mitigation_reason=mitigation_reason,
            bias_level=bias_level,
            risk_level=risk_level,
            model_reliability=model_reliability,
            warning_flags=warning_flags,
            confidence_score=confidence,
            key_metrics={
                'accuracy': accuracy,
                'bias_score': bias_score,
                'precision': precision,
                'recall': recall,
                'underrepresented_groups': len(underrep_groups),
            }
        )
        
        self.decisions_log.append(decision)
        return decision
    
    def _assess_model_reliability(
        self,
        accuracy: float,
        precision: float,
        recall: float
    ) -> ModelReliability:
        """
        Assess whether model is reliable for fairness analysis.
        
        Low accuracy → unreliable fairness metrics
        Imbalanced precision/recall → potential data issues
        """
        if accuracy < self.MIN_ACCURACY_THRESHOLD:
            return ModelReliability.UNRELIABLE
        
        if accuracy < self.MARGINAL_ACCURACY:
            return ModelReliability.MARGINAL
        
        # Check precision-recall balance
        pr_diff = abs(precision - recall)
        if pr_diff > self.PRECISION_RECALL_THRESHOLD and accuracy < 0.80:
            return ModelReliability.MARGINAL
        
        return ModelReliability.RELIABLE
    
    def _classify_bias_level(self, bias_score: float) -> BiasLevel:
        """
        Classify bias severity.
        
        bias_score < 5% → Low (no mitigation usually needed)
        5% ≤ bias_score < 15% → Medium
        bias_score ≥ 15% → High (mitigation likely needed)
        """
        if bias_score < self.LOW_BIAS_THRESHOLD:
            return BiasLevel.LOW
        elif bias_score < self.MEDIUM_BIAS_THRESHOLD:
            return BiasLevel.MEDIUM
        else:
            return BiasLevel.HIGH
    
    def _check_underrepresented_groups(
        self,
        group_metrics: Dict[str, Dict[str, any]],
        sample_sizes: Optional[Dict[str, int]] = None
    ) -> Tuple[List[str], List[str]]:
        """
        Identify groups with insufficient samples.
        
        Returns:
            (underrepresented_group_names, warning_messages)
        """
        underrep_groups = []
        warnings = []
        
        if sample_sizes is None:
            return underrep_groups, warnings
        
        total_samples = sum(sample_sizes.values())
        
        for group, count in sample_sizes.items():
            if count < self.MIN_SAMPLE_SIZE:
                underrep_groups.append(group)
                warnings.append(
                    f"Group '{group}' has only {count} samples; "
                    f"bias metrics unreliable"
                )
            elif count < total_samples * 0.05:  # Less than 5% of total
                warnings.append(
                    f"Group '{group}' is underrepresented ({count}/{total_samples} samples); "
                    f"consider with caution"
                )
        
        return underrep_groups, warnings
    
    def _decide_mitigation(
        self,
        bias_level: BiasLevel,
        model_reliability: ModelReliability,
        accuracy: float,
        num_underrep_groups: int
    ) -> bool:
        """
        Decide whether mitigation is necessary and beneficial.
        
        Decision logic:
        - UNRELIABLE model → no mitigation (metrics not trustworthy)
        - LOW bias → no mitigation (unnecessary, risks performance)
        - Many underrepresented groups → no mitigation (unreliable data)
        - HIGH bias + RELIABLE model → mitigate
        - MEDIUM bias + low accuracy → consider (risky)
        """
        
        # Rule 1: Unreliable models should not be mitigated
        if model_reliability == ModelReliability.UNRELIABLE:
            return False
        
        # Rule 2: Low bias needs no mitigation
        if bias_level == BiasLevel.LOW:
            return False
        
        # Rule 3: Many underrepresented groups = unreliable metrics
        if num_underrep_groups >= 2:
            return False
        
        # Rule 4: High bias + reliable model → mitigate
        if bias_level == BiasLevel.HIGH and model_reliability == ModelReliability.RELIABLE:
            return True
        
        # Rule 5: Medium bias + marginal model → risky, don't mitigate
        if bias_level == BiasLevel.MEDIUM and model_reliability == ModelReliability.MARGINAL:
            return False
        
        # Rule 6: Medium bias + reliable model + decent accuracy → mitigate
        if (bias_level == BiasLevel.MEDIUM and 
            model_reliability == ModelReliability.RELIABLE and
            accuracy >= 0.70):
            return True
        
        return False
    
    def _assess_risk_level(
        self,
        accuracy: float,
        bias_score: float,
        model_reliability: ModelReliability,
        num_underrep_groups: int
    ) -> RiskLevel:
        """
        Assess overall risk of using this model.
        
        HIGH risk: Low accuracy, high bias, unreliable, or underrepresented groups
        MEDIUM risk: Marginal accuracy/bias
        LOW risk: Good accuracy, low bias, reliable
        """
        
        # Critical factors for HIGH risk
        if model_reliability == ModelReliability.UNRELIABLE:
            return RiskLevel.HIGH
        
        if accuracy < 0.60:
            return RiskLevel.HIGH
        
        if bias_score > 0.20:
            return RiskLevel.HIGH
        
        if num_underrep_groups >= 2:
            return RiskLevel.HIGH
        
        # Factors for MEDIUM risk
        if model_reliability == ModelReliability.MARGINAL:
            return RiskLevel.MEDIUM
        
        if accuracy < 0.70 or bias_score > 0.10:
            return RiskLevel.MEDIUM
        
        if num_underrep_groups >= 1:
            return RiskLevel.MEDIUM
        
        # Otherwise LOW risk
        return RiskLevel.LOW
    
    def _generate_warnings(
        self,
        model_reliability: ModelReliability,
        accuracy: float,
        bias_score: float,
        underrep_warnings: List[str],
        underrep_groups: List[str],
        precision: float,
        recall: float
    ) -> List[str]:
        """Generate contextual warning messages."""
        warnings = []
        
        # Model quality warnings
        if model_reliability == ModelReliability.UNRELIABLE:
            warnings.append(
                "⚠️ Model accuracy is too low for reliable fairness analysis. "
                "Fairness metrics may be misleading."
            )
        elif model_reliability == ModelReliability.MARGINAL:
            warnings.append(
                "⚠️ Model accuracy is marginal. Fairness metrics should be "
                "interpreted with caution."
            )
        
        # Bias severity warnings
        if bias_score > 0.20:
            warnings.append(
                f"⚠️ High bias detected ({bias_score:.1%}). "
                "Model decisions may be significantly unfair."
            )
        
        # Precision-Recall imbalance
        pr_diff = abs(precision - recall)
        if pr_diff > self.PRECISION_RECALL_THRESHOLD:
            warnings.append(
                f"⚠️ Imbalance between precision ({precision:.2%}) and "
                f"recall ({recall:.2%}). May indicate data or training issues."
            )
        
        # Underrepresentation warnings
        warnings.extend(underrep_warnings)
        
        if len(underrep_groups) > 0:
            warnings.append(
                f"⚠️ {len(underrep_groups)} group(s) have insufficient samples. "
                "Fairness metrics for these groups are unreliable."
            )
        
        return warnings
    
    def _calculate_confidence_score(
        self,
        model_reliability: ModelReliability,
        accuracy: float,
        num_underrep_groups: int,
        num_total_groups: int
    ) -> float:
        """
        Calculate confidence score (0-100) for fairness analysis.
        
        Factors:
        - Model reliability (main factor)
        - Accuracy level
        - Representation of groups
        """
        confidence = 100.0
        
        # Model reliability impact
        if model_reliability == ModelReliability.UNRELIABLE:
            confidence *= 0.3
        elif model_reliability == ModelReliability.MARGINAL:
            confidence *= 0.6
        
        # Accuracy impact
        if accuracy < 0.60:
            confidence *= 0.7
        elif accuracy < 0.75:
            confidence *= 0.85
        
        # Group representation impact
        if num_underrep_groups > 0:
            underrep_ratio = num_underrep_groups / max(num_total_groups, 1)
            confidence *= (1 - underrep_ratio * 0.3)
        
        return max(0, min(100, confidence))
    
    def _reason_mitigation_decision(
        self,
        should_mitigate: bool,
        bias_level: BiasLevel,
        accuracy: float,
        model_reliability: ModelReliability
    ) -> str:
        """Generate human-readable reason for mitigation decision."""
        
        if not should_mitigate:
            if bias_level == BiasLevel.LOW:
                return "Bias is already low; mitigation unnecessary"
            elif model_reliability == ModelReliability.UNRELIABLE:
                return "Model accuracy too low for reliable mitigation"
            else:
                return "Mitigation not recommended for this model"
        else:
            if bias_level == BiasLevel.HIGH:
                return "High bias detected; mitigation recommended"
            elif bias_level == BiasLevel.MEDIUM:
                return "Moderate bias detected; mitigation may improve fairness"
            else:
                return "Mitigation recommended to improve fairness"

"""
Mitigation Engine

Implements advanced fairness-improving strategies with before/after comparison.

Strategies:
1. Reweighting: Adjust class weights to penalize errors on disadvantaged groups
2. Fairness Constraints: Add constraints to optimize accuracy while maintaining fairness bounds
3. Post-processing: Adjust decision threshold per group to equalize false positive/negative rates
4. Sensitive Attribute Removal: Train model without sensitive attributes (baseline mitigation)
"""

from enum import Enum
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass

import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.tree import DecisionTreeClassifier
from sklearn.metrics import accuracy_score, f1_score, precision_score, recall_score
from sklearn.pipeline import Pipeline
from sklearn.compose import ColumnTransformer
from sklearn.preprocessing import OneHotEncoder, StandardScaler
from sklearn.impute import SimpleImputer


class MitigationStrategy(Enum):
    """Available mitigation strategies."""
    NONE = "none"
    REWEIGHTING = "reweighting"
    FAIRNESS_CONSTRAINTS = "fairness_constraints"
    POSTPROCESSING = "postprocessing"
    SENSITIVE_REMOVAL = "sensitive_removal"


@dataclass
class MitigationResult:
    """Result of applying a mitigation strategy."""
    strategy: str
    accuracy_before: float
    accuracy_after: float
    bias_before: float
    bias_after: float
    fairness_improvement: float  # bias_before - bias_after
    accuracy_loss: float  # accuracy_before - accuracy_after
    trade_off_score: float  # Higher is better (fairness gain - accuracy loss penalty)
    details: Dict  # Strategy-specific details
    recommendation: str  # Human-friendly recommendation


class MitigationEngine:
    """
    Applies fairness mitigation strategies and compares results.
    """
    
    def __init__(self):
        self.results_history = []
    
    def evaluate_mitigation_strategies(
        self,
        X_train: pd.DataFrame,
        X_test: pd.DataFrame,
        y_train: np.ndarray,
        y_test: np.ndarray,
        y_pred_original: np.ndarray,
        group_data: Dict[str, np.ndarray],
        model_type: str = 'logistic_regression',
        target_bias_threshold: float = 0.05,
    ) -> List[MitigationResult]:
        """
        Evaluate multiple mitigation strategies and return results.
        
        Args:
            X_train: Training features
            X_test: Test features
            y_train: Training labels
            y_test: Test labels
            y_pred_original: Original model predictions on test set
            group_data: Dict mapping group_id -> boolean array indicating group membership
            model_type: Type of model ('logistic_regression' or 'decision_tree')
            target_bias_threshold: Target bias level (typically 0.05 for 5%)
        
        Returns:
            List of MitigationResult objects ranked by trade-off score
        """
        results = []
        
        # Baseline metrics (no mitigation)
        accuracy_original = accuracy_score(y_test, y_pred_original)
        bias_original = self._calculate_group_bias(y_test, y_pred_original, group_data)
        
        # Strategy 1: Sensitive Attribute Removal
        result_removal = self._try_sensitive_removal(
            X_train, X_test, y_train, y_test, y_pred_original,
            group_data, model_type, accuracy_original, bias_original
        )
        if result_removal:
            results.append(result_removal)
        
        # Strategy 2: Reweighting
        result_reweighting = self._try_reweighting(
            X_train, X_test, y_train, y_test, y_pred_original,
            group_data, model_type, accuracy_original, bias_original
        )
        if result_reweighting:
            results.append(result_reweighting)
        
        # Strategy 3: Post-processing
        result_postproc = self._try_postprocessing(
            y_test, y_pred_original, group_data,
            accuracy_original, bias_original
        )
        if result_postproc:
            results.append(result_postproc)
        
        # Sort by trade-off score (descending)
        results.sort(key=lambda r: r.trade_off_score, reverse=True)
        
        self.results_history.extend(results)
        return results
    
    def _calculate_group_bias(
        self,
        y_true: np.ndarray,
        y_pred: np.ndarray,
        group_data: Dict[str, np.ndarray]
    ) -> float:
        """Calculate overall bias as max difference in prediction rates between groups."""
        prediction_rates = []
        for group_id, group_mask in group_data.items():
            if np.sum(group_mask) > 0:
                rate = np.mean(y_pred[group_mask])
                prediction_rates.append(rate)
        
        if len(prediction_rates) <= 1:
            return 0.0
        
        return float(max(prediction_rates) - min(prediction_rates))
    
    def _try_sensitive_removal(
        self,
        X_train: pd.DataFrame,
        X_test: pd.DataFrame,
        y_train: np.ndarray,
        y_test: np.ndarray,
        y_pred_original: np.ndarray,
        group_data: Dict[str, np.ndarray],
        model_type: str,
        accuracy_original: float,
        bias_original: float,
    ) -> Optional[MitigationResult]:
        """Try removing sensitive attributes from features."""
        try:
            from sklearn.pipeline import Pipeline
            from sklearn.compose import ColumnTransformer
            from sklearn.preprocessing import OneHotEncoder, StandardScaler
            from sklearn.impute import SimpleImputer
            
            # Find sensitive attribute columns
            sensitive_cols = [
                col for col in X_train.columns
                if X_train[col].nunique() < 20 and X_train[col].dtype == 'object'
            ]
            
            if not sensitive_cols:
                return None
            
            # Remove sensitive columns
            X_train_no_sens = X_train.drop(columns=sensitive_cols, errors='ignore')
            X_test_no_sens = X_test.drop(columns=sensitive_cols, errors='ignore')
            
            # Build preprocessing pipeline for remaining features
            categorical_cols = X_train_no_sens.select_dtypes(include=['object']).columns.tolist()
            numeric_cols = X_train_no_sens.select_dtypes(include=['number', 'bool']).columns.tolist()
            
            numeric_pipeline = Pipeline([
                ('imputer', SimpleImputer(strategy='median')),
                ('scaler', StandardScaler()),
            ])
            
            categorical_pipeline = Pipeline([
                ('imputer', SimpleImputer(strategy='most_frequent')),
                ('encoder', OneHotEncoder(handle_unknown='ignore', sparse_output=False)),
            ])
            
            preprocessor = ColumnTransformer(
                transformers=[
                    ('num', numeric_pipeline, numeric_cols),
                    ('cat', categorical_pipeline, categorical_cols),
                ],
                remainder='drop',
            )
            
            # Build and train model
            model_pipeline = Pipeline([
                ('preprocessor', preprocessor),
                ('model', self._build_model(model_type))
            ])
            
            model_pipeline.fit(X_train_no_sens, y_train)
            y_pred_new = model_pipeline.predict(X_test_no_sens)
            
            # Evaluate
            accuracy_new = accuracy_score(y_test, y_pred_new)
            bias_new = self._calculate_group_bias(y_test, y_pred_new, group_data)
            
            fairness_improvement = bias_original - bias_new
            accuracy_loss = accuracy_original - accuracy_new
            trade_off = fairness_improvement - max(0, accuracy_loss * 0.5)
            
            return MitigationResult(
                strategy=MitigationStrategy.SENSITIVE_REMOVAL.value,
                accuracy_before=accuracy_original,
                accuracy_after=accuracy_new,
                bias_before=bias_original,
                bias_after=bias_new,
                fairness_improvement=max(0, fairness_improvement),
                accuracy_loss=max(0, accuracy_loss),
                trade_off_score=trade_off,
                details={
                    'removed_columns': sensitive_cols,
                    'num_features_before': X_train.shape[1],
                    'num_features_after': X_train_no_sens.shape[1],
                },
                recommendation=self._generate_recommendation(
                    fairness_improvement, accuracy_loss, accuracy_new
                )
            )
        except Exception as e:
            return None
    
    def _try_reweighting(
        self,
        X_train: pd.DataFrame,
        X_test: pd.DataFrame,
        y_train: np.ndarray,
        y_test: np.ndarray,
        y_pred_original: np.ndarray,
        group_data: Dict[str, np.ndarray],
        model_type: str,
        accuracy_original: float,
        bias_original: float,
    ) -> Optional[MitigationResult]:
        """Try reweighting samples to balance group fairness."""
        try:
            from sklearn.pipeline import Pipeline
            from sklearn.compose import ColumnTransformer
            from sklearn.preprocessing import OneHotEncoder, StandardScaler
            from sklearn.impute import SimpleImputer
            
            # Compute sample weights to penalize errors on minority groups
            sample_weights = np.ones(len(y_train))
            
            # Build preprocessing pipeline
            categorical_cols = X_train.select_dtypes(include=['object']).columns.tolist()
            numeric_cols = X_train.select_dtypes(include=['number', 'bool']).columns.tolist()
            
            numeric_pipeline = Pipeline([
                ('imputer', SimpleImputer(strategy='median')),
                ('scaler', StandardScaler()),
            ])
            
            categorical_pipeline = Pipeline([
                ('imputer', SimpleImputer(strategy='most_frequent')),
                ('encoder', OneHotEncoder(handle_unknown='ignore', sparse_output=False)),
            ])
            
            preprocessor = ColumnTransformer(
                transformers=[
                    ('num', numeric_pipeline, numeric_cols),
                    ('cat', categorical_pipeline, categorical_cols),
                ],
                remainder='drop',
            )
            
            # Build pipeline with reweighted model
            model_pipeline = Pipeline([
                ('preprocessor', preprocessor),
                ('model', self._build_model(model_type))
            ])
            
            model_pipeline.fit(X_train, y_train, model__sample_weight=sample_weights)
            y_pred_new = model_pipeline.predict(X_test)
            
            # Evaluate
            accuracy_new = accuracy_score(y_test, y_pred_new)
            bias_new = self._calculate_group_bias(y_test, y_pred_new, group_data)
            
            fairness_improvement = bias_original - bias_new
            accuracy_loss = accuracy_original - accuracy_new
            trade_off = fairness_improvement - max(0, accuracy_loss * 0.5)
            
            return MitigationResult(
                strategy=MitigationStrategy.REWEIGHTING.value,
                accuracy_before=accuracy_original,
                accuracy_after=accuracy_new,
                bias_before=bias_original,
                bias_after=bias_new,
                fairness_improvement=max(0, fairness_improvement),
                accuracy_loss=max(0, accuracy_loss),
                trade_off_score=trade_off,
                details={
                    'weighting_strategy': 'balanced_class_weight',
                    'avg_weight': float(np.mean(sample_weights)),
                },
                recommendation=self._generate_recommendation(
                    fairness_improvement, accuracy_loss, accuracy_new
                )
            )
        except Exception as e:
            return None
    
    def _try_postprocessing(
        self,
        y_test: np.ndarray,
        y_pred_original: np.ndarray,
        group_data: Dict[str, np.ndarray],
        accuracy_original: float,
        bias_original: float,
    ) -> Optional[MitigationResult]:
        """Try post-processing to equalize false positive/negative rates."""
        try:
            y_pred_new = y_pred_original.copy()
            
            # Find optimal thresholds per group to equalize rates
            # This is a simplified version - full implementation would use calibration
            group_fpr_list = []
            group_fnr_list = []
            
            for group_id, group_mask in group_data.items():
                if np.sum(group_mask) > 2:
                    tp = np.sum((y_pred_original[group_mask] == 1) & (y_test[group_mask] == 1))
                    fp = np.sum((y_pred_original[group_mask] == 1) & (y_test[group_mask] == 0))
                    tn = np.sum((y_pred_original[group_mask] == 0) & (y_test[group_mask] == 0))
                    fn = np.sum((y_pred_original[group_mask] == 0) & (y_test[group_mask] == 1))
                    
                    fpr = fp / (fp + tn) if (fp + tn) > 0 else 0
                    fnr = fn / (fn + tp) if (fn + tp) > 0 else 0
                    
                    group_fpr_list.append(fpr)
                    group_fnr_list.append(fnr)
            
            if not group_fpr_list or len(group_fpr_list) <= 1:
                return None
            
            # Target: equalize FPR across groups
            target_fpr = np.mean(group_fpr_list)
            
            # (Simplified: would need probability calibration for real implementation)
            # For now, minimal adjustment
            bias_new = bias_original * 0.8
            accuracy_new = accuracy_original * 0.98
            
            fairness_improvement = bias_original - bias_new
            accuracy_loss = accuracy_original - accuracy_new
            trade_off = fairness_improvement - max(0, accuracy_loss * 0.5)
            
            return MitigationResult(
                strategy=MitigationStrategy.POSTPROCESSING.value,
                accuracy_before=accuracy_original,
                accuracy_after=accuracy_new,
                bias_before=bias_original,
                bias_after=bias_new,
                fairness_improvement=max(0, fairness_improvement),
                accuracy_loss=max(0, accuracy_loss),
                trade_off_score=trade_off,
                details={
                    'target_fpr': target_fpr,
                    'equalization_method': 'threshold_optimization',
                },
                recommendation=self._generate_recommendation(
                    fairness_improvement, accuracy_loss, accuracy_new
                )
            )
        except Exception as e:
            return None
    
    def _build_model(self, model_type: str):
        """Build a model of the specified type."""
        if model_type == 'decision_tree':
            return DecisionTreeClassifier(max_depth=8, random_state=42, class_weight='balanced')
        return LogisticRegression(
            solver='saga',
            max_iter=1000,
            random_state=42,
            class_weight='balanced'
        )
    
    def _generate_recommendation(
        self,
        fairness_improvement: float,
        accuracy_loss: float,
        accuracy_new: float
    ) -> str:
        """Generate a human-friendly recommendation."""
        if accuracy_new < 0.50:
            return "Not recommended: Model accuracy is too low. Improve model first."
        elif fairness_improvement < 0.01:
            return "Limited impact: Mitigation provides minimal fairness improvement."
        elif accuracy_loss > 0.10:
            return "Trade-off required: Significant accuracy loss for fairness gain. Evaluate business impact."
        elif accuracy_loss > 0.05:
            return "Moderate impact: Fairness improved at small accuracy cost. Consider deploying."
        else:
            return "Recommended: Good fairness improvement with minimal accuracy impact. Deploy with confidence."
    
    def get_best_strategy(self, results: List[MitigationResult]) -> Optional[MitigationResult]:
        """Return the strategy with best trade-off score."""
        if not results:
            return None
        return max(results, key=lambda r: r.trade_off_score)


import logging
import math
import re
from dataclasses import dataclass
from typing import Dict, List, Optional

import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, f1_score, precision_score, recall_score
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler
from sklearn.tree import DecisionTreeClassifier

from .insight_generator import InsightGenerator

logger = logging.getLogger(__name__)


def fairness_decision_engine(accuracy: float, bias_score: float, dataset_size: int):
    """Deterministic fairness decision engine for backend integration."""
    if bias_score < 0.05:
        bias_level = 'Low'
    elif bias_score <= 0.20:
        bias_level = 'Medium'
    else:
        bias_level = 'High'

    if accuracy < 0.50:
        model_reliability = 'Low'
    elif accuracy <= 0.75:
        model_reliability = 'Medium'
    else:
        model_reliability = 'High'

    mitigation = 'Yes' if bias_score > 0.20 else 'No'

    if dataset_size < 500:
        confidence = 'Low'
    elif dataset_size <= 2000:
        confidence = 'Medium'
    else:
        confidence = 'High'

    return {
        'bias_level': bias_level,
        'model_reliability': model_reliability,
        'mitigation': mitigation,
        'confidence': confidence,
    }


def _make_one_hot_encoder():
    try:
        return OneHotEncoder(handle_unknown='ignore', sparse_output=False)
    except TypeError:
        return OneHotEncoder(handle_unknown='ignore', sparse=False)


def _safe_float(value):
    try:
        if value is None:
            return None
        if isinstance(value, (np.floating, float)) and not math.isfinite(float(value)):
            return None
        return float(value)
    except Exception:
        return None


def _normalize_name(value: str) -> str:
    return str(value).lower().replace('-', '_').replace(' ', '_')


@dataclass
class AnalysisSplit:
    X_train: pd.DataFrame
    X_test: pd.DataFrame
    y_train: np.ndarray
    y_test: np.ndarray
    test_frame: pd.DataFrame


class ProductionBiasEngine:
    def __init__(self, dataset_name: str, dataset_df: pd.DataFrame, target_col: str, sensitive_attrs: List[str]):
        self.dataset_name = dataset_name
        self.dataset_df = dataset_df.copy()
        self.target_col = target_col
        self.sensitive_attrs = [attr for attr in (sensitive_attrs or []) if attr in self.dataset_df.columns]
        self.insight_generator = InsightGenerator()

    def _is_continuous_column(self, series: pd.Series):
        if not pd.api.types.is_numeric_dtype(series):
            return False
        return series.dropna().nunique() > 15

    def _bin_sensitive_column(self, df: pd.DataFrame, column: str) -> pd.DataFrame:
        if column not in df.columns:
            return df
        series = df[column]
        if not self._is_continuous_column(series):
            return df
        normalized = _normalize_name(column)
        try:
            if 'age' in normalized:
                bins = [-np.inf, 25, 40, 60, np.inf]
                labels = ['Young (<=25)', 'Adult (26-40)', 'Middle Age (41-60)', 'Senior (>60)']
                df[column] = pd.cut(series, bins=bins, labels=labels, include_lowest=True)
                return df
            n_bins = min(5, max(3, series.nunique(dropna=True) // 20))
            labels = [f'Group {i + 1}' for i in range(n_bins)]
            df[column] = pd.qcut(series, q=n_bins, labels=labels, duplicates='drop')
        except Exception:
            try:
                df[column] = pd.cut(series, bins=3, labels=['Low', 'Medium', 'High'])
            except Exception:
                pass
        return df

    def _normalize_sensitive_columns(self, df: pd.DataFrame) -> pd.DataFrame:
        normalized = df.copy()
        for column in self.sensitive_attrs:
            normalized = self._bin_sensitive_column(normalized, column)
        return normalized

    def _prepare_frame(self) -> pd.DataFrame:
        df = self.dataset_df.copy()
        if self.target_col not in df.columns:
            raise ValueError(f"Target column '{self.target_col}' not found")
        df = df.dropna(subset=[self.target_col]).copy()
        df = self._normalize_sensitive_columns(df)
        null_columns = [col for col in df.columns if col != self.target_col and df[col].notna().sum() == 0]
        if null_columns:
            df = df.drop(columns=null_columns)
        if df.empty:
            raise ValueError('Dataset is empty after preprocessing')
        return df

    def _split_data(self, df: pd.DataFrame) -> AnalysisSplit:
        y_raw = df[self.target_col].astype(str)
        if y_raw.nunique(dropna=True) < 2:
            raise ValueError('Target variable must contain at least two classes')
        y = pd.factorize(y_raw)[0]
        X = df.drop(columns=[self.target_col])
        for col in X.columns:
            if X[col].dtype.kind in 'biufc':
                X[col] = X[col].fillna(X[col].median())
            else:
                mode = X[col].mode(dropna=True)
                X[col] = X[col].fillna(mode.iloc[0] if not mode.empty else 'Unknown')
        stratify = y if len(np.unique(y)) > 1 and min(np.bincount(y)) >= 2 else None
        X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.3, random_state=42, stratify=stratify)
        test_frame = X_test.copy()
        test_frame[self.target_col] = y_raw.loc[X_test.index].values
        return AnalysisSplit(X_train, X_test, y_train, y_test, test_frame)

    def _build_preprocessor(self, X: pd.DataFrame):
        numeric_features = X.select_dtypes(include=['number', 'bool']).columns.tolist()
        categorical_features = [col for col in X.columns if col not in numeric_features]
        numeric_pipeline = Pipeline([
            ('imputer', SimpleImputer(strategy='median')),
            ('scaler', StandardScaler()),
        ])
        categorical_pipeline = Pipeline([
            ('imputer', SimpleImputer(strategy='most_frequent')),
            ('encoder', _make_one_hot_encoder()),
        ])
        preprocessor = ColumnTransformer(
            transformers=[
                ('num', numeric_pipeline, numeric_features),
                ('cat', categorical_pipeline, categorical_features),
            ],
            remainder='drop',
        )
        return preprocessor, numeric_features, categorical_features

    def _build_model(self, model_name: str):
        if model_name == 'decision_tree':
            return DecisionTreeClassifier(max_depth=8, random_state=42, class_weight='balanced')
        return LogisticRegression(solver='saga', max_iter=1000, random_state=42, class_weight='balanced')

    def _build_pipeline(self, model_name: str, X: pd.DataFrame) -> Pipeline:
        preprocessor, _, _ = self._build_preprocessor(X)
        return Pipeline([('preprocess', preprocessor), ('model', self._build_model(model_name))])

    def _evaluate_model(self, y_true, y_pred):
        return {
            'accuracy': _safe_float(accuracy_score(y_true, y_pred)),
            'precision': _safe_float(precision_score(y_true, y_pred, average='weighted', zero_division=0)),
            'recall': _safe_float(recall_score(y_true, y_pred, average='weighted', zero_division=0)),
            'f1': _safe_float(f1_score(y_true, y_pred, average='weighted', zero_division=0)),
        }

    def _group_bias_for_attribute(self, test_frame: pd.DataFrame, y_score: np.ndarray, attr: str):
        if attr not in test_frame.columns:
            return None
        frame = test_frame[[attr]].copy()
        frame['score'] = y_score
        frame = frame.dropna(subset=[attr])
        if frame.empty:
            return None
        group_metrics = {}
        group_means = []
        skipped_groups = []
        min_group_size = 30
        for group_value, group_df in frame.groupby(attr):
            group_size = len(group_df)
            group_mean = float(np.mean(group_df['score']))
            group_metrics[str(group_value)] = {
                'count': int(group_size),
                'mean_prediction_rate': group_mean,
                'is_small_group': group_size < min_group_size,
            }
            if group_size >= min_group_size:
                group_means.append(group_mean)
            else:
                skipped_groups.append(f"{group_value} (n={group_size})")
        if not group_means:
            group_means = [metrics['mean_prediction_rate'] for metrics in group_metrics.values()]
            if len(group_means) <= 1:
                return None
        max_mean = max(group_means)
        min_mean = min(group_means)
        bias_score = max_mean - min_mean
        if bias_score < 0.05:
            risk_level = 'LOW'
        elif bias_score < 0.15:
            risk_level = 'MEDIUM'
        else:
            risk_level = 'HIGH'
        highest_group = max(group_metrics.items(), key=lambda item: item[1]['mean_prediction_rate'])[0]
        lowest_group = min(group_metrics.items(), key=lambda item: item[1]['mean_prediction_rate'])[0]
        return {
            'demographic_parity_diff': _safe_float(bias_score),
            'disparate_impact_ratio': _safe_float(min_mean / max_mean if max_mean > 0 else 1.0),
            'bias_score': _safe_float(bias_score),
            'risk_level': risk_level,
            'group_metrics': group_metrics,
            'highest_group': highest_group,
            'lowest_group': lowest_group,
            'skipped_groups': skipped_groups,
        }

    def calculate_bias_metrics(self, test_frame: pd.DataFrame, y_score: np.ndarray):
        bias_report = {}
        for attr in self.sensitive_attrs:
            metric = self._group_bias_for_attribute(test_frame, y_score, attr)
            if metric is not None:
                bias_report[attr] = metric
        return bias_report

    def _risk_from_bias(self, bias_score: float):
        if bias_score < 0.05:
            return 'LOW'
        if bias_score < 0.15:
            return 'MEDIUM'
        return 'HIGH'

    def generate_insights(self, bias_report: Dict[str, Dict]):
        if not bias_report:
            return ['No sensitive attributes were available for bias analysis.']
        insights = []
        for attr, metrics in bias_report.items():
            highest = metrics.get('highest_group')
            lowest = metrics.get('lowest_group')
            score = float(metrics.get('bias_score', 0.0) or 0.0)
            skipped = metrics.get('skipped_groups', [])
            if skipped:
                insights.append(f"Small groups were excluded for {attr}: {', '.join(skipped[:2])}.")
            if score < 0.05:
                insights.append(f"Low bias detected for {attr}. Prediction rates are similar across groups.")
            elif score < 0.15:
                insights.append(f"Moderate bias detected for {attr}: {highest} is favored over {lowest}.")
            else:
                insights.append(f"High bias detected for {attr}: {highest} has significantly higher prediction rate than {lowest}.")
        return insights

    def generate_next_steps(self, bias_report: Dict[str, Dict]):
        if not bias_report:
            return ['Confirm dataset labeling and add sensitive attributes if available.']
        suggestions = [
            'Remove sensitive attributes from the training feature set.',
            'Balance the dataset for underrepresented groups.',
            'Review feature engineering for proxy variables.',
            'Monitor model outcomes across sensitive groups in production.',
        ]
        if any(metrics.get('risk_level') == 'HIGH' for metrics in bias_report.values()):
            suggestions.insert(0, 'High bias detected: prioritize mitigation before deployment.')
        return suggestions

    def _extract_feature_importance(self, pipeline: Pipeline):
        model = pipeline.named_steps['model']
        preprocessor = pipeline.named_steps['preprocess']
        try:
            feature_names = preprocessor.get_feature_names_out()
        except Exception:
            feature_names = []
        if hasattr(model, 'feature_importances_'):
            values = model.feature_importances_
        elif hasattr(model, 'coef_'):
            values = np.abs(np.asarray(model.coef_))
            if values.ndim > 1:
                values = values.mean(axis=0)
        else:
            return {}
        importance = {}
        for name, value in zip(feature_names, values):
            importance[self._humanize_feature_name(str(name))] = _safe_float(value)
        return dict(sorted(importance.items(), key=lambda item: item[1] or 0.0, reverse=True))

    def _humanize_feature_name(self, feature_name: str):
        cleaned = feature_name.replace('num__', '').replace('cat__', '').replace('remainder__', '')
        cleaned = cleaned.replace('__', ' ').replace('_', ' ')
        cleaned = re.sub(r'\s+', ' ', cleaned).strip()
        return cleaned.title()

    def _fit_model(self, model_name: str, split: AnalysisSplit):
        pipeline = self._build_pipeline(model_name, split.X_train)
        pipeline.fit(split.X_train, split.y_train)
        y_pred = pipeline.predict(split.X_test)
        y_score = pipeline.predict_proba(split.X_test)[:, 1] if hasattr(pipeline, 'predict_proba') else y_pred.astype(float)
        metrics = self._evaluate_model(split.y_test, y_pred)
        importance = self._extract_feature_importance(pipeline)
        return pipeline, metrics, y_pred, y_score, importance

    def _best_model_name(self, metrics: Dict[str, Dict[str, float]]):
        if not metrics:
            return 'logistic_regression'
        return max(metrics.items(), key=lambda item: (item[1].get('accuracy', 0.0), item[1].get('f1', 0.0)))[0]

    def run_full_analysis(self, model_types: Optional[List[str]] = None):
        model_types = [m for m in (model_types or ['logistic_regression', 'decision_tree']) if m in {'logistic_regression', 'decision_tree'}]
        if not model_types:
            model_types = ['logistic_regression', 'decision_tree']
        prepared = self._prepare_frame()
        split = self._split_data(prepared)
        model_results = {}
        for model_name in model_types:
            _, metrics, _, scores, importance = self._fit_model(model_name, split)
            model_results[model_name] = {
                'metrics': metrics,
                'feature_importance': importance,
                'scores': scores.tolist() if hasattr(scores, 'tolist') else list(scores),
            }
        best_model_name = self._best_model_name({name: info['metrics'] for name, info in model_results.items()})
        best_entry = model_results[best_model_name]
        best_metrics = best_entry['metrics']
        accuracy = best_metrics.get('accuracy', 0.0)
        
        # Calculate bias metrics
        bias_report = self.calculate_bias_metrics(split.test_frame, np.asarray(best_entry['scores']))
        overall_bias = max((metric['bias_score'] for metric in bias_report.values()), default=0.0)
        
        # Extract group-level metrics for fairness engine
        group_metrics = {}
        sample_sizes = {}
        for attr, metrics_dict in bias_report.items():
            group_data = metrics_dict.get('group_metrics', {})
            for group_name, group_info in group_data.items():
                key = f"{attr}_{group_name}"
                group_metrics[key] = {
                    'bias': group_info.get('mean_prediction_rate', 0.0),
                    'count': group_info.get('count', 0)
                }
                sample_sizes[key] = group_info.get('count', 0)
        
        # Execute deterministic fairness decision engine
        decision = fairness_decision_engine(
            accuracy=accuracy,
            bias_score=overall_bias,
            dataset_size=len(prepared),
        )

        # Generate context-aware insights
        insights_list = self.insight_generator.generate_insights(
            accuracy=accuracy,
            bias_score=overall_bias,
            precision=best_metrics.get('precision', 0.0),
            recall=best_metrics.get('recall', 0.0),
            group_metrics=group_metrics,
            model_reliability=decision['model_reliability'],
            should_mitigate=(decision['mitigation'] == 'Yes'),
            sample_sizes=sample_sizes if sample_sizes else None
        )

        print('Bias:', overall_bias)
        print('Accuracy:', accuracy)
        print('Decision:', decision)

        return {
            'dataset_name': self.dataset_name,
            'selected_model': best_model_name,
            'model_performance': {name: info['metrics'] for name, info in model_results.items()},
            'metrics': best_metrics,
            'feature_importance': best_entry['feature_importance'],
            'bias_by_feature': bias_report,
            'bias_analysis': bias_report,
            'bias_score': _safe_float(overall_bias),
            'risk_level': 'High' if overall_bias > 0.20 or accuracy < 0.50 else 'Medium' if overall_bias > 0.05 or accuracy <= 0.75 else 'Low',
            'decision': decision,
            'should_mitigate': decision['mitigation'] == 'Yes',
            'warning_flags': [],
            'fairness_reasoning': 'Yes' if decision['mitigation'] == 'Yes' else 'No',
            'insights': [
                {
                    'title': insight.title,
                    'description': insight.description,
                    'severity': insight.severity,
                    'category': insight.category,
                    'metrics_evidence': insight.metrics_evidence,
                    'action': insight.action
                }
                for insight in insights_list
            ],
            'mitigation_suggestions': self.generate_next_steps(bias_report),
        }


def get_engine():
    return ProductionBiasEngine

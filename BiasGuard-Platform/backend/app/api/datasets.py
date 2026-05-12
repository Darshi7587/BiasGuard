
import io
import logging
import csv
from enum import Enum
from typing import Dict, List, Optional
from uuid import uuid4

import pandas as pd
from fastapi import APIRouter, File, HTTPException, UploadFile
from pydantic import BaseModel, Field

from app.services.dataset_loader import get_loader
from app.services.production_engine import ProductionBiasEngine
from app.services.mitigation_engine import MitigationEngine

logger = logging.getLogger(__name__)
router = APIRouter()

DATASET_CONFIGS: Dict[str, Dict] = {}
ANALYSIS_RESULTS: Dict[str, Dict] = {}
UPLOADED_DATASETS: Dict[str, Dict] = {}

VALID_MODEL_TYPES = {'logistic_regression', 'decision_tree'}


class DatasetStatus(str, Enum):
    """Enum for valid dataset status values."""
    READY = 'Ready'
    NOT_STARTED = 'Not Started'
    PENDING = 'Pending'
    PROCESSING = 'Processing'


def _normalize_status(status: Optional[str]) -> str:
    """
    Normalize status strings to valid enum values.
    Handles null, empty, mixed-case, and whitespace.
    
    Examples:
        'ready' -> 'Ready'
        'READY' -> 'Ready'
        ' Ready ' -> 'Ready'
        None -> 'Not Started'
        'invalid' -> 'Not Started'
    """
    if not status or not isinstance(status, str):
        return DatasetStatus.NOT_STARTED.value
    
    normalized = status.strip().lower()
    
    # Map common variants to canonical status values
    status_map = {
        'ready': DatasetStatus.READY.value,
        'analyzed': DatasetStatus.READY.value,
        'complete': DatasetStatus.READY.value,
        'done': DatasetStatus.READY.value,
        'not_started': DatasetStatus.NOT_STARTED.value,
        'notstarted': DatasetStatus.NOT_STARTED.value,
        'pending': DatasetStatus.PENDING.value,
        'waiting': DatasetStatus.PENDING.value,
        'queued': DatasetStatus.PENDING.value,
        'processing': DatasetStatus.PROCESSING.value,
        'analyzing': DatasetStatus.PROCESSING.value,
        'running': DatasetStatus.PROCESSING.value,
        'in progress': DatasetStatus.PROCESSING.value,
        'inprogress': DatasetStatus.PROCESSING.value,
    }
    
    return status_map.get(normalized, DatasetStatus.NOT_STARTED.value)


class ConfigureRequest(BaseModel):
    dataset_id: str
    target_column: str
    sensitive_attributes: List[str]
    model_types: List[str] = Field(default_factory=lambda: ['logistic_regression', 'decision_tree'])


class AnalyzeRequest(BaseModel):
    dataset_id: str
    target_column: Optional[str] = None
    sensitive_attributes: List[str] = Field(default_factory=list)
    model_types: Optional[List[str]] = None


class MitigationRequest(BaseModel):
    dataset_id: str
    target_column: Optional[str] = None
    sensitive_attributes: List[str] = Field(default_factory=list)
    model_types: Optional[List[str]] = None


def _serialize_value(value):
    if isinstance(value, dict):
        return {key: _serialize_value(inner) for key, inner in value.items()}
    if isinstance(value, list):
        return [_serialize_value(item) for item in value]
    if hasattr(value, 'item'):
        try:
            return _serialize_value(value.item())
        except Exception:
            pass
    if isinstance(value, float):
        return value if value == value and value not in (float('inf'), float('-inf')) else None
    return value


def _sanitize_model_types(model_types: Optional[List[str]]):
    if not model_types:
        return ['logistic_regression', 'decision_tree']
    return [m for m in model_types if m in VALID_MODEL_TYPES]


def _get_uploaded_dataset(dataset_id: str):
    return UPLOADED_DATASETS.get(dataset_id)


def _get_dataset_and_metadata(dataset_id: str):
    uploaded = _get_uploaded_dataset(dataset_id)
    if uploaded:
        return uploaded['data'], uploaded['metadata']
    loader = get_loader()
    metadata = loader.get_metadata(dataset_id)
    if metadata is None:
        return None, None
    df = loader.get_dataset(dataset_id)
    return df, metadata


def _validate_dataset(target_column: str, sensitive_attributes: List[str], metadata: dict):
    if target_column not in metadata.get('column_names', []):
        raise HTTPException(status_code=400, detail='Invalid target column')
    for attr in sensitive_attributes:
        if attr not in metadata.get('column_names', []):
            raise HTTPException(status_code=400, detail=f'Invalid sensitive attribute: {attr}')


@router.get('/datasets')
def list_datasets():
    """
    List all datasets (folder-based and uploaded).
    Applies deduplication, normalization, and consistent status formatting.
    
    Returns:
        - Deduplicated dataset list (uploaded datasets take precedence)
        - Normalized status values (Ready, Not Started, Pending, Processing)
        - Total count of unique datasets
    """
    loader = get_loader()
    metadata = loader.get_all_metadata()
    
    # Use dict to deduplicate by dataset_id (uploaded datasets override folder datasets)
    datasets_map: Dict[str, dict] = {}
    
    # Add folder-based datasets first
    for name, meta in metadata.items():
        datasets_map[name] = {
            'dataset_id': name,
            'name': meta.get('name', name),
            'filename': meta.get('filename', name),
            'rows': meta.get('rows', meta.get('shape', [None, None])[0]),
            'columns': meta.get('columns', meta.get('shape', [None, None])[1]),
            'column_names': meta.get('column_names', []),
            'target': meta.get('target'),
            'target_candidates': meta.get('target_candidates', []),
            'sensitive_attributes': meta.get('sensitive', []),
            'description': meta.get('description'),
            'source': 'folder',
            # Normalize status to title case
            'status': _normalize_status('ready' if name in ANALYSIS_RESULTS else 'not_started'),
        }
    
    # Add/override with uploaded datasets (uploaded takes precedence if duplicate ID)
    for dataset_id, uploaded in UPLOADED_DATASETS.items():
        datasets_map[dataset_id] = {
            'dataset_id': dataset_id,
            'name': uploaded['metadata'].get('filename', dataset_id),
            'filename': uploaded['metadata'].get('filename', dataset_id),
            'rows': uploaded['metadata'].get('rows'),
            'columns': uploaded['metadata'].get('columns'),
            'column_names': uploaded['metadata'].get('column_names', []),
            'target': uploaded['metadata'].get('target'),
            'target_candidates': uploaded['metadata'].get('target_candidates', []),
            'sensitive_attributes': uploaded['metadata'].get('sensitive', []),
            'description': uploaded['metadata'].get('description', 'Uploaded dataset'),
            'source': 'uploaded',
            # Normalize status to title case
            'status': _normalize_status('ready' if dataset_id in ANALYSIS_RESULTS else 'not_started'),
        }
    
    # Convert dict back to list and sort by filename for consistent ordering
    datasets = sorted(datasets_map.values(), key=lambda x: x['filename'].lower())
    
    return {
        'datasets': datasets,
        'count': len(datasets),
        'stats': {
            'total': len(datasets),
            'ready': sum(1 for d in datasets if d['status'] == DatasetStatus.READY.value),
            'not_started': sum(1 for d in datasets if d['status'] == DatasetStatus.NOT_STARTED.value),
            'pending': sum(1 for d in datasets if d['status'] == DatasetStatus.PENDING.value),
            'processing': sum(1 for d in datasets if d['status'] == DatasetStatus.PROCESSING.value),
        }
    }


@router.get('/datasets/{dataset_id}')
def get_dataset(dataset_id: str):
    df, metadata = _get_dataset_and_metadata(dataset_id)
    if metadata is None:
        raise HTTPException(status_code=404, detail='Dataset not found')
    
    # Determine if this dataset has been analyzed
    is_analyzed = dataset_id in ANALYSIS_RESULTS
    
    return {
        'dataset_id': dataset_id,
        'filename': metadata.get('filename', dataset_id),
        'name': metadata.get('name', dataset_id),
        'rows': metadata.get('rows'),
        'columns': metadata.get('columns'),
        'column_names': metadata.get('column_names', []),
        'target': metadata.get('target'),
        'target_candidates': metadata.get('target_candidates', []),
        'sensitive_attributes': metadata.get('sensitive', []),
        'description': metadata.get('description', 'Dataset'),
        'status': _normalize_status('ready' if is_analyzed else 'not_started'),
    }


@router.post('/configure')
def configure_analysis(config: ConfigureRequest):
    df, metadata = _get_dataset_and_metadata(config.dataset_id)
    if metadata is None:
        raise HTTPException(status_code=404, detail='Dataset not found')
    _validate_dataset(config.target_column, config.sensitive_attributes, metadata)
    valid_models = _sanitize_model_types(config.model_types)
    if not valid_models:
        valid_models = ['logistic_regression', 'decision_tree']
    DATASET_CONFIGS[config.dataset_id] = {
        'dataset_id': config.dataset_id,
        'target_column': config.target_column,
        'sensitive_attributes': config.sensitive_attributes,
        'model_types': valid_models,
    }
    return {'status': 'configured', 'config': DATASET_CONFIGS[config.dataset_id]}


@router.post('/analyze')
def analyze_dataset(request: AnalyzeRequest):
    df, metadata = _get_dataset_and_metadata(request.dataset_id)
    if metadata is None:
        raise HTTPException(status_code=404, detail='Dataset not found')
    config = DATASET_CONFIGS.get(request.dataset_id, {})
    target_column = request.target_column or config.get('target_column') or metadata.get('target')
    sensitive_attributes = request.sensitive_attributes or config.get('sensitive_attributes') or metadata.get('sensitive', [])
    model_types = _sanitize_model_types(request.model_types or config.get('model_types'))
    if not model_types:
        model_types = ['logistic_regression', 'decision_tree']
    if not target_column or not sensitive_attributes:
        raise HTTPException(status_code=400, detail='Target column and sensitive attributes are required for analysis')
    _validate_dataset(target_column, sensitive_attributes, metadata)
    if df is None or df.empty:
        raise HTTPException(status_code=400, detail='Dataset is unavailable or empty')
    if len(df) > 10000:
        df = df.head(10000)
    engine = ProductionBiasEngine(
        dataset_name=request.dataset_id,
        dataset_df=df,
        target_col=target_column,
        sensitive_attrs=sensitive_attributes,
    )
    result = engine.run_full_analysis(model_types=model_types)
    result['dataset_id'] = request.dataset_id
    result['configuration'] = {
        'target_column': target_column,
        'sensitive_attributes': sensitive_attributes,
        'model_types': model_types,
    }
    result['dataset_info'] = {
        'rows': int(df.shape[0]),
        'columns': int(df.shape[1]),
        'column_names': list(df.columns),
    }
    print('Decision Output:', result.get('decision'))
    ANALYSIS_RESULTS[request.dataset_id] = _serialize_value(result)
    return ANALYSIS_RESULTS[request.dataset_id]


@router.post('/mitigation')
def evaluate_mitigation(request: MitigationRequest):
    """
    Evaluate multiple fairness mitigation strategies for a dataset.
    Returns ranked mitigation strategies with before/after comparisons.
    """
    df, metadata = _get_dataset_and_metadata(request.dataset_id)
    if metadata is None:
        raise HTTPException(status_code=404, detail='Dataset not found')
    
    config = DATASET_CONFIGS.get(request.dataset_id, {})
    target_column = request.target_column or config.get('target_column') or metadata.get('target')
    sensitive_attributes = request.sensitive_attributes or config.get('sensitive_attributes') or metadata.get('sensitive', [])
    model_types = _sanitize_model_types(request.model_types or config.get('model_types'))
    
    if not target_column or not sensitive_attributes:
        raise HTTPException(status_code=400, detail='Target column and sensitive attributes are required')
    
    _validate_dataset(target_column, sensitive_attributes, metadata)
    
    if df is None or df.empty:
        raise HTTPException(status_code=400, detail='Dataset is unavailable or empty')
    
    if len(df) > 10000:
        df = df.head(10000)
    
    try:
        # Import here to avoid circular dependency
        from sklearn.model_selection import train_test_split
        from sklearn.pipeline import Pipeline
        from sklearn.compose import ColumnTransformer
        from sklearn.preprocessing import OneHotEncoder, StandardScaler
        from sklearn.impute import SimpleImputer
        from sklearn.linear_model import LogisticRegression
        import numpy as np
        
        # Prepare data (similar to ProductionBiasEngine)
        y_raw = df[target_column].astype(str)
        if y_raw.nunique(dropna=True) < 2:
            raise ValueError('Target variable must contain at least two classes')
        
        y = pd.factorize(y_raw)[0]
        X = df.drop(columns=[target_column])
        
        # Handle missing values
        for col in X.columns:
            if X[col].dtype.kind in 'biufc':
                X[col] = X[col].fillna(X[col].median())
            else:
                mode = X[col].mode(dropna=True)
                X[col] = X[col].fillna(mode.iloc[0] if not mode.empty else 'Unknown')
        
        # Split data
        stratify = y if len(np.unique(y)) > 1 and min(np.bincount(y)) >= 2 else None
        X_train, X_test, y_train, y_test = train_test_split(
            X, y, test_size=0.3, random_state=42, stratify=stratify
        )
        
        # Build preprocessing pipeline (handles categorical + numeric features)
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
        
        # Build and train baseline model with preprocessing
        baseline_pipeline = Pipeline([
            ('preprocessor', preprocessor),
            ('model', LogisticRegression(
                solver='saga', max_iter=1000, random_state=42, class_weight='balanced'
            ))
        ])
        
        baseline_pipeline.fit(X_train, y_train)
        y_pred_baseline = baseline_pipeline.predict(X_test)
        
        # Create group data dict
        group_data = {}
        for attr in sensitive_attributes:
            if attr in X_test.columns:
                for group_val in X_test[attr].unique():
                    if pd.notna(group_val):
                        group_key = f"{attr}_{group_val}"
                        group_data[group_key] = X_test[attr].values == group_val
        
        # Run mitigation engine
        mitigation_engine = MitigationEngine()
        mitigation_results = mitigation_engine.evaluate_mitigation_strategies(
            X_train=X_train,
            X_test=X_test,
            y_train=y_train,
            y_test=y_test,
            y_pred_original=y_pred_baseline,
            group_data=group_data,
            model_type='logistic_regression',
            target_bias_threshold=0.05
        )
        
        # Convert results to JSON-serializable format
        results_json = []
        for result in mitigation_results:
            results_json.append({
                'strategy': result.strategy,
                'accuracy_before': float(result.accuracy_before),
                'accuracy_after': float(result.accuracy_after),
                'bias_before': float(result.bias_before),
                'bias_after': float(result.bias_after),
                'fairness_improvement': float(result.fairness_improvement),
                'accuracy_loss': float(result.accuracy_loss),
                'trade_off_score': float(result.trade_off_score),
                'details': result.details,
                'recommendation': result.recommendation,
            })
        
        # Store mitigation results
        mitigation_cache_key = f"{request.dataset_id}_mitigation"
        ANALYSIS_RESULTS[mitigation_cache_key] = _serialize_value({
            'dataset_id': request.dataset_id,
            'strategies': results_json,
            'best_strategy': results_json[0] if results_json else None,
            'configuration': {
                'target_column': target_column,
                'sensitive_attributes': sensitive_attributes,
                'model_types': model_types,
            }
        })
        
        return ANALYSIS_RESULTS[mitigation_cache_key]
    
    except Exception as e:
        logger.error(f'Mitigation evaluation error: {e}')
        raise HTTPException(status_code=500, detail=f'Mitigation evaluation failed: {str(e)}')


@router.get('/results/{dataset_id}')
def get_results(dataset_id: str):
    if dataset_id not in ANALYSIS_RESULTS:
        raise HTTPException(status_code=404, detail='Analysis results not found. Run analysis first.')
    return ANALYSIS_RESULTS[dataset_id]


def _read_uploaded_file(file: UploadFile):
    contents = file.file.read()
    if not contents:
        raise ValueError('Uploaded file is empty')
    filename = file.filename.lower()
    if filename.endswith(('.xlsx', '.xls')):
        return pd.read_excel(io.BytesIO(contents))
    if filename.endswith(('.csv', '.txt')):
        encodings = ['utf-8', 'latin1', 'cp1252']
        delimiters = [',', ';', '	', '|']
        for encoding in encodings:
            try:
                sample = contents[:4096].decode(encoding, errors='ignore')
                separator = None
                try:
                    separator = csv.Sniffer().sniff(sample, delimiters=delimiters).delimiter
                except Exception:
                    separator = None
                candidates = []
                if separator:
                    candidates.append(pd.read_csv(io.BytesIO(contents), encoding=encoding, sep=separator))
                candidates.append(pd.read_csv(io.BytesIO(contents), encoding=encoding, sep=None, engine='python'))
                candidates.append(pd.read_csv(io.BytesIO(contents), encoding=encoding, sep=';'))
                candidates.append(pd.read_csv(io.BytesIO(contents), encoding=encoding, sep=','))
                for frame in candidates:
                    if frame.shape[1] > 1:
                        return frame
            except Exception:
                continue
        return pd.read_csv(io.BytesIO(contents), encoding='utf-8', encoding_errors='replace', sep=None, engine='python')
    return pd.read_csv(io.BytesIO(contents), encoding='utf-8', encoding_errors='replace')


@router.post('/upload')
def upload_dataset(file: UploadFile = File(...)):
    try:
        df = _read_uploaded_file(file)
        if df is None or df.empty:
            raise HTTPException(status_code=400, detail='Unable to parse uploaded dataset')
        dataset_id = f'uploaded-{uuid4()}'
        column_names = list(df.columns)
        categorical_columns = df.select_dtypes(include=['object', 'category']).columns.tolist()
        numerical_columns = df.select_dtypes(include=['number']).columns.tolist()
        target_candidates = [col for col in column_names if col.lower() in ['target', 'income', 'y', 'label', 'class', 'credit_risk', 'g3', 'is_recid', 'is_recidivist']]
        sensitive_candidates = [col for col in column_names if any(keyword in col.lower() for keyword in ['sex', 'gender', 'race', 'age', 'ethnicity', 'marital', 'school', 'relationship', 'native_country', 'custody', 'language', 'legal_status'])]
        target = target_candidates[0] if target_candidates else (column_names[-1] if column_names else None)
        sensitive = sensitive_candidates[:2] if sensitive_candidates else column_names[:2]
        metadata = {
            'dataset_id': dataset_id,
            'name': file.filename,
            'filename': file.filename,
            'rows': int(df.shape[0]),
            'columns': int(df.shape[1]),
            'column_names': column_names,
            'categorical_columns': categorical_columns,
            'numerical_columns': numerical_columns,
            'target': target,
            'target_candidates': target_candidates,
            'sensitive': sensitive,
            'target_reason': 'Uploaded dataset default target selection',
            'sensitive_reason': 'Uploaded dataset default sensitive selection',
            'description': 'Uploaded dataset available for analysis',
        }
        UPLOADED_DATASETS[dataset_id] = {'data': df, 'metadata': metadata}
        DATASET_CONFIGS[dataset_id] = {
            'dataset_id': dataset_id,
            'target_column': target,
            'sensitive_attributes': sensitive,
            'model_types': ['logistic_regression', 'decision_tree'],
        }
        return {
            'dataset_id': dataset_id,
            'filename': file.filename,
            'rows': int(df.shape[0]),
            'columns': int(df.shape[1]),
            'column_names': column_names,
            'suggested_target': target,
            'suggested_sensitive_attrs': sensitive,
        }
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except Exception as exc:
        logger.error(f'Upload error: {exc}')
        raise HTTPException(status_code=500, detail='Upload failed')

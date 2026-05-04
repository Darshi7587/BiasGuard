
import io
import logging
import csv
from typing import Dict, List, Optional
from uuid import uuid4

import pandas as pd
from fastapi import APIRouter, File, HTTPException, UploadFile
from pydantic import BaseModel, Field

from app.services.dataset_loader import get_loader
from app.services.production_engine import ProductionBiasEngine

logger = logging.getLogger(__name__)
router = APIRouter()

DATASET_CONFIGS: Dict[str, Dict] = {}
ANALYSIS_RESULTS: Dict[str, Dict] = {}
UPLOADED_DATASETS: Dict[str, Dict] = {}

VALID_MODEL_TYPES = {'logistic_regression', 'decision_tree'}


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
    loader = get_loader()
    metadata = loader.get_all_metadata()
    datasets = []
    for name, meta in metadata.items():
        datasets.append({
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
            'analyzed': name in ANALYSIS_RESULTS,
            'status': 'ready' if name in ANALYSIS_RESULTS else 'not_started',
        })
    for dataset_id, uploaded in UPLOADED_DATASETS.items():
        datasets.append({
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
            'analyzed': dataset_id in ANALYSIS_RESULTS,
            'status': 'ready' if dataset_id in ANALYSIS_RESULTS else 'not_started',
        })
    return {'datasets': datasets, 'count': len(datasets)}


@router.get('/datasets/{dataset_id}')
def get_dataset(dataset_id: str):
    df, metadata = _get_dataset_and_metadata(dataset_id)
    if metadata is None:
        raise HTTPException(status_code=404, detail='Dataset not found')
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
        'target_reason': metadata.get('target_reason'),
        'sensitive_reason': metadata.get('sensitive_reason'),
        'description': metadata.get('description'),
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
    ANALYSIS_RESULTS[request.dataset_id] = _serialize_value(result)
    return ANALYSIS_RESULTS[request.dataset_id]


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

from fastapi import APIRouter, HTTPException, Query
import logging
import math
import numpy as np
from app.api.upload import UPLOADED_DATASETS
from app.services.production_engine import ProductionBiasEngine

logger = logging.getLogger(__name__)

router = APIRouter()

@router.post("/configure-uploaded")
def configure_analysis(config: dict):
    """Configure analysis for an uploaded dataset."""
    try:
        dataset_id = config.get('dataset_id')
        target_column = config.get('target_column')
        sensitive_attributes = config.get('sensitive_attributes', [])
        model_type = config.get('model_type', 'logistic_regression')
        
        if dataset_id not in UPLOADED_DATASETS:
            raise HTTPException(status_code=404, detail="Dataset not found")
        
        UPLOADED_DATASETS[dataset_id]['config'] = {
            'target_column': target_column,
            'sensitive_attributes': sensitive_attributes,
            'model_type': model_type
        }
        
        logger.info(f"Configured analysis for {dataset_id}: target={target_column}, sensitive={sensitive_attributes}, model_type={model_type}")
        
        return {
            'status': 'configured',
            'dataset_id': dataset_id,
            'target_column': target_column,
            'sensitive_attributes': sensitive_attributes,
            'model_type': model_type
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Configuration error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/analyze")
def analyze(
    dataset_id: str = Query(...),
    target_column: str | None = Query(None),
    sensitive_attributes: str | None = Query(None),
):
    """Analyze a dataset for bias."""
    try:
        logger.info(f"Starting analysis for dataset_id: {dataset_id}")
        
        if dataset_id not in UPLOADED_DATASETS:
            logger.error(f"Dataset {dataset_id} not found in UPLOADED_DATASETS")
            raise HTTPException(status_code=404, detail="Dataset not found")
        
        dataset = UPLOADED_DATASETS[dataset_id]
        df = dataset['data']
        config = dataset.get('config', {})
        
        logger.info(f"Dataset shape: {df.shape}")
        logger.info(f"Dataset columns: {list(df.columns)}")
        logger.info(f"Dataset config: {config}")
        
        if not config or not config.get('target_column'):
            logger.error(f"Dataset {dataset_id} not configured")
            raise HTTPException(status_code=400, detail="Dataset not configured. Please configure the dataset first.")
        
        target_col = target_column or config.get('target_column')
        sensitive_attrs = (
            [item.strip() for item in sensitive_attributes.split(',') if item.strip()]
            if sensitive_attributes else config.get('sensitive_attributes', []) or []
        )
        model_type = config.get('model_type', 'logistic_regression')
        
        logger.info(f"Target column: {target_col}")
        logger.info(f"Sensitive attributes: {sensitive_attrs}")
        logger.info(f"Selected model type: {model_type}")
        
        if not target_col or target_col not in df.columns:
            numeric_cols = df.select_dtypes(include=['number']).columns.tolist()
            binary_numeric = [col for col in numeric_cols if df[col].nunique(dropna=True) == 2]
            low_cardinality = [col for col in df.columns if 2 <= df[col].nunique(dropna=True) <= 10]

            if binary_numeric:
                target_col = binary_numeric[0]
                target_col_reason = f"Selected binary target candidate '{target_col}'"
            elif low_cardinality:
                target_col = low_cardinality[0]
                target_col_reason = f"Selected low-cardinality target candidate '{target_col}'"
            else:
                target_col = df.columns[-1]
                target_col_reason = f"Auto-selected fallback target '{target_col}'"
        else:
            target_col_reason = f"Using confirmed target column: '{target_col}'"
        
        if not target_col:
            logger.error(f"No suitable target column found for dataset {dataset_id}")
            raise HTTPException(status_code=400, detail="No suitable target column found")
        
        if not sensitive_attrs:
            categorical_cols = df.select_dtypes(include=['object', 'category']).columns.tolist()
            demographic_keywords = ['race', 'gender', 'sex', 'age', 'ethnicity', 'marital', 'education', 'school']
            demographic_cols = [col for col in categorical_cols if any(kw in col.lower() for kw in demographic_keywords)]
            if demographic_cols:
                sensitive_attrs = demographic_cols[:2]
                sensitive_attrs_reason = f"Selected demographic columns: {sensitive_attrs}"
            else:
                sensitive_attrs = categorical_cols[:2] if len(categorical_cols) >= 2 else categorical_cols
                sensitive_attrs_reason = f"Selected categorical columns: {sensitive_attrs}"
        else:
            sensitive_attrs_reason = f"Using confirmed sensitive attributes: {sensitive_attrs}"
        
        if not sensitive_attrs:
            logger.error(f"No suitable sensitive attributes found for dataset {dataset_id}")
            raise HTTPException(status_code=400, detail="No suitable sensitive attributes found")

        logger.info(f"Final target column: {target_col}")
        logger.info(f"Final sensitive attributes: {sensitive_attrs}")

        engine = ProductionBiasEngine('uploaded', df, target_col, sensitive_attrs)
        result = engine.run_full_analysis(target_column=target_col, sensitive_attributes=sensitive_attrs)
        result['dataset_id'] = dataset_id
        result['selection_reasoning'] = {
            'target_column_reason': target_col_reason,
            'sensitive_attributes_reason': sensitive_attrs_reason,
        }
        result['configuration'] = {
            'target_column': target_col,
            'sensitive_attributes': sensitive_attrs,
            'model_type': model_type,
        }
        result['dataset_info'] = {
            'rows': int(df.shape[0]),
            'columns': int(df.shape[1]),
            'column_names': list(df.columns),
        }

        def sanitize_value(value):
            if isinstance(value, dict):
                return {k: sanitize_value(v) for k, v in value.items()}
            if isinstance(value, list):
                return [sanitize_value(v) for v in value]
            if isinstance(value, np.generic):
                return sanitize_value(value.item())
            if isinstance(value, float):
                if math.isfinite(value):
                    return value
                return None
            if isinstance(value, int):
                return value
            return value

        sanitized_response = sanitize_value(result)
        logger.info(f"Analysis complete for {dataset_id}")
        return sanitized_response
    except HTTPException:
        raise
    except ValueError as e:
        logger.error(f"Analysis validation error for dataset {dataset_id}: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Analysis error for dataset {dataset_id}: {str(e)}")
        logger.error(f"Exception type: {type(e).__name__}")
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/dataset/{dataset_id}")
def get_dataset(dataset_id: str):
    """Get dataset metadata for old upload flow compatibility."""
    if dataset_id not in UPLOADED_DATASETS:
        raise HTTPException(status_code=404, detail="Dataset not found")
    
    dataset = UPLOADED_DATASETS[dataset_id]
    return {
        'dataset_id': dataset_id,
        'filename': dataset['filename'],
        'shape': dataset.get('shape', (dataset.get('rows'), dataset.get('columns'))),
        'columns': dataset.get('columns', dataset.get('shape', [None, None])[1])
    }

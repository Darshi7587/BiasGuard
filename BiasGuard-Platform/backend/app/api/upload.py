from fastapi import APIRouter, UploadFile, File, HTTPException
import csv
import uuid
import io
import pandas as pd
import logging
from app.utils.dataset_analyzer import analyze_dataset

logger = logging.getLogger(__name__)

router = APIRouter()

# Store uploaded datasets in memory (in production, use a database)
UPLOADED_DATASETS = {}

MAX_UPLOAD_SIZE = 50 * 1024 * 1024

async def _read_uploaded_file(file: UploadFile):
    contents = await file.read()
    if len(contents) > MAX_UPLOAD_SIZE:
        raise ValueError("Uploaded file exceeds maximum allowed size of 50 MB.")

    filename = file.filename.lower()
    if filename.endswith(('.xlsx', '.xls')):
        try:
            return pd.read_excel(io.BytesIO(contents))
        except Exception as exc:
            raise ValueError(f"Unable to parse Excel file: {exc}")

    if filename.endswith('.csv') or filename.endswith('.txt'):
        encodings = ['utf-8', 'latin1', 'cp1252']
        delimiters = [',', ';', '\t', '|']

        for encoding in encodings:
            try:
                sample = contents[:4096].decode(encoding, errors='ignore')
                try:
                    sniffed = csv.Sniffer().sniff(sample, delimiters=delimiters)
                    separator = sniffed.delimiter
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

        try:
            return pd.read_csv(io.BytesIO(contents), encoding='utf-8', encoding_errors='replace', sep=None, engine='python')
        except Exception as exc:
            raise ValueError(f"Unable to parse CSV file: {exc}")

    # Default to CSV parser for unknown extensions
    try:
        return pd.read_csv(io.BytesIO(contents), encoding='utf-8', encoding_errors='replace')
    except Exception as exc:
        raise ValueError(f"Unable to parse uploaded file: {exc}")


@router.post("/upload")
async def upload_dataset(file: UploadFile = File(...)):
    """Upload a dataset file for analysis."""
    try:
        df = await _read_uploaded_file(file)

        # Generate unique ID
        dataset_id = str(uuid.uuid4())

        # Build metadata for the uploaded dataset
        column_names = list(df.columns)
        categorical_columns = df.select_dtypes(include=['object', 'category']).columns.tolist()
        numerical_columns = df.select_dtypes(include=['number']).columns.tolist()
        suggested_target = next(
            (col for col in column_names if col.lower() in ['target', 'income', 'y', 'label', 'class', 'credit_risk', 'g3', 'is_recid', 'is_recidivist']),
            column_names[-1] if column_names else None
        )
        suggested_sensitive_attrs = [
            col for col in column_names
            if col.lower() in ['sex', 'gender', 'race', 'age', 'marital', 'school', 'relationship', 'native_country']
        ]

        UPLOADED_DATASETS[dataset_id] = {
            'data': df,
            'filename': file.filename,
            'shape': df.shape,
            'rows': int(df.shape[0]),
            'columns': int(df.shape[1]),
            'column_names': column_names,
            'categorical_columns': categorical_columns,
            'numerical_columns': numerical_columns,
            'suggested_target': suggested_target,
            'suggested_sensitive_attrs': suggested_sensitive_attrs,
            'config': {
                'target_column': None,
                'sensitive_attributes': []
            }
        }

        logger.info(f"Uploaded dataset {dataset_id}: {df.shape}")
        logger.info(f"Dataset columns: {column_names}")
        logger.info(f"Categorical columns: {categorical_columns}")
        logger.info(f"Numerical columns: {numerical_columns}")

        return {
            'dataset_id': dataset_id,
            'filename': file.filename,
            'rows': int(df.shape[0]),
            'columns': int(df.shape[1]),
            'column_names': column_names,
            'categorical_columns': categorical_columns,
            'numerical_columns': numerical_columns,
            'suggested_target': suggested_target,
            'suggested_sensitive_attrs': suggested_sensitive_attrs
        }
    except Exception as e:
        logger.error(f"Upload error: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/dataset-info/{dataset_id}")
def get_dataset_info(dataset_id: str):
    """Get information about an uploaded dataset."""
    if dataset_id not in UPLOADED_DATASETS:
        raise HTTPException(status_code=404, detail="Dataset not found")
    
    dataset = UPLOADED_DATASETS[dataset_id]
    analysis = analyze_dataset(dataset['data'], dataset_id)
    
    return {
        'dataset_id': dataset_id,
        'filename': dataset['filename'],
        'rows': dataset['rows'],
        'columns': dataset['columns'],
        'column_names': dataset['column_names'],
        'categorical_columns': dataset['categorical_columns'],
        'numerical_columns': dataset['numerical_columns'],
        'suggested_target': dataset['suggested_target'],
        'suggested_sensitive_attrs': dataset['suggested_sensitive_attrs'],
        'analysis': analysis
    }

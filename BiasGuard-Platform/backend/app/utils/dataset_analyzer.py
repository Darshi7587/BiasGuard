import pandas as pd
import numpy as np
from sklearn.preprocessing import LabelEncoder
import logging

logger = logging.getLogger(__name__)

def analyze_dataset(df, dataset_id=None):
    """Comprehensive dataset analysis."""
    try:
        analysis = {
            'dataset_id': dataset_id,
            'shape': df.shape,
            'columns': list(df.columns),
            'dtypes': {col: str(dtype) for col, dtype in df.dtypes.items()},
            'missing_values': {col: int(df[col].isnull().sum()) for col in df.columns},
            'duplicates': int(df.duplicated().sum()),
            'numeric_columns': list(df.select_dtypes(include=[np.number]).columns),
            'categorical_columns': list(df.select_dtypes(include=['object']).columns)
        }
        return analysis
    except Exception as e:
        logger.error(f"Error analyzing dataset: {str(e)}")
        return {}

def preprocess_dataset(df, target_column, sensitive_attributes):
    """Preprocess dataset for bias analysis."""
    preprocessing_info = {}
    
    try:
        df_clean = df.copy()
        
        # Identify categorical columns
        categorical_cols = df_clean.select_dtypes(include=['object']).columns.tolist()
        
        # Handle missing values
        for col in df_clean.columns:
            if df_clean[col].isnull().sum() > 0:
                if col in categorical_cols:
                    mode_val = df_clean[col].mode()
                    if len(mode_val) > 0:
                        df_clean[col] = df_clean[col].fillna(mode_val[0])
                else:
                    df_clean[col] = df_clean[col].fillna(df_clean[col].median())
                preprocessing_info[f"filled_{col}"] = df_clean[col].isnull().sum()
        
        # Remove duplicates
        df_clean = df_clean.drop_duplicates()
        preprocessing_info['duplicates_removed'] = df.shape[0] - df_clean.shape[0]
        
        # Encode categorical variables
        encoders = {}
        for col in categorical_cols:
            if col in df_clean.columns:
                le = LabelEncoder()
                df_clean[col] = le.fit_transform(df_clean[col].astype(str))
                encoders[col] = le
        
        preprocessing_info['encoded_columns'] = list(encoders.keys())
        preprocessing_info['final_shape'] = df_clean.shape
        
        logger.info(f"Preprocessing complete: {preprocessing_info}")
        return df_clean, preprocessing_info
        
    except Exception as e:
        logger.error(f"Error preprocessing dataset: {str(e)}")
        raise

def calculate_descriptive_stats(df):
    """Calculate descriptive statistics."""
    try:
        stats = {
            'numeric_stats': df.describe().to_dict(),
            'correlation': df.corr().to_dict() if len(df.select_dtypes(include=[np.number]).columns) > 0 else {}
        }
        return stats
    except Exception as e:
        logger.error(f"Error calculating stats: {str(e)}")
        return {}

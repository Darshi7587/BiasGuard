from pydantic import BaseModel
from typing import List, Optional, Dict, Any

class ColumnConfig(BaseModel):
    name: str
    type: str
    
class ConfigurationRequest(BaseModel):
    dataset_id: str
    target_column: str
    sensitive_attributes: List[str]
    protected_groups: Optional[Dict[str, List[Any]]] = None
    categorical_columns: Optional[List[str]] = None
    model_types: Optional[List[str]] = None

class AnalysisRequest(BaseModel):
    dataset_id: str
    target_column: str
    sensitive_attributes: List[str]
    protected_groups: Optional[Dict[str, List[Any]]] = None
    model_types: Optional[List[str]] = None

class BiasMetrics(BaseModel):
    demographic_parity_diff: float
    disparate_impact_ratio: float
    bias_score: float
    accuracy: float
    
class DatasetMetadata(BaseModel):
    name: str
    shape: tuple
    columns: List[str]
    target: str
    sensitive_attributes: List[str]
    description: str


import csv
import logging
from pathlib import Path

import pandas as pd

logger = logging.getLogger(__name__)


class FolderDatasetLoader:
    TARGET_HINTS = [
        'target', 'income', 'y', 'label', 'class', 'credit_risk',
        'g3', 'is_recid', 'is_recidivist', 'outcome', 'approved', 'loan_status'
    ]

    SENSITIVE_HINTS = [
        'sex', 'gender', 'race', 'age', 'ethnicity', 'ethical', 'marital',
        'school', 'relationship', 'native_country', 'disability', 'religion',
        'marital_status', 'custody', 'language', 'legal_status'
    ]

    def __init__(self, root_dir: str | None = None):
        self.root_dir = Path(root_dir) if root_dir else Path(__file__).resolve().parents[4]
        self.datasets: dict[str, pd.DataFrame] = {}
        self.metadata: dict[str, dict] = {}
        self._dataset_paths: dict[str, Path] = {}
        self._full_loaded: dict[str, bool] = {}
        self.refresh()

    def refresh(self):
        self.datasets.clear()
        self.metadata.clear()
        self._dataset_paths.clear()
        self._full_loaded.clear()
        self._load_all_datasets()

    def _dataset_files(self):
        ignore_parts = {'backend', 'frontend', 'node_modules', '.git', '__pycache__'}
        for path in self.root_dir.rglob('*.csv'):
            if any(part in ignore_parts for part in path.parts):
                continue
            if path.name.startswith('.'):
                continue
            yield path

    def _read_csv(self, path: Path, nrows: int | None = None):
        contents = path.read_bytes()
        encodings = ['utf-8', 'latin1', 'cp1252']
        delimiters = [',', ';', '	', '|']
        read_kwargs = {}
        if nrows is not None:
            read_kwargs['nrows'] = nrows

        for encoding in encodings:
            try:
                sample = contents[:4096].decode(encoding, errors='ignore')
                separator = None
                try:
                    separator = csv.Sniffer().sniff(sample, delimiters=delimiters).delimiter
                except Exception:
                    pass

                candidates = []
                if separator:
                    candidates.append(pd.read_csv(path, encoding=encoding, sep=separator, **read_kwargs))
                candidates.append(pd.read_csv(path, encoding=encoding, sep=None, engine='python', **read_kwargs))
                candidates.append(pd.read_csv(path, encoding=encoding, sep=';', **read_kwargs))
                candidates.append(pd.read_csv(path, encoding=encoding, sep=',', **read_kwargs))

                for frame in candidates:
                    if frame.shape[1] > 1:
                        return frame
            except Exception:
                continue

        return pd.read_csv(path, encoding='utf-8', encoding_errors='replace', sep=None, engine='python', **read_kwargs)

    def _normalize_column_names(self, df: pd.DataFrame, path: Path) -> pd.DataFrame:
        if df.shape[1] <= 1:
            return df
        if all(isinstance(col, str) for col in df.columns):
            return df
        stem = path.stem.lower()
        if stem.startswith('student-') and df.shape[1] == 33:
            df.columns = [
                'school', 'sex', 'age', 'address', 'famsize', 'Pstatus', 'Medu', 'Fedu',
                'Mjob', 'Fjob', 'reason', 'guardian', 'traveltime', 'studytime', 'failures',
                'schoolsup', 'famsup', 'paid', 'activities', 'nursery', 'higher', 'internet',
                'romantic', 'famrel', 'freetime', 'goout', 'Dalc', 'Walc', 'health',
                'absences', 'G1', 'G2', 'G3'
            ]
        return df

    def _matches_hint(self, column_name: str, hint: str):
        normalized = str(column_name).lower().replace('-', '_')
        tokens = [token for token in normalized.replace('__', '_').split('_') if token]
        if len(hint) <= 2:
            return normalized == hint or hint in tokens
        return normalized == hint or normalized.startswith(f'{hint}_') or normalized.endswith(f'_{hint}') or hint in tokens

    def _looks_like_identifier(self, column_name: str):
        normalized = str(column_name).lower().replace('-', '_')
        if normalized in {'id', 'idx', 'identifier'}:
            return True
        if normalized.endswith('id') or normalized.endswith('_id'):
            return True
        tokens = [token for token in normalized.replace('__', '_').split('_') if token]
        return 'id' in tokens

    def _count_rows(self, path: Path) -> int:
        try:
            with path.open('r', encoding='utf-8', errors='ignore') as reader:
                return max(sum(1 for _ in reader) - 1, 0)
        except Exception:
            return 0

    def _pick_target_column(self, df: pd.DataFrame):
        columns = list(df.columns)
        sensitive_like = {
            col for col in columns
            if any(self._matches_hint(col, hint) for hint in self.SENSITIVE_HINTS)
        }
        identifier_like = {col for col in columns if self._looks_like_identifier(col)}

        for hint in self.TARGET_HINTS:
            for col in columns:
                if col in sensitive_like or col in identifier_like:
                    continue
                if self._matches_hint(col, hint) and df[col].nunique(dropna=True) > 1:
                    return col, f"Matched target hint '{hint}'"

        binary_candidates = []
        low_cardinality = []
        for col in columns:
            if col in sensitive_like or col in identifier_like:
                continue
            count = df[col].nunique(dropna=True)
            if count <= 1:
                continue
            if count == 2:
                binary_candidates.append(col)
            elif count <= 10:
                low_cardinality.append((count, col))

        if binary_candidates:
            return binary_candidates[0], 'Selected binary target candidate'
        if low_cardinality:
            low_cardinality.sort(key=lambda item: item[0])
            return low_cardinality[0][1], f"Selected low-cardinality target candidate with {low_cardinality[0][0]} unique values"

        for col in columns:
            if col in sensitive_like or col in identifier_like:
                continue
            if df[col].nunique(dropna=True) > 1:
                return col, 'Selected first non-constant column as target'

        return columns[0] if columns else None, 'Fallback target selection'

    def _pick_sensitive_columns(self, df: pd.DataFrame, target_col: str | None):
        columns = [col for col in df.columns if col != target_col]
        selected = []
        for hint in self.SENSITIVE_HINTS:
            for col in columns:
                if self._matches_hint(col, hint) and col not in selected:
                    selected.append(col)
        if selected:
            return selected[:2], f"Matched sensitive hints: {selected[:2]}"

        categorical = []
        for col in columns:
            unique_count = df[col].nunique(dropna=True)
            if unique_count <= max(2, min(10, len(df) // 10)):
                categorical.append((unique_count, col))
        categorical.sort(key=lambda item: item[0])
        fallback = [col for _, col in categorical[:2]]
        if fallback:
            return fallback, f"Selected low-cardinality sensitive attributes: {fallback}"

        return [], 'No sensitive attribute candidates found'

    def _describe_dataset(self, path: Path, df: pd.DataFrame):
        target_col, target_reason = self._pick_target_column(df)
        sensitive_cols, sensitive_reason = self._pick_sensitive_columns(df, target_col)
        categorical_columns = df.select_dtypes(include=['object', 'category']).columns.tolist()
        numerical_columns = df.select_dtypes(include=['number']).columns.tolist()
        row_count = self._count_rows(path)

        return {
            'dataset_id': path.relative_to(self.root_dir).as_posix(),
            'name': path.stem,
            'filename': path.name,
            'path': str(path.relative_to(self.root_dir)),
            'shape': tuple(df.shape),
            'rows': int(row_count or df.shape[0]),
            'columns': int(df.shape[1]),
            'column_names': list(df.columns),
            'categorical_columns': categorical_columns,
            'numerical_columns': numerical_columns,
            'target': target_col,
            'target_reason': target_reason,
            'target_candidates': [target_col] if target_col else [],
            'sensitive': sensitive_cols,
            'sensitive_reason': sensitive_reason,
            'description': f"Automatically discovered dataset from {path.parent.name}",
        }

    def _load_all_datasets(self):
        logger.info(f'Scanning dataset folder {self.root_dir}')
        for path in self._dataset_files():
            try:
                dataset_id = path.relative_to(self.root_dir).as_posix()
                sample_frame = self._read_csv(path, nrows=1000)
                sample_frame = self._normalize_column_names(sample_frame, path)
                metadata = self._describe_dataset(path, sample_frame)
                self._dataset_paths[dataset_id] = path
                self._full_loaded[dataset_id] = False
                self.datasets[dataset_id] = sample_frame
                self.metadata[dataset_id] = metadata
                logger.info(f"Loaded metadata for {dataset_id}: {metadata['shape']}")
            except Exception as exc:
                logger.error(f'Failed to load {path}: {exc}')

    def get_dataset(self, name: str):
        if name not in self._dataset_paths:
            return None
        if self._full_loaded.get(name):
            return self.datasets.get(name)
        path = self._dataset_paths[name]
        try:
            df = self._read_csv(path)
            df = self._normalize_column_names(df, path)
            self.datasets[name] = df
            self._full_loaded[name] = True
            logger.info(f'Loaded full dataset {name}: shape={df.shape}')
            return df
        except Exception as exc:
            logger.error(f'Failed to load full dataset {path}: {exc}')
            return self.datasets.get(name)

    def get_metadata(self, name: str):
        return self.metadata.get(name)

    def list_datasets(self):
        return list(self.metadata.keys())

    def get_all_metadata(self):
        return self.metadata


_loader_instance = None


def get_loader():
    global _loader_instance
    if _loader_instance is None:
        _loader_instance = FolderDatasetLoader()
    return _loader_instance

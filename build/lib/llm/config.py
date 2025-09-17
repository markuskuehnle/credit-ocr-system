"""
Document configuration loading and management.
"""

import json
from typing import Dict, List, Any
from dataclasses import dataclass


@dataclass
class DocumentTypeConfig:
    """Configuration for a specific document type."""
    name: str
    expected_fields: List[str]
    field_descriptions: Dict[str, str]
    validation_rules: Dict[str, Any]


def load_document_config(config_path: str) -> Dict[str, DocumentTypeConfig]:
    """
    Load document configuration from JSON file.
    
    Args:
        config_path: Path to the configuration file
        
    Returns:
        Dictionary mapping document type names to DocumentTypeConfig objects
    """
    with open(config_path, 'r', encoding='utf-8') as f:
        config_data = json.load(f)

    document_types = {}
    for doc_type, doc_config in config_data.items():
        document_types[doc_type] = DocumentTypeConfig(
            name=doc_config['name'],
            expected_fields=doc_config['expected_fields'],
            field_descriptions=doc_config['field_descriptions'],
            validation_rules=doc_config['validation_rules'],
        )

    return document_types

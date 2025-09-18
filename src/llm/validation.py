import re
from typing import Dict, Any
from .config import DocumentTypeConfig


def validate_field(value: Any, rules: Dict[str, Any]) -> Dict[str, Any]:
    """
    Validate a field value against validation rules.
    
    Args:
        value: Field value to validate
        rules: Validation rules dictionary
        
    Returns:
        Validation result with is_valid flag and errors list
    """
    validation_result = {
        "is_valid": True,
        "errors": []
    }
    
    if not isinstance(value, dict) or "value" not in value:
        validation_result["is_valid"] = False
        validation_result["errors"].append("Invalid field format")
        return validation_result
    
    field_value = value["value"]
    
    # Type validation
    if "type" in rules:
        expected_type = rules["type"]
        if expected_type == "number":
            try:
                # Handle German number format (1.234,56)
                if isinstance(field_value, str):
                    field_value = field_value.replace(".", "").replace(",", ".")
                float(field_value)
            except (ValueError, TypeError):
                validation_result["is_valid"] = False
                validation_result["errors"].append(f"Value must be a number")
        elif expected_type == "boolean":
            if str(field_value).lower() not in ["true", "false"]:
                validation_result["is_valid"] = False
                validation_result["errors"].append(f"Value must be a boolean")
        elif expected_type == "date":
            # Skip number validation for dates
            pass
    
    # Range validation (only for numbers)
    if "min" in rules and "type" in rules and rules["type"] == "number":
        try:
            if isinstance(field_value, str):
                field_value = field_value.replace(".", "").replace(",", ".")
            if float(field_value) < rules["min"]:
                validation_result["is_valid"] = False
                validation_result["errors"].append(f"Value must be at least {rules['min']}")
        except (ValueError, TypeError):
            pass
    
    if "max" in rules and "type" in rules and rules["type"] == "number":
        try:
            if isinstance(field_value, str):
                field_value = field_value.replace(".", "").replace(",", ".")
            if float(field_value) > rules["max"]:
                validation_result["is_valid"] = False
                validation_result["errors"].append(f"Value must be at most {rules['max']}")
        except (ValueError, TypeError):
            pass
    
    # Pattern validation
    if "pattern" in rules:
        if not re.match(rules["pattern"], str(field_value)):
            validation_result["is_valid"] = False
            validation_result["errors"].append(f"Value does not match required pattern")
    
    return validation_result


def validate_extracted_fields(fields: Dict[str, Any], doc_config: DocumentTypeConfig) -> Dict[str, Any]:
    """
    Validate all extracted fields against their validation rules.
    
    Args:
        fields: Dictionary of extracted fields
        doc_config: Document type configuration with validation rules
        
    Returns:
        Dictionary of validation results for each field
    """
    validation_results = {}
    for field_name, field_data in fields.items():
        if field_name in doc_config.validation_rules:
            validation_results[field_name] = validate_field(field_data, doc_config.validation_rules[field_name])
    return validation_results

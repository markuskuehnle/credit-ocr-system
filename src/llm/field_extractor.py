"""
LLM-based field extraction from OCR results.
"""

import json
import re
from typing import Dict, List, Any
from .config import DocumentTypeConfig


def clean_value(value: str, field_type: str) -> Any:
    """
    Clean and convert value based on field type.
    
    Args:
        value: Raw value string
        field_type: Type of field (string, date, currency, etc.)
        
    Returns:
        Cleaned and converted value
    """
    if not value:
        return None

    if field_type == "string":
        return value.strip()
    
    elif field_type == "date":
        # Ensure date format DD.MM.YYYY
        if re.match(r"^\d{2}\.\d{2}\.\d{4}$", value):
            return value
        return None
    
    elif field_type == "currency":
        # Remove currency symbols, spaces, and convert comma to dot
        cleaned = value.replace("€", "").replace(" ", "").replace(",", ".")
        # Remove any non-numeric characters except decimal point
        cleaned = ''.join(c for c in cleaned if c.isdigit() or c == '.')
        return float(cleaned) if cleaned else None
    
    elif field_type == "area":
        # Remove unit and spaces
        cleaned = value.replace("m²", "").replace(" ", "")
        return float(cleaned) if cleaned else None
    
    elif field_type == "number":
        # Remove any non-numeric characters
        cleaned = ''.join(c for c in value if c.isdigit())
        return int(cleaned) if cleaned else None
    
    elif field_type == "boolean":
        return "[x]" in value.lower()
    
    return value


def extract_json_from_response(response: str) -> Dict[str, Any]:
    """
    Extract JSON from LLM response, handling potential text prefixes and comments.
    
    Args:
        response: Raw LLM response text
        
    Returns:
        Parsed JSON dictionary
    """
    try:
        # Find JSON between code blocks if present
        if "```" in response:
            # Find the first code block
            start = response.find("```")
            if start != -1:
                # Skip the opening ```
                start = response.find("\n", start) + 1
                # Find the closing ```
                end = response.find("```", start)
                if end != -1:
                    response = response[start:end].strip()
        
        # Remove any comments
        lines = []
        for line in response.split('\n'):
            if '//' in line:
                line = line[:line.find('//')]
            lines.append(line)
        response = '\n'.join(lines)
        
        # Try to parse the JSON
        return json.loads(response)
    except json.JSONDecodeError as e:
        raise ValueError(f"Invalid JSON in response: {e}")


def create_extraction_prompt(ocr_lines: List[Dict[str, Any]], config: DocumentTypeConfig) -> str:
    """
    Create a prompt for field extraction.
    
    Args:
        ocr_lines: List of OCR lines with text and metadata
        config: Document type configuration
        
    Returns:
        Formatted prompt for the LLM
    """
    # Get field descriptions (attribute or dict)
    field_descs = (
        config.field_descriptions
        if hasattr(config, "field_descriptions")
        else config.get("field_descriptions", {})
    )

    # Format field descriptions: "<db_key>: <human label>"
    field_descriptions = [f"- {field}: {desc}" for field, desc in field_descs.items()]

    formatted_lines = []
    for line in ocr_lines:
        if line["type"] == "label_value":
            formatted_lines.append(f"{line['label']}: {line['value']}")
        elif line["type"] in ("text_line", "line"):
            formatted_lines.append(line["text"])

    # Construct the prompt
    prompt = f"""Extract the following fields from the document content below. Return a valid JSON object with the extracted fields.

Field Descriptions:
{chr(10).join(field_descriptions)}

Document Content:
{chr(10).join(formatted_lines)}

Instructions:
1. Return a valid JSON object with the extracted fields
2. Use the exact field names from the mappings above
3. Include only fields that are present in the document
4. For fields with units (e.g., years, currency), include the unit in the value
5. For boolean fields, return true/false
6. For dates, use the format DD.MM.YYYY
7. For numbers, include any units or currency symbols

Example response format:
{{
    "extracted_fields": {{
        "company_name": "DemoTech GmbH",
        "legal_form": "GmbH",
        "founding_date": "01.01.2020",
        "business_address": "Musterstraße 123, 12345 Berlin",
        "purchase_price": "€500.000",
        "term": "20 Years",
        "interest_rate": "3,5%"
    }},
    "missing_fields": ["website", "vat_id"],
    "validation_results": {{
        "company_name": {{"valid": true}},
        "legal_form": {{"valid": true}},
        "founding_date": {{"valid": true}}
    }}
}}

Please extract the fields from the document content above and return a JSON object in this format."""
    return prompt


async def extract_fields_with_llm(
    ocr_lines: List[Dict[str, Any]],
    doc_config: DocumentTypeConfig,
    llm_client,
    original_ocr_lines: List[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Extract fields from OCR lines using LLM.
    The LLM is only used to map OCR text to field names.
    Original OCR data (value, confidence, bounding box, page) is preserved.
    
    Args:
        ocr_lines: List of OCR lines with text and metadata
        doc_config: Document type configuration
        llm_client: LLM client for field extraction
        original_ocr_lines: Optional list of original OCR lines for reference
        
    Returns:
        Dictionary containing extracted fields, missing fields, and validation results
    """
    if not ocr_lines:
        return {
            "extracted_fields": {},
            "missing_fields": list(doc_config.expected_fields),
            "validation_results": {}
        }
        
    # Step 1: Let LLM map OCR text to field names
    prompt = create_extraction_prompt(ocr_lines, doc_config)
    response = await llm_client.generate(prompt)
    
    try:
        llm_result = extract_json_from_response(response)
    except ValueError as e:
        raise
        
    # Step 2: Process extracted fields
    extracted_fields = {}
    for field_name, field_data in llm_result.get("extracted_fields", {}).items():
        # Ensure field data is a dictionary
        if not isinstance(field_data, dict):
            field_data = {"value": field_data}
            
        # Ensure required keys exist
        if "value" not in field_data:
            field_data["value"] = None
            
        # Step 3: Find matching normalized label-value pair
        if field_data["value"] is not None:
            value_str = str(field_data["value"]).lower()
            
            # Get all possible labels for this field
            # Use the DB key and its human description as candidate labels
            df_field_names = []
            try:
                field_desc = doc_config.field_descriptions.get(field_name, "")
            except AttributeError:
                # If doc_config is a dict
                field_desc = (doc_config.get("field_descriptions", {}) or {}).get(field_name, "")
            df_field_names = [field_name.lower()]
            if field_desc:
                df_field_names.append(str(field_desc).lower())
            
            # First try to find a matching label-value pair
            matching_pair = None
            for line in ocr_lines:
                if line["type"] == "label_value":
                    line_label = line["label"].lower()
                    line_value = line["value"].lower()
                    
                    # Match if either the label or value matches
                    if (any(label in line_label for label in df_field_names) or 
                        value_str in line_value):
                        matching_pair = line
                        break
            
            if matching_pair:
                # Use the label-value pair's data directly
                extracted_fields[field_name] = {
                    "value": matching_pair["value"],
                    "confidence": matching_pair.get("confidence", 0.5),
                    "bounding_box": matching_pair.get("bounding_box"),
                    "page": matching_pair.get("page")
                }
            else:
                # If no matching pair found, try to find matching OCR line
                matching_line = None
                if original_ocr_lines:
                    for line in original_ocr_lines:
                        line_text = line["text"].lower()
                        
                        # Match if line contains either the value or any of the field's labels
                        if value_str in line_text or any(label in line_text for label in df_field_names):
                            matching_line = line
                            break
                
                if matching_line:
                    # Use the OCR line's data directly
                    extracted_fields[field_name] = {
                        "value": matching_line["text"],
                        "confidence": matching_line.get("confidence", 0.5),
                        "bounding_box": matching_line.get("bounding_box"),
                        "page": matching_line.get("page")
                    }
                else:
                    # If no matching line found, use LLM output with default confidence
                    extracted_fields[field_name] = {
                        "value": field_data["value"],
                        "confidence": 0.5
                    }
        else:
            # If no value provided, use LLM output with default confidence
            extracted_fields[field_name] = {
                "value": field_data["value"],
                "confidence": 0.5
            }
            
    # Step 4: Apply field mappings
    mapped_fields = extracted_fields
            
    # Step 5: Validate fields
    from .validation import validate_extracted_fields
    validation_results = validate_extracted_fields(mapped_fields, doc_config)
    
    # Prepare final result
    result = {
        "extracted_fields": mapped_fields,
        "missing_fields": llm_result.get("missing_fields", []),
        "validation_results": validation_results
    }
    
    return result

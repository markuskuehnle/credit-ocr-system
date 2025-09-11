import re
from typing import Dict, Any


def load_system_config() -> Dict[str, Any]:
    """
    Load system configuration from config file.
    
    Returns:
        Dictionary containing system configuration including LLM settings
    """
    with open("config/credit-ocr-system.conf", 'r') as f:
        content = f.read()
    
    llm_match = re.search(r'generative_llm\s*\{\s*url\s*=\s*"([^"]+)"\s*model_name\s*=\s*"([^"]+)"\s*\}', content, re.DOTALL)
    if llm_match:
        return {
            'llm': {
                'url': llm_match.group(1),
                'model_name': llm_match.group(2)
            }
        }
    return {}

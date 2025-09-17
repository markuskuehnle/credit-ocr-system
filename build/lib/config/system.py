import os
import re
from typing import Dict, Any


def load_system_config() -> Dict[str, Any]:
    """
    Load system configuration from config file with environment-aware adjustments.
    
    Returns:
        Dictionary containing system configuration including LLM settings
    """
    with open("config/credit-ocr-system.conf", 'r') as f:
        content = f.read()
    
    llm_match = re.search(r'generative_llm\s*\{\s*url\s*=\s*"([^"]+)"\s*model_name\s*=\s*"([^"]+)"\s*\}', content, re.DOTALL)
    if llm_match:
        base_url = llm_match.group(1)
        model_name = llm_match.group(2)
        
        # Make URL environment-aware
        is_in_docker = bool(
            os.environ.get("IN_DOCKER", "").strip() == "1" or os.path.exists("/.dockerenv")
        )
        
        # Allow explicit override
        ollama_url_env = os.environ.get("OLLAMA_URL", "").strip()
        if ollama_url_env:
            resolved_url = ollama_url_env
        elif is_in_docker:
            # In Docker, use the service name and correct port
            resolved_url = "http://ollama:11434"
        else:
            # Outside Docker, use the config file URL (likely localhost)
            resolved_url = base_url
        
        return {
            'llm': {
                'url': resolved_url,
                'model_name': model_name
            }
        }
    return {}

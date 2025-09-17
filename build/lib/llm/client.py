"""
LLM client implementations for field extraction.
"""

from abc import ABC, abstractmethod
import aiohttp
from typing import Dict, List, Any
from dataclasses import dataclass


@dataclass
class GenerativeLlm:
    """Configuration for generative LLM."""
    url: str
    model_name: str


class LLMClient(ABC):
    """Abstract base class for LLM clients."""
    
    @abstractmethod
    async def generate(self, prompt: str) -> str:
        """Generate a response from the LLM."""
        pass


class OllamaClient(LLMClient):
    """Client for Ollama LLM service."""
    
    def __init__(self, base_url: str, model_name: str):
        self.base_url = base_url.rstrip('/')
        self.model_name = model_name
        
    async def generate(self, prompt: str) -> str:
        """
        Generate a response from Ollama.
        
        Args:
            prompt: The input prompt for the LLM
            
        Returns:
            The generated response text
        """
        timeout = aiohttp.ClientTimeout(total=120)  # 2 minutes timeout
        async with aiohttp.ClientSession(timeout=timeout) as session:
            try:
                async with session.post(
                    f"{self.base_url}/api/generate",
                    json={
                        "model": self.model_name,
                        "prompt": prompt,
                        "stream": False
                    }
                ) as response:
                    if response.status != 200:
                        error_text = await response.text()
                        raise Exception(f"Ollama API error: {error_text}")
                    
                    result = await response.json()
                    return result.get("response", "")
                    
            except Exception as e:
                print("Error calling Ollama API")
                raise

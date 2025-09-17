"""
Blob storage operations for document processing stages.
"""

import os
import threading
from enum import Enum
from pathlib import PurePosixPath
from typing import Optional, Dict, Any
import json
from datetime import datetime

from azure.storage.blob import BlobServiceClient, BlobClient
from azure.core.exceptions import ResourceExistsError


class Stage(Enum):
    """Processing stages for credit documents."""
    RAW = "raw"
    OCR = "ocr"
    LLM = "llm"
    ANNOTATED = "annotated"


class BlobStorage:
    """Thread-safe singleton for blob storage operations."""
    
    _instance: Optional['BlobStorage'] = None
    _lock = threading.Lock()
    
    def __new__(cls):
        with cls._lock:
            if cls._instance is None:
                cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        if hasattr(self, '_initialized'):
            return
        
        # Initialize without connection string - will be loaded on first use
        self._connection_string = None
        self._blob_service_client = None
        
        # Track initialized containers
        self._initialized_containers = set()
        self._container_lock = threading.Lock()
        
        self._initialized = True
        print("BlobStorage initialized with multiple containers")
    
    @property
    def connection_string(self) -> str:
        """Resolve connection string, adapting to local or Docker environments."""
        if self._connection_string is None:
            # Allow explicit override first
            env_connection: Optional[str] = os.getenv('AZURE_STORAGE_CONNECTION_STRING')
            if env_connection:
                self._connection_string = env_connection
                return self._connection_string

            # Determine host for Azurite
            is_in_docker: bool = bool(
                os.environ.get("IN_DOCKER", "").strip() == "1" or os.path.exists("/.dockerenv")
            )
            azurite_host_env: str = os.environ.get("AZURITE_HOST", "").strip()
            azurite_host: str = azurite_host_env or ("azurite" if is_in_docker else "127.0.0.1")
            azurite_port: str = os.environ.get("AZURITE_BLOB_PORT", "10000").strip()

            account_name: str = os.environ.get("AZURE_ACCOUNT_NAME", "devstoreaccount1").strip()
            account_key: str = os.environ.get(
                "AZURE_ACCOUNT_KEY",
                "Eby8vdM02xNOcqFlqUwJPLlmEtlCDXJ1OUzFT50uSRZ6IFsuFq2UVErCz4I6tq/"
                "K1SZFPTOtr/KBHBeksoGMGw==",
            ).strip()

            resolved_connection: str = (
                "DefaultEndpointsProtocol=http;"
                f"AccountName={account_name};"
                f"AccountKey={account_key};"
                f"BlobEndpoint=http://{azurite_host}:{azurite_port}/devstoreaccount1;"
            )
            self._connection_string = resolved_connection

        return self._connection_string
    
    @property
    def blob_service_client(self) -> BlobServiceClient:
        """Get blob service client, initializing if needed."""
        if self._blob_service_client is None:
            self._blob_service_client = BlobServiceClient.from_connection_string(self.connection_string)
        return self._blob_service_client
    
    def _ensure_container_exists(self, container_name: str) -> None:
        """Ensure a specific container exists."""
        if container_name in self._initialized_containers:
            return
            
        with self._container_lock:
            if container_name in self._initialized_containers:
                return
                
            try:
                container_client = self.blob_service_client.get_container_client(container_name)
                container_client.create_container()
                print(f"Container '{container_name}' created successfully")
            except ResourceExistsError:
                print(f"Container '{container_name}' already exists")
            except Exception as e:
                print(f"Failed to create container '{container_name}': {e}")
                raise
            
            self._initialized_containers.add(container_name)
    
    def ensure_all_containers_ready(self) -> None:
        """Ensure all document containers are ready for use (for test setup)."""
        for stage in Stage:
            self._ensure_container_exists(stage.value)
    
    def blob_path(self, uuid: str, stage: Stage, ext: str) -> PurePosixPath:
        """
        Build blob path for a document at a specific stage.
        
        Args:
            uuid: Document UUID
            stage: Processing stage
            ext: File extension (e.g., '.pdf', '.json')
            
        Returns:
            PurePosixPath representing the blob path
        """
        if not ext.startswith('.'):
            ext = f'.{ext}'
        
        path = PurePosixPath(f"{uuid}{ext}")
        return path
    
    def blob_client(self, uuid: str, stage: Stage, ext: str) -> BlobClient:
        """
        Get blob client for a document at a specific stage.
        
        Args:
            uuid: Document UUID
            stage: Processing stage
            ext: File extension (e.g., '.pdf', '.json')
            
        Returns:
            BlobClient for the specified blob
        """
        container_name = stage.value
        self._ensure_container_exists(container_name)
        blob_path = self.blob_path(uuid, stage, ext)
        container_client = self.blob_service_client.get_container_client(container_name)
        return container_client.get_blob_client(str(blob_path))
    
    def upload_blob(self, uuid: str, stage: Stage, ext: str, data: bytes, overwrite: bool = True) -> None:
        """
        Upload data to a blob at a specific stage.
        
        Args:
            uuid: Document UUID
            stage: Processing stage
            ext: File extension
            data: Data to upload
            overwrite: Whether to overwrite existing blob
        """
        blob_client = self.blob_client(uuid, stage, ext)
        blob_client.upload_blob(data, overwrite=overwrite)
        print(f"Uploaded blob: {stage.value}/{self.blob_path(uuid, stage, ext)}")

    def upload_document_data(
        self, 
        uuid: str, 
        stage: Stage, 
        ext: str, 
        data: Dict[str, Any], 
        metadata: Optional[Dict[str, Any]] = None,
        overwrite: bool = True
    ) -> None:
        """
        Upload document data with standardized structure.
        
        Args:
            uuid: Document UUID
            stage: Processing stage
            ext: File extension
            data: The actual data to store
            metadata: Optional metadata
            overwrite: Whether to overwrite existing blob
        """
        standardized_data = {
            "document_uuid": uuid,
            "timestamp": datetime.now().isoformat(),
            "data": data,
            "metadata": metadata or {}
        }
        
        blob_data = json.dumps(standardized_data, indent=2, ensure_ascii=False).encode('utf-8')
        self.upload_blob(uuid, stage, ext, blob_data, overwrite)

    def download_document_data(self, uuid: str, stage: Stage, ext: str) -> Optional[Dict[str, Any]]:
        """
        Download and parse document data with standardized structure.
        
        Args:
            uuid: Document UUID
            stage: Processing stage
            ext: File extension
            
        Returns:
            Parsed document data dictionary or None if not found
        """
        blob_bytes = self.download_blob(uuid, stage, ext)
        if blob_bytes is None:
            return None
        
        try:
            return json.loads(blob_bytes.decode('utf-8'))
        except (json.JSONDecodeError, UnicodeDecodeError) as e:
            print(f"Failed to parse document data: {e}")
            return None
    
    def download_blob(self, uuid: str, stage: Stage, ext: str) -> Optional[bytes]:
        """
        Download data from a blob at a specific stage.
        
        Args:
            uuid: Document UUID
            stage: Processing stage
            ext: File extension
            
        Returns:
            Blob data as bytes or None if not found
        """
        try:
            blob_client = self.blob_client(uuid, stage, ext)
            blob_data = blob_client.download_blob()
            data = blob_data.readall()
            print(f"Downloaded blob: {stage.value}/{self.blob_path(uuid, stage, ext)}")
            return data
        except Exception as e:
            print(f"Failed to download blob {stage.value}/{self.blob_path(uuid, stage, ext)}: {e}")
            return None
    
    def blob_exists(self, uuid: str, stage: Stage, ext: str) -> bool:
        """
        Check if a blob exists at a specific stage.
        
        Args:
            uuid: Document UUID
            stage: Processing stage
            ext: File extension
            
        Returns:
            True if blob exists, False otherwise
        """
        try:
            blob_client = self.blob_client(uuid, stage, ext)
            blob_client.get_blob_properties()
            return True
        except Exception:
            return False
    
    def delete_blob(self, uuid: str, stage: Stage, ext: str) -> bool:
        """
        Delete a blob at a specific stage.
        
        Args:
            uuid: Document UUID
            stage: Processing stage
            ext: File extension
            
        Returns:
            True if blob was deleted, False if it didn't exist
        """
        try:
            blob_client = self.blob_client(uuid, stage, ext)
            blob_client.delete_blob()
            print(f"Deleted blob: {stage.value}/{self.blob_path(uuid, stage, ext)}")
            return True
        except Exception as e:
            print(f"Failed to delete blob {stage.value}/{self.blob_path(uuid, stage, ext)}: {e}")
            return False
    
    def list_blobs_in_stage(self, stage: Stage) -> list[str]:
        """
        List all blobs in a specific stage container.
        
        Args:
            stage: Processing stage
            
        Returns:
            List of blob names in the stage container
        """
        container_name = stage.value
        self._ensure_container_exists(container_name)
        container_client = self.blob_service_client.get_container_client(container_name)
        
        blob_names = []
        try:
            blob_list = container_client.list_blobs()
            for blob in blob_list:
                blob_names.append(blob.name)
            print(f"Found {len(blob_names)} blobs in container: {container_name}")
            return blob_names
        except Exception as e:
            print(f"Failed to list blobs in container {container_name}: {e}")
            return []


def get_storage() -> BlobStorage:
    """Get the singleton BlobStorage instance."""
    return BlobStorage()


def ensure_all_containers() -> None:
    """Ensure all document containers exist (for test setup)."""
    storage = get_storage()
    storage.ensure_all_containers_ready()

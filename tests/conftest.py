import pytest
import asyncio
import os
import subprocess
import time
import psycopg2
import redis
from azure.storage.blob import BlobServiceClient

# Set test environment variables
os.environ["API_DEBUG"] = "true"
os.environ["ENVIRONMENT"] = "testing"
os.environ["DATABASE_HOST"] = "localhost"
os.environ["REDIS_HOST"] = "localhost"
os.environ["ENABLE_BACKGROUND_PROCESSING"] = "true"


@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="session")
def docker_compose_environment():
    """Start Docker Compose services for testing and tear down after tests."""
    print("\nStarting Docker Compose services for testing...")
    
    # Start the required services
    services = ["postgres", "redis", "azurite"]
    
    try:
        # Start services
        subprocess.run(
            ["docker-compose", "up", "-d"] + services,
            check=True,
            capture_output=True,
            text=True
        )
        
        # Wait for services to be ready
        print("Waiting for services to be ready...")
        wait_for_services()
        
        print("All services are ready")
        yield
        
    finally:
        # Cleanup: Stop and remove containers
        print("\nCleaning up Docker Compose services...")
        subprocess.run(
            ["docker-compose", "down", "-v"],
            capture_output=True,
            text=True
        )
        print("Cleanup completed")


def wait_for_services(max_retries=30, delay=1):
    """Wait for all required services to be ready."""
    
    # Wait for PostgreSQL
    print("  Waiting for PostgreSQL...")
    for i in range(max_retries):
        try:
            conn = psycopg2.connect(
                host="localhost",
                port=5432,
                database="dms_meta",
                user="dms",
                password="dms"
            )
            conn.close()
            print("  PostgreSQL is ready")
            break
        except Exception:
            if i == max_retries - 1:
                raise RuntimeError("PostgreSQL did not start in time")
            time.sleep(delay)
    
    # Wait for Redis
    print("  Waiting for Redis...")
    for i in range(max_retries):
        try:
            r = redis.Redis(host="localhost", port=6379, db=0)
            r.ping()
            print("  Redis is ready")
            break
        except Exception:
            if i == max_retries - 1:
                raise RuntimeError("Redis did not start in time")
            time.sleep(delay)
    
    # Wait for Azurite
    print("  Waiting for Azurite...")
    for i in range(max_retries):
        try:
            connection_string = (
                "DefaultEndpointsProtocol=http;"
                "AccountName=devstoreaccount1;"
                "AccountKey=Eby8vdM02xNOcqFlqUwJPLlmEtlCDXJ1OUzFT50uSRZ6IFsuFq2UVErCz4I6tq/"
                "K1SZFPTOtr/KBHBeksoGMGw==;"
                "BlobEndpoint=http://localhost:10000/devstoreaccount1;"
            )
            blob_service_client = BlobServiceClient.from_connection_string(connection_string)
            blob_service_client.list_containers()
            print("  Azurite is ready")
            break
        except Exception:
            if i == max_retries - 1:
                raise RuntimeError("Azurite did not start in time")
            time.sleep(delay)


@pytest.fixture(scope="session")
def setup_test_database(docker_compose_environment):
    """Set up test database schema and initial data."""
    print("Setting up test database...")
    
    conn = psycopg2.connect(
        host="localhost",
        port=5432,
        database="dms_meta",
        user="dms",
        password="dms"
    )
    
    try:
        with conn.cursor() as cursor:
            # Create documents table if it doesn't exist
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS documents (
                    id VARCHAR(255) PRIMARY KEY,
                    filename VARCHAR(255),
                    file_path TEXT,
                    file_size BIGINT,
                    mime_type VARCHAR(100),
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    text_extraction_status VARCHAR(50) DEFAULT 'ready',
                    processing_status VARCHAR(50)
                );
            """)
            
            # Create extraction_jobs table if it doesn't exist  
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS extraction_jobs (
                    id VARCHAR(255) PRIMARY KEY,
                    document_id VARCHAR(255) REFERENCES documents(id),
                    status VARCHAR(50),
                    error_message TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    completed_at TIMESTAMP
                );
            """)
            
        conn.commit()
        print("Test database schema created")
        yield conn
        
    finally:
        # Clean up test data
        with conn.cursor() as cursor:
            cursor.execute("DELETE FROM extraction_jobs;")
            cursor.execute("DELETE FROM documents;")
        conn.commit()
        conn.close()
        print("Test database cleaned up")


@pytest.fixture(scope="session")
def setup_test_storage(docker_compose_environment):
    """Set up test blob storage containers."""
    print("Setting up test storage...")
    
    from src.storage.storage import get_storage
    from azure.storage.blob import BlobServiceClient
    from azure.core.exceptions import ResourceExistsError
    
    # Set up storage client
    storage_client = get_storage()
    storage_client.ensure_all_containers_ready()
    
    # Also create the "documents" container that DMS service needs
    connection_string = (
        "DefaultEndpointsProtocol=http;"
        "AccountName=devstoreaccount1;"
        "AccountKey=Eby8vdM02xNOcqFlqUwJPLlmEtlCDXJ1OUzFT50uSRZ6IFsuFq2UVErCz4I6tq/"
        "K1SZFPTOtr/KBHBeksoGMGw==;"
        "BlobEndpoint=http://localhost:10000/devstoreaccount1;"
    )
    blob_service_client = BlobServiceClient.from_connection_string(connection_string)
    
    try:
        container_client = blob_service_client.get_container_client("documents")
        container_client.create_container()
        print("  Documents container created")
    except ResourceExistsError:
        print("  Documents container already exists")
    
    print("Test storage containers created")
    yield storage_client
    
    # Storage containers will be cleaned up with docker-compose down


@pytest.fixture(autouse=True)
def clean_test_data(setup_test_database, setup_test_storage):
    """Clean test data before each test."""
    # Clean database
    with setup_test_database.cursor() as cursor:
        cursor.execute("DELETE FROM extraction_jobs;")
        cursor.execute("DELETE FROM documents;")
    setup_test_database.commit()
    
    # Clean storage containers (optional, could be expensive)
    # For now, we'll rely on unique document IDs per test
    
    yield
    
    # Post-test cleanup happens in the session-scoped fixtures

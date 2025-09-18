#!/usr/bin/env python3
"""
System-agnostic startup script for Credit OCR System.
Handles infrastructure startup, model downloads, and API launch.
"""

import os
import sys
import time
import subprocess
import platform
import signal
import logging
from pathlib import Path
from typing import List, Optional

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class CreditOCRStarter:
    """System-agnostic starter for Credit OCR System."""
    
    def __init__(self):
        self.project_root = Path(__file__).parent
        self.is_windows = platform.system() == "Windows"
        self.docker_compose_cmd = self._get_docker_compose_cmd()
        self.processes: List[subprocess.Popen] = []
        
    def _get_docker_compose_cmd(self) -> str:
        """Get the appropriate docker-compose command."""
        try:
            subprocess.run(["docker", "compose", "version"], 
                         capture_output=True, check=True)
            return "docker compose"
        except (subprocess.CalledProcessError, FileNotFoundError):
            try:
                subprocess.run(["docker-compose", "version"], 
                             capture_output=True, check=True)
                return "docker-compose"
            except (subprocess.CalledProcessError, FileNotFoundError):
                raise RuntimeError("Neither 'docker compose' nor 'docker-compose' found")
    
    def check_prerequisites(self) -> bool:
        """Check if Docker and Python are available."""
        try:
            # Check Docker
            subprocess.run(["docker", "--version"], 
                         capture_output=True, check=True)
            logger.info("Docker is available")
            
            # Check Python
            python_version = sys.version_info
            if python_version >= (3, 9):
                logger.info(f"Python {python_version.major}.{python_version.minor} is available")
            else:
                logger.error(f"Python 3.9+ required, found {python_version.major}.{python_version.minor}")
                return False
                
            return True
        except (subprocess.CalledProcessError, FileNotFoundError) as e:
            logger.error(f"Prerequisite check failed: {e}")
            return False
    
    def start_infrastructure(self) -> bool:
        """Start Docker Compose services, reusing existing containers when possible."""
        logger.info("Starting infrastructure services...")
        
        try:
            # Check for existing containers first
            check_cmd = f"{self.docker_compose_cmd} ps -q"
            check_result = subprocess.run(check_cmd, shell=True, cwd=self.project_root,
                                        capture_output=True, text=True)
            
            existing_containers = check_result.stdout.strip()
            if existing_containers:
                logger.info("Found existing containers, reusing them...")
                # Start existing containers that might be stopped
                cmd = f"{self.docker_compose_cmd} start"
                result = subprocess.run(cmd, shell=True, cwd=self.project_root,
                                      capture_output=True, text=True)
                
                # Then ensure all services are up (this will create missing ones)
                cmd = f"{self.docker_compose_cmd} up -d"
                result = subprocess.run(cmd, shell=True, cwd=self.project_root,
                                      capture_output=True, text=True)
            else:
                logger.info("No existing containers found, creating new ones...")
                # Start all services fresh
                cmd = f"{self.docker_compose_cmd} up -d"
                result = subprocess.run(cmd, shell=True, cwd=self.project_root,
                                      capture_output=True, text=True)
            
            if result.returncode != 0:
                logger.error(f"Failed to start services: {result.stderr}")
                return False
                
            logger.info("Infrastructure services started")
            return True
            
        except Exception as e:
            logger.error(f"Failed to start infrastructure: {e}")
            return False
    
    def wait_for_services(self, max_wait: int = 300) -> bool:
        """Wait for all services to be healthy."""
        logger.info("Waiting for services to be ready...")
        
        services = ["postgres", "redis", "azurite"]
        start_time = time.time()
        
        while time.time() - start_time < max_wait:
            try:
                # Check service health
                cmd = f"{self.docker_compose_cmd} ps --format json"
                result = subprocess.run(cmd, shell=True, cwd=self.project_root,
                                      capture_output=True, text=True)
                
                if result.returncode == 0:
                    healthy_services = []
                    for service in services:
                        status_cmd = f"{self.docker_compose_cmd} ps {service} --format json"
                        status_result = subprocess.run(status_cmd, shell=True, 
                                                     cwd=self.project_root,
                                                     capture_output=True, text=True)
                        if status_result.returncode == 0 and "running" in status_result.stdout.lower():
                            healthy_services.append(service)
                    
                    if len(healthy_services) >= len(services):
                        logger.info("Core services are ready")
                        return True
                
                time.sleep(5)
                logger.info(f"Waiting for services... ({int(time.time() - start_time)}s)")
                
            except Exception as e:
                logger.warning(f"Error checking service status: {e}")
                time.sleep(5)
        
        logger.warning("Services may not be fully ready, continuing anyway")
        return True
    
    def wait_for_ollama_model(self, max_wait: int = 600) -> bool:
        """Wait for Ollama model to be ready."""
        logger.info("Checking Ollama model availability...")
        
        start_time = time.time()
        model_status_logged = False
        
        while time.time() - start_time < max_wait:
            try:
                import requests
                response = requests.get('http://127.0.0.1:11435/api/tags', timeout=10)
                if response.status_code == 200:
                    models = response.json().get('models', [])
                    if any('llama3.1:8b' in m.get('name', '') for m in models):
                        logger.info("Ollama model (llama3.1:8b) is ready")
                        return True
                    else:
                        elapsed = int(time.time() - start_time)
                        if not model_status_logged and elapsed > 30:
                            # Check container logs to see if model already exists or is downloading
                            try:
                                logs_cmd = f"{self.docker_compose_cmd} logs ollama --tail 5"
                                logs_result = subprocess.run(logs_cmd, shell=True, cwd=self.project_root,
                                                           capture_output=True, text=True)
                                if "already exists" in logs_result.stdout:
                                    logger.info("Model already exists in volume, loading...")
                                elif "pulling" in logs_result.stdout.lower():
                                    logger.info("Downloading model llama3.1:8b (first time setup)...")
                                else:
                                    logger.info("Preparing model llama3.1:8b...")
                                model_status_logged = True
                            except:
                                logger.info(f"Waiting for model llama3.1:8b... ({elapsed}s)")
                        elif elapsed > 60 and elapsed % 30 == 0:
                            logger.info(f"Still waiting for model... ({elapsed}s)")
                else:
                    elapsed = int(time.time() - start_time)
                    if elapsed > 30 and elapsed % 30 == 0:
                        logger.info(f"Ollama service starting... ({elapsed}s)")
                
            except Exception as e:
                elapsed = int(time.time() - start_time)
                if elapsed > 30 and elapsed % 30 == 0:
                    logger.info(f"Waiting for Ollama service... ({elapsed}s)")
            
            time.sleep(5)
        
        logger.warning("Ollama model timeout, but continuing (model may still be initializing)")
        return True
    
    def start_celery_worker(self) -> bool:
        """Start Celery worker process."""
        logger.info("Starting Celery worker...")
        
        try:
            # Start Celery worker
            python_cmd = sys.executable
            celery_cmd = [python_cmd, "-m", "celery", "-A", "src.celery_app", 
                         "worker", "--loglevel=info", "--concurrency=2"]
            
            process = subprocess.Popen(
                celery_cmd,
                cwd=self.project_root,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL
            )
            
            self.processes.append(process)
            time.sleep(3)
            
            # Check if process is still running
            if process.poll() is None:
                logger.info("Celery worker started")
                return True
            else:
                logger.error("Celery worker failed to start")
                return False
                
        except Exception as e:
            logger.error(f"Failed to start Celery worker: {e}")
            return False
    
    def start_api(self) -> bool:
        """Start the FastAPI server using existing run_api.py."""
        logger.info("Starting Credit OCR API...")
        
        try:
            # Use the existing run_api.py script
            python_cmd = sys.executable
            api_cmd = [python_cmd, "run_api.py"]
            
            process = subprocess.Popen(
                api_cmd,
                cwd=self.project_root,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            
            self.processes.append(process)
            time.sleep(5)
            
            # Check if API is responding
            try:
                import requests
                response = requests.get('http://127.0.0.1:8000/api/v1/health', timeout=10)
                if response.status_code == 200:
                    logger.info("Credit OCR API is running")
                    return True
            except Exception:
                pass
            
            logger.error("API failed to start or is not responding")
            return False
            
        except Exception as e:
            logger.error(f"Failed to start API: {e}")
            return False
    
    def cleanup(self):
        """Clean up started processes."""
        logger.info("Cleaning up...")
        
        # Terminate Python processes
        for process in self.processes:
            try:
                if process.poll() is None:
                    process.terminate()
                    process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                process.kill()
            except Exception as e:
                logger.warning(f"Error cleaning up process: {e}")
    
    def run(self):
        """Run the complete startup sequence."""
        try:
            logger.info("Starting Credit OCR System...")
            
            # Check prerequisites
            if not self.check_prerequisites():
                return False
            
            # Start infrastructure
            if not self.start_infrastructure():
                return False
            
            # Wait for services
            if not self.wait_for_services():
                return False
            
            # Wait for Ollama model to be ready
            # The Docker Compose setup handles downloading automatically
            
            # Start Celery worker
            if not self.start_celery_worker():
                logger.warning("Celery worker failed to start, continuing anyway")
            
            # Start API
            if not self.start_api():
                return False
            
            # Wait for Ollama model to be ready (Docker handles the download)
            if self.wait_for_ollama_model():
                logger.info("Credit OCR System is fully ready!")
            else:
                logger.info("Credit OCR System is ready! (Ollama model may still be downloading)")
            
            logger.info("Web interface: http://127.0.0.1:8000/")
            logger.info("API docs: http://127.0.0.1:8000/docs")
            logger.info("Press Ctrl+C to stop the system")
            
            # Keep running until interrupted
            try:
                while True:
                    time.sleep(1)
                    # Check if processes are still running
                    for i, process in enumerate(self.processes):
                        if process.poll() is not None:
                            process_name = "Celery worker" if i == 0 else f"API server (PID: {process.pid})"
                            logger.error(f"{process_name} has stopped unexpectedly (exit code: {process.returncode})")
                            # Get some error output if available
                            try:
                                if process.stderr:
                                    stderr_output = process.stderr.read()
                                    if stderr_output:
                                        logger.error(f"Error output: {stderr_output}")
                            except:
                                pass
                            return False
            except KeyboardInterrupt:
                logger.info("Received interrupt signal")
                return True
                
        except Exception as e:
            logger.error(f"Startup failed: {e}")
            return False
        finally:
            self.cleanup()


def signal_handler(signum, frame):
    """Handle interrupt signals."""
    logger.info("Shutting down Credit OCR System...")
    sys.exit(0)


def main():
    """Main entry point."""
    # Set up signal handlers
    signal.signal(signal.SIGINT, signal_handler)
    if hasattr(signal, 'SIGTERM'):
        signal.signal(signal.SIGTERM, signal_handler)
    
    starter = CreditOCRStarter()
    success = starter.run()
    
    if success:
        logger.info("Credit OCR System stopped successfully")
        sys.exit(0)
    else:
        logger.error("Credit OCR System failed to start or run")
        sys.exit(1)


if __name__ == "__main__":
    main()

from celery import Celery
from src.config import AppConfig

# Load configuration
app_config = AppConfig()

# Create a Celery instance
celery_app = Celery(
    "credit_ocr",
    broker=app_config.redis.broker_url,
    backend=app_config.redis.result_backend,
    include=["src.tasks.pipeline_tasks"],
)

# Configuration from config files
celery_app.conf.update(
    task_serializer=app_config.redis.task_serializer,
    accept_content=app_config.redis.accept_content,
    result_serializer=app_config.redis.result_serializer,
    timezone=app_config.redis.timezone,
    enable_utc=app_config.redis.enable_utc,
    # Task routing and execution settings
    task_track_started=True,
    task_time_limit=30 * 60,  # 30 minutes
    task_soft_time_limit=25 * 60,  # 25 minutes
    worker_prefetch_multiplier=1,
    task_acks_late=True,
    worker_disable_rate_limits=False,
)

if __name__ == "__main__":
    celery_app.start()



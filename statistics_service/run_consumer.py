import os
import django
import logging
import sys

# Set Django settings module
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "statistics_service.settings")

# Initialize Django before any ORM/model access
django.setup()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)

from traffic_app.kafka_consumer import MLResultsConsumer

logger = logging.getLogger(__name__)

if __name__ == "__main__":
    logger.info("Starting Statistics Service Kafka Consumer...")

    try:
        consumer = MLResultsConsumer()
        consumer.start()
    except KeyboardInterrupt:
        logger.info("Consumer stopped by user")
    except Exception as e:
        logger.error(f"Consumer failed: {e}", exc_info=True)
        sys.exit(1)

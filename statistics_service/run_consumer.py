import os
import django
import asyncio

# Set Django settings module
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "statistics_service.settings")

# Initialize Django before any ORM/model access
django.setup()

from traffic_app.consumers import run_all_consumers

if __name__ == "__main__":
    asyncio.run(run_all_consumers())

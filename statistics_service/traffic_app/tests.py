from django.test import TestCase, override_settings
from rest_framework.test import APIClient
from unittest.mock import patch, AsyncMock
from .models import TrafficData
import json

TEST_DATABASE_SETTINGS = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': ':memory:',
    }
}


@override_settings(DATABASES=TEST_DATABASE_SETTINGS)
class TrafficDataTestCase(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user_id = 'user123'
        self.test_data = {
            'user_id': self.user_id,
            'jwt_token': 'some.jwt.token',
            'data_field': 'test_data'
        }

    @patch('traffic_app.consumers.AIOKafkaConsumer')
    def test_kafka_consumer_saves_data_correctly(self, mock_kafka_consumer):
        # Mock Kafka consumer
        mock_message = AsyncMock()
        mock_message.value = json.dumps(self.test_data).encode('utf-8')

        mock_consumer_instance = mock_kafka_consumer.return_value
        mock_consumer_instance.start = AsyncMock()
        mock_consumer_instance.stop = AsyncMock()
        mock_consumer_instance.__aiter__.return_value = [mock_message]

        # Run consumer method directly
        from traffic_app.consumers import consume_traffic_data
        import asyncio

        asyncio.run(consume_traffic_data())

        # Check if data is saved in DB
        self.assertTrue(TrafficData.objects.filter(user_id=self.user_id).exists())
        saved_data = TrafficData.objects.get(user_id=self.user_id)
        self.assertEqual(saved_data.data, self.test_data)

    def test_traffic_endpoint_returns_correct_data(self):
        # Pre-create traffic data
        TrafficData.objects.create(user_id=self.user_id, data=self.test_data)

        # Make GET request
        response = self.client.get(f'/api/traffic/{self.user_id}/')
        print("RESPONSE DATA:", response.data)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]['user_id'], self.user_id)
        self.assertEqual(response.data[0]['data'], self.test_data)

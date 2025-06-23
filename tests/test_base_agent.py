# ag-agents/tests/test_base_agent.py
# agents/base_agent.py
import unittest
from agents.base_agent import BaseAgent
from agents.weather_agent import WeatherAgent
import json

class TestBaseAgent(unittest.TestCase):
    def setUp(self):
        self.weather_agent = WeatherAgent()
    
    def test_agent_initialization(self):
        self.assertEqual(self.weather_agent.name, "Weather & Climate Agent")
        self.assertEqual(self.weather_agent.status, "ready")
        self.assertEqual(len(self.weather_agent.message_queue), 0)
    
    def test_message_receiving(self):
        test_message = {
            'sender': 'test_agent',
            'content': 'test message',
            'type': 'test'
        }
        
        result = self.weather_agent.receive_message(test_message)
        self.assertTrue(result)
        self.assertEqual(len(self.weather_agent.message_queue), 1)
    
    def test_status_reporting(self):
        status = self.weather_agent.get_status()
        self.assertIn('agent_id', status)
        self.assertIn('name', status)
        self.assertIn('status', status)
    
    def test_weather_data_fetch(self):
        weather_data = self.weather_agent.fetch_weather_data('gaborone')
        self.assertIn('location', weather_data)
        self.assertIn('temperature', weather_data)
        self.assertEqual(weather_data['location'], 'gaborone')

if __name__ == '__main__':
    unittest.main()
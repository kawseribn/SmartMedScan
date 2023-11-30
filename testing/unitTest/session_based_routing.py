from app import app
import unittest

class TestFlaskRoutes(unittest.TestCase):
    def setUp(self):
        app.config['TESTING'] = True
        self.client = app.test_client()

    def test_patient_home(self):
        response = self.client.get('/patient_home')
        self.assertEqual(response.status_code, 200)

    def test_doctors_list(self):
        response = self.client.get('/doctors_list')
        self.assertEqual(response.status_code, 200)

if __name__ == '__main__':
    unittest.main()

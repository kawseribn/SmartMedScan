import unittest
from app import app, register_user, username_exists
from unittest.mock import patch, MagicMock

class TestRegistration(unittest.TestCase):
    def setUp(self):
        app.config['TESTING'] = True
        self.client = app.test_client()

    @patch('app.register_user')
    @patch('app.username_exists')
    def test_registration_success(self, mock_username_exists, mock_register_user):
        mock_username_exists.return_value = False
        mock_register_user.return_value = True
        response = self.client.post('/register', data={
            'username': 'new_user',
            'password': 'password123',
            'role': 'user'
        })
        self.assertEqual(response.status_code, 302)
        self.assertIn('Location', response.headers, '/login')

    @patch('app.username_exists')
    def test_registration_failure_due_to_duplicate_username(self, mock_username_exists):
        mock_username_exists.return_value = True

        response = self.client.post('/register', data={
            'username': 'existing_user',
            'password': 'password123',
            'role': 'user'
        })
        self.assertIn(b'Username already exists', response.data) 
        self.assertEqual(response.status_code, 200) 
if __name__ == '__main__':
    unittest.main()

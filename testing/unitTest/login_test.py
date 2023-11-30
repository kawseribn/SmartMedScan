import unittest
from app import app, check_user
from unittest.mock import patch

class TestLogin(unittest.TestCase):
    def setUp(self):
        app.config['TESTING'] = True
        self.client = app.test_client()

    @patch('app.check_user')
    def test_login_success(self, mock_check_user):
        mock_check_user.return_value = {'id': 1, 'username': 'testuser', 'role': 'patient'}
        with self.client as c:
            response = c.post('/login', data={'username': 'testuser', 'password': 'password'})
            self.assertEqual(response.status_code, 302)
            self.assertIn('Location', response.headers, '/patient_home')
            with c.session_transaction() as sess:
                self.assertEqual(sess['username'], 'testuser')

    @patch('app.check_user')
    def test_login_failure(self, mock_check_user):
        # Return None to simulate invalid credentials
        mock_check_user.return_value = None

        response = self.client.post('/login', data={'username': 'wronguser', 'password': 'wrongpass'})
        self.assertIn(b'Invalid username or password', response.data)
        self.assertEqual(response.status_code, 200)


if __name__ == '__main__':
    unittest.main()

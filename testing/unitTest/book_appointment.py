import unittest
from app import app
from unittest.mock import patch

class TestBookAppointment(unittest.TestCase):
    def setUp(self):
        self.client = app.test_client()
        app.config['TESTING'] = True

    @patch('app.get_db_connection')
    def test_book_appointment(self, mock_db):
        # Mock the session and database connection
        with self.client as client, client.session_transaction() as sess:
            sess['user_id'] = 1  # Example user ID
            mock_db.return_value.cursor.return_value.execute.return_value = None

            response = client.post('/book_appointment', data={'time_slot': '10:00', 'doctor_id': 2})
            self.assertEqual(response.status_code, 302)  # Redirect indicates success

if __name__ == '__main__':
    unittest.main()

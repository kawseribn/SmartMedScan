import unittest
import os
import io
from app import app
from unittest.mock import patch

class TestImageUpload(unittest.TestCase):
    def setUp(self):
        app.config['TESTING'] = True
        self.client = app.test_client()

    def test_image_upload(self):
        # Mock image file
        data = {'image': (io.BytesIO(b'test image data'), 'test.jpg')}
        response = self.client.post('/upload_route', content_type='multipart/form-data', data=data)
        self.assertEqual(response.status_code, 200)  # Check for successful upload response

    def test_invalid_file_type(self):
        # Mock non-image file
        data = {'image': (io.BytesIO(b'test data'), 'test.txt')}
        response = self.client.post('/upload_route', content_type='multipart/form-data', data=data)
        self.assertIn('Invalid file format', response.get_data(as_text=True))  # Check for file type error

if __name__ == '__main__':
    unittest.main()

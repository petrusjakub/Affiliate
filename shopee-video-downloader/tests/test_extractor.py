"""
Unit Tests untuk Shopee Video Extractor

Menggunakan unittest dan unittest.mock untuk testing tanpa akses jaringan.
"""

import unittest
import json
import sys
import os
from unittest.mock import patch, MagicMock, Mock
from urllib.error import HTTPError, URLError

# Tambahkan parent directory ke path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from extractor import (
    is_valid_shopee_url,
    extract_video_id,
    resolve_short_url,
    fetch_video_info,
    parse_video_response,
    extract_video,
    InvalidURLError,
    NetworkError,
    VideoNotFoundError,
    ExtractionError,
)


class TestIsValidShopeeUrl(unittest.TestCase):
    """Test validasi URL Shopee."""
    
    def test_valid_standard_url(self):
        """URL video standar harus valid."""
        self.assertTrue(is_valid_shopee_url('https://shopee.co.id/video/12345'))
    
    def test_valid_universal_link(self):
        """URL universal-link harus valid."""
        self.assertTrue(is_valid_shopee_url('https://shopee.co.id/universal-link/video/67890'))
    
    def test_valid_short_link(self):
        """Short link harus valid."""
        self.assertTrue(is_valid_shopee_url('https://s.shopee.co.id/abc123'))
    
    def test_valid_http_url(self):
        """URL dengan http (tanpa s) harus valid."""
        self.assertTrue(is_valid_shopee_url('http://shopee.co.id/video/12345'))
    
    def test_valid_other_country_domain(self):
        """URL dengan domain negara lain harus valid."""
        self.assertTrue(is_valid_shopee_url('https://shopee.com.my/video/12345'))
        self.assertTrue(is_valid_shopee_url('https://shopee.sg/video/12345'))
        self.assertTrue(is_valid_shopee_url('https://shopee.ph/video/12345'))
    
    def test_valid_url_with_whitespace(self):
        """URL dengan whitespace di sekitarnya harus valid."""
        self.assertTrue(is_valid_shopee_url('  https://shopee.co.id/video/12345  '))
    
    def test_invalid_empty_string(self):
        """String kosong tidak valid."""
        self.assertFalse(is_valid_shopee_url(''))
    
    def test_invalid_none(self):
        """None tidak valid."""
        self.assertFalse(is_valid_shopee_url(None))
    
    def test_invalid_random_url(self):
        """URL random bukan Shopee tidak valid."""
        self.assertFalse(is_valid_shopee_url('https://www.google.com'))
    
    def test_invalid_shopee_product_url(self):
        """URL produk Shopee (bukan video) tidak valid."""
        self.assertFalse(is_valid_shopee_url('https://shopee.co.id/product/12345'))
    
    def test_invalid_number_input(self):
        """Input bukan string tidak valid."""
        self.assertFalse(is_valid_shopee_url(12345))
    
    def test_invalid_youtube_url(self):
        """URL YouTube tidak valid."""
        self.assertFalse(is_valid_shopee_url('https://www.youtube.com/watch?v=12345'))


class TestExtractVideoId(unittest.TestCase):
    """Test ekstraksi Video ID dari URL."""
    
    def test_extract_from_standard_url(self):
        """Ekstrak ID dari URL standar."""
        self.assertEqual(
            extract_video_id('https://shopee.co.id/video/123456'),
            '123456'
        )
    
    def test_extract_from_universal_link(self):
        """Ekstrak ID dari universal-link."""
        self.assertEqual(
            extract_video_id('https://shopee.co.id/universal-link/video/789012'),
            '789012'
        )
    
    def test_extract_from_other_domain(self):
        """Ekstrak ID dari domain negara lain."""
        self.assertEqual(
            extract_video_id('https://shopee.sg/video/456789'),
            '456789'
        )
    
    def test_extract_long_id(self):
        """Ekstrak ID panjang."""
        self.assertEqual(
            extract_video_id('https://shopee.co.id/video/9876543210123'),
            '9876543210123'
        )
    
    def test_none_for_short_url(self):
        """Short URL tidak langsung memiliki video ID."""
        self.assertIsNone(extract_video_id('https://s.shopee.co.id/abc123'))
    
    def test_none_for_invalid_url(self):
        """URL invalid mengembalikan None."""
        self.assertIsNone(extract_video_id('https://google.com'))
    
    def test_none_for_empty(self):
        """String kosong mengembalikan None."""
        self.assertIsNone(extract_video_id(''))
    
    def test_none_for_none_input(self):
        """None input mengembalikan None."""
        self.assertIsNone(extract_video_id(None))


class TestResolveShortUrl(unittest.TestCase):
    """Test resolusi short URL."""
    
    @patch('extractor.urllib.request.build_opener')
    def test_resolve_redirect(self, mock_build_opener):
        """Short URL yang redirect harus di-resolve."""
        # Simulasi HTTPError dengan redirect
        headers = MagicMock()
        headers.get.return_value = 'https://shopee.co.id/video/12345'
        
        mock_opener = MagicMock()
        error = HTTPError(
            'https://s.shopee.co.id/abc',
            302,
            'Found',
            headers,
            None
        )
        mock_opener.open.side_effect = error
        mock_build_opener.return_value = mock_opener
        
        result = resolve_short_url('https://s.shopee.co.id/abc123')
        self.assertEqual(result, 'https://shopee.co.id/video/12345')
    
    @patch('extractor.urllib.request.build_opener')
    def test_resolve_no_redirect(self, mock_build_opener):
        """URL tanpa redirect mengembalikan URL asli."""
        mock_opener = MagicMock()
        mock_response = MagicMock()
        mock_opener.open.return_value = mock_response
        mock_build_opener.return_value = mock_opener
        
        result = resolve_short_url('https://s.shopee.co.id/abc123')
        self.assertEqual(result, 'https://s.shopee.co.id/abc123')
    
    @patch('extractor.urllib.request.build_opener')
    def test_resolve_network_error(self, mock_build_opener):
        """Network error harus raise NetworkError."""
        mock_opener = MagicMock()
        mock_opener.open.side_effect = URLError('Connection refused')
        mock_build_opener.return_value = mock_opener
        
        with self.assertRaises(NetworkError):
            resolve_short_url('https://s.shopee.co.id/abc123')
    
    @patch('extractor.urllib.request.build_opener')
    def test_resolve_http_error_non_redirect(self, mock_build_opener):
        """HTTP error non-redirect harus raise NetworkError."""
        mock_opener = MagicMock()
        headers = MagicMock()
        error = HTTPError(
            'https://s.shopee.co.id/abc',
            500,
            'Server Error',
            headers,
            None
        )
        mock_opener.open.side_effect = error
        mock_build_opener.return_value = mock_opener
        
        with self.assertRaises(NetworkError):
            resolve_short_url('https://s.shopee.co.id/abc123')


class TestFetchVideoInfo(unittest.TestCase):
    """Test pengambilan info video dari API."""
    
    @patch('extractor.urllib.request.urlopen')
    def test_successful_fetch(self, mock_urlopen):
        """Berhasil mengambil info video."""
        api_response = {
            'data': {
                'video_info': {
                    'video_url': 'https://cdn.shopee.co.id/video/12345.mp4',
                    'thumbnail': 'https://cdn.shopee.co.id/thumb/12345.jpg',
                    'title': 'Video Produk Keren',
                    'duration': 120
                }
            }
        }
        
        mock_response = MagicMock()
        mock_response.read.return_value = json.dumps(api_response).encode('utf-8')
        mock_urlopen.return_value = mock_response
        
        result = fetch_video_info('12345')
        
        self.assertEqual(result['video_url'], 'https://cdn.shopee.co.id/video/12345.mp4')
        self.assertEqual(result['thumbnail'], 'https://cdn.shopee.co.id/thumb/12345.jpg')
        self.assertEqual(result['title'], 'Video Produk Keren')
        self.assertEqual(result['duration'], 120)
    
    @patch('extractor.urllib.request.urlopen')
    def test_fetch_404(self, mock_urlopen):
        """Video tidak ditemukan (404) harus raise VideoNotFoundError."""
        mock_urlopen.side_effect = HTTPError(
            'https://shopee.co.id/api/v4/video/get?video_id=99999',
            404,
            'Not Found',
            {},
            None
        )
        
        with self.assertRaises(VideoNotFoundError):
            fetch_video_info('99999')
    
    @patch('extractor.urllib.request.urlopen')
    def test_fetch_network_error(self, mock_urlopen):
        """URLError harus raise NetworkError."""
        mock_urlopen.side_effect = URLError('Connection timed out')
        
        with self.assertRaises(NetworkError):
            fetch_video_info('12345')
    
    @patch('extractor.urllib.request.urlopen')
    def test_fetch_invalid_json(self, mock_urlopen):
        """Response bukan JSON harus raise ExtractionError."""
        mock_response = MagicMock()
        mock_response.read.return_value = b'not json at all'
        mock_urlopen.return_value = mock_response
        
        with self.assertRaises(ExtractionError):
            fetch_video_info('12345')
    
    @patch('extractor.urllib.request.urlopen')
    def test_fetch_http_500(self, mock_urlopen):
        """HTTP 500 harus raise NetworkError."""
        mock_urlopen.side_effect = HTTPError(
            'https://shopee.co.id/api/v4/video/get?video_id=12345',
            500,
            'Internal Server Error',
            {},
            None
        )
        
        with self.assertRaises(NetworkError):
            fetch_video_info('12345')


class TestParseVideoResponse(unittest.TestCase):
    """Test parsing respons API video."""
    
    def test_parse_standard_response(self):
        """Parse respons standar dengan video_info."""
        data = {
            'data': {
                'video_info': {
                    'video_url': 'https://cdn.shopee.co.id/video.mp4',
                    'thumbnail': 'https://cdn.shopee.co.id/thumb.jpg',
                    'title': 'Test Video',
                    'duration': 60
                }
            }
        }
        
        result = parse_video_response(data, '12345')
        
        self.assertEqual(result['video_id'], '12345')
        self.assertEqual(result['video_url'], 'https://cdn.shopee.co.id/video.mp4')
        self.assertEqual(result['thumbnail'], 'https://cdn.shopee.co.id/thumb.jpg')
        self.assertEqual(result['title'], 'Test Video')
        self.assertEqual(result['duration'], 60)
    
    def test_parse_with_formats(self):
        """Parse respons dengan array formats."""
        data = {
            'data': {
                'video_info': {
                    'formats': [
                        {'url': 'https://cdn.shopee.co.id/720p.mp4', 'quality': '720p', 'width': 1280, 'height': 720},
                        {'url': 'https://cdn.shopee.co.id/480p.mp4', 'quality': '480p', 'width': 854, 'height': 480}
                    ],
                    'thumbnail': 'https://cdn.shopee.co.id/thumb.jpg',
                    'title': 'Format Test'
                }
            }
        }
        
        result = parse_video_response(data, '12345')
        
        self.assertEqual(len(result['formats']), 2)
        self.assertEqual(result['video_url'], 'https://cdn.shopee.co.id/720p.mp4')
        self.assertEqual(result['formats'][0]['quality'], '720p')
    
    def test_parse_with_play_url(self):
        """Parse respons dengan play_url."""
        data = {
            'video_info': {
                'play_url': 'https://cdn.shopee.co.id/play.mp4',
                'thumb_url': 'https://cdn.shopee.co.id/thumb.jpg'
            }
        }
        
        result = parse_video_response(data, '999')
        
        self.assertEqual(result['video_url'], 'https://cdn.shopee.co.id/play.mp4')
        self.assertEqual(result['thumbnail'], 'https://cdn.shopee.co.id/thumb.jpg')
    
    def test_parse_empty_response(self):
        """Respons tanpa video URL harus raise VideoNotFoundError."""
        data = {
            'data': {
                'video_info': {
                    'title': 'No URL Video'
                }
            }
        }
        
        with self.assertRaises(VideoNotFoundError):
            parse_video_response(data, '12345')
    
    def test_parse_default_title(self):
        """Jika tidak ada title, gunakan default."""
        data = {
            'data': {
                'video_info': {
                    'video_url': 'https://cdn.shopee.co.id/video.mp4'
                }
            }
        }
        
        result = parse_video_response(data, '55555')
        self.assertEqual(result['title'], 'Shopee Video 55555')
    
    def test_parse_duration_as_string(self):
        """Duration sebagai string harus di-convert ke int."""
        data = {
            'data': {
                'video_info': {
                    'video_url': 'https://cdn.shopee.co.id/video.mp4',
                    'duration': '90'
                }
            }
        }
        
        result = parse_video_response(data, '12345')
        self.assertEqual(result['duration'], 90)


class TestExtractVideo(unittest.TestCase):
    """Test fungsi utama extract_video."""
    
    def test_invalid_url_empty(self):
        """URL kosong harus raise InvalidURLError."""
        with self.assertRaises(InvalidURLError):
            extract_video('')
    
    def test_invalid_url_none(self):
        """URL None harus raise InvalidURLError."""
        with self.assertRaises(InvalidURLError):
            extract_video(None)
    
    def test_invalid_url_format(self):
        """URL format salah harus raise InvalidURLError."""
        with self.assertRaises(InvalidURLError):
            extract_video('https://www.youtube.com/watch?v=123')
    
    @patch('extractor.fetch_video_info')
    def test_extract_standard_url(self, mock_fetch):
        """Ekstraksi dari URL standar harus berhasil."""
        mock_fetch.return_value = {
            'video_id': '12345',
            'video_url': 'https://cdn.shopee.co.id/video.mp4',
            'thumbnail': 'https://cdn.shopee.co.id/thumb.jpg',
            'title': 'Test Video',
            'duration': 30,
            'formats': []
        }
        
        result = extract_video('https://shopee.co.id/video/12345')
        
        self.assertEqual(result['video_id'], '12345')
        self.assertEqual(result['video_url'], 'https://cdn.shopee.co.id/video.mp4')
        self.assertIn('download_url', result)
        mock_fetch.assert_called_once_with('12345')
    
    @patch('extractor.resolve_short_url')
    @patch('extractor.fetch_video_info')
    def test_extract_short_url(self, mock_fetch, mock_resolve):
        """Ekstraksi dari short URL harus resolve dulu."""
        mock_resolve.return_value = 'https://shopee.co.id/video/67890'
        mock_fetch.return_value = {
            'video_id': '67890',
            'video_url': 'https://cdn.shopee.co.id/video67890.mp4',
            'thumbnail': None,
            'title': 'Short URL Video',
            'duration': None,
            'formats': []
        }
        
        result = extract_video('https://s.shopee.co.id/abc123XYZ')
        
        mock_resolve.assert_called_once_with('https://s.shopee.co.id/abc123XYZ')
        mock_fetch.assert_called_once_with('67890')
        self.assertEqual(result['video_id'], '67890')
    
    @patch('extractor.resolve_short_url')
    def test_extract_short_url_resolve_failure(self, mock_resolve):
        """Short URL yang gagal resolve harus raise error."""
        mock_resolve.side_effect = NetworkError("Connection refused")
        
        with self.assertRaises(NetworkError):
            extract_video('https://s.shopee.co.id/abc123')
    
    @patch('extractor.fetch_video_info')
    def test_extract_network_error(self, mock_fetch):
        """Network error saat fetch harus propagate."""
        mock_fetch.side_effect = NetworkError("Timeout")
        
        with self.assertRaises(NetworkError):
            extract_video('https://shopee.co.id/video/12345')
    
    @patch('extractor.resolve_short_url')
    def test_extract_short_url_no_video_id(self, mock_resolve):
        """Short URL yang resolve ke non-video URL harus raise InvalidURLError."""
        mock_resolve.return_value = 'https://shopee.co.id/shop/somestore'
        
        with self.assertRaises(InvalidURLError):
            extract_video('https://s.shopee.co.id/abc123')


class TestServerIntegration(unittest.TestCase):
    """Test integrasi server (tanpa menjalankan server penuh)."""
    
    def test_server_module_imports(self):
        """Server module harus bisa di-import tanpa error."""
        import server
        self.assertTrue(hasattr(server, 'ShopeeVideoHandler'))
        self.assertTrue(hasattr(server, 'run_server'))
    
    def test_server_static_dir_exists(self):
        """Directory static harus ada."""
        import server
        self.assertTrue(os.path.isdir(server.STATIC_DIR))
    
    def test_server_index_html_exists(self):
        """File index.html harus ada di static directory."""
        import server
        index_path = os.path.join(server.STATIC_DIR, 'index.html')
        self.assertTrue(os.path.isfile(index_path))


if __name__ == '__main__':
    unittest.main()

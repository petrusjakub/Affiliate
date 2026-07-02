"""
Unit Tests untuk Shopee Video Extractor

Menggunakan unittest dan unittest.mock untuk testing tanpa akses jaringan.
"""

import unittest
import json
import ssl
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


class TestIsAllowedDownloadDomain(unittest.TestCase):
    """Test domain allowlist for the download proxy (SSRF protection)."""
    
    def test_allowed_static_domain(self):
        """Known Shopee CDN domains should be allowed."""
        import server
        self.assertTrue(server.is_allowed_download_domain('cf.shopee.co.id'))
        self.assertTrue(server.is_allowed_download_domain('cv.shopee.co.id'))
        self.assertTrue(server.is_allowed_download_domain('cf.shopee.sg'))
    
    def test_allowed_dynamic_pattern(self):
        """Dynamic CDN subdomains matching patterns should be allowed."""
        import server
        self.assertTrue(server.is_allowed_download_domain('down-id.susercontent.com'))
        self.assertTrue(server.is_allowed_download_domain('media-sg.susercontent.com'))
        self.assertTrue(server.is_allowed_download_domain('cdn-01.shopee.co.id'))
    
    def test_disallowed_internal_ip(self):
        """Internal network IPs should not be allowed."""
        import server
        self.assertFalse(server.is_allowed_download_domain('169.254.169.254'))
        self.assertFalse(server.is_allowed_download_domain('127.0.0.1'))
        self.assertFalse(server.is_allowed_download_domain('10.0.0.1'))
    
    def test_disallowed_external_domain(self):
        """External non-Shopee domains should not be allowed."""
        import server
        self.assertFalse(server.is_allowed_download_domain('evil.com'))
        self.assertFalse(server.is_allowed_download_domain('google.com'))
        self.assertFalse(server.is_allowed_download_domain('attacker.shopee.co.id.evil.com'))
    
    def test_case_insensitive(self):
        """Domain check should be case-insensitive."""
        import server
        self.assertTrue(server.is_allowed_download_domain('CF.SHOPEE.CO.ID'))
        self.assertTrue(server.is_allowed_download_domain('Down-ID.Susercontent.Com'))
    
    def test_disallowed_empty(self):
        """Empty hostname should not be allowed."""
        import server
        self.assertFalse(server.is_allowed_download_domain(''))


class TestServerHandler(unittest.TestCase):
    """Test server HTTP handler routing, path traversal defense, and proxy behavior."""

    def setUp(self):
        """Set up mock handler for testing."""
        import server
        self.server_module = server
        # Create a mock handler that can be tested without a real socket
        self.handler = self._create_mock_handler()

    def _create_mock_handler(self):
        """Create a ShopeeVideoHandler instance with mocked socket/IO."""
        import server
        import io
        handler = object.__new__(server.ShopeeVideoHandler)
        handler.wfile = io.BytesIO()
        handler.rfile = io.BytesIO()
        handler.requestline = ''
        handler.client_address = ('127.0.0.1', 12345)
        handler.request_version = 'HTTP/1.1'
        handler.headers = {}
        handler.responses = {}
        handler._headers_buffer = []
        # Capture sent responses
        handler._sent_responses = []
        handler._sent_headers = []
        
        original_send_response = handler.send_response
        def mock_send_response(code, message=None):
            handler._sent_responses.append(code)
        handler.send_response = mock_send_response
        
        original_send_header = handler.send_header
        def mock_send_header(keyword, value):
            handler._sent_headers.append((keyword, value))
        handler.send_header = mock_send_header
        
        handler.end_headers = lambda: None
        handler.log_message = lambda format, *args: None
        
        return handler

    def test_get_root_serves_index(self):
        """GET / should serve index.html."""
        import server
        handler = self._create_mock_handler()
        handler.path = '/'
        
        # The serve_static method should be called and serve index.html
        with patch.object(handler, 'serve_static') as mock_serve:
            handler.do_GET()
            mock_serve.assert_called_once_with('/')

    def test_get_api_download_routes_to_handler(self):
        """GET /api/download should route to handle_download."""
        import server
        handler = self._create_mock_handler()
        handler.path = '/api/download?url=http://test.com'
        
        with patch.object(handler, 'handle_download') as mock_download:
            handler.do_GET()
            mock_download.assert_called_once()

    def test_post_api_extract_routes_to_handler(self):
        """POST /api/extract should route to handle_extract."""
        import server
        handler = self._create_mock_handler()
        handler.path = '/api/extract'
        
        with patch.object(handler, 'handle_extract') as mock_extract:
            handler.do_POST()
            mock_extract.assert_called_once()

    def test_post_unknown_returns_404(self):
        """POST to unknown path should return 404 error."""
        import server
        handler = self._create_mock_handler()
        handler.path = '/api/unknown'
        
        with patch.object(handler, 'send_error_json') as mock_error:
            handler.do_POST()
            mock_error.assert_called_once_with("Endpoint tidak ditemukan", 404)

    def test_path_traversal_dotdot_rejected(self):
        """Path traversal with .. should be rejected."""
        import server
        handler = self._create_mock_handler()
        
        with patch.object(handler, 'send_error_json') as mock_error:
            handler.serve_static('/../../../etc/passwd')
            mock_error.assert_called_with("Akses ditolak", 403)

    def test_path_traversal_absolute_rejected(self):
        """Absolute paths should be rejected by path traversal check."""
        import server
        handler = self._create_mock_handler()
        
        with patch.object(handler, 'send_error_json') as mock_error:
            # The normpath of something like '//etc/passwd' on Unix is '/etc/passwd' which is absolute
            handler.serve_static('//etc/passwd')
            mock_error.assert_called_with("Akses ditolak", 403)

    def test_download_proxy_rejects_disallowed_domain(self):
        """Download proxy should reject URLs not on the allowlist."""
        import server
        handler = self._create_mock_handler()
        
        with patch.object(handler, 'send_error_json') as mock_error:
            handler.handle_download('url=http%3A%2F%2F169.254.169.254%2Flatest%2Fmeta-data%2F')
            mock_error.assert_called()
            call_args = mock_error.call_args
            self.assertIn('403', str(call_args) or '')
            # Check that the error message references domain restriction
            self.assertIn("Domain tidak diizinkan", call_args[0][0])

    def test_download_proxy_rejects_empty_url(self):
        """Download proxy should return error when url param is missing."""
        import server
        handler = self._create_mock_handler()
        
        with patch.object(handler, 'send_error_json') as mock_error:
            handler.handle_download('')
            mock_error.assert_called_with("Parameter 'url' diperlukan")

    def test_download_proxy_rejects_non_http_scheme(self):
        """Download proxy should reject file:// and ftp:// schemes."""
        import server
        handler = self._create_mock_handler()
        
        with patch.object(handler, 'send_error_json') as mock_error:
            handler.handle_download('url=file%3A%2F%2F%2Fetc%2Fpasswd')
            mock_error.assert_called()
            self.assertIn("tidak diizinkan", mock_error.call_args[0][0])

    def test_download_proxy_rejects_oversized_content(self):
        """Download proxy should reject responses exceeding MAX_DOWNLOAD_SIZE."""
        import server
        handler = self._create_mock_handler()
        
        # Mock urlopen to return a response with huge Content-Length
        mock_response = MagicMock()
        mock_response.headers = {'Content-Type': 'video/mp4', 'Content-Length': '999999999999'}
        mock_response.close = MagicMock()
        
        with patch.object(handler, 'send_error_json') as mock_error:
            with patch('server.urllib.request.urlopen', return_value=mock_response):
                handler.handle_download('url=https%3A%2F%2Fcf.shopee.co.id%2Fvideo.mp4')
                mock_error.assert_called()
                self.assertEqual(mock_error.call_args[0][1], 413)

    def test_download_proxy_allows_shopee_cdn(self):
        """Download proxy should allow URLs from Shopee CDN domains."""
        import server
        handler = self._create_mock_handler()
        
        mock_response = MagicMock()
        mock_response.headers = {'Content-Type': 'video/mp4', 'Content-Length': '1024'}
        mock_response.read = MagicMock(side_effect=[b'x' * 1024, b''])
        
        with patch('server.urllib.request.urlopen', return_value=mock_response):
            handler.handle_download('url=https%3A%2F%2Fcf.shopee.co.id%2Fvideo%2F12345.mp4')
            # Should have sent 200 response
            self.assertIn(200, handler._sent_responses)

    def test_download_proxy_ssl_verification_enabled(self):
        """Download proxy should use SSL context with verification enabled."""
        import server
        handler = self._create_mock_handler()
        
        mock_response = MagicMock()
        mock_response.headers = {'Content-Type': 'video/mp4', 'Content-Length': '100'}
        mock_response.read = MagicMock(side_effect=[b'x' * 100, b''])
        
        captured_ctx = []
        
        def mock_urlopen(req, timeout=None, context=None):
            captured_ctx.append(context)
            return mock_response
        
        with patch('server.urllib.request.urlopen', side_effect=mock_urlopen):
            handler.handle_download('url=https%3A%2F%2Fcf.shopee.co.id%2Fvideo.mp4')
        
        # The SSL context should have verification enabled (default behavior)
        self.assertEqual(len(captured_ctx), 1)
        ctx = captured_ctx[0]
        self.assertNotEqual(ctx.verify_mode, ssl.CERT_NONE)


if __name__ == '__main__':
    unittest.main()

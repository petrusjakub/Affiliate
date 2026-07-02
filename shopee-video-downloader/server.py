"""
Shopee Video Downloader - HTTP Server

Server HTTP sederhana menggunakan Python stdlib yang menyediakan:
- Serving static files (HTML, CSS, JS)
- API endpoint untuk ekstraksi video
- Proxy download untuk menghindari CORS

Penggunaan:
    python3 server.py [PORT]
    
    PORT default: 8000 (atau dari environment variable PORT)
"""

import os
import re
import sys
import json
import ssl
import urllib.request
import urllib.parse
import urllib.error
from http.server import HTTPServer, BaseHTTPRequestHandler
from typing import Optional

# Tambahkan parent directory ke path agar bisa import extractor
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from extractor import (
    extract_video,
    ExtractionError,
    InvalidURLError,
    NetworkError,
    VideoNotFoundError,
)

# Konfigurasi
DEFAULT_PORT = 8000
STATIC_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'static')

# Maximum download proxy response size (default: 500 MB)
MAX_DOWNLOAD_SIZE = int(os.environ.get('MAX_DOWNLOAD_SIZE', 500 * 1024 * 1024))

# Allowlist of Shopee CDN domains permitted by the download proxy.
# This prevents SSRF by ensuring only known Shopee media hosts are proxied.
ALLOWED_DOWNLOAD_DOMAINS = [
    'cf.shopee.co.id',
    'cv.shopee.co.id',
    'mall.shopee.co.id',
    'cf.shopee.sg',
    'cf.shopee.com.my',
    'cf.shopee.ph',
    'cf.shopee.com.br',
    'cf.shopee.tw',
    'cf.shopee.co.th',
    'cf.shopee.vn',
]

# Patterns for dynamic CDN subdomains (e.g., down-xx.susercontent.com)
ALLOWED_DOWNLOAD_DOMAIN_PATTERNS = [
    re.compile(r'^[a-z0-9-]+\.susercontent\.com$'),
    re.compile(r'^[a-z0-9-]+\.shopee\.co\.id$'),
    re.compile(r'^[a-z0-9-]+\.shopee\.sg$'),
    re.compile(r'^[a-z0-9-]+\.shopee\.com\.my$'),
    re.compile(r'^[a-z0-9-]+\.shopee\.ph$'),
    re.compile(r'^[a-z0-9-]+\.shopee\.com\.br$'),
    re.compile(r'^[a-z0-9-]+\.shopee\.tw$'),
    re.compile(r'^[a-z0-9-]+\.shopee\.co\.th$'),
    re.compile(r'^[a-z0-9-]+\.shopee\.vn$'),
]


def is_allowed_download_domain(hostname: str) -> bool:
    """Check if a hostname is in the allowed download domain list."""
    hostname = hostname.lower()
    if hostname in ALLOWED_DOWNLOAD_DOMAINS:
        return True
    for pattern in ALLOWED_DOWNLOAD_DOMAIN_PATTERNS:
        if pattern.match(hostname):
            return True
    return False

# Content type mapping
CONTENT_TYPES = {
    '.html': 'text/html; charset=utf-8',
    '.css': 'text/css; charset=utf-8',
    '.js': 'application/javascript; charset=utf-8',
    '.json': 'application/json; charset=utf-8',
    '.png': 'image/png',
    '.jpg': 'image/jpeg',
    '.jpeg': 'image/jpeg',
    '.gif': 'image/gif',
    '.svg': 'image/svg+xml',
    '.ico': 'image/x-icon',
    '.mp4': 'video/mp4',
}


class ShopeeVideoHandler(BaseHTTPRequestHandler):
    """Request handler untuk Shopee Video Downloader."""
    
    def log_message(self, format, *args):
        """Override log agar lebih informatif."""
        sys.stderr.write(
            f"[{self.log_date_time_string()}] {format % args}\n"
        )
    
    def send_cors_headers(self):
        """Mengirim CORS headers untuk development."""
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
    
    def send_json_response(self, data: dict, status: int = 200):
        """Mengirim respons JSON."""
        body = json.dumps(data, ensure_ascii=False).encode('utf-8')
        self.send_response(status)
        self.send_header('Content-Type', 'application/json; charset=utf-8')
        self.send_header('Content-Length', str(len(body)))
        self.send_cors_headers()
        self.end_headers()
        self.wfile.write(body)
    
    def send_error_json(self, message: str, status: int = 400):
        """Mengirim error response dalam format JSON."""
        self.send_json_response({
            'success': False,
            'error': message
        }, status)
    
    def do_OPTIONS(self):
        """Handle preflight CORS requests."""
        self.send_response(204)
        self.send_cors_headers()
        self.end_headers()
    
    def do_GET(self):
        """Handle GET requests."""
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path
        
        # Route: API download proxy
        if path == '/api/download':
            self.handle_download(parsed.query)
            return
        
        # Route: Static files
        self.serve_static(path)
    
    def do_POST(self):
        """Handle POST requests."""
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path
        
        if path == '/api/extract':
            self.handle_extract()
        else:
            self.send_error_json("Endpoint tidak ditemukan", 404)
    
    def serve_static(self, path: str):
        """Serve static files dari directory static/."""
        # Default ke index.html
        if path == '/' or path == '':
            path = '/index.html'
        
        # Hapus leading slash dan prefix /static/
        if path.startswith('/static/'):
            file_path = path[8:]  # Remove '/static/'
        elif path.startswith('/'):
            file_path = path[1:]  # Remove leading '/'
        else:
            file_path = path
        
        # Cegah path traversal
        file_path = os.path.normpath(file_path)
        if file_path.startswith('..') or os.path.isabs(file_path):
            self.send_error_json("Akses ditolak", 403)
            return
        
        full_path = os.path.join(STATIC_DIR, file_path)
        
        # Pastikan file ada dan masih di dalam STATIC_DIR
        real_path = os.path.realpath(full_path)
        real_static = os.path.realpath(STATIC_DIR)
        if not real_path.startswith(real_static):
            self.send_error_json("Akses ditolak", 403)
            return
        
        if not os.path.isfile(full_path):
            self.send_error_json("File tidak ditemukan", 404)
            return
        
        # Tentukan content type
        _, ext = os.path.splitext(full_path)
        content_type = CONTENT_TYPES.get(ext.lower(), 'application/octet-stream')
        
        try:
            with open(full_path, 'rb') as f:
                content = f.read()
            
            self.send_response(200)
            self.send_header('Content-Type', content_type)
            self.send_header('Content-Length', str(len(content)))
            self.send_cors_headers()
            self.end_headers()
            self.wfile.write(content)
        except IOError:
            self.send_error_json("Gagal membaca file", 500)
    
    def handle_extract(self):
        """Handle POST /api/extract - ekstrak info video dari URL."""
        try:
            # Baca body
            content_length = int(self.headers.get('Content-Length', 0))
            if content_length == 0:
                self.send_error_json("Request body kosong")
                return
            
            body = self.rfile.read(content_length)
            
            try:
                data = json.loads(body.decode('utf-8'))
            except (json.JSONDecodeError, UnicodeDecodeError):
                self.send_error_json("Format JSON tidak valid")
                return
            
            url = data.get('url', '').strip()
            if not url:
                self.send_error_json("Parameter 'url' diperlukan")
                return
            
            # Ekstrak video info
            result = extract_video(url)
            
            self.send_json_response({
                'success': True,
                'data': result
            })
            
        except InvalidURLError as e:
            self.send_error_json(str(e), 400)
        except VideoNotFoundError as e:
            self.send_error_json(str(e), 404)
        except NetworkError as e:
            self.send_error_json(str(e), 502)
        except ExtractionError as e:
            self.send_error_json(str(e), 500)
        except Exception as e:
            self.send_error_json(f"Terjadi error internal: {str(e)}", 500)
    
    def handle_download(self, query_string: str):
        """Handle GET /api/download - proxy download video.
        
        Security measures:
        - Domain allowlist: Only proxies content from known Shopee CDN domains
        - Content-Length cap: Rejects responses larger than MAX_DOWNLOAD_SIZE
        - TLS verification enabled: Validates server certificates to prevent MITM
        """
        params = urllib.parse.parse_qs(query_string)
        url = params.get('url', [None])[0]
        
        if not url:
            self.send_error_json("Parameter 'url' diperlukan")
            return
        
        try:
            # Decode URL jika perlu
            url = urllib.parse.unquote(url)
            
            # SSRF protection: validate target domain against allowlist
            parsed_url = urllib.parse.urlparse(url)
            hostname = parsed_url.hostname
            scheme = parsed_url.scheme
            
            if scheme not in ('http', 'https'):
                self.send_error_json("Skema URL tidak diizinkan", 403)
                return
            
            if not hostname or not is_allowed_download_domain(hostname):
                self.send_error_json(
                    "Domain tidak diizinkan. Hanya domain CDN Shopee yang diperbolehkan.",
                    403
                )
                return
            
            # Use proper SSL verification for the download proxy path.
            # Unlike the Shopee API calls (which may need relaxed verification due to
            # certificate issues with some Shopee endpoints), the download proxy should
            # verify certificates to protect users from MITM attacks.
            ctx = ssl.create_default_context()
            
            req = urllib.request.Request(url)
            req.add_header('User-Agent',
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0.0.0 Safari/537.36"
            )
            
            response = urllib.request.urlopen(req, timeout=30, context=ctx)
            
            # Content-Length cap: reject responses that exceed the configured maximum
            content_length_str = response.headers.get('Content-Length')
            if content_length_str:
                try:
                    content_length = int(content_length_str)
                    if content_length > MAX_DOWNLOAD_SIZE:
                        response.close()
                        self.send_error_json(
                            f"File terlalu besar (maks {MAX_DOWNLOAD_SIZE // (1024*1024)} MB)",
                            413
                        )
                        return
                except (ValueError, TypeError):
                    content_length = None
            else:
                content_length = None
            
            # Kirim header
            content_type = response.headers.get('Content-Type', 'video/mp4')
            
            self.send_response(200)
            self.send_header('Content-Type', content_type)
            if content_length is not None:
                self.send_header('Content-Length', str(content_length))
            self.send_header(
                'Content-Disposition',
                'attachment; filename="shopee_video.mp4"'
            )
            self.send_cors_headers()
            self.end_headers()
            
            # Stream content with size enforcement
            chunk_size = 65536
            bytes_read = 0
            while True:
                chunk = response.read(chunk_size)
                if not chunk:
                    break
                bytes_read += len(chunk)
                if bytes_read > MAX_DOWNLOAD_SIZE:
                    # Stop streaming if we exceed the limit even without
                    # Content-Length header
                    break
                self.wfile.write(chunk)
                
        except urllib.error.HTTPError as e:
            self.send_error_json(f"Gagal mengunduh video: HTTP {e.code}", 502)
        except urllib.error.URLError as e:
            self.send_error_json(f"Gagal terhubung ke server video: {str(e)}", 502)
        except Exception as e:
            self.send_error_json(f"Error saat mengunduh: {str(e)}", 500)


def run_server(port: Optional[int] = None):
    """Menjalankan HTTP server."""
    if port is None:
        port = int(os.environ.get('PORT', DEFAULT_PORT))
    
    server = HTTPServer(('0.0.0.0', port), ShopeeVideoHandler)
    print(f"Shopee Video Downloader server berjalan di http://localhost:{port}")
    print(f"Static files dari: {STATIC_DIR}")
    print("Tekan Ctrl+C untuk berhenti...")
    
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nServer dihentikan.")
        server.shutdown()


if __name__ == '__main__':
    port = None
    if len(sys.argv) > 1:
        try:
            port = int(sys.argv[1])
        except ValueError:
            print(f"Error: Port harus berupa angka, diberikan: {sys.argv[1]}")
            sys.exit(1)
    
    run_server(port)

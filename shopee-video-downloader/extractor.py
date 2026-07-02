"""
Shopee Video Extractor Module

Modul ini bertanggung jawab untuk:
1. Mem-parsing URL video Shopee dalam berbagai format
2. Mengekstrak Video ID dari URL
3. Mengambil metadata video dari API Shopee
4. Mengembalikan URL download langsung video
"""

import re
import json
import ssl
import urllib.request
import urllib.parse
import urllib.error
from typing import Optional, Dict, Any, Tuple


# Pattern URL Shopee yang didukung
URL_PATTERNS = [
    # Format: https://shopee.co.id/video/VIDEO_ID
    re.compile(r'https?://shopee\.co\.id/video/(\d+)'),
    # Format: https://shopee.co.id/universal-link/video/VIDEO_ID
    re.compile(r'https?://shopee\.co\.id/universal-link/video/(\d+)'),
    # Format: berbagai domain negara
    re.compile(r'https?://shopee\.[a-z.]+/video/(\d+)'),
    re.compile(r'https?://shopee\.[a-z.]+/universal-link/video/(\d+)'),
]

# Pattern untuk short link Shopee
SHORT_LINK_PATTERN = re.compile(r'https?://s\.shopee\.co\.id/.+')
SHORT_LINK_PATTERN_GENERIC = re.compile(r'https?://s\.shopee\.[a-z.]+/.+')

# User-Agent untuk request
USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/120.0.0.0 Safari/537.36"
)

# API endpoint Shopee
SHOPEE_VIDEO_API = "https://shopee.co.id/api/v4/video/get"


class ExtractionError(Exception):
    """Custom exception untuk error saat ekstraksi video."""
    pass


class InvalidURLError(ExtractionError):
    """URL yang diberikan bukan URL Shopee yang valid."""
    pass


class NetworkError(ExtractionError):
    """Terjadi error jaringan saat mengambil data."""
    pass


class VideoNotFoundError(ExtractionError):
    """Video tidak ditemukan di Shopee."""
    pass


def is_valid_shopee_url(url: str) -> bool:
    """
    Memeriksa apakah URL adalah URL Shopee yang valid.
    
    Args:
        url: URL yang akan diperiksa
        
    Returns:
        True jika URL adalah URL Shopee yang valid
    """
    if not url or not isinstance(url, str):
        return False
    
    url = url.strip()
    
    # Cek apakah cocok dengan pattern video langsung
    for pattern in URL_PATTERNS:
        if pattern.match(url):
            return True
    
    # Cek apakah short link
    if SHORT_LINK_PATTERN.match(url) or SHORT_LINK_PATTERN_GENERIC.match(url):
        return True
    
    return False


def extract_video_id(url: str) -> Optional[str]:
    """
    Mengekstrak Video ID dari URL Shopee.
    
    Args:
        url: URL video Shopee
        
    Returns:
        Video ID sebagai string, atau None jika tidak ditemukan
    """
    if not url:
        return None
    
    url = url.strip()
    
    for pattern in URL_PATTERNS:
        match = pattern.match(url)
        if match:
            return match.group(1)
    
    return None


def resolve_short_url(url: str, timeout: int = 10) -> str:
    """
    Mengikuti redirect dari short URL Shopee untuk mendapatkan URL asli.
    
    Args:
        url: Short URL Shopee (format: https://s.shopee.co.id/XXXXX)
        timeout: Timeout dalam detik
        
    Returns:
        URL asli setelah redirect
        
    Raises:
        NetworkError: Jika terjadi error jaringan
    """
    try:
        # Buat SSL context yang tidak strict untuk kompatibilitas
        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
        
        req = urllib.request.Request(url, method='HEAD')
        req.add_header('User-Agent', USER_AGENT)
        
        # Gunakan opener yang tidak follow redirect otomatis
        class NoRedirectHandler(urllib.request.HTTPRedirectHandler):
            def redirect_request(self, req, fp, code, msg, headers, newurl):
                return None
        
        opener = urllib.request.build_opener(
            NoRedirectHandler,
            urllib.request.HTTPSHandler(context=ctx)
        )
        
        try:
            response = opener.open(req, timeout=timeout)
            # Jika tidak ada redirect, kembalikan URL asli
            return url
        except urllib.error.HTTPError as e:
            if e.code in (301, 302, 303, 307, 308):
                location = e.headers.get('Location', '')
                if location:
                    return location
            raise NetworkError(f"HTTP Error {e.code} saat mengikuti redirect")
        
    except urllib.error.URLError as e:
        raise NetworkError(f"Gagal mengakses URL: {str(e)}")
    except Exception as e:
        if isinstance(e, NetworkError):
            raise
        raise NetworkError(f"Error tidak terduga: {str(e)}")


def fetch_video_info(video_id: str, timeout: int = 10) -> Dict[str, Any]:
    """
    Mengambil informasi video dari API Shopee.
    
    Args:
        video_id: ID video Shopee
        timeout: Timeout dalam detik
        
    Returns:
        Dictionary berisi informasi video:
        - video_url: URL download langsung
        - thumbnail: URL thumbnail
        - title: Judul video (jika tersedia)
        - duration: Durasi video dalam detik (jika tersedia)
        - formats: List format yang tersedia
        
    Raises:
        NetworkError: Jika terjadi error jaringan
        VideoNotFoundError: Jika video tidak ditemukan
    """
    api_url = f"{SHOPEE_VIDEO_API}?video_id={video_id}"
    
    try:
        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
        
        req = urllib.request.Request(api_url)
        req.add_header('User-Agent', USER_AGENT)
        req.add_header('Accept', 'application/json')
        req.add_header('Referer', f'https://shopee.co.id/video/{video_id}')
        req.add_header('X-Requested-With', 'XMLHttpRequest')
        
        response = urllib.request.urlopen(req, timeout=timeout, context=ctx)
        data = json.loads(response.read().decode('utf-8'))
        
        return parse_video_response(data, video_id)
        
    except urllib.error.HTTPError as e:
        if e.code == 404:
            raise VideoNotFoundError(f"Video dengan ID {video_id} tidak ditemukan")
        raise NetworkError(f"HTTP Error {e.code} dari API Shopee")
    except urllib.error.URLError as e:
        raise NetworkError(f"Gagal terhubung ke API Shopee: {str(e)}")
    except json.JSONDecodeError:
        raise ExtractionError("Gagal mem-parsing respons dari API Shopee")
    except Exception as e:
        if isinstance(e, (ExtractionError,)):
            raise
        raise NetworkError(f"Error tidak terduga: {str(e)}")


def parse_video_response(data: Dict[str, Any], video_id: str) -> Dict[str, Any]:
    """
    Mem-parsing respons JSON dari API Shopee untuk mengekstrak info video.
    
    Args:
        data: Dictionary respons dari API
        video_id: ID video untuk referensi
        
    Returns:
        Dictionary berisi informasi video yang sudah di-parse
        
    Raises:
        VideoNotFoundError: Jika data video tidak ditemukan dalam respons
    """
    result = {
        'video_id': video_id,
        'video_url': None,
        'thumbnail': None,
        'title': None,
        'duration': None,
        'formats': []
    }
    
    # Coba ekstrak dari struktur data yang umum
    # Format 1: data.data.video_info
    video_info = None
    if isinstance(data, dict):
        if 'data' in data and isinstance(data['data'], dict):
            video_info = data['data'].get('video_info', data['data'])
        elif 'video_info' in data:
            video_info = data['video_info']
        else:
            video_info = data
    
    if video_info:
        # Ekstrak video URL
        video_url = video_info.get('video_url') or video_info.get('url') or video_info.get('play_url')
        if video_url:
            result['video_url'] = video_url
        
        # Ekstrak dari formats/quality array
        formats = video_info.get('formats', []) or video_info.get('qualities', [])
        if isinstance(formats, list):
            for fmt in formats:
                if isinstance(fmt, dict):
                    fmt_info = {
                        'url': fmt.get('url', ''),
                        'quality': fmt.get('quality', '') or fmt.get('label', ''),
                        'width': fmt.get('width', 0),
                        'height': fmt.get('height', 0),
                    }
                    result['formats'].append(fmt_info)
                    # Gunakan format pertama sebagai default jika belum ada
                    if not result['video_url'] and fmt_info['url']:
                        result['video_url'] = fmt_info['url']
        
        # Ekstrak thumbnail
        thumbnail = video_info.get('thumbnail')
        if not thumbnail:
            cover = video_info.get('cover')
            if isinstance(cover, dict):
                thumbnail = cover.get('url')
            elif isinstance(cover, str):
                thumbnail = cover
        if not thumbnail:
            thumbnail = video_info.get('thumb_url')
        if not thumbnail:
            thumbnail = video_info.get('poster')
        result['thumbnail'] = thumbnail
        
        # Ekstrak title
        result['title'] = (
            video_info.get('title') or 
            video_info.get('description') or
            video_info.get('caption') or
            f"Shopee Video {video_id}"
        )
        
        # Ekstrak duration
        duration = video_info.get('duration') or video_info.get('video_duration')
        if duration is not None:
            try:
                result['duration'] = int(duration)
            except (ValueError, TypeError):
                result['duration'] = None
    
    if not result['video_url'] and not result['formats']:
        raise VideoNotFoundError(
            f"Tidak dapat menemukan URL video dalam respons API untuk video ID {video_id}"
        )
    
    return result


def extract_video(url: str) -> Dict[str, Any]:
    """
    Fungsi utama untuk mengekstrak informasi video dari URL Shopee.
    
    Ini adalah entry point utama yang menggabungkan semua langkah:
    1. Validasi URL
    2. Resolusi short URL jika diperlukan
    3. Ekstraksi Video ID
    4. Pengambilan info video dari API
    
    Args:
        url: URL video Shopee (mendukung berbagai format)
        
    Returns:
        Dictionary berisi:
        - video_id: ID video
        - video_url: URL download langsung
        - thumbnail: URL thumbnail
        - title: Judul video
        - duration: Durasi dalam detik
        - formats: List format tersedia
        - download_url: URL untuk download melalui proxy
        
    Raises:
        InvalidURLError: Jika URL tidak valid
        NetworkError: Jika terjadi error jaringan
        VideoNotFoundError: Jika video tidak ditemukan
    """
    if not url or not isinstance(url, str):
        raise InvalidURLError("URL tidak boleh kosong")
    
    url = url.strip()
    
    if not is_valid_shopee_url(url):
        raise InvalidURLError(
            "URL tidak valid. Gunakan format: "
            "https://shopee.co.id/video/VIDEO_ID atau "
            "https://s.shopee.co.id/XXXXX"
        )
    
    # Jika short URL, resolve terlebih dahulu
    if SHORT_LINK_PATTERN.match(url) or SHORT_LINK_PATTERN_GENERIC.match(url):
        url = resolve_short_url(url)
    
    # Ekstrak video ID
    video_id = extract_video_id(url)
    if not video_id:
        raise InvalidURLError(
            f"Tidak dapat mengekstrak Video ID dari URL: {url}"
        )
    
    # Ambil info video dari API
    video_info = fetch_video_info(video_id)
    
    # Tambahkan download URL melalui proxy
    if video_info.get('video_url'):
        encoded_url = urllib.parse.quote(video_info['video_url'], safe='')
        video_info['download_url'] = f"/api/download?url={encoded_url}"
    
    return video_info

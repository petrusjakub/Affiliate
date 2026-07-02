# Shopee Video Downloader

Aplikasi web sederhana untuk mengunduh video dari Shopee tanpa watermark. Cukup paste link video Shopee, dan aplikasi akan mengekstrak URL video asli yang bisa langsung di-download.

## Fitur

- Download video Shopee tanpa watermark
- Mendukung berbagai format URL Shopee
- Interface web yang simpel dan responsif
- Proxy download untuk menghindari masalah CORS
- Tidak memerlukan instalasi package tambahan (hanya Python stdlib)

## Cara Menjalankan

### Prasyarat

- Python 3.6 atau lebih baru (sudah termasuk dalam sebagian besar sistem operasi)
- Tidak perlu menginstal package tambahan

### Menjalankan Server

```bash
cd shopee-video-downloader
python3 server.py
```

Server akan berjalan di `http://localhost:8000`. Buka alamat tersebut di browser.

### Menggunakan Port Lain

```bash
# Menggunakan argumen command line
python3 server.py 9000

# Atau menggunakan environment variable
PORT=9000 python3 server.py
```

## Cara Menggunakan

1. Buka aplikasi Shopee di HP atau browser
2. Cari video yang ingin di-download
3. Tap tombol "Share" dan salin link video
4. Buka `http://localhost:8000` di browser
5. Paste link video di kolom input
6. Klik tombol "Download"
7. Tunggu proses ekstraksi selesai
8. Klik tombol download untuk menyimpan video

## Format URL yang Didukung

| Format | Contoh |
|--------|--------|
| Video langsung | `https://shopee.co.id/video/12345` |
| Universal link | `https://shopee.co.id/universal-link/video/12345` |
| Short link | `https://s.shopee.co.id/XXXXX` |
| Domain negara lain | `https://shopee.sg/video/12345` |

## Arsitektur Teknis

```
shopee-video-downloader/
├── server.py          # HTTP server (entry point)
├── extractor.py       # Logika ekstraksi video
├── static/
│   ├── index.html     # Halaman web utama
│   ├── style.css      # Stylesheet
│   └── script.js      # JavaScript frontend
├── tests/
│   ├── __init__.py
│   └── test_extractor.py  # Unit tests
└── README.md          # Dokumentasi ini
```

### Komponen

1. **server.py** - HTTP server menggunakan `http.server` dari Python standard library. Menangani routing, serving static files, dan API endpoints.

2. **extractor.py** - Modul inti yang berisi logika untuk:
   - Mem-parsing dan memvalidasi URL Shopee
   - Mengikuti redirect dari short URL
   - Memanggil API Shopee untuk mendapatkan info video
   - Mengekstrak URL download langsung

3. **Frontend (static/)** - Antarmuka web sederhana dengan HTML, CSS, dan JavaScript vanilla (tanpa framework).

### API Endpoints

| Method | Path | Deskripsi |
|--------|------|-----------|
| GET | `/` | Halaman utama (index.html) |
| GET | `/static/*` | File statis (CSS, JS) |
| POST | `/api/extract` | Ekstrak info video dari URL |
| GET | `/api/download?url=...` | Proxy download video |

### POST /api/extract

Request:
```json
{
  "url": "https://shopee.co.id/video/12345"
}
```

Response (sukses):
```json
{
  "success": true,
  "data": {
    "video_id": "12345",
    "video_url": "https://cdn.shopee.co.id/video.mp4",
    "thumbnail": "https://cdn.shopee.co.id/thumb.jpg",
    "title": "Video Produk",
    "duration": 60,
    "formats": [],
    "download_url": "/api/download?url=..."
  }
}
```

Response (error):
```json
{
  "success": false,
  "error": "Pesan error"
}
```

## Menjalankan Tests

```bash
cd shopee-video-downloader
python3 -m unittest discover -s tests/ -v
```

Atau dari root repository:

```bash
python3 -m unittest discover -s shopee-video-downloader/tests/ -v
```

## Catatan Deployment

- Aplikasi ini memerlukan akses internet untuk terhubung ke API Shopee
- Untuk production, disarankan menggunakan reverse proxy (nginx/Apache) di depan server Python
- Server ini dirancang untuk development/penggunaan personal
- Pastikan server memiliki akses ke `shopee.co.id` dan CDN Shopee

## Lisensi

Proyek ini dibuat untuk keperluan edukasi dan penggunaan personal.

/**
 * Shopee Video Downloader - Frontend JavaScript
 * 
 * Menangani interaksi user:
 * - Submit URL video
 * - Validasi input
 * - Komunikasi dengan API backend
 * - Menampilkan hasil atau error
 */

(function() {
    'use strict';

    // DOM Elements
    const urlInput = document.getElementById('url-input');
    const extractBtn = document.getElementById('extract-btn');
    const btnText = extractBtn.querySelector('.btn-text');
    const btnLoading = extractBtn.querySelector('.btn-loading');
    const errorSection = document.getElementById('error-section');
    const errorMessage = document.getElementById('error-message');
    const loadingSection = document.getElementById('loading-section');
    const resultSection = document.getElementById('result-section');
    const videoThumbnail = document.getElementById('video-thumbnail');
    const videoDuration = document.getElementById('video-duration');
    const videoTitle = document.getElementById('video-title');
    const videoIdDisplay = document.getElementById('video-id-display');
    const downloadBtn = document.getElementById('download-btn');
    const copyLinkBtn = document.getElementById('copy-link-btn');

    // State
    let currentVideoUrl = '';
    let isProcessing = false;

    /**
     * Validasi apakah URL adalah format Shopee yang valid
     */
    function isValidShopeeUrl(url) {
        if (!url || typeof url !== 'string') return false;
        url = url.trim();

        var patterns = [
            /^https?:\/\/shopee\.co\.id\/video\/\d+/,
            /^https?:\/\/shopee\.co\.id\/universal-link\/video\/\d+/,
            /^https?:\/\/shopee\.[a-z.]+\/video\/\d+/,
            /^https?:\/\/shopee\.[a-z.]+\/universal-link\/video\/\d+/,
            /^https?:\/\/s\.shopee\.co\.id\/.+/,
            /^https?:\/\/s\.shopee\.[a-z.]+\/.+/
        ];

        for (var i = 0; i < patterns.length; i++) {
            if (patterns[i].test(url)) return true;
        }
        return false;
    }

    /**
     * Tampilkan error
     */
    function showError(message) {
        hideAll();
        errorMessage.textContent = message;
        errorSection.classList.remove('hidden');
    }

    /**
     * Tampilkan loading state
     */
    function showLoading() {
        hideAll();
        loadingSection.classList.remove('hidden');
        extractBtn.disabled = true;
        btnText.classList.add('hidden');
        btnLoading.classList.remove('hidden');
    }

    /**
     * Tampilkan hasil
     */
    function showResult(data) {
        hideAll();
        
        // Set thumbnail
        if (data.thumbnail) {
            videoThumbnail.src = data.thumbnail;
            videoThumbnail.style.display = 'block';
        } else {
            videoThumbnail.style.display = 'none';
        }

        // Set duration
        if (data.duration) {
            var minutes = Math.floor(data.duration / 60);
            var seconds = data.duration % 60;
            videoDuration.textContent = minutes + ':' + (seconds < 10 ? '0' : '') + seconds;
            videoDuration.style.display = 'block';
        } else {
            videoDuration.style.display = 'none';
        }

        // Set title
        videoTitle.textContent = data.title || 'Shopee Video';
        videoIdDisplay.textContent = 'Video ID: ' + (data.video_id || '-');

        // Set download URL
        if (data.download_url) {
            downloadBtn.href = data.download_url;
            currentVideoUrl = data.video_url || '';
        } else if (data.video_url) {
            downloadBtn.href = '/api/download?url=' + encodeURIComponent(data.video_url);
            currentVideoUrl = data.video_url;
        }

        resultSection.classList.remove('hidden');
    }

    /**
     * Sembunyikan semua section status
     */
    function hideAll() {
        errorSection.classList.add('hidden');
        loadingSection.classList.add('hidden');
        resultSection.classList.add('hidden');
        extractBtn.disabled = false;
        btnText.classList.remove('hidden');
        btnLoading.classList.add('hidden');
    }

    /**
     * Proses ekstraksi video
     */
    function processUrl() {
        if (isProcessing) return;

        var url = urlInput.value.trim();

        // Validasi input kosong
        if (!url) {
            showError('Silakan masukkan link video Shopee');
            urlInput.focus();
            return;
        }

        // Validasi format URL
        if (!isValidShopeeUrl(url)) {
            showError(
                'URL tidak valid. Masukkan link video Shopee dengan format:\n' +
                '- https://shopee.co.id/video/VIDEO_ID\n' +
                '- https://s.shopee.co.id/XXXXX'
            );
            return;
        }

        // Mulai proses
        isProcessing = true;
        showLoading();

        // Kirim request ke API
        fetch('/api/extract', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ url: url })
        })
        .then(function(response) {
            return response.json();
        })
        .then(function(result) {
            isProcessing = false;
            
            if (result.success && result.data) {
                showResult(result.data);
            } else {
                showError(result.error || 'Gagal mengekstrak video. Silakan coba lagi.');
            }
        })
        .catch(function(err) {
            isProcessing = false;
            showError('Terjadi error koneksi. Pastikan server berjalan dan coba lagi.');
            console.error('Fetch error:', err);
        });
    }

    /**
     * Salin link video ke clipboard
     */
    function copyVideoLink() {
        var textToCopy = currentVideoUrl || downloadBtn.href;
        
        if (!textToCopy) {
            return;
        }

        // Gunakan Clipboard API jika tersedia
        if (navigator.clipboard && navigator.clipboard.writeText) {
            navigator.clipboard.writeText(textToCopy).then(function() {
                showCopySuccess();
            }).catch(function() {
                fallbackCopy(textToCopy);
            });
        } else {
            fallbackCopy(textToCopy);
        }
    }

    /**
     * Fallback copy menggunakan textarea
     */
    function fallbackCopy(text) {
        var textarea = document.createElement('textarea');
        textarea.value = text;
        textarea.style.position = 'fixed';
        textarea.style.opacity = '0';
        document.body.appendChild(textarea);
        textarea.select();
        
        try {
            document.execCommand('copy');
            showCopySuccess();
        } catch (err) {
            showError('Gagal menyalin link. Silakan salin secara manual.');
        }
        
        document.body.removeChild(textarea);
    }

    /**
     * Tampilkan indikator sukses salin
     */
    function showCopySuccess() {
        var originalText = copyLinkBtn.innerHTML;
        copyLinkBtn.innerHTML = '<span class="copy-icon">&#10003;</span> Tersalin!';
        copyLinkBtn.style.background = '#27ae60';
        copyLinkBtn.style.color = 'white';
        copyLinkBtn.style.borderColor = '#27ae60';
        
        setTimeout(function() {
            copyLinkBtn.innerHTML = originalText;
            copyLinkBtn.style.background = '';
            copyLinkBtn.style.color = '';
            copyLinkBtn.style.borderColor = '';
        }, 2000);
    }

    // Event Listeners
    extractBtn.addEventListener('click', processUrl);

    urlInput.addEventListener('keypress', function(e) {
        if (e.key === 'Enter') {
            e.preventDefault();
            processUrl();
        }
    });

    copyLinkBtn.addEventListener('click', copyVideoLink);

    // Auto-focus input on page load
    urlInput.focus();

})();

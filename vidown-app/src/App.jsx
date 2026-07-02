import React, { useState, useEffect, useRef } from 'react';
import {
  Download, Sparkles, BookOpen, Code, History, Link2, CheckCircle,
  RefreshCw, Send, FileVideo, Info, Smartphone, Copy, Check, Menu, X,
  Play, ExternalLink
} from 'lucide-react';

const apiKey = '';
const modelName = 'gemini-2.5-flash-preview-09-2025';
// External downloader services (fallback when API fails)
const EXTERNAL_DOWNLOADERS = {
  tiktok: 'https://ssstik.io/en',
  instagram: 'https://snapinsta.app',
  facebook: 'https://getmyfb.com',
  threads: 'https://threadsdownloader.com',
  shopee: 'https://shopeenowatermark.com',
};

// Cobalt API - universal video downloader that supports CORS
async function cobaltDownload(videoUrl) {
  const res = await fetch('https://api.cobalt.tools/api/json', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'Accept': 'application/json',
    },
    body: JSON.stringify({ url: videoUrl }),
  });
  if (!res.ok) {
    const errorText = await res.text().catch(() => 'Unknown error');
    throw new Error('Cobalt API gagal: ' + res.status + ' - ' + errorText);
  }
  const data = await res.json();
  if (data.status === 'error') {
    throw new Error(data.text || 'Cobalt tidak bisa memproses URL ini');
  }
  if (data.status === 'redirect' || data.status === 'stream') {
    return { videoUrl: data.url };
  }
  if (data.status === 'picker' && data.picker && data.picker.length > 0) {
    const videoItem = data.picker.find(p => p.type === 'video') || data.picker[0];
    return { videoUrl: videoItem.url, thumbnail: videoItem.thumb || null };
  }
  throw new Error('Cobalt mengembalikan response yang tidak dikenali');
}

// TikTok specific API (tikwm.com) - known to work
async function tiktokDownload(videoUrl) {
  const response = await fetch('https://www.tikwm.com/api/', {
    method: 'POST',
    headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
    body: new URLSearchParams({ url: videoUrl, hd: '1' }),
  });
  if (!response.ok) throw new Error('TikWM API request gagal');
  const data = await response.json();
  if (data.code !== 0 || !data.data) {
    throw new Error(data.msg || 'Gagal mengekstrak video TikTok');
  }
  const videoData = data.data;
  return {
    videoUrl: videoData.hdplay || videoData.play,
    title: videoData.title || 'TikTok Video',
    thumbnail: videoData.cover || videoData.origin_cover,
    duration: videoData.duration ? Math.floor(videoData.duration / 60) + ':' + String(videoData.duration % 60).padStart(2, '0') : null,
    quality: videoData.hdplay ? '1080p HD' : '720p',
    author: videoData.author ? videoData.author.nickname : 'Unknown',
  };
}

const platforms = {
  shopee: {
    name: 'Shopee Video',
    color: 'from-orange-500 to-red-600',
    iconBg: 'bg-orange-100 text-orange-600 dark:bg-orange-950/40 dark:text-orange-400',
    borderColor: 'border-orange-500',
    placeholder: 'https://shopee.co.id/universal-link/video/39201...'
  },
  tiktok: {
    name: 'TikTok',
    color: 'from-zinc-900 to-black',
    iconBg: 'bg-zinc-100 text-zinc-900 dark:bg-zinc-800 dark:text-white',
    borderColor: 'border-zinc-800',
    placeholder: 'https://www.tiktok.com/@username/video/12345...'
  },
  instagram: {
    name: 'Instagram Reel',
    color: 'from-pink-500 via-red-500 to-yellow-500',
    iconBg: 'bg-pink-100 text-pink-600 dark:bg-pink-950/40 dark:text-pink-400',
    borderColor: 'border-pink-500',
    placeholder: 'https://www.instagram.com/reel/C1s2d3f4g...'
  },
  facebook: {
    name: 'Facebook Video',
    color: 'from-blue-600 to-indigo-700',
    iconBg: 'bg-blue-100 text-blue-600 dark:bg-blue-950/40 dark:text-blue-400',
    borderColor: 'border-blue-600',
    placeholder: 'https://www.facebook.com/watch/?v=12345...'
  },
  threads: {
    name: 'Threads',
    color: 'from-zinc-800 to-black',
    iconBg: 'bg-zinc-100 text-zinc-900 dark:bg-zinc-800 dark:text-white',
    borderColor: 'border-zinc-700',
    placeholder: 'https://www.threads.net/@username/post/C1234...'
  }
};

export default function App() {
  const [activeTab, setActiveTab] = useState('download');
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [url, setUrl] = useState('');
  const [detectedPlatform, setDetectedPlatform] = useState(null);
  const [downloadState, setDownloadState] = useState('idle');
  const [downloadProgress, setDownloadProgress] = useState(0);
  const [statusMessage, setStatusMessage] = useState('');
  const [downloadResult, setDownloadResult] = useState(null);
  const [copiedId, setCopiedId] = useState(null);
  const [history, setHistory] = useState([]);
  const [messages, setMessages] = useState([]);
  const [chatInput, setChatInput] = useState('');
  const [isChatLoading, setIsChatLoading] = useState(false);
  const [errorMessage, setErrorMessage] = useState('');
  const [videoPreviewUrl, setVideoPreviewUrl] = useState(null);
  const [showExternalFallback, setShowExternalFallback] = useState(false);
  const chatEndRef = useRef(null);

  useEffect(() => {
    if (!url) {
      setDetectedPlatform(null);
      return;
    }
    const lower = url.toLowerCase();
    if (lower.includes('shopee') || lower.includes('shp.ee')) {
      setDetectedPlatform('shopee');
    } else if (lower.includes('tiktok')) {
      setDetectedPlatform('tiktok');
    } else if (lower.includes('instagram') || lower.includes('instagr.am')) {
      setDetectedPlatform('instagram');
    } else if (lower.includes('facebook') || lower.includes('fb.watch') || lower.includes('fb.com')) {
      setDetectedPlatform('facebook');
    } else if (lower.includes('threads.net') || lower.includes('threads.com')) {
      setDetectedPlatform('threads');
    } else {
      setDetectedPlatform(null);
    }
  }, [url]);

  useEffect(() => {
    if (chatEndRef.current) {
      chatEndRef.current.scrollIntoView({ behavior: 'smooth' });
    }
  }, [messages]);

  const handlePaste = async () => {
    try {
      const text = await navigator.clipboard.readText();
      setUrl(text);
    } catch (err) {
      console.error('Failed to read clipboard:', err);
    }
  };

  const triggerDownload = async () => {
    setErrorMessage('');
    setVideoPreviewUrl(null);
    setShowExternalFallback(false);
    setDownloadResult(null);

    if (!url) {
      setErrorMessage('Silakan paste URL video terlebih dahulu!');
      return;
    }
    if (!detectedPlatform) {
      setErrorMessage('Platform tidak terdeteksi. Paste URL yang valid dari Shopee, TikTok, Instagram, Facebook, atau Threads.');
      return;
    }

    setDownloadState('analyzing');
    setDownloadProgress(10);
    setStatusMessage('Menganalisis URL...');

    try {
      let result = null;

      // For TikTok: use tikwm.com API (proven to work)
      if (detectedPlatform === 'tiktok') {
        setDownloadProgress(30);
        setStatusMessage('Menghubungi TikTok API...');
        try {
          result = await tiktokDownload(url);
        } catch (tiktokErr) {
          // TikTok API failed, try Cobalt
          setDownloadProgress(50);
          setStatusMessage('API utama gagal, mencoba Cobalt...');
          try {
            result = await cobaltDownload(url);
          } catch (cobaltErr) {
            throw new Error('Semua API gagal. ' + tiktokErr.message);
          }
        }
      } else {
        // For other platforms: try Cobalt API first
        setDownloadProgress(30);
        setStatusMessage('Menghubungi Cobalt API...');
        try {
          result = await cobaltDownload(url);
        } catch (cobaltErr) {
          // Cobalt failed - show external fallback
          throw new Error('Cobalt API gagal: ' + cobaltErr.message);
        }
      }

      if (!result || !result.videoUrl) {
        throw new Error('Tidak bisa mengekstrak URL video. Video mungkin private atau link tidak valid.');
      }

      // Success - show video player
      setDownloadProgress(90);
      setStatusMessage('Video berhasil diekstrak!');
      setVideoPreviewUrl(result.videoUrl);

      await new Promise(resolve => setTimeout(resolve, 300));
      setDownloadProgress(100);
      setStatusMessage('Siap disimpan!');

      const downloadResultData = {
        id: Date.now().toString(),
        platform: detectedPlatform,
        url: url,
        title: result.title || 'Video dari ' + platforms[detectedPlatform].name,
        thumbnail: result.thumbnail || null,
        videoUrl: result.videoUrl,
        duration: result.duration || null,
        quality: result.quality || '720p',
        author: result.author || 'Unknown',
        timestamp: new Date().toLocaleString()
      };

      setDownloadResult(downloadResultData);
      setDownloadState('completed');
      setHistory(prev => [downloadResultData, ...prev]);

    } catch (error) {
      // Download failed - show external fallback option
      setDownloadState('idle');
      setDownloadProgress(0);
      setStatusMessage('');
      setErrorMessage(error.message || 'Terjadi kesalahan. Silakan coba lagi.');
      setShowExternalFallback(true);
    }
  };

  const handleOpenExternalDownloader = () => {
    if (!detectedPlatform) return;
    const externalUrl = EXTERNAL_DOWNLOADERS[detectedPlatform];
    if (externalUrl) {
      window.open(externalUrl, '_blank');
    }
  };

  const handleSaveFile = async () => {
    if (!downloadResult || !downloadResult.videoUrl) return;

    try {
      // Try to fetch the video as a blob for proper download
      const response = await fetch(downloadResult.videoUrl, { mode: 'cors' });
      if (!response.ok) throw new Error('Fetch gagal');

      const blob = await response.blob();
      const blobUrl = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = blobUrl;
      a.download = 'vidown_' + downloadResult.platform + '_' + downloadResult.id + '.mp4';
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      URL.revokeObjectURL(blobUrl);
    } catch {
      // Fallback: use download attribute with direct link
      try {
        const a = document.createElement('a');
        a.href = downloadResult.videoUrl;
        a.download = 'vidown_' + downloadResult.platform + '_' + downloadResult.id + '.mp4';
        a.target = '_blank';
        a.rel = 'noopener noreferrer';
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
      } catch {
        // Ultimate fallback: open in new tab
        window.open(downloadResult.videoUrl, '_blank');
      }
    }
  };

  const handleOpenVideo = () => {
    if (downloadResult && downloadResult.videoUrl) {
      window.open(downloadResult.videoUrl, '_blank');
    }
  };

  const resetDownload = () => {
    setDownloadState('idle');
    setDownloadProgress(0);
    setStatusMessage('');
    setDownloadResult(null);
    setVideoPreviewUrl(null);
    setErrorMessage('');
    setShowExternalFallback(false);
  };

  const handleSendMessage = async () => {
    if (!chatInput.trim()) return;
    const userMessage = { role: 'user', content: chatInput.trim() };
    setMessages(prev => [...prev, userMessage]);
    setChatInput('');
    setIsChatLoading(true);

    try {
      const response = await fetch(
        'https://generativelanguage.googleapis.com/v1beta/models/' + modelName + ':generateContent?key=' + apiKey,
        {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            contents: [{ parts: [{ text: userMessage.content }] }]
          })
        }
      );

      if (!response.ok) throw new Error('API request failed');
      const data = await response.json();
      const aiText = data.candidates && data.candidates[0] && data.candidates[0].content && data.candidates[0].content.parts && data.candidates[0].content.parts[0] ? data.candidates[0].content.parts[0].text : 'Maaf, tidak bisa membuat respons.';
      setMessages(prev => [...prev, { role: 'assistant', content: aiText }]);
    } catch (error) {
      setMessages(prev => [...prev, { role: 'assistant', content: 'Maaf, terjadi error. Periksa API key dan coba lagi.' }]);
    } finally {
      setIsChatLoading(false);
    }
  };

  const copyToClipboard = (text, id) => {
    navigator.clipboard.writeText(text);
    setCopiedId(id);
    setTimeout(() => setCopiedId(null), 2000);
  };

  const navItems = [
    { id: 'download', label: 'Download', icon: Download },
    { id: 'ai-chat', label: 'AI Chat', icon: Sparkles },
    { id: 'guides', label: 'Guides', icon: BookOpen },
    { id: 'developer', label: 'Developer', icon: Code }
  ];

  const developerCode = `import yt_dlp

def download_video(url, output_path='./downloads'):
    ydl_opts = {
        'outtmpl': f'{output_path}/%(title)s.%(ext)s',
        'format': 'best[ext=mp4]/best',
        'quiet': False,
    }
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        ydl.download([url])

# Example usage
download_video('https://www.tiktok.com/@user/video/123')`;

  return (
    <div className="min-h-screen bg-slate-950 text-white flex">
      {/* Mobile Header */}
      <div className="lg:hidden fixed top-0 left-0 right-0 z-50 bg-slate-900/95 backdrop-blur-sm border-b border-slate-800 px-4 py-3 flex items-center justify-between">
        <button onClick={() => setSidebarOpen(!sidebarOpen)} className="p-2 rounded-lg hover:bg-slate-800">
          {sidebarOpen ? <X size={20} /> : <Menu size={20} />}
        </button>
        <span className="font-bold text-lg bg-gradient-to-r from-blue-400 to-purple-400 bg-clip-text text-transparent">vIDown</span>
        <div className="w-9" />
      </div>

      {/* Sidebar Overlay */}
      {sidebarOpen && (
        <div className="lg:hidden fixed inset-0 z-40 bg-black/50" onClick={() => setSidebarOpen(false)} />
      )}

      {/* Sidebar */}
      <aside className={`fixed lg:static inset-y-0 left-0 z-40 w-64 bg-slate-900 border-r border-slate-800 flex flex-col transform transition-transform duration-200 ${sidebarOpen ? 'translate-x-0' : '-translate-x-full lg:translate-x-0'}`}>
        <div className="p-6 border-b border-slate-800">
          <h1 className="text-2xl font-bold bg-gradient-to-r from-blue-400 to-purple-400 bg-clip-text text-transparent">vIDown</h1>
          <p className="text-xs text-slate-500 mt-1">Multi-Platform Video Downloader</p>
        </div>
        <nav className="flex-1 p-4 space-y-2">
          {navItems.map(item => (
            <button
              key={item.id}
              onClick={() => { setActiveTab(item.id); setSidebarOpen(false); }}
              className={`w-full flex items-center gap-3 px-4 py-3 rounded-xl text-sm font-medium transition-all ${
                activeTab === item.id
                  ? 'bg-blue-600/20 text-blue-400 border border-blue-500/30'
                  : 'text-slate-400 hover:text-white hover:bg-slate-800'
              }`}
            >
              <item.icon size={18} />
              {item.label}
            </button>
          ))}
        </nav>
        <div className="p-4 border-t border-slate-800">
          <div className="text-xs text-slate-500 space-y-1">
            <p className="flex items-center gap-1"><Info size={12} /> Engine: Cobalt + TikWM</p>
            <p>AI: Gemini 2.5 Flash</p>
          </div>
        </div>
      </aside>

      {/* Main Content */}
      <main className="flex-1 lg:ml-0 mt-14 lg:mt-0 overflow-y-auto">
        {/* Header */}
        <div className="p-6 border-b border-slate-800">
          <div className="flex flex-wrap items-center gap-2">
            <span className="text-sm text-slate-400">Active platforms:</span>
            {Object.entries(platforms).map(([key, platform]) => (
              <span key={key} className={`px-3 py-1 rounded-full text-xs font-medium ${platform.iconBg}`}>
                {platform.name}
              </span>
            ))}
          </div>
        </div>

        <div className="p-6 max-w-5xl mx-auto">
          {/* Download Tab */}
          {activeTab === 'download' && (
            <div className="space-y-6 animate-fadeIn">
              {/* URL Input - Hero Section */}
              <div className="bg-gradient-to-br from-slate-900 via-slate-900 to-slate-800 rounded-3xl p-8 border border-blue-500/20 shadow-lg shadow-blue-500/5">
                <h2 className="text-2xl font-bold mb-2 bg-gradient-to-r from-blue-400 to-purple-400 bg-clip-text text-transparent">Download Video Instantly</h2>
                <p className="text-slate-400 text-sm mb-5">Paste URL video dari Shopee, TikTok, Instagram, Facebook, atau Threads</p>
                <div className="flex flex-col sm:flex-row gap-3">
                  <div className="flex-1 relative">
                    <input
                      type="text"
                      value={url}
                      onChange={(e) => { setUrl(e.target.value); setErrorMessage(''); setShowExternalFallback(false); }}
                      placeholder={detectedPlatform ? platforms[detectedPlatform].placeholder : 'Paste URL video di sini...'}
                      className="w-full bg-slate-800 border border-slate-700 rounded-xl px-5 py-4 text-base text-white placeholder-slate-500 focus:outline-none focus:border-blue-500 focus:ring-2 focus:ring-blue-500/20 transition-all"
                    />
                    {detectedPlatform && (
                      <span className={`absolute right-3 top-1/2 -translate-y-1/2 px-2 py-0.5 rounded-full text-xs font-medium bg-gradient-to-r ${platforms[detectedPlatform].color} text-white`}>
                        {platforms[detectedPlatform].name}
                      </span>
                    )}
                  </div>
                  <button
                    onClick={handlePaste}
                    className="px-5 py-4 bg-slate-800 border border-slate-700 rounded-xl hover:bg-slate-700 transition-colors text-sm font-medium flex items-center justify-center gap-2"
                  >
                    <Link2 size={18} /> Paste
                  </button>
                  <button
                    onClick={triggerDownload}
                    disabled={downloadState === 'downloading' || downloadState === 'analyzing'}
                    className={`px-8 py-4 rounded-xl font-semibold text-base transition-all flex items-center justify-center gap-2 ${
                      downloadState === 'downloading' || downloadState === 'analyzing'
                        ? 'bg-gradient-to-r from-blue-600/50 to-purple-600/50 text-white/70 cursor-wait'
                        : 'bg-gradient-to-r from-blue-600 to-purple-600 text-white hover:from-blue-500 hover:to-purple-500 hover:shadow-lg hover:shadow-purple-500/25 active:scale-95'
                    }`}
                  >
                    {downloadState === 'downloading' || downloadState === 'analyzing' ? (
                      <><RefreshCw size={18} className="animate-spin" /> Processing</>
                    ) : (
                      <><Download size={18} /> Download</>
                    )}
                  </button>
                </div>

                {/* Error Message */}
                {errorMessage && (
                  <div className="mt-3 text-sm text-red-400 bg-red-500/10 border border-red-500/20 rounded-lg px-4 py-3">
                    <p className="mb-2">{errorMessage}</p>
                    {showExternalFallback && detectedPlatform && (
                      <div className="mt-3 pt-3 border-t border-red-500/20">
                        <p className="text-slate-300 text-sm mb-2">
                          Gunakan downloader eksternal yang sudah terbukti bekerja:
                        </p>
                        <button
                          onClick={handleOpenExternalDownloader}
                          className="inline-flex items-center gap-2 px-4 py-2 bg-gradient-to-r from-blue-600 to-purple-600 text-white rounded-lg text-sm font-medium hover:from-blue-500 hover:to-purple-500 transition-all"
                        >
                          <ExternalLink size={16} />
                          Buka di {EXTERNAL_DOWNLOADERS[detectedPlatform] ? new URL(EXTERNAL_DOWNLOADERS[detectedPlatform]).hostname : 'Downloader Eksternal'}
                        </button>
                        <p className="text-xs text-slate-500 mt-2">
                          Tip: Paste URL video kamu di situs tersebut untuk mendownload.
                        </p>
                      </div>
                    )}
                  </div>
                )}

                {/* Progress Bar */}
                {(downloadState === 'analyzing' || downloadState === 'downloading') && (
                  <div className="mt-4 animate-fadeIn">
                    <div className="flex justify-between text-xs text-slate-400 mb-2">
                      <span>{statusMessage}</span>
                      <span>{downloadProgress}%</span>
                    </div>
                    <div className="w-full bg-slate-800 rounded-full h-2">
                      <div
                        className="bg-gradient-to-r from-blue-500 to-purple-500 h-2 rounded-full transition-all duration-500"
                        style={{ width: downloadProgress + '%' }}
                      />
                    </div>
                  </div>
                )}

                {/* Download Result with Video Player */}
                {downloadState === 'completed' && downloadResult && (
                  <div className="mt-4 bg-slate-800 rounded-2xl p-5 border border-green-500/30 animate-scaleIn">
                    <div className="flex items-center justify-between mb-3">
                      <div className="flex items-center gap-3">
                        <CheckCircle size={20} className="text-green-400" />
                        <span className="text-sm font-medium text-green-400">Video Siap!</span>
                      </div>
                      <button
                        onClick={resetDownload}
                        className="text-xs text-slate-400 hover:text-white px-2 py-1 rounded-lg hover:bg-slate-700 transition-colors"
                      >
                        Download Baru
                      </button>
                    </div>

                    {/* Video Preview Player */}
                    {videoPreviewUrl && (
                      <div className="mb-4 rounded-xl overflow-hidden bg-black">
                        <video
                          src={videoPreviewUrl}
                          controls
                          className="w-full max-h-[300px] object-contain"
                          poster={downloadResult.thumbnail || undefined}
                          preload="metadata"
                        >
                          Browser tidak mendukung pemutaran video.
                        </video>
                      </div>
                    )}

                    {/* Thumbnail fallback */}
                    {!videoPreviewUrl && downloadResult.thumbnail && (
                      <div className="mb-4 rounded-xl overflow-hidden">
                        <img
                          src={downloadResult.thumbnail}
                          alt={downloadResult.title}
                          className="w-full max-h-[200px] object-cover"
                        />
                      </div>
                    )}

                    <div className="space-y-2 text-sm text-slate-300">
                      <p><span className="text-slate-500">Judul:</span> {downloadResult.title}</p>
                      {downloadResult.author && <p><span className="text-slate-500">Author:</span> {downloadResult.author}</p>}
                      {downloadResult.quality && <p><span className="text-slate-500">Kualitas:</span> {downloadResult.quality}</p>}
                      {downloadResult.duration && <p><span className="text-slate-500">Durasi:</span> {downloadResult.duration}</p>}
                    </div>

                    <div className="mt-4 flex gap-2">
                      <button
                        onClick={handleSaveFile}
                        className="flex-1 py-3 bg-gradient-to-r from-green-600 to-emerald-600 hover:from-green-500 hover:to-emerald-500 rounded-xl text-sm font-medium transition-all flex items-center justify-center gap-2"
                      >
                        <Download size={16} /> Simpan Video (MP4)
                      </button>
                      <button
                        onClick={handleOpenVideo}
                        className="px-4 py-3 bg-slate-700 hover:bg-slate-600 rounded-xl text-sm font-medium transition-colors flex items-center justify-center gap-2"
                      >
                        <Play size={16} /> Buka
                      </button>
                    </div>

                    <p className="mt-3 text-xs text-slate-500 text-center">
                      Jika Simpan tidak bekerja, klik Buka lalu klik kanan video dan pilih "Save video as..."
                    </p>
                  </div>
                )}
              </div>

              {/* Promo Banner */}
              <div className="bg-gradient-to-r from-blue-600/20 to-purple-600/20 border border-blue-500/30 rounded-2xl p-6">
                <h2 className="text-xl font-bold mb-2">Download Video dari 5 Platform</h2>
                <p className="text-slate-300 text-sm">Paste URL video dari Shopee, TikTok, Instagram, Facebook, atau Threads. TikTok menggunakan API langsung, platform lain menggunakan Cobalt API dengan fallback ke downloader eksternal.</p>
              </div>

              {/* Platform Cards */}
              <div className="grid grid-cols-2 md:grid-cols-5 gap-3">
                {Object.entries(platforms).map(([key, platform]) => (
                  <div
                    key={key}
                    className={`p-4 rounded-2xl border border-slate-700 hover:border-slate-600 transition-all cursor-pointer ${
                      detectedPlatform === key ? 'border-2 ' + platform.borderColor : ''
                    }`}
                  >
                    <div className={`w-10 h-10 rounded-xl ${platform.iconBg} flex items-center justify-center mb-3`}>
                      <FileVideo size={18} />
                    </div>
                    <p className="text-sm font-medium text-slate-200">{platform.name}</p>
                  </div>
                ))}
              </div>

              {/* History */}
              {history.length > 0 && (
                <div className="bg-slate-900 rounded-3xl p-6 border border-slate-800">
                  <h3 className="text-lg font-semibold mb-4 flex items-center gap-2">
                    <History size={18} /> Riwayat Download
                  </h3>
                  <div className="space-y-3">
                    {history.map((item) => (
                      <div key={item.id} className="flex items-center justify-between p-3 bg-slate-800 rounded-xl">
                        <div className="flex items-center gap-3">
                          <div className={`w-8 h-8 rounded-lg ${platforms[item.platform] ? platforms[item.platform].iconBg : ''} flex items-center justify-center`}>
                            <FileVideo size={14} />
                          </div>
                          <div>
                            <p className="text-sm font-medium">{item.title}</p>
                            <p className="text-xs text-slate-500">{item.timestamp}</p>
                          </div>
                        </div>
                        <button
                          onClick={() => copyToClipboard(item.url, item.id)}
                          className="p-2 rounded-lg hover:bg-slate-700 transition-colors"
                        >
                          {copiedId === item.id ? <Check size={14} className="text-green-400" /> : <Copy size={14} className="text-slate-400" />}
                        </button>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
          )}

          {/* AI Chat Tab */}
          {activeTab === 'ai-chat' && (
            <div className="space-y-4 animate-fadeIn">
              <div className="bg-slate-900 rounded-3xl border border-slate-800 flex flex-col h-[600px]">
                <div className="p-4 border-b border-slate-800">
                  <h3 className="font-semibold flex items-center gap-2"><Sparkles size={18} className="text-purple-400" /> AI Assistant</h3>
                  <p className="text-xs text-slate-500 mt-1">Powered by Gemini 2.5 Flash</p>
                </div>

                <div className="flex-1 overflow-y-auto p-4 space-y-4">
                  {messages.length === 0 && (
                    <div className="text-center text-slate-500 py-12">
                      <Sparkles size={40} className="mx-auto mb-4 text-purple-400/50" />
                      <p className="text-sm">Tanya apa saja tentang download video!</p>
                      <div className="flex flex-wrap justify-center gap-2 mt-4">
                        {['Cara download video TikTok?', 'Setting kualitas terbaik', 'Platform yang didukung'].map(tag => (
                          <button
                            key={tag}
                            onClick={() => setChatInput(tag)}
                            className="px-3 py-1.5 bg-slate-800 border border-slate-700 rounded-full text-xs text-slate-300 hover:border-purple-500/50 transition-colors"
                          >
                            {tag}
                          </button>
                        ))}
                      </div>
                    </div>
                  )}
                  {messages.map((msg, idx) => (
                    <div key={idx} className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}>
                      <div className={`max-w-[80%] px-4 py-3 rounded-2xl text-sm ${
                        msg.role === 'user'
                          ? 'bg-blue-600 text-white'
                          : 'bg-slate-800 text-slate-200 border border-slate-700'
                      }`}>
                        {msg.content}
                      </div>
                    </div>
                  ))}
                  {isChatLoading && (
                    <div className="flex justify-start">
                      <div className="bg-slate-800 border border-slate-700 rounded-2xl px-4 py-3 text-sm text-slate-400">
                        <RefreshCw size={14} className="animate-spin inline mr-2" /> Berpikir...
                      </div>
                    </div>
                  )}
                  <div ref={chatEndRef} />
                </div>

                <div className="p-4 border-t border-slate-800">
                  <div className="flex gap-2">
                    <input
                      type="text"
                      value={chatInput}
                      onChange={(e) => setChatInput(e.target.value)}
                      onKeyDown={(e) => e.key === 'Enter' && handleSendMessage()}
                      placeholder="Ketik pesan..."
                      className="flex-1 bg-slate-800 border border-slate-700 rounded-xl px-4 py-3 text-sm text-white placeholder-slate-500 focus:outline-none focus:border-purple-500"
                    />
                    <button
                      onClick={handleSendMessage}
                      disabled={!chatInput.trim() || isChatLoading}
                      className="px-4 py-3 bg-purple-600 rounded-xl hover:bg-purple-700 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                    >
                      <Send size={16} />
                    </button>
                  </div>
                </div>
              </div>
            </div>
          )}

          {/* Guides Tab */}
          {activeTab === 'guides' && (
            <div className="space-y-4 animate-fadeIn">
              <h2 className="text-xl font-bold mb-4">Panduan Platform</h2>
              <div className="grid gap-4">
                {[
                  {
                    platform: 'shopee',
                    steps: ['Buka aplikasi Shopee', 'Temukan video yang ingin diunduh', 'Tap tombol Share', 'Pilih "Salin Link"', 'Paste URL ke vIDown']
                  },
                  {
                    platform: 'tiktok',
                    steps: ['Buka aplikasi TikTok', 'Temukan video yang ingin diunduh', 'Tap tombol Share (panah)', 'Pilih "Copy Link"', 'Paste URL ke vIDown']
                  },
                  {
                    platform: 'instagram',
                    steps: ['Buka aplikasi Instagram', 'Temukan Reel yang ingin diunduh', 'Tap icon tiga titik (...)', 'Pilih "Copy Link"', 'Paste URL ke vIDown']
                  },
                  {
                    platform: 'facebook',
                    steps: ['Buka aplikasi Facebook', 'Temukan video yang ingin diunduh', 'Tap tombol Share', 'Pilih "Copy Link"', 'Paste URL ke vIDown']
                  },
                  {
                    platform: 'threads',
                    steps: ['Buka app Threads', 'Temukan post video', 'Tap icon share/tiga titik', 'Pilih "Copy link"', 'Paste ke vIDown']
                  }
                ].map(guide => (
                  <div key={guide.platform} className="bg-slate-900 rounded-2xl p-6 border border-slate-800">
                    <div className="flex items-center gap-3 mb-4">
                      <div className={`w-10 h-10 rounded-xl ${platforms[guide.platform].iconBg} flex items-center justify-center`}>
                        <Smartphone size={18} />
                      </div>
                      <h3 className="font-semibold">{platforms[guide.platform].name}</h3>
                    </div>
                    <ol className="space-y-2">
                      {guide.steps.map((step, idx) => (
                        <li key={idx} className="flex items-start gap-3 text-sm text-slate-300">
                          <span className="flex-shrink-0 w-6 h-6 bg-slate-800 rounded-full flex items-center justify-center text-xs font-medium text-blue-400">{idx + 1}</span>
                          {step}
                        </li>
                      ))}
                    </ol>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Developer Tab */}
          {activeTab === 'developer' && (
            <div className="space-y-4 animate-fadeIn">
              <h2 className="text-xl font-bold mb-4">Developer Reference</h2>
              <div className="bg-slate-900 rounded-2xl border border-slate-800 overflow-hidden">
                <div className="flex items-center justify-between px-4 py-3 border-b border-slate-800 bg-slate-800/50">
                  <span className="text-xs font-medium text-slate-400">Python - yt-dlp Example</span>
                  <button
                    onClick={() => copyToClipboard(developerCode, 'dev-code')}
                    className="flex items-center gap-1 px-2 py-1 rounded-lg hover:bg-slate-700 transition-colors text-xs text-slate-400"
                  >
                    {copiedId === 'dev-code' ? <><Check size={12} className="text-green-400" /> Copied</> : <><Copy size={12} /> Copy</>}
                  </button>
                </div>
                <pre className="p-4 text-sm text-slate-300 overflow-x-auto">
                  <code>{developerCode}</code>
                </pre>
              </div>
            </div>
          )}
        </div>
      </main>
    </div>
  );
}

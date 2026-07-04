import fetch from 'node-fetch';

function detectPlatform(url) {
  const lower = url.toLowerCase();
  if (lower.includes('shopee') || lower.includes('shp.ee')) return 'shopee';
  if (lower.includes('tiktok') || lower.includes('vm.tiktok')) return 'tiktok';
  if (lower.includes('instagram') || lower.includes('instagr.am')) return 'instagram';
  if (lower.includes('facebook') || lower.includes('fb.watch') || lower.includes('fb.com')) return 'facebook';
  if (lower.includes('threads.net') || lower.includes('threads.com')) return 'threads';
  return null;
}

async function extractWithCobalt(url) {
  const response = await fetch('https://co.wuk.sh/api/json', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'Accept': 'application/json'
    },
    body: JSON.stringify({ url: url, vCodec: 'h264', vQuality: '720' })
  });

  if (!response.ok) {
    throw new Error(`Cobalt API error: ${response.status}`);
  }

  const data = await response.json();

  if (data.status === 'redirect' || data.status === 'stream') {
    return { videoUrl: data.url };
  }

  if (data.status === 'picker' && data.picker && data.picker.length > 0) {
    return { videoUrl: data.picker[0].url };
  }

  if (data.url) {
    return { videoUrl: data.url };
  }

  throw new Error(data.text || 'Cobalt API gagal memproses URL');
}

async function extractTikTok(url) {
  const response = await fetch('https://www.tikwm.com/api/', {
    method: 'POST',
    headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
    body: `url=${encodeURIComponent(url)}&hd=1`
  });
  const data = await response.json();
  if (data && data.data) {
    return {
      videoUrl: data.data.hdplay || data.data.play || null,
      title: data.data.title || 'TikTok Video',
      thumbnail: data.data.cover || data.data.origin_cover || null
    };
  }
  throw new Error('Gagal mengekstrak video TikTok');
}

async function extractInstagram(url) {
  // Primary: Cobalt API
  try {
    const result = await extractWithCobalt(url);
    return {
      videoUrl: result.videoUrl,
      title: 'Instagram Video',
      thumbnail: null
    };
  } catch (cobaltError) {
    throw new Error(`Gagal mengekstrak video Instagram: ${cobaltError.message}`);
  }
}

async function extractFacebook(url) {
  // Primary: Cobalt API
  try {
    const result = await extractWithCobalt(url);
    return {
      videoUrl: result.videoUrl,
      title: 'Facebook Video',
      thumbnail: null
    };
  } catch (cobaltError) {
    // Fallback: getmyfb.com
    try {
      const response = await fetch('https://getmyfb.com/process', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/x-www-form-urlencoded',
          'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        },
        body: `id=${encodeURIComponent(url)}&locale=en`
      });
      const html = await response.text();
      const hdMatch = html.match(/href="(https?:\/\/[^"]*)"[^>]*>.*?HD/i);
      const sdMatch = html.match(/href="(https?:\/\/[^"]*)"[^>]*>.*?SD/i);
      const anyMatch = html.match(/href="(https?:\/\/[^"]*\.mp4[^"]*)"/);
      const videoUrl = (hdMatch && hdMatch[1]) || (sdMatch && sdMatch[1]) || (anyMatch && anyMatch[1]);
      if (videoUrl) {
        return {
          videoUrl,
          title: 'Facebook Video',
          thumbnail: null
        };
      }
    } catch (fbError) {
      // Fallback also failed
    }
    throw new Error('Gagal mengekstrak video Facebook. Semua API gagal.');
  }
}

async function extractShopee(url) {
  const response = await fetch(url, {
    headers: {
      'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
    },
    redirect: 'follow'
  });
  const html = await response.text();
  const ogVideoMatch = html.match(/<meta[^>]*property=["']og:video(?::url)?["'][^>]*content=["']([^"']+)["']/i);
  if (ogVideoMatch && ogVideoMatch[1]) {
    return {
      videoUrl: ogVideoMatch[1],
      title: 'Shopee Video',
      thumbnail: null
    };
  }
  // Try alternate pattern
  const videoSrcMatch = html.match(/"videoUrl"\s*:\s*"([^"]+)"/);
  if (videoSrcMatch && videoSrcMatch[1]) {
    return {
      videoUrl: videoSrcMatch[1].replace(/\\u002F/g, '/'),
      title: 'Shopee Video',
      thumbnail: null
    };
  }
  throw new Error('Gagal mengekstrak video Shopee');
}

async function extractThreads(url) {
  // Primary: Cobalt API
  try {
    const result = await extractWithCobalt(url);
    return {
      videoUrl: result.videoUrl,
      title: 'Threads Video',
      thumbnail: null
    };
  } catch (cobaltError) {
    throw new Error(`Gagal mengekstrak video Threads: ${cobaltError.message}`);
  }
}

async function extractUniversal(url) {
  const response = await fetch('https://co.wuk.sh/api/json', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'Accept': 'application/json'
    },
    body: JSON.stringify({ url: url, vCodec: 'h264', vQuality: '720' })
  });

  if (!response.ok) {
    throw new Error('Gagal mengekstrak video. API tidak merespons.');
  }

  const data = await response.json();

  if (data.status === 'redirect' || data.status === 'stream') {
    return {
      videoUrl: data.url,
      title: 'Video',
      thumbnail: null
    };
  }

  if (data.status === 'picker' && data.picker && data.picker.length > 0) {
    return {
      videoUrl: data.picker[0].url,
      title: 'Video',
      thumbnail: null
    };
  }

  if (data.url) {
    return {
      videoUrl: data.url,
      title: 'Video',
      thumbnail: null
    };
  }

  throw new Error(data.text || 'Gagal mengekstrak video. Coba URL lain.');
}

export default async function handler(req, res) {
  // Set CORS headers
  res.setHeader('Access-Control-Allow-Origin', '*');
  res.setHeader('Access-Control-Allow-Methods', 'POST,OPTIONS');
  res.setHeader('Access-Control-Allow-Headers', 'Content-Type');

  // Handle preflight
  if (req.method === 'OPTIONS') {
    return res.status(200).end();
  }

  if (req.method !== 'POST') {
    return res.status(405).json({ success: false, error: 'Method not allowed' });
  }

  try {
    const { url } = req.body || {};

    if (!url) {
      return res.status(400).json({ success: false, error: 'URL diperlukan' });
    }

    const platform = detectPlatform(url);
    let result;

    try {
      switch (platform) {
        case 'tiktok':
          result = await extractTikTok(url);
          break;
        case 'instagram':
          result = await extractInstagram(url);
          break;
        case 'facebook':
          result = await extractFacebook(url);
          break;
        case 'shopee':
          result = await extractShopee(url);
          break;
        case 'threads':
          result = await extractThreads(url);
          break;
        default:
          // Universal fallback
          result = await extractUniversal(url);
          break;
      }
    } catch (platformError) {
      // Try universal fallback if platform-specific extraction fails
      if (platform) {
        try {
          result = await extractUniversal(url);
        } catch (fallbackError) {
          throw new Error(`Semua metode download gagal untuk ${platform}. Error: ${platformError.message}`);
        }
      } else {
        throw platformError;
      }
    }

    return res.status(200).json({
      success: true,
      videoUrl: result.videoUrl,
      title: result.title || 'Video',
      platform: platform || 'unknown',
      thumbnail: result.thumbnail || null
    });
  } catch (error) {
    return res.status(500).json({
      success: false,
      error: error.message || 'Terjadi kesalahan server. Silakan coba lagi.'
    });
  }
}

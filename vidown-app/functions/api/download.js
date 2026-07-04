export async function onRequest(context) {
  const corsHeaders = {
    'Access-Control-Allow-Origin': '*',
    'Access-Control-Allow-Methods': 'POST, OPTIONS',
    'Access-Control-Allow-Headers': 'Content-Type',
    'Content-Type': 'application/json',
  };

  if (context.request.method === 'OPTIONS') {
    return new Response(null, { headers: corsHeaders });
  }

  if (context.request.method !== 'POST') {
    return new Response(JSON.stringify({ success: false, error: 'Method not allowed' }), { status: 405, headers: corsHeaders });
  }

  try {
    const { url } = await context.request.json();
    if (!url) {
      return new Response(JSON.stringify({ success: false, error: 'URL diperlukan' }), { status: 400, headers: corsHeaders });
    }

    const platform = detectPlatform(url);
    let result;
    try {
      switch (platform) {
        case 'tiktok': result = await extractTikTok(url); break;
        case 'instagram':
        case 'threads':
        case 'facebook': result = await extractWithCobalt(url); break;
        case 'shopee': result = await extractShopee(url); break;
        default: result = await extractWithCobalt(url); break;
      }
    } catch (e) {
      try { result = await extractWithCobalt(url); } catch (e2) { throw e; }
    }

    return new Response(JSON.stringify({
      success: true,
      videoUrl: result.videoUrl,
      title: result.title || 'Video',
      platform: platform || 'unknown',
      thumbnail: result.thumbnail || null
    }), { status: 200, headers: corsHeaders });
  } catch (error) {
    return new Response(JSON.stringify({
      success: false,
      error: error.message || 'Terjadi kesalahan server'
    }), { status: 500, headers: corsHeaders });
  }
}

function detectPlatform(url) {
  const lower = url.toLowerCase();
  if (lower.includes('shopee') || lower.includes('shp.ee')) return 'shopee';
  if (lower.includes('tiktok') || lower.includes('vm.tiktok')) return 'tiktok';
  if (lower.includes('instagram') || lower.includes('instagr.am')) return 'instagram';
  if (lower.includes('facebook') || lower.includes('fb.watch') || lower.includes('fb.com')) return 'facebook';
  if (lower.includes('threads.net') || lower.includes('threads.com')) return 'threads';
  return null;
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

async function extractWithCobalt(url) {
  const response = await fetch('https://co.wuk.sh/api/json', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', 'Accept': 'application/json' },
    body: JSON.stringify({ url, vCodec: 'h264', vQuality: '720' })
  });
  if (!response.ok) throw new Error('Cobalt API gagal: ' + response.status);
  const data = await response.json();
  if (data.status === 'redirect' || data.status === 'stream') {
    return { videoUrl: data.url, title: 'Video', thumbnail: null };
  }
  if (data.status === 'picker' && data.picker && data.picker.length > 0) {
    const video = data.picker.find(p => p.type === 'video') || data.picker[0];
    return { videoUrl: video.url, title: 'Video', thumbnail: video.thumb || null };
  }
  if (data.status === 'error') throw new Error(data.text || 'Cobalt error');
  throw new Error('Response tidak dikenali');
}

async function extractShopee(url) {
  const response = await fetch(url, {
    headers: { 'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36' },
    redirect: 'follow'
  });
  const html = await response.text();
  const ogMatch = html.match(/<meta[^>]*property=["']og:video(?::url)?["'][^>]*content=["']([^"']+)["']/i);
  if (ogMatch) return { videoUrl: ogMatch[1], title: 'Shopee Video', thumbnail: null };
  const jsonMatch = html.match(/"(?:videoUrl|playUrl)"\s*:\s*"([^"]+)"/);
  if (jsonMatch) return { videoUrl: jsonMatch[1].replace(/\\u002F/g, '/'), title: 'Shopee Video', thumbnail: null };
  throw new Error('Gagal mengekstrak video Shopee');
}

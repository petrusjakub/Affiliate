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
    let lastError;
    const extractors = getExtractors(platform, url);
    
    for (const extractor of extractors) {
      try {
        result = await extractor();
        if (result && result.videoUrl) break;
      } catch (e) {
        lastError = e;
        continue;
      }
    }

    if (!result || !result.videoUrl) {
      throw lastError || new Error('Semua metode ekstraksi gagal');
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

function getExtractors(platform, url) {
  switch (platform) {
    case 'tiktok':
      return [() => extractTikWM(url), () => extractByFetchingPage(url)];
    case 'instagram':
    case 'threads':
      return [() => extractInstagramV1(url), () => extractByFetchingPage(url)];
    case 'facebook':
      return [() => extractByFetchingPage(url)];
    case 'shopee':
      return [() => extractByFetchingPage(url)];
    default:
      return [() => extractTikWM(url), () => extractByFetchingPage(url)];
  }
}

async function extractTikWM(url) {
  const response = await fetch('https://www.tikwm.com/api/', {
    method: 'POST',
    headers: { 
      'Content-Type': 'application/x-www-form-urlencoded',
      'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
    },
    body: `url=${encodeURIComponent(url)}&hd=1`
  });
  if (!response.ok) throw new Error('TikWM API gagal: ' + response.status);
  const data = await response.json();
  if (data && data.code === 0 && data.data) {
    return {
      videoUrl: data.data.hdplay || data.data.play,
      title: data.data.title || 'TikTok Video',
      thumbnail: data.data.cover || data.data.origin_cover
    };
  }
  throw new Error('TikWM: tidak ada data video');
}

async function extractInstagramV1(url) {
  const response = await fetch('https://v1.saveig.app/api/ajaxSearch', {
    method: 'POST',
    headers: { 
      'Content-Type': 'application/x-www-form-urlencoded',
      'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
      'Origin': 'https://saveig.app'
    },
    body: `q=${encodeURIComponent(url)}&t=media&lang=en`
  });
  if (!response.ok) throw new Error('SaveIG gagal: ' + response.status);
  const data = await response.json();
  if (data && data.data) {
    const mp4Match = data.data.match(/href="(https?:\/\/[^"]*\.mp4[^"]*)"/i);
    const anyMatch = data.data.match(/href="(https?:\/\/[^"]+)"[^>]*download/i) || data.data.match(/href="(https?:\/\/[^"]+)"/i);
    const videoUrl = (mp4Match && mp4Match[1]) || (anyMatch && anyMatch[1]);
    if (videoUrl) {
      return { videoUrl: videoUrl.replace(/&amp;/g, '&'), title: 'Instagram Video', thumbnail: null };
    }
  }
  throw new Error('SaveIG: tidak ditemukan link video');
}

async function extractByFetchingPage(url) {
  const response = await fetch(url, {
    headers: { 
      'User-Agent': 'Mozilla/5.0 (compatible; Googlebot/2.1; +http://www.google.com/bot.html)',
      'Accept': 'text/html,application/xhtml+xml'
    },
    redirect: 'follow'
  });
  if (!response.ok) throw new Error('Gagal mengakses halaman: ' + response.status);
  const html = await response.text();
  
  const ogVideo = html.match(/<meta[^>]*property=["']og:video(?::url)?["'][^>]*content=["']([^"']+)["']/i);
  if (ogVideo && ogVideo[1]) return { videoUrl: ogVideo[1].replace(/&amp;/g, '&'), title: 'Video', thumbnail: null };

  const videoSrc = html.match(/<video[^>]*src=["']([^"']+)["']/i);
  if (videoSrc && videoSrc[1]) return { videoUrl: videoSrc[1].replace(/&amp;/g, '&'), title: 'Video', thumbnail: null };

  const jsonVideo = html.match(/"(?:videoUrl|playUrl|video_url|contentUrl)"\s*:\s*"(https?:\/\/[^"]+)"/i);
  if (jsonVideo && jsonVideo[1]) return { videoUrl: jsonVideo[1].replace(/\\u002F/g, '/').replace(/\\\//g, '/'), title: 'Video', thumbnail: null };

  const sourceSrc = html.match(/<source[^>]*src=["']([^"']+)["'][^>]*type=["']video/i);
  if (sourceSrc && sourceSrc[1]) return { videoUrl: sourceSrc[1].replace(/&amp;/g, '&'), title: 'Video', thumbnail: null };

  throw new Error('Tidak ditemukan video di halaman ini');
}

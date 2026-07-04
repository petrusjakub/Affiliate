const CORS_HEADERS = {
  'Access-Control-Allow-Origin': '*',
  'Access-Control-Allow-Methods': 'POST, OPTIONS',
  'Access-Control-Allow-Headers': 'Content-Type',
};

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
    body: `url=${encodeURIComponent(url)}&hd=1`,
  });
  const data = await response.json();
  if (data && data.data) {
    return {
      videoUrl: data.data.hdplay || data.data.play || null,
      title: data.data.title || 'TikTok Video',
      thumbnail: data.data.cover || data.data.origin_cover || null,
    };
  }
  throw new Error('Gagal mengekstrak video TikTok');
}

async function extractInstagram(url) {
  const response = await fetch('https://co.wuk.sh/api/json', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'Accept': 'application/json',
    },
    body: JSON.stringify({ url }),
  });
  const data = await response.json();
  if (data && data.url) {
    return {
      videoUrl: data.url,
      title: 'Instagram Video',
      thumbnail: null,
    };
  }
  throw new Error('Gagal mengekstrak video Instagram');
}

async function extractFacebook(url) {
  const response = await fetch('https://co.wuk.sh/api/json', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'Accept': 'application/json',
    },
    body: JSON.stringify({ url }),
  });
  const data = await response.json();
  if (data && data.url) {
    return {
      videoUrl: data.url,
      title: 'Facebook Video',
      thumbnail: null,
    };
  }
  throw new Error('Gagal mengekstrak video Facebook');
}

async function extractShopee(url) {
  const response = await fetch(url, {
    headers: {
      'User-Agent':
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    },
    redirect: 'follow',
  });
  const html = await response.text();
  const ogVideoMatch = html.match(
    /<meta[^>]*property=["']og:video(?::url)?["'][^>]*content=["']([^"']+)["']/i
  );
  if (ogVideoMatch && ogVideoMatch[1]) {
    return {
      videoUrl: ogVideoMatch[1],
      title: 'Shopee Video',
      thumbnail: null,
    };
  }
  // Try alternate pattern
  const videoSrcMatch = html.match(/"videoUrl"\s*:\s*"([^"]+)"/);
  if (videoSrcMatch && videoSrcMatch[1]) {
    return {
      videoUrl: videoSrcMatch[1].replace(/\\u002F/g, '/'),
      title: 'Shopee Video',
      thumbnail: null,
    };
  }
  throw new Error('Gagal mengekstrak video Shopee');
}

async function extractThreads(url) {
  const response = await fetch('https://co.wuk.sh/api/json', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'Accept': 'application/json',
    },
    body: JSON.stringify({ url }),
  });
  const data = await response.json();
  if (data && data.url) {
    return {
      videoUrl: data.url,
      title: 'Threads Video',
      thumbnail: null,
    };
  }
  throw new Error('Gagal mengekstrak video Threads');
}

async function extractUniversal(url) {
  const response = await fetch('https://co.wuk.sh/api/json', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'Accept': 'application/json',
    },
    body: JSON.stringify({ url }),
  });
  const data = await response.json();
  if (data && data.url) {
    return {
      videoUrl: data.url,
      title: 'Video',
      thumbnail: null,
    };
  }
  throw new Error('Gagal mengekstrak video. Coba URL lain.');
}

export async function onRequestOptions() {
  return new Response(null, {
    status: 204,
    headers: CORS_HEADERS,
  });
}

export async function onRequestPost(context) {
  try {
    const { url } = await context.request.json();

    if (!url) {
      return new Response(
        JSON.stringify({ success: false, error: 'URL diperlukan' }),
        { status: 400, headers: { 'Content-Type': 'application/json', ...CORS_HEADERS } }
      );
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
          result = await extractUniversal(url);
          break;
      }
    } catch (platformError) {
      // Try universal fallback if platform-specific extraction fails
      if (platform) {
        try {
          result = await extractUniversal(url);
        } catch (fallbackError) {
          throw platformError;
        }
      } else {
        throw platformError;
      }
    }

    return new Response(
      JSON.stringify({
        success: true,
        videoUrl: result.videoUrl,
        title: result.title || 'Video',
        platform: platform || 'unknown',
        thumbnail: result.thumbnail || null,
      }),
      { status: 200, headers: { 'Content-Type': 'application/json', ...CORS_HEADERS } }
    );
  } catch (error) {
    return new Response(
      JSON.stringify({
        success: false,
        error: error.message || 'Terjadi kesalahan server',
      }),
      { status: 500, headers: { 'Content-Type': 'application/json', ...CORS_HEADERS } }
    );
  }
}

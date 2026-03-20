import trafilatura
import aiohttp
import ssl
import certifi

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.5",
    "Accept-Encoding": "gzip, deflate, br",
    "Connection": "keep-alive",
    "Upgrade-Insecure-Requests": "1",
}

async def ingest_url(url: str) -> dict:
    ssl_context = ssl.create_default_context(cafile=certifi.where())

    async with aiohttp.ClientSession(headers=HEADERS) as session:
        async with session.get(
            url,
            timeout=aiohttp.ClientTimeout(total=15),
            ssl=ssl_context
        ) as response:
            if response.status == 403:
                raise ValueError(f"Access denied by website (403). This site blocks automated access.")
            html = await response.text()

    content = trafilatura.extract(
        html,
        include_comments=False,
        include_tables=True,
        no_fallback=False
    )

    if not content or len(content.strip()) < 100:
        raise ValueError("Could not extract meaningful content from this URL.")

    return {
        "content": content.strip(),
        "source_label": url,
        "input_type": "url",
        "word_count": len(content.split())
    }
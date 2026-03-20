from ddgs import DDGS
from app.services.ingest_url import ingest_url

async def ingest_topic(topic: str) -> dict:
    with DDGS() as ddgs:
        search_results = list(ddgs.text(
            topic,
            max_results=10,
            safesearch="moderate"
        ))

    successful = 0
    combined_content = []

    for result in search_results:
        if successful >= 3:
            break

        href = result.get("href", "")

        # Skip low quality domains
        skip_domains = ["login", "faq", "search.php", "forum", "reddit.com/r", "quora.com"]
        if any(skip in href.lower() for skip in skip_domains):
            continue

        try:
            ingested = await ingest_url(href)
            if ingested["word_count"] < 200:
                continue
            source_header = f"SOURCE: {result['title']} ({href})\n"
            combined_content.append(source_header + ingested["content"])
            successful += 1
        except Exception:
            continue

    if not combined_content:
        raise ValueError("Could not find reliable sources for this topic. Try being more specific.")

    content = "\n\n---\n\n".join(combined_content)

    return {
        "content": content,
        "source_label": topic,
        "input_type": "topic",
        "word_count": len(content.split())
    }
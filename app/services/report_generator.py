import httpx
import json
from app.config import GROQ_API_KEY
from typing import AsyncGenerator

GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"

SYSTEM_PROMPT = """You are LUMA, an elite intelligence research agent trusted by investigative journalists, senior policy analysts, and academic researchers.

Your output is a structured intelligence report — not a summary. A report that a senior analyst would be proud to send. Every section must contain real interpretation, not description. Ask: what does this mean? Who benefits? What is the mechanism? What are the second-order effects?

════════════════════════════════════════
MANDATORY REPORT STRUCTURE
════════════════════════════════════════

## Executive Brief
One tight, punchy paragraph. Lead with the single most surprising or consequential finding. Do NOT just introduce the topic — deliver a verdict. A decision-maker reading only this paragraph should walk away with a clear picture.

## By the Numbers
The most important statistics, figures, dates, and quantitative facts in this material. Format each as a bullet. **Bold** every number. Only include figures that genuinely change how you understand the topic. No vague or obvious stats.

## [Your Section — title based on content]
## [Your Section — title based on content]  
## [Your Section — title based on content]
Choose 3 to 5 thematic deep-dive sections. Title them yourself based on what the content actually demands. Each section must:
- Contain a minimum of 180 words of genuine analysis
- Use ### sub-headings when a section has more than 2 distinct angles worth separating
- Include at least one > blockquote isolating a striking fact or quote
- Ask and answer: so what? why does this matter? who is affected?

## Key Players & Power Dynamics
Who are the central actors — individuals, organizations, governments, institutions? What are their actual motivations (not their stated ones)? Where do interests conflict? Who has the most to gain or lose, and why?

## Contested Ground
What is genuinely disputed in this material? Where do credible sources disagree? What claims are unverified, speculative, or suspiciously convenient? Name the tension explicitly — do not smooth it over. Use ⚠ Unverified: prefix for any claim that needs flagging.

## Global Lens
How does this topic look from different geographies, cultures, or political contexts? Who is affected differently based on where they live? What international dimensions are being underreported or ignored entirely?

## What Happens Next
3 to 5 concrete, specific predictions or scenarios for the near term (6 to 24 months). Not vague possibilities — specific, testable forecasts grounded in the evidence presented. Label each with likelihood: **High** / **Medium** / **Low**. Explain the reasoning behind each call.

## Intelligence Gaps
What does this source material NOT tell us? What questions remain completely unanswered? What would an investigative journalist need to find to complete this picture? Be specific — name the exact gaps, not general uncertainty. This section should make the reader want to dig further.

## Key Takeaways
Exactly 5 bullet points. Each must be a complete, standalone insight — not a topic label. Write them as if you are briefing someone who has 60 seconds. Each bullet should be surprising, specific, and actionable.

════════════════════════════════════════
NON-NEGOTIABLE WRITING RULES
════════════════════════════════════════

NEVER do these things:
- Summarize without interpreting — every paragraph must contain analysis, not just description
- Use filler phrases: "it is worth noting", "it is important to understand", "this highlights the fact that", "in conclusion", "in summary", "it should be noted"
- Present speculation as fact — always flag with ⚠ Unverified: prefix
- Explain basic concepts the reader already knows
- Use passive voice when active is possible
- Write vague predictions — every forecast must be specific and testable

ALWAYS do these things:
- **Bold** key terms, names, organizations, and critical figures on first use in each section
- Use > blockquotes to isolate striking data points, direct quotes, or findings worth pausing on
- Use ### sub-headings inside sections when there are clearly distinct angles
- Write at minimum 950 words total — a short report is a failed report
- Write for an intelligent adult who is a senior journalist or policy analyst"""


async def generate_report(content: str, source_label: str) -> AsyncGenerator[str, None]:
    user_message = f"""Produce a full LUMA intelligence report on the following source material.

Source: {source_label}

SOURCE MATERIAL:
{content[:14000]}

Critical reminder: minimum 950 words. Every section must contain genuine analysis. Do not describe — interpret. Do not summarize — evaluate."""

    payload = {
        "model": "llama-3.3-70b-versatile",
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user",   "content": user_message},
        ],
        "max_tokens": 4096,
        "temperature": 0.35,
        "stream": True,
    }

    async with httpx.AsyncClient(timeout=120.0) as client:
        async with client.stream(
            "POST",
            GROQ_URL,
            headers={
                "Authorization": f"Bearer {GROQ_API_KEY}",
                "Content-Type": "application/json",
            },
            json=payload,
        ) as response:
            async for line in response.aiter_lines():
                if not line.startswith("data: "):
                    continue
                data = line[6:]
                if data == "[DONE]":
                    break
                try:
                    chunk = json.loads(data)
                    delta = chunk["choices"][0]["delta"].get("content", "")
                    if delta:
                        yield delta
                except Exception:
                    continue


async def generate_suggestions(report_markdown: str) -> list[str]:
    payload = {
        "model": "llama-3.3-70b-versatile",
        "messages": [
            {
                "role": "system",
                "content": """You are LUMA, a sharp research partner. Read this intelligence report and identify exactly 3 high-value follow-up research directions that are SPECIFIC to this report's actual content.

Each suggestion must be:
- Tied to something specific actually mentioned in this report — not a generic research angle
- Written as a direct, actionable research question
- Something that would genuinely deepen understanding of this specific topic

Return ONLY a valid JSON array of 3 strings. No intro, no explanation, no markdown fences.
Example: ["What lobbying expenditures did ExxonMobil report in the same quarter the policy was reversed?", "How does the WHO's 2019 position on this compare to their current guidance?", "Which of the three clinical trials cited has since been retracted or questioned?"]""",
            },
            {
                "role": "user",
                "content": f"Report:\n\n{report_markdown[:5000]}",
            },
        ],
        "max_tokens": 350,
        "temperature": 0.4,
        "stream": False,
    }

    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.post(
            GROQ_URL,
            headers={
                "Authorization": f"Bearer {GROQ_API_KEY}",
                "Content-Type": "application/json",
            },
            json=payload,
        )
        result = response.json()
        text = result["choices"][0]["message"]["content"].strip()
        text = text.replace("```json", "").replace("```", "").strip()
        try:
            suggestions = json.loads(text)
            return suggestions if isinstance(suggestions, list) else []
        except Exception:
            return []


async def extract_image_keywords(source_label: str, report_markdown: str) -> list[str]:
    """Ask the model what 2 Unsplash search queries would produce the best editorial photos for this report."""
    payload = {
        "model": "llama-3.3-70b-versatile",
        "messages": [
            {
                "role": "system",
                "content": """You are a photo editor choosing images for an editorial intelligence report.

Given a research topic and report excerpt, return exactly 2 short Unsplash search queries that would produce beautiful, relevant, high-quality editorial photographs.

Rules:
- 2 to 4 words per query maximum
- Think visually — what would illustrate this story in a magazine?
- Prefer concrete, photogenic subjects over abstract concepts
- Avoid: "people", "technology", "business", "abstract", "background"
- Good examples: "arctic ice shelf", "semiconductor factory", "election ballot counting", "oil pipeline alaska"

Return ONLY a JSON array of exactly 2 strings. No explanation, no markdown.""",
            },
            {
                "role": "user",
                "content": f"Topic: {source_label}\n\nReport excerpt:\n{report_markdown[:1200]}",
            },
        ],
        "max_tokens": 80,
        "temperature": 0.3,
        "stream": False,
    }

    async with httpx.AsyncClient(timeout=20.0) as client:
        response = await client.post(
            GROQ_URL,
            headers={
                "Authorization": f"Bearer {GROQ_API_KEY}",
                "Content-Type": "application/json",
            },
            json=payload,
        )
        result = response.json()
        text = result["choices"][0]["message"]["content"].strip()
        text = text.replace("```json", "").replace("```", "").strip()
        try:
            keywords = json.loads(text)
            if isinstance(keywords, list) and len(keywords) >= 1:
                return keywords[:2]
        except Exception:
            pass
        return [source_label, source_label + " landscape"]
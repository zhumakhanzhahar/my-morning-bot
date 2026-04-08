import anthropic
import httpx
import os
from datetime import datetime
import pytz

ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")
ALMATY_TZ = pytz.timezone("Asia/Almaty")

CRYPTO_IDS = {
    "BTC": "bitcoin",
    "ETH": "ethereum",
    "SOL": "solana",
    "BNB": "binancecoin",
    "TON": "the-open-network",
}

FOREX_PAIRS = {
    "EUR/USD": ("EUR", "USD"),
    "GBP/USD": ("GBP", "USD"),
    "XAU/USD": ("XAU", "USD"),
}


async def get_crypto_prices() -> dict:
    ids = ",".join(CRYPTO_IDS.values())
    url = f"https://api.coingecko.com/api/v3/simple/price?ids={ids}&vs_currencies=usd&include_24hr_change=true"
    async with httpx.AsyncClient(timeout=10) as client:
        r = await client.get(url)
        r.raise_for_status()
        data = r.json()
    result = {}
    for symbol, cg_id in CRYPTO_IDS.items():
        d = data.get(cg_id, {})
        price = d.get("usd", 0)
        change = d.get("usd_24h_change", 0)
        arrow = "▲" if change >= 0 else "▼"
        result[symbol] = f"${price:,.2f} {arrow}{abs(change):.2f}%"
    return result


async def get_forex_prices() -> dict:
    result = {}
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            r = await client.get("https://api.frankfurter.app/latest?from=USD&to=EUR,GBP")
            r.raise_for_status()
            data = r.json()
        eur_usd = round(1 / data["rates"]["EUR"], 5)
        gbp_usd = round(1 / data["rates"]["GBP"], 5)
        result["EUR/USD"] = f"{eur_usd}"
        result["GBP/USD"] = f"{gbp_usd}"
    except Exception:
        result["EUR/USD"] = "N/A"
        result["GBP/USD"] = "N/A"

    try:
        async with httpx.AsyncClient(timeout=10) as client:
            r = await client.get("https://api.metals.live/v1/spot/gold")
            r.raise_for_status()
            data = r.json()
        xau = data[0].get("gold", 0) if isinstance(data, list) else data.get("gold", 0)
        result["XAU/USD"] = f"${xau:,.2f}"
    except Exception:
        result["XAU/USD"] = "N/A"

    return result


async def generate_ai_content() -> dict:
    client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
    today = datetime.now(ALMATY_TZ).strftime("%d %B %Y")

    prompt = f"""Today is {today}. Generate a daily digest in JSON format with these exact keys:
- "news": array of exactly 5 objects, each with "title" (string, English) and "summary" (string, 1-2 sentences, Russian)
- "quote": object with "text" (string, Russian translation of an inspiring quote) and "author" (string)
- "story": string, 2-3 paragraphs in Russian about one great person's success story (rotate: entrepreneurs, scientists, athletes, philosophers). Make it vivid and motivating.
- "hadith": object with "text" (string, hadith in Russian) and "source" (string, e.g. "Сахих аль-Бухари")
- "chess": object with "position" (string, FEN notation), "task" (string, e.g. "Мат в 2 хода. Белые ходят."), "solution" (string, the moves), "hint" (string, one hint)
- "logic": object with "question" (string, a logic/math puzzle in Russian), "answer" (string), "explanation" (string, brief explanation in Russian)

For chess: use real, classic tactical puzzles. Vary difficulty (mate in 1, 2, or 3).
For crypto news: use the most impactful recent crypto market developments you know about.
For hadith: use authentic hadith about knowledge, effort, patience, or excellence.

Return ONLY the JSON object, no markdown, no explanation."""

    message = client.messages.create(
        model="claude-opus-4-5",
        max_tokens=2000,
        messages=[{"role": "user", "content": prompt}],
    )

    import json, re
    raw = message.content[0].text
    raw = re.sub(r"```json|```", "", raw).strip()
    return json.loads(raw)


def format_prices_block(crypto: dict, forex: dict) -> str:
    lines = ["<b>📊 Цены прямо сейчас</b>"]
    lines.append("")
    lines.append("<i>Crypto</i>")
    for sym, val in crypto.items():
        lines.append(f"  <code>{sym}/USD</code>  {val}")
    lines.append("")
    lines.append("<i>Forex &amp; Metals</i>")
    for pair, val in forex.items():
        lines.append(f"  <code>{pair}</code>  {val}")
    return "\n".join(lines)


def format_news_block(news: list) -> str:
    lines = ["<b>📰 Топ-5 крипто-новостей дня</b>"]
    for i, item in enumerate(news, 1):
        lines.append(f"\n{i}. <b>{item['title']}</b>")
        lines.append(f"   {item['summary']}")
    return "\n".join(lines)


def format_digest(ai: dict, crypto: dict, forex: dict) -> str:
    now = datetime.now(ALMATY_TZ)
    date_str = now.strftime("%A, %d %B %Y • %H:%M Almaty")

    sections = []

    # Header
    sections.append(f"☀️ <b>Дневной дайджест</b>\n<i>{date_str}</i>")

    # Prices
    sections.append(format_prices_block(crypto, forex))

    # News
    sections.append(format_news_block(ai["news"]))

    # Quote
    q = ai["quote"]
    sections.append(f'<b>💬 Цитата дня</b>\n\n<i>"{q["text"]}"</i>\n\n— {q["author"]}')

    # Story
    sections.append(f"<b>🏆 История успеха</b>\n\n{ai['story']}")

    # Hadith
    h = ai["hadith"]
    sections.append(f'<b>☪️ Хадис дня</b>\n\n<i>"{h["text"]}"</i>\n\n<i>— {h["source"]}</i>')

    # Chess
    ch = ai["chess"]
    sections.append(
        f"<b>♟ Шахматная задача</b>\n\n"
        f"<b>{ch['task']}</b>\n\n"
        f"Позиция (FEN): <code>{ch['position']}</code>\n"
        f"🔍 Подсказка: <i>{ch['hint']}</i>\n\n"
        f"✅ Решение: <tg-spoiler>{ch['solution']}</tg-spoiler>"
    )

    # Logic
    lg = ai["logic"]
    sections.append(
        f"<b>🧠 Логическая задача</b>\n\n"
        f"{lg['question']}\n\n"
        f"✅ Ответ: <tg-spoiler>{lg['answer']}\n{lg['explanation']}</tg-spoiler>"
    )

    # Footer
    sections.append("━━━━━━━━━━━━━━━\n<i>Каждый день — шаг к цели. 🇺🇸</i>")

    return "\n\n".join(sections)


async def get_daily_digest() -> str:
    crypto, forex, ai = await asyncio.gather_with_fallback(get_crypto_prices(), get_forex_prices(), generate_ai_content())
    return format_digest(ai, crypto, forex)


# Fix: proper async gather
import asyncio as _asyncio

async def get_daily_digest() -> str:
    crypto_task = get_crypto_prices()
    forex_task = get_forex_prices()
    ai_task = _asyncio.get_event_loop().run_in_executor(None, _sync_ai_content)

    crypto, forex = await _asyncio.gather(crypto_task, forex_task)

    import json, re
    client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
    today = datetime.now(ALMATY_TZ).strftime("%d %B %Y")

    prompt = f"""Today is {today}. Generate a daily digest in JSON format with these exact keys:
- "news": array of exactly 5 objects, each with "title" (string, English) and "summary" (string, 1-2 sentences, Russian)
- "quote": object with "text" (string, Russian translation of an inspiring quote) and "author" (string)
- "story": string, 2-3 paragraphs in Russian about one great person's success story (rotate: entrepreneurs, scientists, athletes, philosophers). Make it vivid and motivating.
- "hadith": object with "text" (string, hadith in Russian) and "source" (string, e.g. "Сахих аль-Бухари")
- "chess": object with "position" (string, FEN notation), "task" (string, e.g. "Мат в 2 хода. Белые ходят."), "solution" (string, the moves), "hint" (string, one hint)
- "logic": object with "question" (string, a logic/math puzzle in Russian), "answer" (string), "explanation" (string, brief explanation in Russian)

For chess: use real, classic tactical puzzles. Vary the puzzle each day.
For crypto news: the most impactful recent crypto market developments.
For hadith: authentic hadith about knowledge, effort, patience, or excellence.

Return ONLY the JSON object, no markdown, no explanation."""

    message = client.messages.create(
        model="claude-opus-4-5",
        max_tokens=2000,
        messages=[{"role": "user", "content": prompt}],
    )

    raw = message.content[0].text
    raw = re.sub(r"```json|```", "", raw).strip()
    ai = json.loads(raw)

    return format_digest(ai, crypto, forex)


def _sync_ai_content():
    pass

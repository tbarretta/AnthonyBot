#!/usr/bin/env python3
"""
Article Summarizer
Fetches an article from a URL, summarizes it with Claude, and reads it aloud.
Usage: python summarize.py <url> [--no-tts] [--save]
"""

import sys
import os
import argparse
from datetime import datetime

import anthropic
import pyttsx3
from gtts import gTTS
from newspaper import Article


def fetch_article(url: str) -> tuple[str, str]:
    """Fetch and parse article text from a URL. Returns (title, text)."""
    print(f"📰 Fetching article from {url}...")
    article = Article(url)
    article.download()
    article.parse()
    if not article.text:
        raise ValueError("Could not extract article text from that URL.")
    return article.title or "Untitled", article.text


def summarize(title: str, text: str) -> str:
    """Summarize article text using Claude."""
    print("🤖 Summarizing with Claude...")
    client = anthropic.Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY"))
    prompt = f"""Please summarize the following article in 2-3 concise paragraphs suitable for reading aloud. 
Focus on the key points and main takeaways. Keep it conversational and clear.

Title: {title}

Article:
{text[:8000]}"""

    message = client.messages.create(
        model="claude-haiku-4-5",
        max_tokens=1024,
        messages=[{"role": "user", "content": prompt}],
    )
    return message.content[0].text


def speak(text: str):
    """Read text aloud using pyttsx3."""
    print("🔊 Reading summary aloud...")
    engine = pyttsx3.init()
    engine.setProperty("rate", 175)   # words per minute
    engine.setProperty("volume", 1.0)
    engine.say(text)
    engine.runAndWait()


def save_audio(title: str, summary: str, output_dir: str = "summaries") -> str:
    """Save summary as an MP3 file using gTTS."""
    os.makedirs(output_dir, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    safe_title = "".join(c if c.isalnum() or c in " -_" else "" for c in title)[:50].strip()
    filename = f"{output_dir}/{timestamp}_{safe_title}.mp3"
    print(f"🎙️  Generating audio file...")
    tts = gTTS(text=summary, lang="en", slow=False)
    tts.save(filename)
    print(f"💾 Audio saved to {filename}")
    return filename


def save_summary(title: str, url: str, summary: str, output_dir: str = "summaries"):
    """Save summary to a text file."""
    os.makedirs(output_dir, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    safe_title = "".join(c if c.isalnum() or c in " -_" else "" for c in title)[:50].strip()
    filename = f"{output_dir}/{timestamp}_{safe_title}.txt"
    with open(filename, "w") as f:
        f.write(f"Title: {title}\n")
        f.write(f"URL: {url}\n")
        f.write(f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M')}\n")
        f.write("-" * 60 + "\n\n")
        f.write(summary)
    print(f"💾 Summary saved to {filename}")
    return filename


def main():
    parser = argparse.ArgumentParser(description="Fetch, summarize, and read an article aloud.")
    parser.add_argument("url", help="URL of the article to summarize")
    parser.add_argument("--no-tts", action="store_true", help="Skip text-to-speech, print only")
    parser.add_argument("--save", action="store_true", help="Save summary to a text file")
    parser.add_argument("--save-audio", action="store_true", help="Save summary as an MP3 file")
    args = parser.parse_args()

    try:
        title, text = fetch_article(args.url)
        print(f"\n📄 Title: {title}\n")

        summary = summarize(title, text)
        print("\n--- Summary ---")
        print(summary)
        print("---------------\n")

        if args.save:
            save_summary(title, args.url, summary)

        if args.save_audio:
            save_audio(title, summary)

        if not args.no_tts:
            speak(summary)

    except Exception as e:
        print(f"❌ Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()

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

import asyncio
import anthropic
import pyttsx3
import edge_tts
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
    """Placeholder — live TTS not supported on WSL. Use --save-audio instead."""
    print("⚠️  Live TTS is not supported on this system. Use --save-audio to generate an MP3.")


def save_audio(title: str, summary: str, voice: str = "en-US-AndrewNeural", output_dir: str = "summaries") -> str:
    """Save summary as an MP3 file using edge-tts."""
    os.makedirs(output_dir, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    safe_title = "".join(c if c.isalnum() or c in " -_" else "" for c in title)[:50].strip()
    filename = f"{output_dir}/{timestamp}_{safe_title}.mp3"
    print(f"🎙️  Generating audio file with voice '{voice}'...")
    async def _generate():
        communicate = edge_tts.Communicate(summary, voice)
        await communicate.save(filename)
    asyncio.run(_generate())
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
    popular_voices = [
        "en-US-AndrewNeural (default, American male)",
        "en-US-BrianNeural  (American male, deep)",
        "en-US-ChristopherNeural (American male, warm)",
        "en-US-GuyNeural    (American male, crisp)",
        "en-US-EricNeural   (American male)",
        "en-GB-RyanNeural   (British male)",
        "en-GB-ThomasNeural (British male)",
        "en-AU-WilliamMultilingualNeural (Australian male)",
        "en-US-AriaNeural   (American female)",
        "en-US-JennyNeural  (American female)",
        "en-GB-SoniaNeural  (British female)",
    ]
    voice_list = "\n  ".join(popular_voices)

    parser = argparse.ArgumentParser(
        description="Fetch an article from a URL, summarize it with Claude, and read it aloud.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=f"""
examples:
  python summarize.py https://example.com/article
  python summarize.py https://example.com/article --no-tts
  python summarize.py https://example.com/article --save
  python summarize.py https://example.com/article --save-audio
  python summarize.py https://example.com/article --save-audio --voice en-GB-RyanNeural
  python summarize.py https://example.com/article --no-tts --save --save-audio

popular voices:
  {voice_list}

tip:
  Run `edge-tts --list-voices` in your venv for the full list of available voices.
"""
    )
    parser.add_argument("url", help="URL of the article to summarize")
    parser.add_argument("--no-tts", action="store_true", help="Skip text-to-speech, print only")
    parser.add_argument("--save", action="store_true", help="Save summary to a text file")
    parser.add_argument("--save-audio", action="store_true", help="Save summary as an MP3 file")
    parser.add_argument("--voice", default="en-US-AndrewNeural", help="Edge TTS voice name (default: en-US-AndrewNeural)")
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
            save_audio(title, summary, voice=args.voice)

        if not args.no_tts and not args.save_audio:
            print("ℹ️  Live TTS is not supported on WSL. Use --save-audio to generate an MP3.")

    except Exception as e:
        print(f"❌ Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()

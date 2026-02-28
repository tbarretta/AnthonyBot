#!/usr/bin/env python3
"""
YouTube Podcast Summarizer
Fetches a YouTube video's transcript/captions, summarizes it with Claude, and reads it aloud.
Usage: python summarize.py <youtube_url> [options]
"""

import sys
import os
import argparse
import asyncio
from datetime import datetime

import anthropic
import edge_tts
import yt_dlp

# Resolve paths relative to this script's directory
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))


def fetch_transcript(url: str) -> tuple[str, str]:
    """Fetch auto-generated captions from a YouTube video. Returns (title, transcript)."""
    print(f"🎬 Fetching transcript from {url}...")

    ydl_opts = {
        "writeautomaticsub": True,
        "writesubtitles": True,
        "subtitlesformat": "vtt",
        "subtitleslangs": ["en", "en-US", "en-GB"],
        "skip_download": True,
        "quiet": True,
        "no_warnings": True,
    }

    # First pass: get video info + check for captions
    with yt_dlp.YoutubeDL({"quiet": True, "no_warnings": True}) as ydl:
        info = ydl.extract_info(url, download=False)

    title = info.get("title", "Untitled")
    duration = info.get("duration", 0)
    print(f"📺 Title: {title}")
    print(f"⏱️  Duration: {duration // 60}m {duration % 60}s")

    # Try automatic captions first, then manual
    subtitles = info.get("automatic_captions") or info.get("subtitles") or {}

    transcript_text = None
    for lang in ["en", "en-US", "en-GB"]:
        if lang in subtitles:
            entries = subtitles[lang]
            # Prefer json3 or srv3 format (easiest to parse), fall back to vtt
            for fmt in ["json3", "srv3", "vtt"]:
                for entry in entries:
                    if entry.get("ext") == fmt:
                        transcript_text = _download_and_parse_subtitles(entry["url"], fmt)
                        if transcript_text:
                            print(f"✅ Got transcript ({lang}, {fmt})")
                            break
                if transcript_text:
                    break
        if transcript_text:
            break

    if not transcript_text:
        raise ValueError(
            "No English captions found for this video. "
            "Try a video with auto-generated captions, or check the URL."
        )

    return title, transcript_text


def _download_and_parse_subtitles(url: str, fmt: str) -> str | None:
    """Download and parse subtitle content from a URL."""
    import urllib.request
    import json
    import re

    try:
        with urllib.request.urlopen(url, timeout=15) as resp:
            raw = resp.read().decode("utf-8")
    except Exception as e:
        print(f"⚠️  Could not download subtitles: {e}")
        return None

    if fmt == "json3":
        try:
            data = json.loads(raw)
            events = data.get("events", [])
            words = []
            for event in events:
                for seg in event.get("segs", []):
                    w = seg.get("utf8", "").strip()
                    if w and w != "\n":
                        words.append(w)
            return " ".join(words)
        except Exception:
            return None

    elif fmt in ("vtt", "srv3"):
        # Strip VTT/XML tags and timestamps
        text = re.sub(r"<[^>]+>", " ", raw)
        text = re.sub(r"\d{2}:\d{2}:\d{2}[.,]\d+ --> .+", "", text)
        text = re.sub(r"WEBVTT.*?\n\n", "", text, flags=re.DOTALL)
        # Collapse whitespace
        lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
        # Deduplicate adjacent identical lines (common in VTT rolling captions)
        deduped = []
        for line in lines:
            if not deduped or line != deduped[-1]:
                deduped.append(line)
        return " ".join(deduped)

    return None


def summarize(title: str, transcript: str) -> str:
    """Summarize transcript using Claude."""
    print("🤖 Summarizing with Claude...")
    client = anthropic.Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY"))

    # Trim transcript to fit context window (roughly 6000 words / ~8000 tokens)
    words = transcript.split()
    if len(words) > 6000:
        print(f"ℹ️  Transcript is long ({len(words)} words) — using first 6000 words.")
        transcript = " ".join(words[:6000])

    prompt = f"""Please summarize the following podcast/video transcript in 3-4 concise paragraphs suitable for reading aloud.
Focus on the key topics discussed, main insights, and important takeaways.
Keep it conversational, clear, and engaging — as if you're telling a friend what the episode was about.

Title: {title}

Transcript:
{transcript}"""

    message = client.messages.create(
        model="claude-haiku-4-5",
        max_tokens=1024,
        messages=[{"role": "user", "content": prompt}],
    )
    return message.content[0].text


def speak(text: str):
    """Read text aloud using pyttsx3."""
    import pyttsx3
    print("🔊 Reading summary aloud...")
    engine = pyttsx3.init()
    engine.setProperty("rate", 175)
    engine.setProperty("volume", 1.0)
    engine.say(text)
    engine.runAndWait()


def save_audio(title: str, summary: str, voice: str = "en-US-AndrewNeural", output_dir: str = None) -> str:
    """Save summary as an MP3 file using edge-tts."""
    if output_dir is None:
        output_dir = os.path.join(SCRIPT_DIR, "summaries")
    os.makedirs(output_dir, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    safe_title = "".join(c if c.isalnum() or c in " -_" else "" for c in title)[:50].strip()
    filename = f"{output_dir}/{timestamp}_{safe_title}.mp3"
    print(f"🎙️  Generating audio with voice '{voice}'...")

    async def _generate():
        communicate = edge_tts.Communicate(summary, voice)
        await communicate.save(filename)

    asyncio.run(_generate())
    print(f"💾 Audio saved to {filename}")
    return filename


def save_summary(title: str, url: str, summary: str, output_dir: str = None):
    """Save summary to a text file."""
    if output_dir is None:
        output_dir = os.path.join(SCRIPT_DIR, "summaries")
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
        description="Fetch a YouTube video's transcript, summarize it with Claude, and read it aloud.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=f"""
examples:
  python summarize.py https://www.youtube.com/watch?v=VIDEO_ID
  python summarize.py https://youtu.be/VIDEO_ID --no-tts
  python summarize.py https://www.youtube.com/watch?v=VIDEO_ID --save
  python summarize.py https://www.youtube.com/watch?v=VIDEO_ID --save-audio
  python summarize.py https://www.youtube.com/watch?v=VIDEO_ID --save-audio --voice en-GB-RyanNeural
  python summarize.py https://www.youtube.com/watch?v=VIDEO_ID --no-tts --save --save-audio

popular voices:
  {voice_list}

tip:
  Run `edge-tts --list-voices` in your venv for the full list of available voices.
  Works best with videos that have auto-generated captions (most English-language podcasts do).
"""
    )
    parser.add_argument("url", help="YouTube video URL to summarize")
    parser.add_argument("--no-tts", action="store_true", help="Skip text-to-speech, print only")
    parser.add_argument("--save", action="store_true", help="Save summary to a text file")
    parser.add_argument("--save-audio", action="store_true", help="Save summary as an MP3 file")
    parser.add_argument("--voice", default="en-US-AndrewNeural",
                        help="Edge TTS voice name (default: en-US-AndrewNeural)")
    args = parser.parse_args()

    try:
        title, transcript = fetch_transcript(args.url)

        summary = summarize(title, transcript)
        print("\n--- Summary ---")
        print(summary)
        print("---------------\n")

        if args.save:
            save_summary(title, args.url, summary)

        if args.save_audio:
            save_audio(title, summary, voice=args.voice)

        if not args.no_tts:
            speak(summary)

    except Exception as e:
        print(f"❌ Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()

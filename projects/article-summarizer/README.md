# Article Summarizer 📰🔊

Fetches an article from a URL, summarizes it with Claude, and reads it aloud.

## Setup

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

Set your Anthropic API key:
```bash
export ANTHROPIC_API_KEY=your_key_here
```

## Usage

```bash
# Summarize and read aloud
python summarize.py https://example.com/article

# Print only, no TTS
python summarize.py https://example.com/article --no-tts

# Save summary to file
python summarize.py https://example.com/article --save

# Both
python summarize.py https://example.com/article --no-tts --save
```

## Requirements

- Python 3.10+
- `espeak-ng` (system package for TTS): `sudo apt install espeak-ng`

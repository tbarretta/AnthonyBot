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

Use `./run.sh` — it handles the virtual environment automatically:

```bash
# Print summary only
./run.sh --no-tts https://example.com/article

# Save summary as text file
./run.sh --save --no-tts https://example.com/article

# Save summary as MP3
./run.sh --save-audio https://example.com/article

# Save both text and MP3
./run.sh --save --save-audio https://example.com/article

# Save MP3 with a different voice
./run.sh --save-audio --voice en-GB-RyanNeural https://example.com/article
```

> **Note:** Live TTS playback is not supported on WSL. Use `--save-audio` to generate an MP3.

## Requirements

- Python 3.10+
- `ANTHROPIC_API_KEY` environment variable set

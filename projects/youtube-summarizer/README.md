# YouTube Podcast Summarizer

Fetches a YouTube video's auto-generated captions, summarizes them with Claude, and reads the summary aloud (or saves it as an MP3).

Works great for podcasts, interviews, talks, and any video with auto-generated English captions.

## Requirements

- Python 3.9+
- `ANTHROPIC_API_KEY` environment variable set

## Setup

```bash
pip install -r requirements.txt
```

## Usage

Use `./run.sh` — it handles the virtual environment automatically:

```bash
# Print summary only
./run.sh --no-tts "https://www.youtube.com/watch?v=VIDEO_ID"

# Save summary as text file
./run.sh --save --no-tts "https://www.youtube.com/watch?v=VIDEO_ID"

# Save summary as MP3
./run.sh --save-audio "https://www.youtube.com/watch?v=VIDEO_ID"

# Save both text and MP3
./run.sh --save --save-audio "https://www.youtube.com/watch?v=VIDEO_ID"

# Save MP3 with a different voice
./run.sh --save-audio --voice en-GB-RyanNeural "https://www.youtube.com/watch?v=VIDEO_ID"
```

> **Note:** Live TTS playback is not supported on WSL. Use `--save-audio` to generate an MP3.

> **Always wrap URLs in quotes.** YouTube URLs contain `&` which the shell interprets as a background operator without them — causing the script to hang.

## Options

| Flag | Description |
|---|---|
| `--no-tts` | Skip live text-to-speech playback |
| `--save` | Save summary text to `summaries/` folder |
| `--save-audio` | Save summary as MP3 in `summaries/` folder |
| `--voice` | Edge TTS voice (default: `en-US-AndrewNeural`) |

## Popular Voices

- `en-US-AndrewNeural` — American male (default)
- `en-US-BrianNeural` — American male, deep
- `en-US-ChristopherNeural` — American male, warm
- `en-GB-RyanNeural` — British male
- `en-US-AriaNeural` — American female
- `en-US-JennyNeural` — American female

Run `edge-tts --list-voices` for the full list.

## How It Works

1. **yt-dlp** fetches the video's auto-generated English captions (no audio download needed)
2. Captions are cleaned and deduplicated
3. **Claude** (Haiku) summarizes the transcript in 3-4 conversational paragraphs
4. Summary is printed and optionally read aloud or saved as MP3

## Notes

- Works best with videos that have auto-generated captions (most English podcasts do)
- Long transcripts are trimmed to ~6,000 words before summarization
- Summaries are saved to a `summaries/` folder in the project directory

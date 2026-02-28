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

```bash
# Summarize and read aloud
python summarize.py https://www.youtube.com/watch?v=VIDEO_ID

# Print only, no TTS
python summarize.py https://youtu.be/VIDEO_ID --no-tts

# Save summary as text file
python summarize.py https://www.youtube.com/watch?v=VIDEO_ID --save

# Save summary as MP3
python summarize.py https://www.youtube.com/watch?v=VIDEO_ID --save-audio

# Save MP3 with a different voice
python summarize.py https://www.youtube.com/watch?v=VIDEO_ID --save-audio --voice en-GB-RyanNeural

# All options combined
python summarize.py https://www.youtube.com/watch?v=VIDEO_ID --no-tts --save --save-audio
```

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

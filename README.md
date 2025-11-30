# Telegram Media Loader

A polished showcase of a Telegram automation tool that downloads every media file via a user session, catalogs it into topic-aware folders, and keeps full metadata/ledger coverage with both CLI and Tkinter landing pages.

## Why it catches recruiters' eyes

- **Production-ready reliability** – deduplicated downloads, logging to `logs/app.log`, and a SQLite ledger (`data/state.sqlite`) prove you can ship resilience.
- **Forum/topic intelligence** – media is grouped by forum topics, album IDs, and dates, demonstrating non-trivial filesystem craftsmanship.
- **Dual UX proof** – the CLI and GUI share a single backend, highlighting your ability to compose reusable application layers.
- **Observability at scale** – every download writes a structured `metadata.ndjson` line, so you can confidently talk about monitoring and analytics.

## Stack

- Python 3.11+ (works on 3.10 once Telethon is installed)
- [Telethon](https://github.com/LonamiWebs/Telethon) for Telegram API access via a user session
- Tkinter (standard library) for the desktop GUI
- `python-dotenv`, `PyYAML`, `tqdm`, and `tzdata` for configuration, progress, and timezone handling

## Installation

```bash
git clone https://example.com/telegram_media_loader.git
cd telegram_media_loader
python -m venv .venv
./.venv/Scripts/activate   # on Windows
pip install -e .
```

Copy `.env.example` to `.env` and fill in `TG_API_ID`, `TG_API_HASH`, `TG_PHONE_NUMBER`, and `TG_SESSION_NAME`. Copy `config.example.yaml` to `config.yaml` to set defaults such as:

```yaml
output_root: downloads
default_media_types:
  - photo
  - video
  - document
  - voice
  - audio
  - sticker
  - gif
log_level: INFO
sqlite_path: data/state.sqlite
tz: UTC
```

### Environment secrets

The loader reads sensitive values from `.env`: `TG_API_ID`, `TG_API_HASH`, `TG_PHONE_NUMBER`, and (optional) `TG_SESSION_NAME`. CLI flags override config, and config overrides `.env` when defaults collide.

## CLI usage

```bash
python -m telegram_media_loader \
  --chat-url https://t.me/some_channel \
  --output-root "D:/tg_downloads" \
  --date-from 2024-01-01 \
  --date-to 2024-03-31 \
  --media-types photo,video,document \
  --config config.yaml \
  --log-level INFO
```

### CLI options

- `--chat-url`: required; accepts `https://t.me/<username>`, `https://t.me/c/<internal_id>`, or the special values `me`/`self`.
- `--output-root`: overrides the YAML root path.
- `--date-from` / `--date-to`: inclusive UTC datetimes (e.g. `2024-02-01`, `2024-02-01T12:30`). Missing values fetch the entire history.
- `--media-types`: comma-separated list (photo, video, document, voice, audio, sticker, gif, other).
- `--config`: YAML or JSON config file (defaults to `config.yaml`).
- `--log-level`: overrides INFO, DEBUG, or ERROR for both console and file output.

## Metadata

Every chat writes `metadata.ndjson` inside `<output_root>/<chat_slug>/metadata.ndjson`. Each line records fields such as:

```
chat_id, chat_username, chat_title, chat_type,
message_id, grouped_id, topic_id, topic_title, date_iso (UTC),
sender_id, sender_username, sender_display_name, text_raw, reply_to_message_id,
media_type, file_path (relative), file_size, mime_type,
has_spoiler, is_forwarded, forward_from_id, forward_from_username, extra
```

This structured output is ideal evidence of observability for recruiters.

## Filesystem layout

```
<output_root>/
  <chat_slug>/
    <topic_slug_or___root>/
      YYYY-MM-DD/
        <message_id>_<media_index>_<media_type>.<ext>
```

Topic folders come from the forum title or fallback ID (`topic-<id>`); albums use the first message ID as a subfolder so bulk uploads stay together.

## SQLite ledger

`data/state.sqlite` tracks the `downloaded_media` table with columns like:

- `chat_id`, `message_id`, `media_index`, `media_type`
- `file_path`, `file_size`, `mime_type`, `date_iso`, `downloaded_at`, `status`
- A unique constraint on `(chat_id, message_id, media_index)` ensures reruns skip repeats.

Failed attempts are logged, and metadata entries are still appended so you can diagnose retries.

## Logging

`logs/app.log` records structured entries such as `[2024-01-01 12:00:00] INFO telegram_media_loader.cli - message`. Console output mirrors INFO+ERROR logs to keep the experience consistent.

## GUI

Launch the GUI with:

```bash
python -m telegram_media_loader.gui
```

Or simply run:

```bash
python gui.py
```

It prompts for phone/code (plus 2FA if needed), then reuses the CLI backend. The fields mirror CLI flags and support right-click copy/paste for URL/output reuse. Hit **Start** to run the background download thread and watch log output in the window.

![GUI dashboard](docs/screenshots/gui-dashboard.png)

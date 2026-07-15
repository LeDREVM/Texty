# Audit — Texty / Transcripteur Audio Pro

Date : 2026-07-15
Scope : full codebase (Flask backend, `utils/` modules, frontend JS, templates, repo structure).
Areas: functional bugs, security, structure/deploy, code quality.

Legend: **[FIXED]** applied in this change · **[REPORTED]** documented, follow-up required.

---

## Executive summary

The project **did not run** before this audit: `utils/audio_processor.py` had a fatal
`IndentationError`, the app crashed at import (log directory created after the log handler),
and even once importable the home page and static assets 404'd due to folder casing/placement.
There was no `requirements.txt` and no `wsgi.py`, so neither the documented dev nor prod start
command worked.

The **backend is now functional and hardened**. The main remaining gap is the **frontend**, which
references JavaScript modules and a stylesheet that do not exist (or are empty) — this needs a
follow-up because completing it is net-new feature work, not a defect fix.

---

## Functional bugs

- **[FIXED] F1 — Critical — `utils/audio_processor.py`**: `batch_process()` ended with
  `return processed_files_segment[start_ms:end_ms]` plus a block of orphaned, mis-indented code,
  causing an `IndentationError` that broke the import of the entire application. Restored to
  `return processed_files` and removed the orphaned lines.
- **[FIXED] F2 — Critical — `extract_segment()`**: the PyDub branch computed `start_ms/end_ms`
  but never sliced/exported and referenced an undefined `output_path`. Restored the missing
  slice + export (the code that had been mis-pasted into `batch_process`).
- **[FIXED] F3 — High — template folder**: Flask expects `templates/`; the folder was `Templates`,
  breaking `render_template('index.html')` on case-sensitive Linux. Renamed to `templates/` and
  set an explicit `template_folder`.
- **[FIXED] F4 — High — static files**: `static/` lives at the repo root but the app runs from
  `ranscripteur-audio-pro/`; the default handler and a redundant custom `/static/<path>` route
  both pointed at a non-existent directory. Set `static_folder` to the repo-root `static/` and
  removed the custom route.
- **[FIXED] F5 — Medium — import-time crash**: `logging.FileHandler('logs/app.log')` ran before
  the `logs/` directory was created. Directories are now created (anchored to the app dir) before
  logging is configured.
- **[FIXED] F6 — Medium — `/api/convert_format`**: `request.get_json()` returned `None` on
  non-JSON bodies → `AttributeError` → 500. Now uses `get_json(silent=True)` and returns 400.
- **[FIXED] F7 — Medium — numeric params**: unguarded `float(...)` on form fields → 500 on bad
  input. Added a `parse_float()` helper that validates and clamps, returning 400.
- **[FIXED] F8 — Low — model/format validation**: `model`, `language`, and `format` are now
  validated against allowed sets before use.
- **[REPORTED] F9 — Low — fake diarization**: `TranscriptionEngine.detect_speakers()` returns
  hardcoded simulated speakers while the README advertises real detection. Left as-is (integrating
  `pyannote.audio` is feature work); recommend labeling it experimental in the UI until then.

## Security

- **[FIXED] S1 — High — open CORS**: `CORS(app)` allowed every origin on every route. Now scoped
  to `CORS_ORIGINS` (default localhost), configurable per environment.
- **[FIXED/REPORTED] S2 — High — debug/bind**: debug stays off by default; README no longer
  advises enabling it in production and the `.env` sample sets `FLASK_DEBUG=False`. Binding to
  `0.0.0.0` is retained (needed behind Hostinger/gunicorn) — run behind a reverse proxy.
- **[FIXED] S3 — Medium — error disclosure**: endpoints returned `str(e)` to clients. They now
  return generic messages and log details server-side via `logger.exception`.
- **[FIXED] S4 — Medium — DOM XSS**: `showToast()` injected user-controlled filenames via
  `innerHTML`, and `showAutoSuggestions()` injected `item.action.toString()` into an inline
  `onclick`. Both now build DOM nodes with `textContent` and real event listeners.
- **[REPORTED] S5 — Medium — no auth / rate limiting**: upload/transcription endpoints are
  unauthenticated and CPU-heavy (100 MB uploads) → resource-exhaustion risk. Recommend adding
  authentication and per-IP rate limiting (e.g. `flask-limiter`) before public exposure.
- **[FIXED] S6 — Low — temp collisions**: second-granularity timestamped temp names could collide
  under concurrency. Now use `uuid4()` via a `safe_temp_path()` helper.
- **[FIXED] S7 — Low — download/cleanup race**: `finally` deleted files that `send_file` might
  still be streaming. Files are now read into memory (`BytesIO`) before cleanup.

## Structure / deploy

- **[FIXED] D1 — High**: added `requirements.txt` at the repo root.
- **[FIXED] D2 — High**: added `ranscripteur-audio-pro/wsgi.py` exposing `application`
  (`gunicorn wsgi:application` now works).
- **[FIXED] D3 — Medium**: template/static layout resolved via explicit `template_folder` /
  `static_folder` and path anchoring; the app now works regardless of the current directory
  (`utils/` is put on `sys.path` from the app).
- **[REPORTED] D4 — Low**: top-level dir is misspelled `ranscripteur-audio-pro` (missing "T").
  Left unchanged to avoid churning `wsgi`/run paths and docs; rename is a safe optional cleanup.
- **[FIXED] D5 — Low**: removed stray empty files `utils/dd`,
  `utils/Transcripteur Audio Web.html`, `ranscripteur-audio-pro/README.md`.
- **[FIXED] D6 — Low**: README `.env` sample now uses `FLASK_DEBUG`/`MAX_FILE_SIZE`/`CORS_ORIGINS`
  (dropped deprecated `FLASK_ENV`); fixed the `Requirements.txt` casing reference.

## Frontend assets (surfaced during verification)

- **[FIXED] Low**: `index.html` referenced `/static/css/style.css` but the file was `styles.css`.
  Renamed the file to match.
- **[REPORTED] High — missing JS modules**: `index.html` loads `/static/js/audio-processor.js`
  and `/static/js/transcription.js`, **neither of which exists**. Functions they must provide —
  e.g. `startTranscription()`, `analyzeAudioQuality()`, `loadCurrentEnhancementSettings()`,
  `updateExportPreview()` — are called from `app.js` but defined nowhere, so the Transcribe /
  quality-analysis / export actions fail client-side. Completing these modules is feature work
  and needs the intended DOM contract; it was **not** implemented here.
- **[REPORTED] Medium — empty stylesheet**: `static/css/style.css` is 0 bytes, so no styling
  ships. Needs a real stylesheet.

## Code quality

- **[FIXED] Q1**: removed a duplicated comment in `transcription_engine.py`.
- **[FIXED] Q3**: `TranscriptionEngine` no longer raises at construction when no engine is
  installed (it would crash the whole app import); the error is raised only when a transcription
  is actually requested, so the web UI and info endpoints stay available.
- **[FIXED] Q4**: `FormatConverter` advertised a `pdf` format it never implemented; removed it
  from the supported list (unknown formats now raise cleanly).
- **[FIXED] Q5**: dropped unused imports in `app.py` (`io`, `json`, `asyncio`, `tempfile`, typing).
- **[FIXED] Q6**: `_transcribe_whisper` fallback loaded a hardcoded `"small"`; now uses the
  requested model size.
- **[REPORTED] Q2/Q7**: some broad/bare `except` blocks remain in non-critical cleanup paths, and
  the README has duplicated header content — minor, left for a later cleanup.

---

## Verification performed

- `python -m py_compile` passes for `app.py`, all `utils/*.py`, and `wsgi.py` (previously
  `audio_processor.py` failed to compile).
- `utils/format_converter.py` exercised end-to-end (stdlib only): `text/srt/vtt/json/csv/docx`
  all produce output; `pdf` is now rejected with a clear `ValueError`.
- Static wiring confirmed against `index.html`'s actual references.

**Not verifiable in this environment**: a live Flask boot and the full Whisper/librosa
transcription path — the sandbox has no network egress to install Flask/numpy/ML dependencies.
Once `pip install -r requirements.txt` succeeds, verify:
`GET /` (renders), `GET /static/js/app.js` (200), `GET /api/health` & `/api/formats` (200),
`POST /api/convert_format` with an empty body (400, not 500).

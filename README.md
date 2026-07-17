# Live Explanation

A Chrome extension + local backend that listens to a video's audio, transcribes it in real time, and (soon) explains jargon as it's spoken — as a sidebar when the tab is windowed, and overlaid when the video is fullscreen.

## How it fits together

```
Video's audio  →  Chrome extension captures it  →  WebSocket  →  Backend
                                                                     │
                                                          faster-whisper transcribes
                                                                     │
                                                            (LLM explanation — coming soon)
```

- `frontend/extension/` — the Chrome extension. Taps a video's audio without touching playback, and streams it to the backend.
- `backend/` — a FastAPI server. Receives audio, transcribes it with faster-whisper, and (in progress) sends it to an LLM for jargon detection.
- `frontend/src/` — the React app that will render the sidebar/overlay UI.

## Prerequisites

- Python 3.12+ and [uv](https://docs.astral.sh/uv/)
- Node.js and npm
- Google Chrome 

## 1. Start the backend

```bash
cd backend
uv sync 
uv run uvicorn main:app --reload --port 8000
```
uv sync downloads needed libraries, and uv run executes backend
Wait for `Whisper model loaded and ready.` in the terminal — that means it's up. **Keep this terminal open**; it streams live transcription output while you test, so open a separate terminal tab for anything else.

The first run downloads the Whisper model weights, which takes a moment.

## 2. Build the extension

```bash
cd frontend
npm install
npm run build:extension
```

This compiles `extension/content_script.tsx` and `extension/background.ts` into `extension/dist/`. Re-run this command any time you edit either of those two files — it does **not** watch for changes automatically.

> `extension/audio_processor.js` is plain JavaScript and needs no build step — edits to it take effect the next time the extension reloads (see below).

## 3. Load the extension in Chrome

Use a **separate Chrome profile** for testing, not your main one — this extension requests broad permissions (`tabs`, `scripting`, and injection into every `https://` page).

1. Click your profile icon (top-right in Chrome) → **Add** → **Continue without an account**.
2. In the new profile window, go to `chrome://extensions`.
3. Toggle **Developer mode** on (top-right).
4. Click **Load unpacked** and select the `frontend/extension` folder (not `dist`).

## 4. Test it

1. In the test profile, open any page with an HTML5 `<video>` and play it.
2. Watch the **backend terminal** — every few seconds you should see a line like:
   ```
   Transcription took 0.4s — text: this is a test of the transcription pipeline.
   ```
   This is your transcript quality check.
3. To check the extension's connection, go to `chrome://extensions`, click **"service worker"** under the Live Explanation card to open its console, and confirm you see `WebSocket connected to FastAPI backend`.

## After editing code

| You changed...                                  | You need to...                                                                 |
|--------------------------------------------------|----------------------------------------------------------------------------------|
| `backend/*.py`                                    | Restart uvicorn (or save — `--reload` restarts it for you)                      |
| `extension/content_script.tsx` or `background.ts` | Re-run `npm run build:extension`, then reload the extension in `chrome://extensions`, then refresh the video page |
| `extension/audio_processor.js`                    | Reload the extension in `chrome://extensions`, then refresh the video page (no build needed) |
| `frontend/src/*` (the React sidebar app)           | N/A yet — not wired up to the extension                                          |

## Project status

- ✅ Audio capture (extension → backend over WebSocket)
- ✅ Real-time transcription (faster-whisper, `base` model, VAD-filtered)
- ✅ LLM jargon detection (with space for possible improvements)
- 🚧 Streaming explanations back to the frontend
- 🚧 React sidebar/overlay UI

## How the frotend may look like (The goal)

Attaches itself to videos in full screen, acts as a sidebar
outside of full screen independent of the video.

Contains a button to adjust latency, which determines
how fast they want explanations. High latency = more accumulated context per LLM message and slower speeds

Perhaps we can add a translation button.
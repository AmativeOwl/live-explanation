# Live Explanation

A Chrome extension + local backend that listens to a video's audio, transcribes it in real time, and (soon) explains jargon as it's spoken — as a sidebar when the tab is windowed, and overlaid when the video is fullscreen.

## How it fits together

```
Video's audio  →  Chrome extension captures it  →  WebSocket  →  Backend
                                                                     │
                                                          faster-whisper transcribes
                                                                     │
                                                            LLM explanation
```

- `frontend/extension/` — the Chrome extension. Taps a video's audio without touching playback, and streams it to the backend.
- `backend/` — a FastAPI server. Receives audio, transcribes it with faster-whisper, and (in progress) sends it to an LLM for jargon detection.
- `frontend/src/` — the React app rendering the sidebar/overlay UI. Bundled into the extension via `content_script.tsx`, which mounts it directly into the page.

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
uv sync downloads needed libraries, and uv run executes backend.
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
| `frontend/src/*` (the React sidebar app)           | It's bundled into `content_script.js` by `content_script.tsx`'s import — re-run `npm run build:extension`, then reload the extension and refresh the video page, same as editing the content script itself. `npm run dev` (the standalone page at `localhost:5173`) is only for previewing UI changes quickly — it's not what the extension actually loads |

## Project status

- ✅ Audio capture (extension → backend over WebSocket)
- ✅ Real-time transcription (faster-whisper, `base` model, VAD-filtered)
- ✅ LLM jargon detection (with space for possible improvements)
- ✅ Streaming explanations back to the frontend
- ✅ React panel mounted into the page, reparenting into fullscreen (basic version — no styling/positioning polish yet)

## How the frotend may look like (The goal)

Attaches itself to videos in full screen, acts as a sidebar
outside of full screen independent of the video.

You should be able to scroll upwards towards older explanations. 

Contains a button to adjust latency, which determines
how fast they want explanations. High latency = more accumulated context per LLM message and slower speeds

Perhaps we can add a translation button.

## Things to add

- **Split `explanation` into two fields.** Right now one field has to be both a quick, plain-language summary of what's being said *and* carry deeper insight (why/how, comparisons, caveats) — those two goals fight each other. Add a second field (e.g. `comment`/`insight`) dedicated to the deeper analysis, so `explanation` can stay short and plain while the new field does the teaching. Like `jargon_terms`, it should be allowed to come back empty on sentences that genuinely have nothing deeper to add (e.g. administrative/logistics lines) rather than forcing manufactured insight. Needs a backend prompt/schema change plus a frontend change to display the new field.

- **Give the frontend real control over its own connection to the pipeline, not just a fire-and-forget socket.** `App.tsx` opens its WebSocket to `/explanations` once on mount and never retries — if the backend isn't up yet when the page loads, or the connection drops, the panel is stuck silently until the page is refreshed. Compare to `background.ts`'s audio socket, which already reconnects every 3s on close. Once the panel is a real UI (not just a test page), this should go further than "add a retry loop": surface connection state to the user (connected / reconnecting / backend unreachable) so they know *why* explanations stopped, and once the latency-adjustment button from the goals section exists, that's also "control of the pipeline" that needs a real channel from frontend → backend (currently there's no frontend → backend messaging at all, only backend → frontend).
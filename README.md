# Live Explanation

A Chrome extension + local backend that listens to a video's audio, transcribes it in real time, and explains jargon as it's spoken — as a persistent panel that stays visible whether the video is windowed or fullscreen.

## How it fits together

```
Video's audio  →  Chrome extension captures it  →  WebSocket  →  Backend
                                                                     │
                                                          faster-whisper transcribes
                                                                     │
                                                            LLM explanation
```

- `frontend/extension/` — the Chrome extension. Taps a video's audio without touching playback, and streams it to the backend.
- `backend/` — a FastAPI server. Receives audio, transcribes it with faster-whisper, and sends it to an LLM for jargon detection and explanation.
- `frontend/src/` — the React app rendering the sidebar/overlay UI. Bundled into the extension via `content_script.tsx`, which mounts it directly into the page.

## Prerequisites

- Python 3.12+ and [uv](https://docs.astral.sh/uv/)
- Node.js and npm
- Google Chrome 

## Quick start

Once you've done the one-time `uv sync` / `npm install` / load-the-extension setup below (steps 1-3), starting a session each time is just:

```bash
./dev.sh
```

This rebuilds the extension and starts the backend in one command, no need to `cd` between folders or run two separate commands. It doesn't replace steps 2-3 the first time (you still need `npm install` once, and the extension still needs to be loaded into Chrome once), and it doesn't reload the extension in Chrome for you, that's still a manual click in `chrome://extensions`, but only actually needed when you've edited `content_script.tsx`, `background.ts`, or `App.tsx` since Chrome last loaded it (see the table below).

## 1. Start the backend

Once you've done the one-time setup below, `./dev.sh` from the project root rebuilds the extension and starts the backend in one command — see [Quick start](#quick-start) below. First time through, do it manually so each step is clear:

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

1. In the test profile, open any page with an HTML5 `<video>` and play it. You should see the panel appear pinned to the middle-right of the page.
2. Watch the **backend terminal** — every few seconds you should see a line like:
   ```
   Transcription took 0.4s — text: this is a test of the transcription pipeline.
   ```
   This is your transcript quality check. A little later, look for `LLM explanation: {...}` — that's the jargon/insight call succeeding.
3. There are actually **two** separate connections to the backend, and both need to be up for everything to work:
   - Audio in, from `background.ts`. Check by going to `chrome://extensions`, clicking **"service worker"** under the Live Explanation card, and confirming you see `WebSocket connected to FastAPI backend`. The backend terminal should also print `Chrome extension connected.`.
   - Explanations out, from the panel itself (`App.tsx`, running inside the page). The backend terminal should print `React frontend connected.`. If it never does, check the site permissions on the video's tab (padlock icon in the address bar → Site settings) for something like "Local network access" set to Block — Chrome gates any page script's access to `localhost` behind a permission prompt, and this connection is the one subject to it (the audio-in socket runs from the extension's privileged background script, so it isn't).
4. The first time a video starts playing, Chrome may log `The AudioContext was not allowed to start...` — this is expected and handled: audio capture waits for your first click or keypress on the page (browsers require a real user gesture before allowing audio to start), which normally happens the instant you click play.

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
- ✅ `insight` field — a second, optional layer of analysis (why/how, comparison, example, caveat) separate from the plain `explanation`
- ✅ Resilience fixes: clean WebSocket disconnect handling on the backend (no more `RuntimeError` crashes when the extension disconnects), debounced "new video" detection (YouTube's adaptive streaming can fire several spurious source-reload events in a row for ads/quality switches/seeking, not just real navigation), `AudioContext` resume tied to a real user gesture instead of relying on the browser's autoplay heuristics, and exponential-backoff reconnection for the frontend's `/explanations` socket

## How the frotend may look like (The goal)

Attaches itself to videos in full screen, acts as a sidebar
outside of full screen independent of the video.

You should be able to scroll upwards towards older explanations. 

Contains a button to adjust latency, which determines
how fast they want explanations. High latency = more accumulated context per LLM message and slower speeds

Perhaps we can add a translation button.

## Things to add

- **Surface connection state to the user, not just recover silently.** The frontend socket now reconnects with backoff on its own, but the panel gives no indication *why* explanations stopped if the backend's unreachable for a while — a small "reconnecting..." state would close that gap.
- **A real frontend → backend control channel.** Right now data only flows one way (backend → frontend). Once the latency-adjustment button from the goals section below exists, that's a case of the frontend needing to tell the backend something, and there's no channel for that yet.
- **Shadow DOM for the injected panel**, so its styles are fully isolated from whatever page it's injected into (and vice versa) — a prerequisite before bringing in a real stylesheet or Tailwind (currently unused despite being installed) instead of the inline `style={{}}` objects everywhere.

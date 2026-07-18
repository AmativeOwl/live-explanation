import asyncio
import json
from dotenv import load_dotenv
import time
import numpy as np
from faster_whisper import WhisperModel  # type: ignore
from faster_whisper.vad import get_speech_timestamps, VadOptions  # type: ignore
from fastapi import FastAPI, WebSocket
from fastapi.websockets import WebSocketDisconnect
from contextlib import asynccontextmanager

from llm import detect_jargon, reset_context

load_dotenv()

SAMPLE_RATE = 16000  # must match the rate audio_processor.js resamples to

# model
print("Loading Whisper model...")
model = WhisperModel(model_size_or_path="base", device="cpu", compute_type="int8")
print("Whisper model loaded and ready.")


class _ResetSignal:
    """Sentinel put on audio_queue to mark a viewer switching to a new video.
    Distinct from np.ndarray so transcription_pipeline() can tell it apart
    from a real audio chunk without ambiguity."""


RESET_SIGNAL = _ResetSignal()

# instantiating asyncio queue
audio_queue: asyncio.Queue[np.ndarray | _ResetSignal] = asyncio.Queue()

# WebSocket clients currently listening for explanations (the React frontend)
frontend_clients: set[WebSocket] = set()


async def broadcast_to_frontend(payload: dict[str, object]) -> None:
    """Sends a JSON payload to every connected frontend client."""
    dead: list[WebSocket] = []
    for client in frontend_clients:
        try:
            await client.send_json(payload)
        except Exception:
            dead.append(client)
    for client in dead:
        frontend_clients.discard(client)

# VAD tuning: groups incoming audio into full spoken utterances by detecting
# real pauses, instead of chopping transcripts at an arbitrary fixed duration.
VAD_OPTIONS = VadOptions(
    min_speech_duration_ms=250,  # discard blips/coughs shorter than this
    min_silence_duration_ms=600,  # pause length that closes an utterance
    max_speech_duration_s=15,  # force-split run-on speech that never pauses
)

# if no speech is detected at all for this long, drop the buffered silence
# rather than let it grow unbounded
MAX_IDLE_BUFFER_SECONDS = 5

# LLM dispatch buffer: merges consecutive confirmed utterances into one larger,
# more comprehensive explanation instead of firing on every single utterance.
# MAX_DISPATCH_WAIT_SECONDS is the real driver — it sets the explanation
# cadence (~every 25s). MIN_DISPATCH_WORDS is a safety cap, not the everyday
# trigger: at typical speaking pace (~2.5 words/sec), 25s of continuous speech
# is already ~60-65 words, so 80 sits above that and only fires early for
# unusually dense/fast speech.
MIN_DISPATCH_WORDS = 80
MAX_DISPATCH_WAIT_SECONDS = 25.0


async def dispatch_to_llm(text: str) -> None:
    """Sends merged transcript text to the LLM and logs the result.

    Runs as a detached background task (see asyncio.create_task below), so
    errors must be caught here — otherwise a failed call (bad key, no
    credits, network error) would fail silently instead of surfacing.
    """
    try:
        result = await detect_jargon(text)
        print(f"LLM explanation: {result}")
        await broadcast_to_frontend(result)
    except Exception as e:
        print(f"LLM call failed: {e}")


def flush_confirmed_segments(
    buffer: np.ndarray,
) -> tuple[list[np.ndarray], np.ndarray]:
    """Runs VAD over `buffer` and splits off any utterances that are confirmed complete.

    A segment is "confirmed" once we know it has actually ended rather than
    just being cut off because no more audio has arrived yet. get_speech_timestamps
    only leaves a segment's end sitting at the buffer's current end when it's
    still mid-utterance and waiting for more audio — every other segment (closed
    by a real pause OR by the max_speech_duration_s force-split) is already final.

    Returns (confirmed utterance audio arrays, remaining unconfirmed buffer).
    """
    # get_speech_timestamps is only loosely typed upstream (-> List[dict]); this
    # annotation reflects the actual {"start": int, "end": int} shape (sample
    # indices) confirmed from faster_whisper/vad.py, so downstream uses of
    # `seg["start"]`/`seg["end"]` are properly typed instead of Unknown.
    segments: list[dict[str, int]] = get_speech_timestamps( # type: ignore
        buffer, VAD_OPTIONS, sampling_rate=SAMPLE_RATE
    )

    if not segments:
        # nothing detected at all — drop stale silence so the buffer doesn't grow forever
        if len(buffer) > MAX_IDLE_BUFFER_SECONDS * SAMPLE_RATE:
            return [], np.array([], dtype=np.float32)
        return [], buffer

    confirmed: list[np.ndarray] = []
    last_confirmed_end = 0

    for i, seg in enumerate(segments):
        is_last = i == len(segments) - 1
        if is_last and seg["end"] >= len(buffer):
            break  # still might be growing — wait for more audio before trusting it
        confirmed.append(buffer[seg["start"] : seg["end"]])
        last_confirmed_end = seg["end"]

    remaining = buffer[last_confirmed_end:]
    return confirmed, remaining


# transcription pipeline
async def transcription_pipeline() -> None:
    """Consumes audio chunks from the queue, groups them into full utterances via VAD,
    transcribes each confirmed utterance, and dispatches merged text to the LLM."""

    buffer: np.ndarray = np.array([], dtype=np.float32)
    pending_text = ""
    pending_since: float | None = None

    while True:
        # wait for a chunk (or a new-video reset signal) to arrive from the queue
        item = await audio_queue.get()

        if isinstance(item, _ResetSignal):
            # viewer switched to a new video — drop all in-progress state so
            # nothing from the previous video bleeds into the new one
            buffer = np.array([], dtype=np.float32)
            pending_text = ""
            pending_since = None
            reset_context()
            print("New video detected — pipeline state reset.")
            continue

        chunk: np.ndarray = item
        buffer = np.concatenate([buffer, chunk])

        confirmed_utterances, buffer = flush_confirmed_segments(buffer)

        for utterance_audio in confirmed_utterances:
            # timestamp before transcription
            t_start = time.perf_counter()

            # vad_filter skips any residual silence within the utterance, which
            # otherwise gets transcribed into garbled or hallucinated text.
            segments, _ = model.transcribe(utterance_audio, language="en", vad_filter=True)  # type: ignore
            transcript = " ".join([seg.text for seg in segments]).strip()

            # timestamp after transcription
            t_end = time.perf_counter()
            print(f"Transcription took {t_end - t_start:.2f}s — text: {transcript}")

            if not transcript:
                continue

            pending_text = f"{pending_text} {transcript}".strip()
            if pending_since is None:
                pending_since = time.perf_counter()

        # Checked every loop tick (not just when a new utterance completes) so a
        # short pending utterance can't get stuck waiting through a long silence —
        # audio chunks keep arriving roughly every 500ms even when no one's talking.
        if pending_text:
            word_count = len(pending_text.split())
            waited_long_enough = (
                pending_since is not None
                and time.perf_counter() - pending_since >= MAX_DISPATCH_WAIT_SECONDS
            )

            if word_count >= MIN_DISPATCH_WORDS or waited_long_enough:
                asyncio.create_task(dispatch_to_llm(pending_text))
                pending_text = ""
                pending_since = None


# lifespan
@asynccontextmanager
async def lifespan(app: FastAPI):  # type: ignore
    """Start the transcription pipeline when the server starts."""
    asyncio.create_task(transcription_pipeline())
    print("Transcription pipeline started.")
    yield


app = FastAPI(lifespan=lifespan)


# status endpoint
@app.get("/status")
async def status() -> dict[str, str]:
    """Health check endpoint."""
    return {"status": "ok"}


# WebSocket - Chrome Extension (audio in, plus control messages like "new video")
@app.websocket("/ws")
async def audio_endpoint(websocket: WebSocket) -> None:
    """Accepts WebSocket connections from the Chrome Extension.

    Two kinds of messages arrive here: binary frames (raw audio bytes) and
    text frames (JSON control messages, e.g. {"type": "new_video"} sent when
    the viewer switches to a different video).
    """
    await websocket.accept()
    print("Chrome extension connected.")
    try:
        while True:
            message = await websocket.receive()

            if "bytes" in message and message["bytes"] is not None:
                chunk = np.frombuffer(message["bytes"], dtype=np.float32)
                await audio_queue.put(chunk)

            elif "text" in message and message["text"] is not None:
                control = json.loads(message["text"])
                if control.get("type") == "new_video":
                    await audio_queue.put(RESET_SIGNAL)

    except WebSocketDisconnect:
        print("Chrome extension disconnected.")


# WebSocket - React frontend (explanations out)
@app.websocket("/explanations")
async def explanations_endpoint(websocket: WebSocket) -> None:
    """Accepts WebSocket connections from the React frontend and streams
    LLM explanations to it as they're produced. The frontend doesn't send
    anything meaningful here — this is a broadcast-only channel."""
    await websocket.accept()
    frontend_clients.add(websocket)
    print("React frontend connected.")
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        frontend_clients.discard(websocket)
        print("React frontend disconnected.")

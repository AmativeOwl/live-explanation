import asyncio
import time
import numpy as np
from faster_whisper import WhisperModel  # type: ignore
from fastapi import FastAPI, WebSocket
from fastapi.websockets import WebSocketDisconnect
from contextlib import asynccontextmanager

# model
print("Loading Whisper model...")
model = WhisperModel(model_size_or_path="tiny", device="cpu", compute_type="int8")
print("Whisper model loaded and ready.")

# instantiating asyncio queue
audio_queue: asyncio.Queue[np.ndarray] = asyncio.Queue()

# sentence buffer
sentence_buffer: str = ""


def is_sentence_boundary(text: str) -> bool:
    """Check if text ends with a sentence boundary."""
    return text.strip().endswith((".", "?", "!"))


# transcription pipeline
async def transcription_pipeline() -> None:
    """Consumes audio chunks from the queue and transcribes them."""
    global sentence_buffer

    while True:
        # wait for a chunk to arrive from the queue
        chunk: np.ndarray = await audio_queue.get()

        # timestamp before transcription
        t_start = time.perf_counter()

        # transcribe the chunk
        segments, _ = model.transcribe(chunk, language="en")  # type: ignore
        transcript = " ".join([seg.text for seg in segments]).strip()

        # timestamp after transcription
        t_end = time.perf_counter()
        print(f"Transcription took {t_end - t_start:.2f}s — text: {transcript}")

        if not transcript:
            continue

        # accumulate into sentence buffer
        sentence_buffer += " " + transcript

        # if we hit a sentence boundary, send to LLM layer
        if is_sentence_boundary(sentence_buffer):
            sentence = sentence_buffer.strip()
            print(f"Complete sentence ready for LLM: {sentence}")
            sentence_buffer = ""  # reset buffer
            # TODO: pass sentence to LLM layer in Phase 4


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


# WebSocket - React frontend
@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket) -> None:
    """Accepts WebSocket connections from the React frontend."""
    await websocket.accept()
    print("React frontend connected.")
    try:
        while True:
            # receive raw audio bytes from frontend
            data: bytes = await websocket.receive_bytes()

            # convert bytes to numpy array and add to queue
            chunk = np.frombuffer(data, dtype=np.float32)
            await audio_queue.put(chunk)

    except WebSocketDisconnect:
        print("React frontend disconnected.")


# WebSocket - Chrome Extension
@app.websocket("/audio")
async def audio_endpoint(websocket: WebSocket) -> None:
    """Accepts WebSocket connections from the Chrome Extension."""
    await websocket.accept()
    print("Chrome extension connected.")
    try:
        while True:
            # receive raw audio bytes from extension
            data: bytes = await websocket.receive_bytes()

            # convert bytes to numpy array and add to queue
            chunk = np.frombuffer(data, dtype=np.float32)
            await audio_queue.put(chunk)

    except WebSocketDisconnect:
        print("Chrome extension disconnected.")

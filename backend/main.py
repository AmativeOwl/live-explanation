import asyncio
import time
import numpy as np
from faster_whisper import WhisperModel  # type: ignore

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

from faster_whisper import WhisperModel  # type: ignore

# instantiate model once at startup — not per request
print("Loading Whisper model...")
model = WhisperModel(
    model_size_or_path="tiny",  # swap to "base" or "small" for better accuracy
    device="cpu",
    compute_type="int8",  # halves memory usage with minimal accuracy loss
)
print("Whisper model loaded and ready.")

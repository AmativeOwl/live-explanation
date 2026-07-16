class AudioProcessor extends AudioWorkletProcessor {
  constructor() {
    super();
    this.buffer = [];

    // `sampleRate` is a built-in global inside every AudioWorkletProcessor —
    // it's the REAL sample rate of the AudioContext that created this node
    // (commonly 48000Hz, sometimes 44100Hz depending on the OS/device).
    // We must not hardcode it, since faster-whisper needs to know exactly
    // how much audio (in seconds) it's receiving.
    //
    // Chunks are sent frequently (every 500ms) rather than buffered into one
    // big window — the backend now does its own VAD-based buffering to group
    // audio into full spoken utterances, so we just need to hand it audio
    // promptly and let it decide where a sentence actually starts and ends.
    this.targetSamples = 0.5 * sampleRate; // 500ms of audio at the native rate

    // faster-whisper is trained on and expects 16kHz mono audio. If we send
    // audio at any other rate, Whisper will misinterpret the playback speed
    // (e.g. 48kHz audio read as 16kHz sounds 3x too fast), producing garbled
    // transcripts even though the captured audio itself is fine.
    this.outRate = 16000;
  }

  // Downsamples `input` (native rate) to `outRate` using linear interpolation.
  // This only affects the copy we send to the backend for transcription —
  // it never touches the audio actually reaching the speakers.
  resample(input, inRate, outRate) {
    if (inRate === outRate) return input; // nothing to do

    const ratio = outRate / inRate;
    const outLength = Math.floor(input.length * ratio);
    const output = new Float32Array(outLength);

    for (let i = 0; i < outLength; i++) {
      // Map each output sample back to a fractional position in the input.
      const inputPos = i / ratio;
      const indexBefore = Math.floor(inputPos);
      const fraction = inputPos - indexBefore;

      const sampleBefore = input[indexBefore];
      // Guard the final sample: there may be no "next" sample to interpolate to.
      const sampleAfter =
        indexBefore + 1 < input.length ? input[indexBefore + 1] : sampleBefore;

      // Blend the two neighbouring samples proportionally to how close
      // `inputPos` sits to each of them.
      output[i] = sampleBefore + (sampleAfter - sampleBefore) * fraction;
    }

    return output;
  }

  process(inputs) {
    const input = inputs[0];

    if (input && input.length > 0) {
      // Capture ONLY (no playback logic) — this node has zero outputs,
      // so nothing here can affect what the user actually hears.

      const channelData = input[0]; // still mono capture
      this.buffer.push(...channelData);

      if (this.buffer.length >= this.targetSamples) {
        // Convert the buffered native-rate samples down to 16kHz before
        // handing them off — this is the format the backend/Whisper expects.
        const resampled = this.resample(
          Float32Array.from(this.buffer),
          sampleRate,
          this.outRate
        );
        this.port.postMessage(resampled);
        this.buffer = [];
      }
    }

    return true;
  }
}

registerProcessor("audio-processor", AudioProcessor);
class AudioProcessor extends AudioWorkletProcessor {
  constructor() {
    super();
    this.buffer = [];
    this.targetSamples = 8 * 44100; // 8 seconds at 44100Hz
  }

  process(inputs) {
    const input = inputs[0];

    if (input && input.length > 0) {
      // 🎙️ Capture ONLY (no playback logic)

      const channelData = input[0]; // still mono capture
      this.buffer.push(...channelData);

      if (this.buffer.length >= this.targetSamples) {
        this.port.postMessage(new Float32Array(this.buffer));
        this.buffer = [];
      }
    }

    return true;
  }
}

registerProcessor("audio-processor", AudioProcessor);
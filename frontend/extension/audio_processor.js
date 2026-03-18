class AudioProcessor extends AudioWorkletProcessor {
  constructor() {
    super();
    this.buffer = [];
    this.targetSamples = 8 * 44100; // 8 seconds at 44100Hz sample rate
  }

  process(inputs) {
    const input = inputs[0];
    if (input && input[0]) {
      // accumulate samples into buffer
      this.buffer.push(...input[0]);

      // when we have 8 seconds worth of samples, send the chunk
      if (this.buffer.length >= this.targetSamples) {
        this.port.postMessage(new Float32Array(this.buffer));
        this.buffer = []; // reset buffer for next chunk
      }
    }
    return true;
  }
}

registerProcessor("audio-processor", AudioProcessor);
/// <reference types="chrome"/>

let isAttached = false;

const attachToVideo = (): void => {
  if (isAttached) return;

  const video = document.querySelector<HTMLVideoElement>("video");

  if (!video) {
    console.log("No video found on this page");
    return;
  }

  isAttached = true;

  console.log("Video found, attaching audio capture...");

  const audioContext = new AudioContext();

  // Ensure the AudioContext is running (may require user interaction in some cases)
  audioContext.resume();

  const source: MediaElementAudioSourceNode =
    audioContext.createMediaElementSource(video);

  // Load the AudioWorklet processor
  audioContext.audioWorklet
    .addModule(chrome.runtime.getURL("audio_processor.js"))
    .then(() => {
      // Create a worklet node with no outputs so it cannot affect playback
      const workletNode = new AudioWorkletNode(audioContext, "audio-processor", {
        numberOfInputs: 1,
        numberOfOutputs: 0,
      });

      // Connect source to worklet for capture only
      source.connect(workletNode);

      // Connect source directly to destination for original playback
      source.connect(audioContext.destination);

      // Receive captured audio chunks from the worklet
      workletNode.port.onmessage = (event: MessageEvent): void => {
        const chunk: Float32Array = event.data;

        chrome.runtime.sendMessage({
          type: "AUDIO_CHUNK",
          data: Array.from(chunk),
        });
      };
    })
    .catch((err) => console.error("AudioWorklet failed to load:", err));
};

// Run when page loads
attachToVideo();

// Observe DOM changes to handle dynamically added video elements (e.g. YouTube SPA)
const observer = new MutationObserver(attachToVideo);
observer.observe(document.body, { childList: true, subtree: true });
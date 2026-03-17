/// <reference types="chrome"/>

const attachToVideo = (): void => {
  const video = document.querySelector<HTMLVideoElement>("video");

  if (!video) {
    console.log("No video found on this page");
    return;
  }

  console.log("Video found, attaching audio capture...");

  const audioContext = new AudioContext();
  const source: MediaElementAudioSourceNode =
    audioContext.createMediaElementSource(video);

  // AudioWorklet replaces the deprecated ScriptProcessorNode
  audioContext.audioWorklet
    .addModule(chrome.runtime.getURL("audio_processor.js"))
    .then(() => {
      const workletNode = new AudioWorkletNode(audioContext, "audio-processor");

      source.connect(workletNode);
      workletNode.connect(audioContext.destination);

      // receive processed chunks from the worklet
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

// run when page loads
attachToVideo();

// watch for dynamically added video elements (e.g. YouTube SPA behaviour)
const observer = new MutationObserver(attachToVideo);
observer.observe(document.body, { childList: true, subtree: true });

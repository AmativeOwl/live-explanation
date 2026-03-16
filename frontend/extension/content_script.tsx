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
  const processor: ScriptProcessorNode = audioContext.createScriptProcessor(
    4096,
    1,
    1,
  );

  source.connect(processor);
  processor.connect(audioContext.destination);

  processor.onaudioprocess = (event: AudioProcessingEvent): void => {
    const chunk: Float32Array = event.inputBuffer.getChannelData(0);

    chrome.runtime.sendMessage({
      type: "AUDIO_CHUNK",
      data: Array.from(chunk),
    });
  };
};

// run when page loads
attachToVideo();

// watch for dynamically added video elements (e.g. YouTube SPA behaviour)
const observer = new MutationObserver(attachToVideo);
observer.observe(document.body, { childList: true, subtree: true });

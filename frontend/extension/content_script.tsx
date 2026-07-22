/// <reference types="chrome"/>
import { createRoot } from "react-dom/client";
import App from "../src/App";

let isAttached = false;
let uiMounted = false;

const mountUI = (): void => {
  if (uiMounted) return;
  uiMounted = true;

  const container = document.createElement("div");
  container.id = "live-explanation-root";
  container.style.position = "fixed";
  container.style.top = "50%";
  container.style.right = "16px";
  container.style.transform = "translateY(-50%)";
  container.style.zIndex = "999999";
  container.style.maxWidth = "320px";
  container.style.maxHeight = "60vh";
  container.style.overflowY = "auto";
  container.style.background = "rgba(20, 20, 20, 0.85)";
  container.style.color = "#fff";
  container.style.padding = "12px";
  container.style.borderRadius = "8px";
  container.style.fontFamily = "sans-serif";
  document.body.appendChild(container);

  createRoot(container).render(<App />); 

  // Fullscreen hides all normal page chrome except whatever lives inside
  // the fullscreen element itself, so the panel has to physically move
  // there to stay visible — then move back once fullscreen exits.
  document.addEventListener("fullscreenchange", () => {
    const target = document.fullscreenElement ?? document.body;
    target.appendChild(container);
  });
};

const attachToVideo = (): void => {
  if (isAttached) return;

  const video = document.querySelector<HTMLVideoElement>("video");

  if (!video) {
    console.log("No video found on this page");
    return;
  }

  isAttached = true;

  console.log("Video found, attaching audio capture...");

  // Tell the backend this is a new video, so it resets any leftover LLM
  // context/state from whatever was playing before.
  chrome.runtime.sendMessage({ type: "NEW_VIDEO" });

  // The audio graph below only needs to be built once per <video> element, but
  // sites like YouTube reuse the same element across SPA navigations and just
  // swap its source — "loadstart" fires on every one of those swaps, so this
  // is what actually catches a viewer moving to a new video.
  //
  // YouTube's adaptive streaming (MediaSource Extensions) reassigns the
  // element's source internally during quality negotiation, ads, and even
  // seeking to an unbuffered position — each of those fires its own
  // "loadstart" too, so a single real video can produce a burst of several
  // in quick succession. Debounce so a burst collapses into one reset
  // instead of resetting the pipeline several times over.
  let loadstartDebounce: ReturnType<typeof setTimeout> | null = null;
  video.addEventListener("loadstart", () => {
    if (loadstartDebounce) clearTimeout(loadstartDebounce);
    loadstartDebounce = setTimeout(() => {
      chrome.runtime.sendMessage({ type: "NEW_VIDEO" });
    }, 1000);
  });

  const audioContext = new AudioContext();

  // Chrome suspends a new AudioContext unless resume() runs as a direct
  // result of a real user gesture (click, key press, etc). Calling it here
  // unconditionally works only when Chrome's per-site engagement heuristics
  // happen to allow it — tying it to the page's first click makes it work
  // reliably regardless of that.
  audioContext.resume();
  document.addEventListener(
    "click",
    () => {
      audioContext.resume();
    },
    { once: true }
  );

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
mountUI();
attachToVideo();

// Observe DOM changes to handle dynamically added video elements (e.g. YouTube SPA)
const observer = new MutationObserver(attachToVideo);
observer.observe(document.body, { childList: true, subtree: true });
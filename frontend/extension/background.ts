/// <reference types="chrome"/>

let socket: WebSocket | null = null;

const connectWebSocket = (): void => {
  socket = new WebSocket("ws://localhost:8000/ws");

  socket.onopen = (): void => {
    console.log("WebSocket connected to FastAPI backend");
  };

  socket.onclose = (): void => {
    console.log("WebSocket disconnected, retrying in 3s...");
    setTimeout(connectWebSocket, 3000);
  };

  socket.onerror = (error): void => {
    console.error("WebSocket error:", error);
  };
};

// listen for messages from content script
chrome.runtime.onMessage.addListener((message): void => {
  if (message.type === "AUDIO_CHUNK") {
    if (socket && socket.readyState === WebSocket.OPEN) {
      // convert array back to Float32Array and send as binary
      const chunk = new Float32Array(message.data);
      socket.send(chunk.buffer);
    } else {
      console.log("WebSocket not ready, dropping chunk");
    }
  }
});

// connect on startup
connectWebSocket();
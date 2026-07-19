"use client";

import { useState, useEffect, useRef, useCallback } from 'react';

const CHUNK_FRAMES = 1600;
const TARGET_SR = 16000;

export function useMoshi() {
  const [isConnected, setIsConnected] = useState(false);
  const [state, setState] = useState('IDLE');
  const [message, setMessage] = useState('Click Connect to start');
  const [cart, setCart] = useState({ items: [], total: 0 });
  const [transcript, setTranscript] = useState([]);
  const [monologue, setMonologue] = useState('');
  const [activeCategory, setActiveCategory] = useState(null);
  
  const wsRef = useRef(null);
  const audioCtxRef = useRef(null);
  const micStreamRef = useRef(null);
  const workletNodeRef = useRef(null);
  
  const playbackSourcesRef = useRef([]);
  const nextPlayTimeRef = useRef(0);

  const connect = async () => {
    if (isConnected) return;
    try {
      setMessage('Requesting mic...');
      
      const stream = await navigator.mediaDevices.getUserMedia({
        audio: {
          channelCount: 1,
          echoCancellation: true,
          noiseSuppression: true,
          autoGainControl: true,
        }
      });
      micStreamRef.current = stream;

      const audioCtx = new (window.AudioContext || window.webkitAudioContext)({ sampleRate: TARGET_SR });
      audioCtxRef.current = audioCtx;
      if (audioCtx.state === 'suspended') await audioCtx.resume();

      const workletCode = `
          const CHUNK = ${CHUNK_FRAMES};
          class MoshiMicProcessor extends AudioWorkletProcessor {
              constructor() { super(); this._buf = []; }
              process(inputs) {
                  const ch = inputs[0]?.[0];
                  if (!ch) return true;
                  for (let i = 0; i < ch.length; i++) this._buf.push(ch[i]);
                  while (this._buf.length >= CHUNK) {
                      const chunk = new Float32Array(this._buf.splice(0, CHUNK));
                      this.port.postMessage(chunk, [chunk.buffer]);
                  }
                  return true;
              }
          }
          registerProcessor('moshi-mic', MoshiMicProcessor);
      `;
      const blob = new Blob([workletCode], { type: 'application/javascript' });
      const blobUrl = URL.createObjectURL(blob);
      await audioCtx.audioWorklet.addModule(blobUrl);
      URL.revokeObjectURL(blobUrl);

      const micSource = audioCtx.createMediaStreamSource(stream);
      const workletNode = new AudioWorkletNode(audioCtx, 'moshi-mic');
      workletNodeRef.current = workletNode;

      workletNode.port.onmessage = (e) => {
        const chunk = e.data;
        if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
          wsRef.current.send(chunk.buffer);
        }
      };
      micSource.connect(workletNode);

      // Connect to FastAPI backend (local or production)
      let wsUrl = `ws://localhost:8998/ws`;
      if (process.env.NEXT_PUBLIC_BACKEND_HOST) {
        wsUrl = `wss://${process.env.NEXT_PUBLIC_BACKEND_HOST}/ws`;
      } else if (process.env.NEXT_PUBLIC_WS_URL) {
        wsUrl = process.env.NEXT_PUBLIC_WS_URL;
      }
      const ws = new WebSocket(wsUrl);
      ws.binaryType = 'arraybuffer';
      wsRef.current = ws;

      ws.onopen = () => {
        setIsConnected(true);
        nextPlayTimeRef.current = 0;
        setState('IDLE');
        setMessage('Ready! Start speaking...');
        
        // Tell backend what sample rate the browser actually gave us
        ws.send(JSON.stringify({
          type: "setup",
          sample_rate: audioCtx.sampleRate
        }));
      };

      ws.onmessage = (event) => {
        if (event.data instanceof ArrayBuffer) {
          playAudio(event.data);
          return;
        }

        try {
          const msg = JSON.parse(event.data);
          switch (msg.type) {
            case 'status':
              setState(msg.state || 'IDLE');
              if (msg.message) setMessage(msg.message);
              break;
            case 'cart_update':
              setCart(msg);
              break;
            case 'transcript':
              setTranscript(prev => [...prev, { speaker: msg.speaker, text: msg.text }]);
              break;
            case 'inner_monologue':
              setMonologue(msg.full_text);
              break;
            case 'interrupted':
              stopAllAudio();
              break;
            case 'category_change':
              if (msg.category) setActiveCategory(msg.category);
              break;
            default:
              break;
          }
        } catch (e) {
          console.error("Parse error", e);
        }
      };

      ws.onclose = () => {
        cleanup();
      };
      ws.onerror = (err) => {
        cleanup();
      };
    } catch (err) {
      console.error(err);
      cleanup();
    }
  };

  const playAudio = async (arrayBuffer) => {
    const audioCtx = audioCtxRef.current;
    if (!audioCtx) return;
    if (audioCtx.state === 'suspended') await audioCtx.resume();

    try {
      const decoded = await audioCtx.decodeAudioData(arrayBuffer.slice(0));
      const source = audioCtx.createBufferSource();
      source.buffer = decoded;

      const gain = audioCtx.createGain();
      gain.gain.value = 1.0;

      source.connect(gain);
      gain.connect(audioCtx.destination);

      const startAt = Math.max(nextPlayTimeRef.current, audioCtx.currentTime + 0.02);
      source.start(startAt);
      nextPlayTimeRef.current = startAt + decoded.duration;

      const srcObj = { source, gain };
      playbackSourcesRef.current.push(srcObj);

      source.onended = () => {
        playbackSourcesRef.current = playbackSourcesRef.current.filter(s => s.source !== source);
      };
    } catch (err) {
      console.warn('Audio decode error:', err);
    }
  };

  const stopAllAudio = () => {
    const audioCtx = audioCtxRef.current;
    const now = audioCtx?.currentTime || 0;
    playbackSourcesRef.current.forEach(({ source, gain }) => {
      try {
        // Very short ramp (a few ms) just to avoid an audible click —
        // this is effectively instant, not a fade.
        gain.gain.cancelScheduledValues(now);
        gain.gain.setValueAtTime(gain.gain.value, now);
        gain.gain.linearRampToValueAtTime(0, now + 0.008);
        source.stop(now + 0.012);
      } catch (e) {}
    });
    playbackSourcesRef.current = [];
    nextPlayTimeRef.current = 0;
  };

  const cleanup = useCallback(() => {
    setIsConnected(false);
    stopAllAudio();
    if (micStreamRef.current) {
      micStreamRef.current.getTracks().forEach(t => t.stop());
      micStreamRef.current = null;
    }
    if (workletNodeRef.current) {
      workletNodeRef.current.disconnect();
      workletNodeRef.current = null;
    }
    setState('IDLE');
    setMessage('Disconnected. Click Connect to start.');
  }, []);

  const disconnect = () => {
    if (wsRef.current) {
      wsRef.current.close();
    }
    cleanup();
  };
  
  const sendAction = (action, payload) => {
    if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify({ type: 'user_action', action, ...payload }));
    }
  };

  useEffect(() => {
    return () => cleanup();
  }, [cleanup]);

  return {
    isConnected,
    state,
    message,
    cart,
    transcript,
    monologue,
    activeCategory,
    connect,
    disconnect,
    sendAction
  };
}

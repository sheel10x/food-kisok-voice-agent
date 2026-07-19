/**
 * Moshi Full-Duplex Voice AI — Browser Client
 */

'use strict';

const TARGET_SR = 16000;
const CHUNK_FRAMES = 1600;

let ws = null;
let audioCtx = null;
let micStream = null;
let workletNode = null;
let isConnected = false;
let currentState = 'IDLE';

let playbackSources = [];
let nextPlayTime = 0;

let monoHistory = [];

async function toggleConnection() {
    if (isConnected) {
        disconnect();
    } else {
        await connect();
    }
}

async function connect() {
    if (isConnected) return;
    try {
        setConnLabel('Requesting mic...');

        micStream = await navigator.mediaDevices.getUserMedia({
            audio: {
                channelCount: 1,
                echoCancellation: true,
                noiseSuppression: true,
                autoGainControl: true,
            }
        });

        audioCtx = new (window.AudioContext || window.webkitAudioContext)({ sampleRate: TARGET_SR });
        if (audioCtx.state === 'suspended') await audioCtx.resume();

        const workletCode = `
            const CHUNK = ${CHUNK_FRAMES};
            class MoshiMicProcessor extends AudioWorkletProcessor {
                constructor() {
                    super();
                    this._buf = [];
                }
                process(inputs) {
                    const ch = inputs[0]?.[0];
                    if (!ch) return true;
                    for (let i = 0; i < ch.length; i++) {
                        this._buf.push(ch[i]);
                    }
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

        const micSource = audioCtx.createMediaStreamSource(micStream);
        workletNode = new AudioWorkletNode(audioCtx, 'moshi-mic');

        workletNode.port.onmessage = (e) => {
            const chunk = e.data;
            if (ws && ws.readyState === WebSocket.OPEN) {
                ws.send(chunk.buffer);
            }
        };

        micSource.connect(workletNode);

        const proto = location.protocol === 'https:' ? 'wss' : 'ws';
        const wsUrl = `${proto}://${location.host}/ws`;

        setConnLabel('Connecting server...');
        ws = new WebSocket(wsUrl);
        ws.binaryType = 'arraybuffer';

        ws.onopen = () => {
            isConnected = true;
            nextPlayTime = 0;
            document.getElementById('connect-btn').classList.add('connected');
            document.getElementById('connect-label').textContent = 'Disconnect';
            document.getElementById('interrupt-btn').disabled = false;
            setConnDot('online');
            setConnLabel('Connected');
            
            const sliderVal = document.getElementById('vad-slider').value;
            onVADChange(sliderVal);
            
            setStateUI('IDLE', '🎙️', 'Ready', 'Start speaking...');
            updateDuplex(true);
        };

        ws.onmessage = onMessage;

        ws.onclose = () => {
            setConnLabel('Connection closed');
            cleanup();
        };

        ws.onerror = (err) => {
            setConnLabel('Connection failed');
            cleanup();
        };

    } catch (err) {
        setConnLabel('Failed: ' + (err.message || err));
        cleanup();
    }
}

function disconnect() {
    ws?.close();
    cleanup();
}

function cleanup() {
    isConnected = false;
    stopAllAudio();

    if (micStream) {
        micStream.getTracks().forEach(t => t.stop());
        micStream = null;
    }
    if (workletNode) {
        workletNode.disconnect();
        workletNode = null;
    }

    document.getElementById('connect-btn').classList.remove('connected');
    document.getElementById('connect-label').textContent = 'Connect';
    document.getElementById('interrupt-btn').disabled = true;

    setConnDot('offline');
    setConnLabel('Disconnected');
    setStateUI('IDLE', '🎙️', 'Ready', 'Click Connect to start a conversation');
    setLevel('user', 0);
    setLevel('model', 0);
    updateDuplex(false);
}

function onMessage(event) {
    if (event.data instanceof ArrayBuffer) {
        playAudio(event.data);
        return;
    }

    let msg;
    try { msg = JSON.parse(event.data); }
    catch { return; }

    switch (msg.type) {
        case 'status':          onStatus(msg);         break;
        case 'audio_level':     onAudioLevel(msg);     break;
        case 'inner_monologue': onMonologue(msg);      break;
        case 'monologue_start': onMonologueStart();    break;
        case 'transcript':      onTranscript(msg);     break;
        case 'interrupted':     onInterrupted(msg);    break;
    }
}

function onStatus(msg) {
    const s = msg.state || 'IDLE';
    currentState = s;

    const icons = { LISTENING: '🎙️', PROCESSING: '⚙️', SPEAKING: '🗣️', INTERRUPTED: '✋', IDLE: '🎙️' };
    const labels = { LISTENING: 'Listening', PROCESSING: 'Processing', SPEAKING: 'Speaking', INTERRUPTED: 'Interrupted', IDLE: 'Ready' };
    const dots = { LISTENING: 'listen', PROCESSING: 'process', SPEAKING: 'speak', INTERRUPTED: 'speak', IDLE: 'online' };

    setStateUI(s, icons[s] || '❓', labels[s] || s, msg.message || '');
    setConnDot(dots[s] || 'online');
    setConnLabel(msg.message || labels[s] || s);

    document.getElementById('feat-duplex').classList.toggle('active', s === 'SPEAKING' || s === 'LISTENING');
    document.getElementById('feat-interrupt').classList.toggle('active', s === 'SPEAKING');
    document.getElementById('feat-monologue').classList.toggle('active', s === 'SPEAKING' || s === 'PROCESSING');
}

function onAudioLevel(msg) {
    setLevel(msg.channel, msg.level);
    const canvasId = msg.channel === 'user' ? 'user-canvas' : 'model-canvas';
    pushWaveform(canvasId, msg.level);
    
    if (msg.channel === 'model' && msg.latency_ms) {
        document.getElementById('model-latency').textContent = `latency: ${Math.round(msg.latency_ms)}ms`;
    }
}

function onMonologueStart() {
    const textEl = document.getElementById('mono-text');
    if (textEl && textEl.textContent.trim().length > 0) {
        monoHistory.unshift(textEl.textContent);
        if (monoHistory.length > 8) monoHistory.pop();
        renderMonoHistory();
    }
    if (textEl) textEl.textContent = '';
    const progEl = document.getElementById('mono-prog');
    if (progEl) progEl.style.width = '0%';
}

function onMonologue(msg) {
    const textEl = document.getElementById('mono-text');
    if (textEl && msg.text) textEl.textContent = msg.text;
    const progEl = document.getElementById('mono-prog');
    if (progEl && typeof msg.progress === 'number') {
        progEl.style.width = `${Math.min(100, Math.max(0, msg.progress * 100))}%`;
    }
}

function renderMonoHistory() {
    const histEl = document.getElementById('mono-history');
    if (!histEl) return;
    histEl.innerHTML = '';
    if (monoHistory.length === 0) {
        histEl.innerHTML = '<div class="mono-history-empty">Waiting for generation...</div>';
        return;
    }
    monoHistory.forEach(t => {
        const div = document.createElement('div');
        div.className = 'mono-history-item';
        div.textContent = t;
        histEl.appendChild(div);
    });
}

function onTranscript(msg) {
    const transcriptEl = document.getElementById('transcript');
    if (!transcriptEl) return;
    
    const empty = document.getElementById('transcript-empty');
    if (empty) empty.style.display = 'none';

    const msgClass = msg.speaker.toLowerCase() === 'user' ? 'msg-user' : 'msg-model';
    
    // Check if we need to update the last typing message or create a new one
    let lastMsg = transcriptEl.lastElementChild;
    if (!lastMsg || lastMsg.dataset.speaker !== msg.speaker || lastMsg.dataset.isFinal === 'true') {
        const wrap = document.createElement('div');
        wrap.className = `msg ${msgClass}`;
        wrap.dataset.speaker = msg.speaker;
        
        const header = document.createElement('div');
        header.className = 'msg-header';
        header.textContent = msg.speaker;
        
        const bubble = document.createElement('div');
        bubble.className = 'msg-bubble';
        
        wrap.appendChild(header);
        wrap.appendChild(bubble);
        transcriptEl.appendChild(wrap);
        lastMsg = wrap;
    }
    
    const bubble = lastMsg.querySelector('.msg-bubble');
    bubble.textContent = msg.text;
    lastMsg.dataset.isFinal = msg.is_final ? 'true' : 'false';
    
    transcriptEl.scrollTop = transcriptEl.scrollHeight;
}

function clearTranscript() {
    const transcriptEl = document.getElementById('transcript');
    if (transcriptEl) {
        transcriptEl.innerHTML = `<div class="transcript-empty" id="transcript-empty"><div class="transcript-empty-icon">💬</div><div>Conversation will appear here.<br>Both speakers shown in parallel.</div></div>`;
    }
}

function onInterrupted(msg) {
    stopAllAudio(); // Instantly kill any buffered TTS audio playback
    
    const transcriptEl = document.getElementById('transcript');
    if (!transcriptEl) return;
    const lastMsg = transcriptEl.lastElementChild;
    if (lastMsg && lastMsg.dataset.speaker !== 'User') {
        lastMsg.classList.add('msg-interrupted');
        const header = lastMsg.querySelector('.msg-header');
        if (header && !header.querySelector('.interrupted-tag')) {
            const tag = document.createElement('span');
            tag.className = 'interrupted-tag';
            tag.textContent = 'Interrupted';
            header.appendChild(tag);
        }
        lastMsg.dataset.isFinal = 'true';
    }
}

function sendInterrupt() {
    if (ws?.readyState === WebSocket.OPEN && currentState === 'SPEAKING') {
        ws.send(JSON.stringify({ type: 'interrupt' }));
        document.getElementById('interrupt-btn').disabled = true;
    }
}

function onVADChange(val) {
    document.getElementById('vad-val').textContent = val;
    const threshold = 0.002 + (10 - parseInt(val)) * 0.0025;
    if (ws?.readyState === WebSocket.OPEN) {
        ws.send(JSON.stringify({ type: 'set_vad_threshold', value: threshold }));
    }
}

function setStateUI(stateCls, icon, label, msg) {
    const wrap = document.querySelector('.state-icon-wrap');
    if (wrap) {
        wrap.className = 'state-icon-wrap';
        wrap.parentElement.className = `state-display state-${stateCls}`;
    }
    const icn = document.getElementById('state-icon');
    if (icn) icn.textContent = icon;
    
    const lbl = document.getElementById('state-label');
    if (lbl) lbl.textContent = label;
    
    const dMsg = document.getElementById('state-msg');
    if (dMsg) dMsg.textContent = msg;
}

function setConnDot(cls) {
    const dot = document.getElementById('conn-dot');
    if (dot) dot.className = `conn-dot ${cls}`;
}

function setConnLabel(text) {
    const lbl = document.getElementById('conn-label');
    if (lbl) lbl.textContent = text;
}

function setLevel(channel, val) {
    const fill = document.getElementById(`${channel}-level`);
    if (fill) fill.style.width = `${Math.min(100, val * 100)}%`;
}

function updateDuplex(isActive) {
    const ring = document.getElementById('duplex-ring');
    if (ring) {
        if (isActive) ring.classList.add('active');
        else ring.classList.remove('active');
    }
}

async function playAudio(arrayBuffer) {
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

        const startAt = Math.max(nextPlayTime, audioCtx.currentTime + 0.02);
        source.start(startAt);
        nextPlayTime = startAt + decoded.duration;

        playbackSources.push({ source, gain });

        source.onended = () => {
            playbackSources = playbackSources.filter(s => s.source !== source);
        };
    } catch (err) {
        console.warn('Audio decode error:', err);
    }
}

function stopAllAudio() {
    const now = audioCtx?.currentTime || 0;
    playbackSources.forEach(({ source, gain }) => {
        try {
            // Very short ramp (a few ms) just to avoid an audible click —
            // this is effectively instant, not a fade.
            gain.gain.cancelScheduledValues(now);
            gain.gain.setValueAtTime(gain.gain.value, now);
            gain.gain.linearRampToValueAtTime(0, now + 0.008);
            source.stop(now + 0.012);
        } catch (_) {}
    });
    playbackSources = [];
    nextPlayTime = 0;
}

const wfData = {
    'user-canvas': new Array(40).fill(0),
    'model-canvas': new Array(40).fill(0)
};

function pushWaveform(id, val) {
    if (wfData[id]) {
        wfData[id].push(val);
        wfData[id].shift();
    }
}

function drawWaveforms() {
    ['user-canvas', 'model-canvas'].forEach(id => {
        const canvas = document.getElementById(id);
        if (!canvas) return;
        const ctx = canvas.getContext('2d');
        const w = canvas.width;
        const h = canvas.height;
        const arr = wfData[id];
        
        ctx.clearRect(0, 0, w, h);
        
        const barW = (w / arr.length) - 2;
        ctx.fillStyle = id === 'user-canvas' ? '#00e5ff' : '#b06ef3';
        
        for (let i = 0; i < arr.length; i++) {
            const val = arr[i];
            const barH = Math.max(2, val * h);
            const x = i * (w / arr.length);
            const y = (h - barH) / 2;
            ctx.beginPath();
            ctx.roundRect(x, y, barW, barH, 2);
            ctx.fill();
        }
    });
}

function resizeCanvases() {
    ['user-canvas', 'model-canvas'].forEach(id => {
        const canvas = document.getElementById(id);
        if (canvas) {
            canvas.width = canvas.parentElement.clientWidth;
            canvas.height = canvas.parentElement.clientHeight;
        }
    });
}

function animate() {
    if (currentState === 'IDLE' && !isConnected) {
        pushWaveform('user-canvas', 0);
        pushWaveform('model-canvas', 0);
    } else {
        // Smooth decay for visual aesthetics if no new data
        wfData['user-canvas'] = wfData['user-canvas'].map(v => v * 0.9);
        wfData['model-canvas'] = wfData['model-canvas'].map(v => v * 0.9);
    }
    
    drawWaveforms();
    requestAnimationFrame(animate);
}

document.addEventListener('DOMContentLoaded', () => {
    resizeCanvases();
    animate();
});

window.addEventListener('resize', resizeCanvases);

document.addEventListener('click', () => {
    if (audioCtx?.state === 'suspended') audioCtx.resume();
}, { once: false });

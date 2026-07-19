# Hedes — Full-Duplex Voice AI

**Hedes** is an advanced, real-time voice AI assistant built from the ground up to simulate natural, human-like conversational dynamics. Unlike traditional walkie-talkie style Voice AIs where users have to wait for the AI to finish speaking, Hedes operates in **true Full-Duplex mode**—meaning both the user and the AI can listen and speak simultaneously without explicitly taking turns. 

This project was built to tackle the inherent latency challenges of Voice AI by implementing continuous audio pipelining, advanced Voice Activity Detection (VAD), and token streaming.

## 🚀 Key Features

* **Real-time Full-Duplex Communication**: Talk and listen simultaneously over a continuous WebSocket connection. 
* **Instant Interruption Handling**: Powered by a finely tuned Voice Activity Detection (VAD) algorithm, Hedes detects if you start speaking while it is talking. It immediately aborts its text generation and silences its audio pipeline to listen to you, mimicking natural human conversation.
* **Asynchronous Audio Pipelining**: Hedes dramatically cuts down response latency by streaming LLM text tokens and simultaneously piping them into a Text-to-Speech engine. While the first sentence is being spoken to the user, the backend is seamlessly generating and queueing the second sentence in the background.
* **Inner Monologue Visualization**: As Hedes streams tokens from the LLM, they are presented on the UI as an "Inner Monologue", showing exactly what the AI is thinking before it is spoken.
* **Interactive UI**: A modern, sleek Web Interface built with vanilla HTML/CSS/JS. It features real-time audio waveform visualizers (driven by the Web Audio API) for both the user's microphone and the AI's speaker output.
* **Wikipedia Integration Tooling**: Includes tool-calling capabilities that allow the LLM to search Wikipedia in real-time when asked about factual information.

## 🛠️ Technical Architecture

### Backend (Python)
* **FastAPI**: Serves the frontend assets and provides the high-performance asynchronous runtime.
* **WebSockets**: Maintains a persistent bi-directional binary stream for audio data and JSON control messages between the client and server.
* **Groq / OpenAI / Edge TTS**: Leverages Llama-3.1 via Groq's lightning-fast inference for text generation, combined with Edge TTS (or OpenAI TTS) for instantaneous speech synthesis.
* **Concurrency**: Heavily relies on `asyncio` to run the Speech-to-Text, LLM generation, TTS synthesis, and WebSocket communication in fully asynchronous, non-blocking background tasks.

### Frontend (JavaScript & Web Audio API)
* **AudioWorklets**: Uses low-level `AudioWorkletProcessor` to bypass the browser's main thread and capture raw 16kHz PCM audio data directly from the microphone without stuttering.
* **Dynamic Waveform Rendering**: Calculates real-time audio amplitude envelopes to animate the colorful visualizers.

## ⚙️ How it Works under the Hood
1. The frontend captures audio via the microphone and streams raw 16-bit PCM binary data to the backend.
2. The `moshi_engine.py` ingests this binary data into a ring buffer and constantly runs an energy-based Voice Activity Detection (VAD) pass.
3. Once a speech utterance finishes, it's dispatched to an asynchronous STT (Speech-to-Text) provider.
4. The transcribed text is sent to the LLM (Groq), which immediately begins streaming tokens back.
5. As the text streams in, a background worker parses sentence boundaries and dispatches them to a TTS pipeline.
6. The TTS engine converts the sentences into audio chunks and streams them back down the WebSocket to the browser.
7. If at any point during steps 4-6 the VAD detects the user speaking again, an interruption event is thrown, instantly cancelling the LLM stream, clearing the TTS queues, and resetting the frontend playback buffers.

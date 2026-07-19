"""
Moshi Full-Duplex Engine
========================
Implements the core concepts from arXiv:2410.00037:

1. DUAL AUDIO STREAMS
   - User stream: mic audio → VAD → STT
   - Model stream: LLM → inner monologue → TTS → speaker

2. FULL-DUPLEX
   - Both streams run SIMULTANEOUSLY in asyncio tasks
   - No explicit turn-taking or end-of-speech detection required for model

3. INNER MONOLOGUE
   - Text tokens are predicted FIRST as a prefix (like chain-of-thought)
   - Then audio tokens are generated
   - Visible in the UI as streaming text

4. INTERRUPTION DETECTION
   - User VAD fires while model is speaking → interrupt signal
   - Model immediately stops generating audio
   - Switches back to listening mode
"""

import asyncio
import collections
import json
import logging
import os
import re
import numpy as np
from typing import Optional
from llm_backend import LLMBackend
from cart_manager import CartManager
from menu_data import find_item_by_name, find_category_by_name

logger = logging.getLogger("moshi.engine")


# ── Constants (matching Moshi paper) ──────────────────────────────────
SAMPLE_RATE = 16000          # Hz — matches Moshi's processing rate
FRAME_SIZE = 1600            # samples — 100ms per frame at 16kHz
SILENCE_FRAMES = 8           # 800ms of silence = end of utterance
MONOLOGUE_TOKEN_DELAY = 0.06 # seconds per token (simulates 12.5Hz token rate)
INTERRUPT_MIN_FRAMES = 3     # min speech frames before interrupting (300ms — fast barge-in)


# ═══════════════════════════════════════════════════════════════════════
# VOICE ACTIVITY DETECTOR
# ═══════════════════════════════════════════════════════════════════════

class VAD:
    """
    Adaptive SNR-based Voice Activity Detection with voice-band gating.

    The previous implementation used a single fixed RMS threshold. That is
    exactly the wrong shape for a mic: a threshold high enough to ignore a
    room's background noise is too high to hear a normal-volume voice, and
    a threshold low enough to hear a quiet voice will also fire on any
    background noise louder than a whisper. Two changes fix both problems
    at once:

    1. ADAPTIVE SNR GATE — instead of comparing energy to a fixed number,
       we continuously track the ambient noise floor and require the
       current frame to be a certain multiple *above that floor* (its
       signal-to-noise ratio). This adapts automatically to a quiet room
       or a noisy one, and to quiet or loud speakers.

    2. VOICE-BAND ENERGY — human speech concentrates most of its energy
       in ~250-3400 Hz. Steady background noise (fans, hums, AC, traffic
       rumble) is usually either low-frequency or spread broadband. By
       requiring most of a frame's energy to sit in the voice band, we
       reject most non-speech noise even when it's loud enough to pass
       the SNR gate.

    3. HYSTERESIS — starting to count something as speech requires a
       higher confidence (onset_ratio) than continuing to count it
       (continue_ratio), which prevents flickering on/off right at the
       noise floor boundary — a common cause of choppy, unreliable VAD.

    4. SPEAKING-AWARE SENSITIVITY — while the agent itself is speaking,
       its own TTS audio can bleed back into the mic (imperfect browser
       echo cancellation, speakers instead of headphones, etc). We raise
       the bar for what counts as an interruption during SPEAKING so the
       agent doesn't "hear itself" and cut off randomly, while keeping
       full sensitivity the rest of the time.
    """

    VOICE_BAND_LOW_HZ = 250.0
    VOICE_BAND_HIGH_HZ = 3400.0

    def __init__(self, sample_rate: int = SAMPLE_RATE, window: int = 5):
        self.sample_rate = sample_rate
        self.window = window
        self._history: list[float] = []
        self._noise_floor: float = 0.0015   # adapts to the room automatically
        self._min_noise_floor: float = 0.0006
        self._was_speech = False

        # SNR multipliers over the current noise floor.
        self.onset_ratio = 3.2       # confidence required to START being speech
        self.continue_ratio = 1.7    # confidence required to KEEP being speech
        self.speaking_onset_multiplier = 2.5  # extra caution while agent is talking

        # ── Absolute loudness gate for barge-in ─────────────────────────
        # The SNR gate above is relative to the *adaptive* noise floor, so if
        # background noise is steady it can still raise the effective bar
        # just enough for it to occasionally slip through as "speech" and
        # trip an instant interruption. For barge-in specifically we add a
        # second, absolute (not noise-floor-relative) loudness requirement:
        # no matter what the noise floor is doing, the raw signal must be
        # genuinely loud to cut the agent off immediately. This only gates
        # the fast interrupt path — normal speech detection used for
        # listening/transcription (STT) is untouched, so quieter speech is
        # still heard and understood exactly as before; it just confirms an
        # interruption via STT after you finish talking instead of cutting
        # in instantly. Raise/lower this to tune how "loud" counts as loud.
        self.interrupt_loud_rms = 0.085

    def process(self, audio: np.ndarray, agent_speaking: bool = False) -> dict:
        """Returns VAD analysis for a single audio chunk."""
        audio_f = audio.astype(np.float32)
        n = len(audio_f)
        rms = float(np.sqrt(np.mean(np.square(audio_f))) + 1e-9)

        # ── Zero-Crossing Rate (rejects pure hum / DC rumble) ──────────
        signs = np.sign(audio_f)
        signs[signs == 0] = 1.0
        zcr = float(np.sum(signs[:-1] != signs[1:]) / max(1, n))
        is_speech_zcr = 0.01 < zcr < 0.35

        # ── Voice-band energy ratio (rejects broadband/low-freq noise) ─
        if n >= 64:
            spectrum = np.abs(np.fft.rfft(audio_f * np.hanning(n)))
            freqs = np.fft.rfftfreq(n, d=1.0 / max(1, self.sample_rate))
            band_mask = (freqs >= self.VOICE_BAND_LOW_HZ) & (freqs <= self.VOICE_BAND_HIGH_HZ)
            band_energy = float(np.sum(spectrum[band_mask] ** 2))
            total_energy = float(np.sum(spectrum ** 2) + 1e-9)
            voice_band_ratio = band_energy / total_energy
        else:
            voice_band_ratio = 1.0
        is_voice_dominant = voice_band_ratio > 0.32

        # ── Adaptive noise floor: only track quiet frames, fast-down/slow-up ──
        if rms < self._noise_floor * 2.2:
            alpha = 0.12 if rms < self._noise_floor else 0.03
            self._noise_floor = (1 - alpha) * self._noise_floor + alpha * rms
            self._noise_floor = max(self._noise_floor, self._min_noise_floor)

        self._history.append(rms)
        if len(self._history) > self.window:
            self._history.pop(0)
        avg_rms = float(np.mean(self._history))

        snr = avg_rms / max(self._noise_floor, self._min_noise_floor)

        required_ratio = self.continue_ratio if self._was_speech else self.onset_ratio
        if agent_speaking:
            required_ratio *= self.speaking_onset_multiplier

        is_speech = (snr > required_ratio) and is_speech_zcr and is_voice_dominant
        self._was_speech = is_speech

        threshold_rms = self._noise_floor * required_ratio
        level = float(min(1.0, rms / max(threshold_rms * 2, 0.001)))

        return {
            "is_speech": is_speech,
            "is_loud": rms >= self.interrupt_loud_rms,
            "energy": rms,
            "threshold": threshold_rms,
            "level": level,
            "snr": round(snr, 2),
        }

    def reset(self):
        self._history.clear()
        self._was_speech = False

    def set_threshold(self, value: float):
        """
        Accepts the legacy absolute-RMS-style slider value (roughly
        0.002 - 0.03) and maps it onto the new SNR-ratio scale so the
        existing UI slider still behaves sensibly: smaller value = more
        sensitive (lower ratio required to trigger speech).
        """
        value = max(0.0005, float(value))
        self.onset_ratio = max(1.8, min(8.0, value / 0.0015))
        self.continue_ratio = max(1.2, self.onset_ratio * 0.55)


# ═══════════════════════════════════════════════════════════════════════
# INNER MONOLOGUE TRACKER
# ═══════════════════════════════════════════════════════════════════════

class InnerMonologue:
    """
    Tracks Moshi's inner monologue — text tokens generated BEFORE audio tokens.

    From the paper (Section 3.3 — Inner Monologue):
    "We propose to first predict time-aligned text tokens as a prefix to
    audio tokens... the model first 'thinks' in text before 'speaking'
    in audio tokens."

    This significantly improves linguistic quality of generated speech.
    """

    def __init__(self):
        self.current: str = ""
        self.history: list[str] = []

    def begin(self):
        """Start a new inner monologue sequence."""
        self.current = ""

    def add_token(self, token: str) -> str:
        """Add a text token to the current monologue."""
        self.current += token
        return token

    def commit(self):
        """Finalize current monologue and add to history."""
        text = self.current.strip()
        if text:
            self.history.insert(0, text)
            if len(self.history) > 10:
                self.history.pop()
        self.current = ""

    def reset(self):
        self.current = ""


def split_sentences(text: str) -> list[str]:
    """Split text into sentences for incremental TTS streaming."""
    parts = re.split(r'(?<=[.!?])\s+', text.strip())
    return [p.strip() for p in parts if p.strip()]



# ═══════════════════════════════════════════════════════════════════════
# DUPLEX ENGINE — Core Full-Duplex State Machine
# ═══════════════════════════════════════════════════════════════════════

class DuplexEngine:
    """
    Full-duplex conversation engine implementing Moshi's core concepts.

    State Machine:
    ┌─────────────┐     speech detected      ┌─────────────┐
    │  LISTENING  │ ───────────────────────► │  LISTENING  │ (buffering)
    └─────────────┘                          └──────┬──────┘
           ▲                                        │ silence (800ms)
           │                                        ▼
           │                                 ┌─────────────┐
           │   ◄──── done ─────────────────  │ PROCESSING  │ (STT)
           │                                 └──────┬──────┘
           │                                        │ transcript ready
           │                                        ▼
           │                                 ┌─────────────┐
           └──────── interrupt ────────────  │  SPEAKING   │ (TTS + monologue)
                                             └─────────────┘
    """

    def __init__(self, websocket):
        self.ws = websocket
        self.vad = VAD(sample_rate=SAMPLE_RATE)
        self.llm = LLMBackend()           # Real LLM backend (Ollama / g4f / Groq)
        self.monologue = InnerMonologue()
        self.cart = CartManager()
        self.state = "IDLE"
        self._running = True
        self.client_sample_rate = SAMPLE_RATE  # Will be updated by frontend
        self.silence_frames_threshold = SILENCE_FRAMES
        self.interrupt_min_frames = INTERRUPT_MIN_FRAMES

        # Audio buffers
        self._user_buffer: list[np.ndarray] = []
        self._ring_buffer = collections.deque(maxlen=10) # 1 second of pre-speech audio
        self._silence_count: int = 0
        self._speech_frame_count: int = 0
        self.latest_video_frame: Optional[str] = None

        # Interruption control
        self._speaking_task: Optional[asyncio.Task] = None
        self._interrupt_event = asyncio.Event()

    # ── Main Loop ─────────────────────────────────────────────────────

    async def run(self):
        """Main full-duplex processing loop."""
        await self._emit("status", {
            "state": "LISTENING",
            "message": "Hedes is ready. Start speaking!",
            "mode": "simulation",
        })
        self.state = "LISTENING"

        while self._running:
            try:
                data = await asyncio.wait_for(self.ws.receive(), timeout=0.05)
            except asyncio.TimeoutError:
                continue
            except Exception:
                break

            if data.get("type") == "websocket.disconnect":
                break

            raw_bytes = data.get("bytes")
            raw_text = data.get("text")
            
            # DEBUG
            if not hasattr(self, '_debug_ws_count'):
                self._debug_ws_count = 0
            self._debug_ws_count += 1
            if self._debug_ws_count % 10 == 0:
                logger.info(f"🕸️ WS receive data keys: {list(data.keys())} | bytes len: {len(raw_bytes) if raw_bytes else 'None'} | text: {raw_text}")

            if raw_bytes:
                await self._on_audio_frame(raw_bytes)
            elif raw_text:
                try:
                    await self._on_control(json.loads(raw_text))
                except Exception:
                    pass

    # ── Audio Processing (Full-Duplex: runs even during SPEAKING) ─────

    async def _on_audio_frame(self, raw: bytes):
        """
        Process one audio frame from user microphone.
        """
        audio = np.frombuffer(raw, dtype=np.float32).copy()

        vad = self.vad.process(audio, agent_speaking=(self.state == "SPEAKING"))

        # Send user audio level to UI
        await self._emit("audio_level", {
            "channel": "user",
            "level": vad["level"],
            "energy": round(vad["energy"], 6),
            "is_speech": vad["is_speech"],
        })

        if vad["is_speech"]:
            # If we just started speaking, prepend the ring buffer so we don't lose the start of words
            if not self._user_buffer and self._ring_buffer:
                self._user_buffer.extend(self._ring_buffer)
                
            self._silence_count = 0
            self._speech_frame_count += 1
            self._user_buffer.append(audio)
            self._ring_buffer.clear()
            
            # Immediate VAD interruption — gated on absolute loudness so
            # background noise (which can still pass the adaptive SNR check
            # if it's steady) can't trip an instant barge-in. Quieter real
            # speech isn't lost: it keeps buffering normally and will still
            # interrupt as soon as STT confirms actual words below.
            if (
                self.state == "SPEAKING"
                and self._speech_frame_count >= self.interrupt_min_frames
                and vad["is_loud"]
            ):
                logger.info("🛑 INTERRUPTION detected by VAD (loud)!")
                await self._interrupt()

        else:
            # Silence frame
            if self._user_buffer:
                self._silence_count += 1
                self._speech_frame_count = 0
                self._user_buffer.append(audio)  # MUST keep appending to avoid audio glitching/skipping!

                if self._silence_count >= self.silence_frames_threshold:
                    # End of user utterance
                    buffer_copy = list(self._user_buffer)
                    self._user_buffer = []
                    self._silence_count = 0
                    asyncio.create_task(self._process_utterance(buffer_copy))
            else:
                # Not currently speaking, just keep the last 1 second of audio in the ring buffer
                self._ring_buffer.append(audio)

    # ── Interruption ──────────────────────────────────────────────────

    async def _interrupt(self):
        """
        Handle full-duplex interruption.

        From the paper: Moshi models no explicit speaker turns,
        supporting arbitrary conversational dynamics including interruptions.
        """
        logger.info("✋ Handling interruption...")
        self._interrupt_event.set()

        # Cancel ongoing speech task
        if self._speaking_task and not self._speaking_task.done():
            self._speaking_task.cancel()
            try:
                await asyncio.shield(self._speaking_task)
            except (asyncio.CancelledError, Exception):
                pass

        self._interrupt_event.clear()
        self.state = "LISTENING"
        
        # NOTE: We specifically DO NOT clear _user_buffer or _speech_frame_count here!
        # The user is currently speaking (which triggered the interrupt).
        # We want to keep accumulating their audio until they finish.
        
        await self._emit("interrupted", {"message": "Interrupted! Listening..."})
        await self._emit("status", {"state": "LISTENING", "message": "Go ahead, I'm listening!"})
        await self._emit("audio_level", {"channel": "model", "level": 0.0, "is_speech": False})

    # ── Utterance Processing ──────────────────────────────────────────

    async def _process_utterance(self, buffer: list):
        """Process a complete user utterance and validate with STT before interrupting."""
        if not buffer:
            return

        audio = np.concatenate(buffer)
        
        was_speaking = (self.state == "SPEAKING")
        if not was_speaking:
            self.state = "PROCESSING"
            await self._emit("status", {
                "state": "PROCESSING",
                "message": "Understanding your speech...",
            })

        duration_ms = int(len(audio) / self.client_sample_rate * 1000)
        logger.info(f"📝 Processing utterance ({duration_ms}ms of audio)")

        transcript = await self._stt(audio)
        
        # Whisper often hallucinates these exact strings when fed background noise
        hallucinations = [
            "you", "thank you", "thank you.", "thanks.", "bye", "bye.",
            "great", "great.", "yeah", "yeah.", "ok", "ok.", "okay", "okay.",
            "i'm going to go ahead", "i'm going to go ahead.", "i'm going to go", "i'm going to go.",
            "let's go ahead", "let's go ahead.", "thank you very much", "thank you very much.",
            "you're welcome", "you're welcome.", "subscribe", "please subscribe",
            "thank you for watching", "thank you for watching.", "thanks for watching", "thanks for watching.",
            "i'm not sure what he's doing", "i'm not sure what he's doing.", "i want to make a lot of people", "i want to make a lot of people.",
            "he's a little bit", "he's a little bit.", "what", "what?", "what."
        ]
        is_hallucination = transcript and transcript.strip().lower() in hallucinations

        if transcript and transcript.strip() and len(transcript.strip()) > 1 and not is_hallucination:
            logger.info(f"🗣️  User: '{transcript}'")
            await self._emit("transcript", {"speaker": "user", "text": transcript.strip()})

            if was_speaking or self.state == "SPEAKING":
                logger.info("🛑 INTERRUPTION confirmed by STT — user spoke words")
                await self._interrupt()
                # _interrupt sets state to LISTENING, but we need it to be PROCESSING
            
            self.state = "PROCESSING"
            # Start speaking task
            self._speaking_task = asyncio.create_task(self._generate_response(transcript.strip()))
        else:
            logger.info("🔇 No clear speech recognized")
            if not was_speaking and self.state == "PROCESSING":
                self.state = "LISTENING"
                await self._emit("status", {"state": "LISTENING", "message": "Listening..."})

    # ── Speech-to-Text ────────────────────────────────────────────────

    async def _stt(self, audio: np.ndarray) -> str:
        """
        Convert user audio to text.

        Groq's hosted Whisper (large-v3-turbo) is tried first when a key is
        configured — it is meaningfully more accurate than the free, unofficial
        Google Web Speech endpoint, especially for quieter or accented speech,
        and it's run here with temperature=0 and condition_on_previous_text=False
        specifically to minimize the noise-hallucination risk Whisper is known
        for. Google STT is kept as a fallback for when Groq is unavailable or
        errors out.
        """
        audio_clipped = np.clip(audio, -1.0, 1.0)
        audio_int16 = (audio_clipped * 32767).astype(np.int16)

        groq_key = os.environ.get("GROQ_API_KEY", "")
        if groq_key:
            text = await self._stt_groq(audio_int16, groq_key)
            if text and text.strip():
                return text

        return await self._stt_google(audio_int16)

    async def _stt_groq(self, audio_int16: np.ndarray, groq_key: str) -> str:
        """Transcribe via Groq's hosted Whisper API."""
        try:
            import io, wave, httpx
            buf = io.BytesIO()
            with wave.open(buf, 'wb') as wf:
                wf.setnchannels(1)
                wf.setsampwidth(2)
                wf.setframerate(self.client_sample_rate)
                wf.writeframes(audio_int16.tobytes())

            buf.seek(0)
            files = {'file': ('audio.wav', buf.read(), 'audio/wav')}
            data = {'model': 'whisper-large-v3-turbo', 'language': 'en', 'temperature': '0.0', 'condition_on_previous_text': 'false'}

            async with httpx.AsyncClient(timeout=10.0) as client:
                r = await client.post(
                    'https://api.groq.com/openai/v1/audio/transcriptions',
                    headers={'Authorization': f'Bearer {groq_key}'},
                    files=files,
                    data=data
                )
                if r.status_code == 200:
                    return r.json().get("text", "").strip()
                logger.debug(f"Groq STT returned status {r.status_code}: {r.text[:200]}")
        except Exception as e:
            logger.debug(f"Groq STT failed, falling back to Google: {e}")
        return ""

    async def _stt_google(self, audio_int16: np.ndarray) -> str:
        """Transcribe via the free Google Web Speech endpoint (fallback)."""
        try:
            import speech_recognition as sr
            recognizer = sr.Recognizer()
            # sample_width=2 bytes, matching our int16 PCM data
            audio_data = sr.AudioData(audio_int16.tobytes(), self.client_sample_rate, 2)

            loop = asyncio.get_event_loop()
            text = await loop.run_in_executor(
                None,
                lambda: recognizer.recognize_google(audio_data, language="en-US")
            )
            return text or ""
        except Exception as e:
            logger.warning(f"Google STT error: {type(e).__name__}: {e}")
            return ""

    # ── Response Generation + Inner Monologue ─────────────────────────

    async def _generate_response(self, user_text: str):
        """
        Generate and deliver Moshi's response with inner monologue.

        Architecture mirrors the paper:
        1. LLM generates response text (Inner Monologue phase — text tokens first)
        2. Text streamed token-by-token to UI (visible inner monologue)
        3. TTS converts text to audio (Mimi decoder simulation)
        """
        self.state = "SPEAKING"
        self.monologue.begin()

        await self._emit("status", {"state": "SPEAKING", "message": "Speaking..."})
        await self._emit("monologue_start", {})

        try:
            # ── Call LLM backend ──────────────────────────────────────
            await self._emit("status", {"state": "PROCESSING", "message": "Thinking..."})
            
            # Clear the frame after use so we don't send stale images
            image_frame = self.latest_video_frame
            self.latest_video_frame = None
            
            await self._emit("status", {
                "state": "SPEAKING",
                "message": f"Speaking...",
            })

            sentence_queue = asyncio.Queue()
            
            async def _tts_audio_pipeline():
                pending_audio_tasks = asyncio.Queue()
                
                async def _generator_worker():
                    while True:
                        sentence = await sentence_queue.get()
                        if sentence is None:
                            await pending_audio_tasks.put(None)
                            break
                        if self._interrupt_event.is_set():
                            break
                        task = asyncio.create_task(self._generate_tts_bytes(sentence))
                        await pending_audio_tasks.put((sentence, task))
                        
                gen_task = asyncio.create_task(_generator_worker())
                
                try:
                    while True:
                        item = await pending_audio_tasks.get()
                        if item is None:
                            break
                        if self._interrupt_event.is_set():
                            break
                        sentence, task = item
                        audio_bytes = await task
                        if audio_bytes and not self._interrupt_event.is_set():
                            await self._play_tts_bytes(sentence, audio_bytes)
                finally:
                    if not gen_task.done():
                        gen_task.cancel()

            # Start the TTS pipeline worker
            tts_pipeline_task = asyncio.create_task(_tts_audio_pipeline())

            response_text = ""
            current_sentence = ""
            in_json_block = False
            
            # Construct Cart Context
            cart_data = self.cart.to_dict()
            cart_context = f"CURRENT CART:\n{json.dumps(cart_data, indent=2)}\n"
            
            # Stream tokens from LLM
            async for token in self.llm.stream_generate(user_text, image_base64=image_frame, cart_context=cart_context):
                if self._interrupt_event.is_set():
                    break
                    
                response_text += token
                
                # Check for JSON block start
                if "{" in token and len(current_sentence.strip()) < 5:
                    in_json_block = True
                    
                if in_json_block:
                    if "}" in token:
                        in_json_block = False
                    continue
                
                # Filter markdown json formatting
                if token.strip() == "```" or token.strip() == "```json":
                    continue
                
                current_sentence += token
                
                # Emit token to UI for inner monologue
                self.monologue.add_token(token)
                await self._emit("inner_monologue", {
                    "token": token,
                    "full_text": self.monologue.current,
                    "done": False,
                    "progress": 0.5, # Indeterminate
                })
                
                # Check for sentence boundaries
                if any(punct in token for punct in ['.', '!', '?', '\n']):
                    # Yield complete sentence to the TTS queue
                    clean_sentence = current_sentence.strip()
                    if len(clean_sentence) > 2:
                        await sentence_queue.put(clean_sentence)
                    current_sentence = ""
                    
            # Handle any remaining text
            if current_sentence.strip() and not self._interrupt_event.is_set():
                if len(current_sentence.strip()) > 1:
                    await sentence_queue.put(current_sentence.strip())
            
            # Signal end of stream
            await sentence_queue.put(None)
            
            if not self._interrupt_event.is_set():
                self.monologue.commit()
                await self._emit("inner_monologue", {
                    "token": "",
                    "full_text": self.monologue.current,
                    "done": True,
                    "progress": 1.0,
                })

            # ── PHASE 2: Parse Actions & Transcript ───────────────
            response_text = response_text.strip()
            
            # Check for JSON Action Block anywhere in the response
            action_match = re.search(r'(\{.*?\})', response_text, re.DOTALL)
            if action_match:
                try:
                    action_data = json.loads(action_match.group(1))
                    logger.info(f"🛒 LLM Action: {action_data}")
                    action_type = action_data.get("action")
                    
                    if action_type == "add_item":
                        item_name = action_data.get("item_name")
                        quantity = action_data.get("quantity", 1)
                        item = find_item_by_name(item_name)
                        if item:
                            self.cart.add_item(item, quantity)
                    elif action_type == "remove_item":
                        item_name = action_data.get("item_name")
                        self.cart.remove_by_name(item_name)
                    elif action_type == "mark_declined":
                        category = action_data.get("category")
                        self.cart.mark_declined(category)
                    elif action_type == "checkout":
                        logger.info("Checkout initiated.")
                    elif action_type == "show_category":
                        raw_category = action_data.get("category")
                        category = find_category_by_name(raw_category)
                        if category:
                            logger.info(f"📂 Switching UI to category: {category}")
                            await self._emit("category_change", {"category": category})
                        
                    # Broadcast cart update
                    await self._emit("cart_update", self.cart.to_dict())
                    
                    # Remove JSON block and markdown from spoken text transcript
                    response_text = re.sub(r'```json.*?```', '', response_text, flags=re.DOTALL)
                    response_text = re.sub(r'\{.*?\}', '', response_text, flags=re.DOTALL).strip()
                except Exception as e:
                    logger.error(f"Failed to parse action JSON: {e}")

            # Wait for audio to finish playing
            await tts_pipeline_task

            if response_text:
                await self._emit("transcript", {"speaker": "moshi", "text": response_text})

        except asyncio.CancelledError:
            logger.info("🛑 Response generation cancelled (interrupted)")
            raise
        except Exception as e:
            logger.error(f"Response error: {e}", exc_info=True)
        finally:
            if 'tts_pipeline_task' in locals() and not tts_pipeline_task.done():
                tts_pipeline_task.cancel()
                
            if self.state == "SPEAKING":
                self.state = "LISTENING"
                await self._emit("status", {"state": "LISTENING", "message": "Listening..."})
                await self._emit("audio_level", {"channel": "model", "level": 0.0, "is_speech": False})

    # ── Text-to-Speech Streaming ──────────────────────────────────────

    async def _tts_stream(self, text: str):
        """
        Stream TTS audio back to the browser.
        Uses Audio Pipelining: Starts generating sentence N+1 while playing sentence N
        to completely eliminate network latency gaps between sentences.
        """
        sentences = split_sentences(text)
        if not sentences:
            return

        # Pre-fetch the first sentence
        next_task = asyncio.create_task(self._generate_tts_bytes(sentences[0]))

        for i in range(len(sentences)):
            if self._interrupt_event.is_set():
                next_task.cancel()
                return

            # Wait for current sentence to generate
            audio_bytes = await next_task
            
            # Immediately start generating the NEXT sentence (Pipelining!)
            if i + 1 < len(sentences):
                next_task = asyncio.create_task(self._generate_tts_bytes(sentences[i+1]))
            
            # Send audio and animate waveform for the CURRENT sentence
            if audio_bytes and not self._interrupt_event.is_set():
                await self._play_tts_bytes(sentences[i], audio_bytes)

    async def _generate_tts_bytes(self, text: str) -> Optional[bytes]:
        """Generate audio bytes for a single sentence."""
        try:
            import os
            
            # --- OPENAI TTS INTEGRATION ---
            api_key = os.environ.get("OPENAI_API_KEY")
            
            if not api_key or api_key == "your_openai_api_key_here":
                logger.error("No OPENAI_API_KEY found! Falling back to Edge TTS.")
                import edge_tts
                communicate = edge_tts.Communicate(
                    text, voice="en-US-AriaNeural", rate="+5%", pitch="+0Hz", volume="+0%"
                )
                chunks: list[bytes] = []
                async for chunk in communicate.stream():
                    if self._interrupt_event.is_set():
                        return
                    if chunk["type"] == "audio":
                        chunks.append(chunk["data"])
                
                if self._interrupt_event.is_set() or not chunks:
                    return None
                audio_bytes = b"".join(chunks)
                logger.debug(f"🔊 Generated {len(audio_bytes)} bytes of fallback audio")
                return audio_bytes
            else:
                try:
                    from openai import AsyncOpenAI
                    
                    # If we already got a quota error this session, skip OpenAI to save 2 seconds of latency!
                    if getattr(self, "_openai_quota_exceeded", False):
                        raise Exception("Skipping OpenAI due to previous quota error")

                    client = AsyncOpenAI(api_key=api_key, max_retries=0)

                    response = await client.audio.speech.create(
                        model="tts-1",
                        voice="alloy",
                        input=text,
                        response_format="mp3"
                    )

                    chunks = []
                    async for chunk in response.aiter_bytes(chunk_size=4096):
                        if self._interrupt_event.is_set():
                            return None
                        if chunk:
                            chunks.append(chunk)

                    if self._interrupt_event.is_set() or not chunks:
                        return None

                    audio_bytes = b"".join(chunks)
                    logger.debug(f"🔊 Generated {len(audio_bytes)} bytes of OpenAI audio")
                    return audio_bytes
                except Exception as e:
                    if "insufficient_quota" in str(e):
                        self._openai_quota_exceeded = True
                        
                    logger.warning(f"OpenAI TTS failed, falling back to Edge TTS (fast).")
                    import edge_tts
                    communicate = edge_tts.Communicate(
                        text, voice="en-US-AriaNeural", rate="+5%", pitch="+0Hz", volume="+0%"
                    )
                    chunks: list[bytes] = []
                    async for chunk in communicate.stream():
                        if self._interrupt_event.is_set():
                            return None
                        if chunk["type"] == "audio":
                            chunks.append(chunk["data"])
                    
                    if self._interrupt_event.is_set() or not chunks:
                        return None
                    audio_bytes = b"".join(chunks)
                    logger.debug(f"🔊 Generated {len(audio_bytes)} bytes of fallback audio")
                    return audio_bytes
        except asyncio.CancelledError:
            raise
        except Exception as e:
            logger.error(f"TTS generation error: {e}", exc_info=True)
            return None

    async def _play_tts_bytes(self, text: str, audio_bytes: bytes):
        """Send bytes to frontend and animate waveform."""
        try:
            await self.ws.send_bytes(audio_bytes)

            # Send audio level events to animate model waveform
            # Estimate duration: ~0.3s per word for natural speech
            word_count = max(1, len(text.split()))
            estimated_duration = word_count * 0.32
            updates = max(5, int(estimated_duration * 15))  # 15 updates/sec

            for i in range(updates):
                if self._interrupt_event.is_set():
                    return
                # Natural amplitude envelope (rises and falls)
                t = i / updates
                envelope = np.sin(t * np.pi) ** 0.5
                level = 0.35 + 0.55 * envelope
                await self._emit("audio_level", {
                    "channel": "model",
                    "level": round(float(level), 3),
                    "is_speech": True,
                })
                await asyncio.sleep(estimated_duration / updates)

        except asyncio.CancelledError:
            raise
        except Exception as e:
            logger.error(f"TTS error: {e}", exc_info=True)

    # ── Control Messages ──────────────────────────────────────────────

    async def _on_control(self, msg: dict):
        """Handle control messages from browser."""
        mtype = msg.get("type")

        if mtype == "interrupt":
            if self.state == "SPEAKING":
                await self._interrupt()

        elif mtype == "setup":
            self.client_sample_rate = msg.get("sample_rate", SAMPLE_RATE)
            self.vad.sample_rate = self.client_sample_rate
            frames_per_sec = self.client_sample_rate / FRAME_SIZE
            self.silence_frames_threshold = int(0.8 * frames_per_sec)
            self.interrupt_min_frames = max(2, int(0.3 * frames_per_sec))
            logger.info(f"Client sample rate set to {self.client_sample_rate}, thresholds: {self.silence_frames_threshold} silence, {self.interrupt_min_frames} interrupt")

            async def _initial_greet():
                await asyncio.sleep(0.5)
                self.state = "SPEAKING"
                await self._emit("status", {"state": "SPEAKING", "message": "Speaking..."})
                greet_text = "Hey, I am your Hedes. How may I help you?"
                await self._emit("transcript", {"speaker": "moshi", "text": greet_text})
                audio = await self._generate_tts_bytes(greet_text)
                if audio and not self._interrupt_event.is_set():
                    await self._play_tts_bytes(greet_text, audio)
                if self.state == "SPEAKING":
                    self.state = "LISTENING"
                    await self._emit("status", {"state": "LISTENING", "message": "Listening..."})
                    
            self._speaking_task = asyncio.create_task(_initial_greet())

        elif mtype == "user_action":
            # Handle frontend click events
            action = msg.get("action")
            if action == "add":
                item_name = msg.get("item")
                item = find_item_by_name(item_name)
                if item:
                    self.cart.add_item(item, 1)
                    await self._emit("cart_update", self.cart.to_dict())
            elif action == "remove":
                cart_id = msg.get("cart_id")
                if cart_id:
                    self.cart.remove_item(cart_id)
                    await self._emit("cart_update", self.cart.to_dict())

        elif mtype == "set_vad_threshold":
            value = float(msg.get("value", 0.008))
            self.vad.set_threshold(value)
            logger.info(f"🎚️  VAD threshold set to {value:.4f}")

        elif mtype == "ping":
            await self._emit("pong", {"state": self.state})

    # ── Event Emitter ─────────────────────────────────────────────────

    async def _emit(self, event_type: str, data: dict):
        """Send a JSON event to the browser."""
        try:
            payload = json.dumps({"type": event_type, **data}, ensure_ascii=False)
            await self.ws.send_text(payload)
        except Exception:
            pass  # Connection might have closed

    def stop(self):
        """Gracefully stop the engine."""
        self._running = False
        self._interrupt_event.set()
        if self._speaking_task and not self._speaking_task.done():
            self._speaking_task.cancel()

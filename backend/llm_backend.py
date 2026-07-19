"""
llm_backend.py — Flexible LLM Backend for Hedes Simulation
============================================================
Tries multiple free/local backends in order:
  1. Ollama  — local LLM (llama3, mistral, etc.) if running on localhost:11434
  2. g4f     — free GPT-4o / Claude access via unofficial APIs (no key needed)
  3. Gemini  — Google Gemini free tier (if GEMINI_API_KEY env var set)
  4. Groq    — Ultra-fast free tier (if GROQ_API_KEY env var set)
  5. Rule-based — always works, last resort

Maintains conversation history for coherent multi-turn dialogue.
"""

import os
import json
import logging
import asyncio
import re
from typing import Optional, List, Dict, AsyncGenerator
from menu_data import MENU_ITEMS, MENU_CATEGORIES

logger = logging.getLogger("moshi.llm")


def _build_menu_text() -> str:
    """Render the real menu, grouped by category, for the system prompt."""
    lines = []
    for cat in MENU_CATEGORIES:
        items = [i for i in MENU_ITEMS if i["category"] == cat]
        if not items:
            continue
        lines.append(f"{cat}:")
        for item in items:
            lines.append(f"  - {item['name']} — ₹{item['price']}")
    return "\n".join(lines)


MENU_TEXT = _build_menu_text()

# ── System prompt that makes Moshi feel like a real voice AI ──────────
SYSTEM_PROMPT = f"""You are Hedes, a friendly, persuasive, and intelligent digital menu AI cashier \
created by sheel. You are taking orders at a fast-food drive-thru or kiosk.

THE MENU (this is the ONLY thing this restaurant sells):
{MENU_TEXT}

MENU RULES — FOLLOW STRICTLY:
- You may ONLY talk about, recommend, describe, or add items that appear in the menu list above, word for word.
- NEVER invent, assume, or mention a dish, drink, size, flavor, or combo that is not explicitly listed above, even if it sounds like something a fast-food place "probably" has.
- If the customer asks for something that isn't listed (e.g. a menu item, size, or brand that doesn't exist above), politely say it's not available on this menu, and suggest the closest real item from the list instead.
- If you are not sure whether something is on the menu, treat it as NOT on the menu and check the list above rather than guessing.
- When you tell the customer what's available in a category (e.g. "what drinks do you have?"), only read out real items from that category above — do not pad the list with made-up options.

RULES:
- Keep answers VERY SHORT (1-2 sentences). You are speaking, not writing.
- Be conversational, enthusiastic, and act like a real cashier.
- You have access to a live cart and a menu.
- If the user orders something, take action using the exact JSON format below.
- You MUST only use JSON actions for the cart. Do NOT use them unless taking an action.
- When you output JSON, put it at the VERY BEGINNING of your response, on a new line starting with "{{" and ending with "}}".

AVAILABLE ACTIONS (JSON):
{{"action": "add_item", "item_name": "exact menu item name", "quantity": 1}}
{{"action": "remove_item", "item_name": "exact menu item name"}}
{{"action": "mark_declined", "category": "category name"}}
{{"action": "checkout"}}
{{"action": "show_category", "category": "category name"}}

NAVIGATION:
- If the customer asks to see a category, OR asks what items are in a category (e.g. "show me beverages", "what drinks do you have?"), output {{"action": "show_category", "category": "category name"}} to switch their screen, AND ALSO read out some of the items.

UPSELLING:
- When the cart is missing a pairing (e.g., they have a Burger but no Drink), naturally suggest it — using only real menu items!
- Do not suggest a category if the user previously declined it.
- If they decline an upsell, output {{"action": "mark_declined", "category": "category name"}}.
"""


class ConversationHistory:
    """Maintains rolling conversation context for coherent dialogue."""

    def __init__(self, max_turns: int = 8):
        self.max_turns = max_turns
        self._history: list[dict] = []

    def add_user(self, text: str):
        self._history.append({"role": "user", "content": text})
        self._trim()

    def add_assistant(self, text: str):
        self._history.append({"role": "assistant", "content": text})
        self._trim()

    def get_messages(self) -> list[dict]:
        """Return messages list including system prompt."""
        return [{"role": "system", "content": SYSTEM_PROMPT}] + self._history

    def _trim(self):
        # Keep last N turns (user+assistant pairs)
        max_msgs = self.max_turns * 2
        if len(self._history) > max_msgs:
            self._history = self._history[-max_msgs:]

    def clear(self):
        self._history.clear()


class LLMBackend:
    """
    Tries multiple LLM backends in priority order.
    Falls back gracefully if a backend is unavailable.
    """

    def __init__(self):
        self.history = ConversationHistory()
        self._active_backend: Optional[str] = None
        self._ollama_model: Optional[str] = None

    async def generate(self, user_text: str, image_base64: Optional[str] = None, cart_context: str = "") -> str:
        """Generate a response to user_text using best available backend."""
        self.history.add_user(user_text)
        messages = self.history.get_messages()
        
        # Inject cart context into system prompt temporarily for this generation
        if cart_context:
            messages[0]["content"] += "\n\n" + cart_context

        response = None

        # 0. Try Gemini immediately if an image is provided (Multimodal)
        if image_base64:
            response = await self._try_gemini(messages, user_text, image_base64)
            if response:
                self._active_backend = "gemini-vision"
                self.history.add_assistant(response)
                return response
            else:
                logger.warning("Image provided but Gemini vision failed. Falling back to local Ollama LLaVA.")
                response = await self._try_ollama_vision(messages, user_text, image_base64)
                if response:
                    self._active_backend = "ollama-vision"
                    self.history.add_assistant(response)
                    return response
                else:
                    logger.warning("Local Ollama vision failed. Falling back to text-only.")

        # 1. Try Ollama (fully local, highest quality if available)
        response = await self._try_ollama(messages)
        if response:
            self._active_backend = "ollama"
            self.history.add_assistant(response)
            return response

        # 2. Try g4f (free GPT-4o / Claude, no API key needed)
        response = await self._try_g4f(messages)
        if response:
            self._active_backend = "g4f"
            self.history.add_assistant(response)
            return response

        # 3. Try Gemini (if API key set)
        if not image_base64: # already tried above if there was an image
            response = await self._try_gemini(messages, user_text)
            if response:
                self._active_backend = "gemini"
                self.history.add_assistant(response)
                return response

        # 4. Try Groq (if API key set)
        response = await self._try_groq(messages)
        if response:
            self._active_backend = "groq"
            self.history.add_assistant(response)
            return response

        # 5. Smart rule-based fallback
        response = _smart_fallback(user_text)
        self._active_backend = "fallback"
        self.history.add_assistant(response)
        return response

    async def stream_generate(self, user_text: str, image_base64: Optional[str] = None, cart_context: str = "") -> AsyncGenerator[str, None]:
        """Generate response token-by-token using streaming where supported."""
        self.history.add_user(user_text)
        messages = self.history.get_messages()

        if cart_context:
            messages[0]["content"] += "\n\n" + cart_context

        # Currently we only support streaming on Groq because it's the fastest and primary backend.
        # If Groq is available, use it. Otherwise fallback to the normal block generator.
        api_key = os.environ.get("GROQ_API_KEY", "")
        
        # If no image and we have Groq, use the ultra-fast streaming endpoint!
        if api_key and not image_base64:
            self._active_backend = "groq-stream"
            full_response = ""
            try:
                async for chunk in self._stream_groq(messages):
                    full_response += chunk
                    yield chunk
                self.history.add_assistant(full_response)
                return
            except Exception as e:
                logger.debug(f"Groq streaming failed: {e}. Falling back to normal generate.")
                
        # Fallback to blocking generate, then yield the whole chunk
        response = await self.generate(user_text, image_base64, cart_context)
        yield response
        
    # ── Backend implementations ───────────────────────────────────────

    async def _try_ollama(self, messages: list[dict]) -> Optional[str]:
        """Try local Ollama API."""
        try:
            import httpx

            # Auto-discover available model
            if self._ollama_model is None:
                async with httpx.AsyncClient(timeout=2.0) as client:
                    r = await client.get("http://localhost:11434/api/tags")
                    if r.status_code == 200:
                        models = r.json().get("models", [])
                        preferred = ["llama3", "llama3.2", "llama3.1", "mistral",
                                     "gemma2", "gemma", "phi3", "qwen2", "llama2"]
                        available = [m["name"].split(":")[0] for m in models]
                        for p in preferred:
                            if p in available:
                                self._ollama_model = p
                                break
                        if not self._ollama_model and available:
                            self._ollama_model = available[0]
                        if not self._ollama_model:
                            return None

            async with httpx.AsyncClient(timeout=20.0) as client:
                r = await client.post(
                    "http://localhost:11434/api/chat",
                    json={
                        "model": self._ollama_model,
                        "messages": messages,
                        "stream": False,
                        "options": {"temperature": 0.7, "num_predict": 150}
                    }
                )
                if r.status_code == 200:
                    text = r.json()["message"]["content"].strip()
                    logger.info(f"Ollama ({self._ollama_model}): {text[:60]}...")
                    return _clean_response(text)

        except Exception as e:
            logger.debug(f"Ollama unavailable: {type(e).__name__}")
        return None

    async def _try_g4f(self, messages: list[dict]) -> Optional[str]:
        """Try g4f (free GPT-4o/Claude via unofficial APIs)."""
        try:
            from g4f.client import AsyncClient as G4FClient

            client = G4FClient()

            # Try multiple providers in case some are down
            try:
                import g4f.Provider as P
                providers_to_try = [
                    (P.PollinationsAI, "llama"),
                    (None, "gpt-4o-mini"),  # auto fallback
                ]
            except Exception:
                providers_to_try = [(None, "gpt-4o-mini")]

            for provider, model_name in providers_to_try:
                try:
                    kwargs = {
                        "model": model_name,
                        "messages": messages,
                    }
                    if provider is not None:
                        kwargs["provider"] = provider

                    response = await asyncio.wait_for(
                        client.chat.completions.create(**kwargs),
                        timeout=15.0
                    )
                    text = response.choices[0].message.content
                    if text and len(text.strip()) > 5:
                        text = _clean_response(text.strip())
                        prov_name = provider.__name__ if provider else 'auto'
                        logger.info(f"g4f ({prov_name}): {text[:60]}...")
                        return text
                except asyncio.TimeoutError:
                    continue
                except Exception as e:
                    prov_name = provider.__name__ if provider else 'auto'
                    logger.debug(f"g4f provider {prov_name} failed: {e}")
                    continue

        except ImportError:
            logger.debug("g4f not installed")
        except Exception as e:
            logger.debug(f"g4f failed: {type(e).__name__}: {e}")
        return None

    async def _try_gemini(self, messages: list[dict], user_text: str, image_base64: Optional[str] = None) -> Optional[str]:
        """Try Google Gemini API (requires GEMINI_API_KEY env var)."""
        api_key = os.environ.get("GEMINI_API_KEY", "")
        if not api_key:
            return None
        try:
            import httpx
            # Build prompt from history
            prompt = "\n".join(
                f"{m['role'].upper()}: {m['content']}"
                for m in messages
            )
            
            parts = [{"text": prompt}]
            if image_base64:
                parts.append({
                    "inline_data": {
                        "mime_type": "image/jpeg",
                        "data": image_base64
                    }
                })

            async with httpx.AsyncClient(timeout=15.0) as client:
                r = await client.post(
                    f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key={api_key}",
                    json={"contents": [{"parts": parts}]}
                )
                if r.status_code == 200:
                    text = r.json()["candidates"][0]["content"]["parts"][0]["text"]
                    return _clean_response(text.strip())
                else:
                    logger.error(f"Gemini API Error {r.status_code}: {r.text}")
        except Exception as e:
            logger.debug(f"Gemini failed: {e}")
        return None

    async def _try_groq(self, messages: list[dict]) -> Optional[str]:
        """Try Groq API (requires GROQ_API_KEY env var, free tier available)."""
        api_key = os.environ.get("GROQ_API_KEY", "")
        if not api_key:
            return None
        try:
            import httpx
            async with httpx.AsyncClient(timeout=15.0) as client:
                r = await client.post(
                    "https://api.groq.com/openai/v1/chat/completions",
                    headers={"Authorization": f"Bearer {api_key}"},
                    json={
                        "model": "llama-3.1-8b-instant",
                        "messages": messages,
                        "max_tokens": 150,
                        "temperature": 0.7,
                    }
                )
                if r.status_code == 200:
                    text = r.json()["choices"][0]["message"]["content"]
                    return _clean_response(text.strip())
        except Exception as e:
            logger.debug(f"Groq failed: {e}")
        return None

    async def _stream_groq(self, messages: list[dict]) -> AsyncGenerator[str, None]:
        """Stream Google Groq API responses."""
        api_key = os.environ.get("GROQ_API_KEY", "")
        if not api_key:
            raise ValueError("No Groq API key")
            
        import httpx
        async with httpx.AsyncClient(timeout=15.0) as client:
            async with client.stream(
                "POST",
                "https://api.groq.com/openai/v1/chat/completions",
                headers={"Authorization": f"Bearer {api_key}"},
                json={
                    "model": "llama-3.1-8b-instant",
                    "messages": messages,
                    "max_tokens": 150,
                    "temperature": 0.7,
                    "stream": True,
                }
            ) as response:
                if response.status_code != 200:
                    raise Exception(f"Groq API Error {response.status_code}")
                    
                async for line in response.aiter_lines():
                    if line.startswith("data: ") and line != "data: [DONE]":
                        try:
                            data = json.loads(line[6:])
                            token = data["choices"][0].get("delta", {}).get("content")
                            if token:
                                yield token
                        except:
                            pass

    async def _try_ollama_vision(self, messages: list[dict], user_text: str, image_base64: str) -> Optional[str]:
        """Try local Ollama API using the LLaVA vision model."""
        try:
            import httpx

            # Ensure we're only sending the latest user message with the image to the vision model
            # as some local vision models struggle with long multi-turn text contexts alongside images
            vision_messages = [
                {
                    "role": "user",
                    "content": user_text,
                    "images": [image_base64]
                }
            ]

            async with httpx.AsyncClient(timeout=30.0) as client:
                r = await client.post(
                    "http://localhost:11434/api/chat",
                    json={
                        "model": "llava",
                        "messages": vision_messages,
                        "stream": False,
                        "options": {"temperature": 0.7, "num_predict": 100}
                    }
                )
                if r.status_code == 200:
                    text = r.json()["message"]["content"]
                    return _clean_response(text)
                else:
                    logger.error(f"Ollama Vision API Error {r.status_code}: {r.text}")
        except Exception as e:
            logger.debug(f"Ollama vision failed: {e}")
        return None

    def get_backend_name(self) -> str:
        return self._active_backend or "unknown"


# ── Smart Fallback (handles common question types) ────────────────────

def _smart_fallback(user_text: str) -> str:
    """
    Smarter fallback that handles common question types:
    spelling, math, factual questions, etc.
    """
    text = user_text.lower().strip()

    # ── Spelling questions ────────────────────────────────────────────
    spell_match = re.search(
        r"(?:spell|how (?:do you |to )?spell|spelling of|how is .+ spelled?)\s+(\w+)",
        text
    )
    if spell_match:
        word = spell_match.group(1).upper()
        letters = "-".join(list(word))
        return (
            f"{word} is spelled {letters}. "
            f"That's {letters}, which spells {word.capitalize()}."
        )

    # ── Simple math ───────────────────────────────────────────────────
    math_match = re.search(
        r"what(?:'s| is)\s+(\d+)\s*([+\-×x*÷/])\s*(\d+)",
        text
    )
    if math_match:
        try:
            a, op, b = int(math_match.group(1)), math_match.group(2), int(math_match.group(3))
            ops = {'+': a+b, '-': a-b, '*': a*b, 'x': a*b, '×': a*b,
                   '/': round(a/b, 2) if b != 0 else "undefined", '÷': round(a/b, 2) if b != 0 else "undefined"}
            result = ops.get(op)
            op_word = {'+': 'plus', '-': 'minus', '*': 'times', 'x': 'times',
                       '×': 'times', '/': 'divided by', '÷': 'divided by'}.get(op, op)
            return f"{a} {op_word} {b} equals {result}."
        except Exception:
            pass

    # ── Common greetings ─────────────────────────────────────────────
    if any(w in text for w in ["hello", "hi ", "hey", "good morning", "good evening"]):
        return ("Hello! I'm Hedes, your full-duplex voice AI. I'm ready to help you with "
                "your fast-food order today. What can I get for you?")
    
    if any(w in text_lower for w in ["how are you", "how are you doing"]):
        return ("I'm doing great, thank you! I'm Hedes, your AI assistant. "
                "I'm here to help — what would you like to know?")

    # ── Social questions ─────────────────────────────────────────────
    if "friend" in text:
        return ("Making friends is all about shared interests and open communication. "
                "Try joining a club, taking a class, or just saying hello to someone new. "
                "The most important thing is to be yourself!")

    # ── Wikipedia Knowledge Base ───────────────────────────────────────
    try:
        import wikipedia
        wikipedia.set_user_agent('HedesBot/1.0')
        
        query = text
        for prefix in ["who is the ", "who is ", "what is the ", "what is ", "tell me about ", "can you tell me about "]:
            if query.startswith(prefix):
                query = query[len(prefix):]
                break
        
        # Only search if we have a substantial query
        if len(query) > 3:
            results = wikipedia.search(query)
            if results:
                summary = wikipedia.summary(results[0], sentences=2, auto_suggest=False)
                summary = re.sub(r'\[\d+\]', '', summary)
                return f"According to my local knowledge base: {summary}"
    except Exception as e:
        logger.debug(f"Wikipedia fallback failed: {e}")
        pass

    # ── Conversational Eliza-style Default ───────────────────────────
    words = text.split()
    if len(words) > 3:
        topic = " ".join(words[-2:]).strip("?")
        return (f"That's really interesting that you mention {topic}. "
                "Because of my current network firewall, my main AI brain is offline, "
                "but I'm still actively listening! What else is on your mind?")
    
    return (f"I hear you! You said: {user_text}. "
            "I'm currently running in offline mode. "
            "Try asking me to spell a word, solve a math problem, or ask a factual question!")


def _clean_response(text: str) -> str:
    """Clean and truncate response for voice output."""
    # Remove markdown formatting
    text = re.sub(r'\*\*(.*?)\*\*', r'\1', text)
    text = re.sub(r'\*(.*?)\*', r'\1', text)
    text = re.sub(r'`(.*?)`', r'\1', text)
    text = re.sub(r'#{1,6}\s', '', text)
    text = re.sub(r'\n+', ' ', text)

    # Trim to ~3 sentences for voice
    sentences = re.split(r'(?<=[.!?])\s+', text.strip())
    if len(sentences) > 4:
        text = ' '.join(sentences[:4])

    return text.strip()

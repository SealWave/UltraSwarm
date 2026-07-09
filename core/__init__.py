"""
core/gemini_client.py
=====================
Wraps Google Gemini 2.0 Flash as an OpenAI-compatible client so OpenAI Swarm
can use it transparently. This is the engine that powers every agent.
"""

import os
import json
import re
import time
import threading
from typing import Any, Optional
from dotenv import load_dotenv

try:
    import google.generativeai as genai
except Exception:  # pragma: no cover - optional dependency in some uv envs
    genai = None

load_dotenv()

# ── Configure Gemini globally ──────────────────────────────────────────────
DEFAULT_API_KEY = os.getenv("GOOGLE_API_KEY")
MODEL = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
MAX_TOKENS = int(os.getenv("MAX_TOKENS", 8192))
TEMPERATURE = float(os.getenv("AGENT_TEMPERATURE", 0.7))
MIN_SECONDS_BETWEEN_REQUESTS = float(os.getenv("GEMINI_MIN_SECONDS_BETWEEN_REQUESTS", "4"))
_REQUEST_LOCK = threading.Lock()
_LAST_REQUEST_TS = 0.0


class GeminiClient:
    """
    Drop-in Gemini wrapper with tool-calling support.
    Each agent gets its own instance with its own system prompt + history.
    """

    def __init__(self, system_prompt: str = "", agent_name: str = "Agent", api_key: str = None):
        self.agent_name = agent_name
        self.system_prompt = system_prompt
        self.history: list[dict] = []
        self.api_key = api_key or DEFAULT_API_KEY

        if genai is None:
            raise RuntimeError(
                "google-generativeai is not installed in the active environment. "
                "Install it or set USE_LOCAL_LLM=true for local-only workflows."
            )

        # Configure for this specific instance
        genai.configure(api_key=self.api_key)

        self.model = genai.GenerativeModel(
            model_name=MODEL,
            system_instruction=system_prompt,
            generation_config=genai.types.GenerationConfig(
                max_output_tokens=MAX_TOKENS,
                temperature=TEMPERATURE,
            ),
        )
        self.chat = self.model.start_chat(history=[])

    def reset(self):
        """Clear conversation history (start fresh task)."""
        self.chat = self.model.start_chat(history=[])
        self.history = []

    def ask(self, prompt: str, tools: list = None) -> str:
        """
        Send a message and get a response.
        """
        try:
            if genai is None:
                raise RuntimeError(
                    "google-generativeai is not installed in the active environment. "
                    "Install it or set USE_LOCAL_LLM=true for local-only workflows."
                )
            # Re-configure key before call to ensure this instance uses its assigned key
            genai.configure(api_key=self.api_key)
            _wait_for_local_rate_limit()
            
            response = self.chat.send_message(prompt)
            text = response.text
            self.history.append({"role": "user", "content": prompt})
            self.history.append({"role": "assistant", "content": text})
            return text
        except Exception as e:
            return f"[{self.agent_name} ERROR]: {str(e)}"

    def ask_json(self, prompt: str, schema_hint: str = "") -> dict:
        """
        Ask and parse response as JSON.
        Adds JSON enforcement to prompt automatically.
        """
        json_prompt = f"""{prompt}

IMPORTANT: Respond ONLY with valid JSON. No markdown fences, no preamble, no explanation.
{f'Expected schema: {schema_hint}' if schema_hint else ''}
"""
        response = self.ask(json_prompt)
        # Strip any accidental markdown
        clean = re.sub(r"```json|```", "", response).strip()
        try:
            return json.loads(clean)
        except json.JSONDecodeError:
            # Try to extract JSON object/array from response
            match = re.search(r"(\{.*\}|\[.*\])", clean, re.DOTALL)
            if match:
                try:
                    return json.loads(match.group(1))
                except Exception:
                    pass
            rate_limit = _extract_rate_limit(response)
            return {"raw_response": response, "parse_error": True, **rate_limit}

    def ask_structured(self, prompt: str, output_keys: list[str]) -> dict:
        """
        Ask and return a dict guaranteed to have the specified keys.
        """
        schema = "{" + ", ".join(f'"{k}": "..."' for k in output_keys) + "}"
        return self.ask_json(prompt, schema_hint=schema)


class LocalLLMClient:
    """
    OpenAI-compatible client for Local LLMs (e.g. LM Studio, Ollama).
    """

    def __init__(self, system_prompt: str = "", agent_name: str = "Agent"):
        from openai import OpenAI
        self.agent_name = agent_name
        self.system_prompt = system_prompt
        self.history: list[dict] = []
        
        base_url = os.getenv("LOCAL_LLM_URL", "http://127.0.0.1:1234/v1").rstrip("/")
        self.model = (
            os.getenv("LOCAL_MODEL_NAME")
            or os.getenv("LM_STUDIO_MODEL")
            or os.getenv("LOCAL_LLM_MODEL")
            or "liquid/lfm2.5-1.2b"
        )
        
        # Local LLMs usually don't need a real API key, but openai requires something
        self.client = OpenAI(base_url=base_url, api_key=os.getenv("LOCAL_LLM_API_KEY", "lm-studio"))

    def reset(self):
        """Clear conversation history (start fresh task)."""
        self.history = []

    def ask(self, prompt: str, tools: list = None) -> str:
        """
        Send a message and get a response.
        """
        try:
            messages = [{"role": "system", "content": self.system_prompt}]
            messages.extend(self.history)
            messages.append({"role": "user", "content": prompt})

            text = self._create_completion(messages)
            self.history.append({"role": "user", "content": prompt})
            self.history.append({"role": "assistant", "content": text})
            return text
        except Exception as e:
            return f"[{self.agent_name} ERROR]: {str(e)}"

    def _create_completion(self, messages: list[dict]) -> str:
        """Call the most compatible OpenAI-style endpoint available."""
        last_error = None

        # LM Studio and Ollama both expose chat completions; some client builds
        # differ slightly, so we try the standard API first and then a lighter
        # fallback if needed.
        for attempt in ("chat_completions", "responses"):
            try:
                if attempt == "chat_completions":
                    response = self.client.chat.completions.create(
                        model=self.model,
                        messages=messages,
                        temperature=TEMPERATURE,
                        max_tokens=MAX_TOKENS,
                    )
                    text = getattr(response.choices[0].message, "content", "") or ""
                    if text.strip():
                        return text
                    raise RuntimeError("Empty response from chat completions API")

                response = self.client.responses.create(
                    model=self.model,
                    input=messages,
                    temperature=TEMPERATURE,
                    max_output_tokens=MAX_TOKENS,
                )
                text = getattr(response, "output_text", "") or ""
                if text.strip():
                    return text
                raise RuntimeError("Empty response from responses API")
            except Exception as e:
                last_error = e

        raise last_error  # type: ignore[misc]

    def ask_json(self, prompt: str, schema_hint: str = "") -> dict:
        """
        Ask and parse response as JSON.
        """
        json_prompt = f"{prompt}\n\nIMPORTANT: Respond ONLY with a single valid JSON object. No markdown fences, no preamble.\n{f'Expected schema: {schema_hint}' if schema_hint else ''}"
        response = self.ask(json_prompt)
        
        clean = re.sub(r"```json|```", "", response).strip()
        try:
            return json.loads(clean)
        except json.JSONDecodeError:
            match = re.search(r"(\{.*\}|\[.*\])", clean, re.DOTALL)
            if match:
                try:
                    return json.loads(match.group(1))
                except Exception:
                    pass
            return {"raw_response": response, "parse_error": True}

    def ask_structured(self, prompt: str, output_keys: list[str]) -> dict:
        schema = "{" + ", ".join(f'"{k}": "..."' for k in output_keys) + "}"
        return self.ask_json(prompt, schema_hint=schema)


def make_client(system_prompt: str, agent_name: str, api_key: str = None):
    """Factory function for creating agent clients."""
    use_local = os.getenv("USE_LOCAL_LLM", "").lower() in ["true", "1", "yes"]
    if use_local:
        return LocalLLMClient(system_prompt=system_prompt, agent_name=agent_name)
    return GeminiClient(system_prompt=system_prompt, agent_name=agent_name, api_key=api_key)


def _wait_for_local_rate_limit() -> None:
    """Throttle Gemini calls in this process to fit better within free-tier RPM."""
    global _LAST_REQUEST_TS
    if MIN_SECONDS_BETWEEN_REQUESTS <= 0:
        return
    with _REQUEST_LOCK:
        now = time.monotonic()
        wait_for = MIN_SECONDS_BETWEEN_REQUESTS - (now - _LAST_REQUEST_TS)
        if wait_for > 0:
            time.sleep(wait_for)
        _LAST_REQUEST_TS = time.monotonic()


def _extract_rate_limit(response: str) -> dict:
    """Extract Gemini rate-limit metadata from error text."""
    text = response or ""
    if "429" not in text and "quota" not in text.lower() and "rate" not in text.lower():
        return {}
    retry_match = re.search(r"retry in\s+([0-9]+(?:\.[0-9]+)?)s", text, re.I)
    retry_after = int(float(retry_match.group(1))) + 1 if retry_match else None
    result = {"rate_limited": True}
    if retry_after:
        result["retry_after_seconds"] = retry_after
    return result

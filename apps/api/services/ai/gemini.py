"""
ReportForge AI - Gemini AI Provider
Implements AIProvider using Google Gemini API.
"""

import json
from typing import Optional, Type, TypeVar
import httpx
from pydantic import BaseModel
from apps.api.services.ai.base import AIProvider
from apps.api.core.config import settings
from apps.api.core.exceptions import AIProviderError
from apps.api.core.logging import get_logger

logger = get_logger("ai.gemini")

T = TypeVar("T", bound=BaseModel)


class GeminiProvider(AIProvider):
    """Google Gemini AI integration."""

    def __init__(self, api_key: Optional[str] = None, model: Optional[str] = None):
        self.api_key = api_key or settings.ai.gemini_api_key
        self.model = model or settings.ai.default_model

    def is_configured(self) -> bool:
        return bool(self.api_key and not self.api_key.startswith("placeholder"))

    def generate_text(
        self,
        prompt: str,
        system_instruction: Optional[str] = None,
        temperature: float = 0.3,
        **kwargs
    ) -> str:
        if not self.is_configured():
            raise AIProviderError(
                message="Gemini API Key is not configured. Provide GEMINI_API_KEY in environment variables.",
                details={"provider": "gemini"}
            )

        candidate_models = ["gemini-3.5-flash-lite", "gemini-3.1-flash-lite", "gemini-3.5-flash", "gemini-3.8-flash"]
        last_error = ""

        payload = {
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {"temperature": temperature}
        }
        if system_instruction:
            payload["systemInstruction"] = {"parts": [{"text": system_instruction}]}

        import re
        with httpx.Client(timeout=30.0) as client:
            for model_name in candidate_models:
                url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent?key={self.api_key}"
                try:
                    res = client.post(url, json=payload)
                    if res.status_code == 200:
                        data = res.json()
                        raw_text = data["candidates"][0]["content"]["parts"][0]["text"]
                        # Strip thought blocks or XML thinking tags
                        cleaned = re.sub(r"(?s)<thought>.*?</thought>", "", raw_text).strip()
                        return cleaned if cleaned else raw_text.strip()
                    else:
                        last_error = f"Model {model_name} HTTP {res.status_code}: {res.text}"
                except Exception as ex:
                    last_error = str(ex)

        logger.error(f"Gemini generation error across models: {last_error}")
        raise AIProviderError(f"Gemini generation failed: {last_error}")

    def generate_structured(
        self,
        prompt: str,
        response_schema: Type[T],
        system_instruction: Optional[str] = None,
        temperature: float = 0.2,
        **kwargs
    ) -> T:
        if not self.is_configured():
            raise AIProviderError(
                message="Gemini API Key is not configured. Provide GEMINI_API_KEY in environment variables.",
                details={"provider": "gemini"}
            )

        candidate_models = ["gemini-3.5-flash-lite", "gemini-3.1-flash-lite", "gemini-3.5-flash", "gemini-3.8-flash"]
        last_error = ""

        # Request JSON schema response
        schema_dict = response_schema.model_json_schema()
        schema_json_str = json.dumps(schema_dict)
        
        system_text = (system_instruction or "") + f"\n\nCRITICAL: Respond ONLY with valid JSON conforming to this schema:\n{schema_json_str}"

        payload = {
            "contents": [{"parts": [{"text": prompt}]}],
            "systemInstruction": {"parts": [{"text": system_text.strip()}]},
            "generationConfig": {
                "temperature": temperature,
                "responseMimeType": "application/json"
            }
        }

        import re
        with httpx.Client(timeout=30.0) as client:
            for model_name in candidate_models:
                url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent?key={self.api_key}"
                try:
                    res = client.post(url, json=payload)
                    if res.status_code == 200:
                        data = res.json()
                        raw_json = data["candidates"][0]["content"]["parts"][0]["text"]
                        clean_json = re.sub(r"^```json\s*", "", raw_json.strip())
                        clean_json = re.sub(r"\s*```$", "", clean_json)
                        parsed = json.loads(clean_json)
                        if isinstance(parsed, list) and len(parsed) > 0 and not issubclass(response_schema, list):
                            parsed = parsed[0]
                        return response_schema.model_validate(parsed)
                    else:
                        last_error = f"Model {model_name} HTTP {res.status_code}: {res.text}"
                except Exception as ex:
                    last_error = str(ex)

        logger.error(f"Gemini structured generation error across models: {last_error}")
        raise AIProviderError(f"Gemini structured generation failed: {last_error}")

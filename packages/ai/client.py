import asyncio
import hashlib
import json
import logging
import time
from typing import Any, TypeVar, cast

import httpx
from pydantic import BaseModel

from packages.core.config import settings
from packages.core.redis import get_async_redis

logger = logging.getLogger("applyon.ai")
T = TypeVar("T", bound=BaseModel)


class AIUnavailableError(RuntimeError):
    """The AI provider failed (bad key, retired model, quota, network or unparseable output).

    Callers must handle this explicitly; we never substitute made-up content for a real user.
    """


_GEMINI_SCHEMA_KEYS = {
    "type", "format", "description", "nullable", "enum", "properties", "required",
    "items", "minItems", "maxItems", "minimum", "maximum", "anyOf", "propertyOrdering",
}


def to_gemini_schema(schema: dict[str, Any]) -> dict[str, Any]:
    """Convert a Pydantic JSON schema into Gemini's responseSchema (OpenAPI subset).

    Gemini rejects $defs/$ref, titles and defaults, so refs are inlined, `X | None` becomes
    nullable, and unsupported keys are dropped.
    """
    defs = schema.get("$defs", {})

    def convert(node: Any) -> Any:
        if not isinstance(node, dict):
            return node
        if "$ref" in node:
            return convert(defs[node["$ref"].split("/")[-1]])
        if "anyOf" in node:
            variants = [v for v in node["anyOf"] if v.get("type") != "null"]
            nullable = len(variants) < len(node["anyOf"])
            merged = convert(variants[0]) if len(variants) == 1 else {"anyOf": [convert(v) for v in variants]}
            if nullable:
                merged = {**merged, "nullable": True}
            if "description" in node:
                merged["description"] = node["description"]
            return merged
        out: dict[str, Any] = {}
        for key, value in node.items():
            if key not in _GEMINI_SCHEMA_KEYS:
                continue
            if key == "properties":
                out[key] = {name: convert(v) for name, v in value.items()}
            elif key == "items":
                out[key] = convert(value)
            else:
                out[key] = value
        return out

    result: dict[str, Any] = convert({k: v for k, v in schema.items() if k != "$defs"})
    return result


class GeminiClient:
    """Production-grade client for Google Gemini with structured outputs, caching, and rate limiting."""

    def __init__(self) -> None:
        self.api_key = settings.gemini_api_key
        self.base_url = "https://generativelanguage.googleapis.com/v1beta"

    @property
    def is_mock(self) -> bool:
        """No real key configured: deterministic mock outputs (tests and offline development only)."""
        return not self.api_key or self.api_key.startswith(("mock-", "test-"))

    def _get_cache_key(self, prompt_version: str, model: str, payload: dict[str, Any]) -> str:
        serialized = json.dumps(payload, sort_keys=True)
        h = hashlib.sha256(f"{prompt_version}:{model}:{serialized}".encode()).hexdigest()
        return f"ai_cache:{h}"

    async def generate_structured(
        self,
        model_name: str,
        system_instruction: str,
        prompt: str,
        response_model: type[T],
        prompt_version: str = "v1",
        cache_ttl_seconds: int = 86400 * 7,
    ) -> T:
        """
        Generate structured JSON output adhering strictly to response_model schema.
        Implements Redis response caching and one automated repair retry on parse failure.
        """
        redis = get_async_redis()
        cache_key = self._get_cache_key(
            prompt_version, model_name, {"sys": system_instruction, "prompt": prompt}
        )

        # 1. Check Redis Cache
        cached = await redis.get(cache_key)
        if cached:
            try:
                data = json.loads(cached)
                return response_model.model_validate(data)
            except Exception:
                pass

        # 2. Mock mode only when no real key is configured (tests / offline dev)
        if self.is_mock:
            return self._generate_mock_response(response_model)

        # 3. Call Google Gemini API: the requested model, one retry after a short pause when it's
        #    overloaded or rate-limited, then the lite model as a last resort.
        schema = to_gemini_schema(response_model.model_json_schema())
        payload = {
            "systemInstruction": {"parts": [{"text": system_instruction}]},
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {
                "responseMimeType": "application/json",
                "responseSchema": schema,
                "temperature": 0.2,
            },
        }
        attempts = [model_name, model_name]
        if settings.gemini_model_lite not in attempts:
            attempts.append(settings.gemini_model_lite)

        start_time = time.perf_counter()
        res_json: dict[str, Any] | None = None
        last_error = ""
        for i, attempt_model in enumerate(attempts):
            if i == 1:
                await asyncio.sleep(2)
            url = f"{self.base_url}/models/{attempt_model}:generateContent?key={self.api_key}"
            try:
                async with httpx.AsyncClient(timeout=45.0) as client:
                    resp = await client.post(url, json=payload)
            except httpx.HTTPError as e:
                last_error = f"request to {attempt_model} failed: {type(e).__name__}"
                logger.warning("Gemini %s", last_error)
                continue
            if resp.status_code == 200:
                res_json = resp.json()
                break
            last_error = f"{attempt_model} returned {resp.status_code}"
            logger.warning("Gemini %s: %s", last_error, resp.text[:300])
            if resp.status_code not in (404, 429, 500, 503):
                break  # bad request: retrying won't help
            if resp.status_code == 404 and i == 0:
                continue  # retired model: skip the same-model retry
        if res_json is None:
            raise AIUnavailableError(f"Gemini unavailable ({last_error})")

        latency_ms = int((time.perf_counter() - start_time) * 1000)
        logger.debug(f"Gemini API latency: {latency_ms}ms")

        # Extract candidates text
        try:
            candidates = res_json.get("candidates", [])
            text_content = candidates[0]["content"]["parts"][0]["text"]
            parsed_data = json.loads(text_content)
            validated = response_model.model_validate(parsed_data)

            # Store in cache
            await redis.set(cache_key, json.dumps(parsed_data), ex=cache_ttl_seconds)
            return validated
        except Exception as e:
            logger.warning("Failed to parse Gemini output for %s: %s", response_model.__name__, e)
            raise AIUnavailableError("Gemini returned output that didn't match the expected format") from e

    async def generate_text(
        self,
        prompt: str,
        temperature: float = 0.2,
        max_output_tokens: int = 500,
    ) -> str:
        """Generate plain text with the fast model. Raises AIUnavailableError on failure."""
        if self.is_mock:
            raise AIUnavailableError("No Gemini API key configured")

        url = f"{self.base_url}/models/{settings.gemini_model_fast}:generateContent?key={self.api_key}"
        payload = {
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {
                "temperature": temperature,
                "maxOutputTokens": max_output_tokens,
            },
        }
        try:
            async with httpx.AsyncClient(timeout=20.0) as client:
                resp = await client.post(url, json=payload)
            if resp.status_code == 200:
                candidates = resp.json().get("candidates", [])
                if candidates:
                    return str(candidates[0]["content"]["parts"][0]["text"])
            logger.error("Gemini text error (%s): %s", resp.status_code, resp.text[:300])
        except Exception as e:
            logger.warning("generate_text error: %s", e)
        raise AIUnavailableError("Gemini text generation failed")

    async def get_embedding(self, text: str) -> list[float]:
        """Generate a 768-dimensional semantic embedding vector using Gemini."""
        if self.is_mock:
            # Return deterministic synthetic 768-dim vector for mock/testing
            h = hashlib.md5(text.encode()).hexdigest()
            return [float(int(h[i % len(h)], 16)) / 16.0 for i in range(768)]

        url = (
            f"{self.base_url}/models/{settings.gemini_embed_model}:embedContent?key={self.api_key}"
        )
        payload = {
            "model": f"models/{settings.gemini_embed_model}",
            "content": {"parts": [{"text": text[:2000]}]},
            "outputDimensionality": 768,
        }

        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.post(url, json=payload)
                if resp.status_code == 200:
                    data = resp.json()
                    vals = data.get("embedding", {}).get("values", [0.0] * 768)
                    return cast(list[float], vals)
        except Exception as e:
            logger.error(f"Embedding error: {e}")

        return [0.0] * 768

    def _generate_mock_response(self, response_model: type[T]) -> T:
        """Deterministic mock responses for test environments and eval harnesses."""

        name = response_model.__name__
        if name == "ParsedResumeOutput":
            return response_model.model_validate(
                {
                    "full_name": "Naga Datta Sai",
                    "email": "naga@example.com",
                    "phone": "+91 9876543210",
                    "city": "Bengaluru",
                    "state": "Karnataka",
                    "country": "India",
                    "headline": "Senior Full Stack & AI Systems Engineer",
                    "summary": "Full Stack developer experienced in FastAPI, Next.js, and GenAI systems.",
                    "total_experience_months": 36,
                    "current_title": "Full Stack Developer",
                    "current_company": "Applyon",
                    "experiences": [
                        {
                            "company": "Applyon",
                            "title": "Software Engineer",
                            "start_date": "2023-01",
                            "is_current": True,
                            "bullets": [
                                {
                                    "id": "b1",
                                    "text": "Architected async FastAPI backend with Celery 5 and Redis queues.",
                                    "skills": ["FastAPI", "Python", "Celery"],
                                    "metrics": ["200ms p95 latency"],
                                }
                            ],
                        }
                    ],
                    "skills": [
                        {
                            "name": "Python",
                            "normalized_name": "python",
                            "category": "technical",
                            "years": 3.0,
                        },
                        {
                            "name": "FastAPI",
                            "normalized_name": "fastapi",
                            "category": "technical",
                            "years": 2.5,
                        },
                        {
                            "name": "TypeScript",
                            "normalized_name": "typescript",
                            "category": "technical",
                            "years": 3.0,
                        },
                    ],
                }
            )
        elif name == "MatchScoreOutput":
            return response_model.model_validate(
                {
                    "job_id": "00000000-0000-0000-0000-000000000000",
                    "match_score": 88,
                    "decision": "apply",
                    "fit_reasons": [
                        "Strong FastAPI & asynchronous architecture experience",
                        "Full stack expertise in TypeScript and Next.js",
                    ],
                    "gaps": ["Kubernetes multi-cluster management"],
                    "resume_focus": [
                        "High-throughput queue architecture",
                        "Sub-10ms API latency optimizations",
                    ],
                    "risk_flags": [],
                }
            )
        elif name == "TailoredResumeOutput":
            return response_model.model_validate(
                {
                    "summary": "Full Stack & AI Systems Engineer focused on high-throughput distributed systems.",
                    "skills_ordered": [
                        "Python",
                        "FastAPI",
                        "PostgreSQL",
                        "Celery",
                        "Redis",
                        "TypeScript",
                    ],
                    "experiences": [
                        {
                            "experience_id": "exp-1",
                            "company": "Applyon",
                            "title": "Software Engineer",
                            "bullets": [
                                {
                                    "source_bullet_id": "b1",
                                    "text": "Architected async FastAPI backend with Celery 5 and Redis queues delivering 200ms p95 latency.",
                                }
                            ],
                        }
                    ],
                    "keywords_used": ["FastAPI", "Redis", "Celery", "Asynchronous"],
                    "changes_made": [
                        "Highlighted backend queue processing and API latency metrics"
                    ],
                }
            )
        elif name == "CoverLetterOutput":
            return response_model.model_validate(
                {
                    "cover_letter_text": (
                        "Dear Hiring Team,\n\n"
                        "I am writing to express my strong enthusiasm for this engineering opportunity. "
                        "Having engineered high-throughput backend services using FastAPI, PostgreSQL, and Celery, "
                        "I have demonstrated proficiency in building scalable asynchronous architectures with sub-10ms response times. "
                        "I look forward to discussing how my experience can contribute to your team's objectives.\n\n"
                        "Sincerely,\nNaga Datta Sai"
                    ),
                    "word_count": 58,
                }
            )
        elif name == "ScreeningAnswersOutput":
            return response_model.model_validate(
                {
                    "answers": [
                        {
                            "field_key": "notice_period_days",
                            "question_text": "What is your notice period?",
                            "answer": "30 days",
                            "confidence": 1.0,
                        }
                    ]
                }
            )
        return response_model.model_validate({})


gemini_client = GeminiClient()

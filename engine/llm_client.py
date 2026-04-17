"""LLM client abstraction.

This module ships with a deterministic STUB implementation that lets the
Stage 0-3 pipeline run end-to-end without an API key. The stub inspects the
*user prompt* to figure out which stage is asking and returns a plausibly-
shaped JSON payload. It is intentionally dumb — it does NOT perform real
ethical reasoning. Its only job is to let us wire up the full pipeline.

Switching to real providers:
    Set config.models.api_provider to "openrouter", "anthropic", or
    "openai_compatible" and the corresponding class below will be used.
    Real implementations are left as TODO placeholders and raise
    NotImplementedError — fill them in when a key is available.
"""

from __future__ import annotations

import abc
import asyncio
import hashlib
import json
import os
import re
from dataclasses import dataclass
from typing import Any, Dict, List, Optional


# ---------- Data types ----------

@dataclass
class LLMResponse:
    model: str
    content: str
    raw: Optional[Dict[str, Any]] = None

    def parse_json(self) -> Any:
        """Best-effort JSON extraction from the model response."""
        return extract_json(self.content)


def extract_json(text: str) -> Any:
    """Pull the first JSON object/array out of a text blob."""
    if not text:
        return {}
    # Strip ```json fences.
    fenced = re.search(r"```(?:json)?\s*(.*?)\s*```", text, re.DOTALL)
    if fenced:
        text = fenced.group(1)
    # Find the first balanced { ... } or [ ... ].
    for opener, closer in (("{", "}"), ("[", "]")):
        start = text.find(opener)
        if start == -1:
            continue
        depth = 0
        for i in range(start, len(text)):
            if text[i] == opener:
                depth += 1
            elif text[i] == closer:
                depth -= 1
                if depth == 0:
                    candidate = text[start : i + 1]
                    try:
                        return json.loads(candidate)
                    except Exception:
                        pass
                    break
    # Last resort: try the whole thing.
    try:
        return json.loads(text)
    except Exception:
        return {}


# ---------- Client interface ----------

class BaseLLMClient(abc.ABC):
    provider_name: str = "base"

    def __init__(self, temperature: float = 0.3, timeout: float = 120.0):
        self.temperature = temperature
        self.timeout = timeout

    @abc.abstractmethod
    async def query(
        self,
        model: str,
        system_prompt: str,
        user_prompt: str,
        *,
        temperature: Optional[float] = None,
    ) -> LLMResponse:
        raise NotImplementedError


# ---------- Stub client (default, works offline) ----------

class StubLLMClient(BaseLLMClient):
    """Deterministic fake client used for offline pipeline runs."""

    provider_name = "stub"

    async def query(
        self,
        model: str,
        system_prompt: str,
        user_prompt: str,
        *,
        temperature: Optional[float] = None,
    ) -> LLMResponse:
        # Tiny delay to let async gather behave naturally.
        await asyncio.sleep(0)

        payload = _stub_payload_for(model, system_prompt, user_prompt)
        content = json.dumps(payload, ensure_ascii=False, indent=2)
        return LLMResponse(model=model, content=content, raw={"stub": True})


def _hash_seed(*parts: str) -> int:
    h = hashlib.md5("|".join(parts).encode("utf-8")).hexdigest()
    return int(h[:8], 16)


def _stub_payload_for(model: str, system_prompt: str, user_prompt: str) -> Any:
    """Produce a stage-appropriate JSON payload based on prompt keywords.

    Detection order matters: later stages embed JSON from earlier stages in
    the prompt, so we check the most specific (stage 3) first and work
    backwards to avoid false matches.
    """
    u = user_prompt
    s = system_prompt or ""

    # --- Stage 3 chairman (check FIRST — embeds all earlier stage output) ---
    if "priority_actions" in u and "chairman_notes" in u and "domain_assessments" in u:
        return _stub_chairman(u)

    # --- Stage 2 context discussion ---
    if "cross_domain_risks" in u and "supplements_to_others" in u and "collaborative_recommendations" in u:
        topic_m = re.search(r'"context_topic":\s*"([^"]+)"', u)
        topic = topic_m.group(1) if topic_m else "未命名议题"
        return {
            "context_topic": topic,
            "my_domain": "stub-domain",
            "cross_domain_risks": [
                {
                    "risk_id": "CR1",
                    "description": f"stub: 围绕『{topic}』的交叉风险示例",
                    "severity": "medium",
                    "recommendation": "建立跨领域联合风险评估机制",
                }
            ],
            "supplements_to_others": [],
            "collaborative_recommendations": [
                "在伦理审查意见书中统一交叉议题的表述口径",
            ],
        }

    # --- Stage 1 domain summary ---
    if "divergences" in u and "合并后的核心关切" in u:
        return _stub_domain_summary(model)

    # --- Stage 1 cross-check ---
    if "missed_risks" in u and "severity_adjustments" in u:
        return {
            "missed_risks": [
                {
                    "risk_id": f"R_NEW_{_hash_seed(model, 'missed') % 9 + 1}",
                    "description": "stub: 对方可能忽略的隐私再识别风险",
                    "severity": "medium",
                    "regulatory_basis": "《个人信息保护法》第二十八条",
                    "recommendation": "补充去标识化与访问控制的具体措施",
                }
            ],
            "severity_adjustments": [],
            "legal_corrections": [],
            "additional_recommendations": [
                "建议在知情同意书中加入数据再识别风险的说明",
            ],
            "agreement_items": ["R1"],
        }

    # --- Stage 1 first-pass review ---
    if "risk_items" in u and "key_concerns_summary" in u:
        return _stub_first_pass(model, s)

    # --- Stage 0 router ---
    if "experts_selected" in u and "context_clusters" in u:
        # Extract expert IDs mentioned in the prompt as [id] markers.
        ids = re.findall(r"\[([a-z_]+)\]", u)
        ids = list(dict.fromkeys(ids))  # dedupe, preserve order
        chosen = ids[: max(3, min(len(ids), 5))]
        clusters = []
        if len(chosen) >= 2:
            clusters.append({
                "topic": "数据与受试者保护的交叉议题",
                "participants": chosen[:2],
                "reason": "stub: 默认为前两位专家生成一个示例交叉议题",
            })
        if len(chosen) >= 3:
            clusters.append({
                "topic": "合规与技术伦理的交叉议题",
                "participants": chosen[1:3] if len(chosen) >= 3 else chosen,
                "reason": "stub: 默认为第二、第三位专家生成一个示例交叉议题",
            })
        return {
            "experts_selected": [
                {"id": i, "name": i, "reason": "stub: 按关键词匹配入选"} for i in chosen
            ],
            "context_clusters": clusters,
            "experts_not_needed": [
                {"id": i, "name": i, "reason": "stub: 暂未命中本项目议题"}
                for i in ids[len(chosen):]
            ],
            "high_risk_flags": [],
            "risk_level": "standard",
        }

    # Fallback: generic text.
    return {"note": "stub_default", "model": model}


def _stub_first_pass(model: str, system_prompt: str) -> Dict[str, Any]:
    # Try to guess domain name from system_prompt (first "你是一位..." phrase).
    m = re.search(r"你是一位[资深]*的(.+?)[，。\n]", system_prompt)
    domain = m.group(1) if m else "某领域伦理审查员"
    seed = _hash_seed(model, domain)
    severities = ["low", "medium", "high"]
    return {
        "expert_domain": domain,
        "risk_items": [
            {
                "risk_id": "R1",
                "description": f"stub: {domain}关注的第一类风险点",
                "severity": severities[seed % 3],
                "regulatory_basis": "相关法规/准则（stub占位）",
                "recommendation": "补充具体风险控制措施与应急预案",
                "info_sufficient": True,
            },
            {
                "risk_id": "R2",
                "description": f"stub: {domain}关注的第二类风险点（信息不足）",
                "severity": "medium",
                "regulatory_basis": "相关法规/准则（stub占位）",
                "recommendation": "请研究者补充方法细节",
                "info_sufficient": False,
            },
        ],
        "missing_information": [
            "stub: 需要研究者补充的样本量计算依据",
        ],
        "overall_assessment": "conditional",
        "confidence": round(0.6 + (seed % 30) / 100.0, 2),
        "key_concerns_summary": (
            f"stub: {domain}的主要关切在于风险控制方案、知情同意与合规依据的"
            f"具体性，需要研究者补充上述信息后再复审。"
        ),
    }


def _stub_domain_summary(model: str) -> Dict[str, Any]:
    base = _stub_first_pass(model, system_prompt="你是一位资深的综合伦理审查员，")
    base["divergences"] = []
    return base


def _stub_chairman(user_prompt: str) -> Dict[str, Any]:
    # Pull project_name from the prompt body if possible.
    m = re.search(r'"project_name":\s*"([^"]+)"', user_prompt)
    project = m.group(1) if m else "未命名项目"
    return {
        "project_name": project,
        "review_date": "",
        "risk_level": "standard",
        "overall_conclusion": "conditional",
        "conclusion_rationale": (
            "stub: 多个领域均评估为 conditional，项目在补充信息并完成指定修改"
            "后可予以通过。"
        ),
        "domain_assessments": [],
        "cross_domain_findings": [],
        "unresolved_divergences": [],
        "priority_actions": [
            {
                "priority": "P0",
                "action": "补充数据管理方案的具体条款（加密、访问控制、保留期限）",
                "responsible_domain": "data_privacy",
                "deadline_suggestion": "两周内",
            },
            {
                "priority": "P1",
                "action": "补充知情同意书的可读性验证与弱势群体保护细节",
                "responsible_domain": "human_subjects",
                "deadline_suggestion": "一个月内",
            },
        ],
        "chairman_notes": (
            "stub: 本意见由离线stub生成，仅用于验证流水线端到端可执行。"
            "请配置真实LLM后再使用审查结果。"
        ),
    }


# ---------- Real-provider implementations ----------

class OpenRouterLLMClient(BaseLLMClient):
    provider_name = "openrouter"

    async def query(self, model, system_prompt, user_prompt, *, temperature=None):
        import httpx

        api_key = os.getenv("OPENROUTER_API_KEY")
        if not api_key:
            raise RuntimeError("OPENROUTER_API_KEY environment variable is required")

        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        }
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": user_prompt})

        payload = {
            "model": model,
            "messages": messages,
            "temperature": temperature if temperature is not None else self.temperature,
        }

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            resp = await client.post(
                "https://openrouter.ai/api/v1/chat/completions",
                headers=headers,
                json=payload,
            )
            resp.raise_for_status()
            data = resp.json()
            message = data["choices"][0]["message"]
            content = message.get("content", "")
            return LLMResponse(
                model=model,
                content=content,
                raw=data,
            )


class AnthropicLLMClient(BaseLLMClient):
    provider_name = "anthropic"

    async def query(self, model, system_prompt, user_prompt, *, temperature=None):
        try:
            from anthropic import AsyncAnthropic
        except ImportError as e:
            raise ImportError("anthropic package is required. Run: pip install anthropic") from e

        api_key = os.getenv("ANTHROPIC_API_KEY")
        if not api_key:
            raise RuntimeError("ANTHROPIC_API_KEY environment variable is required")

        client = AsyncAnthropic(api_key=api_key)
        resp = await client.messages.create(
            model=model,
            max_tokens=4096,
            temperature=temperature if temperature is not None else self.temperature,
            system=system_prompt or "",
            messages=[{"role": "user", "content": user_prompt}],
        )
        content = "".join(block.text for block in resp.content if hasattr(block, "text"))
        return LLMResponse(
            model=model,
            content=content,
            raw=resp.model_dump(),
        )


class OpenAICompatibleLLMClient(BaseLLMClient):
    provider_name = "openai_compatible"

    async def query(self, model, system_prompt, user_prompt, *, temperature=None):
        try:
            from openai import AsyncOpenAI
        except ImportError as e:
            raise ImportError("openai package is required. Run: pip install openai") from e

        api_key = os.getenv("OPENAI_API_KEY")
        base_url = os.getenv("OPENAI_BASE_URL")
        if not api_key:
            raise RuntimeError("OPENAI_API_KEY environment variable is required")

        client = AsyncOpenAI(api_key=api_key, base_url=base_url)
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": user_prompt})

        resp = await client.chat.completions.create(
            model=model,
            messages=messages,
            temperature=temperature if temperature is not None else self.temperature,
            timeout=self.timeout,
        )
        content = resp.choices[0].message.content or ""
        return LLMResponse(
            model=model,
            content=content,
            raw=resp.model_dump(),
        )


# ---------- Factory ----------

def make_llm_client(provider: str, *, temperature: float = 0.3, timeout: float = 120.0) -> BaseLLMClient:
    """Return a client instance matching `provider`.

    Honors env override `ETHICS_COUNCIL_LLM` which can force "stub".
    """
    if os.getenv("ETHICS_COUNCIL_LLM") == "stub":
        provider = "stub"
    provider = (provider or "stub").lower()
    if provider == "stub":
        return StubLLMClient(temperature=temperature, timeout=timeout)
    if provider == "openrouter":
        return OpenRouterLLMClient(temperature=temperature, timeout=timeout)
    if provider == "anthropic":
        return AnthropicLLMClient(temperature=temperature, timeout=timeout)
    if provider in ("openai", "openai_compatible"):
        return OpenAICompatibleLLMClient(temperature=temperature, timeout=timeout)
    raise ValueError(f"Unknown LLM provider: {provider}")

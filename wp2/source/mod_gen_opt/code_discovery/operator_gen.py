"""LLM-based operator generation for Large Neighborhood Search.

Asks an LLM to produce Python source code for a custom DestroyOperator and
RepairOperator.  The generated code is compiled at runtime and returned as
importable class objects that implement the LNS operator interfaces.
"""
from __future__ import annotations

import re
import textwrap
import types
from typing import Any

from large_neighborhood_search.components import DestroyOperator, Initializer, RepairOperator
from large_neighborhood_search.models import LNSContext
from llm.llmclient import LLMClient


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def generate_operators_with_llm(
    problem_dsl_text: str,
    lns_result_summary: str,
    llm_client: LLMClient,
    prior_operator_source: str = "",
    prior_assistant_code: str = "",  # Previous LLM response (assistant role in conversation)
    prior_feedback: str = "",          # Execution error or score feedback
    max_tokens: int = 2048,
) -> tuple[DestroyOperator, RepairOperator, str]:
    """Returns ``(destroy_op, repair_op, source_code)``.

    The *source_code* is the extracted Python text and can be passed back in
    *prior_operator_source* on the next round so the LLM can improve its work.
    *prior_assistant_code* is sent as the assistant's prior message for proper conversation context.
    *prior_feedback* contains execution errors or score feedback to guide improvement.
    """
    prompt = _build_prompt(problem_dsl_text, lns_result_summary, prior_operator_source)

    # Build proper conversation: system → [user → assistant → user (with feedback) → ...]
    messages = [
        {
            "role": "system",
            "content": (
                "Generate ONLY valid Python code. No prose, no markdown, no reasoning. "
                "Output exactly one GeneratedDestroyOperator and one GeneratedRepairOperator."
            ),
        },
    ]

    # Build conversation history: if the LLM produced code last round,
    # include it as assistant message + feedback as user follow-up.
    if prior_assistant_code.strip():
        messages.append({"role": "user", "content": prompt})
        messages.append({"role": "assistant", "content": prior_assistant_code})
        if prior_feedback.strip():
            # Append feedback to the prompt for the follow-up message
            follow_up = prompt + f"\n\nFEEDBACK FROM LAST ATTEMPT:\n{prior_feedback}\nPlease fix the issues and generate improved code."
            messages.append({"role": "user", "content": follow_up})
        else:
            messages.append({"role": "user", "content": prompt})
    else:
        messages.append({"role": "user", "content": prompt})

    response = llm_client.chat(messages, max_tokens=max_tokens, temperature=0.3)
    raw_code = _extract_content(response)
    destroy_cls, repair_cls = _compile_operators(raw_code)
    return destroy_cls(), repair_cls(), raw_code


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

_OPERATOR_TEMPLATE = textwrap.dedent("""
    PROBLEM DSL:
    {dsl}

    LNS RESULTS:
    {summary}
    {prior_source}

    Generate a single destroy-repair operator pair for large neighborhood search optimization algorithm. Output ONLY Python code.

    IMPORTANT: Access context data via context.extra["key"] and context.constants["KEY"].

    class GeneratedDestroyOperator(DestroyOperator):
        def destroy(self, assignment: dict, context: LNSContext) -> dict:
            rng = context.extra["rng"]
            decision_keys = context.extra["decision_keys"]
            domains = context.extra["decision_domains"]
            # Select a subset of keys and set to None in assignment
            # return assignment

    class GeneratedRepairOperator(RepairOperator):
        def repair(self, partial: dict, context: LNSContext) -> dict:
            rng = context.extra["rng"]
            domains = context.extra["decision_domains"]
            # Fill None values: rng.randint(domains[key][0], domains[key][1])
            # return partial

    NO explanations. CODE ONLY.
""")



def _build_prompt(dsl_text: str, summary: str, prior_source: str = "") -> str:
    prior_block = (
        "\nPREVIOUS OPERATOR ATTEMPT (study what worked / failed and improve upon it):\n" + prior_source
        if prior_source.strip() else ""
    )

    # Extract constant names from DSL (uppercase identifiers before type annotations)
    constant_names = [
        m.group(1) for m in re.finditer(r'^([A-Z][A-Z0-9_]*)\s*[:=]', dsl_text, re.MULTILINE)
    ]

    constants_hint = ""
    if constant_names:
        constants_hint = (
            f"\n\nAVAILABLE CONSTANTS (use exact case via context.constants[\"KEY\"]):\n"
            f"  {', '.join(sorted(set(constant_names)))}"
        )

    template = _OPERATOR_TEMPLATE + constants_hint
    return template.format(
        dsl=dsl_text.strip(),
        summary=summary.strip(),
        prior_source=prior_block,
    )


def _extract_content(response: dict[str, Any]) -> str:
    """Extract generated operator code from chat response."""
    return _extract_response(response, _is_valid_operator_code_block)


def _extract_initializer_content(response: dict[str, Any]) -> str:
    """Extract generated initializer code from chat response."""
    return _extract_response(response, _is_valid_initializer_code_block)


def _extract_response(response: dict[str, Any], is_valid_fn: callable) -> str:
    """Internal: extract + validate text from LLM response."""
    try:
        message = response["choices"][0]["message"]

        candidates = _collect_text_candidates(message)
        for candidate in candidates:
            normalized = _normalize_candidate_code(candidate)
            if normalized and is_valid_fn(normalized):
                return normalized

        content_preview = (message.get("content") or "")[:300]
        raise ValueError(
            "Could not find valid class definitions in LLM response. "
            f"Content preview: {content_preview!r}"
        )

    except (KeyError, IndexError, TypeError, ValueError) as exc:
        raise RuntimeError(
            f"Failed to extract content from LLM response.\n"
            f"Error: {exc}"
        ) from exc


def _is_valid_operator_code_block(text: str) -> bool:
    """Check if text looks like executable operator code, not prose."""
    has_destroy_inheritance = re.search(r"class\s+\w+\s*\(\s*DestroyOperator\s*\)", text) is not None
    has_repair_inheritance = re.search(r"class\s+\w+\s*\(\s*RepairOperator\s*\)", text) is not None
    has_destroy_method = "def destroy(self" in text
    has_repair_method = "def repair(self" in text
    return has_destroy_inheritance and has_repair_inheritance and has_destroy_method and has_repair_method


def _is_valid_initializer_code_block(text: str) -> bool:
    """Check if text looks like valid initializer code."""
    has_init_inheritance = re.search(r"class\s+\w+\s*\(\s*Initializer\s*\)", text) is not None
    has_init_method = "def initialize(self" in text
    return has_init_inheritance and has_init_method


def _compile_operators(source_code: str) -> tuple[type[DestroyOperator], type[RepairOperator]]:
    """Compile *source_code* in a fresh module namespace and return the two operator classes."""
    if not isinstance(source_code, str):
        raise TypeError(
            f"source_code must be a string, got {type(source_code).__name__}: {source_code!r}"
        )
    
    # Extract only the class definitions, skipping any preamble or explanations
    code = _extract_class_definitions(source_code)
    
    namespace: dict[str, Any] = {
        "DestroyOperator": DestroyOperator,
        "RepairOperator": RepairOperator,
        "LNSContext": LNSContext,
        # Standard library modules commonly needed by generated operators.
        "random": __import__("random"),
        "math": __import__("math"),
    }
    # Allow standard library imports inside the generated code.
    module = types.ModuleType("_generated_operators")
    module.__dict__.update(namespace)

    try:
        exec(compile(code, "<llm_generated>", "exec"), module.__dict__)  # noqa: S102
    except SyntaxError as exc:
        # Provide detailed error context
        raise RuntimeError(
            f"LLM generated code has syntax errors: {exc}\n"
            f"Error at line {exc.lineno}: {exc.text}\n"
            f"First 500 chars of extracted code:\n{code[:500]}"
        ) from exc
    except Exception as exc:
        raise RuntimeError(
            f"Failed to compile generated operators: {type(exc).__name__}: {exc}\n"
            f"Code:\n{code}"
        ) from exc

    destroy_cls = module.__dict__.get("GeneratedDestroyOperator")
    repair_cls = module.__dict__.get("GeneratedRepairOperator")

    if destroy_cls is None or repair_cls is None:
        discovered_destroy, discovered_repair = _discover_operator_classes(module.__dict__)
        destroy_cls = destroy_cls or discovered_destroy
        repair_cls = repair_cls or discovered_repair

    if destroy_cls is None or repair_cls is None:
        raise RuntimeError(
            "LLM response did not define both 'GeneratedDestroyOperator' and "
            f"'GeneratedRepairOperator'.\n\nSource:\n{code}"
        )

    if not (isinstance(destroy_cls, type) and issubclass(destroy_cls, DestroyOperator)):
        raise RuntimeError("GeneratedDestroyOperator must inherit from DestroyOperator.")
    if not (isinstance(repair_cls, type) and issubclass(repair_cls, RepairOperator)):
        raise RuntimeError("GeneratedRepairOperator must inherit from RepairOperator.")

    return destroy_cls, repair_cls


def _extract_class_definitions(text: str) -> str:
    """Extract only the class definitions from text, skipping preamble."""
    class_starts = [m.start() for m in re.finditer(r"^\s*class\s+", text, flags=re.MULTILINE)]
    if not class_starts:
        return text.strip()

    destroy_match = re.search(r"class\s+\w+\s*\(\s*DestroyOperator\s*\)", text)
    if destroy_match is not None:
        destroy_idx = destroy_match.start()
    else:
        destroy_idx = class_starts[0]

    return text[destroy_idx:].rstrip()


def _collect_text_candidates(message: dict[str, Any]) -> list[str]:
    candidates: list[str] = []

    # Prefer content; fall back to reasoning (some models put output there when content is null).
    candidates.extend(_value_to_strings(message.get("content")))
    if not candidates:
        candidates.extend(_value_to_strings(message.get("reasoning")))
    return [c for c in candidates if c.strip()]


def _value_to_strings(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, str):
        return [value]
    if isinstance(value, list):
        out: list[str] = []
        for item in value:
            out.extend(_value_to_strings(item))
        return out
    if isinstance(value, dict):
        out: list[str] = []
        for key in ("text", "content", "reasoning", "value"):
            if key in value:
                out.extend(_value_to_strings(value[key]))
        return out
    return []


def _normalize_candidate_code(text: str) -> str:
    text = text.strip()
    if not text:
        return ""

    fenced_matches = re.findall(r"```(?:python)?\s*(.*?)```", text, flags=re.DOTALL | re.IGNORECASE)
    if fenced_matches:
        text = "\n\n".join(chunk.strip() for chunk in fenced_matches if chunk.strip())

    text = text.replace("\r\n", "\n").strip()
    return text


def _discover_operator_classes(namespace: dict[str, Any]) -> tuple[type[DestroyOperator] | None, type[RepairOperator] | None]:
    destroy_cls: type[DestroyOperator] | None = None
    repair_cls: type[RepairOperator] | None = None

    for obj in namespace.values():
        if not isinstance(obj, type):
            continue
        if destroy_cls is None and issubclass(obj, DestroyOperator) and obj is not DestroyOperator:
            destroy_cls = obj
        if repair_cls is None and issubclass(obj, RepairOperator) and obj is not RepairOperator:
            repair_cls = obj
        if destroy_cls is not None and repair_cls is not None:
            break

    return destroy_cls, repair_cls


# ---------------------------------------------------------------------------
# Initializer generation
# ---------------------------------------------------------------------------

_INITIALIZER_TEMPLATE = textwrap.dedent("""
    PROBLEM DSL:
    {dsl}

    PRIOR ATTEMPTS:
    {history}

    Generate 2-3 Initializer subclasses. Output ONLY Python code.

    IMPORTANT: Access context via context.extra["key"] and context.constants["KEY"].

    class GeneratedInitializerA(Initializer):
        def initialize(self, context: LNSContext) -> dict[str, object]:
            rng = context.extra["rng"]
            decision_keys = context.extra["decision_keys"]
            domains = context.extra["decision_domains"]
            result: dict[str, object] = {{}}
            for key in decision_keys:
                lo, hi = domains[key]
                result[key] = rng.randint(lo, hi)
            return result

    Generate 2 more with different strategies (all must return dict for ALL decision_keys).
    Use context.constants["KEY_NAME"] to read problem data (read DSL for key names).
    NO explanations. CODE ONLY.
""")


def generate_initializers_with_llm(
    problem_dsl_text: str,
    llm_client: LLMClient,
    history: str = "First attempt.",
    max_tokens: int = 2048,
) -> list[tuple[Initializer, str]]:
    """Ask the LLM to generate 2-3 construction heuristics.

    Returns a list of ``(initializer_instance, source_code)`` pairs.
    Raises ``RuntimeError`` if the LLM response cannot be parsed or compiled.
    """
    prompt = _INITIALIZER_TEMPLATE.format(
        dsl=problem_dsl_text.strip(),
        history=history.strip(),
    )
    messages = [
        {
            "role": "system",
            "content": (
                "Generate ONLY valid Python code. No prose, no markdown, no reasoning. "
                "Output Initializer subclasses."
            ),
        },
        {"role": "user", "content": prompt},
    ]

    response = llm_client.chat(messages, max_tokens=max_tokens, temperature=0.4)
    raw_code = _extract_initializer_content(response)
    return _compile_initializers(raw_code)


def _compile_initializers(source_code: str) -> list[tuple[Initializer, str]]:
    """Compile *source_code* and return (instance, source) for each Initializer subclass."""
    code = _extract_initializer_class_definitions(source_code)
    namespace: dict[str, Any] = {
        "Initializer": Initializer,
        "LNSContext": LNSContext,
        # Standard library modules commonly needed by generated initializers.
        "random": __import__("random"),
        "math": __import__("math"),
    }
    module = types.ModuleType("_generated_initializers")
    module.__dict__.update(namespace)

    try:
        exec(compile(code, "<llm_generated_init>", "exec"), module.__dict__)  # noqa: S102
    except SyntaxError as exc:
        raise RuntimeError(f"Syntax error in generated initializer: {exc}") from exc
    except Exception as exc:
        raise RuntimeError(f"Compile error in generated initializer: {exc}") from exc

    results: list[tuple[Initializer, str]] = []
    for obj in module.__dict__.values():
        if (
            isinstance(obj, type)
            and issubclass(obj, Initializer)
            and obj is not Initializer
        ):
            try:
                results.append((obj(), code))
            except Exception as exc:
                raise RuntimeError(f"Failed to instantiate {obj.__name__}: {exc}") from exc

    if not results:
        raise RuntimeError("Could not find valid class definitions in LLM response.")
    return results


def _extract_initializer_class_definitions(text: str) -> str:
    """Extract class definitions from text, skipping any prose preamble."""
    text = _normalize_candidate_code(text)
    init_match = re.search(r"class\s+\w+\s*\(\s*Initializer\s*\)", text)
    if init_match is not None:
        return text[init_match.start():].rstrip()
    class_starts = [m.start() for m in re.finditer(r"^\s*class\s+", text, flags=re.MULTILINE)]
    if class_starts:
        return text[class_starts[0]:].rstrip()
    return text.strip()


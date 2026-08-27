"""Compile structured voice-design attributes into a stable instruction."""

from __future__ import annotations


KNOWN_GENDERS = {
    "female": "female",
    "male": "male",
    "neutral": "gender-neutral",
}

KNOWN_AGES = {
    "child": "child",
    "teenager": "teenager",
    "young-adult": "young adult",
    "adult": "adult",
    "middle-aged": "middle-aged",
    "senior": "senior",
}

KNOWN_PITCHES = {
    "very-low": "very low pitch",
    "low": "low pitch",
    "medium-low": "medium-low pitch",
    "medium": "medium pitch",
    "medium-high": "medium-high pitch",
    "high": "high pitch",
    "very-high": "very high pitch",
}


def _normalize(value: str | None, mapping: dict[str, str]) -> str | None:
    if not value:
        return None
    normalized = value.strip().lower()
    return mapping.get(normalized, normalized)


def compile_instruction(
    *,
    prompt: str | None = None,
    gender: str | None = None,
    age: str | None = None,
    accent: str | None = None,
    pitch: str | None = None,
    tone: str | None = None,
    style: str | None = None,
    emotion: str | None = None,
    language: str | None = None,
) -> str:
    """Build a stable, backend-authoritative instruction from design inputs.

    The freeform *prompt* is preserved as the primary source of truth.
    Structured attributes are appended as a consistent, predictable suffix so
    the compiled result remains reproducible and easy to diff.
    """
    clauses: list[str] = []

    if prompt and prompt.strip():
        clauses.append(prompt.strip())

    structured: list[str] = []
    gender_norm = _normalize(gender, KNOWN_GENDERS)
    age_norm = _normalize(age, KNOWN_AGES)
    pitch_norm = _normalize(pitch, KNOWN_PITCHES)

    identity_parts: list[str] = []
    if age_norm:
        identity_parts.append(age_norm)
    if gender_norm:
        identity_parts.append(gender_norm)
    if language:
        identity_parts.append(language.lower())
    if accent:
        identity_parts.append(accent.lower())
    if identity_parts:
        structured.append(f"{' '.join(identity_parts)} speaker")

    qualities: list[str] = []
    if pitch_norm:
        qualities.append(pitch_norm)
    if tone:
        qualities.append(f"{tone.lower()} tone")
    if style:
        qualities.append(f"{style.lower()} delivery")
    if emotion:
        qualities.append(f"{emotion.lower()} emotional register")
    if qualities:
        structured.append(", ".join(qualities))

    if structured:
        suffix = "; ".join(structured)
        if clauses:
            # Append structured details to the freeform prompt.
            clauses[-1] = f"{clauses[-1]}. {suffix}."
        else:
            clauses.append(suffix.capitalize() + ".")

    instruction = " ".join(clauses).strip()
    return instruction if instruction else "Natural, clear narrator voice."

"""
Rule Guard (`core/rule_guard.py`)

Enforces business governance rules:
1. Max active rule cap (max 20 rules).
2. Semantic duplicate check using SentenceTransformer cosine similarity.
"""

import logging
import math
import re
from typing import List, Optional, Tuple, Dict
from backend.core.schemas import Rule, GuardResult

logger = logging.getLogger(__name__)

# Try importing SentenceTransformer lazily
_model_instance = None
_model_failed = False


def _get_sentence_transformer():
    global _model_instance, _model_failed
    if _model_instance is None and not _model_failed:
        try:
            from sentence_transformers import SentenceTransformer
            # Load lightweight all-MiniLM-L6-v2 model (~80MB)
            logger.info("Loading sentence-transformers 'all-MiniLM-L6-v2' model for Rule Guard...")
            _model_instance = SentenceTransformer('all-MiniLM-L6-v2')
        except Exception as e:
            logger.warning(f"SentenceTransformer not available or failed to load ({e}). Using token Jaccard fallback.")
            _model_failed = True
    return _model_instance


def _cosine_similarity(vec1: List[float], vec2: List[float]) -> float:
    """Calculates cosine similarity between two vector embeddings."""
    dot_product = sum(a * b for a, b in zip(vec1, vec2))
    norm_a = math.sqrt(sum(a * a for a in vec1))
    norm_b = math.sqrt(sum(b * b for b in vec2))
    if norm_a == 0.0 or norm_b == 0.0:
        return 0.0
    return dot_product / (norm_a * norm_b)


def _token_jaccard_similarity(text1: str, text2: str) -> float:
    """Fallback similarity calculation if SentenceTransformer is not installed/loaded."""
    tokens1 = set(re.findall(r'\w+', text1.lower()))
    tokens2 = set(re.findall(r'\w+', text2.lower()))
    if not tokens1 or not tokens2:
        return 0.0
    intersection = tokens1.intersection(tokens2)
    union = tokens1.union(tokens2)
    return len(intersection) / len(union)


def canonicalize_rule(rule: Rule) -> str:
    """Extract canonical string representation of rule for embedding comparison."""
    clean_code = re.sub(r'\s+', ' ', rule.code).strip()
    return f"{rule.name} {rule.description} {clean_code} {rule.created_by_command}"


class RuleGuard:
    def __init__(self, max_rules_cap: int = 20, similarity_threshold: float = 0.85):
        self.max_rules_cap: int = max_rules_cap
        self.similarity_threshold: float = similarity_threshold

    def evaluate_rule(self, proposed_rule: Rule, active_rules: List[Rule]) -> GuardResult:
        """
        Evaluates proposed rule against max cap and active rules for duplicate logic.
        """
        # 1. Capacity check
        if len(active_rules) >= self.max_rules_cap:
            return GuardResult(
                passed=False,
                reason=f"Rule capacity cap reached ({len(active_rules)}/{self.max_rules_cap} active rules). Deactivate or revert an existing rule first."
            )

        if not active_rules:
            return GuardResult(passed=True)

        # 2. Semantic Duplicate check
        proposed_canonical = canonicalize_rule(proposed_rule)
        active_canonicals = [canonicalize_rule(r) for r in active_rules]

        model = _get_sentence_transformer()

        highest_sim: float = 0.0
        duplicate_rule_id: Optional[str] = None

        if model is not None:
            try:
                embeddings = model.encode([proposed_canonical] + active_canonicals, convert_to_numpy=True)
                proposed_vec = embeddings[0].tolist()
                for i, existing_rule in enumerate(active_rules):
                    existing_vec = embeddings[i + 1].tolist()
                    sim = _cosine_similarity(proposed_vec, existing_vec)
                    if sim > highest_sim:
                        highest_sim = sim
                        duplicate_rule_id = existing_rule.id
            except Exception as e:
                logger.error(f"Error computing sentence embeddings: {e}")
                model = None

        # Fallback if sentence-transformers not available or failed
        if model is None:
            for existing_rule in active_rules:
                existing_canonical = canonicalize_rule(existing_rule)
                sim = _token_jaccard_similarity(proposed_canonical, existing_canonical)
                if sim > highest_sim:
                    highest_sim = sim
                    duplicate_rule_id = existing_rule.id

        if highest_sim >= self.similarity_threshold:
            return GuardResult(
                passed=False,
                reason=f"Duplicate rule detected (similarity {highest_sim:.2f} >= threshold {self.similarity_threshold}) with existing rule '{duplicate_rule_id}'.",
                similarity_score=round(highest_sim, 4),
                duplicate_rule_id=duplicate_rule_id
            )

        return GuardResult(
            passed=True,
            similarity_score=round(highest_sim, 4)
        )

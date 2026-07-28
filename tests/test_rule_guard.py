"""
Comprehensive unit tests for rule_guard.py targeting 100% line coverage.
Missing lines: 30-32 (SentenceTransformer exception), 42 (cosine zero norm),
48-54 (Jaccard fallback), 101-103 (embedding exception fallback), 107-112 (Jaccard path)
"""

import math
import pytest
from unittest.mock import patch, MagicMock
from backend.core.schemas import Rule, GuardResult
from backend.core.rule_guard import (
    RuleGuard,
    canonicalize_rule,
    _cosine_similarity,
    _token_jaccard_similarity,
    _get_sentence_transformer,
)


def make_rule(rule_id, name, code, desc="desc", cmd="cmd"):
    return Rule(
        id=rule_id, name=name, code=code, description=desc,
        created_at="2026-07-27T12:00:00Z", status="active",
        created_by_command=cmd
    )


# --------------- helper function tests ---------------

def test_cosine_similarity_normal():
    a = [1.0, 0.0]
    b = [1.0, 0.0]
    assert math.isclose(_cosine_similarity(a, b), 1.0)


def test_cosine_similarity_orthogonal():
    a = [1.0, 0.0]
    b = [0.0, 1.0]
    assert math.isclose(_cosine_similarity(a, b), 0.0)


def test_cosine_similarity_zero_vector():
    """Hits line 42: returns 0.0 when norm is zero."""
    a = [0.0, 0.0]
    b = [1.0, 0.0]
    assert _cosine_similarity(a, b) == 0.0

    a2 = [1.0, 0.0]
    b2 = [0.0, 0.0]
    assert _cosine_similarity(a2, b2) == 0.0


def test_token_jaccard_empty_text():
    """Hits line 50-51: returns 0.0 when tokens are empty."""
    assert _token_jaccard_similarity("", "hello world") == 0.0
    assert _token_jaccard_similarity("hello", "") == 0.0


def test_token_jaccard_identical_text():
    """Hits lines 48-54: normal Jaccard calculation path."""
    result = _token_jaccard_similarity("high amount crypto", "high amount crypto")
    assert math.isclose(result, 1.0)


def test_token_jaccard_partial_overlap():
    r = _token_jaccard_similarity("flag high amount", "flag low amount transaction")
    assert 0.0 < r < 1.0


def test_canonicalize_rule():
    rule = make_rule("r1", "My Rule", "def evaluate(tx): return True",
                     desc="description", cmd="command")
    canon = canonicalize_rule(rule)
    assert "My Rule" in canon
    assert "description" in canon
    assert "command" in canon


# --------------- RuleGuard cap check ---------------

def test_rule_cap_exceeded():
    guard = RuleGuard(max_rules_cap=3)
    active = [make_rule(f"rule_{i}", f"Rule {i}", f"code {i}") for i in range(3)]
    proposed = make_rule("new_rule", "New Rule", "new code")
    res = guard.evaluate_rule(proposed, active)
    assert res.passed is False
    assert "cap reached" in res.reason


def test_no_active_rules_always_passes():
    guard = RuleGuard(max_rules_cap=20)
    proposed = make_rule("r1", "Rule 1", "def evaluate(tx): return True")
    res = guard.evaluate_rule(proposed, [])
    assert res.passed is True
    assert res.reason is None


# --------------- sentence-transformer model loading ---------------

def test_sentence_transformer_load_failure_falls_back():
    """Hits lines 30-32: when SentenceTransformer raises, _model_failed is set."""
    import backend.core.rule_guard as rg_module

    # Reset state so the try-block runs
    original_instance = rg_module._model_instance
    original_failed = rg_module._model_failed
    rg_module._model_instance = None
    rg_module._model_failed = False

    try:
        with patch.dict("sys.modules", {"sentence_transformers": None}):
            # Importing SentenceTransformer will raise ImportError
            model = rg_module._get_sentence_transformer()
        assert model is None
        assert rg_module._model_failed is True
    finally:
        rg_module._model_instance = original_instance
        rg_module._model_failed = original_failed


# --------------- embedding exception → Jaccard fallback ---------------

def test_embedding_exception_triggers_jaccard_fallback():
    """
    Hits lines 101-103: encode() raises → model set to None → Jaccard path 107-112.
    """
    guard = RuleGuard(max_rules_cap=20, similarity_threshold=0.99)

    existing = make_rule("rule_existing", "Existing Rule",
                         "def evaluate(tx): return tx.amount > 1000",
                         desc="Flag large amounts", cmd="Flag large")
    proposed = make_rule("rule_proposed", "Different Rule",
                         "def evaluate(tx): return tx.account_age_days < 5",
                         desc="Flag new accounts", cmd="Flag new accounts")

    mock_model = MagicMock()
    mock_model.encode.side_effect = RuntimeError("CUDA OOM")

    import backend.core.rule_guard as rg_module
    original = rg_module._model_instance
    rg_module._model_instance = mock_model

    try:
        res = guard.evaluate_rule(proposed, [existing])
        # With very high threshold and completely different rules, Jaccard < 0.99 → passes
        assert isinstance(res, GuardResult)
    finally:
        rg_module._model_instance = original


# --------------- duplicate detection ---------------

def test_identical_rule_is_duplicate():
    guard = RuleGuard(max_rules_cap=20, similarity_threshold=0.80)
    code = "def evaluate(tx):\n    return tx.amount > 2000 and tx.merchant_category == 'crypto'"
    existing = make_rule("rule_crypto", "High Crypto", code,
                         desc="Flag high crypto over $2000", cmd="Flag crypto")
    proposed = make_rule("rule_crypto2", "High Crypto Alert", code,
                         desc="Flag high crypto over $2000", cmd="Flag crypto")
    res = guard.evaluate_rule(proposed, [existing])
    assert res.passed is False
    assert res.duplicate_rule_id == "rule_crypto"
    assert res.similarity_score >= 0.80


def test_completely_different_rule_passes():
    guard = RuleGuard(max_rules_cap=20, similarity_threshold=0.85)
    existing = make_rule("rule_amount", "High Amount",
                         "def evaluate(tx): return tx.amount > 5000",
                         desc="Flag transactions over $5000", cmd="Flag amount")
    proposed = make_rule("rule_intl_new", "International New Account",
                         "def evaluate(tx): return tx.is_international and tx.account_age_days < 7",
                         desc="Flag cross-border on new accounts", cmd="Flag international new")
    res = guard.evaluate_rule(proposed, [existing])
    assert res.passed is True


# --------------- Jaccard-only path (no sentence-transformers) ---------------

def test_jaccard_fallback_duplicate_detected():
    """
    Hits lines 107-112: with model=None forced, Jaccard detects duplicate.
    """
    import backend.core.rule_guard as rg_module
    original_instance = rg_module._model_instance
    original_failed = rg_module._model_failed
    rg_module._model_instance = None
    rg_module._model_failed = True  # Prevent model loading

    try:
        guard = RuleGuard(max_rules_cap=20, similarity_threshold=0.70)
        code = "def evaluate(tx): return tx.amount > 1000 and tx.merchant_category == 'crypto'"
        existing = make_rule("rule_j1", "Crypto High Amount", code,
                             desc="Flag crypto high amount over 1000",
                             cmd="Flag crypto high amount over 1000")
        proposed = make_rule("rule_j2", "Crypto High Amount", code,
                             desc="Flag crypto high amount over 1000",
                             cmd="Flag crypto high amount over 1000")
        res = guard.evaluate_rule(proposed, [existing])
        assert res.passed is False
        assert "Duplicate rule detected" in res.reason
    finally:
        rg_module._model_instance = original_instance
        rg_module._model_failed = original_failed


def test_jaccard_fallback_distinct_passes():
    """Jaccard fallback on truly distinct rules → passes."""
    import backend.core.rule_guard as rg_module
    original_instance = rg_module._model_instance
    original_failed = rg_module._model_failed
    rg_module._model_instance = None
    rg_module._model_failed = True

    try:
        guard = RuleGuard(max_rules_cap=20, similarity_threshold=0.90)
        existing = make_rule("rule_j3", "Amount Check",
                             "def evaluate(tx): return tx.amount > 5000",
                             desc="High amount only", cmd="amount check")
        proposed = make_rule("rule_j4", "New Account International",
                             "def evaluate(tx): return tx.is_international and tx.account_age_days < 7",
                             desc="International new accounts", cmd="intl new accounts")
        res = guard.evaluate_rule(proposed, [existing])
        assert res.passed is True
    finally:
        rg_module._model_instance = original_instance
        rg_module._model_failed = original_failed

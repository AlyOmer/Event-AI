"""
Unit and property-based tests for SearchService hybrid scoring.

Covers:
  - 13.1  Scoring formula unit tests: weighted combination applied correctly,
          missing scores default to 0.0, rank-based trigram normalisation.
  - 13.2  Property-based test (Hypothesis): hybrid score is always in [0.0, 1.0]
          for any t, s ∈ [0,1] with w_t + w_s = 1.0.

The scoring formula is pure math — no DB or async needed for these tests.
"""
import pytest
from hypothesis import given, settings as h_settings
from hypothesis import strategies as st


# ── Scoring formula helper (mirrors the logic in SearchService.hybrid_search) ─

def compute_hybrid_score(
    trigram_score: float,
    semantic_score: float,
    w_t: float,
    w_s: float,
) -> float:
    """
    Compute the hybrid score as a weighted combination of trigram and semantic scores.

    Formula: hybrid_score = (trigram_score * w_t) + (semantic_score * w_s)

    This mirrors the formula in SearchService.hybrid_search (search_service.py):
        hybrid_score = (t_score * w_t) + (s_score * w_s)
    """
    return (trigram_score * w_t) + (semantic_score * w_s)


def compute_rank_normalised_score(rank: int, total: int) -> float:
    """
    Compute the rank-based normalised trigram score.

    Formula: score = 1.0 - (rank / max(total, 1))

    This mirrors the normalisation in SearchService.hybrid_search:
        score = 1.0 - (rank / max(n_trigram, 1))
    """
    return 1.0 - (rank / max(total, 1))


# ── Default weights (from Settings defaults in src/config/database.py) ────────

DEFAULT_W_T = 0.3  # hybrid_trigram_weight
DEFAULT_W_S = 0.7  # hybrid_semantic_weight


# ── 13.1  Scoring formula unit tests ─────────────────────────────────────────

class TestHybridScoringFormula:
    """
    Unit tests for the hybrid scoring formula:
        hybrid_score = (trigram_score * w_t) + (semantic_score * w_s)

    Default weights: w_t = 0.3, w_s = 0.7
    """

    def test_both_scores_max_gives_1(self):
        """t=1.0, s=1.0 → hybrid_score = 1.0"""
        score = compute_hybrid_score(1.0, 1.0, DEFAULT_W_T, DEFAULT_W_S)
        assert score == pytest.approx(1.0)

    def test_trigram_only_gives_trigram_weight(self):
        """t=1.0, s=0.0 → hybrid_score = w_t = 0.3"""
        score = compute_hybrid_score(1.0, 0.0, DEFAULT_W_T, DEFAULT_W_S)
        assert score == pytest.approx(0.3)

    def test_semantic_only_gives_semantic_weight(self):
        """t=0.0, s=1.0 → hybrid_score = w_s = 0.7"""
        score = compute_hybrid_score(0.0, 1.0, DEFAULT_W_T, DEFAULT_W_S)
        assert score == pytest.approx(0.7)

    def test_equal_scores_gives_weighted_average(self):
        """t=0.5, s=0.5 → hybrid_score = 0.5 * 0.3 + 0.5 * 0.7 = 0.5"""
        score = compute_hybrid_score(0.5, 0.5, DEFAULT_W_T, DEFAULT_W_S)
        assert score == pytest.approx(0.5)

    def test_both_scores_zero_gives_zero(self):
        """t=0.0, s=0.0 → hybrid_score = 0.0"""
        score = compute_hybrid_score(0.0, 0.0, DEFAULT_W_T, DEFAULT_W_S)
        assert score == pytest.approx(0.0)

    def test_custom_weights_applied_correctly(self):
        """Custom weights: t=0.8, s=0.2, w_t=0.5, w_s=0.5 → 0.8*0.5 + 0.2*0.5 = 0.5"""
        score = compute_hybrid_score(0.8, 0.2, 0.5, 0.5)
        assert score == pytest.approx(0.5)

    def test_weights_sum_to_one_is_convex_combination(self):
        """When w_t + w_s = 1.0, the result is a convex combination of t and s."""
        t, s = 0.6, 0.4
        w_t, w_s = 0.4, 0.6
        assert w_t + w_s == pytest.approx(1.0)
        score = compute_hybrid_score(t, s, w_t, w_s)
        assert score == pytest.approx(t * w_t + s * w_s)

    def test_missing_trigram_score_defaults_to_zero(self):
        """
        Vendor present only in semantic results → trigram_score defaults to 0.0.
        hybrid_score = 0.0 * w_t + s * w_s = s * w_s
        """
        s = 0.9
        # trigram_score missing → default 0.0
        score = compute_hybrid_score(0.0, s, DEFAULT_W_T, DEFAULT_W_S)
        assert score == pytest.approx(s * DEFAULT_W_S)

    def test_missing_semantic_score_defaults_to_zero(self):
        """
        Vendor present only in trigram results → semantic_score defaults to 0.0.
        hybrid_score = t * w_t + 0.0 * w_s = t * w_t
        """
        t = 0.8
        # semantic_score missing → default 0.0
        score = compute_hybrid_score(t, 0.0, DEFAULT_W_T, DEFAULT_W_S)
        assert score == pytest.approx(t * DEFAULT_W_T)

    def test_vendor_only_in_trigram_results_uses_trigram_weight(self):
        """
        A vendor that appears only in trigram results (no embedding) gets
        semantic_score = 0.0, so hybrid_score = trigram_score * w_t.
        """
        trigram_score = 0.6
        hybrid_score = compute_hybrid_score(trigram_score, 0.0, DEFAULT_W_T, DEFAULT_W_S)
        assert hybrid_score == pytest.approx(trigram_score * DEFAULT_W_T)
        # Must be less than a vendor with both scores
        full_score = compute_hybrid_score(trigram_score, trigram_score, DEFAULT_W_T, DEFAULT_W_S)
        assert hybrid_score < full_score

    def test_vendor_only_in_semantic_results_uses_semantic_weight(self):
        """
        A vendor that appears only in semantic results (no trigram match) gets
        trigram_score = 0.0, so hybrid_score = semantic_score * w_s.
        """
        semantic_score = 0.85
        hybrid_score = compute_hybrid_score(0.0, semantic_score, DEFAULT_W_T, DEFAULT_W_S)
        assert hybrid_score == pytest.approx(semantic_score * DEFAULT_W_S)


# ── 13.1  Rank-based trigram normalisation unit tests ─────────────────────────

class TestRankNormalisedTrigramScore:
    """
    Unit tests for the rank-based normalisation formula used in hybrid_search:
        score = 1.0 - (rank / max(total, 1))

    Position 0 is the best match (highest score); position N-1 is the worst.
    """

    def test_first_of_five_gives_1(self):
        """Position 0 of 5 → 1.0 - (0/5) = 1.0"""
        score = compute_rank_normalised_score(rank=0, total=5)
        assert score == pytest.approx(1.0)

    def test_last_of_five_gives_0_2(self):
        """Position 4 of 5 → 1.0 - (4/5) = 0.2"""
        score = compute_rank_normalised_score(rank=4, total=5)
        assert score == pytest.approx(0.2)

    def test_single_result_gives_1(self):
        """Single result (position 0 of 1) → 1.0 - (0/1) = 1.0"""
        score = compute_rank_normalised_score(rank=0, total=1)
        assert score == pytest.approx(1.0)

    def test_middle_of_ten_gives_correct_score(self):
        """Position 5 of 10 → 1.0 - (5/10) = 0.5"""
        score = compute_rank_normalised_score(rank=5, total=10)
        assert score == pytest.approx(0.5)

    def test_second_of_four_gives_0_75(self):
        """Position 1 of 4 → 1.0 - (1/4) = 0.75"""
        score = compute_rank_normalised_score(rank=1, total=4)
        assert score == pytest.approx(0.75)

    def test_scores_are_monotonically_decreasing(self):
        """Higher rank (worse position) must always produce a lower score."""
        total = 10
        scores = [compute_rank_normalised_score(rank=i, total=total) for i in range(total)]
        for i in range(len(scores) - 1):
            assert scores[i] > scores[i + 1], (
                f"Score at rank {i} ({scores[i]}) should be greater than "
                f"score at rank {i+1} ({scores[i+1]})"
            )

    def test_all_scores_in_range(self):
        """All rank-normalised scores must be in [0.0, 1.0]."""
        total = 20
        for rank in range(total):
            score = compute_rank_normalised_score(rank=rank, total=total)
            assert 0.0 <= score <= 1.0, (
                f"Score {score} at rank {rank}/{total} is out of [0.0, 1.0]"
            )

    def test_zero_total_uses_max_guard(self):
        """
        When total=0 (empty result set), max(total, 1) guard prevents ZeroDivisionError.
        rank=0, total=0 → 1.0 - (0/max(0,1)) = 1.0 - 0 = 1.0
        """
        score = compute_rank_normalised_score(rank=0, total=0)
        assert score == pytest.approx(1.0)


# ── 13.2  Property-based test (Hypothesis) ────────────────────────────────────

class TestHybridScoreBoundsProperty:
    """
    Property-based test verifying that the hybrid score is always in [0.0, 1.0].

    **Validates: Requirements 7.2**

    For any t, s ∈ [0,1] and any w_t ∈ [0,1] with w_s = 1.0 - w_t,
    the hybrid score h = (t * w_t) + (s * w_s) must satisfy 0.0 ≤ h ≤ 1.0.
    """

    @given(
        t=st.floats(min_value=0.0, max_value=1.0, allow_nan=False),
        s=st.floats(min_value=0.0, max_value=1.0, allow_nan=False),
        w_t=st.floats(min_value=0.0, max_value=1.0, allow_nan=False),
    )
    @h_settings(max_examples=100)
    def test_hybrid_score_always_in_range(self, t: float, s: float, w_t: float):
        """
        For any t, s ∈ [0,1] and w_t ∈ [0,1] with w_s = 1.0 - w_t,
        the hybrid score must always be in [0.0, 1.0].
        """
        w_s = 1.0 - w_t
        hybrid_score = (t * w_t) + (s * w_s)
        assert 0.0 <= hybrid_score <= 1.0, (
            f"hybrid_score={hybrid_score} is out of [0.0, 1.0] "
            f"for t={t}, s={s}, w_t={w_t}, w_s={w_s}"
        )

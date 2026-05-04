"""
TruLensEvaluator — RAG Triad evaluation for hallucination detection.

Research basis:
- TruLens (Snowflake, 2024) — RAG evaluation framework
- "RAG Triad": Context Relevance, Groundedness, Answer Relevance
- "Evaluating RAG Applications" (arXiv 2025)

Purpose:
Evaluate RAG responses for:
1. Context Relevance: Is retrieved context relevant to the query?
2. Groundedness: Is the answer grounded in the context (no hallucination)?
3. Answer Relevance: Is the answer relevant to the original question?

When groundedness < threshold, emit HALLUCINATION_RISK audit event.
"""

import logging
import asyncio
from dataclasses import dataclass
from typing import Optional, List
from datetime import datetime, timezone

logger = logging.getLogger(__name__)

# Thresholds for evaluation scores (0.0 - 1.0)
GROUNDEDNESS_THRESHOLD = 0.7  # Below this = hallucination risk
CONTEXT_RELEVANCE_THRESHOLD = 0.6
ANSWER_RELEVANCE_THRESHOLD = 0.6

# ── TruLens availability check ───────────────────────────────────
_TRULENS_AVAILABLE = False
try:
    from trulens.core import Feedback
    from trulens.providers.openai import OpenAI
    from trulens.feedback import Groundedness
    _TRULENS_AVAILABLE = True
except ImportError:
    logger.info("TruLens not installed — using fallback evaluation")


@dataclass
class RAGTriadResult:
    """Result of RAG Triad evaluation."""
    context_relevance: float
    groundedness: float
    answer_relevance: float
    hallucination_risk: bool
    details: str
    timestamp: str


class TruLensEvaluator:
    """
    Evaluates RAG responses using the RAG Triad.
    
    Falls back to simple heuristics if TruLens is not installed.
    """
    
    def __init__(
        self,
        groundedness_threshold: float = GROUNDEDNESS_THRESHOLD,
        context_relevance_threshold: float = CONTEXT_RELEVANCE_THRESHOLD,
        answer_relevance_threshold: float = ANSWER_RELEVANCE_THRESHOLD,
        llm_provider: str = "gemini",
    ):
        self._groundedness_threshold = groundedness_threshold
        self._context_relevance_threshold = context_relevance_threshold
        self._answer_relevance_threshold = answer_relevance_threshold
        self._llm_provider = llm_provider
        self._provider = None
        
        if _TRULENS_AVAILABLE:
            try:
                # Initialize TruLens provider
                # Note: For Gemini, we use OpenAI-compatible endpoint
                self._provider = OpenAI()
                logger.info("TruLens evaluator initialized with OpenAI-compatible provider")
            except Exception as e:
                logger.warning("TruLens provider init failed: %s — using fallback", e)
    
    async def evaluate(
        self,
        question: str,
        answer: str,
        context: List[str],
        session_id: Optional[str] = None,
    ) -> RAGTriadResult:
        """
        Evaluate a RAG response using the RAG Triad.
        
        Args:
            question: The original user question
            answer: The generated answer
            context: List of retrieved context chunks
            session_id: Optional session ID for audit logging
        
        Returns:
            RAGTriadResult with evaluation scores
        """
        timestamp = datetime.now(timezone.utc).isoformat()
        
        if _TRULENS_AVAILABLE and self._provider:
            return await self._evaluate_trulens(question, answer, context, timestamp)
        else:
            return await self._evaluate_fallback(question, answer, context, timestamp)
    
    async def _evaluate_trulens(
        self,
        question: str,
        answer: str,
        context: List[str],
        timestamp: str,
    ) -> RAGTriadResult:
        """Full TruLens evaluation (when available)."""
        try:
            context_str = "\n".join(context) if context else ""
            
            # Groundedness check
            groundedness = Groundedness.groundedness_measure(
                self._provider,
                statement=answer,
                source=context_str,
            )
            
            # Context relevance (simplified)
            context_relevance = self._provider.relevance(
                prompt=question,
                response=context_str,
            )
            
            # Answer relevance
            answer_relevance = self._provider.relevance(
                prompt=question,
                response=answer,
            )
            
            hallucination_risk = groundedness < self._groundedness_threshold
            
            result = RAGTriadResult(
                context_relevance=float(context_relevance),
                groundedness=float(groundedness),
                answer_relevance=float(answer_relevance),
                hallucination_risk=hallucination_risk,
                details=f"TruLens evaluation completed",
                timestamp=timestamp,
            )
            
            if hallucination_risk:
                self._emit_hallucination_event(result, question, answer)
            
            return result
            
        except Exception as e:
            logger.error("TruLens evaluation failed: %s — falling back", e)
            return await self._evaluate_fallback(question, answer, context, timestamp)
    
    async def _evaluate_fallback(
        self,
        question: str,
        answer: str,
        context: List[str],
        timestamp: str,
    ) -> RAGTriadResult:
        """
        Fallback evaluation using simple heuristics.
        
        This is NOT a replacement for TruLens but provides basic checks:
        - Groundedness: Check if answer terms appear in context
        - Context relevance: Check if context terms appear in question
        - Answer relevance: Check if answer addresses question topic
        """
        context_str = " ".join(context).lower() if context else ""
        question_lower = question.lower()
        answer_lower = answer.lower()
        
        # Simple term overlap for groundedness
        answer_terms = set(answer_lower.split())
        context_terms = set(context_str.split())
        common_terms = answer_terms & context_terms
        
        # Exclude common stop words
        stop_words = {"the", "a", "an", "is", "are", "was", "were", "be", "been", 
                      "being", "have", "has", "had", "do", "does", "did", "will",
                      "would", "could", "should", "may", "might", "must", "shall",
                      "can", "need", "dare", "ought", "used", "to", "of", "in",
                      "for", "on", "with", "at", "by", "from", "as", "into",
                      "through", "during", "before", "after", "above", "below",
                      "between", "under", "again", "further", "then", "once", "and",
                      "but", "or", "nor", "so", "yet", "both", "either", "neither",
                      "not", "only", "own", "same", "than", "too", "very", "just"}
        
        meaningful_answer_terms = answer_terms - stop_words
        meaningful_common = meaningful_answer_terms & context_terms
        
        groundedness = len(meaningful_common) / max(len(meaningful_answer_terms), 1)
        
        # Context relevance: question terms in context
        question_terms = set(question_lower.split()) - stop_words
        context_relevance = len(question_terms & context_terms) / max(len(question_terms), 1)
        
        # Answer relevance: question topic in answer
        answer_relevance = 1.0 if question_terms & answer_terms else 0.5
        
        hallucination_risk = groundedness < self._groundedness_threshold
        
        result = RAGTriadResult(
            context_relevance=min(1.0, context_relevance),
            groundedness=min(1.0, groundedness),
            answer_relevance=answer_relevance,
            hallucination_risk=hallucination_risk,
            details=f"Fallback evaluation (TruLens unavailable)",
            timestamp=timestamp,
        )
        
        if hallucination_risk:
            self._emit_hallucination_event(result, question, answer)
        
        return result
    
    def _emit_hallucination_event(
        self,
        result: RAGTriadResult,
        question: str,
        answer: str,
    ):
        """Emit HALLUCINATION_RISK audit event."""
        from guardrails import audit_event
        audit_event(
            "HALLUCINATION_RISK",
            "system",
            None,
            {
                "groundedness": result.groundedness,
                "threshold": self._groundedness_threshold,
                "question_preview": question[:100],
                "answer_preview": answer[:100],
            }
        )
        logger.warning(
            "HALLUCINATION_RISK: groundedness=%.2f (threshold=%.2f)",
            result.groundedness,
            self._groundedness_threshold
        )


# Singleton instance
trulens_evaluator = TruLensEvaluator()

"""
Consensus/Voting Engine for Oracle Decision System

Inspired by TradingView's voting architecture where multiple technical analysis
modules vote on market direction, and signals fire only when consensus is reached.

This adds transparency and conflict detection to our decision-making process.
"""

from dataclasses import dataclass
from typing import List, Dict, Tuple
from oracle.features.base import FeatureResult


@dataclass
class CategoryVotes:
    """Votes within a feature category"""
    bull: int = 0
    bear: int = 0
    neutral: int = 0

    @property
    def total(self) -> int:
        return self.bull + self.bear + self.neutral

    @property
    def direction(self) -> str:
        if self.bull > self.bear and self.bull > self.neutral:
            return "BULLISH"
        elif self.bear > self.bull and self.bear > self.neutral:
            return "BEARISH"
        return "NEUTRAL"

    @property
    def strength(self) -> float:
        """Strength of consensus within category (0-1)"""
        if self.total == 0:
            return 0.0
        max_votes = max(self.bull, self.bear, self.neutral)
        return max_votes / self.total


@dataclass
class ConsensusResult:
    """Result of consensus analysis"""
    consensus_percentage: float
    category_votes: Dict[str, CategoryVotes]
    agreement_level: str
    conflicts: List[str]
    total_features: int
    bull_count: int
    bear_count: int
    neutral_count: int
    cross_category_agreement: float


class ConsensusEngine:
    """
    Analyzes agreement/disagreement across feature categories

    Key improvements over simple weighted scoring:
    1. Transparency: Clear view of which categories agree/disagree
    2. Conflict Detection: Identifies when different analysis types conflict
    3. Confidence Calibration: Higher consensus = higher confidence
    4. User Control: Adjustable consensus thresholds
    """

    # Consensus thresholds
    STRONG_CONSENSUS = 0.75  # 75%+ agreement
    MODERATE_CONSENSUS = 0.60  # 60-75% agreement
    WEAK_CONSENSUS = 0.50  # 50-60% agreement

    def __init__(self):
        self.categories = [
            'TECHNICAL',
            'MACRO',
            'CRYPTO_DERIVATIVES',
            'INTERMARKET',
            'SENTIMENT',  # Future: Twitter, Reddit sentiment
            'ONCHAIN'  # Future: Whale tracking, exchange flows
        ]

    def calculate_consensus(self, feature_results: List[FeatureResult]) -> ConsensusResult:
        """
        Calculate consensus across all features and categories

        Args:
            feature_results: List of FeatureResult objects from analysis

        Returns:
            ConsensusResult with detailed consensus breakdown
        """
        # Initialize vote tracking
        votes = {cat: CategoryVotes() for cat in self.categories}

        # Count votes by category
        for result in feature_results:
            category = result.category
            if category not in votes:
                # Handle unknown categories gracefully
                votes[category] = CategoryVotes()

            # Classify vote based on direction
            if result.direction > 0:
                votes[category].bull += 1
            elif result.direction < 0:
                votes[category].bear += 1
            else:
                votes[category].neutral += 1

        # Calculate overall consensus
        total_bull = sum(v.bull for v in votes.values())
        total_bear = sum(v.bear for v in votes.values())
        total_neutral = sum(v.neutral for v in votes.values())
        total_features = len(feature_results)

        # Consensus percentage = % of features agreeing on dominant direction
        consensus_pct = max(total_bull, total_bear, total_neutral) / total_features if total_features > 0 else 0

        # Classify agreement level
        agreement_level = self._classify_consensus(consensus_pct)

        # Detect conflicts between categories
        conflicts = self._detect_conflicts(votes)

        # Calculate cross-category agreement
        cross_category_agreement = self._calculate_cross_category_agreement(votes)

        return ConsensusResult(
            consensus_percentage=consensus_pct * 100,
            category_votes=votes,
            agreement_level=agreement_level,
            conflicts=conflicts,
            total_features=total_features,
            bull_count=total_bull,
            bear_count=total_bear,
            neutral_count=total_neutral,
            cross_category_agreement=cross_category_agreement
        )

    def _classify_consensus(self, pct: float) -> str:
        """Classify consensus level"""
        if pct >= self.STRONG_CONSENSUS:
            return "STRONG_CONSENSUS"
        elif pct >= self.MODERATE_CONSENSUS:
            return "MODERATE_CONSENSUS"
        elif pct >= self.WEAK_CONSENSUS:
            return "WEAK_CONSENSUS"
        else:
            return "NO_CONSENSUS"

    def _detect_conflicts(self, votes: Dict[str, CategoryVotes]) -> List[str]:
        """
        Detect conflicts between feature categories

        Examples:
        - Technical indicators bullish but macro bearish
        - Derivatives data bearish but spot technicals bullish
        - Sentiment bullish but price action bearish
        """
        conflicts = []

        # Get direction of each category
        directions = {cat: v.direction for cat, v in votes.items() if v.total > 0}

        # Define conflict pairs (categories that often conflict)
        conflict_pairs = [
            ('TECHNICAL', 'MACRO'),
            ('TECHNICAL', 'SENTIMENT'),
            ('CRYPTO_DERIVATIVES', 'TECHNICAL'),
            ('ONCHAIN', 'TECHNICAL'),
            ('SENTIMENT', 'TECHNICAL')
        ]

        for cat1, cat2 in conflict_pairs:
            if cat1 in directions and cat2 in directions:
                dir1 = directions[cat1]
                dir2 = directions[cat2]

                # Check for opposing signals
                if (dir1 == 'BULLISH' and dir2 == 'BEARISH') or \
                   (dir1 == 'BEARISH' and dir2 == 'BULLISH'):
                    # Calculate strength of conflict
                    strength1 = votes[cat1].strength
                    strength2 = votes[cat2].strength

                    # Only report significant conflicts (both categories have strong opinion)
                    if strength1 >= 0.6 and strength2 >= 0.6:
                        conflicts.append(
                            f"{cat1} {dir1.lower()} ({strength1:.0%} agreement) but "
                            f"{cat2} {dir2.lower()} ({strength2:.0%} agreement)"
                        )

        return conflicts

    def _calculate_cross_category_agreement(self, votes: Dict[str, CategoryVotes]) -> float:
        """
        Calculate how well categories agree with each other (0-1)

        High score = categories pointing same direction
        Low score = categories disagree
        """
        active_categories = [v for v in votes.values() if v.total > 0]

        if len(active_categories) < 2:
            return 1.0  # Perfect agreement with only 1 category

        # Count pairwise agreements
        agreements = 0
        comparisons = 0

        for i, cat1 in enumerate(active_categories):
            for cat2 in active_categories[i+1:]:
                comparisons += 1
                if cat1.direction == cat2.direction:
                    agreements += 1

        return agreements / comparisons if comparisons > 0 else 1.0

    def adjust_confidence_by_consensus(
        self,
        base_confidence: float,
        consensus: ConsensusResult
    ) -> Tuple[float, str]:
        """
        Adjust confidence score based on consensus level

        Args:
            base_confidence: Original confidence (0-100)
            consensus: ConsensusResult object

        Returns:
            (adjusted_confidence, explanation)
        """
        adjustment_factor = 1.0
        explanation_parts = []

        # 1. Adjust based on overall consensus level
        if consensus.agreement_level == "STRONG_CONSENSUS":
            adjustment_factor *= 1.15
            explanation_parts.append(f"Strong consensus ({consensus.consensus_percentage:.0f}%)")
        elif consensus.agreement_level == "MODERATE_CONSENSUS":
            adjustment_factor *= 1.05
            explanation_parts.append(f"Moderate consensus ({consensus.consensus_percentage:.0f}%)")
        elif consensus.agreement_level == "WEAK_CONSENSUS":
            adjustment_factor *= 0.95
            explanation_parts.append(f"Weak consensus ({consensus.consensus_percentage:.0f}%)")
        else:
            adjustment_factor *= 0.80
            explanation_parts.append(f"No consensus ({consensus.consensus_percentage:.0f}%)")

        # 2. Penalize for conflicts
        if consensus.conflicts:
            conflict_penalty = 0.10 * len(consensus.conflicts)
            adjustment_factor *= (1.0 - conflict_penalty)
            explanation_parts.append(f"{len(consensus.conflicts)} conflict(s) detected")

        # 3. Reward cross-category agreement
        if consensus.cross_category_agreement >= 0.8:
            adjustment_factor *= 1.10
            explanation_parts.append(f"High cross-category agreement ({consensus.cross_category_agreement:.0%})")
        elif consensus.cross_category_agreement <= 0.4:
            adjustment_factor *= 0.90
            explanation_parts.append(f"Low cross-category agreement ({consensus.cross_category_agreement:.0%})")

        # Calculate final confidence
        adjusted_confidence = base_confidence * adjustment_factor

        # Clamp to 0-100
        adjusted_confidence = max(0, min(100, adjusted_confidence))

        explanation = " | ".join(explanation_parts)

        return adjusted_confidence, explanation

    def get_consensus_summary(self, consensus: ConsensusResult) -> str:
        """
        Generate human-readable consensus summary

        Example:
        "Strong bullish consensus (78%): 15 bull, 4 bear, 0 neutral.
         Categories agree: TECHNICAL bullish, MACRO bullish, CRYPTO_DERIVATIVES bullish.
         No conflicts detected."
        """
        # Determine dominant direction
        if consensus.bull_count > consensus.bear_count:
            direction = "bullish"
            count = consensus.bull_count
        elif consensus.bear_count > consensus.bull_count:
            direction = "bearish"
            count = consensus.bear_count
        else:
            direction = "neutral"
            count = consensus.neutral_count

        summary_parts = []

        # Overall consensus
        summary_parts.append(
            f"{consensus.agreement_level.replace('_', ' ').title()} {direction} "
            f"({consensus.consensus_percentage:.0f}%): "
            f"{consensus.bull_count} bull, {consensus.bear_count} bear, "
            f"{consensus.neutral_count} neutral"
        )

        # Category breakdown
        category_directions = []
        for cat, votes in consensus.category_votes.items():
            if votes.total > 0:
                category_directions.append(f"{cat} {votes.direction.lower()}")

        if category_directions:
            summary_parts.append(f"Categories: {', '.join(category_directions)}")

        # Conflicts
        if consensus.conflicts:
            summary_parts.append(f"⚠️ Conflicts: {'; '.join(consensus.conflicts)}")
        else:
            summary_parts.append("✓ No conflicts detected")

        return ". ".join(summary_parts)

    def should_fire_signal(
        self,
        consensus: ConsensusResult,
        min_consensus_pct: float = 60.0,
        allow_conflicts: bool = False
    ) -> Tuple[bool, str]:
        """
        Determine if signal should fire based on consensus rules

        Inspired by TradingView's approach: only fire when threshold met

        Args:
            consensus: ConsensusResult object
            min_consensus_pct: Minimum consensus % required (default 60%)
            allow_conflicts: Whether to allow signals with conflicts

        Returns:
            (should_fire, reason)
        """
        reasons = []

        # Check consensus threshold
        if consensus.consensus_percentage < min_consensus_pct:
            return False, f"Consensus {consensus.consensus_percentage:.0f}% below threshold {min_consensus_pct:.0f}%"

        # Check for conflicts (if strict mode)
        if not allow_conflicts and consensus.conflicts:
            return False, f"Conflicts detected: {'; '.join(consensus.conflicts)}"

        # Check minimum feature count
        if consensus.total_features < 5:
            return False, f"Insufficient features ({consensus.total_features} < 5 required)"

        # All checks passed
        return True, f"Consensus criteria met ({consensus.consensus_percentage:.0f}%)"


# Convenience function for integration
def analyze_consensus(feature_results: List[FeatureResult]) -> ConsensusResult:
    """
    Convenience function to analyze consensus

    Usage:
        consensus = analyze_consensus(feature_results)
        print(consensus.consensus_percentage)
        print(consensus.conflicts)
    """
    engine = ConsensusEngine()
    return engine.calculate_consensus(feature_results)

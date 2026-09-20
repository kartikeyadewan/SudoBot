"""Sudobot deterministic fuzzy matching engine.

Uses RapidFuzz for fuzzy string comparison.

Provides: match_command() - takes a mistyped command and available commands,
returns ranked correction candidates with similarity scores.

The matcher is standalone: it does NOT discover commands, does NOT execute,
does NOT enforce safety, and does NOT modify arguments.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional

import rapidfuzz.fuzz
import rapidfuzz.process


@dataclass(frozen=True, order=True)
class Candidate:
    """Immutable candidate command with similarity score."""
    command: str
    score: int


# Conservative confidence threshold for suggesting a correction.
#
# Rationale:
# - RapidFuzz's Damerau-Levenshtein similarity scores range 0-100.
# - Scores above 90 typically indicate very similar strings (1-2 edits).
# - Scores 80-90 indicate plausible corrections with 2-3 edits.
# - Scores below 80 are increasingly unlikely to be intentional corrections.
#
# Short commands (< 5 chars) require higher thresholds because random
# similarity is more likely. The threshold adjustment below handles this.
CONFIDENCE_THRESHOLD = 85

# For very short commands (1-2 chars), require near-perfect match.
# This prevents false corrections like "l" -> "ls".
SHORT_COMMAND_THRESHOLD = 95


def _is_single_edit_typo(cmd: str, target: str) -> bool:
    """
    Determine if the typo and candidate represent a single-edit pattern
    that should receive a score boost.
    
    Currently recognizes:
    - Transpositions: two adjacent characters swapped (e.g. pyhton -> python)
    
    Does NOT recognize single substitutions to avoid false positives like
    pythonn -> python2.
    
    Returns True if the pattern is detected.
    """
    t_len = len(target)
    if t_len == len(cmd) and len(cmd) >= 3:
        diffs = sum(1 for a, b in zip(cmd, target) if a != b)
        
        # Check for transposition: exactly 2 differing positions,
        # adjacent in both strings, characters are crossed
        if diffs == 2:
            positions = [i for i in range(len(cmd)) if cmd[i] != target[i]]
            if len(positions) == 2 and abs(positions[0] - positions[1]) == 1:
                i = positions[0]
                if cmd[i] == target[i + 1] and cmd[i + 1] == target[i]:
                    return True
    
    return False


def _is_single_substitution_typo(cmd: str, target: str, raw_score: int) -> bool:
    """
    Determine if the typo and candidate represent a single-character
    substitution that should receive a score boost.
    
    Conditions (all must be met):
    1. Candidate and input have equal length.
    2. They differ by exactly one character (substitution, not transposition).
    3. The raw RapidFuzz score is >= 80.
    
    Returns True if the pattern is detected and the score threshold is met.
    """
    t_len = len(target)
    # Condition 1: equal length
    if t_len != len(cmd) or len(cmd) < 3:
        return False
    
    # Count differing positions
    diff_positions = [i for i in range(len(cmd)) if cmd[i] != target[i]]
    
    # Condition 2: exactly one differing position (substitution, not transposition)
    if len(diff_positions) != 1:
        return False
    
    # Condition 3: raw score >= 80
    if raw_score < 80:
        return False
    
    return True


def _is_single_deletion_typo(cmd: str, target: str) -> bool:
    """
    Return True when deleting exactly one character from cmd produces target.

    Conditions:
    - len(cmd) == len(target) + 1
    - removing one character from cmd yields target
    """
    if len(cmd) != len(target) + 1:
        return False
    for i in range(len(cmd)):
        if cmd[:i] + cmd[i + 1:] == target:
            return True
    return False


def _is_single_insertion_typo(cmd: str, target: str) -> bool:
    """
    Return True when deleting exactly one character from target produces cmd.

    Conditions:
    - len(cmd) == len(target) - 1
    - removing one character from target yields cmd
    """
    if len(cmd) != len(target) - 1:
        return False
    for i in range(len(target)):
        if target[:i] + target[i + 1:] == cmd:
            return True
    return False


def match_command(
    command: str,
    available_commands: list[str],
) -> list[Candidate]:
    """Rank fuzzy correction candidates for a mistyped command.

    Parameters
    ----------
    command : str
        The mistyped command name (e.g. "unmount", "sytemctl").
    available_commands : list[str]
        Commands actually available on the user's system (from discover_commands()).

    Returns
    -------
    list[Candidate]
        Ranked candidates sorted by score descending. Empty list if no
        candidate meets the confidence threshold.

    Notes
    -----
    - Does NOT modify the input `command` or `available_commands`.
    - Uses RapidFuzz's similarity scorer.
    - Applies conservative confidence thresholds.
    - Short commands require higher similarity.
    - Exact matches in available_commands are excluded (caller should
      handle those separately).
    - Deterministic: same input always produces same ordered output.
    - Adds deterministic transposition detection for obvious typos:
      when two adjacent characters are swapped (e.g. pyhton -> python),
      a 10-point boost is added to the RapidFuzz ratio score, helping
      recognize this common typing mistake that falls just below the 85
      threshold.
    """
    # Input validation
    if not command or not command.strip():
        return []

    if not available_commands:
        return []

    # Normalize: strip whitespace but preserve case (command names are case-sensitive)
    cmd = command.strip()

    # Use RapidFuzz process to find best matches
    # ratio (Damerau-Levenshtein similarity) is the primary scorer.
    # It provides a globally-normalized 0-100 score suitable for conservative
    # confidence thresholding. The threshold of 85 balances recall of obvious
    # typos against false-positive suggestions.
    scores = rapidfuzz.process.extract(
        cmd,
        available_commands,
        scorer=rapidfuzz.fuzz.ratio,
        score_cutoff=0,  # Keep all candidates; thresholds applied in loop
        limit=None,
    )

    # Build candidate list with scores
    candidates: list[Candidate] = []
    for target, score, _idx in scores:
        # Skip if score is 0 (no similarity at all)
        if score <= 0:
            continue

        # Skip exact matches - caller should handle these
        if target == cmd:
            continue

        # --- Apply deterministic transposition detection for obvious typos.
        # Check BEFORE the threshold check so we can boost scores for recognized patterns.
        # When two adjacent characters are swapped (e.g. pyhton -> python),
        # a 10-point boost is added to the RapidFuzz ratio score.
        transposition_boost = 0
        if _is_single_edit_typo(cmd, target):
            transposition_boost = 10

        # --- Apply deterministic substitution, deletion, and insertion detection.
        # These are only checked when no transposition boost was applied,
        # to avoid double-boosting the same candidate.
        # Single-character substitutions receive a +5 boost.
        # Single-character deletions and insertions receive a +10 boost,
        # matching the transposition boost since they are equally obvious typos.
        substitution_boost = 0
        deletion_boost = 0
        insertion_boost = 0
        if transposition_boost == 0:
            if _is_single_substitution_typo(cmd, target, round(score)):
                substitution_boost = 5
            elif _is_single_deletion_typo(cmd, target) and score < CONFIDENCE_THRESHOLD:
                deletion_boost = 10
            elif _is_single_insertion_typo(cmd, target) and score < CONFIDENCE_THRESHOLD:
                insertion_boost = 10

        # Apply short command guard (using original score; boost applied later)
        if len(cmd) <= 2:
            if score < SHORT_COMMAND_THRESHOLD:
                continue
        else:
            if score < CONFIDENCE_THRESHOLD:
                # but if we have a boost, use the boosted score instead
                if transposition_boost == 0 and substitution_boost == 0 and deletion_boost == 0 and insertion_boost == 0:
                    continue

        # Apply all boosts for recognized edit patterns
        final_score = min(round(score) + transposition_boost + substitution_boost + deletion_boost + insertion_boost, 100)

        # Apply confidence threshold with boost
        if final_score < CONFIDENCE_THRESHOLD:
            continue

        # Store as int (round to nearest integer, with boost applied)
        # Deduplicate: if same command appears multiple times with same score, keep one
        if not any(c.command == target for c in candidates):
            candidates.append(Candidate(command=target, score=final_score))

    # Limit candidates to top results to avoid excessive suggestions
    # This prevents returning dozens of equally-good matches
    candidates = candidates[:3]

    # Sort by score descending (the dataclass order=True handles this)
    # Then by command name ascending for tie-breaking (deterministic)
    candidates.sort(key=lambda c: (-c.score, c.command))

    # Deduplicate: if same command appears multiple times with same score, keep one
    seen: set[str] = set()
    unique: list[Candidate] = []
    for c in candidates:
        if c.command not in seen:
            seen.add(c.command)
            unique.append(c)

    return unique


def match_command_with_scores(
    command: str,
    available_commands: list[str],
) -> list[tuple[str, int]]:
    """Return command/score pairs for CLI display.

    Convenience wrapper around match_command() that returns tuples
    instead of Candidate objects for flexibility.

    Parameters
    ----------
    command : str
        The mistyped command name.
    available_commands : list[str]
        Commands actually available on the user's system.

    Returns
    -------
    list[tuple[str, int]]
        List of (command, score) tuples sorted by score descending.
        Empty list if no confident correction.
    """
    candidates = match_command(command, available_commands)
    return [(c.command, c.score) for c in candidates]
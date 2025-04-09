from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from Levenshtein import distance as levenshtein_distance
from scipy.stats import pearsonr
from sortedcontainers import SortedList


class ApplyPatchError(Exception):
    pass


@dataclass(frozen=True)
class LineMatch:
    idx: int
    """The index of the line in some file."""
    distance: int
    """The Levenshtein distance between the line in some file and a reference line."""

    def __lt__(self, other):
        return self.distance < other.distance

    def __le__(self, other):
        return self.distance <= other.distance

    def __gt__(self, other):
        return self.distance > other.distance

    def __ge__(self, other):
        return self.distance >= other.distance

    def __eq__(self, other):
        return self.distance == other.distance


@dataclass(frozen=True)
class CodeMatch:
    start: int
    """The index of the starting line of the best match."""
    end: int
    """The index od the ending line of the best match."""
    distance: int
    """The Levenshtein distance between the matched lines."""

    @classmethod
    def from_text(
        cls, orig_text: str, start: int, end: int, ref_to_match: str
    ) -> CodeMatch:
        """Create a CodeFragment from the original text."""
        return cls(
            start=start,
            end=end,
            distance=levenshtein_distance(orig_text[start:end], ref_to_match),
        )

    def __lt__(self, other):
        return self.distance < other.distance

    def __le__(self, other):
        return self.distance <= other.distance

    def __gt__(self, other):
        return self.distance > other.distance

    def __ge__(self, other):
        return self.distance >= other.distance

    def __eq__(self, other):
        return self.distance == other.distance


class RankingList(SortedList):
    """
    A sorted list that only keeps a given number of best values.

    The list is sorted in ascending order by default. The list can be configured to keep
    the best values in the list, either by keeping the smallest values or the largest.
    The list can also be configured to allow draws.
    """

    def __init__(
        self,
        iterable=None,
        key=None,
        limit: int = 3,
        smaller_better: bool = True,
        ok_draws: bool = True,
    ):
        self.limit = limit
        self.smaller_better = smaller_better
        self.ok_draws = ok_draws
        super().__init__(iterable, key)

    def __new__(
        cls,
        iterable=None,
        key=None,
        limit: int = 3,
        smaller_better: bool = True,
        ok_draws: bool = True,
    ):
        return super().__new__(cls, iterable, key)

    def _pop(self):
        if self.smaller_better:
            del self[-1]
        else:
            del self[0]

    def _within_range(self, value) -> bool:
        if self.ok_draws:
            return value <= self[0] if self.smaller_better else value >= self[-1]
        else:
            return value < self[0] if self.smaller_better else value > self[-1]

    def add(self, value):
        """
        Add a new value to the list.

        Add a value to the list if it is better than the worst value in the list and
        remove the worst value if the list was full.
        """
        if len(self) < self.limit:
            super().add(value)
            return

        if not self._within_range(value):
            return

        super().add(value)
        self._pop()

    @property
    def best(self):
        """Return the best value in the list."""
        return self[0] if self.smaller_better else self[-1]


class Frame:
    """
    A frame represents a place in a code file and its similarity to a given code patch.

    A frame is defined by:
    - a start and end line of a code file,
    - lines between the start and end line that are similar to lines the code patch,
    - the coverage of lines in the code patch by the lines the frame,
    - the similarity of the line order in the frame and the line order in code patch.
    """

    @property
    def n_lines(self) -> int:
        return self.file_end_line - self.file_start_line + 1

    def __init__(self, start_line: LineMatch, end_line: LineMatch, n_patch_lines: int):
        self.file_start_line = start_line.idx
        self.file_end_line = end_line.idx
        self.n_patch_lines = n_patch_lines
        self.matched_lines = []

        self.add_matched_line(0, start_line)
        self.add_matched_line(n_patch_lines - 1, end_line)

    def add_matched_line(self, patch_line_idx: int, line_match: LineMatch) -> bool:
        if self.file_start_line <= line_match.idx <= self.file_end_line:
            self.matched_lines.append((patch_line_idx, line_match))
            return True
        return False

    def add_matched_lines(self, patch_line_idx: int, line_matches: list[LineMatch]):
        for line_match in line_matches:
            if self.add_matched_line(patch_line_idx, line_match):
                return

    @property
    def score(self):
        """Return the score of the frame.

        The score represents how good of a match the frame is to a fragment of code.
        Lower score is better. The lowest possible score is 0. The highest possible
        score is infinity.

        The score is calculated as a product of:
        - the average levenstein distance between the matched lines in the frame and
        the code patch,
        - the coverage of the code patch by the frame,
        - the correlation between the order of lines in the frame and the order of
        lines in the code patch.
        """
        n_matches = len(self.matched_lines)
        line_idx_corr = pearsonr(
            [line_match.idx for patch_line_idx, line_match in self.matched_lines],
            [patch_line_idx for patch_line_idx, line_match in self.matched_lines],
        )[0]

        if np.isnan(line_idx_corr):
            line_idx_corr = 0

        total_dist = sum(
            [line_match.distance for patch_line_idx, line_match in self.matched_lines]
        )

        avg_dist = total_dist / n_matches
        match_coverage = n_matches / self.n_patch_lines

        return avg_dist * (2 - match_coverage) * (1 - line_idx_corr)

    def to_match(self):
        """Return a CodeMatch object based on the frame."""
        return CodeMatch(
            start=self.file_start_line, end=self.file_end_line, distance=self.score
        )

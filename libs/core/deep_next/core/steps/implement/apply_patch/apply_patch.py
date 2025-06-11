from deep_next.core.steps.implement.apply_patch.common import (
    ApplyPatchError,
    CodeMatch,
    Frame,
    LineMatch,
    RankingList,
)
from deep_next.core.steps.implement.apply_patch.lint_merge import lint_and_merge
from deep_next.core.steps.implement.utils import CodePatch
from rapidfuzz.distance import Levenshtein as levenshtein_distance


def _get_exact_match(text: str, match: str) -> CodeMatch | None:
    """
    Get the exact match for 'match' in 'text'.

    Get the exact match for 'match' in 'text' and return a CodeMatch object pointing to
    the place of the match in 'text'. If no exact match is found, None is returned.

    Args:
        text: Text to search in.
        match: Text to search for.
    """
    result = text.split(match)
    if len(result) == 1:
        return None

    start = len(result[0].splitlines())
    n_match_lines = len(match.splitlines())
    return CodeMatch(start=start, end=start + n_match_lines - 1, distance=0)


def _apply_patch_exact_match(file_text: str, patch: CodePatch) -> bool:
    """
    Apply a code patch to a code file by finding an exact match.

    If an exact match is not found, 'False' is returned. Otherwise, 'True' is returned.
    """
    best_match = _get_exact_match(file_text, patch.before)

    if not best_match:
        return False

    file_lines = file_text.split("\n")
    new_file_text = lint_and_merge(file_lines, best_match, patch)
    patch.file_path.write_text(new_file_text)

    return True


def _get_closest_line_idx(
    file_lines: list[str], line: str, limit: int = 3
) -> list[LineMatch]:
    """
    Get indices of lines in 'file_lines' most similar to 'line' .

    Args:
        file_lines: List of lines to search in.
        line: Line to search for.
        limit: Maximum number of matches to return.
    """
    rank_list = RankingList(limit=limit)

    for idx, candidate_line in enumerate(file_lines):
        dist = levenshtein_distance(candidate_line, line, weights=(1, 1, 3))
        line_match = LineMatch(idx=idx, distance=dist)
        rank_list.add(line_match)

    return list(rank_list)


def _mask_file_lines(
    file_lines: list[str], frames: list[Frame], mask: str = "=" * 20
) -> list[str]:
    """
    Replace all lines in 'file_lines' with the 'mask' that are not part of any frame.

    Args:
        file_lines: List of all lines.
        frames: List of frames within which lines will not be replaced.
        mask: String to replace unmatched.
    """
    selection = [False] * len(file_lines)
    for frame in frames:
        for line_idx in range(frame.file_start_line, frame.file_end_line + 1):
            selection[line_idx] = True

    return [line if selection[idx] else mask for idx, line in enumerate(file_lines)]


def _select_matching_frames(
    file_lines: list[str],
    patch: CodePatch,
    start_line_match_limit: int = 7,
    end_line_match_limit: int = 3,
) -> list[Frame]:
    """
    Select frames from a code file that best match the code patch.

    The number of frames will be 'start_line_match_limit' * 'end_line_match_limit'.

    Args:
        file_lines: List of lines in the code file.
        patch: Code patch to match.
        start_line_match_limit: Maximum number of start line matches to consider.
        end_line_match_limit: Maximum number of end line matches for each start line
            match.
    """
    best_frames = []

    before_lines = patch.before.splitlines()

    best_start_line_matches = _get_closest_line_idx(
        file_lines, before_lines[0], limit=start_line_match_limit
    )

    for start_line in best_start_line_matches:
        best_end_line_matches = _get_closest_line_idx(
            file_lines[start_line.idx : start_line.idx + 2 * len(before_lines)],
            line=before_lines[-1],
            limit=end_line_match_limit,
        )
        best_end_line_matches = [
            LineMatch(start_line.idx + end_line_match.idx, end_line_match.distance)
            for end_line_match in best_end_line_matches
        ]

        for end_line in best_end_line_matches:
            frame = Frame(
                start_line=start_line,
                end_line=end_line,
                n_patch_lines=len(before_lines),
            )
            best_frames.append(frame)

    return best_frames


def _apply_patch_by_frame(file_text: str, patch: CodePatch) -> None:
    """
    Apply a code patch to a code file by selecting the best matching code frame.

    If no matching frames are found, an exception is raised.
    """
    file_lines = file_text.split("\n")

    matching_frames = _select_matching_frames(file_lines, patch)

    if not matching_frames:
        raise ApplyPatchError(f"No frames found.\n\n{patch.before}")

    masked_file_lines = _mask_file_lines(file_lines, matching_frames)
    for line_idx, line in enumerate(patch.before.splitlines()):
        closest_lines = _get_closest_line_idx(masked_file_lines, line)
        for frame in matching_frames:
            frame.add_matched_lines(line_idx, closest_lines)

    best_frame = min(matching_frames, key=lambda frame: frame.score)

    if best_frame.score > 20:
        raise ApplyPatchError("The best match is too different from the original code.")

    best_match = best_frame.to_match()

    file_lines = file_text.split("\n")
    new_file_text = lint_and_merge(file_lines, best_match, patch)
    patch.file_path.write_text(new_file_text)


def apply_patch(patch: CodePatch) -> None:
    """Apply a code patch to a code file."""
    file_text = patch.file_path.read_text()

    if _apply_patch_exact_match(file_text, patch):
        return None

    return _apply_patch_by_frame(file_text, patch)

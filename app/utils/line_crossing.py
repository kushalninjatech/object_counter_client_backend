"""Line crossing detection logic."""

from typing import Tuple, List, Optional
import numpy as np


class SingleLineCrossingDetector:
    """Detects when objects cross a single line and determines direction."""

    def __init__(self, line: List[Tuple[int, int]]):
        """Initialize detector with a single counting line.

        Args:
            line: Counting line as [(x1, y1), (x2, y2)]
        """
        self.line = line

    def _get_side_of_line(self, point: Tuple[int, int], line: List[Tuple[int, int]]) -> float:
        """Determine which side of the line a point is on.

        Args:
            point: Point (x, y)
            line: Line as [(x1, y1), (x2, y2)]

        Returns:
            Positive if on one side, negative if on other side, 0 if on line
        """
        (x1, y1), (x2, y2) = line
        px, py = point

        # Cross product to determine side
        # If result > 0: point is on left side
        # If result < 0: point is on right side
        # If result = 0: point is on the line
        return (x2 - x1) * (py - y1) - (y2 - y1) * (px - x1)

    def check_crossing(self, prev_point: Tuple[int, int],
                      curr_point: Tuple[int, int],
                      line: List[Tuple[int, int]]) -> bool:
        """Check if movement from prev_point to curr_point crosses the line.

        Uses cross product method to check if points are on opposite sides.

        Args:
            prev_point: Previous position (x, y)
            curr_point: Current position (x, y)
            line: Line as [(x1, y1), (x2, y2)]

        Returns:
            True if the movement crosses the line, False otherwise
        """
        if prev_point is None or curr_point is None:
            return False

        # Get which side of the line each point is on
        prev_side = self._get_side_of_line(prev_point, line)
        curr_side = self._get_side_of_line(curr_point, line)

        # If signs are different (one positive, one negative), they're on opposite sides
        # This means the vehicle crossed the line
        return prev_side * curr_side < 0

    def get_crossing_direction(self, prev_point: Tuple[int, int],
                               curr_point: Tuple[int, int]) -> Optional[str]:
        """Check if line was crossed and determine direction.

        Args:
            prev_point: Previous position
            curr_point: Current position

        Returns:
            "in" if crossed from positive side to negative side
            "out" if crossed from negative side to positive side
            None if no crossing occurred
        """
        if prev_point is None or curr_point is None:
            return None

        # Get which side of the line each point is on
        prev_side = self._get_side_of_line(prev_point, self.line)
        curr_side = self._get_side_of_line(curr_point, self.line)

        # Check if crossing occurred (points on opposite sides)
        if prev_side * curr_side < 0:
            # Crossing occurred - determine direction
            # If moving from positive side to negative side = IN
            # If moving from negative side to positive side = OUT
            if prev_side > 0 and curr_side < 0:
                return "in"
            else:
                return "out"

        return None  # No crossing

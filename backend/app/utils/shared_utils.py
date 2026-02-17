"""Shared utilities for behavioral analysis agents."""

from datetime import time


def parse_usual_hours(usual_hours: str) -> tuple[time, time]:
    """Parse usual hours string like '08:00-22:00' into (start_time, end_time).

    Args:
        usual_hours: Time range string in format "HH:MM-HH:MM"

    Returns:
        Tuple of (start_time, end_time)

    Raises:
        ValueError: If format is invalid
    """
    start_str, end_str = usual_hours.split("-")
    start = time.fromisoformat(start_str.strip())
    end = time.fromisoformat(end_str.strip())
    return start, end


def is_time_in_range(check_time: time, start: time, end: time) -> bool:
    """Check if a time falls within a time range (handles overnight ranges).

    Args:
        check_time: Time to check
        start: Range start time
        end: Range end time

    Returns:
        True if check_time is within the range
    """
    if start <= end:
        return start <= check_time <= end
    else:  # Overnight range (e.g., 22:00-06:00)
        return check_time >= start or check_time <= end

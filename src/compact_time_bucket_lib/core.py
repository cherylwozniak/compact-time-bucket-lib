"""Compact time bucketing for aggregating timestamped data.

The library groups timestamps into variable-length buckets. Bucket boundaries
are defined by the caller as a sequence of non-negative integer offsets. This
keeps the representation compact and makes the grouping rule explicit, rather
than relying on wall-clock alignment.

Design decision: a bucket is a half-open interval [start, end). A timestamp
that falls exactly on a boundary belongs to the bucket that starts there.
"""

from bisect import bisect_right
from typing import Callable, List, Sequence, Tuple


class Bucket:
    """A half-open time interval [start, end) with an optional label.

    Attributes:
        start: Inclusive start offset.
        end: Exclusive end offset.
        label: Optional human-readable label for the bucket.
    """

    __slots__ = ("start", "end", "label")

    def __init__(self, start: int, end: int, label: str = "") -> None:
        if start < 0 or end < 0:
            raise ValueError("bucket offsets must be non-negative")
        if end <= start:
            raise ValueError("bucket end must be greater than start")
        self.start = start
        self.end = end
        self.label = label

    def contains(self, timestamp: int) -> bool:
        """Return True if timestamp is in [start, end)."""
        return self.start <= timestamp < self.end

    def __repr__(self) -> str:
        return f"Bucket(start={self.start!r}, end={self.end!r}, label={self.label!r})"

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Bucket):
            return NotImplemented
        return (
            self.start == other.start
            and self.end == other.end
            and self.label == other.label
        )


class _Bucketer:
    """Callable that assigns timestamps to buckets.

    The bucketer is constructed from a sequence of boundaries. Boundaries are
the starts of each bucket, and must be strictly increasing and non-negative.
The final bucket extends to positive infinity, so any timestamp at or beyond
the last boundary is assigned to it.

    Attributes:
        boundaries: The tuple of bucket start offsets.
        buckets: The tuple of Bucket instances.
    """

    __slots__ = ("_boundaries", "_buckets", "_labels")

    def __init__(
        self,
        boundaries: Sequence[int],
        labels: Sequence[str] | None = None,
    ) -> None:
        if not boundaries:
            raise ValueError("at least one boundary is required")

        previous = -1
        for boundary in boundaries:
            if boundary < 0:
                raise ValueError("boundaries must be non-negative")
            if boundary <= previous:
                raise ValueError("boundaries must be strictly increasing")
            previous = boundary

        if labels is None:
            labels = [""] * len(boundaries)
        elif len(labels) != len(boundaries):
            raise ValueError("labels must match the number of boundaries")

        self._boundaries = tuple(boundaries)
        self._labels = tuple(labels)
        self._buckets = self._build_buckets()

    def _build_buckets(self) -> Tuple[Bucket, ...]:
        buckets: List[Bucket] = []
        for index, start in enumerate(self._boundaries):
            if index + 1 < len(self._boundaries):
                end = self._boundaries[index + 1]
            else:
                # The final bucket is open-ended. We use a very large sentinel
                # rather than math.inf because Bucket stores integer offsets
                # and comparisons with floats would be surprising.
                end = 1 << 62
            buckets.append(Bucket(start, end, self._labels[index]))
        return tuple(buckets)

    @property
    def boundaries(self) -> Tuple[int, ...]:
        return self._boundaries

    @property
    def buckets(self) -> Tuple[Bucket, ...]:
        return self._buckets

    def __call__(self, timestamp: int) -> Bucket:
        """Return the bucket that contains timestamp.

        Timestamps before the first boundary are clamped into the first
        bucket. This keeps the function total over all integers, which is
        useful when data may predate the configured range.
        """
        if not isinstance(timestamp, int):
            raise TypeError("timestamp must be an integer")
        index = bisect_right(self._boundaries, timestamp) - 1
        if index < 0:
            index = 0
        return self._buckets[index]

    def group(self, timestamps: Sequence[int]) -> dict:
        """Group timestamps by bucket label.

        Buckets with an empty label are keyed by their start offset as a
        string. This avoids collisions between unlabeled buckets and keeps
        the return type a plain dict.
        """
        result: dict = {}
        for timestamp in timestamps:
            bucket = self(timestamp)
            key = bucket.label if bucket.label else str(bucket.start)
            result.setdefault(key, []).append(timestamp)
        return result


def bucketer(
    boundaries: Sequence[int],
    labels: Sequence[str] | None = None,
) -> _Bucketer:
    """Create a bucketer from bucket start offsets.

    Args:
        boundaries: Strictly increasing, non-negative bucket starts.
        labels: Optional labels, one per boundary.

    Returns:
        A callable that maps a timestamp to a Bucket and can group sequences.
    """
    return _Bucketer(boundaries, labels)

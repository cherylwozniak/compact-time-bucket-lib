# compact-time-bucket-lib

Groups timestamps into variable-length buckets defined by explicit start offsets, for aggregation without wall-clock alignment.

```python
from compact_time_bucket_lib import bucketer

b = bucketer([0, 10, 20], ["low", "mid", "high"])

assert b(0).label == "low"
assert b(10).label == "mid"
assert b(20).label == "high"
assert b(-5).label == "low"

print(b.group([0, 5, 10, 19, 20, 99]))
# {'low': [0, 5], 'mid': [10, 19], 'high': [20, 99]}
```

The exported names are `Bucket` and `bucketer`. `bucketer(boundaries, labels=None)` returns a callable that maps a timestamp to a `Bucket` and exposes `.group(timestamps)`, `.boundaries`, and `.buckets`.

## Why this exists

Time-series aggregation often needs buckets that are not regular clock intervals: an early window, a middle window, and an open-ended tail. Building those with fixed-width arithmetic requires padding and sentinel values. This library instead takes the bucket starts directly, so the grouping rule is one explicit list.

The trade-off is that timestamps before the first boundary are clamped into the first bucket rather than rejected. That keeps the mapping total over all integers, which is convenient when input data may predate the configured range.

## Edge you will hit

A timestamp exactly on a boundary belongs to the bucket that starts there: buckets are half-open `[start, end)`. The final bucket is open-ended and absorbs every timestamp at or beyond the last boundary. Unlabeled buckets are keyed in `group()` by their start offset as a string, so mixing labeled and unlabeled buckets in one call is not supported.

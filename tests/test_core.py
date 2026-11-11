import unittest

from compact_time_bucket_lib import Bucket, bucketer


class BucketTests(unittest.TestCase):
    def test_contains_is_half_open(self):
        bucket = Bucket(10, 20, "a")
        self.assertTrue(bucket.contains(10))
        self.assertTrue(bucket.contains(19))
        self.assertFalse(bucket.contains(20))
        self.assertFalse(bucket.contains(9))

    def test_rejects_invalid_ranges(self):
        with self.assertRaises(ValueError):
            Bucket(5, 5)
        with self.assertRaises(ValueError):
            Bucket(5, 4)
        with self.assertRaises(ValueError):
            Bucket(-1, 4)

    def test_equality_and_repr(self):
        first = Bucket(0, 10, "x")
        second = Bucket(0, 10, "x")
        third = Bucket(0, 10, "y")
        self.assertEqual(first, second)
        self.assertNotEqual(first, third)
        self.assertIn("Bucket", repr(first))


class BucketerTests(unittest.TestCase):
    def test_boundaries_must_be_strictly_increasing(self):
        with self.assertRaises(ValueError):
            bucketer([0, 5, 5])
        with self.assertRaises(ValueError):
            bucketer([5, 0])
        with self.assertRaises(ValueError):
            bucketer([])

    def test_boundaries_must_be_non_negative(self):
        with self.assertRaises(ValueError):
            bucketer([-1, 5])

    def test_labels_must_match_boundaries(self):
        with self.assertRaises(ValueError):
            bucketer([0, 10], ["only-one"])

    def test_exact_boundary_goes_to_next_bucket(self):
        b = bucketer([0, 10, 20], ["first", "second", "third"])
        self.assertEqual(b(0).label, "first")
        self.assertEqual(b(10).label, "second")
        self.assertEqual(b(20).label, "third")

    def test_timestamp_before_first_boundary_clamps_to_first(self):
        b = bucketer([100, 200], ["early", "late"])
        self.assertEqual(b(0).label, "early")
        self.assertEqual(b(99).label, "early")
        self.assertEqual(b(100).label, "early")
        self.assertEqual(b(150).label, "early")
        self.assertEqual(b(200).label, "late")

    def test_final_bucket_is_open_ended(self):
        b = bucketer([0, 10])
        self.assertTrue(b(10).contains(10))
        self.assertTrue(b(10).contains(10**9))

    def test_group_uses_labels(self):
        b = bucketer([0, 10, 20], ["low", "mid", "high"])
        grouped = b.group([0, 5, 10, 19, 20, 99])
        self.assertEqual(grouped, {"low": [0, 5], "mid": [10, 19], "high": [20, 99]})

    def test_group_uses_start_offsets_when_unlabeled(self):
        b = bucketer([0, 10])
        grouped = b.group([0, 9, 10, 15])
        self.assertEqual(grouped, {"0": [0, 9], "10": [10, 15]})

    def test_non_integer_timestamp_raises(self):
        b = bucketer([0, 10])
        with self.assertRaises(TypeError):
            b(3.5)

    def test_buckets_property_exposes_intervals(self):
        b = bucketer([0, 10, 20], ["a", "b", "c"])
        self.assertEqual([bucket.start for bucket in b.buckets], [0, 10, 20])
        self.assertEqual([bucket.end for bucket in b.buckets], [10, 20, 1 << 62])

    def test_boundaries_property_is_immutable(self):
        b = bucketer([0, 10])
        self.assertEqual(b.boundaries, (0, 10))
        with self.assertRaises(TypeError):
            b.boundaries[0] = 5


if __name__ == "__main__":
    unittest.main()

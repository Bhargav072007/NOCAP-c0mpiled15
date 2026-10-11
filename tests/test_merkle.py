import unittest
from ledger.merkle import merkle_root


class MerkleTests(unittest.TestCase):
    def test_repeatable_and_non_mutating(self):
        hashes = ['0' * 64, '1' * 64, '2' * 64]
        before = hashes[:]
        self.assertEqual(merkle_root(hashes), merkle_root(hashes))
        self.assertEqual(hashes, before)

    def test_changed_hash_changes_root(self):
        self.assertNotEqual(merkle_root(['0' * 64, '1' * 64]),
                            merkle_root(['0' * 64, '2' * 64]))

    def test_empty(self):
        self.assertIsNone(merkle_root([]))

    def test_single_leaf_is_not_rehashed(self):
        self.assertEqual(merkle_root(['AB' * 32]), 'ab' * 32)

    def test_fixed_vectors(self):
        # Independently generated SHA-256 pair vectors; no call to the SUT
        # is used to calculate expectations.
        vectors = {
            2: '8878b15a7d6a3a4f464e8f9f42591dbc0cf4bedea0ec309003d2b2ee53655ef8',
            3: 'f59242779d0bc9cfb1f3decf078f0dd2e0a5797bad13a4451ed3a96ad0e4182f',
            5: 'ae34cc7349863b0540da9636267a42625d9ab7ea5be7a995550b66fdc0ab2ef2',
        }
        for count, expected in vectors.items():
            with self.subTest(count=count):
                self.assertEqual(merkle_root([str(i) * 64 for i in range(count)]), expected)

    def test_order_matters(self):
        self.assertNotEqual(merkle_root(['0' * 64, '1' * 64]),
                            merkle_root(['1' * 64, '0' * 64]))

    def test_invalid_hex_raises(self):
        with self.assertRaises(ValueError):
            merkle_root(['not hex'])

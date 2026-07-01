from django.test import SimpleTestCase

from skinconcerns.normalization import normalize_search_text, normalized_phrase_in_text


class NormalizeSearchTextTests(SimpleTestCase):
    def test_folds_accented_characters(self):
        self.assertEqual(normalize_search_text("rosácea"), "rosacea")
        self.assertEqual(normalize_search_text("Rosácea"), "rosacea")
        self.assertEqual(normalize_search_text("café au lait"), "cafe au lait")

    def test_preserves_ascii_normalization(self):
        self.assertEqual(normalize_search_text("  Zits!  "), "zits")


class NormalizedPhraseMatchingTests(SimpleTestCase):
    def test_matches_unnegated_phrases(self):
        self.assertTrue(
            normalized_phrase_in_text(
                "painful rash",
                "I have a painful rash on my arm.",
            )
        )
        self.assertTrue(
            normalized_phrase_in_text(
                "new changing spot",
                "I noticed a new changing spot near my cheek.",
            )
        )

    def test_ignores_negated_phrases(self):
        self.assertFalse(
            normalized_phrase_in_text("painful rash", "No painful rash right now.")
        )
        self.assertFalse(
            normalized_phrase_in_text(
                "bleeding mole",
                "This is not a bleeding mole.",
            )
        )
        self.assertFalse(
            normalized_phrase_in_text(
                "fever with rash",
                "No fever with rash today.",
            )
        )
        self.assertFalse(
            normalized_phrase_in_text(
                "painful rash",
                "I don't have a painful rash.",
            )
        )
        self.assertFalse(
            normalized_phrase_in_text(
                "fever with rash",
                "She doesn't have a fever with rash.",
            )
        )
        self.assertFalse(
            normalized_phrase_in_text(
                "painful rash",
                "No sign of painful rash right now.",
            )
        )
        self.assertFalse(
            normalized_phrase_in_text(
                "bleeding mole",
                "Not suffering from a bleeding mole.",
            )
        )

    def test_still_matches_positive_phrases_with_connectors(self):
        self.assertTrue(
            normalized_phrase_in_text(
                "painful rash",
                "I have a sign of painful rash on my arm.",
            )
        )
        self.assertTrue(
            normalized_phrase_in_text(
                "painful rash",
                "I do have a painful rash.",
            )
        )

    def test_still_avoids_substring_false_positives(self):
        self.assertFalse(
            normalized_phrase_in_text("open sores", "Please reopen sores clinic hours.")
        )

import unittest

from Preprocessing.lang_utils_chr import chr_mco_ipa


class CherokeeCaseTest(unittest.TestCase):
    def test_lowercase_mco_matches_uppercase(self):
        lowercase = "gadō ű:sdi?"
        uppercase = lowercase.upper()
        self.assertEqual(chr_mco_ipa(lowercase), chr_mco_ipa(uppercase))


if __name__ == "__main__":
    unittest.main()
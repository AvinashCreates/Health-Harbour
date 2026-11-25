import unittest

from loadtest import validate_local_target


class LoadTestTargetTests(unittest.TestCase):
    def test_accepts_loopback_origins(self):
        for target in (
            "http://localhost:8000",
            "http://127.0.0.1:8000/",
            "http://[::1]:8000",
        ):
            with self.subTest(target=target):
                self.assertEqual(validate_local_target(target), target.rstrip("/"))

    def test_rejects_non_loopback_hosts(self):
        for target in (
            "https://example.com",
            "http://192.168.1.10:8000",
            "http://localhost.example.com:8000",
        ):
            with self.subTest(target=target):
                with self.assertRaises(ValueError):
                    validate_local_target(target)

    def test_rejects_malformed_or_ambiguous_origins(self):
        for target in (
            "ftp://localhost:8000",
            "http://user:password@localhost:8000",
            "http://localhost:8000/api",
            "http://localhost:8000/?target=example.com",
            "http://localhost:8000/#fragment",
        ):
            with self.subTest(target=target):
                with self.assertRaises(ValueError):
                    validate_local_target(target)


if __name__ == "__main__":
    unittest.main()

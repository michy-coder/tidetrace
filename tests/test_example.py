import unittest
from unittest.mock import patch

from scripts.example import get_messages, main


class ExampleScriptTest(unittest.TestCase):
    def test_get_messages_returns_expected_messages(self) -> None:
        self.assertEqual(
            get_messages(),
            ["Hello, Codex!", "This is a practice script."],
        )

    def test_main_prints_messages(self) -> None:
        with patch("builtins.print") as mock_print:
            main()

        mock_print.assert_any_call("Hello, Codex!")
        mock_print.assert_any_call("This is a practice script.")
        self.assertEqual(mock_print.call_count, 2)


if __name__ == "__main__":
    unittest.main()

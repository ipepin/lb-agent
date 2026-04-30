import unittest

from app.utils.text_utils import cleanup_email_text, html_to_text


class TestTextUtils(unittest.TestCase):
    def test_html_to_text_removes_tags(self) -> None:
        value = "<html><body><p>Hello</p><div>World</div></body></html>"
        result = html_to_text(value)
        self.assertIn("Hello", result)
        self.assertIn("World", result)
        self.assertNotIn("<p>", result)

    def test_cleanup_email_text_removes_noise(self) -> None:
        value = (
            "Important update\n"
            "View in browser\n"
            "https://example.com/very/long/link/that/should/not/stay/in/clean/text\n"
            "Please reply tomorrow.\n"
            "Unsubscribe here\n"
        )
        result = cleanup_email_text(value)
        self.assertIn("Important update", result)
        self.assertIn("Please reply tomorrow.", result)
        self.assertNotIn("View in browser", result)
        self.assertNotIn("Unsubscribe", result)


if __name__ == "__main__":
    unittest.main()

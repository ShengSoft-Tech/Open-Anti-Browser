import unittest
from unittest.mock import patch

from backend.browser_manager import BrowserManager


class PlatformCapabilitiesTests(unittest.TestCase):
    def setUp(self):
        self.manager = BrowserManager()

    @patch("backend.browser_manager.sys.platform", "darwin")
    def test_darwin_capabilities(self):
        result = self.manager.get_platform_capabilities()

        self.assertEqual(result["platform"], "darwin")
        self.assertTrue(result["engines"]["chrome"]["available"])
        self.assertFalse(result["engines"]["firefox"]["available"])
        self.assertFalse(result["window"]["arrange"]["available"])
        self.assertIsInstance(result["window"]["arrange"]["reason"], str)
        self.assertTrue(result["window"]["arrange"]["reason"])
        self.assertFalse(result["window"]["sync"]["available"])
        self.assertIsInstance(result["window"]["sync"]["reason"], str)
        self.assertTrue(result["window"]["sync"]["reason"])

    @patch("backend.browser_manager.sys.platform", "win32")
    def test_win32_capabilities(self):
        result = self.manager.get_platform_capabilities()

        self.assertEqual(result["platform"], "win32")
        self.assertTrue(result["engines"]["chrome"]["available"])
        self.assertTrue(result["engines"]["firefox"]["available"])
        self.assertTrue(result["window"]["arrange"]["available"])
        self.assertIsNone(result["window"]["arrange"]["reason"])
        self.assertTrue(result["window"]["sync"]["available"])
        self.assertIsNone(result["window"]["sync"]["reason"])

    @patch("backend.browser_manager.sys.platform", "darwin")
    def test_bootstrap_includes_capabilities_key(self):
        result = self.manager.bootstrap()

        self.assertIn("capabilities", result)
        self.assertEqual(result["capabilities"], self.manager.get_platform_capabilities())


if __name__ == "__main__":
    unittest.main()

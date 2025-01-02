"""Test the session_data module."""

from unittest import TestCase

from simple_config_builder.gui_backend.session_data import SessionData


class SessionDataTest(TestCase):
    """Test the SessionData class."""

    def test_session_data(self):
        """Test the SessionData class."""
        session_data = SessionData()
        session_data.set("key", "value")
        self.assertEqual(session_data.get("key"), "value")
        session_data.delete("key")
        self.assertIsNone(session_data.get("key"))
        session_data.clear()
        self.assertEqual(session_data._session_data, {})

        session_data["key"] = "value"
        self.assertEqual(session_data["key"], "value")
        del session_data["key"]
        self.assertIsNone(session_data.get("key"))
        session_data.clear()
        self.assertEqual(session_data._session_data, {})

    def test_session_data_contains(self):
        """Test the __contains__ method."""
        session_data = SessionData()
        session_data.set("key", "value")
        self.assertTrue("key" in session_data)
        self.assertFalse("key2" in session_data)
        session_data.clear()
        self.assertFalse("key" in session_data)

    def test_session_data_len(self):
        """Test the __len__ method."""
        session_data = SessionData()
        session_data.set("key", "value")
        self.assertEqual(len(session_data), 1)
        session_data.clear()
        self.assertEqual(len(session_data), 0)

    def test_session_data_iter(self):
        """Test the __iter__ method."""
        session_data = SessionData()
        session_data.set("key", "value")
        session_data.set("key2", "value2")
        self.assertEqual(list(iter(session_data)), ["key", "key2"])
        session_data.clear()
        self.assertEqual(list(iter(session_data)), [])

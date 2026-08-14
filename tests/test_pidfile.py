import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "www-scanner", "cgi-bin"))

from scanlib.pidfile import read_pid, remove_pid, write_pid


class TestPidFile(unittest.TestCase):
    def setUp(self):
        fd, self.path = tempfile.mkstemp()
        os.close(fd)
        os.remove(self.path)  # start from "file doesn't exist"

    def tearDown(self):
        remove_pid(self.path)

    def test_write_then_read_round_trips(self):
        write_pid(self.path, 12345)
        self.assertEqual(read_pid(self.path), 12345)

    def test_read_missing_file_returns_none(self):
        self.assertIsNone(read_pid(self.path))

    def test_read_garbage_content_returns_none(self):
        with open(self.path, "w") as f:
            f.write("not-a-pid")
        self.assertIsNone(read_pid(self.path))

    def test_remove_missing_file_is_a_no_op(self):
        remove_pid(self.path)  # must not raise

    def test_remove_deletes_file(self):
        write_pid(self.path, 999)
        remove_pid(self.path)
        self.assertIsNone(read_pid(self.path))


if __name__ == "__main__":
    unittest.main()

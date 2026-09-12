"""Offline payload and space-safe launcher regressions, without running a JVM."""
import hashlib
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import toolchain


class ToolchainTests(unittest.TestCase):
    def test_missing_pointer_corrupt_and_valid_payload(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "tool with spaces.jar"
            expected = hashlib.sha256(b"payload").hexdigest()
            with patch.dict(toolchain.HASHES, {path: expected}):
                with self.assertRaisesRegex(RuntimeError, "Missing tool payload"):
                    toolchain.checked(path)
                path.write_text("version https://git-lfs.github.com/spec/v1\n")
                with self.assertRaisesRegex(RuntimeError, "Git LFS pointer"):
                    toolchain.checked(path)
                path.write_bytes(b"corrupt")
                with self.assertRaisesRegex(RuntimeError, "Checksum mismatch"):
                    toolchain.checked(path)
                path.write_bytes(b"payload")
                self.assertEqual(toolchain.checked(path), path)

    def test_java_paths_and_arguments_remain_single_arguments(self):
        jar = Path("/checkout with spaces/tla-bin/tla2tools.jar")
        with patch.object(toolchain, "JAR", jar), patch.object(toolchain, "checked"):
            command = toolchain.java_command("tlc", ["model with spaces.tla"], "/tmp with spaces")
        self.assertIn(str(jar), command)
        self.assertIn("-Djava.io.tmpdir=/tmp with spaces", command)
        self.assertEqual(command[-1], "model with spaces.tla")

    def test_tmpdir_is_retained(self):
        with tempfile.TemporaryDirectory(prefix="scratch with spaces ") as directory:
            with patch.dict(toolchain.os.environ, {"TMPDIR": directory}):
                self.assertEqual(toolchain.scratch_base(), Path(directory).resolve())


if __name__ == "__main__":
    unittest.main()

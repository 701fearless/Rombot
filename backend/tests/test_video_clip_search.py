import sys
import unittest
from pathlib import Path

from app.routers.video import _retrieval_python


class ClipSearchRuntimeTests(unittest.TestCase):
    def test_retrieval_uses_backend_python_environment(self) -> None:
        self.assertEqual(_retrieval_python(), Path(sys.executable).resolve())


if __name__ == "__main__":
    unittest.main()

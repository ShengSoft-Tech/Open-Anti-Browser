import unittest
from unittest.mock import MagicMock, patch

from backend.services import network


class KillProcessTreeGracefulTests(unittest.TestCase):
    @patch("backend.services.network.psutil.wait_procs")
    @patch("backend.services.network.psutil.Process")
    def test_sends_sigterm_before_sigkill(self, mock_process_cls, mock_wait_procs):
        parent = MagicMock()
        child = MagicMock()
        parent.children.return_value = [child]
        mock_process_cls.return_value = parent
        mock_wait_procs.return_value = ([parent, child], [])

        network.kill_process_tree(1234)

        parent.terminate.assert_called_once()
        child.terminate.assert_called_once()
        parent.kill.assert_not_called()
        child.kill.assert_not_called()

    @patch("backend.services.network.psutil.wait_procs")
    @patch("backend.services.network.psutil.Process")
    def test_sigkill_survivors_after_grace_period(self, mock_process_cls, mock_wait_procs):
        parent = MagicMock()
        mock_process_cls.return_value = parent
        parent.children.return_value = []
        mock_wait_procs.side_effect = [([], [parent]), ([parent], [])]

        network.kill_process_tree(1234)

        parent.terminate.assert_called_once()
        parent.kill.assert_called_once()


if __name__ == "__main__":
    unittest.main()

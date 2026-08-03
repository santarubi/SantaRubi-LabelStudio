import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

from scripts.project_signature import (
    compute_signature,
    current_git_version,
    load_build_info,
    needs_rebuild,
    save_build_info,
)


class ComputeSignatureTests(unittest.TestCase):
    def test_signature_is_deterministic(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "app.py").write_text("print('hello')", encoding="utf-8")

            self.assertEqual(compute_signature(root), compute_signature(root))

    def test_signature_changes_when_a_tracked_file_changes(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            file_path = root / "app.py"
            file_path.write_text("print('v1')", encoding="utf-8")
            before = compute_signature(root)

            file_path.write_text("print('v2')", encoding="utf-8")
            after = compute_signature(root)

            self.assertNotEqual(before, after)

    def test_signature_changes_when_a_new_tracked_file_is_added(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "app.py").write_text("print('v1')", encoding="utf-8")
            before = compute_signature(root)

            (root / "helper.py").write_text("print('new')", encoding="utf-8")
            after = compute_signature(root)

            self.assertNotEqual(before, after)

    def test_ignores_files_in_excluded_directories(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "app.py").write_text("print('v1')", encoding="utf-8")
            before = compute_signature(root)

            for excluded in ("__pycache__", "build", "dist", ".git", "venv"):
                nested = root / excluded / "nested"
                nested.mkdir(parents=True)
                (nested / "whatever.py").write_text("print('ignored')", encoding="utf-8")

            after = compute_signature(root)
            self.assertEqual(before, after)

    def test_ignores_untracked_extensions(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "app.py").write_text("print('v1')", encoding="utf-8")
            before = compute_signature(root)

            (root / "readme.md").write_text("documentação", encoding="utf-8")
            (root / "icon.png").write_bytes(b"\x89PNG")

            after = compute_signature(root)
            self.assertEqual(before, after)

    def test_tracks_spec_and_txt_files(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "app.py").write_text("print('v1')", encoding="utf-8")
            before = compute_signature(root)

            (root / "app.spec").write_text("spec content", encoding="utf-8")
            after_spec = compute_signature(root)
            self.assertNotEqual(before, after_spec)

            (root / "requirements.txt").write_text("openpyxl", encoding="utf-8")
            after_txt = compute_signature(root)
            self.assertNotEqual(after_spec, after_txt)


class NeedsRebuildTests(unittest.TestCase):
    def test_true_when_no_previous_build_info(self):
        with tempfile.TemporaryDirectory() as tmp:
            exe = Path(tmp) / "app.exe"
            exe.write_text("fake exe", encoding="utf-8")
            self.assertTrue(needs_rebuild(None, "abc123", exe))

    def test_false_when_signature_matches_and_exe_exists(self):
        with tempfile.TemporaryDirectory() as tmp:
            exe = Path(tmp) / "app.exe"
            exe.write_text("fake exe", encoding="utf-8")
            self.assertFalse(needs_rebuild({"signature": "abc123"}, "abc123", exe))

    def test_true_when_signature_differs(self):
        with tempfile.TemporaryDirectory() as tmp:
            exe = Path(tmp) / "app.exe"
            exe.write_text("fake exe", encoding="utf-8")
            self.assertTrue(needs_rebuild({"signature": "old"}, "new", exe))

    def test_true_when_exe_missing_even_if_signature_matches(self):
        """Ex.: o build anterior falhou e apagou dist/ — precisa rebuildar
        mesmo que nada tenha mudado desde então."""
        with tempfile.TemporaryDirectory() as tmp:
            exe = Path(tmp) / "does-not-exist.exe"
            self.assertTrue(needs_rebuild({"signature": "abc123"}, "abc123", exe))


class BuildInfoRoundTripTests(unittest.TestCase):
    def test_load_returns_none_when_file_missing(self):
        with tempfile.TemporaryDirectory() as tmp:
            self.assertIsNone(load_build_info(Path(tmp) / "missing.json"))

    def test_load_returns_none_for_corrupted_json(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "build_info.json"
            path.write_text("{not valid json", encoding="utf-8")
            self.assertIsNone(load_build_info(path))

    def test_save_then_load_round_trip(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "nested" / "build_info.json"
            info = {"version": "v3.0-stable", "built_at": "2026-07-23 21:00:00", "duration_seconds": 12.3, "signature": "abc"}

            save_build_info(path, info)
            loaded = load_build_info(path)

            self.assertEqual(loaded, info)


class CurrentGitVersionTests(unittest.TestCase):
    @patch("scripts.project_signature.subprocess.run")
    def test_returns_stripped_stdout_on_success(self, mock_run):
        mock_run.return_value = MagicMock(stdout="v3.0-stable-2-g9201af6\n")

        self.assertEqual(current_git_version(Path(".")), "v3.0-stable-2-g9201af6")

    @patch("scripts.project_signature.subprocess.run")
    def test_returns_fallback_when_git_is_not_available(self, mock_run):
        mock_run.side_effect = FileNotFoundError()

        self.assertEqual(current_git_version(Path(".")), "desconhecida")

    @patch("scripts.project_signature.subprocess.run")
    def test_returns_fallback_when_output_is_empty(self, mock_run):
        mock_run.return_value = MagicMock(stdout="")

        self.assertEqual(current_git_version(Path(".")), "desconhecida")


if __name__ == "__main__":
    unittest.main()

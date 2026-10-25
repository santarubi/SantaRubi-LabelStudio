import subprocess
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

from scripts.build_runner import CREATE_NO_WINDOW, run_build

PROJECT_ROOT = Path(__file__).resolve().parent.parent
BUILD_BAT_PATH = PROJECT_ROOT / "scripts" / "build.bat"


def make_fake_process(lines: list[str], returncode: int) -> MagicMock:
    process = MagicMock()
    process.stdout = iter(line + "\n" for line in lines)
    process.returncode = returncode
    process.wait.return_value = None
    return process


class RunBuildTests(unittest.TestCase):
    @patch("scripts.build_runner.subprocess.Popen")
    def test_success_returns_full_log_and_success_true(self, mock_popen):
        mock_popen.return_value = make_fake_process(["linha 1", "linha 2", "BUILD CONCLUIDO"], returncode=0)

        result = run_build(Path("build.bat"), Path("."))

        self.assertTrue(result.success)
        self.assertEqual(result.log, "linha 1\nlinha 2\nBUILD CONCLUIDO")
        self.assertGreaterEqual(result.duration_seconds, 0)

    @patch("scripts.build_runner.subprocess.Popen")
    def test_failure_returns_success_false(self, mock_popen):
        mock_popen.return_value = make_fake_process(["erro: modulo nao encontrado"], returncode=1)

        result = run_build(Path("build.bat"), Path("."))

        self.assertFalse(result.success)
        self.assertIn("erro", result.log)

    @patch("scripts.build_runner.subprocess.Popen")
    def test_calls_on_output_line_for_each_line(self, mock_popen):
        mock_popen.return_value = make_fake_process(["a", "b", "c"], returncode=0)
        received: list[str] = []

        run_build(Path("build.bat"), Path("."), on_output_line=received.append)

        self.assertEqual(received, ["a", "b", "c"])

    @patch("scripts.build_runner.subprocess.Popen")
    def test_runs_with_stdin_devnull_to_avoid_hanging_on_pause(self, mock_popen):
        """build.bat termina com `pause` — sem stdin=DEVNULL, rodar isso
        sem console interativo travaria o Launcher para sempre."""
        mock_popen.return_value = make_fake_process([], returncode=0)

        run_build(Path("build.bat"), Path("."))

        _args, kwargs = mock_popen.call_args
        self.assertEqual(kwargs.get("stdin"), subprocess.DEVNULL)

    @patch("scripts.build_runner.subprocess.Popen")
    def test_runs_build_script_via_cmd_in_the_given_directory(self, mock_popen):
        mock_popen.return_value = make_fake_process([], returncode=0)
        build_script = Path("scripts/build.bat")
        cwd = Path("/projeto")

        run_build(build_script, cwd)

        args, kwargs = mock_popen.call_args
        self.assertEqual(args[0], ["cmd", "/c", str(build_script)])
        self.assertEqual(kwargs.get("cwd"), cwd)

    @patch("scripts.build_runner.subprocess.Popen")
    def test_runs_with_create_no_window_so_no_cmd_window_ever_appears(self, mock_popen):
        mock_popen.return_value = make_fake_process([], returncode=0)

        run_build(Path("build.bat"), Path("."))

        _args, kwargs = mock_popen.call_args
        self.assertEqual(kwargs.get("creationflags"), CREATE_NO_WINDOW)

    def test_create_no_window_constant_matches_subprocess_module(self):
        """Confere que a constante realmente usada é a do subprocess (não
        um valor inventado) quando o módulo subprocess a expõe."""
        expected = getattr(subprocess, "CREATE_NO_WINDOW", 0)
        self.assertEqual(CREATE_NO_WINDOW, expected)


class BuildScriptDoesNotOpenDistFolderTests(unittest.TestCase):
    """scripts/build.bat não deve mais abrir o Explorador de Arquivos na
    pasta dist/ ao final de um build bem-sucedido."""

    def test_build_bat_does_not_start_the_dist_folder(self):
        content = BUILD_BAT_PATH.read_text(encoding="utf-8")
        self.assertNotIn('start "" dist', content)

    def test_build_bat_still_has_pause_for_manual_runs(self):
        """pause continua lá para quem roda o .bat manualmente com
        duplo-clique (o Launcher lida com isso via stdin=DEVNULL)."""
        content = BUILD_BAT_PATH.read_text(encoding="utf-8")
        self.assertIn("pause", content)


if __name__ == "__main__":
    unittest.main()

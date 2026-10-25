import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path

from PIL import Image

from app.version import APP_VERSION, VERSION, WINDOWS_VERSION
from scripts.release_metadata import (
    render_release_info,
    render_windows_version_info,
    sha256_file,
)
from ui.branding import APP_VERSION as BRANDING_VERSION
from ui.branding import ICON_FILENAME

PROJECT_ROOT = Path(__file__).resolve().parent.parent
APP_SPEC = PROJECT_ROOT / "Santa Rubi Label Studio.spec"
LAUNCHER_SPEC = PROJECT_ROOT / "Santa Rubi Launcher.spec"
STATIC_VERSION_INFO = PROJECT_ROOT / "assets" / "windows_version_info.txt"
BUILD_SCRIPT = PROJECT_ROOT / "scripts" / "build_release.py"
SMOKE_SCRIPT = PROJECT_ROOT / "scripts" / "smoke_release.py"
ICON_ASSET = PROJECT_ROOT / "assets" / "santa-rubi-app.ico"


class ProductVersionTests(unittest.TestCase):
    def test_candidate_version_is_1_2_0(self):
        self.assertEqual(VERSION, (1, 2, 0))
        self.assertEqual(APP_VERSION, "v1.2.0")
        self.assertEqual(WINDOWS_VERSION, (1, 2, 0, 0))

    def test_branding_uses_official_version_source(self):
        self.assertEqual(BRANDING_VERSION, APP_VERSION)

    def test_branding_uses_the_new_multiresolution_icon(self):
        self.assertEqual(ICON_FILENAME, "santa-rubi-app.ico")
        with Image.open(ICON_ASSET) as icon:
            required_sizes = {(16, 16), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)}
            self.assertTrue(required_sizes.issubset(icon.ico.sizes()))

    def test_windows_metadata_is_generated_from_official_version(self):
        metadata = render_windows_version_info(PROJECT_ROOT)
        self.assertIn("filevers=(1, 2, 0, 0)", metadata)
        self.assertIn("ProductVersion', 'v1.2.0'", metadata)
        self.assertIn("OriginalFilename', 'Santa Rubi Label Studio.exe'", metadata)

    def test_checked_in_windows_metadata_matches_generated_metadata(self):
        self.assertEqual(STATIC_VERSION_INFO.read_text(encoding="utf-8"), render_windows_version_info(PROJECT_ROOT))


class ReleaseSpecTests(unittest.TestCase):
    def test_application_release_is_one_file_without_upx(self):
        spec = APP_SPEC.read_text(encoding="utf-8")
        self.assertIn("exe = EXE(", spec)
        self.assertNotIn("COLLECT(", spec)
        self.assertIn("upx=False", spec)
        self.assertIn("excludes=['numpy', 'pandas']", spec)

    def test_application_release_embeds_only_required_project_asset(self):
        spec = APP_SPEC.read_text(encoding="utf-8")
        self.assertIn("santa-rubi-app.ico", spec)
        self.assertNotIn("config.json", spec)
        self.assertNotIn("print_log.txt", spec)
        self.assertNotIn("jueri_debug.log", spec)
        self.assertNotIn("Launcher", spec)

    def test_launcher_remains_a_separate_development_build(self):
        launcher_spec = LAUNCHER_SPEC.read_text(encoding="utf-8")
        self.assertIn("scripts' / 'launcher.py", launcher_spec)
        self.assertIn("name='Santa Rubi Launcher'", launcher_spec)
        self.assertIn("santa-rubi-app.ico", launcher_spec)

    def test_application_and_launcher_specs_use_the_same_icon(self):
        for spec_path in (APP_SPEC, LAUNCHER_SPEC):
            spec = spec_path.read_text(encoding="utf-8")
            self.assertIn("icon=str(icon_path)", spec)
            self.assertIn("santa-rubi-app.ico", spec)
            self.assertNotIn("santa-rubi.ico", spec)

    def test_specs_generate_windows_metadata_from_the_central_version_source(self):
        for spec_path in (APP_SPEC, LAUNCHER_SPEC):
            spec = spec_path.read_text(encoding="utf-8")
            self.assertIn("scripts' / 'release_metadata.py", spec)
            self.assertIn("write_windows_version_info", spec)

    def test_build_script_does_not_fall_back_to_previous_release_version(self):
        self.assertNotIn("v1.1.2", BUILD_SCRIPT.read_text(encoding="utf-8"))

    def test_release_output_is_isolated_in_versioned_directory(self):
        build_script = BUILD_SCRIPT.read_text(encoding="utf-8")
        smoke_script = SMOKE_SCRIPT.read_text(encoding="utf-8")
        self.assertIn('RELEASE_ROOT / str(load_version(PROJECT_ROOT)["APP_VERSION"])', build_script)
        self.assertIn('str(load_version(PROJECT_ROOT)["APP_VERSION"])', smoke_script)


class ReleaseInfoTests(unittest.TestCase):
    def test_release_info_contains_integrity_data_without_personal_configuration(self):
        with tempfile.TemporaryDirectory() as tmp:
            executable = Path(tmp) / "Santa Rubi Label Studio.exe"
            executable.write_bytes(b"release artifact")
            info = render_release_info(
                PROJECT_ROOT,
                executable,
                build_time=datetime(2026, 10, 4, 12, 0, tzinfo=timezone.utc),
                signed=False,
            )

            self.assertIn("Versão: v1.2.0", info)
            self.assertIn(f"SHA-256: {sha256_file(executable)}", info)
            self.assertIn("Arquitetura: Windows x64", info)
            self.assertIn("Não assinado (NotSigned)", info)
            self.assertNotIn("config.json", info)
            self.assertNotIn("token", info.lower())
            self.assertNotIn("G:\\", info)


if __name__ == "__main__":
    unittest.main()

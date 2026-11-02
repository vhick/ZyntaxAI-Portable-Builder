"""Local builder regression tests; no network required."""
import pathlib
import sys
import tempfile
import unittest
ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
from package import pe_details
from patch_upstream import replace_once

class BuilderTests(unittest.TestCase):
    def test_source_patch_must_fail_closed(self):
        with self.assertRaises(RuntimeError): replace_once('one one', 'one', 'two', 'unit')
        with self.assertRaises(RuntimeError): replace_once('one', 'missing', 'two', 'unit')
        self.assertEqual(replace_once('before', 'before', 'after', 'unit'), 'after')

    def test_batch_cannot_masquerade_as_exe(self):
        with tempfile.TemporaryDirectory() as d:
            file = pathlib.Path(d) / 'fake.exe'
            file.write_bytes(b'@echo off\r\necho hello')
            with self.assertRaises(ValueError): pe_details(file)

    def test_required_workflow_and_original_icon_generation(self):
        workflow = (ROOT / '.github/workflows/build-native.yml').read_text()
        cmake = (ROOT / 'launcher/CMakeLists.txt').read_text()
        self.assertIn('workflow_dispatch:', workflow)
        self.assertNotIn('schedule:', workflow)
        self.assertIn('pnpm tauri build --ci --no-bundle', workflow)
        self.assertIn('gh release create', workflow)
        self.assertIn('icon.rc', cmake)
        self.assertIn('ZyntaxAIPortable WIN32', cmake)
        self.assertIn('persist-credentials: false', workflow)

if __name__ == '__main__': unittest.main()

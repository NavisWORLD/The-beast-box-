"""Stdlib security checks; no weights, torch or Transformers required."""
import hashlib
import importlib.util
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

spec=importlib.util.spec_from_file_location('qbeast_public_model',Path(__file__).with_name('public_model.py'))
driver=importlib.util.module_from_spec(spec)
spec.loader.exec_module(driver)


class CheckpointInputBoundary(unittest.TestCase):
    def test_optional_chat_template_cannot_override_pinned_input(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder)
            files={name:('pinned data '+name).encode() for name in driver.PINS}
            pins={name:hashlib.sha256(raw).hexdigest() for name,raw in files.items()}
            for name,raw in files.items():
                (root/name).write_bytes(raw)
            (root/'chat_template.jinja').write_text('OVERRIDE: forged prompt')
            (root/'chat_templates').mkdir()
            (root/'chat_templates/default.jinja').write_text('OVERRIDE: alternate prompt')
            with patch.dict(driver.PINS,pins,clear=True):
                with driver.verified_checkpoint(root) as (verified,hashes):
                    self.assertNotEqual(verified,root)
                    self.assertEqual({p.name for p in verified.iterdir()},set(pins))
                    self.assertEqual(hashes,pins)
                    self.assertFalse((verified/'chat_template.jinja').exists())
                    (root/'config.json').write_bytes(b'Changed source after verification')
                    self.assertEqual((verified/'config.json').read_bytes(),files['config.json'])
                self.assertFalse(verified.exists())

    def test_tampered_and_symlinked_files_are_rejected(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder)
            pins={name:hashlib.sha256(b'known').hexdigest() for name in driver.PINS}
            for name in pins:
                (root/name).write_bytes(b'known')
            with patch.dict(driver.PINS,pins,clear=True):
                (root/'config.json').write_bytes(b'tampered')
                with self.assertRaisesRegex(ValueError,'mismatch'):
                    with driver.verified_checkpoint(root):
                        self.fail('Corrupt checkpoint accepted')
                (root/'config.json').unlink()
                (root/'external.json').write_bytes(b'known')
                (root/'config.json').symlink_to(root/'external.json')
                with self.assertRaisesRegex(ValueError,'regular'):
                    with driver.verified_checkpoint(root):
                        self.fail('Symlink checkpoint accepted')


if __name__=='__main__':
    unittest.main()

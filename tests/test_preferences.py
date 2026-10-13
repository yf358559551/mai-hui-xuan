import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

SCRIPT = Path(__file__).resolve().parents[1] / "skills/mai-hui-xuan/scripts/preferences.py"


class PreferenceTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.env = dict(os.environ, MAI_HUI_XUAN_HOME=self.temp.name)
        self.path = Path(self.temp.name) / "preferences.json"

    def call(self, *args):
        return subprocess.run([sys.executable, str(SCRIPT), *args], env=self.env, text=True, capture_output=True)

    def test_store_merge_remove_and_clear(self):
        self.assertEqual(self.call("set", "--json", '{"likes":["辣"],"budget_yuan":30}').returncode, 0)
        self.assertEqual(self.call("set", "--json", '{"avoid":["含糖饮料"]}').returncode, 0)
        self.assertEqual(json.loads(self.call("show").stdout)["likes"], ["辣"])
        self.assertEqual(self.path.stat().st_mode & 0o777, 0o600)
        self.assertEqual(self.call("unset", "budget_yuan").returncode, 0)
        self.assertNotIn("budget_yuan", json.loads(self.call("show").stdout))
        self.assertEqual(self.call("clear").returncode, 0)
        self.assertFalse(self.path.exists())

    def test_invalid_update_preserves_existing(self):
        self.call("set", "--json", '{"budget_yuan":30}')
        before = self.path.read_bytes()
        for payload in ('{"token":"secret"}', '{"budget_yuan":true}', '{"budget_yuan":NaN}', '{"low_calorie":"yes"}'):
            self.assertEqual(self.call("set", "--json", payload).returncode, 2)
            self.assertEqual(self.path.read_bytes(), before)

    def test_show_does_not_create_file(self):
        self.assertEqual(json.loads(self.call("show").stdout), {})
        self.assertFalse(self.path.exists())


if __name__ == "__main__":
    unittest.main()

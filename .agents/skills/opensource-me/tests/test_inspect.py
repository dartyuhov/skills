import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "inspect-repo.py"


class InspectTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="inspect tests ")
        self.addCleanup(self.temp.cleanup)
        self.repo = Path(self.temp.name) / "repo with spaces"
        self.repo.mkdir()
        self.git("init", "-b", "main")
        self.git("config", "user.name", "Fixture")
        self.git("config", "user.email", "fixture@example.invalid")

    def git(self, *args):
        return subprocess.run(["git", "-C", str(self.repo), *args], check=True,
                              capture_output=True, text=True).stdout

    def inspect(self, path=None, env=None):
        result = subprocess.run([sys.executable, str(SCRIPT), str(path or self.repo)],
                                capture_output=True, text=True, env=env)
        self.assertEqual(result.stderr, "")
        return result.returncode, json.loads(result.stdout)

    def test_inventory_distinguishes_files_without_reading_sensitive_contents(self):
        for name, text in {"README.md": "PRIVATE DOCUMENT CONTENT", "package.json": "{}",
                           ".gitignore": "secret.env\n", "secret.env": "SECRET_VALUE",
                           "new file.txt": "untracked"}.items():
            (self.repo / name).write_text(text)
        self.git("add", "README.md", "package.json", ".gitignore")
        self.git("commit", "-m", "sensitive commit subject")
        (self.repo / "README.md").write_text("changed")
        before = self.git("status", "--porcelain=v1", "--ignored")
        code, data = self.inspect()
        self.assertEqual(code, 0)
        self.assertTrue(data["ok"])
        self.assertEqual(data["repo_root"], str(self.repo.resolve()))
        self.assertIn("README.md", data["files"]["tracked"])
        self.assertIn("new file.txt", data["files"]["untracked"])
        self.assertIn("secret.env", data["files"]["ignored"])
        self.assertIn("node", data["stack"])
        self.assertIn("README.md", data["key_files"]["docs"])
        self.assertEqual(data["history"]["commit_count"], 1)
        self.assertTrue(data["status"]["dirty"])
        self.assertEqual(before, self.git("status", "--porcelain=v1", "--ignored"))
        for secret in ("SECRET_VALUE", "PRIVATE DOCUMENT CONTENT", "sensitive commit subject"):
            self.assertNotIn(secret, json.dumps(data))

    def test_linked_worktree_subdirectory_and_unborn_repository(self):
        code, empty = self.inspect()
        self.assertEqual(code, 0)
        self.assertEqual(empty["history"]["commit_count"], 0)
        (self.repo / "README.md").write_text("hello")
        (self.repo / "nested").mkdir()
        (self.repo / "nested" / "file.txt").write_text("hello")
        self.git("add", ".")
        self.git("commit", "-m", "initial")
        linked = Path(self.temp.name) / "linked tree"
        self.git("worktree", "add", "-b", "linked", str(linked))
        code, data = self.inspect(linked / "nested")
        self.assertEqual(code, 0)
        self.assertEqual(data["repo_root"], str(linked.resolve()))
        self.assertEqual(data["files"]["tracked"], ["README.md", "nested/file.txt"])
        self.assertNotEqual(data["worktree"]["git_dir"], data["worktree"]["common_dir"])

    def test_failures_are_json_and_do_not_echo_subprocess_errors(self):
        for path, env in ((Path(self.temp.name), None),
                          (Path(self.temp.name) / "absent", None),
                          (self.repo, dict(os.environ, PATH=""))):
            with self.subTest(path=path, env=env):
                code, data = self.inspect(path, env)
                self.assertNotEqual(code, 0)
                self.assertFalse(data["ok"])
                self.assertNotIn("fatal:", data["error"])

    def test_inventory_preserves_unusual_paths_and_reports_workflows_and_config(self):
        (self.repo / ".github" / "workflows").mkdir(parents=True)
        (self.repo / ".github" / "workflows" / "ci.yml").write_text("private config")
        (self.repo / "Cargo.toml").write_text("private manifest")
        (self.repo / 'old "name\n.txt').write_text("contents")
        self.git("add", ".")
        self.git("commit", "-m", "initial")
        self.git("mv", 'old "name\n.txt', "new name.txt")
        code, data = self.inspect()
        self.assertEqual(code, 0)
        self.assertEqual(data["key_files"]["workflows"], [".github/workflows/ci.yml"])
        self.assertIn("Cargo.toml", data["key_files"]["config"])
        self.assertIn("rust", data["stack"])
        self.assertEqual(data["status"]["entries"], [{"code": "R ", "path": "new name.txt",
                          "original_path": 'old "name\n.txt'}])


if __name__ == "__main__":
    unittest.main()

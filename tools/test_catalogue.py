"""One bad source must not hold back the rest of the catalogue (plugins#5).

Two parts:
- build-index.py with one unreachable and one good source writes the good one's new version.
- catalogue.yml, read as GitHub runs it: on push and schedule a failed rebuild still reaches
  Publish, and the run still ends red so the bad source is seen. On a pull request a problem
  fails the run and nothing is published.

Run: python tools/test_catalogue.py   (needs PyYAML for the workflow part)
"""
from __future__ import annotations

import importlib.util
import io
import json
import pathlib
import re
import sys
import tempfile
import unittest
import urllib.error
from contextlib import redirect_stderr, redirect_stdout

HERE = pathlib.Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location("build_index", HERE / "build-index.py")
bi = importlib.util.module_from_spec(spec)
sys.modules["build_index"] = bi
spec.loader.exec_module(bi)

PLUGIN_ID = "01HZX0000000000000000000AB"
SHA = "0" * 64


class BadSourceIsSkipped(unittest.TestCase):
    def test_good_source_still_lands_in_the_index(self):
        tmp = pathlib.Path(tempfile.mkdtemp())
        (tmp / "sources.json").write_text(json.dumps({"sources": [
            {"name": "down", "url": "https://down.example.test/index.json"},
            {"name": "good", "url": "https://good.example.test/index.json"},
        ]}), encoding="utf-8")
        (tmp / "index.json").write_text(json.dumps({"plugins": [{
            "id": PLUGIN_ID, "name": "Example", "versions": [
                {"version": "1.0.0", "downloadUrl": "https://good.example.test/1.0.0.zip", "checksum": SHA}]}]}),
            encoding="utf-8")
        good = {"plugins": [{"id": PLUGIN_ID, "name": "Example", "description": "d", "author": "a",
                             "versions": [{"version": "1.1.0", "downloadUrl": "https://good.example.test/1.1.0.zip",
                                           "checksum": SHA}]}]}

        def fetch(url):
            if "down" in url:
                raise urllib.error.URLError("unreachable")
            return good

        bi.SOURCES, bi.INDEX, bi.fetch = tmp / "sources.json", tmp / "index.json", fetch
        argv, sys.argv = sys.argv, ["build-index.py"]
        try:
            with redirect_stdout(io.StringIO()), redirect_stderr(io.StringIO()):
                code = bi.main()
        finally:
            sys.argv = argv
        versions = [v["version"] for v in json.loads((tmp / "index.json").read_text())["plugins"][0]["versions"]]
        self.assertEqual(code, 1, "the bad source is still reported")
        self.assertEqual(versions, ["1.1.0", "1.0.0"])


def run_job(event: str, rebuild_exit: int):
    """Which steps run, and how the job ends, for the real catalogue.yml (GitHub's rules)."""
    import yaml
    wf = yaml.safe_load((HERE.parent / ".github/workflows/catalogue.yml").read_text(encoding="utf-8"))
    steps = wf["jobs"]["catalogue"]["steps"]
    outcomes: dict[str, str] = {}
    ran: list[str] = []
    job_failed = False
    for step in steps:
        cond = str(step.get("if", "success()"))
        expr = cond.replace("github.event_name", repr(event)).replace("&&", " and ").replace("||", " or ")
        expr = re.sub(r"steps\.([\w-]+)\.outcome", lambda m: repr(outcomes.get(m.group(1), "")), expr)
        expr = expr.replace("success()", repr(not job_failed)).replace("failure()", repr(job_failed))
        expr = expr.replace("always()", "True").replace("!=", "!= ").replace("!", " not ").replace("not =", "!=")
        if "success()" not in cond and "always()" not in cond and "failure()" not in cond and job_failed:
            run = False
        else:
            run = eval(expr, {}, {})
        if not run:
            continue
        name = step.get("name", step.get("uses", "?"))
        ran.append(name)
        script = step.get("run", "")
        failed = (("build-index.py" in script) and rebuild_exit != 0) or bool(re.search(r"(^|\n)\s*exit 1\s*$", script))
        if step.get("id"):
            outcomes[step["id"]] = "failure" if failed else "success"
        if failed and not step.get("continue-on-error"):
            job_failed = True
    return ran, job_failed


class WorkflowPublishesPastABadSource(unittest.TestCase):
    def test_push_with_a_bad_source_publishes_and_ends_red(self):
        for event in ("push", "schedule"):
            ran, failed = run_job(event, rebuild_exit=1)
            self.assertIn("Publish", ran, event)
            self.assertTrue(failed, f"{event}: the bad source must still turn the run red")

    def test_push_with_clean_sources_publishes_and_ends_green(self):
        ran, failed = run_job("push", rebuild_exit=0)
        self.assertIn("Publish", ran)
        self.assertFalse(failed)

    def test_pull_request_with_a_problem_fails_and_publishes_nothing(self):
        ran, failed = run_job("pull_request", rebuild_exit=1)
        self.assertNotIn("Publish", ran)
        self.assertTrue(failed)


if __name__ == "__main__":
    unittest.main()

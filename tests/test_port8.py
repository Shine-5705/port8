import json, os, shutil, subprocess, sys, tempfile, unittest
from port8.scan import scan, strip_c_comments, apply_fixes

HERE = os.path.dirname(__file__)
LEGACY = os.path.join(HERE, "fixtures", "legacy-driver")
CLEAN = os.path.join(HERE, "fixtures", "clean")


class Port8(unittest.TestCase):
    def test_legacy_findings(self):
        f, n = scan(LEGACY)
        self.assertEqual(n, 3)
        ids = sorted({x["rule"] for x in f})
        self.assertEqual(ids, ["Q8001", "Q8002", "Q8004", "Q8006", "Q8007", "Q8011", "Q8015", "Q8101", "Q8102", "Q8103"])

    def test_comments_and_strings_ignored(self):
        f, _ = scan(LEGACY)
        q1 = [x for x in f if x["rule"] == "Q8001"]
        self.assertEqual(len(q1), 1)            # not the comment on line 15, not the printf string
        self.assertEqual(q1[0]["line"], 31)

    def test_clean_8_0_code_passes(self):
        f, n = scan(CLEAN)
        self.assertEqual((f, n), ([], 1))

    def test_strip_keeps_positions(self):
        s = 'a(); /* x\ny */ b("InterruptAttach(");\n'
        t = strip_c_comments(s)
        self.assertEqual(len(s), len(t)); self.assertEqual(s.count("\n"), t.count("\n"))
        self.assertNotIn("InterruptAttach", t)

    def test_fix_is_safe_and_idempotent(self):
        d = tempfile.mkdtemp()
        p = os.path.join(d, "a.c")
        open(p, "w").write("#include <sys/neutrino.h>\nint rcvid;\nint chid, rcvid2;\nx = PROCMGR_AID_INTERRUPTEVENT;\n")
        apply_fixes(d); out = open(p).read()
        self.assertIn("rcvid_t rcvid;", out)
        self.assertIn("int chid, rcvid2;", out)        # declaration lists are reported, never rewritten
        self.assertIn("PROCMGR_AID_INTERRUPT;", out)
        self.assertIn("#ifndef __RCVID_T_SIZE", out)
        apply_fixes(d); self.assertEqual(out, open(p).read())
        shutil.rmtree(d)

    def test_cli_sarif_and_exit_code(self):
        r = subprocess.run([sys.executable, "-m", "port8", LEGACY, "--format", "sarif"], capture_output=True, text=True,
                           cwd=os.path.dirname(HERE))
        self.assertEqual(r.returncode, 1)
        s = json.loads(r.stdout)
        self.assertEqual(s["version"], "2.1.0")
        self.assertTrue(all(res["ruleId"].startswith("Q8") for res in s["runs"][0]["results"]))
        r2 = subprocess.run([sys.executable, "-m", "port8", CLEAN], capture_output=True, text=True, cwd=os.path.dirname(HERE))
        self.assertEqual(r2.returncode, 0)


if __name__ == "__main__":
    unittest.main()

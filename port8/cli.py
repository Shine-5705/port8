import argparse, json, sys
from . import __version__
from .scan import scan, apply_fixes
from .rules import RULES, SHARED_RULE

COL = {"error": "\033[31m", "warning": "\033[33m", "info": "\033[36m"}
RESET, DIM, BOLD = "\033[0m", "\033[2m", "\033[1m"


def sarif(findings):
    rules = RULES + [SHARED_RULE]
    level = {"error": "error", "warning": "warning", "info": "note"}
    return {"$schema": "https://json.schemastore.org/sarif-2.1.0.json", "version": "2.1.0",
            "runs": [{"tool": {"driver": {"name": "port8", "version": __version__, "informationUri": "https://github.com/Shine-5705/port8",
                                          "rules": [{"id": r.id, "shortDescription": {"text": r.title}, "helpUri": r.doc,
                                                     "help": {"text": r.advice}} for r in rules]}},
                      "results": [{"ruleId": f["rule"], "level": level[f["severity"]], "message": {"text": f"{f['title']}. {f['advice']}"},
                                   "locations": [{"physicalLocation": {"artifactLocation": {"uri": f["path"]},
                                                                       "region": {"startLine": f["line"], "startColumn": f["col"]}}}]}
                                  for f in findings]}]}


def markdown(findings, scanned):
    c = {s: sum(f["severity"] == s for f in findings) for s in ("error", "warning", "info")}
    out = [f"# port8 report: QNX SDP 7.1 -> 8.0", "", f"Scanned {scanned} files. {c['error']} errors, {c['warning']} warnings, {c['info']} notes.", "",
           "| Severity | Rule | Location | Finding | Fix |", "| --- | --- | --- | --- | --- |"]
    for f in findings:
        out.append(f"| {f['severity']} | [{f['rule']}]({f['doc']}) | `{f['path']}:{f['line']}` | {f['title']} | {f['advice']} |")
    return "\n".join(out) + "\n"


def main(argv=None):
    ap = argparse.ArgumentParser(prog="port8", description="Find what breaks when you move QNX SDP 7.1 code to QNX SDP 8.0.")
    ap.add_argument("path", nargs="?", default=".")
    ap.add_argument("--format", choices=["text", "json", "sarif", "md"], default="text")
    ap.add_argument("--fix", action="store_true", help="apply the safe automatic fixes (Q8002, Q8007) in place")
    ap.add_argument("--fail-on", choices=["error", "warning", "never"], default="error")
    ap.add_argument("--rules", action="store_true", help="list rules and their QNX 8.0 doc sources")
    ap.add_argument("--version", action="version", version=f"port8 {__version__}")
    a = ap.parse_args(argv)
    color = sys.stdout.isatty()

    if a.rules:
        for r in RULES + [SHARED_RULE]:
            print(f"{r.id}  {r.severity:<7}  {r.title}\n        {r.doc}")
        return 0
    if a.fix:
        for p in apply_fixes(a.path):
            print(f"fixed {p}")
    findings, scanned = scan(a.path)
    if a.format == "json": print(json.dumps(findings, indent=2))
    elif a.format == "sarif": print(json.dumps(sarif(findings), indent=2))
    elif a.format == "md": print(markdown(findings, scanned), end="")
    else:
        for f in findings:
            s = f["severity"]; c0 = COL[s] if color else ""; r0 = RESET if color else ""
            d0 = DIM if color else ""; b0 = BOLD if color else ""
            print(f"{b0}{f['path']}:{f['line']}:{f['col']}{r0}  {c0}{s}{r0}  {f['rule']}  {f['title']}")
            print(f"    {d0}{f['snippet']}{r0}")
            print(f"    fix: {f['advice']}{'  [auto-fixable: --fix]' if f['fixable'] else ''}")
            print(f"    {d0}{f['doc']}{r0}")
        c = {s: sum(f["severity"] == s for f in findings) for s in ("error", "warning", "info")}
        print(f"\nport8: scanned {scanned} files: {c['error']} errors, {c['warning']} warnings, {c['info']} notes")
    if a.fail_on == "never": return 0
    bad = [f for f in findings if f["severity"] == "error" or (a.fail_on == "warning" and f["severity"] == "warning")]
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())

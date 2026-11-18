import os, re
from .rules import RULES, SHARED_RULE, SHM_RE, DEFAULT_SYNC_RE, SHARED_RE, C_EXT, BUILD_EXT, MAKE_NAMES

SEV_ORDER = {"error": 0, "warning": 1, "info": 2}


def strip_c_comments(src):
    """Blank out comments and string literals but keep line/column positions."""
    out, i, n = [], 0, len(src)
    while i < n:
        c = src[i]
        if src.startswith("//", i):
            j = src.find("\n", i); j = n if j < 0 else j
            out.append(" " * (j - i)); i = j
        elif src.startswith("/*", i):
            j = src.find("*/", i + 2); j = n if j < 0 else j + 2
            out.append(re.sub(r"[^\n]", " ", src[i:j])); i = j
        elif c == '"':
            j = i + 1
            while j < n and src[j] != '"' and src[j] != "\n":
                j += 2 if src[j] == "\\" else 1
            out.append('"' + " " * (min(j, n) - i - 1)); i = j
        else:
            out.append(c); i += 1
    return "".join(out)


def kind_of(path):
    base = os.path.basename(path)
    if path.endswith(C_EXT): return "c"
    if path.endswith(BUILD_EXT): return "buildfile"
    if base in MAKE_NAMES or base.endswith(".mk"): return "build"
    return None


def scan_text(path, text, kind):
    findings = []
    code = strip_c_comments(text) if kind == "c" else re.sub(r"#[^\n]*", lambda m: " " * len(m.group()), text)
    lines = code.split("\n"); raw = text.split("\n")
    for rule in RULES:
        if rule.applies != kind and not (rule.applies == "build" and kind == "buildfile"):
            continue
        for ln, line in enumerate(lines, 1):
            for m in rule.pattern.finditer(line):
                findings.append({"rule": rule.id, "severity": rule.severity, "title": rule.title, "path": path,
                                 "line": ln, "col": m.start() + 1, "snippet": raw[ln - 1].strip(), "advice": rule.advice,
                                 "doc": rule.doc, "fixable": bool(rule.fix and re.search(rule.fix[0], line))})
                break
    if kind == "c" and SHM_RE.search(code) and not SHARED_RE.search(code):
        for ln, line in enumerate(lines, 1):
            if DEFAULT_SYNC_RE.search(line):
                r = SHARED_RULE
                findings.append({"rule": r.id, "severity": r.severity, "title": r.title, "path": path, "line": ln,
                                 "col": 1, "snippet": raw[ln - 1].strip(), "advice": r.advice, "doc": r.doc, "fixable": False})
    return findings


def iter_files(root):
    if os.path.isfile(root):
        yield root; return
    for d, dirs, files in os.walk(root):
        dirs[:] = [x for x in dirs if not x.startswith(".") and x not in ("node_modules", "build", "out")]
        for f in sorted(files):
            yield os.path.join(d, f)


def scan(root):
    findings, scanned = [], 0
    for p in iter_files(root):
        k = kind_of(p)
        if not k: continue
        scanned += 1
        with open(p, encoding="utf-8", errors="replace") as fh:
            findings += scan_text(os.path.relpath(p, root if os.path.isdir(root) else os.path.dirname(root) or "."), fh.read(), k)
    findings.sort(key=lambda f: (SEV_ORDER[f["severity"]], f["path"], f["line"]))
    return findings, scanned


def apply_fixes(root):
    from .rules import RULES
    changed = []
    for p in iter_files(root):
        if kind_of(p) != "c": continue
        src = open(p, encoding="utf-8").read(); new = src
        for r in RULES:
            if r.fix: new = re.sub(r.fix[0], r.fix[1], new)
        if new != src:
            if "rcvid_t" in new and "__RCVID_T_SIZE" not in new:
                guard = "#ifndef __RCVID_T_SIZE\ntypedef int rcvid_t; /* QNX 7.1 compatibility, added by port8 */\n#endif\n"
                incl = list(re.finditer(r"^#include[^\n]*\n", new, re.M))
                pos = incl[-1].end() if incl else 0
                new = new[:pos] + guard + new[pos:]
            open(p, "w", encoding="utf-8").write(new); changed.append(p)
    return changed

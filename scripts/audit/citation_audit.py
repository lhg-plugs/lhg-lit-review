#!/usr/bin/env python3
"""lhg-lit-review 确定性引用审计：10 条规则，零第三方依赖。

扫描目标目录的 Markdown 稿件，检查文内引用与文末参考文献的对应关系、
GB/T 7714 著录完整性与引用制一致性；输出 JSON 与人类可读报告；
有 blocker 时以 exit code 2 退出（供 hooks 与 CI 使用）。

用法：
    python3 citation_audit.py --target <目录> [--format json|text] [--fail-on blocker|warning|nit]

规则文案均为本项目原创（GB/T 7714 / APA 的格式事实属于公共知识，
检测规则为独立实现；未复制任何第三方原文案与代码）。
"""

import argparse
import json
import os
import re
import sys

VERSION = "1.0.0"
TOOL = "lhg-lit-review/citation-audit"

SKIP_DIRS = {
    "node_modules", ".git", "__pycache__", "dist", "build", ".venv",
}
SCAN_EXTS = {".md", ".markdown"}

REFS_HEADING_RE = re.compile(r"^#{1,4}\s*(参考文献|References)\b")
ENTRY_RE = re.compile(r"^\s*\[(\d+)\]\s*(.+)$")
NUMCITE_RE = re.compile(r"\[(\d+)\]")
AUTHORYEAR_CN_RE = re.compile(r"[\u4e00-\u9fa5]{2,4}，\s*(?:19|20)\d{2}")
AUTHORYEAR_EN_RE = re.compile(r"\([A-Za-z][A-Za-z\-]+,?\s+(?:19|20)\d{2}\)")
YEAR_RE = re.compile(r"(?:19|20)\d{2}")
TYPEID_RE = re.compile(r"\[(?:J|M|D|N|C|R|A|Z|EB/OL|J/OL|M/OL)\]")
AUTHOR_CN_RE = re.compile(r"^[\u4e00-\u9fa5·]{2,8}(?:[，,、][\u4e00-\u9fa5·]{2,8})*")
AUTHOR_CN_FULL = re.compile(r"^[\u4e00-\u9fa5·]{2,4}(?:[，,、][\u4e00-\u9fa5·]{2,4})*(?:[，,]等|、等)?$")
AUTHOR_EN_FULL = re.compile(r"^[A-Z][A-Za-z\-]+(?:\s+[A-Z]\.?)?(?:\s*,\s*[A-Z][A-Za-z\-]+(?:\s+[A-Z]\.?)?)*(?:\s+et al\.?)?$")
AUTHOR_EN_RE = re.compile(r"^[A-Z][A-Za-z\-]+(?:\s+[A-Z]\.?)?(?:\s*,\s*[A-Z][A-Za-z\-]+(?:\s+[A-Z]\.?)?)*")


class Finding:
    __slots__ = ("rule_id", "severity", "category", "title", "file", "line", "snippet", "detail")

    def __init__(self, rule_id, severity, category, title, file, line, snippet, detail):
        self.rule_id = rule_id
        self.severity = severity
        self.category = category
        self.title = title
        self.file = file
        self.line = line
        self.snippet = snippet
        self.detail = detail

    def to_dict(self):
        return {
            "rule_id": self.rule_id, "severity": self.severity,
            "category": self.category, "title": self.title,
            "file": self.file, "line": self.line,
            "snippet": self.snippet, "detail": self.detail,
        }


def collect_files(target):
    out = []
    for root, dirs, files in os.walk(target):
        dirs[:] = [d for d in dirs if d not in SKIP_DIRS]
        for f in files:
            _, ext = os.path.splitext(f)
            if ext.lower() in SCAN_EXTS:
                out.append(os.path.join(root, f))
    return sorted(out)


def read_text(path):
    try:
        with open(path, "r", encoding="utf-8", errors="replace") as fh:
            return fh.read()
    except OSError:
        return ""


def split_body_refs(lines):
    """切分正文与参考文献节。返回 (body_lines, [(entry_no, entry_text, line_no)])。"""
    ref_start = None
    for i, ln in enumerate(lines):
        if REFS_HEADING_RE.match(ln.strip()):
            ref_start = i
            break
    if ref_start is None:
        return lines, None
    entries = []
    for i in range(ref_start + 1, len(lines)):
        m = ENTRY_RE.match(lines[i])
        if m:
            entries.append((int(m.group(1)), m.group(2).strip(), i + 1))
    return lines[:ref_start], entries


def cited_numbers(body_lines):
    """正文中的编号引用 -> {编号: 首现行号}。"""
    out = {}
    for i, ln in enumerate(body_lines):
        for m in NUMCITE_RE.finditer(ln):
            n = int(m.group(1))
            if n not in out:
                out[n] = i + 1
    return out


def entry_title(entry_text):
    """粗提标题：取文献类型标识之前、最后一个句号/．之后的部分。"""
    m = TYPEID_RE.search(entry_text)
    if not m:
        return ""
    before = entry_text[:m.start()]
    parts = re.split(r"[．.]", before)
    title = parts[-1] if parts else ""
    title = re.sub(r"[\s，,、；:：\-─…《》\"“”'']+", "", title)
    return title


# ---------------------------------------------------------------- 规则定义

RULES = []
_RULE_BY_ID = {}


def rule(rule_id, severity, category, title, detail):
    def deco(fn):
        r = {"id": rule_id, "severity": severity, "category": category,
             "title": title, "detail": detail}
        _RULE_BY_ID[rule_id] = r
        r["check"] = fn
        RULES.append(r)
        return fn
    return deco


def _mk(rule_id, path, line, snippet):
    r = _RULE_BY_ID[rule_id]
    return Finding(r["id"], r["severity"], r["category"], r["title"],
                   path, line, snippet[:160], r["detail"])


@rule("CITE-001", "blocker", "对应关系", "孤儿引用",
      "文内引用编号在文末参考文献中没有对应条目。补条目或删除该引用，不许留悬空编号。")
def r_cite_001(lines, text, path, ctx):
    body, entries = ctx["parsed"]
    if entries is None:
        if cited_numbers(body):
            return [_mk("CITE-001", path, 1, "未找到参考文献节，无法核对文内引用编号")]
        return []
    have = {n for n, _, _ in entries}
    return [_mk("CITE-001", path, ln, "文内引用 [%d] 无对应条目" % n)
            for n, ln in sorted(cited_numbers(body).items()) if n not in have]


@rule("CITE-002", "blocker", "对应关系", "僵尸条目",
      "文末参考文献条目从未在正文中被引用。多半是复制粘贴带进来的，删除或补引用。")
def r_cite_002(lines, text, path, ctx):
    body, entries = ctx["parsed"]
    if entries is None:
        return []
    cited = set(cited_numbers(body))
    return [_mk("CITE-002", path, ln, "条目 [%d] 从未被正文引用" % n)
            for n, _, ln in entries if n not in cited]


@rule("CITE-003", "blocker", "著录完整", "疑似缺主要责任者",
      "条目在编号后没有出现著者名（GB/T 7714 要求主要责任者为著录第一项）。核对原文补上。")
def r_cite_003(lines, text, path, ctx):
    body, entries = ctx["parsed"]
    if entries is None:
        return []
    out = []
    for n, etext, ln in entries:
        head = re.split(r"[．.]", etext, maxsplit=1)[0]
        head = TYPEID_RE.sub("", head).strip()
        if AUTHOR_CN_FULL.match(head) or AUTHOR_EN_FULL.match(head):
            continue
        out.append(_mk("CITE-003", path, ln, "[%d] %s" % (n, etext[:60])))
    return out


@rule("CITE-004", "blocker", "著录完整", "著录缺年份",
      "条目中没有 4 位出版年份。年份是著录必备项，查原文补上，不许空着。")
def r_cite_004(lines, text, path, ctx):
    body, entries = ctx["parsed"]
    if entries is None:
        return []
    return [_mk("CITE-004", path, ln, "[%d] %s" % (n, etext[:60]))
            for n, etext, ln in entries if not YEAR_RE.search(etext)]


@rule("CITE-005", "warning", "著录规范", "著者超3人未用“等”",
      "GB/T 7714：著者超过 3 人时列前 3 人加“，等”（西文加 et al.）。检测到 4+ 著者且无“等”。")
def r_cite_005(lines, text, path, ctx):
    body, entries = ctx["parsed"]
    if entries is None:
        return []
    out = []
    for n, etext, ln in entries:
        head = re.split(r"[．.]", etext, maxsplit=1)[0]
        if "等" in head or "et al" in head:
            continue
        names = [s for s in re.split(r"[，,、;；]", head) if re.match(r"^[\u4e00-\u9fa5·]{2,8}$", s.strip())]
        if len(names) > 3:
            out.append(_mk("CITE-005", path, ln, "[%d] 著者 %d 人未用“等”" % (n, len(names))))
    return out


@rule("CITE-006", "warning", "引用制", "引用编号不连续",
      "顺序编码制下文内引用编号出现断号（如引用了 [5] 却没有 [4]）。检查是否漏标或错号。")
def r_cite_006(lines, text, path, ctx):
    body, entries = ctx["parsed"]
    cited = sorted(cited_numbers(body))
    if len(cited) < 2:
        return []
    if cited[-1] - cited[0] + 1 != len(cited):
        missing = [str(i) for i in range(cited[0], cited[-1] + 1) if i not in cited]
        return [_mk("CITE-006", path, 1, "引用编号断号，缺失：%s" % "、".join(missing[:10]))]
    return []


@rule("CITE-007", "warning", "引用制", "混用编号制与著者-年份制",
      "同一稿件同时出现 [n] 编号引用与（张三，2024）著者-年份引用。选定一种引用制并全文统一。")
def r_cite_007(lines, text, path, ctx):
    body, entries = ctx["parsed"]
    body_text = "\n".join(body)
    if not NUMCITE_RE.search(body_text):
        return []
    hits = []
    for i, ln in enumerate(body):
        if AUTHORYEAR_CN_RE.search(ln) or AUTHORYEAR_EN_RE.search(ln):
            hits.append(_mk("CITE-007", path, i + 1, ln.strip()[:80]))
            if len(hits) >= 5:
                break
    return hits


@rule("CITE-008", "warning", "著录规范", "重复著录",
      "文末出现标题高度相同的重复条目，多半是同一文献被著录了两次。去重只留一条。")
def r_cite_008(lines, text, path, ctx):
    body, entries = ctx["parsed"]
    if entries is None:
        return []
    seen = {}
    out = []
    for n, etext, ln in entries:
        t = entry_title(etext)
        if len(t) < 4:
            continue
        if t in seen:
            out.append(_mk("CITE-008", path, ln, "[%d] 与 [%d] 疑似同一文献" % (n, seen[t])))
        else:
            seen[t] = n
    return out


@rule("CITE-009", "warning", "著录规范", "缺文献类型标识",
      "条目缺少 [J]/[M]/[D]/[C]/[N]/[EB/OL] 等文献类型标识。GB/T 7714 要求必须标注。")
def r_cite_009(lines, text, path, ctx):
    body, entries = ctx["parsed"]
    if entries is None:
        return []
    return [_mk("CITE-009", path, ln, "[%d] 缺文献类型标识" % n)
            for n, etext, ln in entries if not TYPEID_RE.search(etext)]


@rule("CITE-010", "nit", "著录规范", "标点全角半角混用",
      "条目同时出现全角句号．与半角句号.。全文统一用一种（中文条目建议全角）。")
def r_cite_010(lines, text, path, ctx):
    body, entries = ctx["parsed"]
    if entries is None:
        return []
    out = []
    for n, etext, ln in entries:
        if "．" in etext and re.search(r"[0-9a-zA-Z]\.[0-9a-zA-Z（(]", etext):
            out.append(_mk("CITE-010", path, ln, "[%d] 全角．与半角.混用" % n))
    return out


# ---------------------------------------------------------------- 运行器

def run(target):
    files = collect_files(target)
    findings = []
    for path in files:
        text = read_text(path)
        lines = text.split("\n")
        rel = os.path.relpath(path, target)
        ctx = {"parsed": split_body_refs(lines)}
        for r in RULES:
            try:
                for f in r["check"](lines, text, path, ctx) or []:
                    f.file = rel
                    findings.append(f)
            except Exception:
                continue  # 单条规则异常不影响整体
    return files, findings


def main(argv=None):
    ap = argparse.ArgumentParser(description="lhg-lit-review 确定性引用审计")
    ap.add_argument("--target", default=".", help="扫描目录")
    ap.add_argument("--format", choices=["json", "text"], default="text")
    ap.add_argument("--fail-on", choices=["blocker", "warning", "nit"], default="blocker")
    args = ap.parse_args(argv)

    target = os.path.abspath(args.target)
    if not os.path.isdir(target):
        print("target 不是目录：%s" % args.target, file=sys.stderr)
        return 1

    files, findings = run(target)
    sev_rank = {"blocker": 3, "warning": 2, "nit": 1}
    counts = {"blocker": 0, "warning": 0, "nit": 0}
    for f in findings:
        counts[f.severity] = counts.get(f.severity, 0) + 1

    result = {
        "tool": TOOL,
        "version": VERSION,
        "target": args.target,
        "summary": {
            "files_scanned": len(files),
            "rules_run": len(RULES),
            "blocker": counts["blocker"],
            "warning": counts["warning"],
            "nit": counts["nit"],
        },
        "findings": [f.to_dict() for f in sorted(
            findings, key=lambda x: (-sev_rank.get(x.severity, 0), x.file, x.line))],
    }

    if args.format == "json":
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        s = result["summary"]
        print("引用审计：扫描 %d 文件，运行 %d 条规则" % (s["files_scanned"], s["rules_run"]))
        print("blocker=%d warning=%d nit=%d" % (s["blocker"], s["warning"], s["nit"]))
        for f in result["findings"]:
            print("[%s][%s] %s:%d %s" % (
                f["severity"].upper(), f["rule_id"], f["file"], f["line"], f["title"]))
            print("    %s" % f["detail"])
            if f["snippet"]:
                print("    → %s" % f["snippet"])

    level = sev_rank[args.fail_on]
    bad = any(sev_rank.get(f.severity, 0) >= level for f in findings)
    return 2 if bad else 0


if __name__ == "__main__":
    sys.exit(main())

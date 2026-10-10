#!/usr/bin/env python3
"""lhg-lit-review 确定性结构审计：6 条规则，零第三方依赖。

扫描目标目录的 Markdown 综述稿，检查综述必备结构（引言/批判性述评/展望/
方法说明）是否齐全；输出 JSON 与人类可读报告；
有 blocker 时以 exit code 2 退出（供 hooks 与 CI 使用）。

用法：
    python3 structure_audit.py --target <目录> [--format json|text] [--fail-on blocker|warning|nit]

规则文案均为本项目原创，未复制任何第三方原文案与代码。
"""

import argparse
import json
import os
import re
import sys

VERSION = "1.0.0"
TOOL = "lhg-lit-review/structure-audit"

SKIP_DIRS = {
    "node_modules", ".git", "__pycache__", "dist", "build", ".venv",
}
SCAN_EXTS = {".md", ".markdown"}

HEADING_RE = re.compile(r"^(#{1,6})\s*(.+?)\s*$")
REFS_HEADING_RE = re.compile(r"参考文献|References")

INTRO_RES = [re.compile(p) for p in
             (r"引言", r"研究背景", r"绪论", r"前言", r"Introduction")]
CRITIQUE_RES = [re.compile(p) for p in
                (r"述评", r"批判", r"评价", r"不足", r"局限", r"反思",
                 r"研究现状", r"评析", r"Critique", r"Discussion")]
OUTLOOK_RES = [re.compile(p) for p in
               (r"展望", r"未来", r"趋势", r"方向", r"建议", r"Outlook", r"Future")]
METHOD_RES = [re.compile(p) for p in
              (r"检索", r"筛选", r"纳入", r"排除", r"文献来源", r"数据库",
               r"方法", r"Method")]


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


def headings(lines):
    """返回 [(level, title, line_no)]。"""
    out = []
    for i, ln in enumerate(lines):
        m = HEADING_RE.match(ln)
        if m:
            out.append((len(m.group(1)), m.group(2).strip(), i + 1))
    return out


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


def _has(heads, patterns):
    return any(any(p.search(t) for p in patterns) for _, t, _ in heads)


@rule("STR-001", "blocker", "结构完整", "缺引言",
      "全文没有引言/研究背景/绪论类章节。综述必须开篇讲清问题与综述的必要性，补一节引言。")
def r_str_001(lines, text, path, ctx):
    if not _has(ctx["heads"], INTRO_RES):
        return [_mk("STR-001", path, 1, "未发现引言类标题")]
    return []


@rule("STR-002", "blocker", "结构完整", "缺批判性述评",
      "全文没有述评/批判/评价类章节，只有文献罗列。没有批判就没有综述的贡献，补一节批判性述评。")
def r_str_002(lines, text, path, ctx):
    if not _has(ctx["heads"], CRITIQUE_RES):
        return [_mk("STR-002", path, 1, "未发现批判性述评类标题")]
    return []


@rule("STR-003", "warning", "结构完整", "缺研究展望",
      "全文没有展望/未来方向类章节。批判指出了短板，展望要给出下一步做什么，补一节。")
def r_str_003(lines, text, path, ctx):
    if not _has(ctx["heads"], OUTLOOK_RES):
        return [_mk("STR-003", path, 1, "未发现研究展望类标题")]
    return []


@rule("STR-004", "warning", "方法透明", "缺方法说明",
      "全文未说明文献检索与筛选方法（数据库/检索式/纳入排除标准）。方法不透明，综述不可复现，补一段说明。")
def r_str_004(lines, text, path, ctx):
    if not _has(ctx["heads"], METHOD_RES):
        # 标题没有，再看正文是否提及
        if not any(p.search(text) for p in METHOD_RES):
            return [_mk("STR-004", path, 1, "未发现文献检索/筛选方法说明")]
    return []


@rule("STR-005", "warning", "结构质量", "主题结构扁平",
      "正文超过 1500 字但二级标题少于 3 个，说明主题没有聚类，可能是流水账。按主题/阶段/学派重组。")
def r_str_005(lines, text, path, ctx):
    heads = ctx["heads"]
    body_heads = [(lv, t, ln) for lv, t, ln in heads if not REFS_HEADING_RE.search(t)]
    h2 = [h for h in body_heads if h[0] == 2]
    body_len = len(re.sub(r"\s+", "", text))
    if body_len > 1500 and len(h2) < 3:
        return [_mk("STR-005", path, 1,
                     "正文约 %d 字，仅 %d 个二级标题" % (body_len, len(h2)))]
    return []


@rule("STR-006", "nit", "结构质量", "标题层级跳跃",
      "标题层级跳跃（如 # 后直接 ###）。层级逐级递进，方便读者定位。")
def r_str_006(lines, text, path, ctx):
    out = []
    prev = 0
    for lv, t, ln in ctx["heads"]:
        if prev and lv > prev + 1:
            out.append(_mk("STR-006", path, ln, "标题跳跃：%s" % ("#" * lv + " " + t)))
        prev = lv
    return out


# ---------------------------------------------------------------- 运行器

def run(target):
    files = collect_files(target)
    findings = []
    for path in files:
        text = read_text(path)
        lines = text.split("\n")
        rel = os.path.relpath(path, target)
        ctx = {"heads": headings(lines)}
        for r in RULES:
            try:
                for f in r["check"](lines, text, path, ctx) or []:
                    f.file = rel
                    findings.append(f)
            except Exception:
                continue  # 单条规则异常不影响整体
    return files, findings


def main(argv=None):
    ap = argparse.ArgumentParser(description="lhg-lit-review 确定性结构审计")
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
        print("结构审计：扫描 %d 文件，运行 %d 条规则" % (s["files_scanned"], s["rules_run"]))
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

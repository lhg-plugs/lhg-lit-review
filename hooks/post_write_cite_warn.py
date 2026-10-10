#!/usr/bin/env python3
"""lhg-lit-review 硬门②（警告级，不拦截）：写综述稿 md 时提醒核对引用对应关系。

触发：PostToolUse / Write|Edit。只做提醒，永远 exit 0、不拦截写入。

逻辑：被写的 .md 文件若含文内编号引用 [n] 但全文没有"参考文献"节，
大概率是引用编号与文末条目脱节，提醒跑 citation_audit.py。

逃生方式：LHG_LR_HOOKS_OFF=1（环境变量）可关闭本提醒；
或 /plugin disable lhg-lit-review 停用整个插件。
零第三方依赖；内部出错 fail-open。
"""

import json
import os
import re
import sys

CITE_RE = re.compile(r"\[\d+\]")
REFS_HEADING_RE = re.compile(r"^#{1,4}\s*(参考文献|References)\b", re.M)


def main() -> int:
    if os.environ.get("LHG_LR_HOOKS_OFF") == "1":
        return 0

    try:
        raw = sys.stdin.read()
        payload = json.loads(raw) if raw.strip() else {}
    except Exception:
        return 0  # 输入解析失败：fail-open

    tool_input = payload.get("tool_input", {}) or {}
    file_path = tool_input.get("file_path", "") or ""
    if not file_path.endswith(".md"):
        return 0

    try:
        with open(file_path, encoding="utf-8", errors="replace") as fh:
            text = fh.read()
    except OSError:
        return 0  # 读不到文件：fail-open

    if not CITE_RE.search(text):
        return 0  # 没有文内引用，不提醒
    if REFS_HEADING_RE.search(text):
        return 0  # 有参考文献节（标题行），不提醒

    msg = (
        '引用提醒（lhg-lit-review）：%s 含文内引用编号但未发现"参考文献"节。\n'
        "写完本节请跑：python3 <插件目录>/scripts/audit/citation_audit.py --target <稿件目录>\n"
        "确认每个编号在文末都有对应条目（防孤儿引用）。\n"
        "关闭本提醒：export LHG_LR_HOOKS_OFF=1（当前会话有效）。"
    ) % file_path
    out = {
        "hookSpecificOutput": {
            "hookEventName": "PostToolUse",
            "additionalContext": msg,
        }
    }
    sys.stdout.write(json.dumps(out, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())

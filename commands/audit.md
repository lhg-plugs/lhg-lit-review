---
description: 引用与结构审计：跑确定性脚本校验引用对应关系、著录完整性与综述结构，输出分级报告。
argument-hint: [稿件目录] [--style gb7714|apa]
---

# /lhg-lit-review:audit —— 引用与结构审计

用户输入在 `$ARGUMENTS` 中：`[稿件目录] [--style gb7714|apa]`。目录缺省为当前目录；风格缺省 `gb7714`。

## 流程（加载 lhg-lr-cite 全程指导）

### 1. 跑脚本
```bash
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/audit/citation_audit.py  --target <目录> --format text
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/audit/structure_audit.py --target <目录> --format text
```
记下 blocker / warning / nit 的数量与明细（含文件、行号、规则说明）。

### 2. 分级处理
- blocker（孤儿引用、僵尸条目、缺主要责任者、缺年份、缺引言、缺批判性述评）：逐条修，修一条用脚本复查一条。
- 修不掉的（如题录实在查不到）→ 列入"需人工处理"，**不许**为清零改规则。
- warning（编号不连续、混用引用制、重复著录、缺展望、缺方法说明）：修掉或写豁免理由。

### 3. 人工核对（脚本做不到的）
- 抽 5 条文内引用，核对转述是否忠实原文（防曲解）。
- 抽 3 条参考文献，核对著录信息与真实出版信息一致（防编造）。
- 通读批判性述评节：确认是真批判（指出具体不足），不是"作者们做了很多有益探索"式套话。

### 4. 输出报告
按 lhg-lr-cite 第 6 节模板输出自查报告，存为 `自查报告-YYYYMMDD.md`，结论写清"通过 / 不通过"。

## 硬规则
- 有 blocker 就说"通过" → 不许。
- 为清零改脚本规则或阈值 → 这是作弊，不许。
- 引用风格全文统一，gb7714 与 apa 不许混用（脚本 CITE-007 会抓）。

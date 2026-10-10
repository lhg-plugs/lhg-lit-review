<!-- About 简介（推送后填写到仓库 About 栏）：
文献综述专家：从文献收集到规范引用的写作流水线 ｜ 一键安装：/plugin marketplace add lhg-plugs/lhg-lit-review
-->
<!-- topics（推送后打）：claude-code, claude-plugin, agent-skills, literature-review, academic -->

# lhg-lit-review：文献综述专家

> **一句话介绍**：给 AI 助手装上"文献综述流水线"——文献收集、框架设计（主题聚类/时间线/学派对比）、逐节写作、引用格式校验（GB/T 7714 / APA），硕博开题到论文文献章的刚需工具。
>
> **一键安装**：在 Claude Code 里运行
> ```
> /plugin marketplace add lhg-plugs/lhg-lit-review
> /plugin install lhg-lit-review@lhg-plugs
> ```

## 它是什么

`lhg-lit-review` 是一个 Claude Code 插件（plugin 为主、skill 为辅）：

- **5 个命令**（写作流水线）：`lit-review` 一条龙（收集→框架→写作→校验），`collect` 文献收集，`frame` 框架设计，`write` 逐节写作，`audit` 引用与结构审计
- **4 个平台中立 skill**（方法论，可移植到豆包/Workbuddy 等 agent 平台）：文献收集、框架设计、逐节写作、引用格式规范
- **3 个专家 agent**：文献调研专家、学术写作专家、引用审计专家
- **2 个硬门 hooks**：commit 前引用审计拦截、写稿无参考文献节提醒（均可一键豁免）
- **16 条确定性审计规则**：纯 Python、零第三方依赖，引用对应关系与著录完整性秒级检查

引用格式覆盖 **GB/T 7714**（顺序编码制 / 著者-出版年制）与 **APA 第 7 版**。

## 5 个命令用法

| 命令 | 作用 | 示例 |
|---|---|---|
| `/lhg-lit-review:lit-review` | 文献综述一条龙（收集→框架→写作→校验） | `/lhg-lit-review:lit-review "大语言模型在教育评价中的应用"` |
| `/lhg-lit-review:collect` | 文献收集：关键词矩阵→检索式→筛选→文献池 | `/lhg-lit-review:collect "主题"` |
| `/lhg-lit-review:frame` | 框架设计：三条路线三选一，输出大纲 | `/lhg-lit-review:frame` |
| `/lhg-lit-review:write` | 逐节写作：主题句+证据+评价三段式 | `/lhg-lit-review:write --section 批判性述评` |
| `/lhg-lit-review:audit` | 引用与结构审计（脚本 + 人工抽查） | `/lhg-lit-review:audit` |

## 自查说明

自查 = 确定性脚本（机器）+ 人工抽查（人）：

1. 先跑 `scripts/audit/` 下的两个脚本（引用审计 10 条、结构审计 6 条规则），零 LLM 成本；
2. 发现分三级：**blocker**（孤儿引用、僵尸条目、缺著者、缺引言、缺批判性述评——必须修，commit 前 hook 会拦截）、**warning**（编号不连续、混用引用制、缺展望——修或写豁免理由）、**nit**（标点混用等——顺手修）；
3. 再做人工抽查：随机抽 5 条文内引用核对转述忠实度，抽 3 条参考文献核对著录真实性（防编造）。

blocker 清零才算做完；为清零改规则算作弊，不许。

## 目录结构

```
lhg-lit-review/
├── .claude-plugin/          # plugin.json（插件清单）+ marketplace.json（本仓即市场）
├── commands/                # 5 个命令：lit-review / collect / frame / write / audit
├── skills/                  # 4 个平台中立 skill（lhg-lr-collect/frame/write/cite）
├── agents/                  # 3 个专家 agent（reviewer / writer / cite-auditor）
├── hooks/                   # 2 个硬门（commit 前审计拦截 / 写稿引用提醒）+ 豁免说明
├── scripts/audit/           # 16 条确定性审计规则（零第三方依赖）
├── fixtures/                # 冒烟测试用例（坏/好对照）
├── smoke_test.py            # 一键冒烟测试
├── ATTRIBUTION.md           # 灵感来源与许可声明
└── LICENSE                  # MIT
```

## 诚实声明

- **不编造文献**：检索动作由用户亲手执行（知网/万方/Web of Science 等），助手只做策略、筛选与建池。题录信息不全先标"待补全"，绝不杜撰作者、期刊、年份——编造一条文献，整个交付作废。
- **引用审计是启发式**：脚本能抓"对应关系"和"著录完整性"，抓不到"转述是否曲解原文"。交稿前的人工抽查（5+3 条）不可省略。
- **未核实项**：`ppsz-qqq/cse-skills` 仓库在本插件编写时未声明开源许可，本插件仅借鉴其"系统化文献调研流程"的高层思想，未复制其任何原文案与代码（见 ATTRIBUTION.md）。

## 什么时候用 / 什么时候不用（FAQ）

**什么时候用：**

- 你要写开题报告、学位论文的文献综述章，面对几十篇文献不知从何下笔时 → 用 `/lhg-lit-review:lit-review` 一条龙
- 你已经有一堆文献但乱成一团时 → 用 `collect` 建文献池，再用 `frame` 定框架
- 你写完初稿，怕引用编号对不上、著录格式被导师打回来时 → 跑 `/lhg-lit-review:audit`
- 你想立一套"综述写作纪律"（先框架后动笔、引用双向对应）时 → 它的 hooks 硬门开箱即用

**什么时候不用：**

- 你只需要查几篇文献、不写综述 → 本插件是"写作流水线"，单点检索需求用学术数据库更快
- 你的学校/期刊要求 GB/T 7714 与 APA 之外的格式（如 Chicago、MLA）→ 审计脚本只覆盖 GB/T 7714 与 APA，需要自己加规则
- 你希望 AI 直接"帮你找好文献" → 助手无法访问付费数据库，给出的题录不可信；检索必须亲手做，这是本插件的红线

## lhg-plugs 插件矩阵

| 插件 | 一句话 | 安装 |
|---|---|---|
| [lhg-lit-review](https://github.com/lhg-plugs/lhg-lit-review) | 文献综述专家：从文献收集到规范引用的写作流水线 | `/plugin install lhg-lit-review@lhg-plugs` |
| [lhg-fullstack](https://github.com/lhg-plugs/lhg-fullstack) | 小白一句话 → 高质量全栈应用 | `/plugin install lhg-fullstack@lhg-plugs` |
| [lhg-video-edit](https://github.com/lhg-plugs/lhg-video-edit) | 一句话把口播素材剪成爆款短视频（+口播脚本子命令） | `/plugin install lhg-video-edit@lhg-plugs` |
| [lhg-wechat-article](https://github.com/lhg-plugs/lhg-wechat-article) | 公众号写作专家：选题到排版一气呵成 | `/plugin install lhg-wechat-article@lhg-plugs` |
| [lhg-xiaohongshu](https://github.com/lhg-plugs/lhg-xiaohongshu) | 小红书种草专家：卖点到爆款笔记一键生成 | `/plugin install lhg-xiaohongshu@lhg-plugs` |
| [lhg-resume](https://github.com/lhg-plugs/lhg-resume) | 简历优化专家：ATS诊断到模拟面试一条龙 | `/plugin install lhg-resume@lhg-plugs` |
| [lhg-ppt](https://github.com/lhg-plugs/lhg-ppt) | PPT制作专家：述职融资答辩一键成稿 | `/plugin install lhg-ppt@lhg-plugs` |
| [lhg-excel](https://github.com/lhg-plugs/lhg-excel) | 表格数据专家：清洗透视图表一条龙 | `/plugin install lhg-excel@lhg-plugs` |
| [lhg-thesis](https://github.com/lhg-plugs/lhg-thesis) | 毕业论文助手：开题到盲审的写作流水线 | `/plugin install lhg-thesis@lhg-plugs` |
| [lhg-miniprogram](https://github.com/lhg-plugs/lhg-miniprogram) | 小程序开发专家：一句话生成微信小程序 | `/plugin install lhg-miniprogram@lhg-plugs` |
| [lhg-contract](https://github.com/lhg-plugs/lhg-contract) | 合同审查助手：风险条款标红+修改建议 | `/plugin install lhg-contract@lhg-plugs` |

## 自检与反馈

本插件自带质检：每次使用后可跑 `python3 smoke_test.py` 一键验证（JSON 合法、skill/command/agent 完整性、16 条规则、fixtures 命中、hooks 行为）。

发现 bug 或有改进建议，以 `[QC] <一句话问题>` 为标题提交到 https://github.com/lhg-plugs/lhg-lit-review/issues，正文写清"复现步骤 → 实际表现 → 期望表现"。

## 出品：刘洪光

本插件由真人出镜 IP「刘洪光」（安徽合肥）出品，归属 [lhg-skills](https://github.com/lhg-skills)。

- GitHub 主页：https://github.com/lhg-skills —— 全部 skill 开源在此，欢迎 star
- 视频号：搜「刘洪光实名上网」
- 微信：lhgsmsw

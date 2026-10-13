# 麦会选 · Mai Hui Xuan

**想吃的留下，预算和热量帮你算好。**

一个在现有 AI 助手中使用的麦当劳点餐 skill，面向想省钱、纠结吃什么、也想了解热量的人。通过麦当劳 MCP 核验菜单、优惠、实付价格和营养信息。

| 入口 | 试着这样说 |
|---|---|
| 帮我选 | 25 元以内，想吃鸡肉，帮我选午饭。 |
| 帮我改 | 薯条必须保留，饮料可以换，看看怎么点更划算。 |
| 吃轻点 | 开低卡模式，给我一份完整的一人餐。 |
| 找优惠 | 现在有什么活动值得吃？预算 30 元，按我的口味挑。 |

四种需求可以组合。**默认先确认门店，先推荐一份该店当前划算的活动套餐，再每次问一个问题细化需求。** 首推前不要求填完预算、口味和热量问卷；已提供的约束直接应用。首轮仅展示一份套餐，细化后一个首选、最多两个备选，均展示到手价、热量档、推荐理由。没有可用活动或普通组合更划算时如实说明。偏好只有用户要求记住时才保存，支持查看、修改和清除。

## 当前状态

已实现 skill 指令、离线候选筛选排序、价格对比、营养汇总、活动与普通套餐对比、偏好本地存储和自动化测试。本机已完成 MCP 认证握手与工具发现（35 个工具）。**尚未验证真实点餐流程、营养覆盖或实际活动；示例全部为模拟数据，不可用于下单。**

## 安装

需要支持 Skills、Streamable HTTP MCP 的 AI 助手。完整本地计算与记忆需要 Python 3.9+，运行代码仅使用标准库。

将 `skills/mai-hui-xuan` 整个目录放入客户端的 Skills 目录。通用安装单元是该目录，其他参赛文档无需安装。对于本地目录约定为 `~/.codex/skills` 的环境，可复制到该目录；其他客户端请按其 Skills 导入说明操作。若目标目录已存在，请先比较内容，避免覆盖已有修改。重新加载客户端技能列表后，使用 `$mai-hui-xuan` 或直接提出麦当劳点餐需求。

在 [麦当劳 MCP 平台](https://open.mcd.cn/mcp) 获取自己的 Token，在客户端私有连接器设置中连接 `https://mcp.mcd.cn`，采用 Streamable HTTP 和 Bearer 认证。配置结构参考 [mcp-config.example.json](mcp-config.example.json)。`${MCD_MCP_TOKEN}` 是占位符，客户端是否自动展开环境变量需按其文档核验；若不支持，应通过客户端凭据设置配置，不把真实 Token 写进公开文件。

首次接入先读取工具列表，再查询门店/菜单和试算。`agents/openai.yaml` 的依赖声明不自动完成认证。无需 Token 也可运行以下离线验证。

## 离线体验

在仓库根目录执行：

```sh
python3 skills/mai-hui-xuan/scripts/recommend.py examples/demo.json --demo-now 2026-10-13T12:00:00+08:00
python3 -m unittest discover -s tests -v
```

示例模拟“30 元预算、保留小份配餐、低卡、找活动”，演示普通方案比活动套餐更便宜时的推荐。餐品名称、价格和营养均为虚构测试值，输出中持续标注模拟状态。

数据格式见 [本地契约](skills/mai-hui-xuan/references/data-contract.md)。Python 负责确定性筛选，助手负责调用真实 MCP、组建有意义的候选和解释结果。没有本地执行能力时仍可阅读 skill 完成对话流程，但不承诺持久记忆或脚本级校验。

## 产品规则

- 先满足预算、忌口、必吃餐品与低卡约束，再排序；找不到就解释，不偷偷放宽。
- 一人整餐 ≤500 kcal 为较低热量，>500 且 ≤800 为中等，>800 为较高。这是产品内部比较档位，不是医学标准。低卡模式默认上限 500 kcal，可按用户要求修改。
- 未知营养不当作零；缺少组件热量的套餐不进入低卡推荐。不把低卡直接称为低脂或适合减脂。
- 只比较本次核验候选，不承诺全局最低价。付费会员、积分成本、领券门槛不能隐藏。
- 偏好保存在用户本机，见 [偏好管理](skills/mai-hui-xuan/references/preferences.md)。本仓库不保存 Token、地址和订单信息。

## 参赛与真实验收

参赛所需文件已准备：本文件、官方原文 [CONTEST_DECLARATION.md](CONTEST_DECLARATION.md)、[MCP_INTEGRATION.md](MCP_INTEGRATION.md)、脱敏配置与可运行内容。项目仓库：https://github.com/yf358559551/mai-hui-xuan 。尚未提交比赛报名，也未声称真实 MCP 验收已完成。未使用 WorkBuddy 开发，不生成虚假的 workbuddy.md。

接入后按 [验收场景](tests/ACCEPTANCE.md) 完成真实查询与价格验证，再录制演示、发布和报名。官方规则要求项目真实使用 MCP，离线测试不能代替该项。官方来源：[MCP 文档](https://github.com/M-China/mcd-mcp-server)、[比赛规则](https://github.com/M-China/mcd-developer-innovation-challenge/blob/main/activityGuidelines.md)。

本项目为独立参赛作品，不代表麦当劳官方背书。

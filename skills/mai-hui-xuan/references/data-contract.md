# 本地归一化数据契约

`recommend.py` 接收 UTF-8 JSON。它只筛选已经由助手组建、核价的候选；不枚举官方菜单、不调用 MCP。真实参数与响应由宿主工具 schema 决定。

顶层字段：

| 字段 | 含义 |
|---|---|
| demo | 布尔，默认 false。模拟数据必须 true |
| mode | choose / modify / deals；低卡可与任一模式叠加 |
| store_id、channel | 当前统一门店 ID、渠道标识，来自实际工具 |
| budget_yuan | 可选，人民币元，比较含必要费用的实付总额 |
| low_calorie、low_kcal_max | 布尔与可选上限，默认 false / 500 |
| likes、avoid | 口味标签数组；归一化时统一同义词。过敏限制不能靠标签猜测 |
| required_items | `{规格ID: 数量}`；保留项必须含规格，不能只用模糊餐品名 |
| original_id | modify 原方案候选 ID |
| candidates | 候选数组 |

每份候选：`id`、`name`、`available`（明确核验可售）、`meal_complete`（是否构成一餐）、`items`、`quote`。套餐先展开成最终选定的组件，避免重复计数。

每个 item：`id`（包含规格的稳定 ID）、`name`、正整数 `quantity`、`tags` 数组；`kcal`、`protein_g`、`fat_g` 是**每份**的数值，未知传 null 或省略。总量由脚本乘数量。单位、份量匹配与可售状态依赖助手核验。

quote：`total_yuan` 为**整份候选实付总额**，`verified=true` 表示真实试算成功，`all_fees_included=true` 表示配送等必要费用全部计入；还需 `store_id`、`channel`、`queried_at`。如任何优惠到期更早，在 `expires_at` 写最早到期时间。所有时间必须为带时区 ISO 8601。

activity 可选：`name`、`verified`、`starts_at`、`ends_at`、`store_id`、`channel`。只有已确认用户资格、活动生效时间和门店/渠道的价格方案才赋 verified=true。缺乏有效期时不构造已验证活动，可说明线索未核验；普通已核价候选可单独推荐。

same_contents_baseline 可选：`total_yuan`、`verified`、`all_fees_included`、`store_id`、`channel`、`queried_at`、`items`（规格 ID→数量）。必须与当前内容一一对应，才产生 `verified_saving_yuan`；套餐更换不能使用此字段包装为同款省钱。

输出 recommendations 最多三份，包含热量总数、档位、匹配口味、可信同内容节省金额。rejected 给出硬约束排除原因。modify 的 comparison 为原方案减新方案，正数表示减少，负数表示增加。结果为空时不自动放宽。

CLI：`python3 scripts/recommend.py INPUT.json`。只有 `demo=true` 才能用 `--demo-now 2026-10-13T12:00:00+08:00` 固定时钟；真实数据按系统当前时间。输入文件和输出可能含个人点餐偏好，应放私有临时目录，不能提交仓库。

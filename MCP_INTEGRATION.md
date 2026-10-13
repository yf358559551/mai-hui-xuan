# 麦会选 MCP 集成说明

服务：麦当劳中国 MCP，`https://mcp.mcd.cn`，Streamable HTTP，客户端私有 Bearer Token。

## 集成方式与状态

这是由宿主 AI 助手编排 MCP 的 skill，不内置第二套 HTTP 客户端。宿主发现工具 schema 后按 SKILL.md 调用，归一化到本地数据契约，再运行筛选脚本。工具返回字段未知前不编造参数映射。

截至本版本：流程和工具名称已对照官方说明；已实现离线逻辑。2026-10-13 在本机完成真实服务认证握手与 tools/list，发现 35 个工具，确认活动、核价、营养、菜单和门店优惠工具存在。**下表业务调用路径尚待完整联调，工具发现不能代替真实点餐验收。**

| 流程 | 计划使用工具 | 用户价值 |
|---|---|---|
| 定位点餐上下文 | now-time-info、query-nearby-stores；外送时 delivery-query-addresses、delivery-query-stores | 时间、门店与渠道一致 |
| 构建与修改套餐 | query-meals、query-meal-detail | 可售且支持实际替换 |
| 用户优惠 | query-store-coupons、query-my-coupons、available-coupons | 优惠符合账户资格与门店条件 |
| 找优惠 | campaign-calendar | 排除已过期和未来活动 |
| 核验实付 | calculate-price | 比较包括必要费用的总价 |
| 热量与营养 | list-nutrition-foods | 根据所选组件汇总并分档 |

用户明确要求领券后才使用 auto-bind-coupons 并重新核价。推荐主流程不创建订单、不扣积分、不支付。用户进一步明确要求下单时，由宿主按实时 schema 处理 create-order 等工具，并遵循 skill 中的交易边界。

## 调用顺序

先确认门店/必要就餐方式 → 当前活动、菜单与券 → 套餐详情 → 构建候选 → calculate-price → 营养逐项匹配 → 本地硬约束筛选/排序 → 展示一份活动首推 → 每次一个问题细化需求 → 更新首选与备选。已知偏好始终应用，未知预算不阻塞首推；没有适用活动或普通方案更划算时明确给出普通替代。明确改餐等请求直接处理。

帮我改包含原方案和新方案的同条件试算；找优惠包含至少一个可行普通方案对照。既有工具返回不满足证据要求时诚实降级，不用模拟返回冒充线上结果。

## 联调记录要求

记录测试日期、客户端、工具名、成功/失败、已脱敏的关键结果摘要；核对实际 schema、费用单位、营养单位/规格、套餐替换和活动有效期。不得提交 Token、手机号、精确地址、券码或订单标识。通过 tests/ACCEPTANCE.md 的真实场景后再将状态改为已验证。

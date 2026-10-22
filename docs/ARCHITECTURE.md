# 架构与业务边界

## 后端六模块

- `api`：对外接口定义与 DTO。
- `app`：Spring Boot 启动和依赖装配、配置、MyBatis XML。
- `domain`：活动、策略、奖品、任务领域；仓储接口由基础设施实现。
- `infrastructure`：MySQL 仓储、Redisson、RabbitMQ 事件发布。
- `trigger`：HTTP Controller、RabbitMQ Listener、Spring 定时任务。
- `types`：统一响应、错误码、常量和事件基础模型。

## 一次抽奖

1. 活动装配将 SKU 库存、奖品查找表和必要配置预热到 Redis。
2. 活动参与服务校验活动状态和日期；可复用未使用订单，否则在事务内处理额度与新订单。
3. `AbstractRaffleStrategy` 模板调用责任链进行默认/黑名单/权重抽奖，默认结果再通过规则树过滤。
4. 规则树可检查当日抽奖次数、库存和兜底奖励。
5. `AwardRepository` 同事务插入中奖记录、task，并将用户抽奖单改为 `used`。
6. 事务外发送 RabbitMQ；失败任务由 `SendMessageTaskJob` 每 5 秒逐库扫描并补发。
7. `SendAwardCustomer` 收到消息后目前只打印日志，真实奖品履约尚未实现。

## 数据组织

| 数据库 | 用途 |
|---|---|
| `big_market` | 活动、SKU、策略、奖品、规则树等配置 |
| `big_market_01` / `big_market_02` | userId 路由的用户业务数据 |

`raffle_activity_order`、`user_raffle_order`、`user_award_record` 各在每个业务库中有 `_000` 至 `_003` 四张表；账户和 task 为每个业务库各一张，**不是所有表都拆成八张**。

## 库存异步回写

`DECR` 后以剩余序号拼接 `setNx` 标记；成功后将扣减事件放入 Redisson 延迟队列（3 秒），定时任务每 5 秒 `poll` 一条并更新数据库。因此它是**逐条异步回写，不是批量 SQL 更新**。活动 SKU 归零时另发 MQ 清零数据库库存并清理队列。

队列来自 Redis，而非 JVM 本地内存。该设计降低同步请求中的数据库更新压力，但不承诺 Redis 故障恢复时的绝对不超卖、消息恰好一次或全链路强一致。

## 本次整合修复

- Spring AMQP 跟随 Boot 2.7.12 BOM，不再强制引入 Boot 3.2 starter。
- Fastjson2 编解码器保留对象类型信息，并仅允许领域包和指定集合类型，避免读取缓存后得到 JSONObject。
- 前端真实请求携带 `{userId, activityId}`，正确使用 `/raffle/strategy/query_raffle_award_list`。
- `await fetch` 捕获网络异常，失败返回可见错误而非随机结果；重复点击有界面级防重，不等于服务端全局幂等。
- 前端根据后端奖品 ID 定位停格，结果文字直接显示后端奖品名称，避免兜底奖品和锁定文案混淆。

## 不能据此声称的能力

未实现微服务注册治理、XXL-JOB、积分支付与行为返利、Canal/ES、真实发奖履约、完整 MQ 消费幂等与死信补偿、生产限流风控、全链路压测。

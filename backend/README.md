# big-market-dxw · 大营销平台（抽奖营销后端）

> 一个基于 **DDD 分层架构** 的营销抽奖平台后端实现——支持「抽奖活动 → 策略装配 → 责任链 + 规则树抽奖 → 额度扣减 → 中奖落库 → MQ 异步发奖」的完整链路。
>
> 本项目为个人独立开发实现（在学习「小傅哥·大营销平台」项目思路的基础上自行设计、编码、联调并完成前端对接），用于展示 DDD 建模、设计模式落地与高并发库存/额度处理能力。

---

## 目录

- [一、项目是做什么的](#一项目是做什么的)
- [二、功能清单](#二功能清单)
- [三、技术栈](#三技术栈)
- [四、工程结构（DDD 分层）](#四工程结构ddd-分层)
- [五、核心设计](#五核心设计)
- [六、数据库设计](#六数据库设计)
- [七、接口文档](#七接口文档)
- [八、本地运行（保姆级步骤）](#八本地运行保姆级步骤)
- [九、Docker 部署](#九docker-部署)
- [十、常见问题 FAQ](#十常见问题-faq)

---

## 一、项目是做什么的

**大营销平台** 是一个典型的「电商/营销活动抽奖」中台后端。它把一次抽奖拆成可配置、可扩展、可复用的几个环节：

```
用户发起抽奖
   │
   ├─ 1. 参与活动     校验活动状态/时间 → 创建「用户抽奖单」→ 扣减活动账户额度（总/月/日）
   ├─ 2. 策略装配     把数据库里的「策略 + 奖品 + 概率 + 规则」预计算进 Redis（概率查找表）
   ├─ 3. 责任链过滤   黑名单 → 权重 → 默认抽奖，决定「初步中奖奖品 ID」
   ├─ 4. 规则树过滤   次数锁 → 库存扣减 → 兜底奖品，决定「最终可获得奖品」
   ├─ 5. 中奖落库     写入 user_award_record 中奖记录 + task 任务表
   └─ 6. MQ 异步发奖  定时任务扫描 task 表补发消息，send_award 队列消费发奖
```

它的核心价值在于：**抽奖规则全部由数据库配置驱动，代码只负责编排**。运营改一个 `rule_weight`、加一个 `rule_lock` 次数锁、换一个兜底奖品，都不需要改代码、不需要重新发布。

---

## 二、功能清单

| 能力 | 说明 |
| --- | --- |
| 活动装配（数据预热） | 把活动 SKU 库存、策略奖品概率一次性装配进 Redis，抽奖时零数据库压力 |
| 策略装配（概率查找表） | 按最小概率生成 `1 / minRate` 长度的占位数组，打散后写入 Redis，抽奖为 **O(1)** 查表 |
| 权重抽奖 | 按用户积分落在 `4000 / 5000 / 6000` 区间，切换不同奖品池（子策略独立装配） |
| 黑名单抽奖 | 命中黑名单用户直接返回「兜底奖品」，不走随机 |
| 规则树（决策树） | 次数锁 `rule_lock` → 库存扣减 `rule_stock` → 兜底 `rule_luck_award`，树结构存库、运行时组装 |
| 活动账户额度 | 总次数 / 月次数 / 日次数三级额度，实时扣减 + 剩余校验，杜绝超领 |
| 库存防超卖 | Redis `decr` 原子扣减 + 本地延迟队列异步更新 DB + MQ 库存归零事件 |
| 中奖记录 & 可靠发奖 | 抽奖结果写 `user_award_record`，同时写 `task` 任务表；定时任务补偿投递 MQ，保证最终一致 |
| 分库分表 | 接入自研 `db-router-spring-boot-starter`，按 `userId` 路由到 2 库 × 4 表 |
| 定时任务 | 库存延迟更新、奖品库存延迟更新、MQ 消息补偿投递，全部基于 `@Scheduled` |

---

## 三、技术栈

| 分类 | 选型 |
| --- | --- |
| 语言 / 构建 | Java 8、Maven（多模块聚合工程） |
| 框架 | Spring Boot 2.7.12、Spring MVC、Spring Scheduling |
| 持久层 | MyBatis 2.1.4、MySQL 8.0.22、HikariCP |
| 缓存 | Redis 6.2、Redisson 3.23.4（分布式、自定义编解码） |
| 消息队列 | RabbitMQ 3.12.9、Spring AMQP |
| 分库分表 | `cn.bugstack.middleware:db-router-spring-boot-starter`（自研路由组件） |
| 工具 | Lombok、Fastjson 2.0.28、Guava、Apache Commons Lang3 |
| 部署 | Docker、Docker Compose |

---

## 四、工程结构（DDD 分层）

```
big-market-dxw
├── big-market-dxw-api            # 【API 层】对外接口契约与 DTO（纯接口，供前端/其他服务依赖）
│   └── cn.bugstack.trigger.api   #   IRaffleActivityService / IRaffleStrategyService + dto/*
│
├── big-market-dxw-types          # 【通用层】Response 统一返回、ResponseCode 错误码、Constants、BaseEvent
│
├── big-market-dxw-domain         # 【领域层】全部业务规则与领域模型，不依赖任何框架实现
│   ├── activity                  #   活动聚合：参与抽奖、额度账户、SKU 库存、装配
│   ├── strategy                  #   策略聚合：概率查找表、责任链、规则树
│   ├── award                     #   奖品聚合：中奖记录、发奖
│   └── task                      #   任务聚合：MQ 消息任务表
│
├── big-market-dxw-infrastructure # 【基础设施层】仓储实现、DAO、Redis、MQ、分库分表路由
│   └── persistent/repository     #   ActivityRepository / StrategyRepository / AwardRepository / TaskRepository
│
├── big-market-dxw-trigger        # 【触发器层】HTTP Controller、RabbitMQ Listener、Scheduled Job
│   ├── http                      #   RaffleActivityController / RaffleStrategyController
│   ├── listener                  #   SendAwardCustomer / ActivitySkuStockZeroCustomer
│   └── job                       #   UpdateAwardStockJob / UpdateActivitySkuStockJob / SendMessageTaskJob
│
├── big-market-dxw-app            # 【启动模块】Spring Boot 启动类、application-*.yml、Mapper XML、Dockerfile
│
└── docs/dev-ops                  # 【运维】docker-compose、MySQL 初始化 SQL、Redis/RabbitMQ 配置、启停脚本
```

**依赖方向**：`app → trigger → domain ← infrastructure`，`domain → types`。
领域层通过 `IxxxRepository` 接口定义「需要什么」，由 infrastructure 提供实现，符合依赖倒置。

---

## 五、核心设计

### 5.1 抽奖算法：概率查找表（O(1)）

`StrategyArmoryDispatch#assembleLotteryStrategy`

1. 取所有奖品概率的 **最小值** `minRate`；
2. 计算概率总和 `totalRate`，得到区间大小 `range = totalRate / minRate`（向上取整）；
3. 按 `range * awardRate` 向上取整，往数组里塞入对应数量的奖品 ID（奖品概率越大，占位越多）；
4. `Collections.shuffle` 打乱数组，转成 `index → awardId` 的 Map 写入 Redis；
5. 抽奖时 `random.nextInt(range)` 得到下标，直接查表拿到奖品 ID。

> 例如概率 `0.3 / 0.2 / 0.0001`，区间为 `10000`，`随机积分` 占 3000 个位置。抽奖是一次随机数 + 一次哈希查表，**不涉及任何数据库查询**。

### 5.2 责任链：先决定「抽什么」

`domain/strategy/service/rule/chain`

```
BackListLogicChain (rule_blacklist)  →  RuleWeightLogicChain (rule_weight)  →  DefaultLogicChain (default)
```

- **黑名单**：`rule_value = 101:user001,user002`，命中直接返回兜底奖品 ID，链提前结束；
- **权重**：`rule_value = 4000:102,103 5000:102,103,104`，按用户积分解析出奖品范围，调用装配好的「子策略」随机（key = `strategyId_4000`）；
- **默认**：调用默认概率查找表随机。

每个节点只做一件事，新增规则只需实现 `ILogicChain` 并在 `DefaultChainFactory` 注册 `ruleModel → Bean`，**开闭原则**。

### 5.3 规则树：再决定「给不给 / 给哪个」

`domain/strategy/service/rule/tree`

规则树结构存于三张表（`rule_tree` / `rule_tree_node` / `rule_tree_node_line`），运行时由 `DefaultTreeFactory` 组装成 `Map<String, ILogicTreeNode>` 并通过 `IDecisionTreeEngine` 沿边流转：

| 节点 | 作用 | 出边条件 |
| --- | --- | --- |
| `rule_lock` | 次数锁：当天抽奖次数 ≥ 配置值才放行 | `ALLOW` / `TAKE_OVER` |
| `rule_stock` | 库存扣减：Redis 原子扣减成功则接管返回该奖品 | `ALLOW`（库存不足，继续走兜底） |
| `rule_luck_award` | 兜底奖品：返回配置的保底奖品 ID | 终结节点 |

> 这样「抽到小米 SU7」这种大奖，可以被配置成「抽奖 3 次后解锁」+「库存 100 件」+「兜底为随机积分」，全部是数据配置。

### 5.4 活动账户额度：三级防超领

`AbstractRaffleActivityPartake#createOrder`

1. 校验活动状态 `open` 与活动起止时间；
2. 查询**未使用**的抽奖单，存在则直接复用（幂等）；
3. 扣减额度前依次校验：**总剩余 → 月剩余 → 日剩余**，任一不足抛业务异常（`ERR_BIZ_006/007/008`）；
4. 月/日账户不存在则按活动配置初始化；
5. 构建 `CreatePartakeOrderAggregate` 聚合，**一次事务**完成「订单 + 额度 + 流水」写入。

### 5.5 库存与最终一致

```
抽奖 → Redis DECR 库存（原子、防超卖）
        │
        ├─ 扣减成功 → 写入本地延迟队列 → @Scheduled 每 5s 批量更新 MySQL
        │
        └─ 库存归零 → 发送 MQ「activity_sku_stock_zero」→ 消费者清理缓存 + 停止延迟更新
```

奖品库存同理：`UpdateAwardStockJob` 每 5 秒从延迟队列取一条，异步刷库，**降低数据库写压力、避免行锁竞争**。

发奖则通过 `task` 任务表 + `SendMessageTaskJob`（每 5s 扫全部库表）实现**本地消息表 + 定时补偿**，保证抽奖成功后消息一定投递到 `send_award` 队列。

### 5.6 分库分表

- `dbCount = 2`、`tbCount = 4`，路由键 `userId`；
- 库：`big_market`（配置类，单库）、`big_market_01`、`big_market_02`（分片业务表）；
- 分片表：`raffle_activity_order_000~003`、`user_award_record_000~003`、`user_raffle_order_000~003`；
- 路由规则：`dbIdx = userId.hashCode() % dbCount`，`tbIdx = userId.hashCode() / dbCount % tbCount`。

---

## 六、数据库设计

初始化脚本位于 `docs/dev-ops/environment/mysql/sql/`，会建立 3 个库：

| 库 | 表 | 用途 |
| --- | --- | --- |
| `big_market` | `award`、`raffle_activity`、`raffle_activity_count`、`raffle_activity_sku`、`strategy`、`strategy_award`、`strategy_rule`、`rule_tree`、`rule_tree_node`、`rule_tree_node_line` | 活动/策略/奖品的**配置主数据** |
| `big_market_01` | `raffle_activity_account`、`raffle_activity_account_day`、`raffle_activity_account_month`、`raffle_activity_order_000~003`、`user_raffle_order_000~003`、`user_award_record_000~003`、`task` | **分片业务数据**（db01） |
| `big_market_02` | 同 `big_market_01` | **分片业务数据**（db02） |

### 内置示例数据（可直接用于联调）

| 项 | 值 |
| --- | --- |
| 活动 ID | `100301`（测试活动，`state = open`，有效期至 2034 年） |
| 绑定的策略 ID | `100006`（规则树策略，8 个奖品） |
| 活动 SKU | `9011`，活动库存 100000，额度账户 `11101`（总 10000 / 日 1000 / 月 1000） |
| 奖品 | 随机积分、OpenAI 会员卡、支付优惠券、小米台灯、小米 SU7 周体验（抽 3 次解锁）、轻奢办公椅（抽 2 次解锁）、小霸王游戏机（抽 1 次解锁）、暴走玩偶 |
| 其他策略 | `100001`（黑名单 + 权重演示）、`100002~100005`（概率/随机/测试策略） |

---

## 七、接口文档

统一返回体：

```json
{ "code": "0000", "info": "成功", "data": {} }
```

错误码见 `cn.bugstack.types.enums.ResponseCode`（`0000` 成功、`0001` 未知失败、`0002` 非法参数、`ERR_BIZ_00x` 业务异常）。

| 方法 | 路径 | 说明 |
| --- | --- | --- |
| GET | `/api/v1/raffle/activity/armory?activityId=100301` | 活动装配（活动 SKU + 策略一起预热到 Redis） |
| POST | `/api/v1/raffle/activity/draw` | **活动抽奖**（走完整链路） |
| GET | `/api/v1/raffle/strategy/strategy_armory?strategyId=100001` | 仅装配某个策略 |
| POST | `/api/v1/raffle/strategy/query_raffle_award_list` | 查询奖品列表（含解锁状态、还需抽奖次数） |
| POST | `/api/v1/raffle/strategy/random_raffle` | 纯策略随机抽奖（不走活动，调试用） |

**curl 示例**

```bash
# 1) 装配活动（必须先执行，否则抽奖会提示未装配）
curl "http://127.0.0.1:8091/api/v1/raffle/activity/armory?activityId=100301"

# 2) 抽奖
curl -X POST "http://127.0.0.1:8091/api/v1/raffle/activity/draw" \
     -H "Content-Type: application/json" \
     -d '{"userId":"xiaofuge","activityId":100301}'

# 3) 查询奖品列表（含解锁状态）
curl -X POST "http://127.0.0.1:8091/api/v1/raffle/strategy/query_raffle_award_list" \
     -H "Content-Type: application/json" \
     -d '{"userId":"xiaofuge","activityId":100301}'
```

抽奖成功响应：

```json
{
  "code": "0000",
  "info": "成功",
  "data": { "awardId": 105, "awardTitle": "小米su7周体验", "awardIndex": 5 }
}
```

---

## 八、本地运行（保姆级步骤）

### 8.0 环境要求

| 软件 | 版本 |
| --- | --- |
| JDK | 8（推荐 1.8；更高版本需确认编译 target 兼容） |
| Maven | 3.6+ |
| Docker / Docker Compose | 任意较新版本（用于一键起 MySQL / Redis / RabbitMQ） |
| Node.js | 18+（若要一起跑前端 `big-market-front-dxw`） |

### 8.1 一键启动中间件

```bash
cd docs/dev-ops/environment

# 国内网络可用阿里云镜像版本（推荐）
docker-compose -f docker-compose-environment-aliyun.yml up -d

# 或使用 Docker Hub 官方镜像
docker-compose -f docker-compose-environment.yml up -d
```

启动的容器与端口：

| 容器 | 宿主机端口 | 账号 |
| --- | --- | --- |
| MySQL 8.0.32 | `13306` → 3306 | `root / 123456` |
| phpMyAdmin | `8899` | root / 123456 |
| Redis 6.2 | `16379` → 6379 | 无密码 |
| Redis Commander | `8081` | admin / admin |
| RabbitMQ 3.12.9 | `5672`、管理台 `15672` | admin / admin |

> **数据库自动初始化**：compose 把 `./mysql/sql` 挂载到 `/docker-entrypoint-initdb.d`，首次启动会自动执行 3 个 SQL，创建 `big_market`、`big_market_01`、`big_market_02` 并灌入示例数据。
>
> ⚠️ `docker-compose-environment.yml` 中 `mysql-data` 数据卷默认被注释，容器**重建**会重新初始化数据。需要持久化请取消注释。

等待 MySQL 健康检查通过（约 15~30 秒），确认数据已导入：

```bash
docker exec -it mysql mysql -uroot -p123456 -e "show databases; select activity_id, activity_name, strategy_id, state from big_market.raffle_activity;"
```

### 8.2 编译打包

```bash
# 回到项目根目录
cd ../../..

mvn clean package -DskipTests
```

产物：`big-market-dxw-app/target/big-market-dxw-app.jar`

### 8.3 关于配置（重要，不改也能跑）

`big-market-dxw-app/src/main/resources/application.yml`：

```yaml
spring:
  profiles:
    active: prod   # 默认激活 prod
```

各 profile 的关键差异：

| profile | MySQL 端口 | Redis 端口 | 说明 |
| --- | --- | --- | --- |
| `prod`（**默认**） | `13306` | `16379` | ✅ 与上面的 docker-compose 完全对应，**开箱即用，无需修改** |
| `test` | `13306` | `16379` | 同上 |
| `dev` | `3306` | `16379` | 需本机自建 MySQL 在 3306，或自行改端口 |

配置项位置：`mini-db-router.jdbc.datasource.*`（多数据源路由）、`redis.sdk.config.*`、`spring.rabbitmq.*`。

> 如需切换 profile，修改 `application.yml` 的 `spring.profiles.active`，或启动时加 `--spring.profiles.active=dev`。

### 8.4 启动应用

```bash
java -jar big-market-dxw-app/target/big-market-dxw-app.jar
```

或在 IDEA 中直接运行 `cn.bugstack.Application`。

应用启动后监听 **`http://127.0.0.1:8091`**。
启动日志中可以看到定时任务（每 5 秒）与 RabbitMQ 消费者的注册信息。

### 8.5 验证：装配 + 抽奖

```bash
# 第一步：活动装配（必做，只做一次即可）
curl "http://127.0.0.1:8091/api/v1/raffle/activity/armory?activityId=100301"
# => {"code":"0000","info":"成功","data":true}

# 第二步：抽奖（可重复执行，额度为 10000 次）
curl -X POST "http://127.0.0.1:8091/api/v1/raffle/activity/draw" \
     -H "Content-Type: application/json" \
     -d '{"userId":"xiaofuge","activityId":100301}'
# => {"code":"0000","info":"成功","data":{"awardId":107,"awardTitle":"小霸王游戏机","awardIndex":7}}

# 第三步：查询奖品列表（会显示哪些奖品还需抽奖几次解锁）
curl -X POST "http://127.0.0.1:8091/api/v1/raffle/strategy/query_raffle_award_list" \
     -H "Content-Type: application/json" \
     -d '{"userId":"xiaofuge","activityId":100301}'
```

验证数据落库：

```bash
docker exec -it mysql mysql -uroot -p123456 -e "
  use big_market_01;
  select * from user_raffle_order_000;
  select * from user_award_record_000;
  select * from task;"
```

### 8.6 运行单元测试

测试类位于 `big-market-dxw-app/src/test/java/cn/bugstack/test/`：

| 测试类 | 覆盖内容 |
| --- | --- |
| `domain/strategy/StrategyTest` | 策略装配、概率分布 |
| `domain/strategy/LogicChainTest` / `LogicTreeTest` | 责任链、决策树 |
| `domain/strategy/RaffleStrategyTest` | 完整抽奖 |
| `domain/activity/RaffleActivityPartakeServiceTest` | 活动参与、额度扣减 |
| `domain/award/AwardServiceTest` | 中奖记录与发奖 |
| `infrastructure/*DaoTest` | 各 DAO / 分片 |
| `trigger/RaffleActivityControllerTest` | `armory` + `draw` 接口 |

```bash
# 前置：中间件已启动
mvn -pl big-market-dxw-app test
```

> 注意：`big-market-dxw-app/pom.xml` 中 surefire 配置了 `<skipTests>true</skipTests>`，直接 `mvn test` 会跳过；如需执行请先去掉该配置，或在 IDEA 中单独运行测试方法。

### 8.7 一起跑前端

前端仓库：[`big-market-front-dxw`](https://github.com/dxw2544523082/big-market-front-dxw)

```bash
cd big-market-front-dxw
echo "API_HOST_URL=http://127.0.0.1:8091" > .env.local
npm install
npm run dev
```

访问 <http://localhost:3000/?userId=xiaofuge&activityId=100301>，先点「装配抽奖」，即可玩大转盘 / 九宫格。

---

## 九、Docker 部署

### 9.1 构建后端镜像

`big-market-dxw-app/Dockerfile`：

```dockerfile
FROM eclipse-temurin:8-jre
ADD target/big-market-dxw-app.jar /big-market-dxw-app.jar
ENTRYPOINT ["sh","-c","java -jar $JAVA_OPTS /big-market-dxw-app.jar $PARAMS"]
```

```bash
mvn clean package -DskipTests
cd big-market-dxw-app
docker build -t dxw123/big-market-dxw-app:1.0-SNAPSHOT .
```

### 9.2 前后端 + 中间件整体编排

```bash
cd docs/dev-ops/environment
docker-compose -f docker-compose-app.yml up -d
```

`docker-compose-app.yml` 会同时拉起：

| 服务 | 镜像 | 端口 |
| --- | --- | --- |
| `big-market-app` | `dxw123/big-market-dxw-app:1.0-SNAPSHOT` | 8091 |
| `big-market-front-app` | `dxw123/big-market-front-dxw-app:1.4` | 3000 |

### 9.3 单容器脚本

```bash
docs/dev-ops/app/start.sh   # 启动（默认镜像 system/big-market-dxw:1.0-SNAPSHOT，端口 8091）
docs/dev-ops/app/stop.sh    # 停止
```

---

## 十、常见问题 FAQ

| 现象 | 原因 / 解决 |
| --- | --- |
| `ERR_BIZ_002 抽奖策略配置未装配` | 没有先调用 `armory` 接口，或 Redis 重启导致缓存丢失。重新调用装配接口即可。 |
| `ERR_BIZ_003 活动未开启` | `raffle_activity.state != open`，检查库表。 |
| `ERR_BIZ_004 非活动日期范围` | 当前时间不在 `begin_date_time ~ end_date_time` 之间。 |
| `ERR_BIZ_006/007/008 额度不足` | 总/月/日额度耗尽，重置 `raffle_activity_account*` 表数据。 |
| 连不上 MySQL / Redis | 确认 docker 容器已启动、端口为 `13306` / `16379`，并核对当前激活的 profile。 |
| 抽奖后数据库没有记录 | 中奖记录写入了分片表（如 `user_award_record_000`），且为异步刷库，稍等或查全部分片表。 |
| 数据库数据没初始化 | 首次启动才会执行 `docker-entrypoint-initdb.d`；请删除旧容器后 `docker-compose up -d` 重新初始化。 |

---

## 致谢

- 架构思想与业务场景参考「小傅哥」《大营销平台》项目教程（<https://bugstack.cn>）。
- 本项目代码为个人独立实现版本，用于学习与作品展示。

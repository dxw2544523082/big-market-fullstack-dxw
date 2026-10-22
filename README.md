# 大营销平台 · 前后端整合版

基于 DDD 分层的抽奖活动后端与 Next.js 抽奖页面的**单仓库项目**。`backend/` 和 `frontend/` 均为完整源码，不依赖子模块或其他源码目录。

> 个人学习与实战项目，业务与架构参考小傅哥「大营销平台」（[bugstack.cn](https://bugstack.cn)）；保留原代码署名。它不是抖音官方系统，也不声称具备生产流量或线上压测结果。

## 1. 项目实现了什么

```text
活动和策略预热到 Redis
  → 查询奖品列表及次数解锁条件
  → 校验活动状态、时间、总/月/日抽奖额度
  → 创建或复用用户抽奖订单
  → 责任链抽奖（黑名单 / 权重 / 默认）
  → 规则树过滤（次数锁 / 库存 / 兜底）
  → 同事务写中奖记录、消息任务并标记订单已使用
  → RabbitMQ 发布发奖事件；定时任务补偿未发送消息
```

- **流程编排**：模板方法串联抽奖；责任链与数据库配置的规则树处理不同规则。
- **概率预计算**：按概率构建并打散奖品查找表，写入 Redis 后用随机下标查询。
- **库存处理**：Redis 原子扣减与库存序号 `setNx` 标记；Redisson 延迟队列 + 定时任务异步回写数据库。活动 SKU 耗尽后发 MQ 通知清零。
- **额度与订单**：总/月/日额度账户，事务内扣减额度并创建订单；复用尚未使用的抽奖订单。
- **消息补偿**：中奖记录与 task 表同事务写入，事务外投递；`@Scheduled` 逐库扫描未发送任务并重发。
- **分库分表**：接入 `db-router-spring-boot-starter`，`userId` 路由，2 个业务库、每类分片表每库 4 张。
- **用户页面**：大转盘、九宫格、奖品解锁提示、装配按钮、真实抽奖结果与失败信息；结果由后端返回，不在浏览器随机生成。

### 实现边界（避免误解）

- `SendAwardCustomer` **目前只记录收到的发奖消息**，没有接入真实优惠券、积分、实物履约；中奖记录的 `award_state=create` 不等于奖品已实际发放。
- 权重责任链的用户积分值仍为示例字段，未接真实积分支付、行为返利服务。
- 没有实现 OpenFeign、Nacos、XXL-JOB、Canal、Elasticsearch，也没有宣称万级 QPS 或生产级高可用。
- 本地可验证的是「装配 → 奖品查询 → 抽奖 → 结果展示 → 订单/中奖/任务落库与消息消费日志」。
- 现有库存锁和异步回写是演示方案，不代表已经解决 Redis 故障恢复、跨资源原子性或消息恰好一次语义。

## 2. 技术栈与目录

| 后端 | 前端 | 本地基础设施 |
|---|---|---|
| JDK 8、Spring Boot 2.7.12、Maven | Next.js 16.0.3、React 19、TypeScript | MySQL 8.0.32 |
| MyBatis、db-router 1.0.2 | Tailwind CSS 4、lucky-canvas | Redis 6.2 / Redisson 3.23.4 |
| Spring AMQP（版本跟随 Boot BOM） | 大转盘 / 九宫格 | RabbitMQ 3.12.9、Docker Compose v2 |

```text
backend/                        Maven 聚合工程
  big-market-dxw-api/            接口和 DTO
  big-market-dxw-app/            启动入口、配置、Mapper XML、测试
  big-market-dxw-domain/         活动、抽奖策略、奖品、任务领域
  big-market-dxw-infrastructure/ 仓储、数据库、Redis、消息发布
  big-market-dxw-trigger/        HTTP、MQ 消费者、定时任务
  big-market-dxw-types/          通用返回、错误码、事件模型
frontend/                       Next.js 前端完整源码
infra/mysql/10-demo.sql          独立测试账号初始化
compose.infra.yml               独立、仅绑定本机回环地址的中间件
scripts/dev.py                  构建 / 启停 / 日志管理
scripts/smoke.py                真实 API 与数据库一致性冒烟验证
docs/                           迁移记录、架构说明、验证记录
.env.example                    本地环境变量示例
```

## 3. 从首次克隆到运行

### 3.1 准备环境

- Docker Desktop 已启动，使用 **Linux containers**；`docker compose version` 为 v2。
- **JDK 8**（当前项目目标版本）、Maven 3.8+。
- Node.js **20.9+**（Next.js 16 的最低要求），本次验证为 Node 24.19.0 / npm 11.17.0。
- Python 3.9+，只使用标准库，无额外 Python 依赖。
- 首次构建需要能下载 Maven/npm 依赖和 Docker 镜像。仓库不包含依赖、jar、node_modules。

### 3.2 克隆与配置

```bash
git clone https://github.com/dxw2544523082/big-market-fullstack-dxw.git
cd big-market-fullstack-dxw
```

默认配置无需修改即可运行。需要自定义端口/口令时，先复制环境示例：

```bash
python -c "import shutil; shutil.copyfile('.env.example', '.env')"
```

如果机器默认 Java 不是 JDK 8，在 `.env` 配置：

```dotenv
JAVA8_HOME=C:/Program Files/Java/jdk1.8.0_202
```

脚本也会尝试使用 `JAVA_HOME`，并在 Windows 标准 Java 安装目录查找 JDK 8；没有找到时会明确报错。

### 3.3 一条命令构建并启动

在**仓库根目录**执行（Windows 可用 `python` / `py -3`，Linux/macOS 可用 `python3`）：

```bash
python scripts/dev.py up
```

脚本依次完成：

1. 检查前后端端口未被其他进程占用。
2. 启动隔离的 MySQL / Redis / RabbitMQ，等待健康检查。
3. Maven 编译打包后端，并执行 4 个 Redis 编解码回归测试。
4. `npm ci` 从锁文件安装依赖，执行生产构建和 ESLint。
5. 启动后端与前端，等待**业务装配成功**和前端 HTTP 200。
6. 将进程 PID、构建和运行日志保存在 `.runtime/`（已忽略，不上传）。

打开：

**<http://127.0.0.1:13000/?userId=fullstack_demo&activityId=100301>**

点击「装配抽奖」，看到成功提示后，点击「大转盘抽奖」或「九宫格抽奖」。抽奖动画结束后页面会展示真实后端返回的奖品。

> 请使用 `127.0.0.1`，不要擅自改成 `localhost`：默认 CORS 允许源为 `http://127.0.0.1:13000`。改前端端口请同时修改根 `.env` 并重新构建。

### 3.4 验证接口与落库

```bash
python scripts/smoke.py
```

它不是 Mock：会在演示账号上实际抽奖 1 次，并断言：

- 连续两次装配均成功（覆盖 Redis 缓存反序列化问题）；
- 查询得到 8 个奖品；
- 新抽奖单状态为 `used`，中奖记录的订单号与奖品 ID 对得上；
- 账户额度减少 1 次，task 消息任务新增且为 `completed`；
- 前端页面返回 200。

结果保存在 `.runtime/smoke.json`。此脚本不代替浏览器交互测试；本次浏览器测试记录见 [验证记录](docs/VALIDATION.md)。

### 3.5 端口、测试数据和停止

| 服务 | 默认宿主机端口 |
|---|---|
| 前端 | 13000 |
| 后端 | 18091 |
| MySQL | 23306 |
| Redis | 26379 |
| RabbitMQ AMQP / 管理台 | 25673 / 35673 |

- 所有 Compose 端口仅绑定 `127.0.0.1`，不复用本机已有数据库或 RabbitMQ 服务。
- 默认 MySQL 用户 `root`；RabbitMQ 用户 `bigmarket`；口令在 `.env.example` 中，是**仅供本地演示的公开默认值**，不要用于生产或公网服务。
- 首次创建 MySQL 数据卷时自动初始化 `big_market`、`big_market_01`、`big_market_02`；演示账号 `fullstack_demo` 在两个账户库各预置一条，实际订单只由路由命中的库处理。
- 默认测试活动 `100301`、策略 `100006`、活动有效期至 2034 年。演示账号总额度 1000、日额度 100。
- MySQL 使用命名卷持久化；再次启动不重复执行初始化 SQL。

```bash
python scripts/dev.py down          # 只停止本仓库脚本启动的前后端
python scripts/dev.py down --infra  # 同时停止本仓库 Compose 容器，保留 MySQL 数据卷
```

脚本会核对保存 PID 对应的命令行，避免 PID 被复用后误杀其他项目。不会执行 `docker compose down -v`，也不会清空原项目数据库。

### 3.6 只构建 / 快速重启 / 手动启动

```bash
python scripts/dev.py build
python scripts/dev.py up --skip-build  # 仅限已经在当前目录、同样配置下成功构建
```

不使用 Python 启动器时：

```bash
# 根目录，启动中间件（Compose 会读取根 .env）
docker compose -p big-market-fullstack -f compose.infra.yml up -d --wait

# 终端 1：确保 java -version 是 JDK 8
cd backend
mvn clean package -DskipTests
java -jar big-market-dxw-app/target/big-market-dxw-app.jar --spring.profiles.active=local

# 终端 2，从根目录进入前端
cd frontend
npm ci
npm run build
npm run start -- --hostname 127.0.0.1 --port 13000
```

手动启动时，根 `.env` **不会自动注入 Java/Node 进程**，需自行导出变量。无自定义配置时默认值相互匹配；有自定义配置建议使用 `scripts/dev.py`。

`API_HOST_URL` 是前端**公开的构建期**变量，默认 `http://127.0.0.1:18091`。改动后必须重新 `npm run build`，不能只在 `next start` 时修改。前端没有 Mock 回退地址。开发模式可用 `npm run dev -- --hostname 127.0.0.1 --port 13000`。

## 4. 接口速查

```bash
curl "http://127.0.0.1:18091/api/v1/raffle/activity/armory?activityId=100301"

curl -X POST "http://127.0.0.1:18091/api/v1/raffle/strategy/query_raffle_award_list" \
  -H "Content-Type: application/json" \
  -d '{"userId":"fullstack_demo","activityId":100301}'

curl -X POST "http://127.0.0.1:18091/api/v1/raffle/activity/draw" \
  -H "Content-Type: application/json" \
  -d '{"userId":"fullstack_demo","activityId":100301}'
```

业务成功必须同时满足 HTTP 正常与 JSON `code="0000"`，不能只看 HTTP 200。Windows PowerShell 可使用 `curl.exe` 或 `Invoke-RestMethod`。

## 5. 常见问题

| 问题 | 排查方式 |
|---|---|
| Docker daemon 无法连接 | 先启动 Docker Desktop，确认 `docker version` 有 Server 信息 |
| 端口被占用 | 先 `python scripts/dev.py down`；若为其他项目，不要误杀，调整 `.env` |
| npm 下载 ECONNRESET | 本仓库 `.npmrc` 使用官方 registry，并替换旧锁文件里的镜像主机；检查自己的网络/代理，不复制他人代理设置 |
| Java 版本错误 | 为脚本设置 `JAVA8_HOME`，手动启动时确认当前 shell 的 `JAVA_HOME` |
| `0001` / `ClassCastException` | 检查 `.runtime/backend.log`；本次已修复 Redis 领域对象类型恢复，并有回归测试 |
| `ERR_BIZ_006/007/008` | 新用户没有额度，或总/月/日额度用尽；先使用预置账号，不要连接生产库重置数据 |
| 修改口令后 MySQL 不认 | 已有数据卷不会因修改环境变量自动修改数据库口令，需显式管理自己的测试卷 |
| 改前端接口地址不生效 | 它是构建期值，需要重新构建；脚本会根据 `BACKEND_PORT` 注入 |
| 启动后没有实际发券/积分 | 当前消费者只打印发奖事件，不是已实现真实履约 |

## 6. 历史、迁移和已知限制

- 默认 `main`：完整整合项目；`backend-*`：20 个后端历史分支；`frontend-*`：3 个前端历史分支。历史分支保持当时的独立项目布局，不作为整合启动入口。
- 历史使用 Git subtree 非 squash 合入；为了避免继续公开旧配置中的非通用口令，对整合副本进行了历史脱敏，受影响提交哈希变化，但分支和开发过程保留。原始完整历史、源码与映射均有本地备份。
- **按用户最新要求，两个旧 GitHub 仓库保留，不删除、不改写；本地原目录同样保留。** 旧公开仓库中的历史口令不会因新仓库脱敏自动消失，若曾用于真实环境，应自行轮换。
- 本次修复了 Boot 2.7 与 AMQP 3.x 混用、Redis 缓存类型恢复、前端网络异常处理和 Mock 回退，移除了构建时 Google 字体/外部背景图片依赖。
- `backend/docs/dev-ops/` 下旧 compose 和脚本是历史材料，**不要作为整合版启动入口**；使用仓库根的 `compose.infra.yml` 和 Python 脚本。
- 本次以宿主机运行前后端、Docker 运行中间件为验收路径；未将旧应用 Dockerfile 宣称为已通过的全容器部署。
- 使用已有版本验证运行，没有完成所有依赖安全升级、鉴权、防刷、限流或压力测试；仅供隔离的本地学习演示。

更多：[架构说明](docs/ARCHITECTURE.md) · [迁移说明](docs/MIGRATION.md) · [验证记录](docs/VALIDATION.md)

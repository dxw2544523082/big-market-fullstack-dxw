# 实际验证记录

验证日期：2026-10-22。以下仅记录已经执行并检查结果的步骤，不把“编译成功”当作“业务可用”。

## 第一轮：本地整合目录

| 项目 | 结果 |
|---|---|
| MySQL 8.0.32 / Redis 6.2 / RabbitMQ 3.12.9 独立 Compose | 全部 healthy，仅绑定回环地址 |
| JDK 8 + Maven 后端构建 | BUILD SUCCESS |
| RedisCodecTest | 4 项通过，0 failures / errors |
| Node 24.19.0 / npm 11.17.0，npm ci | 成功；独立安装，不复制原 node_modules |
| Next.js 生产构建 / TypeScript | 通过 |
| ESLint | 通过 |
| 实际启动 | 后端 18091，前端 13000 |
| 活动装配及再次缓存命中 | 均 code=0000 |
| 奖品列表 | 8 个奖品，来自真实后端 |
| 自动 API 冒烟 | 连续两次抽奖，与订单、中奖、任务、额度对账通过 |
| Playwright 页面 | 两个 canvas，实际点击装配、大转盘和九宫格 |
| 大转盘 | 奖品 108：暴走玩偶，页面与 HTTP JSON 一致 |
| 九宫格 | 奖品 101：随机积分，页面与 HTTP JSON 一致 |
| 浏览器抽奖落库 | 2 笔新订单均 used，中奖记录对应正确，额度减少 2 |
| 消息任务 | 对应 task=completed，并在 SendAwardCustomer 日志确认消费 |
| 错误检查 | 浏览器 console errors=0；修复后该轮 backend.log 无 ERROR/Exception |

### 实际发现并修复的故障

1. 原编码器写入类型信息，但读取后得到 JSONObject；重复装配与奖品查询触发 ClassCastException。
2. 改为 Fastjson2 受限类型恢复后，浏览器重复抽奖又命中嵌套 typed Map 的类型元数据解析问题。
3. 新增 RuleTreeVO + HashMap + 中文用例，先复现失败；避免冗余集合类型信息后 4 项回归全部通过。
4. 仅失效独立测试 Redis 的规则树缓存；失败时留下的未使用订单复用成功，未二次扣减额度。
5. npm 旧锁文件依赖镜像 CDN 下载 ECONNRESET；`.npmrc` 切换官方 registry 并统一替换历史镜像主机后安装通过。

## 第二轮：GitHub 干净克隆

从公开 GitHub 仓库克隆提交 `4af00ea` 到全新目录，确认不存在 node_modules、target 或私有 .env。使用新的 Compose 项目和全新命名卷初始化三份 SQL 与演示账号，没有复用第一轮数据库。

- `python scripts/dev.py up` 完整执行 Maven 打包、4 项编解码测试、npm ci、生产构建、TypeScript、ESLint并启动成功。
- 2 次 API 抽奖和数据库对账通过。
- 浏览器大转盘返回 106「轻奢办公椅」、九宫格返回 108「暴走玩偶」；页面、HTTP JSON、两笔 used 订单与中奖记录一致，额度减少 2，task 均 completed。
- 后端日志无 ERROR/Exception；克隆工作区仍干净。
- 对特殊依赖 `db-router-spring-boot-starter:1.0.2` 另外从 POM 声明的公共仓库下载 JAR，HTTP 200，SHA256 与实际使用的 JAR 相同，未依赖不可获取的本地私有安装。
- 此验证为同机干净源码克隆，允许复用 Maven/npm 下载缓存，不冒称已在另一台空白机器上验证。

## 前端依赖修补与运行回归

初始生产依赖审计发现 1 critical + 4 high，已升级 Next.js `16.4.2`、React/React DOM `19.3.1`，更新配套 ESLint 配置及锁文件。

- `npm audit --omit=dev`：**0 漏洞**。
- 生产构建、ESLint、独立 `tsc --noEmit`：均通过。
- 修补后真实 API 抽奖及落库检查通过；浏览器大转盘 101「随机积分」、九宫格 106「轻奢办公椅」，**两边均等待动画真正结束**，控件恢复可点击且页面、接口、数据库一致。
- 回归中发现 lucky-canvas 在约 1 FPS 的节流环境中可能选择零减速距离，导致九宫格不结束。已调整安全动画参数、稳定传入 props，并增加超时保护：先展示真实后端结果，超时提示刷新而非自动重试抽奖。
- 完整 `npm audit` 仍报告 5 个开发依赖高危条目，源头为 [braces 深度嵌套模式拒绝服务](https://github.com/advisories/GHSA-vfj7-8cjw-p6xm)，经 micromatch / fast-glob / Next ESLint 配置传播。当前自动修复建议降级到不兼容的 ESLint 配置主版本，故不盲目 `--force`。请只在可信源码上运行开发工具；这不是生产运行依赖的漏洞清零声明。

## 最终修补版再次干净克隆：通过

从 GitHub 再次克隆最终代码提交 `54ef049` 至另一个全新目录，仍确认无依赖、产物和私有配置；使用新的 `big-market-fullstack-verify-final` Compose 项目及**全新** MySQL 命名卷。

| 最终版验证项 | 结果 |
|---|---|
| 根 README 启动流程 `python scripts/dev.py up` | 完整构建与启动成功 |
| 后端 / 4 项编解码回归 | BUILD SUCCESS，4 passed / 0 failures / 0 errors |
| npm ci / Next.js 16.4.2 生产构建 / ESLint / 独立 tsc | 全部通过 |
| 生产依赖审计 | 0 漏洞 |
| 连续装配 / 奖品列表 / 2 次 API 抽奖与落库 | 全部通过，额度减少 2 |
| 浏览器大转盘 | 106「轻奢办公椅」，真实动画完成且按钮恢复 |
| 浏览器九宫格 | 101「随机积分」，真实动画完成且按钮恢复 |
| 页面、HTTP JSON 与 MySQL | 两笔新订单 used，中奖记录与奖品一致，task completed，额度减少 2 |
| 页面运行错误 / 后端异常 | 0 page errors；backend.log 无 ERROR/Exception |
| Git 工作区 | 构建与运行后仍干净 |

浏览器该轮订单为 `581074226390`、`253185111522`，仅是隔离演示数据，不是实际权益发放。最终截图和原始 JSON/日志保存在该验证目录 `.runtime/`，仓库截图为同版代码的本地回归记录。

最终功能代码已验证；后续提交仅补充此验证记录，不改变可执行代码。

## 证据与范围

原始构建日志、测试报告、API JSON、页面截图、浏览器响应与数据库对账结果保存在本机 `.runtime/`，不上传运行日志或本地敏感配置。

本次未进行性能压力测试、生产部署、全部历史 JUnit4 集成测试或真实奖品履约。task=completed 表示本地消息发送记录完成，不等于用户已实际收到优惠券/积分/实物。

两个旧 GitHub 仓库和本地原始目录均保留，不执行删除。

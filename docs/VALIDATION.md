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

待仓库上传后，在全新克隆目录和全新的独立 Compose 数据卷上重复构建、启动、接口/数据库和浏览器联调；未完成前不标记通过。

## 证据与范围

原始构建日志、测试报告、API JSON、页面截图、浏览器响应与数据库对账结果保存在本机 `.runtime/`，不上传运行日志或本地敏感配置。

本次未进行性能压力测试、生产部署、全部历史 JUnit4 集成测试或真实奖品履约。task=completed 表示本地消息发送记录完成，不等于用户已实际收到优惠券/积分/实物。

两个旧 GitHub 仓库和本地原始目录均保留，不执行删除。

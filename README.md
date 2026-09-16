# big-market-front-dxw · 大营销平台前端（抽奖展示）

> 基于 **Next.js 16 + React 19 + TypeScript + Tailwind CSS 4** 的抽奖活动前端，对接 [`big-market-dxw`](https://github.com/dxw2544523082/big-market-dxw) 后端。
>
> 一个页面同时提供 **大转盘** 与 **九宫格** 两种抽奖玩法，支持「活动装配 → 查询奖品列表 → 实时抽奖 → 动效揭晓结果」的完整闭环。

---

## 目录

- [一、项目是做什么的](#一项目是做什么的)
- [二、功能清单](#二功能清单)
- [三、技术栈](#三技术栈)
- [四、目录结构](#四目录结构)
- [五、与后端的接口对照](#五与后端的接口对照)
- [六、本地运行](#六本地运行)
- [七、联调步骤](#七联调步骤)
- [八、Docker 构建与部署](#八docker-构建与部署)
- [九、常见问题 FAQ](#九常见问题-faq)

---

## 一、项目是做什么的

这是「大营销平台」项目的**用户端抽奖页面**。用户打开一个带参数的链接：

```
http://localhost:3000/?userId=xiaofuge&activityId=100301
```

页面会：

1. 读取 URL 上的 `userId`（用户）和 `activityId`（活动）；
2. 调用后端查询该活动的**奖品列表**，按配置渲染到大转盘 / 九宫格上；
3. 用户点「装配抽奖」→ 触发后端把活动与策略概率预热进 Redis；
4. 用户点「开始」→ 转盘/九宫格转动 → 调用后端**真实抽奖接口** → 按服务端返回的中奖下标停在中奖格子上，并弹出中奖提示；
5. 九宫格还会根据后端返回的 `isAwardUnlock` / `waitUnLockCount`，对「抽奖 N 次后解锁」的奖品展示**上锁图标**与「再抽奖 N 次解锁」文案。

所有抽奖规则、概率、解锁条件都由后端数据库配置决定，**前端只负责展示与交互**。

---

## 二、功能清单

| 功能 | 实现位置 |
| --- | --- |
| 大转盘抽奖 | `src/app/pages/lucky/lucky-wheel-page.tsx`（`@lucky-canvas/react` 的 `LuckyWheel`） |
| 九宫格抽奖 | `src/app/pages/lucky/lucky-grid-page.tsx`（`LuckyGrid`，3 × 3） |
| 活动装配按钮 | `src/app/components/StrategyArmory.tsx`（动态 import，按需加载） |
| 奖品列表查询与渲染 | 调用 `/api/v1/raffle/strategy/query_raffle_award_list` |
| 服务端真实抽奖 + 停格定位 | 调用 `/api/v1/raffle/activity/draw`，用返回的 `awardIndex` 控制停止位置 |
| 奖品解锁状态展示 | `isAwardUnlock === false` 时显示锁图与「再抽奖 N 次解锁」 |
| 抽奖动效 | 点击后先 `play()` 转 2.5 秒，同时并发请求抽奖接口，拿到结果后 `stop(index)` |

---

## 三、技术栈

| 分类 | 选型 |
| --- | --- |
| 框架 | Next.js `16.0.3`（App Router + Turbopack） |
| UI 库 | React `19.2.0`、React DOM `19.2.0` |
| 语言 | TypeScript 5 |
| 样式 | Tailwind CSS 4（`@tailwindcss/postcss`） |
| 抽奖组件 | `@lucky-canvas/react` `0.1.13`（大转盘 / 九宫格 / 老虎机） |
| 编译增强 | `babel-plugin-react-compiler`（React Compiler） |
| 代码规范 | ESLint 9 + `eslint-config-next` |
| 部署 | Docker 多阶段构建（`output: "standalone"`） |

---

## 四、目录结构

```
big-market-front-dxw
├── public/
│   ├── raffle-award-00.png ~ raffle-award-22.png   # 九宫格各格子奖品图
│   ├── raffle-award-2x-lock.png                    # 上锁状态奖品图
│   ├── raffle-award.png                            # 中奖高亮图（activeSrc）
│   ├── raffle-button.png                           # 九宫格中间「抽奖」按钮图
│   └── background.svg
│
├── src/
│   ├── apis/
│   │   └── index.tsx                 # 全部后端接口封装（装配 / 奖品列表 / 抽奖）
│   ├── app/
│   │   ├── layout.tsx                # 根布局、字体、页面 metadata
│   │   ├── page.tsx                  # 首页：装配按钮 + 大转盘 + 九宫格
│   │   ├── globals.css
│   │   └── components/
│   │       └── StrategyArmory.tsx    # 「装配抽奖」按钮组件
│   ├── app/pages/lucky/
│   │   ├── lucky-wheel-page.tsx      # 大转盘实现
│   │   └── lucky-grid-page.tsx       # 九宫格实现
│   └── types/
│       └── RaffleAwardVO.ts          # 奖品值对象类型定义
│
├── .env.local            # 本地接口地址（已被 .gitignore 忽略，不提交）
├── next.config.ts        # standalone 输出 + 注入 API_HOST_URL
├── Dockerfile            # 多阶段构建镜像
└── build.sh              # 一键 docker build 脚本
```

---

## 五、与后端的接口对照

前端所有请求集中在 `src/apis/index.tsx`，基地址来自环境变量 `API_HOST_URL`。

| 前端方法 | 后端接口 | 入参 | 说明 |
| --- | --- | --- | --- |
| `strategyArmory(activityId)` | `GET /api/v1/raffle/activity/armory` | `activityId` | 活动装配，把活动 SKU 与策略概率预热到 Redis |
| `queryRaffleAwardList(userId, activityId)` | `POST /api/v1/raffle/strategy/query_raffle_award_list` | `{ userId, activityId }` | 查询奖品列表（含解锁状态、还需抽奖次数） |
| `draw(userId, activityId)` | `POST /api/v1/raffle/activity/draw` | `{ userId, activityId }` | 执行抽奖，返回 `awardId / awardTitle / awardIndex` |

统一响应格式：

```json
{ "code": "0000", "info": "成功", "data": {} }
```

`code === "0000"` 表示成功，其他为失败（前端会 `alert` 出错误码与信息）。

> `awardIndex` 是奖品在活动奖品列表中的**序号（从 1 开始）**，前端用 `awardIndex - 1` 换算成组件需要的下标来停格。

---

## 六、本地运行

### 6.1 环境要求

| 软件 | 版本 |
| --- | --- |
| Node.js | 18 及以上（本项目在 Node 24 上验证通过） |
| npm | 9 及以上 |
| 后端 | 需要 `big-market-dxw` 后端已启动在 `8091` 端口 |

### 6.2 安装依赖

```bash
cd big-market-front-dxw
npm install
```

### 6.3 配置接口地址

项目读取环境变量 `API_HOST_URL`。在项目根目录新建 `.env.local`：

```bash
echo "API_HOST_URL=http://127.0.0.1:8091" > .env.local
```

> `.env.local` 已被 `.gitignore` 忽略，不会提交到仓库，所以**克隆后必须自己创建**。
> 不配置时会自动回退到内置的 Apifox Mock 地址，只能看到界面、无法真实抽奖。

### 6.4 启动开发服务

```bash
npm run dev
```

打开 <http://localhost:3000>。注意必须带上 URL 参数，否则页面会提示配置 `activityId`：

```
http://localhost:3000/?userId=xiaofuge&activityId=100301
```

### 6.5 其他命令

```bash
npm run build   # 生产构建（含 TypeScript 类型检查）
npm run start   # 运行生产构建产物
npm run lint    # ESLint 检查
```

---

## 七、联调步骤

完整跑通一次抽奖：

```bash
# ── 第 0 步：启动后端依赖与后端服务 ──────────────────────────
# 见 big-market-dxw 仓库 docs/dev-ops/environment/docker-compose-environment.yml
# 后端启动后监听 http://127.0.0.1:8091

# ── 第 1 步：启动前端 ────────────────────────────────────────
cd big-market-front-dxw
npm install
echo "API_HOST_URL=http://127.0.0.1:8091" > .env.local
npm run dev
```

浏览器访问：

```
http://localhost:3000/?userId=xiaofuge&activityId=100301
```

1. 点击 **「装配抽奖」** → 弹出「抽奖策略装配成功」提示（这一步不做，抽奖会返回 `ERR_BIZ_002 抽奖策略配置未装配`）；
2. 点击左侧**大转盘**或右侧**九宫格**中间的「开始」按钮；
3. 等待约 2.5 秒，指针停在中奖格子并弹出中奖奖品名称；
4. 九宫格中「抽奖 1/2/3 次后解锁」的奖品，会随抽奖次数增加自动解锁（页面会重新拉取奖品列表刷新图标）。

> 内置示例活动 `100301` 绑定的策略提供了 8 个奖品，额度为总 10000 次 / 日 1000 次 / 月 1000 次，足够反复测试。

---

## 八、Docker 构建与部署

### 8.1 关键点：`API_HOST_URL` 是**构建期**变量

因为 `src/apis/index.tsx` 运行在客户端，Next.js 会在 `next build` 时把 `API_HOST_URL` **内联进静态产物**。
所以必须在**构建镜像时**传入，运行时再设置环境变量是无效的。

`Dockerfile` 中已声明：

```dockerfile
ARG API_HOST_URL=http://127.0.0.1:8091
ENV API_HOST_URL=$API_HOST_URL
```

### 8.2 构建镜像

```bash
docker build \
  --build-arg API_HOST_URL=http://你的服务器IP:8091 \
  -t dxw123/big-market-front-dxw-app:1.4 .
```

或修改 `build.sh` 后再执行：

```bash
cat build.sh
# docker build -t dxw123/big-market-front-dxw-app:1.4 .
bash build.sh
```

### 8.3 与后端一起编排启动

后端仓库提供 `docs/dev-ops/environment/docker-compose-app.yml`，会同时拉起后端（8091）与前端（3000）：

```bash
cd big-market-dxw/docs/dev-ops/environment
docker-compose -f docker-compose-app.yml up -d
```

> ⚠️ `docker-compose-app.yml` 里给前端传的 `API_HOST_URL` 是**运行时**变量。如果你的镜像不是用对应的 `--build-arg` 构建的，前端仍会访问构建时写死的地址。请确保二者一致。

---

## 九、常见问题 FAQ

| 现象 | 原因 / 解决 |
| --- | --- |
| 点「装配抽奖」提示「请在请求地址中配置 activityId」 | URL 少了参数，访问 `/?userId=xxx&activityId=100301`。 |
| 提示「获取抽奖奖品列表失败 code:0002」 | 请求参数不对（缺少 `userId` 或 `activityId`），或后端未启动。 |
| 提示 `ERR_BIZ_002 抽奖策略配置未装配` | 没有先点「装配抽奖」，或 Redis 重启导致缓存丢失。 |
| 提示 `ERR_BIZ_003 / ERR_BIZ_004` | 活动非 `open` 状态，或当前时间不在活动起止时间内。 |
| 提示 `ERR_BIZ_006/007/008 额度不足` | 用户总/月/日抽奖额度已耗尽，重置后端 `raffle_activity_account*` 表数据。 |
| 页面能打开但抽奖结果和配置对不上 | `API_HOST_URL` 指向了 Mock 地址或旧后端；检查 `.env.local` 并**重启 dev server**。 |
| 改了 `.env.local` 不生效 | Next.js 只在启动时读取环境变量，改完必须重启 `npm run dev`。 |
| Docker 里接口地址不对 | `API_HOST_URL` 必须通过 `--build-arg` 在**构建时**传入，见第 8 节。 |
| 九宫格奖品图不显示 | 确认 `public/raffle-award-*.png` 已随仓库提交（这些图已包含在仓库中）。 |

---

## 相关仓库

- 后端：[`big-market-dxw`](https://github.com/dxw2544523082/big-market-dxw) —— DDD 分层的大营销抽奖平台服务端

## 致谢

- 界面玩法与素材布局参考「小傅哥」《大营销平台》项目教程（<https://bugstack.cn>）。
- 本项目代码为个人独立实现版本，用于学习与作品展示。

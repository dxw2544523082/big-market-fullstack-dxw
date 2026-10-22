# 抽奖前端

Next.js 16 + React 19 + TypeScript + Tailwind CSS 4 + lucky-canvas。

完整运行说明见[根 README](../README.md)。默认连接真实后端 `http://127.0.0.1:18091`，没有 Mock 回退。

```bash
# 先从仓库根执行 python scripts/dev.py up，或单独启动后端和中间件
cd frontend
npm ci
npm run build
npm run start -- --hostname 127.0.0.1 --port 13000
```

打开 <http://127.0.0.1:13000/?userId=fullstack_demo&activityId=100301>，点击装配，再点击大转盘或九宫格抽奖。缺省参数使用同一演示账号和活动。

- Node.js 最低 20.9；`.npmrc` 覆盖旧锁文件中的镜像主机，使用官方 registry。
- `API_HOST_URL` 是公开的**构建期**变量；自定义时复制 `.env.example` 为 `.env.local`，改完重新 build。
- `src/apis/index.tsx`：真实 API、业务码校验、网络错误处理。
- `src/app/components/RafflePanel.tsx`：两种抽奖 UI 共用流程，按后端奖品 ID 停格并显示结果。
- 构建不依赖 Google 字体或外部背景图片。
- `npm run lint`：ESLint；`npm run build` 同时执行 TypeScript 检查。
- 旧 Dockerfile 保留参考，本次验收路径为宿主机运行前后端、Docker 运行中间件，不声称已验证应用容器构建。

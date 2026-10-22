FROM node:20-alpine AS base

FROM base AS deps
RUN apk add --no-cache libc6-compat
WORKDIR /app

COPY package.json yarn.lock* package-lock.json* pnpm-lock.yaml* ./

RUN yarn config set registry 'https://registry.npmmirror.com/'
RUN yarn install

FROM base AS builder
WORKDIR /app
# API_HOST_URL 必须是「构建期」变量：Next.js 会在 build 时把它内联进客户端产物，
# 运行时再传环境变量已经来不及了。
ARG API_HOST_URL=http://127.0.0.1:18091
ENV API_HOST_URL=$API_HOST_URL
COPY --from=deps /app/node_modules ./node_modules
COPY . .

RUN yarn build

FROM base AS runner
WORKDIR /app

COPY --from=builder /app/public ./public
COPY --from=builder /app/.next/standalone ./
COPY --from=builder /app/.next/static ./.next/static
COPY --from=builder /app/.next/server ./.next/server

EXPOSE 3000
ENV PORT 3000
ENV HOSTNAME "0.0.0.0"

CMD ["node", "server.js"]
import type {Metadata} from "next";
import "./globals.css";

export const metadata: Metadata = {
    title: "大营销平台 · 前后端整合演示",
    description: "DDD 抽奖活动后端与大转盘、九宫格前端的真实联调演示",
};

export default function RootLayout({children}: Readonly<{children: React.ReactNode}>) {
    // System fonts keep production builds independent of Google's font service.
    return <html lang="zh-CN"><body>{children}</body></html>;
}

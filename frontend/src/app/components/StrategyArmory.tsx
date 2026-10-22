"use client";

import {useState} from "react";
import {getActivityContext, readResponse, strategyArmory} from "@/apis";

export function StrategyArmory() {
    const [busy, setBusy] = useState(false);
    const [status, setStatus] = useState("请先装配活动，再点击抽奖。默认演示用户 fullstack_demo，活动 100301。");
    async function assemble() {
        setBusy(true);
        try {
            const {activityId} = getActivityContext();
            await readResponse<boolean>(strategyArmory(activityId));
            setStatus("活动装配成功，可以开始抽奖。");
        } catch (error) {
            setStatus(error instanceof Error ? error.message : "装配失败");
        } finally {
            setBusy(false);
        }
    }
    return <section className="mb-8 text-center">
        <button type="button" disabled={busy} onClick={assemble}
                className="px-6 py-2 text-white bg-blue-600 rounded-full disabled:opacity-50">
            {busy ? "正在装配…" : "装配抽奖"}
        </button>
        <p role="status" className="mt-3 text-sm text-gray-600">{status}</p>
    </section>;
}

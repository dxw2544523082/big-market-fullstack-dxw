"use client";

import {useEffect, useRef, useState} from "react";
import {LuckyGrid, LuckyWheel, type LuckyHandle} from "@lucky-canvas/react";
import {draw, getActivityContext, queryRaffleAwardList, readResponse} from "@/apis";
import type {DrawResult, RaffleAwardVO} from "@/types/RaffleAwardVO";

const positions = [[0,0],[1,0],[2,0],[2,1],[2,2],[1,2],[0,2],[0,1]];
const imageNames = ["00","01","02","12","22","21","20","10"];

export function RafflePanel({mode}: {mode: "wheel" | "grid"}) {
    const [awards, setAwards] = useState<RaffleAwardVO[]>([]);
    const [busy, setBusy] = useState(false);
    const [status, setStatus] = useState("正在加载奖品列表…");
    const lucky = useRef<LuckyHandle>(null);
    const inFlight = useRef(false);
    const result = useRef<DrawResult | null>(null);
    const timer = useRef<ReturnType<typeof setTimeout> | null>(null);
    const title = mode === "wheel" ? "大转盘" : "九宫格";

    async function loadAwards() {
        const {userId, activityId} = getActivityContext();
        const data = await readResponse<RaffleAwardVO[]>(queryRaffleAwardList(userId, activityId));
        const sorted = [...data].sort((a,b) => a.sort - b.sort);
        if (mode === "grid" && sorted.length !== 8) throw new Error("九宫格需要配置 8 个奖品");
        setAwards(sorted);
        return sorted;
    }

    useEffect(() => {
        let active = true;
        async function load() {
            try {
                const {userId, activityId} = getActivityContext();
                const data = await readResponse<RaffleAwardVO[]>(queryRaffleAwardList(userId, activityId));
                if (!active) return;
                if (mode === "grid" && data.length !== 8) throw new Error("九宫格需要配置 8 个奖品");
                setAwards([...data].sort((a,b) => a.sort - b.sort));
                setStatus("奖品已加载，请先装配活动后抽奖。");
            } catch (error) {
                if (active) setStatus(error instanceof Error ? error.message : "奖品加载失败");
            }
        }
        void load();
        return () => { active = false; if (timer.current) clearTimeout(timer.current); };
    }, [mode]);

    async function start() {
        if (inFlight.current || !awards.length) return;
        inFlight.current = true;
        setBusy(true);
        setStatus("正在向后端请求抽奖结果…");
        try {
            const {userId, activityId} = getActivityContext();
            const data = await readResponse<DrawResult>(draw(userId, activityId));
            const index = awards.findIndex(award => award.awardId === data.awardId);
            if (index < 0) throw new Error("中奖奖品未在当前列表中，请刷新页面");
            result.current = data;
            lucky.current?.play();
            timer.current = setTimeout(() => lucky.current?.stop(index), 800);
        } catch (error) {
            setStatus(error instanceof Error ? error.message : "抽奖失败");
            inFlight.current = false;
            setBusy(false);
        }
    }

    function finish() {
        const data = result.current;
        if (data) setStatus(`恭喜抽中【${data.awardTitle}】，奖品 ID：${data.awardId}`);
        inFlight.current = false;
        setBusy(false);
        void loadAwards().catch(() => { /* Keep the successful result visible if refresh fails. */ });
    }

    const wheelPrizes = awards.map((award,index) => ({
        background: index % 2 === 0 ? "#e9e8fe" : "#b8c5f2",
        fonts: [{text: award.awardTitle, top: "15px", fontSize: "12px"}],
    }));
    const gridPrizes = awards.map((award,index) => ({
        x: positions[index]?.[0], y: positions[index]?.[1],
        fonts: [{text: award.isAwardUnlock ? award.awardTitle : `再抽${award.waitUnLockCount}次解锁`, top: "80%", fontSize: "11px"}],
        imgs: [{src: `/raffle-award-${imageNames[index]}${!award.isAwardUnlock && [4,5,6].includes(index) ? "-lock" : ""}.png`,
            width: "100px", height: "100px", activeSrc: "/raffle-award.png"}],
    }));

    return <section aria-label={title} className="text-center">
        <h2 className="text-xl font-semibold mb-4">{title}</h2>
        {awards.length > 0 && (mode === "wheel" ?
            <LuckyWheel ref={lucky} width="300px" height="300px" prizes={wheelPrizes}
                        blocks={[{padding: "10px", background: "#869cfa"}]}
                        buttons={[{radius: "30%", background: "#617df2", pointer: true, fonts: [{text: "开始", top: "-10px"}]}]}
                        onStart={() => void start()} onEnd={finish}/> :
            <LuckyGrid ref={lucky} width="300px" height="300px" rows={3} cols={3} prizes={gridPrizes}
                       buttons={[{x: 1,y: 1, imgs: [{src: "/raffle-button.png", width: "100px", height: "100px"}]}]}
                       defaultStyle={{background: "#b8c5f2"}} onStart={() => void start()} onEnd={finish}/>)}
        <button type="button" disabled={busy || !awards.length} onClick={() => void start()}
                className="mt-5 px-5 py-2 bg-blue-600 text-white rounded disabled:opacity-50">
            {busy ? "抽奖中…" : `${title}抽奖`}
        </button>
        <p role="status" data-testid={`${mode}-result`} className="mt-3 max-w-xs text-sm text-gray-700 min-h-10">{status}</p>
    </section>;
}

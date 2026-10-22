// Real backend only. Next.js injects this public API URL at build time.
const apiHostUrl = (process.env.API_HOST_URL || "http://127.0.0.1:18091").replace(/\/$/, "");

async function request(path: string, body?: object): Promise<Response> {
    try {
        return await fetch(`${apiHostUrl}${path}`, {
            method: body ? "POST" : "GET",
            headers: {"Content-Type": "application/json"},
            ...(body ? {body: JSON.stringify(body)} : {}),
            signal: AbortSignal.timeout(15000),
        });
    } catch {
        return new Response(JSON.stringify({code: "NETWORK_ERROR", info: "无法连接后端，请检查服务和 API_HOST_URL", data: null}), {
            status: 503,
            headers: {"Content-Type": "application/json"},
        });
    }
}

export const strategyArmory = (activityId: number) =>
    request(`/api/v1/raffle/activity/armory?activityId=${activityId}`);

export const queryRaffleAwardList = (userId: string, activityId: number) =>
    request("/api/v1/raffle/strategy/query_raffle_award_list", {userId, activityId});

export const draw = (userId: string, activityId: number) =>
    request("/api/v1/raffle/activity/draw", {userId, activityId});

export async function readResponse<T>(response: Promise<Response>): Promise<T> {
    const res = await response;
    const body = await res.json();
    if (!res.ok || body.code !== "0000") throw new Error(`${body.code}: ${body.info}`);
    return body.data as T;
}

export function getActivityContext() {
    const params = new URLSearchParams(window.location.search);
    const userId = params.get("userId")?.trim() || "fullstack_demo";
    const activityId = Number(params.get("activityId") || "100301");
    if (!Number.isSafeInteger(activityId) || activityId <= 0) throw new Error("activityId 必须是正整数");
    return {userId, activityId};
}

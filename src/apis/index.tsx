// 请求地址
const apiHostUrl = process.env.API_HOST_URL ? process.env.API_HOST_URL : "https://console-mock.apipost.cn/mock/6afa907d-6678-45e2-b867-032a11090abd";

/**
 * 统一构造失败响应，避免调用方拿到 undefined 直接崩溃
 */
const buildFailResponse = (info: string) => {
    return new Response(JSON.stringify({code: "0001", info, data: null}), {
        status: 200,
        headers: {'Content-Type': 'application/json'}
    });
}

/**
 * 活动装配（活动 SKU + 抽奖策略一起预热到 Redis）
 * 后端接口：GET /api/v1/raffle/activity/armory?activityId=100301
 * @param activityId 活动ID
 */
export const strategyArmory = (activityId?: number) => {
    try {
        return fetch(`${apiHostUrl}/api/v1/raffle/activity/armory?activityId=${activityId}`, {
            method: 'GET',
            headers: {
                'Content-Type': 'application/json'
            }
        })
    } catch (error) {
        return Promise.resolve(buildFailResponse("调用失败"));
    }
}

/**
 * 查询抽奖奖品列表
 * 后端接口：POST /api/v1/raffle/strategy/query_raffle_award_list
 * @param userId 用户ID
 * @param activityId 活动ID
 */
export const queryRaffleAwardList = (userId?: string, activityId?: number) => {
    try {
        return fetch(`${apiHostUrl}/api/v1/raffle/strategy/query_raffle_award_list`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                userId: userId,
                activityId: activityId
            })
        });
    } catch (error) {
        return Promise.resolve(buildFailResponse("调用失败"));
    }
}

/**
 * 抽奖接口
 * 后端接口：POST /api/v1/raffle/activity/draw
 * @param userId 用户ID
 * @param activityId 活动ID
 *
 * {
 * 	"code": "0000",
 * 	"info": "调用成功",
 * 	"data": {
 * 	    "awardIndex": 1, // awardIndex 获得的是列表中第几个奖品，方便测试使用
 * 		"awardId": 535,
 * 		"awardTitle": "一部手机"
 * 	}
 * }
 */
export const draw = (userId?: string, activityId?: number) => {
    try {
        return fetch(`${apiHostUrl}/api/v1/raffle/activity/draw`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json;charset=utf-8'
            },
            body: JSON.stringify({
                userId: userId,
                activityId: activityId
            })
        })
    } catch (error) {
        return Promise.resolve(buildFailResponse("调用失败"));
    }
}

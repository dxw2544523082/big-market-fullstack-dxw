import {strategyArmory} from "@/apis";

export function StrategyArmory() {
    const strategyArmoryHandle = async () => {
        const queryParams = new URLSearchParams(window.location.search);
        const activityId = Number(queryParams.get('activityId'));
        if (!activityId){
            window.alert("请在请求地址中，配置 activityId 值，如：http://localhost:3000/?activityId=100301")
            return;
        }
        const res = await strategyArmory(activityId);
        const {code, info} = await res.json();
        if (code != "0000") {
            window.alert("抽奖策略装配失败 code:" + code + " info:" + info)
            return;
        }
        window.alert("抽奖策略装配成功，可以开始抽奖啦！")
    }

    return (
        <div
            className="px-6 py-2 mb-8 text-white bg-blue-500 rounded-full shadow-lg hover:bg-blue-600 focus:outline-none focus:ring-2 focus:ring-blue-300"
            style={{cursor: "pointer"}}
            onClick={strategyArmoryHandle}
        >
            装配抽奖
        </div>
    );
}

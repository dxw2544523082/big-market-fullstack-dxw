export interface RaffleAwardVO {
    awardId: number;
    awardTitle: string;
    awardSubtitle?: string;
    sort: number;
    isAwardUnlock: boolean;
    waitUnLockCount: number;
}

export interface DrawResult {
    awardId: number;
    awardTitle: string;
    awardIndex: number;
}

declare module "@lucky-canvas/react" {
    import type {ForwardRefExoticComponent, RefAttributes} from "react";
    export interface LuckyHandle { play(): void; stop(index: number): void; }
    interface LuckyProps {
        width: string;
        height: string;
        prizes: Record<string, unknown>[];
        buttons: Record<string, unknown>[];
        blocks?: Record<string, unknown>[];
        defaultStyle?: Record<string, unknown>;
        rows?: number;
        cols?: number;
        onStart: () => void;
        onEnd: () => void;
    }
    export const LuckyWheel: ForwardRefExoticComponent<LuckyProps & RefAttributes<LuckyHandle>>;
    export const LuckyGrid: ForwardRefExoticComponent<LuckyProps & RefAttributes<LuckyHandle>>;
}

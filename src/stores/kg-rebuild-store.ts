import { create } from "zustand";
import type { GraphPhase } from "@/types/documents";

interface KGRebuildStore {
    rebuilding: boolean;
    totalDocs: number;
    processedDocs: number;
    currentDocName: string;
    currentPhase: GraphPhase | null;
    currentPct: number;
    errors: string[];

    startRebuild(total: number): void;
    setCurrentDoc(name: string): void;
    updateProgress(phase: GraphPhase | null, pct: number): void;
    advanceDocs(): void;
    addError(msg: string): void;
    completeRebuild(): void;
}

export const useKGRebuildStore = create<KGRebuildStore>()((set) => ({
    rebuilding: false,
    totalDocs: 0,
    processedDocs: 0,
    currentDocName: "",
    currentPhase: null,
    currentPct: 0,
    errors: [],

    startRebuild: (total) =>
        set({ rebuilding: true, totalDocs: total, processedDocs: 0, currentDocName: "", currentPhase: null, currentPct: 0, errors: [] }),
    setCurrentDoc: (name) =>
        set({ currentDocName: name, currentPhase: null, currentPct: 0 }),
    updateProgress: (phase, pct) =>
        set({ currentPhase: phase, currentPct: pct }),
    advanceDocs: () =>
        set((s) => ({ processedDocs: s.processedDocs + 1 })),
    addError: (msg) =>
        set((s) => ({ errors: [...s.errors, msg] })),
    completeRebuild: () =>
        set({ rebuilding: false, currentPhase: null }),
}));

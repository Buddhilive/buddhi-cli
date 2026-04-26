import { create } from "zustand";
import type { DocumentStore, GraphPhase } from "@/types/documents";

export const useDocumentStore = create<DocumentStore>()((set) => ({
    docs: {},
    activeCount: 0,

    initDoc(id) {
        set((s) => ({
            docs: {
                ...s.docs,
                [id]: {
                    status: "pending",
                    phase: null,
                    overallPct: 0,
                    graphPct: 0,
                    graphPhase: null,
                    chunkCount: null,
                    entityCount: null,
                    errorMsg: null,
                    graphErrorMsg: null,
                },
            },
            activeCount: s.activeCount + 1,
        }));
    },

    updateProgress(id, phase, overallPct) {
        set((s) => ({
            docs: {
                ...s.docs,
                [id]: {
                    ...s.docs[id],
                    status: "processing",
                    phase,
                    overallPct,
                },
            },
        }));
    },

    completeDoc(id, chunkCount) {
        set((s) => ({
            docs: {
                ...s.docs,
                [id]: {
                    ...s.docs[id],
                    status: "completed",
                    phase: null,
                    overallPct: 100,
                    chunkCount,
                    errorMsg: null,
                },
            },
            activeCount: Math.max(0, s.activeCount - 1),
        }));
    },

    failDoc(id, errorMsg) {
        set((s) => ({
            docs: {
                ...s.docs,
                [id]: {
                    ...s.docs[id],
                    status: "failed",
                    phase: null,
                    errorMsg,
                },
            },
            activeCount: Math.max(0, s.activeCount - 1),
        }));
    },

    updateGraphProgress(id, phase: GraphPhase, pct) {
        set((s) => ({
            docs: {
                ...s.docs,
                [id]: {
                    ...s.docs[id],
                    graphPhase: phase,
                    graphPct: pct,
                },
            },
        }));
    },

    completeGraph(id, entityCount) {
        set((s) => ({
            docs: {
                ...s.docs,
                [id]: {
                    ...s.docs[id],
                    graphPhase: null,
                    graphPct: 100,
                    entityCount,
                },
            },
        }));
    },

    failGraph(id, errorMsg) {
        // Graph failure is non-fatal — document remains vector-searchable.
        // Status and activeCount are unchanged.
        set((s) => ({
            docs: {
                ...s.docs,
                [id]: {
                    ...s.docs[id],
                    graphPhase: null,
                    graphErrorMsg: errorMsg,
                },
            },
        }));
    },

    removeDoc(id) {
        set((s) => {
            const { [id]: removed, ...rest } = s.docs;
            const wasActive =
                removed?.status === "pending" || removed?.status === "processing";
            return {
                docs: rest,
                activeCount: wasActive
                    ? Math.max(0, s.activeCount - 1)
                    : s.activeCount,
            };
        });
    },
}));

/**
 * kg-pipeline-worker.ts
 *
 * Web Worker: orchestrates knowledge graph entity extraction and aggregation.
 * Entity extraction requires the on-device Gemma model (MediaPipe) which is
 * bound to the main thread, so this worker uses a relay protocol:
 *
 *   Worker → Main:  { type: 'request-entities', requestId, chunks }
 *   Main → Worker:  { type: 'entities-result',  requestId, graph }
 *   Main → Worker:  { type: 'entities-error',   requestId, error }  ← triggers fallback
 *
 * FLOW
 * ────
 *  Main → Worker:   { type: 'process', docId, fileName, chunkTexts }
 *  Worker:          batches chunks (GEMMA_BATCH_SIZE each)
 *  Worker → Main:   request-entities for each batch
 *  Main  → Worker:  entities-result (Gemma JSON) or entities-error (fallback)
 *  Worker:          aggregates entities, deduplicates, builds CO_OCCURS relations
 *  Worker → Main:   { type: 'result', docId, entities, relations }
 *  Worker → Main:   { type: 'complete', docId, entityCount }
 *
 * If the entire pipeline fails: { type: 'error', docId, message }
 */

import {
    extractEntitiesHeuristic,
    parseEntityExtractionResponse,
    normalizeEntityName,
    type ExtractedEntity,
    type ExtractedGraph,
    type ExtractedRelation,
} from "@/lib/entity-extractor";

// ─── Message types ────────────────────────────────────────────────────────────

export interface KGWorkerProcessRequest {
    type: "process";
    docId: string;
    fileName: string;
    chunkTexts: string[];
}

export interface KGWorkerEntitiesResult {
    type: "entities-result";
    requestId: string;
    graph: ExtractedGraph;
}

export interface KGWorkerEntitiesError {
    type: "entities-error";
    requestId: string;
    error: string;
}

export type KGWorkerRequest =
    | KGWorkerProcessRequest
    | KGWorkerEntitiesResult
    | KGWorkerEntitiesError;

export interface KGWorkerRequestEntities {
    type: "request-entities";
    requestId: string;
    chunks: string[];
    docId: string;
}

export interface KGWorkerProgress {
    type: "progress";
    docId: string;
    phase: "graph-extracting" | "graph-building";
    pct: number;
}

export interface KGWorkerResult {
    type: "result";
    docId: string;
    entities: ExtractedEntity[];
    relations: ExtractedRelation[];
}

export interface KGWorkerComplete {
    type: "complete";
    docId: string;
    entityCount: number;
}

export interface KGWorkerError {
    type: "error";
    docId: string;
    message: string;
}

export type KGWorkerResponse =
    | KGWorkerRequestEntities
    | KGWorkerProgress
    | KGWorkerResult
    | KGWorkerComplete
    | KGWorkerError;

// ─── Config ───────────────────────────────────────────────────────────────────

const GEMMA_BATCH_SIZE = 4; // chunks per Gemma call
// Main thread soft timeout is 90s, hard timeout 200s, plus up to 4 retries × 3s.
// The worker must wait at least as long as the main thread might before responding.
const ENTITY_REQUEST_TIMEOUT_MS = 210_000; // 3.5 min

// ─── Pending entity request registry ─────────────────────────────────────────

interface PendingRequest {
    resolve: (graph: ExtractedGraph) => void;
    timeoutId: ReturnType<typeof setTimeout>;
    chunks: string[]; // kept for heuristic fallback
}

const pendingRequests = new Map<string, PendingRequest>();
let _requestCounter = 0;

function generateRequestId(): string {
    return `kg_req_${++_requestCounter}_${Date.now()}`;
}

// ─── Request entities from main thread (Gemma relay) ─────────────────────────

async function requestEntitiesFromMain(
    docId: string,
    chunks: string[]
): Promise<ExtractedGraph> {
    const requestId = generateRequestId();

    return new Promise<ExtractedGraph>((resolve) => {
        const timeoutId = setTimeout(() => {
            pendingRequests.delete(requestId);
            console.warn(`[kg-worker] Entity extraction timed out for request ${requestId} — using heuristic fallback`);
            resolve(extractEntitiesHeuristic(chunks));
        }, ENTITY_REQUEST_TIMEOUT_MS);

        pendingRequests.set(requestId, { resolve, timeoutId, chunks });

        self.postMessage({
            type: "request-entities",
            requestId,
            chunks,
            docId,
        } satisfies KGWorkerRequestEntities);
    });
}

// ─── Entity aggregation helpers ───────────────────────────────────────────────

function deduplicateEntities(entities: ExtractedEntity[]): ExtractedEntity[] {
    const seen = new Map<string, ExtractedEntity>();
    for (const e of entities) {
        const existing = seen.get(e.normalizedName);
        // Prefer more specific types (not "OTHER") and longer names
        if (!existing || (existing.type === "OTHER" && e.type !== "OTHER")) {
            seen.set(e.normalizedName, e);
        }
    }
    return Array.from(seen.values());
}

function deduplicateRelations(relations: ExtractedRelation[]): ExtractedRelation[] {
    const seen = new Set<string>();
    return relations.filter((r) => {
        const key = [r.from, r.to, r.type].join("|||");
        if (seen.has(key)) return false;
        seen.add(key);
        return true;
    });
}

// ─── Message handler ──────────────────────────────────────────────────────────

self.onmessage = async (event: MessageEvent<KGWorkerRequest>) => {
    const msg = event.data;

    // ── Handle entity resolution responses from main thread ───────────────────
    if (msg.type === "entities-result" || msg.type === "entities-error") {
        const pending = pendingRequests.get(msg.requestId);
        if (!pending) return;

        clearTimeout(pending.timeoutId);
        pendingRequests.delete(msg.requestId);

        if (msg.type === "entities-result") {
            pending.resolve(msg.graph);
        } else {
            // Main thread reported Gemma unavailable — use heuristic fallback
            console.warn(`[kg-worker] Gemma unavailable for request ${msg.requestId}: ${msg.error}. Using heuristic fallback.`);
            pending.resolve(extractEntitiesHeuristic(pending.chunks));
        }
        return;
    }

    // ── Handle process request ────────────────────────────────────────────────
    if (msg.type !== "process") return;

    const { docId, chunkTexts } = msg;

    try {
        const allEntities: ExtractedEntity[] = [];
        const allRelations: ExtractedRelation[] = [];
        const totalBatches = Math.ceil(chunkTexts.length / GEMMA_BATCH_SIZE);

        for (let batchIdx = 0; batchIdx < totalBatches; batchIdx++) {
            const batchStart = batchIdx * GEMMA_BATCH_SIZE;
            const batchChunks = chunkTexts.slice(batchStart, batchStart + GEMMA_BATCH_SIZE);

            // Progress: graph-extracting phase spans 0–70%
            const extractPct = Math.round((batchIdx / totalBatches) * 70);
            self.postMessage({
                type: "progress",
                docId,
                phase: "graph-extracting",
                pct: extractPct,
            } satisfies KGWorkerProgress);

            // Request entity extraction from main thread (Gemma) with heuristic fallback
            const batchGraph = await requestEntitiesFromMain(docId, batchChunks);

            allEntities.push(...batchGraph.entities);
            allRelations.push(...batchGraph.relations);
        }

        // graph-building phase: 70–100%
        self.postMessage({
            type: "progress",
            docId,
            phase: "graph-building",
            pct: 70,
        } satisfies KGWorkerProgress);

        // Add co-occurrence relations from heuristic analysis across all chunks
        // This supplements whatever Gemma found with structural co-occurrence data
        const heuristicGraph = extractEntitiesHeuristic(chunkTexts);
        allEntities.push(...heuristicGraph.entities);

        // Merge and deduplicate
        const finalEntities = deduplicateEntities(allEntities);
        const entityNorms = new Set(finalEntities.map((e) => e.normalizedName));

        // Only keep relations where both endpoints exist after dedup
        const validRelations = deduplicateRelations([
            ...allRelations,
            ...heuristicGraph.relations,
        ]).filter(
            (r) => entityNorms.has(r.from) && entityNorms.has(r.to) && r.from !== r.to
        );

        // Also validate Gemma-produced entity normalizedNames are correctly set
        for (const e of finalEntities) {
            if (!e.normalizedName) {
                e.normalizedName = normalizeEntityName(e.name);
            }
        }

        self.postMessage({
            type: "progress",
            docId,
            phase: "graph-building",
            pct: 90,
        } satisfies KGWorkerProgress);

        self.postMessage({
            type: "result",
            docId,
            entities: finalEntities,
            relations: validRelations,
        } satisfies KGWorkerResult);

        self.postMessage({
            type: "complete",
            docId,
            entityCount: finalEntities.length,
        } satisfies KGWorkerComplete);

    } catch (err) {
        const message = err instanceof Error ? err.message : "Unknown KG pipeline error.";
        console.error(`[kg-worker] Pipeline error for doc ${docId}:`, err);
        self.postMessage({
            type: "error",
            docId,
            message,
        } satisfies KGWorkerError);
    }
};

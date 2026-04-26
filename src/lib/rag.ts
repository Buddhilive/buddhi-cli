/**
 * rag.ts
 *
 * Naive RAG utilities — retrieval, context formatting, and source projection.
 *
 * This module is a pure utility layer with no React dependencies. All RAG
 * logic lives here so that chat-interface.tsx stays thin and the retrieval
 * pipeline can be tested or reused independently.
 *
 * PIPELINE
 * --------
 *  1. retrieveRagContext()   — queries PGlite, filters by score, deduplicates
 *  2. buildRagContextBlock() — formats segments into the plain-text block that
 *                              gets appended to the user message before the LLM
 *  3. toSourceItems()        — projects segments to the minimal shape needed
 *                              by the Sources UI components
 *
 * GRACEFUL DEGRADATION
 * --------------------
 * retrieveRagContext() never throws. Any failure (embedding model not loaded,
 * PGlite unavailable, network error, etc.) is caught, logged, and returns an
 * empty array so the chat continues without augmentation.
 */

import { hasDocuments, retrieveSegments } from "@/lib/llamaindex-provider";
import { retrieveGraphContext } from "@/lib/graph-rag";

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

/** A single retrieved chunk with its provenance and similarity score. */
export interface RagSegment {
    text: string;
    fileName: string;
    documentId: string;
    score: number;
}

/**
 * Minimal shape consumed by the Sources / Source ai-element components.
 * Deduplication is done upstream in retrieveRagContext, so each entry here
 * represents a distinct source document.
 */
export interface RagSourceItem {
    fileName: string;
    documentId: string;
}

// ---------------------------------------------------------------------------
// Constants
// ---------------------------------------------------------------------------

/**
 * Minimum cosine-similarity score (0–1) for a retrieved chunk to be included.
 *
 * 0.35 is conservative — below this threshold the chunk is almost certainly
 * not topically related to the query. The LLM instruction in the context block
 * hedges against borderline chunks being misused.
 */
const DEFAULT_MIN_SCORE = 0.35;

/** Default number of candidate chunks to request from the vector store. */
const DEFAULT_TOP_K = 5;

// ---------------------------------------------------------------------------
// retrieveRagContext
// ---------------------------------------------------------------------------

/**
 * Retrieves, filters, and deduplicates relevant document segments for a query.
 * Always searches the global document store — documents are accessible from
 * any chat regardless of where the conversation started.
 *
 * Returns an empty array (never throws) when:
 *  - query is blank
 *  - no documents have been indexed
 *  - the embedding model is not yet loaded
 *  - any other retrieval error occurs
 *
 * @param query    The user's raw text query.
 * @param topK     Number of raw candidates to fetch before filtering. Default 5.
 * @param minScore Minimum similarity score (0–1) to accept. Default 0.35.
 */
export async function retrieveRagContext(
    query: string,
    topK: number = DEFAULT_TOP_K,
    minScore: number = DEFAULT_MIN_SCORE
): Promise<RagSegment[]> {
    // Guard: nothing to retrieve for a blank query.
    if (!query.trim()) return [];

    console.log(`[rag] retrieveRagContext — query: "${query.slice(0, 80)}${query.length > 80 ? "…" : ""}"`);

    try {
        // Early exit when no documents are indexed — avoids the expensive
        // embedding model cold-start path on every chat submission.
        const hasAny = await hasDocuments();
        console.log(`[rag] hasDocuments: ${hasAny}`);
        if (!hasAny) return [];

        // Query the entire document store (no chatId filter).
        const rawResults = await retrieveSegments(query, topK);
        console.log(`[rag] raw results (${rawResults.length}):`, rawResults.map((r) => ({
            documentId: r.documentId,
            fileName: r.fileName,
            score: r.node.score,
            textSnippet: r.text?.slice(0, 60),
        })));

        // ── Filter by minimum similarity score ────────────────────────────
        const filtered = rawResults.filter(
            (r) => (r.node.score ?? 0) >= minScore
        );
        console.log(`[rag] after score filter (>= ${minScore}): ${filtered.length} results`);

        // ── Deduplicate by documentId (keep highest-score chunk per doc) ──
        const bestByDoc = new Map<string, typeof filtered[number]>();
        for (const result of filtered) {
            const existing = bestByDoc.get(result.documentId);
            if (!existing || (result.node.score ?? 0) > (existing.node.score ?? 0)) {
                bestByDoc.set(result.documentId, result);
            }
        }

        // ── Project to RagSegment[] ───────────────────────────────────────
        const segments = Array.from(bestByDoc.values()).map((r) => ({
            text: r.text,
            fileName: r.fileName,
            documentId: r.documentId,
            score: r.node.score ?? 0,
        }));
        console.log(`[rag] final segments (${segments.length}):`, segments.map((s) => ({
            fileName: s.fileName,
            score: s.score,
        })));
        return segments;
    } catch (err) {
        console.warn(
            "[rag] Retrieval failed — continuing without RAG context.",
            err instanceof Error
                ? `${err.name}: ${err.message}`
                : String(err)
        );
        return [];
    }
}

// ---------------------------------------------------------------------------
// buildRagContextBlock
// ---------------------------------------------------------------------------

/**
 * Formats retrieved segments into a plain-text block that is appended to the
 * user's message before it reaches the LLM.
 *
 * Returns null when segments is empty so callers can skip injection entirely.
 *
 * The block follows this structure:
 *
 *   \n\n---
 *   Relevant context from your knowledge base:
 *
 *   [Source 1: "filename.pdf"]
 *   chunk text …
 *
 *   [Source 2: "other.txt"]
 *   chunk text …
 *
 *   Use the above context …
 *
 * The instruction at the end hedges against low-relevance chunks being
 * over-indexed by the model while keeping it short (context window is limited).
 */
export function buildRagContextBlock(segments: RagSegment[]): string | null {
    if (segments.length === 0) return null;

    const sourceBlocks = segments
        .map(
            (seg, i) =>
                `[Source ${i + 1}: "${seg.fileName}"]\n${seg.text.trim()}`
        )
        .join("\n\n");

    return (
        "\n\n---\n" +
        "Relevant context from your knowledge base:\n\n" +
        sourceBlocks +
        "\n\n" +
        "Use the above context to help answer the question. " +
        "If the context is not relevant, ignore it and answer from your general knowledge."
    );
}

// ---------------------------------------------------------------------------
// toSourceItems
// ---------------------------------------------------------------------------

/**
 * Projects RagSegment[] to the minimal shape consumed by the Sources /
 * Source ai-element components. Deduplication is already done upstream.
 */
export function toSourceItems(segments: RagSegment[]): RagSourceItem[] {
    return segments.map((s) => ({
        fileName: s.fileName,
        documentId: s.documentId,
    }));
}

// ---------------------------------------------------------------------------
// retrieveHybridContext
// ---------------------------------------------------------------------------

/**
 * HybridRAG: combines vector similarity search (Naive RAG) with graph
 * traversal (GraphRAG) for improved recall and precision.
 *
 * ALGORITHM
 * ---------
 *  1. Run vector retrieval and graph retrieval in parallel.
 *  2. Score normalization:
 *       vector scores are already 0–1 (cosine similarity)
 *       graph scores (0.6–1.0) are normalized to 0–1
 *  3. Per documentId, compute combinedScore:
 *       both sources:  0.7 * vectorScore + 0.3 * graphScore
 *       vector only:   0.7 * vectorScore
 *       graph only:    0.3 * graphScore
 *  4. Filter: combinedScore >= 0.25 (lower than vector-only 0.35 to allow
 *     graph-only results to surface entities vector search missed)
 *  5. Deduplicate by documentId (best combined score per document)
 *  6. Sort descending, return top topK.
 *
 * Falls back to vector-only results if graph retrieval fails.
 * Never throws — returns [] on all retrieval failures.
 *
 * @param query    The user's raw text query.
 * @param topK     Maximum segments to return. Default 5.
 * @param minScore Minimum combined score to accept. Default 0.25.
 */
export async function retrieveHybridContext(
    query: string,
    topK: number = DEFAULT_TOP_K,
    minScore: number = 0.25
): Promise<RagSegment[]> {
    if (!query.trim()) return [];

    console.log(`[rag] retrieveHybridContext — query: "${query.slice(0, 80)}${query.length > 80 ? "…" : ""}"`);

    try {
        // Run both retrievers in parallel — graph failure is non-fatal
        const [vectorSegments, graphSegments] = await Promise.all([
            retrieveRagContext(query, topK + 3).catch((err) => {
                console.warn("[rag] Vector retrieval failed in hybrid mode:", err);
                return [] as RagSegment[];
            }),
            retrieveGraphContext(query, topK).catch((err) => {
                console.warn("[rag] Graph retrieval failed in hybrid mode:", err);
                return [] as RagSegment[];
            }),
        ]);

        console.log(`[rag] hybrid — vector: ${vectorSegments.length}, graph: ${graphSegments.length}`);

        // Build score maps keyed by documentId
        const vectorByDoc = new Map<string, RagSegment>();
        for (const seg of vectorSegments) {
            const existing = vectorByDoc.get(seg.documentId);
            if (!existing || seg.score > existing.score) {
                vectorByDoc.set(seg.documentId, seg);
            }
        }

        const graphByDoc = new Map<string, RagSegment>();
        for (const seg of graphSegments) {
            const existing = graphByDoc.get(seg.documentId);
            if (!existing || seg.score > existing.score) {
                graphByDoc.set(seg.documentId, seg);
            }
        }

        // Collect all document IDs seen in either retriever
        const allDocIds = new Set([...vectorByDoc.keys(), ...graphByDoc.keys()]);

        const combined: RagSegment[] = [];

        for (const docId of allDocIds) {
            const vSeg = vectorByDoc.get(docId);
            const gSeg = graphByDoc.get(docId);

            let combinedScore: number;
            let bestSeg: RagSegment;

            if (vSeg && gSeg) {
                combinedScore = 0.7 * vSeg.score + 0.3 * gSeg.score;
                bestSeg = vSeg; // prefer vector segment text (usually more complete)
            } else if (vSeg) {
                combinedScore = 0.7 * vSeg.score;
                bestSeg = vSeg;
            } else {
                // gSeg only — normalize graph score (0.6–1.0) to 0–1 range
                const gScore = gSeg!.score;
                const normalizedGraphScore = (gScore - 0.5) / 0.5; // maps [0.5,1.0]→[0,1]
                combinedScore = 0.3 * Math.max(0, normalizedGraphScore);
                bestSeg = gSeg!;
            }

            if (combinedScore >= minScore) {
                combined.push({ ...bestSeg, score: combinedScore });
            }
        }

        const results = combined
            .sort((a, b) => b.score - a.score)
            .slice(0, topK);

        console.log(
            `[rag] hybrid final: ${results.length} segments`,
            results.map((s) => ({ fileName: s.fileName, score: s.score.toFixed(3) }))
        );

        return results;
    } catch (err) {
        console.warn(
            "[rag] HybridRAG failed — continuing without RAG context.",
            err instanceof Error ? `${err.name}: ${err.message}` : String(err)
        );
        return [];
    }
}

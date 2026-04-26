/**
 * graph-rag.ts
 *
 * Graph RAG retrieval pipeline.
 *
 * At query time:
 *   1. Extract candidate entity names from the query using the fast heuristic NER
 *      (no LLM call at chat time — keeps latency low)
 *   2. Look up matching Entity vertices in the AGE graph
 *   3. Traverse 1-hop (direct HAS_ENTITY) and 2-hop (CO_OCCURS) relationships
 *   4. Return results as RagSegment[] — compatible with buildRagContextBlock()
 *
 * Never throws — returns [] on any failure so chat continues uninterrupted.
 */

import { kgStore } from "@/lib/kg-store";
import { extractEntitiesHeuristic, normalizeEntityName } from "@/lib/entity-extractor";
import type { RagSegment } from "@/lib/rag";

const DEFAULT_GRAPH_TOP_K = 5;

/**
 * Retrieve relevant chunks from the knowledge graph for a query.
 *
 * @param query  The user's raw text query.
 * @param topK   Maximum number of segments to return. Default 5.
 * @returns      RagSegment[] sorted by score descending. Empty on any failure.
 */
export async function retrieveGraphContext(
    query: string,
    topK: number = DEFAULT_GRAPH_TOP_K
): Promise<RagSegment[]> {
    if (!query.trim()) return [];

    try {
        const hasGraph = await kgStore.hasKnowledgeGraph();
        if (!hasGraph) return [];

        // Extract entity candidates from query — heuristic is fast enough at query time
        const queryGraph = extractEntitiesHeuristic([query]);

        // Build a deduplicated list of normalized names from:
        //   a) entities the heuristic extracted
        //   b) significant individual words from the query (nouns / capitalized)
        const normalizedNames = new Set<string>();

        for (const e of queryGraph.entities) {
            normalizedNames.add(e.normalizedName);
        }

        // Also add individual query keywords as fallback entity terms
        const keywords = query
            .split(/\s+/)
            .map((w) => normalizeEntityName(w.replace(/[^\w\s-]/g, "")))
            .filter((w) => w.length >= 3);
        for (const kw of keywords) {
            normalizedNames.add(kw);
        }

        if (normalizedNames.size === 0) return [];

        console.log(
            `[graph-rag] Querying graph with ${normalizedNames.size} entity candidates:`,
            Array.from(normalizedNames).slice(0, 10)
        );

        const graphResults = await kgStore.queryByEntities(
            Array.from(normalizedNames),
            topK
        );

        // Map to RagSegment[] — the existing buildRagContextBlock format
        const segments: RagSegment[] = graphResults
            .filter((r) => r.text && r.text.trim().length > 0)
            .map((r) => ({
                text: r.text,
                fileName: r.fileName || "unknown",
                documentId: r.documentId || "unknown",
                score: r.score,
            }));

        console.log(
            `[graph-rag] Found ${segments.length} graph segments for query "${query.slice(0, 60)}"`
        );

        return segments;

    } catch (err) {
        console.warn(
            "[graph-rag] Graph retrieval failed — continuing without graph context.",
            err instanceof Error ? `${err.name}: ${err.message}` : String(err)
        );
        return [];
    }
}

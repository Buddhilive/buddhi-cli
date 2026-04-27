/**
 * kg-store.ts — Apache AGE Knowledge Graph Store
 *
 * Manages the graph layer of the Buddhi AI knowledge base using Apache AGE
 * on top of the same PGlite instance as the vector store.
 *
 * GRAPH SCHEMA
 * ────────────
 *  Vertices:  Entity  {id, name, normalizedName, type, documentId}
 *             Document {id, documentId, fileName}
 *             Chunk   {id, chunkId, text, documentId, position}
 *
 *  Edges:     HAS_ENTITY  Chunk → Entity   (chunk mentions this entity)
 *             PART_OF     Chunk → Document (chunk belongs to document)
 *             CO_OCCURS   Entity ↔ Entity  (appear together in same chunk)
 *
 * All mutation methods are idempotent (MERGE-based) so re-processing a
 * document after an interruption does not create duplicates.
 */

import { initializeDB } from "@/lib/llamaindex-provider";
import type { ExtractedEntity, ExtractedGraph, ExtractedRelation } from "@/lib/entity-extractor";

// ─── Types ────────────────────────────────────────────────────────────────────

export interface GraphChunkResult {
    text: string;
    chunkId: string;
    documentId: string;
    fileName: string;
    score: number;
}

export interface KGEntity {
    name: string;
    normalizedName: string;
    type: string;
}

export interface KGRelation {
    from: string;
    to: string;
    relType: string;
}

export interface KGDocument {
    fileName: string;
    documentId: string;
}

// ─── Co-occurrence fallback ───────────────────────────────────────────────────

// Computes CO_OCCURS relations directly from chunk texts when the extraction
// pipeline sends 0 relations. O(chunks × entities²) but capped by entity count.
function computeCoOccurrenceFromChunks(
    chunkTexts: string[],
    entities: ExtractedEntity[]
): ExtractedRelation[] {
    const relations: ExtractedRelation[] = [];
    const seenPairs = new Set<string>();
    for (const chunkText of chunkTexts) {
        const lower = chunkText.toLowerCase();
        const present = entities.filter((e) => e.normalizedName && lower.includes(e.normalizedName));
        for (let i = 0; i < present.length; i++) {
            for (let j = i + 1; j < present.length; j++) {
                const a = present[i].normalizedName;
                const b = present[j].normalizedName;
                if (a === b) continue;
                const key = [a, b].sort().join("|||");
                if (seenPairs.has(key)) continue;
                seenPairs.add(key);
                relations.push({ from: a, to: b, type: "CO_OCCURS" });
            }
        }
    }
    return relations;
}

// ─── Cypher string helpers ─────────────────────────────────────────────────────

function escapeCypher(s: string): string {
    return String(s)
        .replace(/\\/g, "\\\\")
        .replace(/'/g, "\\'")
        .replace(/"/g, '\\"')
        .replace(/\n/g, "\\n")
        .replace(/\r/g, "\\r")
        .replace(/\t/g, "\\t");
}

// ─── agtype value parsing ─────────────────────────────────────────────────────

// AGE returns column values as agtype strings (e.g. '"some text"', '42', 'true').
// This helper extracts the plain JS value.
// eslint-disable-next-line @typescript-eslint/no-explicit-any
function fromAgtype(v: unknown): any {
    if (v === null || v === undefined) return null;
    if (typeof v === "string") {
        // Remove optional agtype type annotation suffix (e.g. "::vertex")
        const cleaned = v.replace(/::\w+$/, "").trim();
        try {
            return JSON.parse(cleaned);
        } catch {
            return cleaned;
        }
    }
    return v;
}

// ─── Singleton ────────────────────────────────────────────────────────────────

const GRAPH_NAME = "buddhi_kg";

let _schemaInitialized = false;
let _schemaInitPromise: Promise<void> | null = null;

// ─── Schema initialization ────────────────────────────────────────────────────

async function initializeKGSchema(): Promise<void> {
    if (_schemaInitialized) return;
    if (_schemaInitPromise) return _schemaInitPromise;

    _schemaInitPromise = (async () => {
        const { db } = await initializeDB();

        // Create the graph (idempotent — catch "already exists" gracefully)
        try {
            await db.exec(`SELECT create_graph('${GRAPH_NAME}')`);
        } catch (err) {
            const msg = err instanceof Error ? err.message : String(err);
            if (!msg.includes("already exists") && !msg.includes("duplicate")) {
                throw new Error(`[kg-store] Failed to create graph "${GRAPH_NAME}": ${msg}`);
            }
        }

        // Create vertex labels
        for (const label of ["Entity", "Document", "Chunk"]) {
            try {
                await db.exec(`SELECT create_vlabel('${GRAPH_NAME}', '${label}')`);
            } catch (err) {
                const msg = err instanceof Error ? err.message : String(err);
                if (!msg.includes("already exists") && !msg.includes("duplicate")) {
                    console.warn(`[kg-store] create_vlabel "${label}" warning:`, msg);
                }
            }
        }

        // Create edge labels
        for (const label of ["HAS_ENTITY", "PART_OF", "CO_OCCURS"]) {
            try {
                await db.exec(`SELECT create_elabel('${GRAPH_NAME}', '${label}')`);
            } catch (err) {
                const msg = err instanceof Error ? err.message : String(err);
                if (!msg.includes("already exists") && !msg.includes("duplicate")) {
                    console.warn(`[kg-store] create_elabel "${label}" warning:`, msg);
                }
            }
        }

        _schemaInitialized = true;
        console.info("[kg-store] Knowledge graph schema ready.");
    })();

    return _schemaInitPromise;
}

// ─── Cypher execution helper ──────────────────────────────────────────────────

// eslint-disable-next-line @typescript-eslint/no-explicit-any
async function cypher(query: string): Promise<any[]> {
    const { db } = await initializeDB();
    try {
        const result = await db.query(query);
        return result.rows ?? [];
    } catch (err) {
        const msg = err instanceof Error ? err.message : String(err);
        throw new Error(`[kg-store] Cypher error: ${msg}\nQuery: ${query.slice(0, 200)}`);
    }
}

// ─── Public API ───────────────────────────────────────────────────────────────

export const kgStore = {

    /** Initialize graph schema — call before any write or read operation. */
    async init(): Promise<void> {
        await initializeKGSchema();
    },

    /**
     * Write an entire document's extracted graph data into AGE.
     * Uses MERGE to be idempotent — safe to re-run on reconciliation.
     */
    async addDocumentGraph(
        docId: string,
        fileName: string,
        chunkTexts: string[],
        graph: ExtractedGraph
    ): Promise<void> {
        await initializeKGSchema();

        const safeDocId = escapeCypher(docId);
        const safeFileName = escapeCypher(fileName);

        // Upsert Document vertex
        // AGE does not support ON CREATE SET / ON MATCH SET — use plain SET.
        await cypher(`
            SELECT * FROM cypher('${GRAPH_NAME}', $$
                MERGE (d:Document {documentId: '${safeDocId}'})
                SET d.fileName = '${safeFileName}'
                RETURN d
            $$) AS (d agtype)
        `);

        // Upsert Chunk vertices, then PART_OF edges (two separate queries — AGE
        // doesn't support WITH…MATCH…MERGE chaining reliably).
        for (let i = 0; i < chunkTexts.length; i++) {
            const chunkId = `${docId}_chunk_${i}`;
            const safeChunkId = escapeCypher(chunkId);
            const safeText = escapeCypher(chunkTexts[i].slice(0, 500));

            await cypher(`
                SELECT * FROM cypher('${GRAPH_NAME}', $$
                    MERGE (c:Chunk {chunkId: '${safeChunkId}'})
                    SET c.text = '${safeText}', c.documentId = '${safeDocId}', c.position = ${i}
                    RETURN c
                $$) AS (c agtype)
            `);

            await cypher(`
                SELECT * FROM cypher('${GRAPH_NAME}', $$
                    MATCH (c:Chunk {chunkId: '${safeChunkId}'})
                    MATCH (d:Document {documentId: '${safeDocId}'})
                    MERGE (c)-[:PART_OF]->(d)
                    RETURN c
                $$) AS (c agtype)
            `);
        }

        // Upsert Entity vertices
        for (const entity of graph.entities) {
            const safeName = escapeCypher(entity.name);
            const safeNorm = escapeCypher(entity.normalizedName);
            const safeType = escapeCypher(entity.type);

            await cypher(`
                SELECT * FROM cypher('${GRAPH_NAME}', $$
                    MERGE (e:Entity {normalizedName: '${safeNorm}'})
                    SET e.name = '${safeName}', e.type = '${safeType}'
                    RETURN e
                $$) AS (e agtype)
            `);
        }

        // Upsert CO_OCCURS edges between entities.
        // Always compute co-occurrence from chunk texts and merge with pipeline relations.
        // Pipeline relations may have normalizedName mismatches (Gemma/heuristic dedup drift)
        // causing MATCH to find no vertices and silently skip the MERGE. Co-occurrence uses
        // the exact entity list being stored so MATCH always succeeds for those relations.
        const coOccurrence = computeCoOccurrenceFromChunks(chunkTexts, graph.entities);
        const seenRelPairs = new Set<string>();
        const relationsToStore: ExtractedRelation[] = [];
        for (const rel of [...graph.relations, ...coOccurrence]) {
            if (!rel.from || !rel.to || rel.from === rel.to) continue;
            const key = [rel.from, rel.to].sort().join("|||");
            if (seenRelPairs.has(key)) continue;
            seenRelPairs.add(key);
            relationsToStore.push(rel);
        }

        for (const rel of relationsToStore) {
            if (rel.from === rel.to) continue;
            const safeFrom = escapeCypher(rel.from);
            const safeTo = escapeCypher(rel.to);
            const safeRelType = escapeCypher(rel.type);

            await cypher(`
                SELECT * FROM cypher('${GRAPH_NAME}', $$
                    MATCH (a:Entity {normalizedName: '${safeFrom}'})
                    MATCH (b:Entity {normalizedName: '${safeTo}'})
                    MERGE (a)-[r:CO_OCCURS {relType: '${safeRelType}'}]->(b)
                    RETURN r
                $$) AS (r agtype)
            `);
        }

        // HAS_ENTITY edges: link entities to chunks that contain their name
        for (let i = 0; i < chunkTexts.length; i++) {
            const lowerChunk = chunkTexts[i].toLowerCase();
            const chunkId = `${docId}_chunk_${i}`;
            const safeChunkId = escapeCypher(chunkId);

            for (const entity of graph.entities) {
                if (!lowerChunk.includes(entity.normalizedName)) continue;
                const safeNorm = escapeCypher(entity.normalizedName);

                await cypher(`
                    SELECT * FROM cypher('${GRAPH_NAME}', $$
                        MATCH (c:Chunk {chunkId: '${safeChunkId}'})
                        MATCH (e:Entity {normalizedName: '${safeNorm}'})
                        MERGE (c)-[:HAS_ENTITY]->(e)
                        RETURN c
                    $$) AS (c agtype)
                `);
            }
        }

        console.info(`[kg-store] Graph written for document "${fileName}" (${graph.entities.length} entities, ${relationsToStore.length} relations)`);
    },

    /**
     * Remove all graph nodes and edges for a document.
     * Called during document deletion.
     */
    async deleteDocumentGraph(docId: string): Promise<void> {
        await initializeKGSchema();
        const safeDocId = escapeCypher(docId);

        try {
            // Step 1: Collect entity normalizedNames referenced by this document's
            // chunks BEFORE deleting, so we can check for orphans afterwards.
            const entityRows = await cypher(`
                SELECT * FROM cypher('${GRAPH_NAME}', $$
                    MATCH (c:Chunk {documentId: '${safeDocId}'})-[:HAS_ENTITY]->(e:Entity)
                    RETURN DISTINCT e.normalizedName
                $$) AS (normalizedname agtype)
            `);
            const entityNorms = entityRows
                .map((r) => fromAgtype(r.normalizedname) as string | null)
                .filter((n): n is string => !!n && n.trim().length > 0);

            // Step 2: Delete Chunk nodes (DETACH DELETE removes HAS_ENTITY + PART_OF edges)
            await cypher(`
                SELECT * FROM cypher('${GRAPH_NAME}', $$
                    MATCH (c:Chunk {documentId: '${safeDocId}'})
                    DETACH DELETE c
                $$) AS (result agtype)
            `);

            // Step 3: Delete Document vertex
            await cypher(`
                SELECT * FROM cypher('${GRAPH_NAME}', $$
                    MATCH (d:Document {documentId: '${safeDocId}'})
                    DETACH DELETE d
                $$) AS (result agtype)
            `);

            // Step 4: Delete Entity vertices that are now orphaned (no remaining
            // HAS_ENTITY edges connecting them to any chunk in any document).
            // Use edge-first deletion — DETACH DELETE on Entity fails because
            // CO_OCCURS edges connect Entity↔Entity (same AGE limitation as clearAll).
            let orphansDeleted = 0;
            for (const norm of entityNorms) {
                const safeNorm = escapeCypher(norm);
                try {
                    // Delete CO_OCCURS edges for this entity if it's orphaned
                    await cypher(`
                        SELECT * FROM cypher('${GRAPH_NAME}', $$
                            MATCH (e:Entity {normalizedName: '${safeNorm}'})-[r:CO_OCCURS]-()
                            WHERE NOT (e)-[:HAS_ENTITY]-()
                            DELETE r
                        $$) AS (result agtype)
                    `);
                    // Plain DELETE the vertex (no edges remain)
                    await cypher(`
                        SELECT * FROM cypher('${GRAPH_NAME}', $$
                            MATCH (e:Entity {normalizedName: '${safeNorm}'})
                            WHERE NOT (e)-[:HAS_ENTITY]-()
                            DELETE e
                        $$) AS (result agtype)
                    `);
                    orphansDeleted++;
                } catch {
                    // Silently skip — entity may still be referenced by another document
                }
            }

            console.info(`[kg-store] Deleted graph for document ${docId} (${orphansDeleted}/${entityNorms.length} orphaned entities cleaned up)`);
        } catch (err) {
            console.error(`[kg-store] Error deleting graph for document ${docId}:`, err);
        }
    },

    /**
     * Find chunks related to the given normalized entity names via 1-hop and 2-hop graph traversal.
     * Returns results sorted by score descending (1-hop = 1.0, 2-hop = 0.6).
     */
    async queryByEntities(
        normalizedNames: string[],
        topK = 5
    ): Promise<GraphChunkResult[]> {
        if (!_schemaInitialized || normalizedNames.length === 0) return [];

        const nameList = normalizedNames
            .slice(0, 20) // cap to avoid huge queries
            .map((n) => `'${escapeCypher(n)}'`)
            .join(", ");

        const results: GraphChunkResult[] = [];

        try {
            // 1-hop: chunks directly mentioning matching entities
            const hop1Rows = await cypher(`
                SELECT * FROM cypher('${GRAPH_NAME}', $$
                    MATCH (e:Entity)-[:HAS_ENTITY]-(c:Chunk)-[:PART_OF]-(d:Document)
                    WHERE e.normalizedName IN [${nameList}]
                    RETURN c.text, c.chunkId, c.documentId, d.fileName
                $$) AS (text agtype, chunkId agtype, documentId agtype, fileName agtype)
                LIMIT ${topK * 2}
            `);

            for (const row of hop1Rows) {
                results.push({
                    text: fromAgtype(row.text) ?? "",
                    chunkId: fromAgtype(row.chunkid) ?? fromAgtype(row.chunkId) ?? "",
                    documentId: fromAgtype(row.documentid) ?? fromAgtype(row.documentId) ?? "",
                    fileName: fromAgtype(row.filename) ?? fromAgtype(row.fileName) ?? "",
                    score: 1.0,
                });
            }

            // 2-hop: chunks reachable via co-occurring entities
            const hop2Rows = await cypher(`
                SELECT * FROM cypher('${GRAPH_NAME}', $$
                    MATCH (e:Entity)-[:CO_OCCURS]-(e2:Entity)-[:HAS_ENTITY]-(c:Chunk)-[:PART_OF]-(d:Document)
                    WHERE e.normalizedName IN [${nameList}]
                    RETURN c.text, c.chunkId, c.documentId, d.fileName
                $$) AS (text agtype, chunkId agtype, documentId agtype, fileName agtype)
                LIMIT ${topK * 2}
            `);

            for (const row of hop2Rows) {
                // Don't double-add results already found via 1-hop
                const chunkId = fromAgtype(row.chunkid) ?? fromAgtype(row.chunkId) ?? "";
                if (!results.some((r) => r.chunkId === chunkId)) {
                    results.push({
                        text: fromAgtype(row.text) ?? "",
                        chunkId,
                        documentId: fromAgtype(row.documentid) ?? fromAgtype(row.documentId) ?? "",
                        fileName: fromAgtype(row.filename) ?? fromAgtype(row.fileName) ?? "",
                        score: 0.6,
                    });
                }
            }
        } catch (err) {
            console.warn("[kg-store] Graph query error:", err);
            return [];
        }

        return results
            .sort((a, b) => b.score - a.score)
            .slice(0, topK);
    },

    /**
     * Delete every vertex and edge in the graph regardless of document.
     * Use when re-importing all documents or clearing stale data.
     */
    async clearAll(): Promise<void> {
        console.info("[kg-store] clearAll: starting");
        await initializeKGSchema();

        // Delete edges first — AGE's DETACH DELETE fails on Entity vertices because
        // CO_OCCURS edges connect Entity→Entity (both endpoints in the same batch).
        // Explicit edge deletion avoids that internal relation-lookup conflict.
        for (const edgeLabel of ["CO_OCCURS", "HAS_ENTITY", "PART_OF"]) {
            try {
                await cypher(`
                    SELECT * FROM cypher('${GRAPH_NAME}', $$
                        MATCH ()-[r:${edgeLabel}]-() DELETE r
                    $$) AS (result agtype)
                `);
                console.info(`[kg-store] clearAll: deleted all ${edgeLabel} edges`);
            } catch (err) {
                const msg = err instanceof Error ? err.message : String(err);
                console.warn(`[kg-store] clearAll: could not delete ${edgeLabel} edges: ${msg}`);
            }
        }

        // Plain DELETE (no DETACH) — edges are already gone
        for (const vertexLabel of ["Entity", "Chunk", "Document"]) {
            try {
                await cypher(`
                    SELECT * FROM cypher('${GRAPH_NAME}', $$
                        MATCH (n:${vertexLabel}) DELETE n
                    $$) AS (result agtype)
                `);
                console.info(`[kg-store] clearAll: deleted all ${vertexLabel} vertices`);
            } catch (err) {
                const msg = err instanceof Error ? err.message : String(err);
                console.warn(`[kg-store] clearAll: could not delete ${vertexLabel} vertices: ${msg}`);
            }
        }

        console.info("[kg-store] Knowledge graph cleared.");
    },

    /** Returns true if at least one Entity vertex exists in the graph. */
    async hasKnowledgeGraph(): Promise<boolean> {
        if (!_schemaInitialized) return false;
        try {
            const rows = await cypher(`
                SELECT * FROM cypher('${GRAPH_NAME}', $$
                    MATCH (e:Entity) RETURN e LIMIT 1
                $$) AS (e agtype)
            `);
            return rows.length > 0;
        } catch {
            return false;
        }
    },

    /** Returns all Entity vertices in the graph (up to 500). */
    async getAllEntities(): Promise<KGEntity[]> {
        if (!_schemaInitialized) return [];
        try {
            const rows = await cypher(`
                SELECT * FROM cypher('${GRAPH_NAME}', $$
                    MATCH (e:Entity) RETURN e.name, e.normalizedName, e.type
                $$) AS (name agtype, normalizedname agtype, type agtype)
                LIMIT 500
            `);
            return rows.map((row) => ({
                name: fromAgtype(row.name) ?? "",
                normalizedName: fromAgtype(row.normalizedname) ?? "",
                type: fromAgtype(row.type) ?? "OTHER",
            }));
        } catch (err) {
            console.warn("[kg-store] getAllEntities error:", err);
            return [];
        }
    },

    /** Returns all CO_OCCURS edges between entities (up to 1000, deduplicated). */
    async getAllRelations(): Promise<KGRelation[]> {
        if (!_schemaInitialized) return [];
        try {
            const rows = await cypher(`
                SELECT * FROM cypher('${GRAPH_NAME}', $$
                    MATCH (a:Entity)-[r:CO_OCCURS]-(b:Entity)
                    RETURN a.normalizedName, b.normalizedName, r.relType
                $$) AS (fromnorm agtype, tonorm agtype, reltype agtype)
                LIMIT 1000
            `);
            const seen = new Set<string>();
            const result: KGRelation[] = [];
            for (const row of rows) {
                const from = fromAgtype(row.fromnorm) ?? "";
                const to = fromAgtype(row.tonorm) ?? "";
                const relType = fromAgtype(row.reltype) ?? "RELATES_TO";
                if (!from || !to || from === to) continue;
                const key = [from, to].sort().join("|||");
                if (seen.has(key)) continue;
                seen.add(key);
                result.push({ from, to, relType });
            }
            return result;
        } catch (err) {
            console.warn("[kg-store] getAllRelations error:", err);
            return [];
        }
    },

    /** Returns all Documents that contain a given entity (by normalizedName). */
    async getEntityDocuments(normalizedName: string): Promise<KGDocument[]> {
        if (!_schemaInitialized) return [];
        const safeNorm = escapeCypher(normalizedName);
        try {
            const rows = await cypher(`
                SELECT * FROM cypher('${GRAPH_NAME}', $$
                    MATCH (d:Document)<-[:PART_OF]-(c:Chunk)-[:HAS_ENTITY]->(e:Entity)
                    WHERE e.normalizedName = '${safeNorm}'
                    RETURN DISTINCT d.fileName, d.documentId
                $$) AS (filename agtype, documentid agtype)
            `);
            return rows.map((row) => ({
                fileName: fromAgtype(row.filename) ?? "",
                documentId: fromAgtype(row.documentid) ?? "",
            }));
        } catch (err) {
            console.warn("[kg-store] getEntityDocuments error:", err);
            return [];
        }
    },

    /** Exposed for external callers that need access to extracted-graph types. */
    extractedGraphTypes: {} as { ExtractedEntity: ExtractedEntity; ExtractedRelation: ExtractedRelation },
};

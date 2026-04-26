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
        await cypher(`
            SELECT * FROM cypher('${GRAPH_NAME}', $$
                MERGE (d:Document {documentId: '${safeDocId}'})
                ON CREATE SET d.fileName = '${safeFileName}'
                ON MATCH  SET d.fileName = '${safeFileName}'
                RETURN d
            $$) AS (d agtype)
        `);

        // Upsert Chunk vertices and PART_OF edges
        for (let i = 0; i < chunkTexts.length; i++) {
            const chunkId = `${docId}_chunk_${i}`;
            const safeChunkId = escapeCypher(chunkId);
            // Truncate text stored in graph to 500 chars to keep graph lean;
            // full text lives in the embeddings table.
            const safeText = escapeCypher(chunkTexts[i].slice(0, 500));

            await cypher(`
                SELECT * FROM cypher('${GRAPH_NAME}', $$
                    MERGE (c:Chunk {chunkId: '${safeChunkId}'})
                    ON CREATE SET c.text = '${safeText}', c.documentId = '${safeDocId}', c.position = ${i}
                    ON MATCH  SET c.text = '${safeText}'
                    WITH c
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
                    ON CREATE SET e.name = '${safeName}', e.type = '${safeType}'
                    ON MATCH  SET e.name = '${safeName}', e.type = '${safeType}'
                    RETURN e
                $$) AS (e agtype)
            `);
        }

        // Upsert CO_OCCURS edges between entities from relations
        for (const rel of graph.relations) {
            const safeFrom = escapeCypher(rel.from);
            const safeTo = escapeCypher(rel.to);
            const safeType = escapeCypher(rel.type);

            // Skip self-loops
            if (rel.from === rel.to) continue;

            await cypher(`
                SELECT * FROM cypher('${GRAPH_NAME}', $$
                    MATCH (a:Entity {normalizedName: '${safeFrom}'}),
                          (b:Entity {normalizedName: '${safeTo}'})
                    MERGE (a)-[r:CO_OCCURS {relType: '${safeType}'}]->(b)
                    RETURN r
                $$) AS (r agtype)
            `);
        }

        // Link entities to the chunk they appear in (HAS_ENTITY edges).
        // We do a simple text-match: if the entity name appears in the chunk text,
        // create a HAS_ENTITY edge between that chunk and the entity.
        for (let i = 0; i < chunkTexts.length; i++) {
            const chunkText = chunkTexts[i].toLowerCase();
            const chunkId = `${docId}_chunk_${i}`;
            const safeChunkId = escapeCypher(chunkId);

            const mentionedEntities = graph.entities.filter((e) =>
                chunkText.includes(e.normalizedName)
            );

            for (const entity of mentionedEntities) {
                const safeNorm = escapeCypher(entity.normalizedName);
                await cypher(`
                    SELECT * FROM cypher('${GRAPH_NAME}', $$
                        MATCH (c:Chunk {chunkId: '${safeChunkId}'}),
                              (e:Entity {normalizedName: '${safeNorm}'})
                        MERGE (c)-[:HAS_ENTITY]->(e)
                        RETURN c
                    $$) AS (c agtype)
                `);
            }
        }

        console.info(`[kg-store] Graph written for document "${fileName}" (${graph.entities.length} entities, ${graph.relations.length} relations)`);
    },

    /**
     * Remove all graph nodes and edges for a document.
     * Called during document deletion.
     */
    async deleteDocumentGraph(docId: string): Promise<void> {
        if (!_schemaInitialized) return; // nothing to delete if schema never built
        const safeDocId = escapeCypher(docId);

        try {
            // Delete Chunk nodes and their edges
            await cypher(`
                SELECT * FROM cypher('${GRAPH_NAME}', $$
                    MATCH (c:Chunk {documentId: '${safeDocId}'})
                    DETACH DELETE c
                    RETURN 1
                $$) AS (result agtype)
            `);

            // Delete Document vertex
            await cypher(`
                SELECT * FROM cypher('${GRAPH_NAME}', $$
                    MATCH (d:Document {documentId: '${safeDocId}'})
                    DETACH DELETE d
                    RETURN 1
                $$) AS (result agtype)
            `);

            // Entity nodes are shared across documents — only delete if they have
            // no remaining HAS_ENTITY edges (i.e., no other chunks reference them).
            await cypher(`
                SELECT * FROM cypher('${GRAPH_NAME}', $$
                    MATCH (e:Entity)
                    WHERE NOT (e)<-[:HAS_ENTITY]-()
                    DELETE e
                    RETURN 1
                $$) AS (result agtype)
            `);

            console.info(`[kg-store] Deleted graph for document ${docId}`);
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

    /** Exposed for external callers that need access to extracted-graph types. */
    extractedGraphTypes: {} as { ExtractedEntity: ExtractedEntity; ExtractedRelation: ExtractedRelation },
};

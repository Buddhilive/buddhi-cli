/**
 * entity-extractor.ts
 *
 * Shared entity/relationship extraction utilities used by both the main thread
 * (Gemma-based extraction) and the KG pipeline worker (heuristic fallback).
 *
 * This module has NO browser-only dependencies so it can safely be imported
 * from a web worker.
 *
 * EXTRACTION MODES
 * ────────────────
 *  1. Gemma-based  — buildEntityExtractionPrompt() creates a structured JSON
 *                    prompt for the on-device Gemma model.  The response is
 *                    parsed by parseEntityExtractionResponse() with multi-layer
 *                    fallbacks.
 *
 *  2. Heuristic    — extractEntitiesHeuristic() is a purely deterministic
 *                    regex + TF-IDF approach used when Gemma is unavailable.
 *                    No model loading or network access required.
 */

// ─── Types ────────────────────────────────────────────────────────────────────

export interface ExtractedEntity {
    name: string;
    normalizedName: string; // lowercase, trimmed, deduplication key
    type: "PERSON" | "ORG" | "PRODUCT" | "CONCEPT" | "LOCATION" | "TECH" | "OTHER";
}

export interface ExtractedRelation {
    from: string;  // normalizedName of source entity
    to: string;    // normalizedName of target entity
    type: string;
}

export interface ExtractedGraph {
    entities: ExtractedEntity[];
    relations: ExtractedRelation[];
}

// ─── Normalization ────────────────────────────────────────────────────────────

export function normalizeEntityName(name: string): string {
    return name
        .toLowerCase()
        .trim()
        .replace(/\s+/g, " ")
        .replace(/[^\w\s-]/g, ""); // keep alphanumerics, spaces, hyphens
}

// ─── Gemma prompt builder ─────────────────────────────────────────────────────

const BATCH_SIZE = 4; // chunks per Gemma call

export function buildEntityExtractionPrompt(chunks: string[]): string {
    const segmentLines = chunks
        .slice(0, BATCH_SIZE)
        .map((c, i) => `[${i + 1}] ${c.slice(0, 600)}`)
        .join("\n\n");

    return `Extract named entities and relationships from the text segments below.
Return ONLY valid JSON — no explanation, no markdown fences.

Format:
{"entities":[{"name":"string","type":"PERSON|ORG|PRODUCT|CONCEPT|LOCATION|TECH|OTHER"}],"relations":[{"from":"entity name","to":"entity name","type":"RELATES_TO|USES|CREATES|PART_OF|OTHER"}]}

Rules:
- Include only specific named entities (people, organizations, products, technologies, places, key concepts)
- Omit generic nouns, articles, and common words
- Use full entity names as they appear in the text
- Each relation must reference entity names that appear in the entities list

Text segments:
${segmentLines}

JSON:`;
}

// ─── Gemma response parser ────────────────────────────────────────────────────

const KNOWN_ENTITY_TYPES = new Set([
    "PERSON", "ORG", "PRODUCT", "CONCEPT", "LOCATION", "TECH", "OTHER",
]);

// eslint-disable-next-line @typescript-eslint/no-explicit-any
function validateEntityType(t: unknown): ExtractedEntity["type"] {
    if (typeof t === "string" && KNOWN_ENTITY_TYPES.has(t.toUpperCase())) {
        return t.toUpperCase() as ExtractedEntity["type"];
    }
    return "OTHER";
}

export function parseEntityExtractionResponse(raw: string): ExtractedGraph {
    const empty: ExtractedGraph = { entities: [], relations: [] };
    if (!raw?.trim()) return empty;

    // Attempt 1: strip markdown code fences then parse
    let cleaned = raw.trim()
        .replace(/^```(?:json)?\s*/i, "")
        .replace(/\s*```\s*$/, "")
        .trim();

    // Attempt 2: extract first {...} JSON object from the response
    if (!cleaned.startsWith("{")) {
        const match = cleaned.match(/\{[\s\S]*\}/);
        cleaned = match ? match[0] : cleaned;
    }

    // Attempt 3: strip any trailing template tokens Gemma may leak
    cleaned = cleaned
        .replace(/<turn\|>\s*$/, "")
        .replace(/<end_of_turn>\s*$/, "")
        .trimEnd();

    let parsed: unknown;
    try {
        parsed = JSON.parse(cleaned);
    } catch {
        console.warn("[entity-extractor] Failed to parse Gemma entity extraction response as JSON. Raw:", raw.slice(0, 300));
        return empty;
    }

    if (typeof parsed !== "object" || parsed === null) return empty;
    const obj = parsed as Record<string, unknown>;

    // Validate and map entities
    const rawEntities = Array.isArray(obj.entities) ? obj.entities : [];
    const entities: ExtractedEntity[] = [];
    const seenNorm = new Set<string>();

    for (const e of rawEntities) {
        if (typeof e !== "object" || e === null) continue;
        const rec = e as Record<string, unknown>;
        const name = typeof rec.name === "string" ? rec.name.trim() : "";
        if (!name || name.length < 2 || name.length > 100) continue;

        const norm = normalizeEntityName(name);
        if (!norm || seenNorm.has(norm)) continue;
        seenNorm.add(norm);

        entities.push({
            name,
            normalizedName: norm,
            type: validateEntityType(rec.type),
        });
    }

    // Validate and map relations
    const rawRelations = Array.isArray(obj.relations) ? obj.relations : [];
    const relations: ExtractedRelation[] = [];
    const entityNorms = new Set(entities.map((e) => e.normalizedName));

    for (const r of rawRelations) {
        if (typeof r !== "object" || r === null) continue;
        const rec = r as Record<string, unknown>;
        const fromName = typeof rec.from === "string" ? rec.from.trim() : "";
        const toName = typeof rec.to === "string" ? rec.to.trim() : "";
        const relType = typeof rec.type === "string" ? rec.type.trim() : "RELATES_TO";

        const fromNorm = normalizeEntityName(fromName);
        const toNorm = normalizeEntityName(toName);

        // Only include relations where both endpoints exist in our entity list
        if (!entityNorms.has(fromNorm) || !entityNorms.has(toNorm)) continue;
        if (fromNorm === toNorm) continue; // no self-loops

        relations.push({ from: fromNorm, to: toNorm, type: relType.toUpperCase() });
    }

    return { entities, relations };
}

// ─── Heuristic NER fallback ───────────────────────────────────────────────────

const ENGLISH_STOPWORDS = new Set([
    "a","an","the","and","or","but","in","on","at","to","for","of","with","by",
    "from","as","is","was","are","were","be","been","being","have","has","had",
    "do","does","did","will","would","could","should","may","might","shall","can",
    "that","this","these","those","it","its","i","we","you","he","she","they",
    "my","your","his","her","our","their","what","which","who","when","where",
    "why","how","all","each","every","both","few","more","most","other","some",
    "such","no","not","only","same","so","than","too","very","just","also",
    "into","through","during","before","after","above","below","between","out",
    "up","down","about","over","then","there","here","if","while","although",
    "because","since","unless","until","once","whether","though","even","yet",
]);

const PROPER_NOUN_RE = /\b([A-Z][a-zA-Z-]{1,}(?:\s+[A-Z][a-zA-Z-]{1,}){0,4})\b/g;
const ACRONYM_RE = /\b([A-Z]{2,8})\b/g;
const CAMEL_CASE_RE = /\b([a-z][a-zA-Z]{3,}[A-Z][a-zA-Z]*)\b/g;
const QUOTED_RE = /"([^"]{2,60})"|'([^']{2,60})'/g;
const TECH_RE = /\b([a-zA-Z][a-zA-Z0-9]*(?:[._-][a-zA-Z0-9]+)+)\b/g; // dotted/hyphenated technical terms

function classifyHeuristic(name: string): ExtractedEntity["type"] {
    const lower = name.toLowerCase();
    if (/[A-Z]{2,}/.test(name)) return "TECH";
    if (/[a-z][A-Z]/.test(name)) return "TECH";
    if (/\d/.test(name)) return "PRODUCT";
    if (/\b(corp|inc|ltd|llc|co\.|university|institute|foundation|labs?)\b/i.test(lower)) return "ORG";
    if (/\b(street|avenue|city|country|region|state|province|mountain|river|lake|ocean)\b/i.test(lower)) return "LOCATION";
    if (/\b(api|sdk|framework|library|protocol|algorithm|model|system|platform|tool|service|database)\b/i.test(lower)) return "TECH";
    return "CONCEPT";
}

export function extractEntitiesHeuristic(chunks: string[]): ExtractedGraph {
    const text = chunks.join(" ");

    const candidateFreq = new Map<string, number>();

    // Collect candidates from multiple pattern types
    const addCandidates = (re: RegExp, matchIdx: number = 0) => {
        let match: RegExpExecArray | null;
        re.lastIndex = 0;
        while ((match = re.exec(text)) !== null) {
            const raw = (match[matchIdx] ?? match[0]).trim();
            if (!raw || raw.length < 2 || raw.length > 80) continue;
            const norm = normalizeEntityName(raw);
            if (!norm || ENGLISH_STOPWORDS.has(norm)) continue;
            // Filter pure lowercase words that aren't technical terms
            if (re === PROPER_NOUN_RE && raw === raw.toLowerCase()) continue;
            candidateFreq.set(norm, (candidateFreq.get(norm) ?? 0) + 1);
        }
    };

    addCandidates(PROPER_NOUN_RE, 1);
    addCandidates(ACRONYM_RE, 1);
    addCandidates(CAMEL_CASE_RE, 1);
    addCandidates(TECH_RE, 1);

    // Quoted terms (capture groups 1 or 2)
    let match: RegExpExecArray | null;
    QUOTED_RE.lastIndex = 0;
    while ((match = QUOTED_RE.exec(text)) !== null) {
        const raw = (match[1] ?? match[2] ?? "").trim();
        if (!raw || raw.length < 2 || raw.length > 80) continue;
        const norm = normalizeEntityName(raw);
        if (!norm || ENGLISH_STOPWORDS.has(norm)) continue;
        candidateFreq.set(norm, (candidateFreq.get(norm) ?? 0) + 2); // boost quoted terms
    }

    // Keep entities that appear at least once; rank by frequency
    const entities: ExtractedEntity[] = Array.from(candidateFreq.entries())
        .filter(([, freq]) => freq >= 1)
        .sort((a, b) => b[1] - a[1])
        .slice(0, 50) // cap at 50 entities per document
        .map(([norm]) => {
            // Reconstruct display name: find first occurrence with original casing
            const displayRe = new RegExp(`\\b${norm.replace(/[.*+?^${}()|[\]\\]/g, "\\$&")}\\b`, "i");
            const origMatch = displayRe.exec(text);
            const name = origMatch ? origMatch[0] : norm;
            return {
                name,
                normalizedName: norm,
                type: classifyHeuristic(name),
            };
        });

    // Build co-occurrence relations per chunk
    const relations: ExtractedRelation[] = [];
    const entityNorms = new Set(entities.map((e) => e.normalizedName));
    const seenPairs = new Set<string>();

    for (const chunkText of chunks) {
        const lowerChunk = chunkText.toLowerCase();
        const presentInChunk = entities.filter((e) =>
            lowerChunk.includes(e.normalizedName)
        );

        // Add CO_OCCURS edges for all pairs within this chunk
        for (let i = 0; i < presentInChunk.length; i++) {
            for (let j = i + 1; j < presentInChunk.length; j++) {
                const a = presentInChunk[i].normalizedName;
                const b = presentInChunk[j].normalizedName;
                if (!entityNorms.has(a) || !entityNorms.has(b)) continue;
                const pairKey = [a, b].sort().join("|||");
                if (seenPairs.has(pairKey)) continue;
                seenPairs.add(pairKey);
                relations.push({ from: a, to: b, type: "CO_OCCURS" });
            }
        }
    }

    return { entities, relations };
}

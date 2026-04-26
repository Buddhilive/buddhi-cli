/**
 * documents.ts — Global Knowledge Base API
 *
 * Manages the full document lifecycle:
 *   1. Validate & store raw file in IndexedDB ("buddhi-ai-doc-store")
 *   2. Run TWO vectorization pipelines in parallel:
 *      a) Embedding pipeline (web worker): extract → chunk → embed → PGlite vector store
 *      b) KG pipeline (web worker + Gemma relay): extract entities → build AGE graph
 *   3. Track real-time progress for both pipelines via the Zustand document-store
 *   4. Support reconciliation of documents interrupted by a page close
 */

import { extractTextFromPDF } from "@/lib/text-embeddings";
import {
    chunkText,
    createVectorIndexBatched,
    deleteDocumentEmbeddings,
} from "@/lib/llamaindex-provider";
import { kgStore } from "@/lib/kg-store";
import { buildEntityExtractionPrompt, parseEntityExtractionResponse } from "@/lib/entity-extractor";
import { useDocumentStore } from "@/stores/document-store";
import { useLiteRTModelStore } from "@/stores/litert-store";
import { DocPhase, DocumentInfo, DocStoreRecord } from "@/types/documents";
import type {
    KGWorkerProcessRequest,
    KGWorkerRequest,
    KGWorkerResponse,
} from "@/workers/kg-pipeline-worker";
import type { ExtractedGraph } from "@/lib/entity-extractor";

// ─── Constants ────────────────────────────────────────────────────────────────

const DOC_STORE_DB_NAME = "buddhi-ai-doc-store";
const DOC_STORE_DB_VERSION = 1;
const DOC_STORE_NAME = "documents";

const MAX_FILE_SIZE_BYTES = 25 * 1024 * 1024; // 25 MB
const SUPPORTED_EXTENSIONS = ["pdf", "txt", "md"];

/** chatId used in PGlite for all global knowledge-base documents */
export const GLOBAL_KB_CHAT_ID = "knowledge-base-global";

// ─── IndexedDB helpers ────────────────────────────────────────────────────────

let _db: IDBDatabase | null = null;

function openDocStoreDB(): Promise<IDBDatabase> {
    if (_db) return Promise.resolve(_db);

    return new Promise((resolve, reject) => {
        const req = indexedDB.open(DOC_STORE_DB_NAME, DOC_STORE_DB_VERSION);

        req.onerror = () =>
            reject(new Error(`Failed to open doc store: ${req.error?.message ?? req.error}`));

        req.onsuccess = () => {
            _db = req.result;
            req.result.onclose = () => { _db = null; };
            resolve(req.result);
        };

        req.onupgradeneeded = () => {
            const db = req.result;
            if (!db.objectStoreNames.contains(DOC_STORE_NAME)) {
                const store = db.createObjectStore(DOC_STORE_NAME, { keyPath: "id" });
                store.createIndex("status", "status", { unique: false });
            }
        };
    });
}

async function idbPut(record: DocStoreRecord): Promise<void> {
    const db = await openDocStoreDB();
    return new Promise((resolve, reject) => {
        const tx = db.transaction(DOC_STORE_NAME, "readwrite");
        const req = tx.objectStore(DOC_STORE_NAME).put(record);
        req.onsuccess = () => resolve();
        req.onerror = () =>
            reject(new Error(`IDB put failed: ${req.error?.message ?? req.error}`));
    });
}

async function idbUpdate(id: number, patch: Partial<DocStoreRecord>): Promise<void> {
    const db = await openDocStoreDB();
    return new Promise((resolve, reject) => {
        const tx = db.transaction(DOC_STORE_NAME, "readwrite");
        const store = tx.objectStore(DOC_STORE_NAME);
        const getReq = store.get(id);

        getReq.onsuccess = () => {
            const existing: DocStoreRecord | undefined = getReq.result;
            if (!existing) {
                resolve();
                return;
            }
            const putReq = store.put({ ...existing, ...patch });
            putReq.onsuccess = () => resolve();
            putReq.onerror = () =>
                reject(new Error(`IDB update failed: ${putReq.error?.message ?? putReq.error}`));
        };

        getReq.onerror = () =>
            reject(new Error(`IDB get failed: ${getReq.error?.message ?? getReq.error}`));
    });
}

async function idbGet(id: number): Promise<DocStoreRecord | null> {
    const db = await openDocStoreDB();
    return new Promise((resolve, reject) => {
        const tx = db.transaction(DOC_STORE_NAME, "readonly");
        const req = tx.objectStore(DOC_STORE_NAME).get(id);
        req.onsuccess = () => resolve(req.result ?? null);
        req.onerror = () =>
            reject(new Error(`IDB get failed: ${req.error?.message ?? req.error}`));
    });
}

async function idbGetAll(): Promise<DocStoreRecord[]> {
    const db = await openDocStoreDB();
    return new Promise((resolve, reject) => {
        const tx = db.transaction(DOC_STORE_NAME, "readonly");
        const req = tx.objectStore(DOC_STORE_NAME).getAll();
        req.onsuccess = () => resolve(req.result ?? []);
        req.onerror = () =>
            reject(new Error(`IDB getAll failed: ${req.error?.message ?? req.error}`));
    });
}

async function idbDelete(id: number): Promise<void> {
    const db = await openDocStoreDB();
    return new Promise((resolve, reject) => {
        const tx = db.transaction(DOC_STORE_NAME, "readwrite");
        const req = tx.objectStore(DOC_STORE_NAME).delete(id);
        req.onsuccess = () => resolve();
        req.onerror = () =>
            reject(new Error(`IDB delete failed: ${req.error?.message ?? req.error}`));
    });
}

function toInfo(record: DocStoreRecord): DocumentInfo {
    // eslint-disable-next-line @typescript-eslint/no-unused-vars
    const { file_data, ...info } = record;
    return info;
}

// ─── Worker singletons ────────────────────────────────────────────────────────

let _kgWorker: Worker | null = null;

function getKGWorker(): Worker {
    if (typeof window === "undefined") throw new Error("Workers only available in browser.");
    if (!_kgWorker) {
        _kgWorker = new Worker(
            new URL("../workers/kg-pipeline-worker.ts", import.meta.url),
            { type: "module" }
        );
    }
    return _kgWorker;
}

// ─── Gemma entity extraction relay ───────────────────────────────────────────

// Resolves only when the last Gemma inference WE started fires done=true.
// Prevents "still ongoing" errors when our timeout fires but Gemma is still running.
let _gemmaIdlePromise: Promise<void> = Promise.resolve();

// Soft timeout: give up waiting for the result and post entities-error.
// The idle lock stays held so the next batch waits for Gemma to truly finish.
const GEMMA_SOFT_TIMEOUT_MS = 90_000;
// Hard timeout: release the idle lock unconditionally (safety net for hung models).
const GEMMA_HARD_TIMEOUT_MS = 120_000;  // 30 s after soft timeout, releases idle lock
// Retry for external-caller busyness (e.g. chat generating a response).
const GEMMA_BUSY_RETRY_DELAY_MS = 3_000;
const GEMMA_BUSY_MAX_RETRIES = 4;

/**
 * Called when the KG worker posts a 'request-entities' message.
 * Runs Gemma on the main thread and posts the result back to the KG worker.
 *
 * MediaPipe LlmInference is not re-entrant. Two problems can occur:
 *   A) Our soft timeout fires before Gemma finishes — we post entities-error but
 *      Gemma keeps running. The next batch must wait for it to truly complete
 *      before calling generateResponse again (handled by _gemmaIdlePromise lock).
 *   B) An external caller (e.g. chat) is generating — generateResponse throws
 *      synchronously. We retry with backoff (handled by the retry loop).
 */
async function handleEntityExtractionRequest(
    requestId: string,
    chunks: string[]
): Promise<void> {
    const kgWorker = getKGWorker();
    const { liteRTModelInstance, liteRTModelStatus } = useLiteRTModelStore.getState();

    if (!liteRTModelInstance || liteRTModelStatus !== "ready") {
        console.warn("[documents] Gemma not ready for entity extraction — KG worker will use heuristic fallback.");
        kgWorker.postMessage({
            type: "entities-error",
            requestId,
            error: "Language model not loaded. Using heuristic entity extraction.",
        } satisfies KGWorkerRequest);
        return;
    }

    // Wait for any Gemma inference we started to truly complete (done=true callback).
    await _gemmaIdlePromise;

    const prompt = buildEntityExtractionPrompt(chunks);

    for (let attempt = 0; attempt <= GEMMA_BUSY_MAX_RETRIES; attempt++) {
        if (attempt > 0) {
            await new Promise<void>((r) => setTimeout(r, GEMMA_BUSY_RETRY_DELAY_MS));
        }

        let accumulated = "";
        let timedOut = false;

        // Create signalIdle BEFORE calling generateResponse so the callback
        // can call it even if MediaPipe fires done=true synchronously inside the call.
        let signalIdle!: () => void;
        const pendingIdlePromise = new Promise<void>((r) => { signalIdle = r; });

        try {
            await new Promise<void>((resolve, reject) => {
                const softTimeout = setTimeout(() => {
                    timedOut = true;
                    resolve(); // unblock this await; idle lock stays held — Gemma still running
                }, GEMMA_SOFT_TIMEOUT_MS);

                const hardTimeout = setTimeout(() => {
                    // Safety net: release the lock even if done=true never fires
                    signalIdle();
                }, GEMMA_HARD_TIMEOUT_MS);

                try {
                    liteRTModelInstance.generateResponse(
                        prompt,
                        (partial: string, done: boolean) => {
                            accumulated += partial;
                            if (done) {
                                clearTimeout(softTimeout);
                                clearTimeout(hardTimeout);
                                signalIdle(); // Gemma truly idle — next call can proceed
                                resolve();
                            }
                        }
                    );
                    // generateResponse accepted the call — promote to the shared idle lock.
                    // The next handleEntityExtractionRequest will await this Promise.
                    _gemmaIdlePromise = pendingIdlePromise;
                } catch (syncErr) {
                    clearTimeout(softTimeout);
                    clearTimeout(hardTimeout);
                    signalIdle(); // threw without starting — release the local promise too
                    reject(syncErr); // "still ongoing" — handled by retry loop below
                }
            });

            if (timedOut) {
                console.warn(`[documents] Gemma timed out for request ${requestId}`);
                kgWorker.postMessage({
                    type: "entities-error",
                    requestId,
                    error: "Gemma entity extraction timed out",
                } satisfies KGWorkerRequest);
                return;
            }

            const graph: ExtractedGraph = parseEntityExtractionResponse(accumulated);
            console.log(`[documents] Gemma extracted ${graph.entities.length} entities for request ${requestId}`);
            kgWorker.postMessage({
                type: "entities-result",
                requestId,
                graph,
            } satisfies KGWorkerRequest);
            return;

        } catch (err) {
            const msg = err instanceof Error ? err.message : String(err);

            if (msg.includes("still ongoing") && attempt < GEMMA_BUSY_MAX_RETRIES) {
                console.warn(`[documents] Gemma busy for ${requestId}, retry ${attempt + 1}/${GEMMA_BUSY_MAX_RETRIES}`);
                continue;
            }

            console.warn("[documents] Gemma entity extraction failed:", msg);
            kgWorker.postMessage({
                type: "entities-error",
                requestId,
                error: msg,
            } satisfies KGWorkerRequest);
            return;
        }
    }

    kgWorker.postMessage({
        type: "entities-error",
        requestId,
        error: "Gemma busy — all retries exhausted",
    } satisfies KGWorkerRequest);
}

// ─── Embedding pipeline (main thread) ────────────────────────────────────────

async function runEmbeddingPipeline(
    doc: DocumentInfo,
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    chunks: any[]
): Promise<void> {
    const store = useDocumentStore.getState();
    try {
        const result = await createVectorIndexBatched(
            chunks,
            GLOBAL_KB_CHAT_ID,
            doc.id.toString(),
            doc.original_name,
            (processed, total) => {
                const pct = 35 + Math.round((processed / total) * 60);
                store.updateProgress(doc.id, "embedding" as DocPhase, Math.min(pct, 95));
            }
        );
        await idbUpdate(doc.id, {
            status: "completed",
            chunk_count: result.chunkCount,
            error_msg: null,
        });
        store.completeDoc(doc.id, result.chunkCount);
    } catch (err) {
        const errMsg = err instanceof Error ? err.message : String(err);
        try { await idbUpdate(doc.id, { status: "failed", error_msg: errMsg }); } catch { /* non-fatal */ }
        try { await deleteDocumentEmbeddings(doc.id.toString()); } catch { /* non-fatal */ }
        store.failDoc(doc.id, errMsg);
        throw err;
    }
}

// ─── KG pipeline runner ───────────────────────────────────────────────────────

function runKGPipeline(
    doc: DocumentInfo,
    chunkTexts: string[]
): Promise<void> {
    return new Promise((resolve) => {
        // KG failures are non-fatal — always resolve (never reject)
        const worker = getKGWorker();
        const store = useDocumentStore.getState();

        const onMessage = async (event: MessageEvent<KGWorkerResponse>) => {
            const msg = event.data;

            // Handle entity extraction relay — no docId check needed
            if (msg.type === "request-entities") {
                handleEntityExtractionRequest(msg.requestId, msg.chunks);
                return;
            }

            if (!("docId" in msg) || msg.docId !== doc.id.toString()) return;

            switch (msg.type) {
                case "progress": {
                    store.updateGraphProgress(doc.id, msg.phase, msg.pct);
                    break;
                }

                case "result": {
                    try {
                        await kgStore.init();
                        await kgStore.addDocumentGraph(
                            doc.id.toString(),
                            doc.original_name,
                            chunkTexts,
                            { entities: msg.entities, relations: msg.relations }
                        );
                    } catch (writeErr) {
                        const errMsg = writeErr instanceof Error ? writeErr.message : String(writeErr);
                        console.error("[documents] KG AGE write error:", writeErr);
                        worker.removeEventListener("message", onMessage);
                        store.failGraph(doc.id, `Failed to write knowledge graph: ${errMsg}`);
                        resolve();
                    }
                    break;
                }

                case "complete": {
                    worker.removeEventListener("message", onMessage);
                    store.completeGraph(doc.id, msg.entityCount);
                    resolve();
                    break;
                }

                case "error": {
                    worker.removeEventListener("message", onMessage);
                    store.failGraph(doc.id, msg.message);
                    resolve(); // non-fatal
                    break;
                }
            }
        };

        worker.addEventListener("message", onMessage);

        worker.postMessage({
            type: "process",
            docId: doc.id.toString(),
            fileName: doc.original_name,
            chunkTexts,
        } satisfies KGWorkerProcessRequest);
    });
}

// ─── Main pipeline ────────────────────────────────────────────────────────────

async function runPipeline(doc: DocumentInfo, fileData: ArrayBuffer): Promise<void> {
    const store = useDocumentStore.getState();

    try {
        // ── Stage 1: text extraction ──────────────────────────────────────────
        store.updateProgress(doc.id, "reading" as DocPhase, 5);
        await idbUpdate(doc.id, { status: "processing" });

        const file = new File([fileData], doc.original_name);
        const ext = doc.original_name.split(".").pop()?.toLowerCase();

        let text: string;
        if (ext === "pdf") {
            text = await extractTextFromPDF(file);
        } else {
            text = await file.text();
        }

        if (!text || text.trim().length === 0) {
            throw new Error(
                ext === "pdf"
                    ? "No extractable text found. Scanned/image-only PDFs are not supported — please use a text-based PDF."
                    : "File appears to be empty."
            );
        }

        // ── Stage 2: chunking (main thread — shared for both workers) ─────────
        store.updateProgress(doc.id, "chunking" as DocPhase, 30);
        const chunks = await chunkText(text, 200, 20, doc.id.toString());

        if (chunks.length === 0) {
            throw new Error("No chunks were generated — the document may contain only whitespace.");
        }

        const chunkTexts = chunks.map((c) => c.text ?? "");

        // ── Stage 3a: embedding (main thread — LiteRT/WebGPU) ────────────────
        // Embedding must complete before KG starts: both LiteRT and Gemma use
        // WebGPU, and running them concurrently causes Gemma to time out.
        await runEmbeddingPipeline(doc, chunks);

        // ── Stage 3b: knowledge graph (worker — Gemma/WebGPU) ────────────────
        // KG failure is non-fatal — the document stays fully searchable via vectors.
        store.updateGraphProgress(doc.id, "graph-extracting", 0);
        await runKGPipeline(doc, chunkTexts);

    } catch (error) {
        const msg =
            error instanceof Error ? error.message : "An unknown error occurred during processing.";
        console.error(`[documents] Pipeline error for doc ${doc.id} ("${doc.original_name}"):`, error);

        try {
            await idbUpdate(doc.id, { status: "failed", error_msg: msg });
        } catch (updateErr) {
            console.error("[documents] Could not persist failure to IDB:", updateErr);
        }

        try {
            await deleteDocumentEmbeddings(doc.id.toString());
        } catch (cleanupErr) {
            console.error("[documents] Could not clean up partial embeddings:", cleanupErr);
        }

        store.failDoc(doc.id, msg);
    }
}

// ─── Public API ───────────────────────────────────────────────────────────────

export const documentsApi = {
    async uploadDocument(file: File): Promise<DocumentInfo> {
        const ext = file.name.split(".").pop()?.toLowerCase() ?? "";
        if (!SUPPORTED_EXTENSIONS.includes(ext)) {
            throw new Error(
                `Unsupported file type ".${ext}". Please upload a PDF, TXT, or MD file.`
            );
        }

        if (file.size > MAX_FILE_SIZE_BYTES) {
            throw new Error(
                `"${file.name}" is ${(file.size / 1024 / 1024).toFixed(1)} MB — ` +
                `files must be 25 MB or smaller.`
            );
        }

        const activeCount = useDocumentStore.getState().activeCount;
        if (activeCount >= 5) {
            throw new Error(
                "Processing queue is full (5/5 slots in use). Wait for a document to finish before uploading more."
            );
        }

        let fileData: ArrayBuffer;
        try {
            fileData = await file.arrayBuffer();
        } catch {
            throw new Error(`Could not read "${file.name}". The file may be locked or corrupted.`);
        }

        const id = Date.now();
        const doc: DocumentInfo = {
            id,
            original_name: file.name,
            file_size: file.size,
            status: "pending",
            chunk_count: null,
            error_msg: null,
            created_at: new Date().toISOString(),
        };

        try {
            await idbPut({ ...doc, file_data: fileData });
        } catch (err) {
            const msg = err instanceof Error ? err.message : String(err);
            if (msg.toLowerCase().includes("quota")) {
                throw new Error(
                    "Browser storage quota exceeded. Delete some documents to free space before uploading."
                );
            }
            throw new Error(`Failed to save document to local storage: ${msg}`);
        }

        useDocumentStore.getState().initDoc(id);
        runPipeline(doc, fileData); // intentionally not awaited

        return doc;
    },

    async listDocuments(): Promise<DocumentInfo[]> {
        try {
            const records = await idbGetAll();
            return records
                .map(toInfo)
                .sort(
                    (a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime()
                );
        } catch (err) {
            throw new Error(
                `Failed to load documents: ${err instanceof Error ? err.message : String(err)}`
            );
        }
    },

    async getDocument(id: number): Promise<DocumentInfo> {
        const record = await idbGet(id);
        if (!record) throw new Error(`Document ${id} not found.`);
        return toInfo(record);
    },

    async deleteDocument(id: number): Promise<void> {
        await Promise.allSettled([
            deleteDocumentEmbeddings(id.toString()).catch((err) =>
                console.error(`[documents] Failed to delete embeddings for doc ${id}:`, err)
            ),
            kgStore.deleteDocumentGraph(id.toString()).catch((err) =>
                console.error(`[documents] Failed to delete KG data for doc ${id}:`, err)
            ),
        ]);

        await idbDelete(id);
        useDocumentStore.getState().removeDoc(id);
    },
};

// ─── Reconciliation ───────────────────────────────────────────────────────────

export async function reconcileInterruptedDocuments(): Promise<void> {
    try {
        const records = await idbGetAll();
        const interrupted = records.filter(
            (r) => r.status === "pending" || r.status === "processing"
        );

        if (interrupted.length === 0) return;

        console.info(
            `[documents] Reconciling ${interrupted.length} interrupted document(s)…`
        );

        const store = useDocumentStore.getState();

        for (const record of interrupted) {
            if (store.activeCount < 5) {
                store.initDoc(record.id);
                runPipeline(toInfo(record), record.file_data);
            } else {
                await idbUpdate(record.id, {
                    status: "failed",
                    error_msg:
                        "Processing was interrupted (page was closed or refreshed). Please re-upload the file.",
                });
            }
        }
    } catch (err) {
        console.error("[documents] reconcileInterruptedDocuments failed:", err);
    }
}

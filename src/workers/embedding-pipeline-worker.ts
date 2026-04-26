/**
 * embedding-pipeline-worker.ts
 *
 * Web Worker: runs the LiteRT embedding model in a background thread so the
 * main thread stays responsive during document processing.
 *
 * FLOW
 * ────
 *  Main thread sends  { type: 'process', docId, chunks }
 *  Worker initialises LiteRT (lazy, on first 'process' message)
 *  Worker processes chunks in batches of BATCH_SIZE
 *  For each batch:   postMessage({ type: 'batch', docId, chunks: [...] })
 *  On completion:    postMessage({ type: 'complete', docId, totalChunks })
 *  On any error:     postMessage({ type: 'error', docId, message })
 *
 * Serialization: embeddings are plain number[] — structured-clone friendly.
 * The main thread reconstructs TextNode objects for PGlite writes.
 */

import * as LiteRT from "@litertjs/core";
import { AutoTokenizer } from "@huggingface/transformers";
import type { SerializableChunk, SerializableEmbeddedChunk } from "@/lib/llamaindex-provider";

// ─── Message types ────────────────────────────────────────────────────────────

export interface EmbeddingWorkerRequest {
    type: "process";
    docId: string;
    chunks: SerializableChunk[];
}

export interface EmbeddingBatchMessage {
    type: "batch";
    docId: string;
    chunks: SerializableEmbeddedChunk[];
    processed: number;
    total: number;
}

export interface EmbeddingProgressMessage {
    type: "progress";
    docId: string;
    pct: number;
    processed: number;
    total: number;
}

export interface EmbeddingCompleteMessage {
    type: "complete";
    docId: string;
    totalChunks: number;
}

export interface EmbeddingErrorMessage {
    type: "error";
    docId: string;
    message: string;
}

export type EmbeddingWorkerResponse =
    | EmbeddingBatchMessage
    | EmbeddingProgressMessage
    | EmbeddingCompleteMessage
    | EmbeddingErrorMessage;

// ─── Config ───────────────────────────────────────────────────────────────────

const BUDDHI_CACHE_NAME = "buddhi-ai-models-cache-v1";
const EMBEDDING_MODEL_ID = "litert-community/embeddinggemma-300m";
const LITERTJS_WASM_PATH = "/litert-wasm/";
const SEQ_LEN = 2048;
const DOC_PREFIX = "title: none | text: ";
const BATCH_SIZE = 50;

// ─── Embedding model ──────────────────────────────────────────────────────────

// eslint-disable-next-line @typescript-eslint/no-explicit-any
let model: any = null;
// eslint-disable-next-line @typescript-eslint/no-explicit-any
let tokenizer: any = null;

async function initModel(): Promise<void> {
    if (model && tokenizer) return;

    await LiteRT.loadLiteRt(LITERTJS_WASM_PATH);

    tokenizer = await AutoTokenizer.from_pretrained(
        "onnx-community/embeddinggemma-300m-ONNX"
    );

    const cacheKey = `https://cache.buddhi-ai.local/models/${EMBEDDING_MODEL_ID.replace(/\//g, "_")}`;
    const cache = await caches.open(BUDDHI_CACHE_NAME);
    const response = await cache.match(new Request(cacheKey));

    if (!response) {
        throw new Error(
            'Embedding model not installed. Install "Embedding Gemma 300M" from the Models page.'
        );
    }

    const objectUrl = URL.createObjectURL(await response.blob());
    try {
        model = await LiteRT.loadAndCompile(objectUrl);
    } finally {
        URL.revokeObjectURL(objectUrl);
    }
}

async function embedText(text: string): Promise<number[]> {
    const prefixed = DOC_PREFIX + text;
    const tokens = await tokenizer(prefixed, {
        padding: "max_length",
        max_length: SEQ_LEN,
        truncation: true,
        return_tensors: "np",
    });

    const rawIds = tokens.input_ids.data as BigInt64Array | Int32Array;
    const int32Ids = new Int32Array(rawIds.length);
    for (let i = 0; i < rawIds.length; i++) {
        int32Ids[i] = Number(rawIds[i]);
    }

    const env = LiteRT.getDefaultEnvironment();
    const inputTensor = LiteRT.Tensor.fromTypedArray(int32Ids, [1, SEQ_LEN], env);
    const outputs = await model.run([inputTensor]);
    const embedding = Array.from(await outputs[0].data() as Float32Array);
    inputTensor.delete();
    outputs[0].delete();
    return embedding;
}

// ─── Message handler ──────────────────────────────────────────────────────────

self.onmessage = async (event: MessageEvent<EmbeddingWorkerRequest>) => {
    const { type, docId, chunks } = event.data;
    if (type !== "process") return;

    try {
        // Lazy model initialization
        await initModel();

        const total = chunks.length;
        let processed = 0;

        for (let i = 0; i < chunks.length; i += BATCH_SIZE) {
            const batch = chunks.slice(i, i + BATCH_SIZE);
            const embeddedBatch: SerializableEmbeddedChunk[] = [];

            for (const chunk of batch) {
                const embedding = await embedText(chunk.text);
                embeddedBatch.push({ ...chunk, embedding });
                processed++;
            }

            const pct = 35 + Math.round((processed / total) * 60);

            self.postMessage({
                type: "batch",
                docId,
                chunks: embeddedBatch,
                processed,
                total,
            } satisfies EmbeddingBatchMessage);

            self.postMessage({
                type: "progress",
                docId,
                pct: Math.min(pct, 95),
                processed,
                total,
            } satisfies EmbeddingProgressMessage);
        }

        self.postMessage({
            type: "complete",
            docId,
            totalChunks: total,
        } satisfies EmbeddingCompleteMessage);

    } catch (err) {
        const message = err instanceof Error ? err.message : "Unknown embedding error.";
        console.error(`[embedding-worker] Error processing doc ${docId}:`, err);
        self.postMessage({
            type: "error",
            docId,
            message,
        } satisfies EmbeddingErrorMessage);
    }
};

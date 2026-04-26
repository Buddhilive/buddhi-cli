export type DocPhase = "reading" | "chunking" | "embedding" | null;
export type GraphPhase = "graph-extracting" | "graph-building" | null;
export type DocProcessingStatus = "pending" | "processing" | "completed" | "failed";

export interface DocProcessingState {
    status: DocProcessingStatus;
    phase: DocPhase;
    overallPct: number; // 0–100
    graphPct: number; // 0–100 — KG pipeline progress
    graphPhase: GraphPhase;
    chunkCount: number | null;
    entityCount: number | null; // entities indexed in knowledge graph
    errorMsg: string | null;
    graphErrorMsg: string | null; // non-fatal: document still vector-searchable
}

export interface DocumentStore {
    docs: Record<number, DocProcessingState>;
    activeCount: number;
    initDoc(id: number): void;
    updateProgress(id: number, phase: DocPhase, overallPct: number): void;
    completeDoc(id: number, chunkCount: number): void;
    failDoc(id: number, errorMsg: string): void;
    updateGraphProgress(id: number, phase: GraphPhase, pct: number): void;
    completeGraph(id: number, entityCount: number): void;
    failGraph(id: number, errorMsg: string): void;
    removeDoc(id: number): void;
}

export type DocumentStatus =
    | "uploading"
    | "chunking"
    | "embedding"
    | "saving"
    | "ready"
    | "error";

export interface DocumentItem {
    id: string;
    fileName: string;
    status: DocumentStatus;
    progress: number;
    error?: string;
    fileSize?: number;
}

export interface ProcessingProgress {
    stage: "reading" | "chunking" | "embedding" | "saving";
    progress: number;
    total: number;
    documentId: string;
}

export interface WorkerMessage {
    type: "progress" | "complete" | "error";
    documentId: string;
    progress?: ProcessingProgress;
    error?: string;
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    index?: any;
}

export interface WorkerRequest {
    type: "process";
    documentId: string;
    fileName: string;
    text: string;
    chatId: string;
}

export interface DocumentInfo {
    id: number;
    original_name: string;
    file_size: number;
    status: "pending" | "processing" | "completed" | "failed";
    chunk_count: number | null;
    error_msg: string | null;
    created_at: string;
}

export interface DocStoreRecord extends DocumentInfo {
    file_data: ArrayBuffer;
}
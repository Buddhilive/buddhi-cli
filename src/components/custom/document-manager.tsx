"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { documentsApi, reconcileInterruptedDocuments } from "@/lib/documents";
import { useDocumentStore } from "@/stores/document-store";
import { toast } from "sonner";
import {
    AlertCircleIcon,
    CheckCircleIcon,
    DatabaseIcon,
    FileTextIcon,
    RefreshCcwIcon,
    Trash2Icon,
    UploadCloudIcon,
} from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Progress } from "@/components/ui/progress";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import {
    Table,
    TableBody,
    TableCell,
    TableHead,
    TableHeader,
    TableRow,
} from "@/components/ui/table";
import {
    Dialog,
    DialogContent,
    DialogDescription,
    DialogFooter,
    DialogHeader,
    DialogTitle,
} from "@/components/ui/dialog";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { DocumentInfo } from "@/types/documents";

// ─── Status badge ─────────────────────────────────────────────────────────────

function StatusBadge({ status }: { status: DocumentInfo["status"] }) {
    switch (status) {
        case "completed":
            return (
                <Badge className="bg-green-600 text-white shrink-0 gap-1">
                    <CheckCircleIcon className="h-3 w-3" />
                    Ready
                </Badge>
            );
        case "processing":
            return (
                <Badge variant="secondary" className="animate-pulse shrink-0">
                    Processing
                </Badge>
            );
        case "pending":
            return (
                <Badge variant="outline" className="animate-pulse shrink-0">
                    Queued
                </Badge>
            );
        case "failed":
            return (
                <Badge variant="destructive" className="shrink-0">
                    Failed
                </Badge>
            );
        default:
            return <Badge variant="outline" className="shrink-0">Unknown</Badge>;
    }
}

// ─── Step description text ────────────────────────────────────────────────────

function stepText(doc: DocumentInfo, entityCount?: number | null): string {
    switch (doc.status) {
        case "pending":
            return "Queued for processing…";
        case "processing":
            return "Chunking & generating embeddings…";
        case "completed": {
            const chunkStr = `${doc.chunk_count ?? 0} chunk${doc.chunk_count === 1 ? "" : "s"}`;
            const entityStr = entityCount != null ? ` · ${entityCount} entit${entityCount === 1 ? "y" : "ies"}` : "";
            return `Ready — ${chunkStr}${entityStr} indexed`;
        }
        case "failed":
            return doc.error_msg ? `Failed: ${doc.error_msg}` : "Processing failed";
        default:
            return "";
    }
}

// ─── Active upload row (Zustand-driven, no SSE) ───────────────────────────────

interface UploadRowProps {
    doc: DocumentInfo;
    onUpdate: (doc: DocumentInfo) => void;
}

function UploadRow({ doc, onUpdate }: UploadRowProps) {
    const onUpdateRef = useRef(onUpdate);
    useEffect(() => {
        onUpdateRef.current = onUpdate;
    });

    // Subscribe to live processing state from Zustand store
    const processingState = useDocumentStore(
        useCallback((s) => s.docs[doc.id], [doc.id])
    );

    // Derive live status: Zustand is the source of truth while processing
    const liveStatus: DocumentInfo["status"] =
        processingState?.status ?? doc.status;

    // When processing reaches a terminal state, fetch the final PGlite record
    const prevStatusRef = useRef(liveStatus);
    useEffect(() => {
        const prev = prevStatusRef.current;
        prevStatusRef.current = liveStatus;

        if (
            (liveStatus === "completed" || liveStatus === "failed") &&
            prev !== liveStatus
        ) {
            documentsApi
                .getDocument(doc.id)
                .then(onUpdateRef.current)
                .catch(() => {
                    // Fallback: synthesize the doc from store state
                    onUpdateRef.current({
                        ...doc,
                        status: liveStatus,
                        chunk_count: processingState?.chunkCount ?? null,
                        error_msg: processingState?.errorMsg ?? null,
                    });
                });
        }
    }, [liveStatus, doc, processingState]);

    const isActive = liveStatus === "pending" || liveStatus === "processing";
    const overallPct = processingState?.overallPct ?? (liveStatus === "completed" ? 100 : 0);
    const graphPct = processingState?.graphPct ?? (liveStatus === "completed" ? 100 : 0);
    const graphPhase = processingState?.graphPhase;
    const entityCount = processingState?.entityCount;
    const graphErrorMsg = processingState?.graphErrorMsg;

    // Embedding phase label
    const phaseLabel = processingState?.phase
        ? `Embedding… (${overallPct}%)`
        : stepText({ ...doc, status: liveStatus }, entityCount);

    // Graph phase label
    const graphLabel = graphPhase === "graph-extracting"
        ? `Extracting entities… (${graphPct}%)`
        : graphPhase === "graph-building"
        ? `Building graph… (${graphPct}%)`
        : null;

    const showGraphBar = graphPhase != null;
    const showGraphComplete = liveStatus === "completed" && entityCount != null && entityCount > 0 && !graphErrorMsg;

    return (
        <div
            className={`flex items-start gap-3 rounded-lg border px-4 py-3 text-sm transition-colors ${isActive ? "bg-muted/40" : ""
                }`}
        >
            <FileTextIcon className="mt-0.5 h-4 w-4 shrink-0 text-muted-foreground" />
            <div className="min-w-0 flex-1 space-y-1">
                <div className="flex items-center gap-2">
                    <span className="truncate font-medium">{doc.original_name}</span>
                    <StatusBadge status={liveStatus} />
                </div>
                <p
                    className={`text-xs ${liveStatus === "failed" ? "text-destructive" : "text-muted-foreground"
                        }`}
                >
                    {phaseLabel}
                </p>

                {/* Embedding progress bar */}
                {isActive && processingState?.phase === "embedding" && (
                    <Progress value={overallPct} className="h-1" />
                )}
                {isActive && processingState?.phase && processingState.phase !== "embedding" && (
                    <Progress value={overallPct} className="h-1" />
                )}
                {isActive && !processingState?.phase && (
                    <Progress value={overallPct} className="h-1" />
                )}

                {/* Knowledge graph progress bar — shown while KG pipeline is running */}
                {showGraphBar && graphLabel && (
                    <div className="space-y-0.5">
                        <p className="text-xs text-indigo-500 dark:text-indigo-400">{graphLabel}</p>
                        <Progress value={graphPct} className="h-1 [&>div]:bg-indigo-500" />
                    </div>
                )}

                {/* Graph completion summary */}
                {showGraphComplete && (
                    <p className="text-xs text-indigo-500 dark:text-indigo-400">
                        Knowledge Graph: {entityCount} entit{entityCount === 1 ? "y" : "ies"} indexed
                    </p>
                )}

                {/* Graph error warning — non-fatal, document still usable */}
                {graphErrorMsg && liveStatus !== "failed" && (
                    <p className="text-xs text-amber-600 dark:text-amber-400 truncate" title={graphErrorMsg}>
                        Knowledge Graph incomplete — {graphErrorMsg.slice(0, 80)}
                    </p>
                )}
            </div>
        </div>
    );
}

// ─── Upload tab ───────────────────────────────────────────────────────────────

interface UploadTabProps {
    onDocumentReady: (doc: DocumentInfo) => void;
}

function UploadTab({ onDocumentReady }: UploadTabProps) {
    const [uploads, setUploads] = useState<DocumentInfo[]>([]);
    const [isDragOver, setIsDragOver] = useState(false);
    const [isUploading, setIsUploading] = useState(false);
    const inputRef = useRef<HTMLInputElement>(null);

    const activeCount = useDocumentStore((s) => s.activeCount);
    const atCapacity = activeCount >= 5;

    const handleUpdate = useCallback(
        (updated: DocumentInfo) => {
            setUploads((prev) =>
                prev.map((d) => (d.id === updated.id ? updated : d))
            );
            if (updated.status === "completed") {
                onDocumentReady(updated);
            }
        },
        [onDocumentReady]
    );

    const uploadFiles = async (files: File[]) => {
        if (!files.length) return;
        setIsUploading(true);

        for (const file of files) {
            // Check capacity before each file
            const currentActive = useDocumentStore.getState().activeCount;
            if (currentActive >= 5) {
                toast.warning(
                    `Processing queue is full (5/5 slots in use). "${file.name}" was skipped. Wait for a slot to free up.`
                );
                continue;
            }

            try {
                const doc = await documentsApi.uploadDocument(file);
                setUploads((prev) => [doc, ...prev]);
                toast.success(`"${file.name}" uploaded — processing started`);
            } catch (err: unknown) {
                toast.error((err as Error).message || `Failed to upload ${file.name}`);
            }
        }

        setIsUploading(false);
        if (inputRef.current) inputRef.current.value = "";
    };

    const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
        const files = Array.from(e.target.files ?? []);
        uploadFiles(files);
    };

    const handleDrop = (e: React.DragEvent) => {
        e.preventDefault();
        setIsDragOver(false);
        if (atCapacity) {
            toast.warning("Processing queue is full (5/5). Wait for documents to finish before uploading more.");
            return;
        }
        const files = Array.from(e.dataTransfer.files);
        uploadFiles(files);
    };

    return (
        <div className="space-y-6">
            {/* Drop zone */}
            <label
                className={`flex cursor-pointer flex-col items-center justify-center gap-3 rounded-xl border-2 border-dashed px-6 py-12 text-center transition-colors ${atCapacity
                    ? "cursor-not-allowed border-muted-foreground/15 opacity-50"
                    : isDragOver
                        ? "border-primary bg-primary/5"
                        : "border-muted-foreground/25 hover:border-primary/50 hover:bg-muted/30"
                    }`}
                onDragOver={(e) => {
                    e.preventDefault();
                    if (!atCapacity) setIsDragOver(true);
                }}
                onDragLeave={() => setIsDragOver(false)}
                onDrop={handleDrop}
            >
                <UploadCloudIcon className="h-10 w-10 text-muted-foreground" />
                <div className="space-y-1">
                    <p className="font-medium">
                        {atCapacity
                            ? "Queue full — wait for a slot to free up"
                            : isDragOver
                                ? "Drop files here"
                                : "Drag & drop files or click to browse"}
                    </p>
                    <p className="text-xs text-muted-foreground">
                        PDF, TXT, MD — up to 25 MB each
                    </p>
                    {activeCount > 0 && (
                        <p className="text-xs font-medium text-amber-600 dark:text-amber-400">
                            {activeCount}/5 processing slots in use
                        </p>
                    )}
                </div>
                <input
                    ref={inputRef}
                    type="file"
                    accept=".pdf,.txt,.md"
                    multiple
                    className="sr-only"
                    onChange={handleFileChange}
                    disabled={atCapacity}
                />
            </label>

            <Button
                className="w-full"
                onClick={() => inputRef.current?.click()}
                disabled={isUploading || atCapacity}
            >
                {isUploading ? (
                    <RefreshCcwIcon className="mr-2 h-4 w-4 animate-spin" />
                ) : (
                    <UploadCloudIcon className="mr-2 h-4 w-4" />
                )}
                {isUploading
                    ? "Uploading…"
                    : atCapacity
                        ? "Queue Full (5/5)"
                        : "Upload Files"}
            </Button>

            {/* Active uploads this session */}
            {uploads.length > 0 && (
                <div className="space-y-2">
                    <h3 className="text-sm font-medium text-muted-foreground">
                        This session
                    </h3>
                    <div className="space-y-2">
                        {uploads.map((doc) => (
                            <UploadRow key={doc.id} doc={doc} onUpdate={handleUpdate} />
                        ))}
                    </div>
                </div>
            )}
        </div>
    );
}

// ─── Document Collection tab ───────────────────────────────────────────────────────

function DocumentCollectionTab() {
    const [docs, setDocs] = useState<DocumentInfo[]>([]);
    const [loading, setLoading] = useState(true);
    const [backendError, setBackendError] = useState<string | null>(null);
    const [deleteTarget, setDeleteTarget] = useState<DocumentInfo | null>(null);
    const [isDeleting, setIsDeleting] = useState(false);

    const fetchDocs = useCallback(async () => {
        try {
            setLoading(true);
            setBackendError(null);
            const data = await documentsApi.listDocuments();
            setDocs(data);
        } catch (err: unknown) {
            const msg = (err as Error).message || "Failed to load documents";
            setBackendError(msg);
            toast.error(msg);
        } finally {
            setLoading(false);
        }
    }, []);

    // On first mount: reconcile any interrupted docs then load the list
    useEffect(() => {
        (async () => {
            await reconcileInterruptedDocuments();
            await fetchDocs();
        })();
        // eslint-disable-next-line react-hooks/exhaustive-deps
    }, []);

    const handleDelete = async () => {
        if (!deleteTarget) return;
        try {
            setIsDeleting(true);
            await documentsApi.deleteDocument(deleteTarget.id);
            setDocs((prev) => prev.filter((d) => d.id !== deleteTarget.id));
            toast.success(
                `"${deleteTarget.original_name}" removed from Document Collection`
            );
            setDeleteTarget(null);
        } catch (err: unknown) {
            toast.error((err as Error).message || "Failed to delete document");
        } finally {
            setIsDeleting(false);
        }
    };

    const formatDate = (iso: string) =>
        new Date(iso).toLocaleDateString(undefined, {
            year: "numeric",
            month: "short",
            day: "numeric",
        });

    return (
        <div className="space-y-4">
            <div className="flex items-center justify-between">
                <p className="text-sm text-muted-foreground">
                    {docs.length} document{docs.length !== 1 ? "s" : ""} in Document Collection
                </p>
                <Button
                    variant="outline"
                    size="sm"
                    onClick={fetchDocs}
                    disabled={loading}
                >
                    <RefreshCcwIcon
                        className={`mr-2 h-4 w-4 ${loading ? "animate-spin" : ""}`}
                    />
                    Refresh
                </Button>
            </div>

            {backendError && (
                <div className="flex items-center gap-3 rounded-lg border border-destructive/50 bg-destructive/10 px-4 py-3 text-sm text-destructive">
                    <AlertCircleIcon className="h-4 w-4 shrink-0" />
                    <span>Failed to load Document Collection: {backendError}</span>
                </div>
            )}

            {loading ? (
                <div className="space-y-2">
                    {[1, 2, 3].map((i) => (
                        <div key={i} className="h-12 animate-pulse rounded-lg bg-muted" />
                    ))}
                </div>
            ) : docs.length === 0 ? (
                <div className="flex flex-col items-center justify-center gap-3 rounded-xl border-2 border-dashed border-muted-foreground/20 py-16 text-center">
                    <DatabaseIcon className="h-10 w-10 text-muted-foreground/40" />
                    <div className="space-y-1">
                        <p className="font-medium text-muted-foreground">
                            No documents yet
                        </p>
                        <p className="text-xs text-muted-foreground">
                            Upload files in the Upload tab to populate the Document Collection.
                        </p>
                    </div>
                </div>
            ) : (
                <div className="rounded-lg border">
                    <Table>
                        <TableHeader>
                            <TableRow>
                                <TableHead>Name</TableHead>
                                <TableHead>Status</TableHead>
                                <TableHead className="text-right">Chunks</TableHead>
                                <TableHead>Uploaded</TableHead>
                                <TableHead className="w-16" />
                            </TableRow>
                        </TableHeader>
                        <TableBody>
                            {docs.map((doc) => (
                                <TableRow key={doc.id}>
                                    <TableCell className="max-w-[240px]">
                                        <div className="flex items-center gap-2 min-w-0">
                                            <FileTextIcon className="h-4 w-4 shrink-0 text-muted-foreground" />
                                            <span className="truncate text-sm font-medium">
                                                {doc.original_name}
                                            </span>
                                        </div>
                                    </TableCell>
                                    <TableCell>
                                        <StatusBadge status={doc.status} />
                                    </TableCell>
                                    <TableCell className="text-right text-sm tabular-nums">
                                        {doc.chunk_count ?? "—"}
                                    </TableCell>
                                    <TableCell className="text-sm text-muted-foreground">
                                        {formatDate(doc.created_at)}
                                    </TableCell>
                                    <TableCell>
                                        <Button
                                            variant="ghost"
                                            size="icon"
                                            className="h-8 w-8 text-destructive hover:text-destructive hover:bg-destructive/10"
                                            onClick={() => setDeleteTarget(doc)}
                                        >
                                            <Trash2Icon className="h-4 w-4" />
                                        </Button>
                                    </TableCell>
                                </TableRow>
                            ))}
                        </TableBody>
                    </Table>
                </div>
            )}

            {/* Delete confirmation */}
            <Dialog
                open={!!deleteTarget}
                onOpenChange={(open) => !open && setDeleteTarget(null)}
            >
                <DialogContent>
                    <DialogHeader>
                        <DialogTitle>Remove document?</DialogTitle>
                        <DialogDescription>
                            This will permanently remove{" "}
                            <span className="font-medium">{deleteTarget?.original_name}</span>{" "}
                            and all its indexed chunks from the Document Collection. The original
                            file on disk is kept for audit purposes.
                        </DialogDescription>
                    </DialogHeader>
                    <DialogFooter>
                        <Button
                            variant="outline"
                            onClick={() => setDeleteTarget(null)}
                            disabled={isDeleting}
                        >
                            Cancel
                        </Button>
                        <Button
                            variant="destructive"
                            onClick={handleDelete}
                            disabled={isDeleting}
                        >
                            {isDeleting ? (
                                <RefreshCcwIcon className="mr-2 h-4 w-4 animate-spin" />
                            ) : (
                                <Trash2Icon className="mr-2 h-4 w-4" />
                            )}
                            Remove
                        </Button>
                    </DialogFooter>
                </DialogContent>
            </Dialog>
        </div>
    );
}

// ─── Root view ────────────────────────────────────────────────────────────────

export function DocumentsView() {
    const activeCount = useDocumentStore((s) => s.activeCount);

    const handleDocumentReady = useCallback((doc: DocumentInfo) => {
        toast.success(
            `"${doc.original_name}" is ready — ${doc.chunk_count} chunks indexed`
        );
    }, []);

    // Warn user before tab close / refresh while processing is active
    useEffect(() => {
        if (activeCount === 0) return;

        const handleBeforeUnload = (e: BeforeUnloadEvent) => {
            // Modern browsers show a generic dialog; preventDefault triggers it
            e.preventDefault();
        };

        window.addEventListener("beforeunload", handleBeforeUnload);
        return () => window.removeEventListener("beforeunload", handleBeforeUnload);
    }, [activeCount]);

    return (
        <div className="flex flex-col gap-6 p-6">
            <div>
                <h1 className="text-3xl font-bold tracking-tight">Document Collection</h1>
                <p className="text-muted-foreground">
                    Upload documents for RAG retrieval and manage the Document Collection.
                </p>
            </div>

            {/* Processing alert banner — persists across tab navigation */}
            {activeCount > 0 && (
                <Alert className="border-amber-500/50 bg-amber-500/10 text-amber-600 dark:border-amber-500/40 dark:bg-amber-500/10 dark:text-amber-400">
                    <AlertCircleIcon className="h-4 w-4 !text-amber-600 dark:!text-amber-400" />
                    <AlertTitle>Processing in Progress</AlertTitle>
                    <AlertDescription>
                        {activeCount} document{activeCount !== 1 ? "s are" : " is"} being
                        processed. Please do not close or refresh this tab — it will
                        interrupt the pipeline. Navigation within the app is fine.
                    </AlertDescription>
                </Alert>
            )}

            <Tabs defaultValue="knowledge-base" className="w-full">
                <TabsList className="grid w-full max-w-sm grid-cols-2">
                    <TabsTrigger value="knowledge-base">Document Collection</TabsTrigger>
                    <TabsTrigger value="upload">Upload</TabsTrigger>
                </TabsList>
                <TabsContent value="knowledge-base" className="mt-6">
                    <DocumentCollectionTab />
                </TabsContent>

                <TabsContent value="upload" className="mt-6">
                    <UploadTab onDocumentReady={handleDocumentReady} />
                </TabsContent>
            </Tabs>
        </div>
    );
}
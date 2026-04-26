"use client";

/**
 * chat-interface.tsx
 *
 * Top-level chat UI with a model-readiness gate.
 *
 * COMPONENT TREE
 * --------------
 *  ChatInterface          ← default export; guards against missing model
 *    ├─ ModelLoadingState ← spinner while LlmInference initialises
 *    ├─ ModelUnavailableState ← CTA when no model is downloaded
 *    └─ ChatSession       ← full chat UI, only mounted when model is ready
 *
 * WHY THE SPLIT?
 * --------------
 * `useChat` and the `MediaPipeChatTransport` are only instantiated inside
 * `ChatSession`. Because `ChatSession` is not rendered until the
 * `LlmInference` instance exists, the transport is guaranteed to always
 * receive a valid instance — no null-checks needed at call sites.
 */

import {
    Attachment,
    AttachmentInfo,
    AttachmentPreview,
    AttachmentRemove,
    Attachments,
    type AttachmentData,
} from "@/components/ai-elements/attachments";
import {
    Conversation,
    ConversationContent,
    ConversationScrollButton,
} from "@/components/ai-elements/conversation";
import {
    Message,
    MessageAction,
    MessageActions,
    MessageBranch,
    MessageBranchContent,
    MessageContent,
    MessageResponse,
    MessageToolbar,
} from "@/components/ai-elements/message";
import {
    Reasoning,
    ReasoningContent,
    ReasoningTrigger,
} from "@/components/ai-elements/reasoning";
import type { PromptInputMessage } from "@/components/ai-elements/prompt-input";
import {
    PromptInput,
    /* PromptInputActionAddAttachments,
    PromptInputActionMenu,
    PromptInputActionMenuContent,
    PromptInputActionMenuTrigger, */
    PromptInputBody,
    PromptInputButton,
    PromptInputFooter,
    PromptInputHeader,
    PromptInputSubmit,
    PromptInputTextarea,
    PromptInputTools,
    usePromptInputAttachments,
} from "@/components/ai-elements/prompt-input";
import { SpeechInput } from "@/components/ai-elements/speech-input";
import { Suggestion, Suggestions } from "@/components/ai-elements/suggestion";
import { Button } from "@/components/ui/button";
import { Spinner } from "@/components/ui/spinner";
import { MODELS } from "@/const/models";
import { MediaPipeChatTransport } from "@/lib/buddhi-ai-core/chat-api";
import type { GemmaTemplateVersion } from "@/types/messages";
import {
    createNewChat,
    generateChatTitle,
    loadChat,
    serializeMessagesForStorage,
    updateExistingChat,
} from "@/lib/chat-manager";
import { useLiteRTModelStore } from "@/stores/litert-store";
import { useChatStore } from "@/stores/chat-store";
import { useMemoryStore } from "@/stores/memory-store";
import {
    countTokensForMessages,
    extractBuddhiMessages,
    MAX_CONTEXT_TOKENS,
    runSummarization,
    SUMMARIZATION_THRESHOLD,
} from "@/lib/memory";
import {
    Context,
    ContextContent,
    ContextContentHeader,
    ContextTrigger,
} from "@/components/ai-elements/context";
import { SYSTEM_PROMPT } from "@/const/system-prompt";
import { useChat } from "@ai-sdk/react";
import type { LlmInference } from "@mediapipe/tasks-genai";
import type { FileUIPart } from "ai";
import {
    buildRagContextBlock,
    retrieveHybridContext,
    toSourceItems,
    type RagSourceItem,
} from "@/lib/rag";
import {
    Source,
    Sources,
    SourcesContent,
    SourcesTrigger,
} from "@/components/ai-elements/sources";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import {
    Brain,
    BrainCircuitIcon,
    CheckIcon,
    CopyIcon,
    PencilIcon,
    RefreshCcwIcon,
    TriangleAlert,
    XIcon,
} from "lucide-react";
import Link from "next/link";
import { useParams } from "next/navigation";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { toast } from "sonner";
import { Shimmer } from "../ai-elements/shimmer";

// ---------------------------------------------------------------------------
// Static data
// ---------------------------------------------------------------------------

const suggestions = [
    "What are the latest trends in AI?",
    "How does machine learning work?",
    "Explain quantum computing",
    "Best practices for React development",
    "Tell me about TypeScript benefits",
    "How to optimize database queries?",
    "What is the difference between SQL and NoSQL?",
    "Explain cloud computing basics",
];

// ---------------------------------------------------------------------------
// Gate states
// ---------------------------------------------------------------------------

/**
 * Shown while `useModelEngine` is initialising the LlmInference instance
 * (i.e. `liteRTModelStatus` is `'idle'` or `'loading'`).
 */
function ModelLoadingState() {
    return (
        <div className="flex h-[calc(100vh-80px)] flex-col items-center justify-center gap-4 text-center">
            <Spinner className="size-8" />
            <p className="text-muted-foreground text-sm">Loading AI model…</p>
        </div>
    );
}

/**
 * Shown when the store is hydrated but no completed language model was found,
 * OR when LlmInference initialisation failed.
 *
 * Gives the user a clear path to the Model Manager so they can download one.
 */
function ModelUnavailableState({ isError }: { isError: boolean }) {
    return (
        <div className="flex h-[calc(100vh-80px)] flex-col items-center justify-center gap-6 px-6 text-center">
            <div className="flex flex-col items-center gap-3">
                <BrainCircuitIcon className="text-muted-foreground size-12" />
                <h2 className="text-lg font-semibold">
                    {isError ? "Model failed to load" : "No AI model available"}
                </h2>
                <p className="text-muted-foreground max-w-sm text-sm">
                    {isError
                        ? "The language model could not be initialised. Try reloading the page. If the problem persists, re-download the model."
                        : "Download a language model to start chatting. All inference runs locally — your data never leaves your device."}
                </p>
            </div>
            <Button asChild>
                <Link href="/models">
                    <BrainCircuitIcon className="mr-2 size-4" />
                    {isError ? "Manage Models" : "Download a Model"}
                </Link>
            </Button>
        </div>
    );
}

// ---------------------------------------------------------------------------
// Sub-components (shared between ChatInterface and ChatSession)
// ---------------------------------------------------------------------------

const AttachmentItem = ({
    attachment,
    onRemove,
}: {
    attachment: FileUIPart & { id: string };
    onRemove: (id: string) => void;
}) => {
    const handleRemove = useCallback(() => {
        onRemove(attachment.id);
    }, [onRemove, attachment.id]);

    return (
        <Attachment data={attachment} onRemove={handleRemove}>
            <AttachmentPreview />
            <AttachmentRemove />
        </Attachment>
    );
};

const PromptInputAttachmentsDisplay = () => {
    const attachments = usePromptInputAttachments();

    const handleRemove = useCallback(
        (id: string) => {
            attachments.remove(id);
        },
        [attachments]
    );

    if (attachments.files.length === 0) return null;

    return (
        <Attachments variant="inline">
            {attachments.files.map((attachment) => (
                <AttachmentItem
                    attachment={attachment}
                    key={attachment.id}
                    onRemove={handleRemove}
                />
            ))}
        </Attachments>
    );
};

const SuggestionItem = ({
    suggestion,
    onClick,
}: {
    suggestion: string;
    onClick: (suggestion: string) => void;
}) => {
    const handleClick = useCallback(() => {
        onClick(suggestion);
    }, [onClick, suggestion]);

    return <Suggestion onClick={handleClick} suggestion={suggestion} />;
};

// ---------------------------------------------------------------------------
// ChatSession — the actual chat UI
// ---------------------------------------------------------------------------

/**
 * Mounts only when a valid `LlmInference` instance is available.
 * Creates the transport once (via useMemo) and owns the useChat state.
 * Re-mounts when `chatId` changes (enforced by `key` in ChatInterface).
 */
function ChatSession({
    instance,
    chatId,
}: {
    instance: LlmInference;
    chatId: string | null;
}) {
    const [text, setText] = useState<string>("");
    const [isReasoningOn, setIsReasoningOn] = useState<boolean>(false);

    // ── MessageActions state ──────────────────────────────────────────────────
    // `editingMessageId` — ID of the user message currently in edit mode (null = none).
    // `editText`          — Draft text while editing.
    // `copiedMessageId`   — ID of the last message whose text was just copied;
    //                       used to show a transient check-mark icon for 2 s.
    const [editingMessageId, setEditingMessageId] = useState<string | null>(null);
    const [editText, setEditText] = useState<string>("");
    const [copiedMessageId, setCopiedMessageId] = useState<string | null>(null);

    // true while we're fetching an existing chat from IndexedDB.
    // Starts true when a chatId is present so the spinner shows immediately
    // (before the async load resolves) and prevents a flash of empty messages.
    const [isLoadingChat, setIsLoadingChat] = useState(!!chatId);

    // RAG: sources retrieved for the most recent user turn.
    // Ephemeral — not persisted with chat history (sources vanish on reload).
    const [sources, setSources] = useState<RagSourceItem[]>([]);
    // true while vector retrieval is in flight; disables the submit button.
    const [isRetrieving, setIsRetrieving] = useState(false);

    // Tracks the active chat ID across renders without triggering re-renders.
    const currentChatIdRef = useRef<string | null>(chatId);

    // Tracks the previous streaming status to detect the streaming→ready transition.
    const prevStatusRef = useRef<string>("ready");

    const setCurrentChatId = useChatStore((s) => s.setCurrentChatId);
    const refreshChats = useChatStore((s) => s.refreshChats);

    // ── Memory / token state ──────────────────────────────────────────────────
    const tokenCount = useMemoryStore((s) => s.tokenCount);
    const isSummarizing = useMemoryStore((s) => s.isSummarizing);
    const isSummarized = useMemoryStore((s) => s.isSummarized);
    const setIsSummarizing = useMemoryStore((s) => s.setIsSummarizing);
    const setIsSummarized = useMemoryStore((s) => s.setIsSummarized);
    const resetMemory = useMemoryStore((s) => s.reset);

    /**
     * Runs the summarization LLM call for the given messages (UIMessage[]).
     *
     * Guards against concurrent calls via `isSummarizing` and requires a valid
     * `chatId`. The summary is stored in sessionStorage by `runSummarization`
     * and the memory store is updated accordingly.
     *
     * Defined as a plain async function (not useCallback) so it can be safely
     * called from both the chat-load effect and the streaming→ready effect
     * without stale-closure risk — both effects are inside the same render
     * cycle and both reference the same `instance`, `templateVersion`, etc.
     */
    async function triggerSummarization(uiMessages: typeof messages) {
        const chatId = currentChatIdRef.current;
        if (!chatId) {
            console.debug("[ChatSession] Skipping summarization — no chatId yet.");
            return;
        }
        if (useMemoryStore.getState().isSummarizing) {
            console.debug("[ChatSession] Summarization already in progress, skipping.");
            return;
        }

        setIsSummarizing(true);
        try {
            await runSummarization(
                instance,
                uiMessages,
                SYSTEM_PROMPT,
                chatId,
                templateVersion
            );
            setIsSummarized(true);
            // Update the transport's chatId in case it was set during load.
            transport.chatId = chatId;
        } catch (err) {
            console.error("[ChatSession] Summarization failed:", err);
            toast.error(
                "Memory summarization failed — full history will be used. " +
                "Check console for details."
            );
        } finally {
            setIsSummarizing(false);
        }
    }

    // Resolve per-model config flags so the transport is kept in sync.
    // Falls back to safe defaults when the model ID hasn't been stored yet.
    const loadedModelId = useLiteRTModelStore((s) => s.liteRTModelModel);
    const activeModel = MODELS.find((m) => m.id === loadedModelId);
    const templateVersion: GemmaTemplateVersion =
        activeModel?.chatTemplateVersion ?? "gemma4";
    const supportsVision: boolean = activeModel?.supportsVision ?? false;

    // The transport must be stable — useChat stores it once in a useRef and
    // never re-reads it after mount. Only recreate when the model instance or
    // template version changes (both are set once after model initialisation).
    const transport = useMemo(
        () => new MediaPipeChatTransport(instance, templateVersion),
        [instance, templateVersion]
    );

    // Keep transport flags in sync via mutable properties (same pattern as
    // isReasoningOn — the transport ref is stable so useEffect is correct).
    useEffect(() => {
        transport.isReasoningOn = isReasoningOn;
    }, [transport, isReasoningOn]);

    useEffect(() => {
        transport.supportsVision = supportsVision;
    }, [transport, supportsVision]);

    // Keep the transport's chatId in sync so the memory middleware can look up
    // the correct sessionStorage key when sendMessages() is called.
    useEffect(() => {
        transport.chatId = currentChatIdRef.current;
    }, [transport, chatId]);

    // ── useChat ───────────────────────────────────────────────────────────────
    // `messages`    – UIMessage[] managed by the SDK; updates reactively as
    //                 token chunks arrive from the transport stream.
    // `sendMessage` – appends a user message and calls transport.sendMessages.
    // `stop`        – fires the AbortSignal passed to transport.sendMessages.
    // `status`      – 'ready' | 'submitted' | 'streaming' | 'error'
    // `setMessages` – imperatively set the message list (used for chat restore).
    const { messages, setMessages, sendMessage, stop, status } = useChat({
        transport,
    });

    // ── Load existing chat ─────────────────────────────────────────────────────
    // Runs once on mount. `chatId` is stable for this component instance
    // because the parent applies key={chatId ?? "new"}, forcing a full
    // remount whenever the route changes.
    //
    // We call setMessages() rather than passing initialMessages to useChat
    // because useChat only reads initialMessages on first render — it ignores
    // changes to the option on re-renders. setMessages() works at any time.
    useEffect(() => {
        setCurrentChatId(chatId);

        // Reset memory state whenever the chat changes (new chat or different
        // chat). The memory store is global so stale state from a previous chat
        // must be cleared before this session begins.
        resetMemory();

        if (!chatId) return;

        loadChat(chatId)
            .then(async (chat) => {
                if (chat?.messages?.length) {
                    setMessages(chat.messages);

                    // Check whether this existing chat already exceeds the token
                    // threshold. If so, trigger summarization immediately so the
                    // next turn uses compressed context.
                    try {
                        const buddhiMsgs = extractBuddhiMessages(
                            chat.messages,
                            SYSTEM_PROMPT,
                            templateVersion
                        );
                        const count = await countTokensForMessages(
                            instance,
                            buddhiMsgs,
                            templateVersion
                        );
                        useMemoryStore.getState().setTokenCount(count);

                        if (count > SUMMARIZATION_THRESHOLD) {
                            console.debug(
                                `[ChatSession] Loaded chat "${chatId}" exceeds token threshold ` +
                                `(${count} > ${SUMMARIZATION_THRESHOLD}). Triggering summarization.`
                            );
                            await triggerSummarization(chat.messages);
                        }
                    } catch (err) {
                        console.warn(
                            "[ChatSession] Token count check failed on chat load:",
                            err
                        );
                    }
                }
            })
            .catch(() => {
                console.error("[ChatSession] Failed to load chat:", chatId);
                toast.error("Could not load chat history.");
            })
            .finally(() => setIsLoadingChat(false));

        return () => setCurrentChatId(null);
    }, []); // eslint-disable-line react-hooks/exhaustive-deps

    // Disable submit while a response is in flight, during RAG retrieval,
    // during memory summarization, or when the input is empty.
    const isSubmitDisabled =
        !text.trim() || status === "streaming" || status === "submitted" || isRetrieving || isSummarizing;

    // ── Handlers ──────────────────────────────────────────────────────────────

    const handleSubmit = useCallback(
        async (message: PromptInputMessage) => {
            if (!message.text && !message.files?.length) return;

            if (message.files?.length) {
                // Warn about file types the model cannot process.
                const videoFiles = message.files.filter((f) =>
                    (f.mediaType ?? "").startsWith("video/")
                );
                const unsupportedMime = message.files.filter((f) => {
                    const m = f.mediaType ?? "";
                    return (
                        !m.startsWith("image/") &&
                        !m.startsWith("audio/") &&
                        !m.startsWith("video/")
                    );
                });
                // Images/audio on a text-only model — the attachment shows in the
                // conversation for reference but the LLM will not analyse it.
                const visionFiles = message.files.filter((f) => {
                    const m = f.mediaType ?? "";
                    return m.startsWith("image/") || m.startsWith("audio/");
                });

                if (videoFiles.length > 0) {
                    toast.warning("Video files are not supported", {
                        description:
                            "The on-device AI model cannot process video. " +
                            "Only images and audio (on vision-capable models) are sent to the model.",
                    });
                } else if (unsupportedMime.length > 0) {
                    toast.warning("Some attachments may not be processed", {
                        description:
                            `Files of type "${unsupportedMime.map((f) => f.mediaType ?? "unknown").join(", ")}" ` +
                            "cannot be understood by the model. Only images and audio are supported.",
                    });
                } else if (!supportsVision && visionFiles.length > 0) {
                    // Text-only model: images/audio are displayed but not analysed.
                    toast.info("Image analysis not available", {
                        description:
                            "The currently loaded model does not support images or audio. " +
                            "Your message will be answered as text only. " +
                            "Load a vision-capable model variant to enable image analysis.",
                    });
                }
            }

            // Clear stale sources from the previous turn immediately.
            setSources([]);

            // ── RAG context via promise ───────────────────────────────────────
            // We set ragContextPromise on the transport BEFORE calling sendMessage
            // so the user message appears in the conversation instantly (no delay
            // while the vector store initialises or retrieves).  The transport's
            // execute callback awaits the promise, so the LLM prompt is still
            // augmented with the full RAG context — just asynchronously.
            if (message.text?.trim()) {
                let resolveRag!: (ctx: string | null) => void;
                transport.ragContextPromise = new Promise<string | null>((resolve) => {
                    resolveRag = resolve;
                });

                // Add the user message to the conversation immediately.
                sendMessage({ text: message.text || "", files: message.files });
                setText("");

                // Retrieve RAG context and resolve the promise the transport is awaiting.
                setIsRetrieving(true);
                try {
                    const segments = await retrieveHybridContext(message.text);
                    resolveRag(buildRagContextBlock(segments));
                    setSources(toSourceItems(segments));
                } catch {
                    resolveRag(null);
                } finally {
                    setIsRetrieving(false);
                }
            } else {
                // No text to embed — resolve immediately with no RAG context.
                transport.ragContextPromise = Promise.resolve(null);
                sendMessage({ text: message.text || "", files: message.files });
                setText("");
            }
        },
        [sendMessage, transport, supportsVision]
    );

    const handleSuggestionClick = useCallback(
        (suggestion: string) => {
            sendMessage({ text: suggestion });
        },
        [sendMessage]
    );

    const handleTranscriptionChange = useCallback((transcript: string) => {
        setText((prev) => (prev ? `${prev} ${transcript}` : transcript));
    }, []);

    const handleTextChange = useCallback(
        (event: React.ChangeEvent<HTMLTextAreaElement>) => {
            setText(event.target.value);
        },
        []
    );

    const toggleReasoning = useCallback(() => {
        setIsReasoningOn((prev) => !prev);
    }, []);

    // ── MessageActions handlers ───────────────────────────────────────────────

    /**
     * Copies the given text to the clipboard and briefly shows a check-mark
     * on the copy button for the given message id.
     */
    const handleCopy = useCallback((messageId: string, textToCopy: string) => {
        if (!navigator.clipboard) {
            toast.error("Clipboard is not available in this browser.");
            return;
        }
        navigator.clipboard.writeText(textToCopy).then(() => {
            setCopiedMessageId(messageId);
            // Reset the icon after 2 seconds.
            setTimeout(() => setCopiedMessageId(null), 2000);
        }).catch((err) => {
            console.error("[handleCopy] Clipboard write failed:", err);
            toast.error("Could not copy text to clipboard.");
        });
    }, []);

    /**
     * Regenerates the last assistant response.
     *
     * Strategy (transport variant has no built-in `reload()`):
     *  1. Find the last user message and its index in the array.
     *  2. Trim the messages array to everything BEFORE that user message.
     *  3. Call sendMessage() with the user text — it will re-append the user
     *     message and then invoke the transport to produce a fresh response.
     *
     * IMPORTANT: sendMessage() always prepends a brand-new user UIMessage to
     * the state before invoking the transport. The previous implementation only
     * stripped the last assistant message (keeping the existing user message),
     * so sendMessage added a second copy, duplicating the user turn. By slicing
     * to just before the last user message we give sendMessage a clean slate so
     * exactly one user message is present when the transport runs.
     */
    const handleRegenerate = useCallback(() => {
        if (messages.length === 0) {
            toast.error("No messages to regenerate from.");
            return;
        }

        // Locate the last user message index (search from the end).
        let lastUserMsgIndex = -1;
        for (let i = messages.length - 1; i >= 0; i--) {
            if (messages[i].role === "user") {
                lastUserMsgIndex = i;
                break;
            }
        }

        if (lastUserMsgIndex === -1) {
            toast.error("No user message found to regenerate from.");
            return;
        }

        const lastUserMsg = messages[lastUserMsgIndex];
        const textPart = lastUserMsg.parts.find((p) => p.type === "text");
        const userText = textPart?.type === "text" ? textPart.text : "";

        // Slice to everything BEFORE the last user message so that sendMessage()
        // can re-add it exactly once (it always appends a new user UIMessage).
        const trimmedMessages = messages.slice(0, lastUserMsgIndex);
        setMessages(trimmedMessages);

        // Ensure no stale RAG context bleeds into the regeneration.
        transport.ragContextPromise = Promise.resolve(null);
        sendMessage({ text: userText });
    }, [messages, setMessages, sendMessage, transport]);

    /** Enters edit mode for the given user message. */
    const handleEditStart = useCallback((messageId: string, currentText: string) => {
        setEditingMessageId(messageId);
        setEditText(currentText);
    }, []);

    /** Cancels edit mode without applying any changes. */
    const handleEditCancel = useCallback(() => {
        setEditingMessageId(null);
        setEditText("");
    }, []);

    /**
     * Commits the edited user message:
     *  1. Updates the message's text part in the local state.
     *  2. Drops any messages that followed the edited one (they are now stale).
     *  3. Persists the updated thread to IndexedDB.
     *  4. Re-submits the edited text so the LLM generates a fresh response.
     */
    const handleEditDone = useCallback(async (messageId: string) => {
        const trimmedEdit = editText.trim();
        if (!trimmedEdit) {
            toast.error("Message text cannot be empty.");
            return;
        }

        // Build updated messages: patch the target message, drop anything after it.
        const editedIdx = messages.findIndex((m) => m.id === messageId);
        if (editedIdx === -1) {
            console.error("[handleEditDone] Could not find message with id:", messageId);
            toast.error("Could not locate the message to edit.");
            return;
        }

        const updatedMessages = messages
            .slice(0, editedIdx + 1)
            .map((m) =>
                m.id !== messageId
                    ? m
                    : {
                        ...m,
                        parts: m.parts.map((p) =>
                            p.type === "text" ? { ...p, text: trimmedEdit } : p
                        ),
                    }
            );

        setMessages(updatedMessages);
        setEditingMessageId(null);
        setEditText("");

        // Persist the updated thread so the edit survives a page reload.
        if (currentChatIdRef.current) {
            try {
                const persistable = await serializeMessagesForStorage(updatedMessages);
                await updateExistingChat(currentChatIdRef.current, persistable);
            } catch (err) {
                console.error("[handleEditDone] Failed to persist edited message:", err);
                toast.error("The edit could not be saved to history.");
                // Non-fatal — continue to generate a response.
            }
        }

        // Generate a fresh assistant response for the edited user message.
        transport.ragContextPromise = Promise.resolve(null);
        sendMessage({ text: trimmedEdit });
    }, [editText, messages, setMessages, sendMessage, transport, currentChatIdRef]);

    // ── Persist chat on streaming→ready transition ─────────────────────────────
    // Detects when a streaming response finishes and saves the full conversation
    // to IndexedDB. For new chats, also updates the URL without a re-render.
    // After saving, checks whether the token count exceeds the summarization
    // threshold and triggers summarization if needed.
    useEffect(() => {
        const wasStreaming = prevStatusRef.current === "streaming";
        prevStatusRef.current = status;

        if (!wasStreaming || status !== "ready" || messages.length === 0) return;

        (async () => {
            try {
                // Blob object URLs are ephemeral and die with the browser tab.
                // Convert any blob: URLs in file parts to base64 data: URLs
                // before writing to IndexedDB so attachments survive page reloads.
                const persistableMessages = await serializeMessagesForStorage(messages);

                if (currentChatIdRef.current) {
                    await updateExistingChat(currentChatIdRef.current, persistableMessages);
                } else {
                    const title = generateChatTitle(persistableMessages);
                    const newId = await createNewChat(persistableMessages, title);
                    currentChatIdRef.current = newId;
                    // Update the browser URL silently — no Next.js navigation,
                    // no component re-render, no flicker.
                    window.history.replaceState(null, "", `/chat/${newId}`);
                    setCurrentChatId(newId);
                    // Sync the new chatId to the transport immediately.
                    transport.chatId = newId;
                }
                await refreshChats();
            } catch (error) {
                console.error("[ChatSession] Failed to save chat:", error);
                toast.error("Chat could not be saved.");
            }

            // ── Memory summarization check ────────────────────────────────
            // tokenCount is updated by the transport's sizeInTokens call
            // inside sendMessages, so by the time we reach this point it
            // reflects the prompt that just ran.  If it exceeds the threshold
            // and summarization hasn't already run, start it now.
            //
            // We use the store's current value (not the stale closure) to
            // avoid race conditions between consecutive turns.
            const currentTokenCount = useMemoryStore.getState().tokenCount;
            const alreadySummarized = useMemoryStore.getState().isSummarized;

            if (currentTokenCount > SUMMARIZATION_THRESHOLD && !alreadySummarized) {
                console.debug(
                    `[ChatSession] Token count ${currentTokenCount} exceeds threshold ` +
                    `${SUMMARIZATION_THRESHOLD}. Starting summarization.`
                );
                await triggerSummarization(messages);
            }
        })();
    }, [status]); // eslint-disable-line react-hooks/exhaustive-deps

    // ── Loading guard ─────────────────────────────────────────────────────────
    // Show a spinner while we fetch an existing chat from IndexedDB.
    // Prevents a flash of empty messages before the restored conversation appears.
    if (isLoadingChat) {
        return (
            <div className="flex h-[calc(100vh-80px)] items-center justify-center">
                <Spinner className="size-8" />
            </div>
        );
    }

    // ── Render ────────────────────────────────────────────────────────────────

    return (
        <div className="relative flex h-[calc(100vh-80px)] flex-col divide-y overflow-hidden">
            <Conversation>
                <ConversationContent>
                    {messages.map((message, msgIndex) => {
                        const isLastMessage = msgIndex === messages.length - 1;
                        const isStreaming = status === "streaming" || status === "submitted";

                        // Extract the final text of this message (used by copy and edit).
                        const messageText = message.parts
                            .filter((p) => p.type === "text")
                            .map((p) => (p as { type: "text"; text: string }).text)
                            .join("\n");

                        // True when this specific message is being edited.
                        const isEditing = editingMessageId === message.id;

                        return (
                            // MessageBranch handles multi-version messages (e.g. regenerations).
                            // With a single version the branch selector is hidden automatically.
                            <MessageBranch defaultBranch={0} key={message.id}>
                                <MessageBranchContent>
                                    {/*
                                 * EDIT MODE: Replace the user message bubble with an editable
                                 * textarea.  Only the last user message can be in edit mode and
                                 * only when streaming is not in progress.
                                 */}
                                    {isEditing ? (
                                        <div className="ml-auto flex w-full max-w-[95%] flex-col gap-1">
                                            <textarea
                                                aria-label="Edit message"
                                                autoFocus
                                                className="w-full resize-none rounded-lg bg-secondary px-4 py-3 text-sm text-foreground focus:outline-none focus:ring-2 focus:ring-ring"
                                                onChange={(e) => setEditText(e.target.value)}
                                                rows={Math.max(2, editText.split("\n").length)}
                                                value={editText}
                                            />
                                            <div className="flex justify-end gap-1">
                                                <MessageActions>
                                                    <MessageAction
                                                        label="Cancel edit"
                                                        onClick={handleEditCancel}
                                                        tooltip="Cancel"
                                                    >
                                                        <XIcon size={12} />
                                                    </MessageAction>
                                                    <MessageAction
                                                        disabled={!editText.trim()}
                                                        label="Send edited message"
                                                        onClick={() => handleEditDone(message.id)}
                                                        tooltip="Done"
                                                        variant="default"
                                                    >
                                                        <CheckIcon size={12} />
                                                    </MessageAction>
                                                </MessageActions>
                                            </div>
                                        </div>
                                    ) : (
                                        <Message from={message.role}>
                                            <MessageContent>
                                                {/*
                                         * UIMessage.parts is a discriminated union. We render
                                         * text blocks here; other part types (tool-call, file,
                                         * reasoning) can be added as the transport evolves.
                                         */}
                                                {message.parts.map((part, partIndex) => {
                                                    if (part.type === "reasoning") {
                                                        const isThisMessageStreaming =
                                                            status === "streaming" &&
                                                            message.id === messages[messages.length - 1]?.id;
                                                        return (
                                                            <Reasoning key={partIndex} isStreaming={isThisMessageStreaming}>
                                                                <ReasoningTrigger />
                                                                <ReasoningContent>{part.text}</ReasoningContent>
                                                            </Reasoning>
                                                        );
                                                    }
                                                    if (part.type === "text") {
                                                        return (
                                                            <MessageResponse key={partIndex}>
                                                                {part.text}
                                                            </MessageResponse>
                                                        );
                                                    }
                                                    if (part.type === "file") {
                                                        // Render the file attachment inline inside the
                                                        // message bubble.  A synthetic `id` is built from
                                                        // the message id + part index because persisted
                                                        // UIMessage file parts carry no id of their own.
                                                        const filePart = part as FileUIPart;
                                                        const attachmentData: AttachmentData = {
                                                            ...filePart,
                                                            id: `${message.id}-${partIndex}`,
                                                        };
                                                        return (
                                                            <Attachments key={partIndex} variant="inline">
                                                                <Attachment data={attachmentData}>
                                                                    <AttachmentPreview />
                                                                    <AttachmentInfo />
                                                                </Attachment>
                                                            </Attachments>
                                                        );
                                                    }
                                                    return null;
                                                })}
                                            </MessageContent>

                                            {/*
                                     * Show sources below the last assistant message only.
                                     * Sources are ephemeral — retrieved before each turn
                                     * and cleared on the next submission. They are not
                                     * persisted with chat history.
                                     */}
                                            {message.role === "assistant" &&
                                                isLastMessage &&
                                                sources.length > 0 && (
                                                    <Sources>
                                                        <SourcesTrigger count={sources.length} />
                                                        <SourcesContent>
                                                            {sources.map((source) => (
                                                                // Local files have no URL — Source renders
                                                                // as a non-navigating item (BookIcon + name).
                                                                <Source
                                                                    key={source.documentId}
                                                                    title={source.fileName}
                                                                />
                                                            ))}
                                                        </SourcesContent>
                                                    </Sources>
                                                )}
                                        </Message>
                                    )}
                                </MessageBranchContent>

                                {/*
                                 * ── MessageActions ────────────────────────────────────────────
                                 * Placed OUTSIDE MessageBranchContent (sibling, not child) to
                                 * avoid the duplicate null-key error.  MessageBranchContent keys
                                 * every direct child by `branch.key`; two siblings with key=null
                                 * cause React to drop one.  As a sibling of MessageBranchContent
                                 * inside MessageBranch's grid, the toolbar renders correctly
                                 * without interfering with branch selection.
                                 *
                                 * • Last message is ASSISTANT → Copy + Regenerate
                                 * • Last message is USER      → Regenerate + Edit
                                 *   (arises when the LLM failed or the user just sent a message)
                                 */}
                                {isLastMessage && !isStreaming && !isEditing && (
                                    <MessageToolbar>
                                        <MessageActions>
                                            {message.role === "assistant" && (
                                                <>
                                                    <MessageAction
                                                        label="Copy response"
                                                        onClick={() =>
                                                            handleCopy(message.id, messageText)
                                                        }
                                                        tooltip="Copy"
                                                    >
                                                        {copiedMessageId === message.id ? (
                                                            <CheckIcon size={12} />
                                                        ) : (
                                                            <CopyIcon size={12} />
                                                        )}
                                                    </MessageAction>
                                                    <MessageAction
                                                        label="Regenerate response"
                                                        onClick={handleRegenerate}
                                                        tooltip="Regenerate"
                                                    >
                                                        <RefreshCcwIcon size={12} />
                                                    </MessageAction>
                                                </>
                                            )}

                                            {message.role === "user" && (
                                                <>
                                                    <MessageAction
                                                        label="Regenerate response"
                                                        onClick={handleRegenerate}
                                                        tooltip="Regenerate"
                                                    >
                                                        <RefreshCcwIcon size={12} />
                                                    </MessageAction>
                                                    <MessageAction
                                                        label="Edit message"
                                                        onClick={() =>
                                                            handleEditStart(message.id, messageText)
                                                        }
                                                        tooltip="Edit"
                                                    >
                                                        <PencilIcon size={12} />
                                                    </MessageAction>
                                                </>
                                            )}
                                        </MessageActions>
                                    </MessageToolbar>
                                )}
                            </MessageBranch>
                        );
                    })}
                    {(status === "submitted" || status === "streaming") && (
                        <Message from="assistant">
                            <MessageContent>
                                <Shimmer className="text-sm" duration={1.5}>
                                    {status === "submitted" ? "Thinking..." : "Typing..."}
                                </Shimmer>
                            </MessageContent>
                        </Message>
                    )}

                    {isSummarizing && status === "ready" && (
                        <Message from="assistant">
                            <MessageContent>
                                <Shimmer className="text-sm" duration={2}>
                                    Summarizing conversation memory...
                                </Shimmer>
                            </MessageContent>
                        </Message>
                    )}

                    {status === "error" && (
                        <div className="px-4 py-2">
                            <Alert variant="destructive" className="flex items-start gap-3">
                                <TriangleAlert className="mt-0.5 shrink-0" />
                                <div className="flex-1">
                                    <AlertTitle>Response failed</AlertTitle>
                                    <AlertDescription>
                                        The AI model could not generate a response. This may be a
                                        temporary issue — please try again.
                                    </AlertDescription>
                                </div>
                                <Button
                                    className="shrink-0 self-center"
                                    size="sm"
                                    variant="outline"
                                    onClick={() => {
                                        // Re-submit the last user message so the user
                                        // can recover without reloading the page.
                                        const lastUserMsg = [...messages]
                                            .reverse()
                                            .find((m) => m.role === "user");
                                        if (lastUserMsg) {
                                            const textPart = lastUserMsg.parts.find(
                                                (p) => p.type === "text"
                                            );
                                            sendMessage({
                                                text:
                                                    textPart && textPart.type === "text"
                                                        ? textPart.text
                                                        : "",
                                            });
                                        }
                                    }}
                                >
                                    Retry
                                </Button>
                            </Alert>
                        </div>
                    )}
                </ConversationContent>
                <ConversationScrollButton />
            </Conversation>

            <div className="grid shrink-0 gap-3 pt-4">
                {/* Suggestions disappear once the conversation has started */}
                {/* {messages.length === 0 && (
                    <Suggestions className="px-4">
                        {suggestions.map((suggestion) => (
                            <SuggestionItem
                                key={suggestion}
                                onClick={handleSuggestionClick}
                                suggestion={suggestion}
                            />
                        ))}
                    </Suggestions>
                )} */}

                <div className="w-full px-4 pb-4">
                    <PromptInput globalDrop multiple onSubmit={handleSubmit}>
                        <PromptInputHeader>
                            <PromptInputAttachmentsDisplay />
                        </PromptInputHeader>
                        <PromptInputBody>
                            <PromptInputTextarea
                                onChange={handleTextChange}
                                value={text}
                            />
                        </PromptInputBody>
                        <PromptInputFooter>
                            <PromptInputTools>
                                {/* Attachment button disabled — gemma-4-E2B-it-web.task does not
                                    bundle a vision encoder for web/WebGPU. Re-enable (and set
                                    supportsVision: true in models.ts) once a vision-capable
                                    .task file is available.
                                <PromptInputActionMenu>
                                    <PromptInputActionMenuTrigger />
                                    <PromptInputActionMenuContent>
                                        <PromptInputActionAddAttachments />
                                    </PromptInputActionMenuContent>
                                </PromptInputActionMenu>
                                */}
                                <SpeechInput
                                    className="shrink-0"
                                    onTranscriptionChange={handleTranscriptionChange}
                                    size="icon-sm"
                                    variant="ghost"
                                />
                                <PromptInputButton
                                    onClick={toggleReasoning}
                                    variant={isReasoningOn ? "default" : "ghost"}
                                >
                                    <Brain size={16} />
                                    <span>Reasoning</span>
                                </PromptInputButton>
                            </PromptInputTools>

                            <div className="flex items-center gap-1">
                                {/*
                                 * Token usage indicator — shows context window utilisation
                                 * as a circular progress ring.  Only rendered once we have
                                 * a non-zero token count (i.e. after the first message).
                                 * Hovering reveals the exact used / max token counts.
                                 */}
                                {tokenCount > 0 && (
                                    <Context
                                        usedTokens={tokenCount}
                                        maxTokens={MAX_CONTEXT_TOKENS}
                                    >
                                        <ContextTrigger size="sm" />
                                        <ContextContent>
                                            <ContextContentHeader />
                                        </ContextContent>
                                    </Context>
                                )}

                                {/*
                                 * status – passed straight from useChat; PromptInputSubmit
                                 *          shows a spinner during 'submitted' and a stop icon
                                 *          during 'streaming'.
                                 * onStop  – calls useChat's stop(), which fires the AbortSignal
                                 *           passed to MediaPipeChatTransport.sendMessages().
                                 */}
                                <PromptInputSubmit
                                    disabled={isSubmitDisabled}
                                    onStop={stop}
                                    status={status}
                                />
                            </div>
                        </PromptInputFooter>
                    </PromptInput>
                </div>
                <span className="text-xs text-muted-foreground text-center">BuddiAI can make mistakes, so double-check the output.</span>
            </div>
        </div>
    );
}

// ---------------------------------------------------------------------------
// ChatInterface — model gate (exported)
// ---------------------------------------------------------------------------

/**
 * The top-level chat component. Calls `useModelEngine` to trigger LlmInference
 * initialisation, then guards rendering based on `liteRTModelStatus`:
 *
 *  idle / loading  → spinner
 *  error           → "model failed to load" + manage button
 *  ready (no inst) → "no model available" + download button  (should not happen)
 *  ready           → <ChatSession instance={…} />
 */
export function ChatInterface() {
    const instance = useLiteRTModelStore((s) => s.liteRTModelInstance);
    const modelStatus = useLiteRTModelStore((s) => s.liteRTModelStatus);

    // Read the optional [[...chatId]] route segment.
    const params = useParams<{ chatId?: string[] }>();
    const chatId = params.chatId?.[0] ?? null;

    // Still initialising (store not yet hydrated, or loading from WASM)
    if (!modelStatus || modelStatus === "idle" || modelStatus === "loading") {
        return <ModelLoadingState />;
    }

    // Initialisation failed — no completed model found, or WASM threw
    if (modelStatus === "error") {
        return <ModelUnavailableState isError />;
    }

    // Edge case: status is 'ready' but instance is missing (should not happen)
    if (!instance) {
        return <ModelUnavailableState isError={false} />;
    }

    // key={chatId ?? "new"} forces a full remount when navigating between chats,
    // ensuring each ChatSession starts with a clean state and loads its own data.
    return <ChatSession instance={instance} chatId={chatId} key={chatId ?? "new"} />;
}

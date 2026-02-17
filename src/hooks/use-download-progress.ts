"use client";

import { useEffect, useRef, useState, useCallback } from "react";
import { API_BASE } from "@/lib/constants";
import type { DownloadProgress, SSEEventType } from "@/types/models";

interface UseDownloadProgressOptions {
  onComplete?: (progress: DownloadProgress) => void;
  onFailed?: (progress: DownloadProgress) => void;
  onCancelled?: (progress: DownloadProgress) => void;
}

/**
 * Subscribe to real-time download progress via Server-Sent Events.
 *
 * Opens an EventSource connection to the SSE proxy endpoint and
 * updates state on each event. Automatically closes on terminal states.
 *
 * @param downloadId - The download to track, or null to disable.
 * @param options - Callbacks for terminal events.
 */
export function useDownloadProgress(
  downloadId: string | null,
  options?: UseDownloadProgressOptions
) {
  const [progress, setProgress] = useState<DownloadProgress | null>(null);
  const eventSourceRef = useRef<EventSource | null>(null);
  // Store options in a ref so the EventSource listeners don't trigger re-creation
  const optionsRef = useRef(options);
  optionsRef.current = options;

  const cleanup = useCallback(() => {
    if (eventSourceRef.current) {
      eventSourceRef.current.close();
      eventSourceRef.current = null;
    }
  }, []);

  useEffect(() => {
    if (!downloadId) {
      cleanup();
      return;
    }

    const url = `${API_BASE}/download/${downloadId}/progress`;
    const es = new EventSource(url);
    eventSourceRef.current = es;

    const terminalStates = new Set(["completed", "failed", "cancelled"]);

    /** Handle any SSE event by parsing the data and updating state. */
    const handleEvent = (event: MessageEvent) => {
      try {
        const data: DownloadProgress = JSON.parse(event.data);
        setProgress(data);

        if (terminalStates.has(data.status)) {
          if (data.status === "completed") optionsRef.current?.onComplete?.(data);
          if (data.status === "failed") optionsRef.current?.onFailed?.(data);
          if (data.status === "cancelled") optionsRef.current?.onCancelled?.(data);
          cleanup();
        }
      } catch {
        // Ignore parse errors on malformed events
      }
    };

    // Listen to all event types the backend emits
    const eventTypes: SSEEventType[] = [
      "progress",
      "downloading",
      "completed",
      "failed",
      "cancelled",
      "error",
    ];
    eventTypes.forEach((type) => es.addEventListener(type, handleEvent));

    es.onerror = () => {
      if (es.readyState === EventSource.CLOSED) {
        cleanup();
      }
    };

    return cleanup;
  }, [downloadId, cleanup]);

  return { progress, close: cleanup };
}

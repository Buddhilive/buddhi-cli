"use client";

import { useEffect, useRef, useState, useCallback } from "react";
import type cytoscape from "cytoscape";
import { kgStore, type KGEntity, type KGRelation, type KGDocument } from "@/lib/kg-store";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import {
    RefreshCw,
    Search,
    X,
    ChevronDown,
    ChevronUp,
    FileText,
    AlertCircle,
    Network,
} from "lucide-react";

// ─── Constants ────────────────────────────────────────────────────────────────

const TYPE_COLORS: Record<string, string> = {
    PERSON: "#3b82f6",
    ORG: "#22c55e",
    PRODUCT: "#a855f7",
    CONCEPT: "#f59e0b",
    LOCATION: "#ef4444",
    TECH: "#06b6d4",
    OTHER: "#6b7280",
    DOCUMENT: "#475569",
};

const ENTITY_TYPES = ["PERSON", "ORG", "PRODUCT", "CONCEPT", "LOCATION", "TECH", "OTHER"] as const;

// eslint-disable-next-line @typescript-eslint/no-explicit-any
const CYTOSCAPE_STYLE: any[] = [
    {
        selector: "node[group = 'entity']",
        style: {
            shape: "ellipse",
            "background-color": "data(color)",
            "border-width": 2,
            "border-color": "data(borderColor)",
            label: "data(label)",
            "font-size": "10px",
            "font-weight": "500",
            color: "#f8fafc",
            "text-valign": "center",
            "text-halign": "center",
            "text-wrap": "wrap",
            "text-max-width": "80px",
            "min-zoomed-font-size": "6px",
            width: 60,
            height: 60,
        },
    },
    {
        selector: "node[group = 'document']",
        style: {
            shape: "round-rectangle",
            "background-color": TYPE_COLORS.DOCUMENT,
            "border-width": 1,
            "border-color": "#64748b",
            label: "data(label)",
            "font-size": "9px",
            color: "#cbd5e1",
            "text-valign": "center",
            "text-halign": "center",
            "text-wrap": "ellipsis",
            "text-max-width": "90px",
            "min-zoomed-font-size": "5px",
            width: 100,
            height: 32,
        },
    },
    {
        selector: "edge[group = 'co_occurs']",
        style: {
            width: 1,
            "line-color": "#475569",
            "target-arrow-color": "#475569",
            "curve-style": "bezier",
            label: "data(label)",
            "font-size": "7px",
            color: "#94a3b8",
            "text-rotation": "autorotate",
            "text-margin-y": -6,
            "min-zoomed-font-size": "5px",
            opacity: 0.6,
        },
    },
    {
        selector: "edge[group = 'has_entity']",
        style: {
            width: 1,
            "line-color": "#64748b",
            "line-style": "dashed",
            "target-arrow-shape": "none",
            "curve-style": "bezier",
            opacity: 0.5,
        },
    },
    {
        selector: ".dimmed",
        style: { opacity: 0.15 },
    },
    {
        selector: ".search-hit",
        style: {
            "border-width": 3,
            "border-color": "#fbbf24",
            opacity: 1,
        },
    },
    {
        selector: ":selected",
        style: {
            "border-width": 3,
            "border-color": "#f8fafc",
            opacity: 1,
        },
    },
];

// ─── Helpers ──────────────────────────────────────────────────────────────────

function buildElements(
    entities: KGEntity[],
    relations: KGRelation[]
): cytoscape.ElementDefinition[] {
    const nodes: cytoscape.ElementDefinition[] = entities
        .filter((e) => e.normalizedName.trim().length > 0)
        .map((e) => ({
            data: {
                id: e.normalizedName,
                label: e.name || e.normalizedName,
                type: e.type,
                group: "entity",
                color: TYPE_COLORS[e.type] ?? TYPE_COLORS.OTHER,
                borderColor: TYPE_COLORS[e.type] ?? TYPE_COLORS.OTHER,
            },
        }));

    const seen = new Set<string>();
    const edges: cytoscape.ElementDefinition[] = [];
    const validIds = new Set(nodes.map((n) => n.data.id as string));
    for (const r of relations) {
        if (!r.from.trim() || !r.to.trim()) continue;
        if (!validIds.has(r.from) || !validIds.has(r.to)) continue;
        const key = [r.from, r.to].sort().join("|||");
        if (seen.has(key) || r.from === r.to) continue;
        seen.add(key);
        edges.push({
            data: {
                id: key,
                source: r.from,
                target: r.to,
                label: r.relType,
                group: "co_occurs",
            },
        });
    }

    return [...nodes, ...edges];
}

// ─── Types ────────────────────────────────────────────────────────────────────

interface SelectedEntity {
    name: string;
    normalizedName: string;
    type: string;
    connectionCount: number;
}

// ─── Component ────────────────────────────────────────────────────────────────

export default function KnowledgeGraphView() {
    const containerRef = useRef<HTMLDivElement>(null);
    const cyRef = useRef<cytoscape.Core | null>(null);

    const [entities, setEntities] = useState<KGEntity[]>([]);
    const [relations, setRelations] = useState<KGRelation[]>([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);

    const [selectedEntity, setSelectedEntity] = useState<SelectedEntity | null>(null);
    const [expandedEntities, setExpandedEntities] = useState<Set<string>>(new Set());
    const [entityDocs, setEntityDocs] = useState<KGDocument[]>([]);
    const [docsLoading, setDocsLoading] = useState(false);

    const [hiddenTypes, setHiddenTypes] = useState<Set<string>>(new Set());
    const [searchQuery, setSearchQuery] = useState("");

    // ── Data fetching ──────────────────────────────────────────────────────────

    const fetchGraphData = useCallback(async () => {
        setLoading(true);
        setError(null);
        setSelectedEntity(null);
        setExpandedEntities(new Set());
        setEntityDocs([]);
        try {
            await kgStore.init();
            const [ents, rels] = await Promise.all([
                kgStore.getAllEntities(),
                kgStore.getAllRelations(),
            ]);
            setEntities(ents);
            setRelations(rels);
        } catch (err) {
            setError(err instanceof Error ? err.message : "Failed to load knowledge graph.");
        } finally {
            setLoading(false);
        }
    }, []);

    useEffect(() => { fetchGraphData(); }, [fetchGraphData]);

    // ── Cytoscape initialization ────────────────────────────────────────────────

    useEffect(() => {
        if (loading || !containerRef.current || entities.length === 0) return;

        // Dynamic import — Cytoscape accesses DOM, must be client-only
        import("cytoscape").then(({ default: Cytoscape }) => {
            if (!containerRef.current) return;

            // Destroy previous instance if any
            cyRef.current?.destroy();

            const cy = Cytoscape({
                container: containerRef.current,
                elements: buildElements(entities, relations),
                style: CYTOSCAPE_STYLE,
                layout: {
                    name: "cose",
                    animate: false,
                    nodeRepulsion: () => 8000,
                    idealEdgeLength: () => 80,
                    gravity: 0.4,
                    numIter: 1000,
                    fit: true,
                    padding: 40,
                } as cytoscape.LayoutOptions,
                minZoom: 0.05,
                maxZoom: 5,
            });

            // Tap entity node → select and show sidebar
            cy.on("tap", "node[group = 'entity']", (e) => {
                const node = e.target as cytoscape.NodeSingular;
                const connected = node.neighborhood();
                cy.elements().addClass("dimmed");
                connected.add(node).removeClass("dimmed");
                node.select();

                setSelectedEntity({
                    name: node.data("label"),
                    normalizedName: node.id(),
                    type: node.data("type"),
                    connectionCount: connected.nodes("[group = 'entity']").length,
                });
                setEntityDocs([]);
            });

            // Tap document node → highlight
            cy.on("tap", "node[group = 'document']", (e) => {
                const node = e.target as cytoscape.NodeSingular;
                cy.elements().addClass("dimmed");
                node.neighborhood().add(node).removeClass("dimmed");
            });

            // Tap canvas background → deselect
            cy.on("tap", (e) => {
                if (e.target === cy) {
                    cy.elements().removeClass("dimmed");
                    cy.nodes().unselect();
                    setSelectedEntity(null);
                    setEntityDocs([]);
                }
            });

            cyRef.current = cy;
        });

        return () => {
            cyRef.current?.destroy();
            cyRef.current = null;
        };
        // Re-initialize only when data changes (not on UI state changes)
        // eslint-disable-next-line react-hooks/exhaustive-deps
    }, [entities, relations, loading]);

    // ── Apply type visibility filters ──────────────────────────────────────────

    useEffect(() => {
        const cy = cyRef.current;
        if (!cy) return;
        ENTITY_TYPES.forEach((t) => {
            // eslint-disable-next-line @typescript-eslint/no-explicit-any
            const nodes = cy.nodes(`[type = "${t}"]`) as any;
            if (hiddenTypes.has(t)) nodes.hide();
            else nodes.show();
        });
    }, [hiddenTypes]);

    // ── Search ─────────────────────────────────────────────────────────────────

    useEffect(() => {
        const cy = cyRef.current;
        if (!cy) return;
        cy.nodes().removeClass("search-hit");
        if (!searchQuery.trim()) return;
        const lower = searchQuery.toLowerCase();
        const hits = cy.nodes().filter((n) =>
            (n.data("label") as string).toLowerCase().includes(lower)
        );
        hits.addClass("search-hit");
        if (hits.length > 0) {
            cy.animate({ fit: { eles: hits, padding: 100 } } as Parameters<typeof cy.animate>[0]);
        }
    }, [searchQuery]);

    // ── Document expansion ─────────────────────────────────────────────────────

    const expandDocuments = useCallback(async (normalizedName: string) => {
        const cy = cyRef.current;
        if (!cy) return;
        setDocsLoading(true);
        try {
            const docs = await kgStore.getEntityDocuments(normalizedName);
            setEntityDocs(docs);

            const newEls: cytoscape.ElementDefinition[] = [];
            for (const d of docs) {
                const docNodeId = `doc___${d.documentId}`;
                if (cy.getElementById(docNodeId).length > 0) continue;
                newEls.push(
                    { data: { id: docNodeId, label: d.fileName, group: "document" } },
                    {
                        data: {
                            id: `${normalizedName}___${docNodeId}`,
                            source: normalizedName,
                            target: docNodeId,
                            group: "has_entity",
                        },
                    }
                );
            }

            if (newEls.length > 0) {
                cy.add(newEls);
                cy.layout({
                    name: "cose",
                    animate: true,
                    fit: false,
                    nodeRepulsion: () => 6000,
                } as cytoscape.LayoutOptions).run();
            }

            setExpandedEntities((prev) => new Set([...prev, normalizedName]));
        } catch (err) {
            console.warn("[kg-view] expandDocuments error:", err);
        } finally {
            setDocsLoading(false);
        }
    }, []);

    const collapseDocuments = useCallback((normalizedName: string) => {
        const cy = cyRef.current;
        if (!cy) return;
        // Remove document nodes connected only to this entity (or orphaned)
        cy.nodes("[group = 'document']").forEach((docNode) => {
            const connectedEntityEdges = docNode.connectedEdges().filter(
                (e) => e.source().id() === normalizedName || e.target().id() === normalizedName
            );
            if (connectedEntityEdges.length > 0) docNode.remove();
        });
        setExpandedEntities((prev) => {
            const s = new Set(prev);
            s.delete(normalizedName);
            return s;
        });
        setEntityDocs([]);
    }, []);

    // ── Handlers ───────────────────────────────────────────────────────────────

    const resetView = () => {
        const cy = cyRef.current;
        if (!cy) return;
        cy.elements().removeClass("dimmed").removeClass("search-hit");
        cy.nodes().unselect();
        cy.fit(undefined, 40);
        setSelectedEntity(null);
        setSearchQuery("");
        setEntityDocs([]);
    };

    const toggleType = (type: string) => {
        setHiddenTypes((prev) => {
            const next = new Set(prev);
            next.has(type) ? next.delete(type) : next.add(type);
            return next;
        });
    };

    // ── Derived stats ──────────────────────────────────────────────────────────

    const visibleEntityCount = entities.filter((e) => !hiddenTypes.has(e.type)).length;
    const relatedEntities = selectedEntity
        ? (() => {
              const cy = cyRef.current;
              if (!cy) return [];
              return cy
                  .getElementById(selectedEntity.normalizedName)
                  .neighborhood()
                  .nodes("[group = 'entity']")
                  .map((n) => ({ name: n.data("label") as string, type: n.data("type") as string }));
          })()
        : [];

    // ── Render ─────────────────────────────────────────────────────────────────

    return (
        <div className="flex h-full flex-col overflow-hidden">
            {/* Header */}
            <div className="flex items-center justify-between border-b px-4 py-3">
                <div className="flex items-center gap-2">
                    <Network className="h-5 w-5 text-indigo-400" />
                    <h1 className="text-base font-semibold">Knowledge Graph</h1>
                    {!loading && !error && (
                        <span className="text-muted-foreground text-xs">
                            {visibleEntityCount} entities · {relations.length} relations
                        </span>
                    )}
                </div>
                <Button
                    variant="ghost"
                    size="icon-sm"
                    onClick={fetchGraphData}
                    disabled={loading}
                    title="Refresh graph"
                >
                    <RefreshCw className={`h-4 w-4 ${loading ? "animate-spin" : ""}`} />
                </Button>
            </div>

            {/* Toolbar */}
            {!loading && !error && entities.length > 0 && (
                <div className="flex flex-wrap items-center gap-2 border-b px-4 py-2">
                    {/* Search */}
                    <div className="relative flex-1 min-w-40 max-w-56">
                        <Search className="text-muted-foreground absolute top-1/2 left-2 h-3.5 w-3.5 -translate-y-1/2" />
                        <input
                            type="text"
                            value={searchQuery}
                            onChange={(e) => setSearchQuery(e.target.value)}
                            placeholder="Search entities…"
                            className="bg-muted/50 focus:ring-ring/50 w-full rounded-md py-1 pr-2 pl-7 text-xs outline-none focus:ring-1"
                        />
                        {searchQuery && (
                            <button
                                onClick={() => setSearchQuery("")}
                                className="text-muted-foreground absolute top-1/2 right-1.5 -translate-y-1/2"
                            >
                                <X className="h-3 w-3" />
                            </button>
                        )}
                    </div>

                    {/* Type filter chips */}
                    <div className="flex flex-wrap gap-1">
                        {ENTITY_TYPES.map((t) => {
                            const count = entities.filter((e) => e.type === t).length;
                            if (count === 0) return null;
                            const hidden = hiddenTypes.has(t);
                            return (
                                <button
                                    key={t}
                                    onClick={() => toggleType(t)}
                                    className={`flex items-center gap-1 rounded-full px-2 py-0.5 text-xs font-medium transition-opacity ${
                                        hidden ? "opacity-30" : "opacity-100"
                                    }`}
                                    style={{
                                        backgroundColor: (TYPE_COLORS[t] ?? "#6b7280") + "33",
                                        border: `1px solid ${TYPE_COLORS[t] ?? "#6b7280"}66`,
                                        color: TYPE_COLORS[t] ?? "#6b7280",
                                    }}
                                >
                                    <span
                                        className="inline-block h-1.5 w-1.5 rounded-full"
                                        style={{ backgroundColor: TYPE_COLORS[t] ?? "#6b7280" }}
                                    />
                                    {t}
                                    <span className="opacity-60">{count}</span>
                                </button>
                            );
                        })}
                    </div>

                    {/* Reset */}
                    <Button variant="ghost" size="xs" onClick={resetView} className="ml-auto shrink-0">
                        Reset view
                    </Button>
                </div>
            )}

            {/* Main content */}
            <div className="relative flex flex-1 overflow-hidden">
                {/* Loading */}
                {loading && (
                    <div className="flex flex-1 items-center justify-center">
                        <div className="flex flex-col items-center gap-3 text-sm">
                            <RefreshCw className="text-muted-foreground h-6 w-6 animate-spin" />
                            <span className="text-muted-foreground">Loading knowledge graph…</span>
                        </div>
                    </div>
                )}

                {/* Error */}
                {!loading && error && (
                    <div className="flex flex-1 items-center justify-center p-8">
                        <div className="flex max-w-sm flex-col items-center gap-3 text-center">
                            <AlertCircle className="h-8 w-8 text-red-400" />
                            <p className="text-sm font-medium text-red-400">Failed to load graph</p>
                            <p className="text-muted-foreground text-xs">{error}</p>
                            <Button size="sm" variant="outline" onClick={fetchGraphData}>
                                Retry
                            </Button>
                        </div>
                    </div>
                )}

                {/* Empty state */}
                {!loading && !error && entities.length === 0 && (
                    <div className="flex flex-1 items-center justify-center p-8">
                        <div className="flex max-w-sm flex-col items-center gap-3 text-center">
                            <Network className="text-muted-foreground h-10 w-10" />
                            <p className="text-sm font-medium">No knowledge graph data yet</p>
                            <p className="text-muted-foreground text-xs">
                                Upload documents on the Documents page. The AI will extract entities and
                                relationships to build this graph automatically.
                            </p>
                        </div>
                    </div>
                )}

                {/* Cytoscape canvas */}
                {!loading && !error && entities.length > 0 && (
                    <div ref={containerRef} className="flex-1" style={{ height: "100%", width: "100%" }} />
                )}

                {/* Sidebar */}
                {selectedEntity && (
                    <aside className="border-l bg-background/95 flex w-72 shrink-0 flex-col overflow-y-auto backdrop-blur">
                        {/* Header */}
                        <div className="flex items-start justify-between border-b p-4">
                            <div className="flex flex-col gap-1">
                                <span className="text-sm font-semibold leading-tight">
                                    {selectedEntity.name}
                                </span>
                                <Badge
                                    variant="secondary"
                                    className="w-fit text-xs"
                                    style={{
                                        backgroundColor:
                                            (TYPE_COLORS[selectedEntity.type] ?? "#6b7280") + "33",
                                        color: TYPE_COLORS[selectedEntity.type] ?? "#6b7280",
                                        border: `1px solid ${TYPE_COLORS[selectedEntity.type] ?? "#6b7280"}66`,
                                    }}
                                >
                                    {selectedEntity.type}
                                </Badge>
                            </div>
                            <button
                                onClick={() => {
                                    cyRef.current?.elements().removeClass("dimmed");
                                    cyRef.current?.nodes().unselect();
                                    setSelectedEntity(null);
                                    setEntityDocs([]);
                                }}
                                className="text-muted-foreground hover:text-foreground rounded p-0.5 transition-colors"
                            >
                                <X className="h-4 w-4" />
                            </button>
                        </div>

                        {/* Stats */}
                        <div className="border-b px-4 py-3">
                            <p className="text-muted-foreground text-xs">
                                {selectedEntity.connectionCount} connected{" "}
                                {selectedEntity.connectionCount === 1 ? "entity" : "entities"}
                            </p>
                        </div>

                        {/* Documents section */}
                        <div className="border-b px-4 py-3">
                            <div className="flex items-center justify-between">
                                <span className="text-xs font-medium">Source Documents</span>
                                {expandedEntities.has(selectedEntity.normalizedName) ? (
                                    <Button
                                        variant="ghost"
                                        size="xs"
                                        onClick={() => collapseDocuments(selectedEntity.normalizedName)}
                                        className="h-6 gap-1 text-xs"
                                    >
                                        <ChevronUp className="h-3 w-3" />
                                        Hide
                                    </Button>
                                ) : (
                                    <Button
                                        variant="ghost"
                                        size="xs"
                                        onClick={() => expandDocuments(selectedEntity.normalizedName)}
                                        disabled={docsLoading}
                                        className="h-6 gap-1 text-xs"
                                    >
                                        {docsLoading ? (
                                            <RefreshCw className="h-3 w-3 animate-spin" />
                                        ) : (
                                            <ChevronDown className="h-3 w-3" />
                                        )}
                                        Show on graph
                                    </Button>
                                )}
                            </div>

                            {entityDocs.length > 0 && (
                                <ul className="mt-2 space-y-1">
                                    {entityDocs.map((d) => (
                                        <li
                                            key={d.documentId}
                                            className="flex items-center gap-1.5 text-xs"
                                        >
                                            <FileText className="text-muted-foreground h-3 w-3 shrink-0" />
                                            <span className="truncate text-slate-300">{d.fileName}</span>
                                        </li>
                                    ))}
                                </ul>
                            )}
                        </div>

                        {/* Related entities */}
                        {relatedEntities.length > 0 && (
                            <div className="px-4 py-3">
                                <p className="mb-2 text-xs font-medium">Related Entities</p>
                                <ul className="space-y-1.5">
                                    {relatedEntities.slice(0, 15).map((e) => (
                                        <li key={e.name} className="flex items-center gap-2 text-xs">
                                            <span
                                                className="h-2 w-2 shrink-0 rounded-full"
                                                style={{
                                                    backgroundColor: TYPE_COLORS[e.type] ?? TYPE_COLORS.OTHER,
                                                }}
                                            />
                                            <span className="truncate text-slate-300">{e.name}</span>
                                            <span className="text-muted-foreground ml-auto shrink-0">
                                                {e.type}
                                            </span>
                                        </li>
                                    ))}
                                    {relatedEntities.length > 15 && (
                                        <li className="text-muted-foreground text-xs">
                                            +{relatedEntities.length - 15} more
                                        </li>
                                    )}
                                </ul>
                            </div>
                        )}
                    </aside>
                )}
            </div>

            {/* Legend */}
            {!loading && !error && entities.length > 0 && (
                <div className="border-t px-4 py-2">
                    <div className="flex flex-wrap items-center gap-x-4 gap-y-1">
                        {ENTITY_TYPES.map((t) => {
                            const count = entities.filter((e) => e.type === t).length;
                            if (count === 0) return null;
                            return (
                                <span key={t} className="flex items-center gap-1 text-xs text-slate-400">
                                    <span
                                        className="inline-block h-2 w-2 rounded-full"
                                        style={{ backgroundColor: TYPE_COLORS[t] }}
                                    />
                                    {t}
                                </span>
                            );
                        })}
                        <span className="flex items-center gap-1 text-xs text-slate-400">
                            <span className="inline-block h-2 w-2 rounded bg-slate-600" />
                            DOCUMENT
                        </span>
                    </div>
                </div>
            )}
        </div>
    );
}

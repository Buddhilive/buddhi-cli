---
id: mem-decision-single-sqlite-schema-v2-for-graph-intelligence-ast-cache-and
kind: decision
title: Single SQLite Schema v2 for Graph Intelligence, AST Cache, and Blast Radius
summary: Store communities, SHA-256 extract_cache, and edge confidence/context in
  .buddhi/graphs/tree-graph.db and expose via buddhi_graph MCP and <50ms stdlib hooks
status: stable
confidence: verified
scope: project
paths:
- src/buddhi/graph/**
- src/buddhi/persist/**
- src/buddhi/mcp/**
tags:
- graph
- sdd
generated:
  by: buddhi-cli
  at: '2026-10-27T05:51:26.260828+00:00'
---

# Summary

Store communities, SHA-256 extract_cache, and edge confidence/context in .buddhi/graphs/tree-graph.db and expose via buddhi_graph MCP and <50ms stdlib hooks

# Context & Rationale

Feature 007-analyze-graphify-and consolidates communities, SHA-256 per-file AST extract_cache, and edge provenance (confidence, confidence_score, context) into a single SQLite file (.buddhi/graphs/tree-graph.db Schema v2) carried forward across atomic .tmp-<pid> writes, exposed via buddhi_graph MCP tool, buddhi graph CLI, and a stdlib-only fail-open <50ms graph_context.py hook.

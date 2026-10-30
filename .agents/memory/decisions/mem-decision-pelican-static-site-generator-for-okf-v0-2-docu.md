---
id: mem-decision-pelican-static-site-generator-for-okf-v0-2-documentation
kind: decision
title: Pelican Static Site Generator for OKF v0.2 Documentation
summary: Adopted Pelican static site generator with custom OKFMarkdownReader for live
  documentation.
status: stable
confidence: verified
scope: project
generated:
  by: buddhi-cli
  at: '2026-10-27T16:04:46.258394+00:00'
---

# Summary

Adopted Pelican static site generator with custom OKFMarkdownReader for live documentation.

# Context & Rationale

Selected Pelican as the static site generator for buddhi-cli documentation over MkDocs or Sphinx because Pelican natively parses decoupled frontmatter and supports arbitrary content hierarchies without requiring a strict nav schema. OKFMarkdownReader parses Google OKF v0.2 YAML frontmatter, strips forbidden Attested Computation fields, maps metadata to Pelican Page objects, and rewrites relative markdown links to HTML.

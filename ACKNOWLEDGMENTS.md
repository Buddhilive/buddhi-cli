# Acknowledgments

`buddhi-cli` incorporates concepts, skills, rules, and contrast-checking logic adapted from the following open-source project:

## anti-slop

- **Repository**: [https://github.com/miqdadbadjuber/anti-slop](https://github.com/miqdadbadjuber/anti-slop)
- **Author**: Miqdad Badjuber
- **License**: MIT License

### Description & Adapted Components

The `anti-slop` filter prevents AI coding agents from generating generic, low-effort UI designs, marketing prose, and unnecessary code comments. `buddhi-cli` adapts the `anti-slop` suite into the Google Antigravity harness conventions:
- **Skills**: Six specialized skills scaffolded during `buddhi init` (`antislop`, `antislop-ui`, `antislop-copywriting`, `antislop-human`, `antislop-layoutmobile`, `antislop-code`).
- **Rules**: An always-on Antigravity routing rule (`.agents/rules/antislop.md`).
- **CLI Scripts**: Standalone Python ports of the WCAG 2.x contrast verification script (`buddhi scripts contrast`) and the global mode configuration utility (`buddhi scripts antislop-mode`).
- **MCP Tool**: The `check_contrast` tool integrated into the Buddhi MCP server.

We express our gratitude to Miqdad Badjuber and contributors for creating and sharing the `anti-slop` project.

---

### Upstream MIT License

```text
MIT License

Copyright (c) 2026 Miqdad Badjuber (antislop)

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
```


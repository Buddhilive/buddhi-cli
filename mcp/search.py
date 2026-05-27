import os
import re
import fnmatch
import tiktoken
from collections import Counter
from db import get_workspace_root

MAX_FILE_SIZE = 512 * 1024  # 512KB limit
MAX_WALK_DEPTH = 20
MAX_PATTERN_LEN = 1024
MIN_IDENT_LENGTH = 6
SHORT_ID_PREFIX = 'α'

SKIP_DIRS = {
    ".venv", "venv", "env", ".git", ".github", ".mypy_cache", ".ruff_cache",
    ".buddhi", "node_modules", "__pycache__", "build", "dist", "buddhi_ai.egg-info"
}

BINARY_EXTENSIONS = {
    "png", "jpg", "jpeg", "gif", "webp", "ico", "svg", "woff", "woff2",
    "ttf", "eot", "pdf", "zip", "tar", "gz", "br", "zst", "bz2", "xz",
    "mp3", "mp4", "webm", "ogg", "wasm", "so", "dylib", "dll", "exe",
    "lock", "map", "snap", "patch", "db", "sqlite", "parquet", "arrow",
    "bin", "o", "a", "class", "pyc", "pyo"
}

GENERATED_FILE_SUFFIXES = {
    ".min.js", ".min.css", ".bundle.js", ".chunk.js", ".d.ts", ".js.map", ".css.map"
}

SECRET_EXTENSIONS = {
    "pem", "key", "p12", "pfx", "crt", "der", "p8", "pub"
}

SECRET_FILENAMES = {
    "id_rsa", "id_dsa", "id_ecdsa", "id_ed25519", "credentials", "secrets.json"
}

SECRET_CONTENT_PATTERNS = [
    re.compile(r"(?:api[_-]?key|private[_-]?key|token|password|passwd|secret)\s*[:=]\s*['\"][a-zA-Z0-9_\-\.\~]{12,}['\"]", re.IGNORECASE),
    re.compile(r"-----BEGIN\s+(?:RSA\s+|EC\s+|DSA\s+|OPENSSH\s+)?PRIVATE\s+KEY-----", re.IGNORECASE)
]


class SymbolMap:
    """Algorithm that compresses search output tokens by mapping repeating long code identifiers
    to brief, unique single-character Greek markers, appending a mapping block at the end.
    """
    def __init__(self):
        self.forward = {}
        self.next_id = 1

    def register(self, identifier: str) -> str | None:
        if len(identifier) < MIN_IDENT_LENGTH:
            return None

        if identifier in self.forward:
            return self.forward[identifier]

        short_id = f"{SHORT_ID_PREFIX}{self.next_id}"
        self.next_id += 1
        self.forward[identifier] = short_id
        return short_id

    def apply(self, text: str) -> str:
        if not self.forward:
            return text

        # Sort keys by length in descending order to avoid partial matches
        # e.g., mapping 'validateToken' before 'validate'
        sorted_keys = sorted(self.forward.keys(), key=len, reverse=True)
        result = text
        for long_id in sorted_keys:
            result = result.replace(long_id, self.forward[long_id])
        return result

    def format_table(self) -> str:
        if not self.forward:
            return ""

        # Sort entries by their short ID numeric value
        sorted_entries = sorted(
            self.forward.items(),
            key=lambda x: int(x[1].replace(SHORT_ID_PREFIX, ""))
        )
        table = "\n§MAP:"
        for long_id, short_id in sorted_entries:
            table += f"\n  {short_id}={long_id}"
        return table

    def __len__(self):
        return len(self.forward)


def should_register(identifier: str, count: int, next_id: int, encoder) -> bool:
    """ROI check: Register identifier if token savings outweigh the lookup table entry cost.
    Savings = occurrences * (ident_tokens - short_tokens)
    Cost = ident_tokens + short_tokens + 2 (overhead for '=' and newline)
    """
    if len(identifier) < MIN_IDENT_LENGTH:
        return False

    ident_tokens = len(encoder.encode(identifier))
    short_id = f"{SHORT_ID_PREFIX}{next_id}"
    short_tokens = len(encoder.encode(short_id))

    token_saving_per_use = ident_tokens - short_tokens
    if token_saving_per_use <= 0:
        return False

    total_savings = count * token_saving_per_use
    entry_cost = ident_tokens + short_tokens + 2

    return total_savings > entry_cost


def extract_identifiers(content: str, ext: str, encoder) -> list[str]:
    """Tokenizes output content, filters ROI-positive identifiers, and orders them by net savings."""
    ident_re = re.compile(r"\b[a-zA-Z_][a-zA-Z0-9_]*\b")
    
    # Filter keywords for common languages to avoid compressing standard control structures
    keywords = get_keywords_for_ext(ext)

    seen = Counter()
    for match in ident_re.finditer(content):
        word = match.group(0)
        if len(word) >= MIN_IDENT_LENGTH and word not in keywords:
            seen[word] += 1

    next_id = 1
    roi_positive = []
    for word, count in seen.items():
        if should_register(word, count, next_id, encoder):
            roi_positive.append((word, count))
            next_id += 1

    # Sort by total character/token savings impact descending
    roi_positive.sort(key=lambda x: len(x[0]) * x[1], reverse=True)
    return [word for word, _ in roi_positive]


def get_keywords_for_ext(ext: str) -> set[str]:
    """Returns syntax keyword sets to exclude from substitution for given extensions."""
    if ext == "rs":
        return {"continue", "default", "return", "struct", "unsafe", "where", "impl", "const", "static", "match", "pub", "fn"}
    elif ext in ("ts", "tsx", "js", "jsx"):
        return {"constructor", "arguments", "undefined", "prototype", "instanceof", "function", "return", "const", "class", "export", "import"}
    elif ext == "py":
        return {"continue", "lambda", "return", "import", "class", "def", "global", "yield", "except", "assert"}
    return set()


def is_binary_ext(filepath: str) -> bool:
    ext = os.path.splitext(filepath)[1].lstrip(".").lower()
    return ext in BINARY_EXTENSIONS


def is_generated_file(filepath: str) -> bool:
    name = os.path.basename(filepath).lower()
    return any(name.endswith(suffix) for suffix in GENERATED_FILE_SUFFIXES)


def is_secret_like(filepath: str, content: str = None) -> bool:
    """Security check to skip credentials and certificate files."""
    name = os.path.basename(filepath)
    ext = os.path.splitext(name)[1].lstrip(".").lower()
    
    if ext in SECRET_EXTENSIONS or name.lower() in SECRET_FILENAMES or name.startswith(".env"):
        return True

    if content:
        if any(pat.search(content) for pat in SECRET_CONTENT_PATTERNS):
            return True

    return False


def parse_gitignore(gitignore_path: str) -> list[str]:
    """Parses a .gitignore file and returns a list of clean, non-comment patterns."""
    patterns = []
    if os.path.exists(gitignore_path):
        try:
            with open(gitignore_path, "r", encoding="utf-8", errors="ignore") as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith("#"):
                        patterns.append(line)
        except Exception:
            pass
    return patterns


class GitIgnoreFilter:
    """Manages recursive .gitignore matching."""
    def __init__(self, workspace_root: str):
        self.workspace_root = workspace_root
        self.ignore_cache = {}  # dir_path -> list of patterns

    def get_gitignores_for_file(self, filepath: str) -> list[tuple[str, list[str]]]:
        """Finds all .gitignore files from the file's directory up to the workspace root."""
        abs_path = os.path.abspath(filepath)
        abs_root = os.path.abspath(self.workspace_root)
        
        gitignores = []
        curr = os.path.dirname(abs_path)
        while True:
            gi_path = os.path.join(curr, ".gitignore")
            if os.path.exists(gi_path):
                if gi_path not in self.ignore_cache:
                    self.ignore_cache[gi_path] = parse_gitignore(gi_path)
                gitignores.append((curr, self.ignore_cache[gi_path]))
            
            if curr == abs_root or curr == os.path.dirname(curr):
                break
            curr = os.path.dirname(curr)
        return gitignores

    def is_ignored(self, filepath: str) -> bool:
        abs_path = os.path.abspath(filepath)
        gitignores = self.get_gitignores_for_file(abs_path)
        
        for gi_dir, patterns in gitignores:
            # Calculate path relative to the directory containing this .gitignore
            rel_to_gi = os.path.relpath(abs_path, gi_dir).replace(os.path.sep, "/")
            segments = rel_to_gi.split("/")
            
            for pat in patterns:
                pat_clean = pat.rstrip("/")
                is_anchored = "/" in pat_clean
                
                if is_anchored:
                    # Must match prefix of rel_to_gi
                    pat_parts = pat_clean.split("/")
                    if len(segments) >= len(pat_parts):
                        matched = True
                        for i, part in enumerate(pat_parts):
                            if not fnmatch.fnmatch(segments[i], part):
                                matched = False
                                break
                        if matched:
                            return True
                else:
                    # Can match any segment
                    for seg in segments:
                        if fnmatch.fnmatch(seg, pat_clean):
                            return True
        return False


def get_token_count(text: str, encoder) -> int:
    return len(encoder.encode(text))


def handle_search(
    pattern: str,
    search_path: str = None,
    ext_filter: str = None,
    max_results: int = 50,
    ignore_gitignore: bool = False
) -> str:
    """Performs regex-based text search over files in the workspace with token compression."""
    if len(pattern) > MAX_PATTERN_LEN:
        return f"ERROR: pattern too long ({len(pattern)} > {MAX_PATTERN_LEN} chars)"

    try:
        re_matcher = re.compile(pattern)
    except re.error as e:
        return f"ERROR: invalid regex: {e}"

    workspace_root = get_workspace_root()
    root_dir = os.path.abspath(search_path) if search_path else workspace_root

    if not os.path.exists(root_dir):
        return f"ERROR: {root_dir} does not exist"

    # Initialize gitignore filter
    gi_filter = GitIgnoreFilter(workspace_root)
    
    files_to_search = []
    skipped_large = 0
    skipped_boundary = 0

    # Walk directory tree deterministically
    for root, dirs, files in os.walk(root_dir):
        # Prevent walking too deep
        depth = len(os.path.relpath(root, root_dir).split(os.path.sep))
        if depth > MAX_WALK_DEPTH:
            dirs[:] = []
            continue

        # Prune skipped dirs in place
        dirs[:] = [d for d in dirs if d not in SKIP_DIRS and not d.startswith(".")]

        for file in files:
            filepath = os.path.join(root, file)
            
            # Skip hidden files
            if file.startswith("."):
                continue

            # Respect GitIgnore rules
            if not ignore_gitignore and gi_filter.is_ignored(filepath):
                continue

            # Skip binary / generated
            if is_binary_ext(filepath) or is_generated_file(filepath):
                continue

            # Skip secrets by path/filename
            if is_secret_like(filepath):
                skipped_boundary += 1
                continue

            # Apply extension filter
            if ext_filter:
                ext = os.path.splitext(file)[1].lstrip(".").lower()
                if ext != ext_filter.lstrip(".").lower():
                    continue

            # File size limit
            try:
                size = os.path.getsize(filepath)
                if size > MAX_FILE_SIZE:
                    skipped_large += 1
                    continue
            except OSError:
                continue

            files_to_search.append(filepath)

    # Deterministic search: stable path ordering makes match truncations reproducible.
    files_to_search.sort()

    matches = []
    files_searched = 0
    skipped_encoding = 0
    raw_tokens_accum = 0
    
    # Initialize encoder
    try:
        encoder = tiktoken.get_encoding("cl100k_base")
    except Exception:
        encoder = tiktoken.encoding_for_model("gpt-4")

    for filepath in files_to_search:
        if len(matches) >= max_results:
            break

        try:
            with open(filepath, "r", encoding="utf-8", errors="replace") as f:
                content = f.read()
        except OSError:
            skipped_encoding += 1
            continue

        # Post-read secret checks
        if is_secret_like(filepath, content):
            skipped_boundary += 1
            continue

        files_searched += 1
        lines = content.splitlines()
        
        rel_path = os.path.relpath(filepath, root_dir).replace(os.path.sep, "/")
        
        for i, line in enumerate(lines, 1):
            if re_matcher.search(line):
                trimmed_line = line.strip()
                # Estimate standard token overhead for raw matching lines
                raw_tokens_accum += len(encoder.encode(trimmed_line)) + 2
                matches.append(f"{rel_path}:{i} {trimmed_line}")
                if len(matches) >= max_results:
                    break

    if not matches:
        msg = f"0 matches for '{pattern}' in {files_searched} files"
        if skipped_large > 0:
            msg += f" ({skipped_large} large files skipped)"
        if skipped_encoding > 0:
            msg += f" ({skipped_encoding} files skipped: binary/encoding)"
        if skipped_boundary > 0:
            msg += f" ({skipped_boundary} secret-like files skipped by boundary policy)"
        return msg

    # Identify matching directories for monorepo scope hints
    matched_top_dirs = set()
    for m in matches:
        parts = m.split("/")
        if len(parts) > 1:
            matched_top_dirs.add(parts[0])

    # Structure basic matched header
    matched_files_list = sorted(list(set(m.split(":")[0] for m in matches)))
    result = f"{len(matches)} matches in {files_searched} files"
    if len(matched_files_list) > 1:
        result += f" [{', '.join(matched_files_list)}]"
    result += ":\n" + "\n".join(matches)

    # Append skips info if any
    skips_footer = []
    if skipped_large > 0:
        skips_footer.append(f"({skipped_large} files >512KB skipped)")
    if skipped_encoding > 0:
        skips_footer.append(f"({skipped_encoding} files skipped: binary/encoding)")
    if skipped_boundary > 0:
        skips_footer.append(f"({skipped_boundary} secret-like files skipped by boundary policy)")
    if skips_footer:
        result += "\n" + "\n".join(skips_footer)

    # Apply SymbolMap token-compression
    ext = ext_filter if ext_filter else "py"
    idents = extract_identifiers(result, ext, encoder)
    
    if len(idents) >= 3:
        sym_map = SymbolMap()
        for ident in idents:
            sym_map.register(ident)
            
        sym_table = sym_map.format_table()
        compressed = sym_map.apply(result)
        
        original_tokens = get_token_count(result, encoder)
        compressed_tokens = get_token_count(compressed, encoder) + get_token_count(sym_table, encoder)
        
        net_saving = original_tokens - compressed_tokens
        if original_tokens > 0 and (net_saving * 100 // original_tokens) >= 5:
            result = f"{compressed}{sym_table}"

    # Scope hint for monorepos
    if len(matched_top_dirs) > 3:
        dirs_sorted = sorted(list(matched_top_dirs))
        dir_list = ", ".join(f"'{d}'" for d in dirs_sorted[:6])
        extra = f", +{len(matched_top_dirs) - 6} more" if len(matched_top_dirs) > 6 else ""
        result += f"\n\nResults span {len(matched_top_dirs)} directories ({dir_list}{extra}). Use the 'path' parameter to scope to a specific service, e.g. path=\"{dirs_sorted[0]}/\"."

    # Print token savings metrics
    sent_tokens = get_token_count(result, encoder)
    # rg defaults to showing full paths + 2 context lines per match. We estimate
    # the native cost as ~2.5x raw matches tokens (context + separators + headers)
    native_estimate = int(raw_tokens_accum * 2.5)
    original = max(native_estimate, raw_tokens_accum)
    
    savings_pct = 0
    if original > 0:
        savings_pct = max(0, (original - sent_tokens) * 100 // original)
        
    savings_footer = f"\n\n[Token savings: {savings_pct}% (sent {sent_tokens} tokens vs. ~{original} estimated native tokens)]"
    result += savings_footer

    return result

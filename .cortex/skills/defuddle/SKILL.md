---
name: defuddle
description: Extract clean markdown content from web pages using Defuddle CLI, removing clutter and navigation to save tokens. Use instead of WebFetch when the user provides a URL to read or analyze, for online documentation, articles, blog posts, or any standard web page. Do NOT use for URLs ending in .md — those are already markdown, use WebFetch directly.
---

# Defuddle

Use Defuddle CLI to extract clean readable content from web pages. Prefer over WebFetch for standard web pages — it removes navigation, ads, and clutter, reducing token usage. If not installed: `npm install -g defuddle`

## Usage

Always use `--md` for markdown output:
```bash
defuddle parse --md
```

Save to file:
```bash
defuddle parse --md -o content.md
```

Extract specific metadata:
```bash
defuddle parse -p title
defuddle parse -p description
defuddle parse -p domain
```

## Output formats
| Flag | Format |
|------|--------|
| `--md` | Markdown (default choice) |
| `--json` | JSON with both HTML and markdown |
| (none) | HTML |
| `-p <property>` | Specific metadata property |

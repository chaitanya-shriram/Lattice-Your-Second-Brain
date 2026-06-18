import re
from pathlib import Path
from typing import Any
import yaml

WIKILINK_PATTERN = re.compile(r'\[\[([^\[\]|]+)(?:\|([^\[\]]+))?\]\]')
FRONTMATTER_PATTERN = re.compile(r'^---\n(.*?)\n---\n', re.DOTALL)


def parse_frontmatter(content: str) -> tuple[dict, str]:
    """Return (metadata_dict, body_without_frontmatter)."""
    m = FRONTMATTER_PATTERN.match(content)
    if not m:
        return {}, content
    try:
        meta = yaml.safe_load(m.group(1)) or {}
    except yaml.YAMLError:
        meta = {}
    body = content[m.end():]
    return meta, body


def build_frontmatter(meta: dict) -> str:
    """Build YAML frontmatter string."""
    return "---\n" + yaml.dump(meta, default_flow_style=False, allow_unicode=True) + "---\n\n"


def extract_wikilinks(content: str) -> list[dict]:
    """Extract all [[links]] from content."""
    links = []
    for i, line in enumerate(content.splitlines(), 1):
        for m in WIKILINK_PATTERN.finditer(line):
            links.append({
                "target": m.group(1).strip(),
                "display": m.group(2),
                "line": i,
                "raw": m.group(0),
                "context": line[max(0, m.start()-25):m.end()+25],
            })
    return links


def slugify(text: str) -> str:
    """Convert text to kebab-case slug."""
    text = text.lower().strip()
    text = re.sub(r'[^\w\s-]', '', text)
    text = re.sub(r'[\s_]+', '-', text)
    text = re.sub(r'-+', '-', text)
    return text.strip('-')


def resolve_wikilink(target: str, vault_path: Path) -> Path | None:
    """Find actual file path for a wikilink target."""
    target_slug = slugify(target)
    for md in vault_path.rglob("*.md"):
        if slugify(md.stem) == target_slug or md.stem == target:
            return md
    return None

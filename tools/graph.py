#!/usr/bin/env python3
"""Query and lint an Obsidian vault as a typed-edge knowledge graph.

  node  = one markdown note; frontmatter = properties
  edges = moc (hub) · depends-on · superseded-by (time axis) · implements (code, scalar)

usage:
  graph.py stats   <vault>
  graph.py lint    <vault> [--limit N]
  graph.py query   <vault> --domain <slug> [--depth N]
  graph.py current <vault> <note>
  add --json to any command for machine-readable output
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from collections import defaultdict
from pathlib import Path

SKIP_DIRS = {".git", ".obsidian", "node_modules", ".trash"}
EDGE_KEYS = ("moc", "depends-on", "superseded-by")
WIKILINK = re.compile(r"\[\[([^\]|#]+)(?:#[^\]|]*)?(?:\|[^\]]*)?\]\]")
NULLS = {"", "null", "~", "none"}


def parse_frontmatter(text: str) -> tuple[dict, str]:
    """Small YAML subset: `key: value`, `key: [a, b]`, and `key:` followed by `- item` lines."""
    if not text.startswith("---\n"):
        return {}, text
    end = text.find("\n---", 4)
    if end < 0:
        return {}, text
    fm, body = text[4:end], text[end + 4:]
    data: dict = {}
    key = None
    for line in fm.splitlines():
        m = re.match(r"^([A-Za-z0-9_-]+):\s*(.*)$", line)
        if m:
            key, val = m.group(1), m.group(2).strip()
            if val.startswith("[") and val.endswith("]"):
                data[key] = [v.strip().strip("\"'") for v in split_inline(val[1:-1]) if v.strip()]
            elif val.lower() in NULLS:
                data[key] = [] if val == "" else None
            else:
                data[key] = val.strip("\"'")
            continue
        m = re.match(r"^\s+-\s+(.*)$", line)
        if m and key is not None and isinstance(data.get(key), list):
            data[key].append(m.group(1).strip().strip("\"'"))
    return data, body


def split_inline(s: str) -> list[str]:
    """Split `"[[a]]", "[[b, c]]"` on commas outside quotes/brackets."""
    out, buf, depth, quote = [], "", 0, None
    for ch in s:
        if quote:
            buf += ch
            if ch == quote:
                quote = None
        elif ch in "\"'":
            quote = ch
            buf += ch
        elif ch == "[":
            depth += 1
            buf += ch
        elif ch == "]":
            depth -= 1
            buf += ch
        elif ch == "," and depth == 0:
            out.append(buf)
            buf = ""
        else:
            buf += ch
    out.append(buf)
    return out


def links_in(value) -> list[str]:
    values = value if isinstance(value, list) else [value] if value else []
    return [m.group(1).strip() for v in values for m in WIKILINK.finditer(str(v))]


class Vault:
    def __init__(self, root: Path):
        self.root = root
        self.notes: dict[str, dict] = {}          # relpath (no .md) -> note
        self.by_stem: dict[str, list[str]] = defaultdict(list)
        for p in sorted(root.rglob("*.md")):
            if SKIP_DIRS & set(p.relative_to(root).parts):
                continue
            fm, body = parse_frontmatter(p.read_text(encoding="utf-8", errors="ignore"))
            rel = p.relative_to(root).with_suffix("").as_posix()
            self.notes[rel] = {"id": rel, "fm": fm, "body_links": links_in(body)}
            self.by_stem[p.stem].append(rel)
        self.edges: list[tuple[str, str, str]] = []  # (src, kind, raw target)
        for rel, n in self.notes.items():
            for k in EDGE_KEYS:
                for t in links_in(n["fm"].get(k)):
                    self.edges.append((rel, k, t))

    def resolve(self, target: str, src: str | None = None, kind: str | None = None) -> tuple[str | None, str]:
        """Return (note id, status) — status: ok | broken | ambiguous.

        Same basename in several folders: a `moc` edge prefers the hub under */moc/*,
        otherwise the candidate sharing the longest folder prefix with the linking note wins.
        """
        t = target.removesuffix(".md")
        if t in self.notes:
            return t, "ok"
        cands = [r for r in self.notes if r.endswith("/" + t)] if "/" in t else self.by_stem.get(t.split("/")[-1], [])
        if len(cands) > 1 and kind == "moc":
            hubs = [c for c in cands if self.is_moc(c)]
            cands = hubs or cands
        if len(cands) > 1 and src:
            def shared(c: str) -> int:
                a, b = src.split("/")[:-1], c.split("/")[:-1]
                n = 0
                while n < min(len(a), len(b)) and a[n] == b[n]:
                    n += 1
                return n
            best = max(shared(c) for c in cands)
            cands = [c for c in cands if shared(c) == best]
        if len(cands) == 1:
            return cands[0], "ok"
        return (None, "ambiguous") if cands else (None, "broken")

    def find(self, name: str) -> str | None:
        rid, status = self.resolve(name)
        return rid

    def is_moc(self, rel: str) -> bool:
        return self.notes[rel]["fm"].get("type") == "moc" or "/moc/" in "/" + rel

    def current(self, rel: str) -> list[str]:
        """Follow superseded-by until a note that is not superseded (cycle-safe)."""
        chain, seen = [rel], {rel}
        while True:
            nxt = links_in(self.notes[chain[-1]]["fm"].get("superseded-by"))
            if not nxt:
                return chain
            rid, _ = self.resolve(nxt[0], chain[-1])
            if rid is None or rid in seen:
                return chain + ([f"!{nxt[0]}"] if rid is None else [f"!cycle:{rid}"])
            chain.append(rid)
            seen.add(rid)


def cmd_stats(v: Vault) -> dict:
    total = len(v.notes)
    linked = set()
    resolved = defaultdict(int)
    problems = defaultdict(int)
    for src, kind, t in v.edges:
        rid, status = v.resolve(t, src, kind)
        if status == "ok":
            resolved[kind] += 1
            linked.update({src, rid})
        else:
            problems[status] += 1
    for rel, n in v.notes.items():
        for t in n["body_links"]:
            rid, status = v.resolve(t, rel)
            if status == "ok":
                linked.update({rel, rid})
    implements = sum(1 for n in v.notes.values() if n["fm"].get("implements"))
    return {
        "notes": total,
        "with_domain": sum(1 for n in v.notes.values() if n["fm"].get("domain")),
        "moc_hubs": sum(1 for r in v.notes if v.is_moc(r)),
        "edges": {k: resolved.get(k, 0) for k in EDGE_KEYS} | {"implements(notes)": implements},
        "unresolved_edges": dict(problems),
        "superseded_notes": sum(1 for n in v.notes.values() if links_in(n["fm"].get("superseded-by"))),
        "related_fields": sum(1 for n in v.notes.values() if "related" in n["fm"]),
        "orphan_rate": round(1 - len(linked) / total, 3) if total else 0,
    }


def cmd_lint(v: Vault, limit: int) -> dict:
    issues = defaultdict(list)
    for src, kind, t in v.edges:
        rid, status = v.resolve(t, src, kind)
        if status != "ok":
            issues[f"{status}_{kind}"].append(f"{src} -> [[{t}]]")
    for rel, n in v.notes.items():
        if "related" in n["fm"]:
            issues["related_field"].append(rel)
        chain = v.current(rel)
        if chain[-1].startswith("!cycle"):
            issues["superseded_cycle"].append(" -> ".join(chain))
    return {k: {"count": len(xs), "examples": xs[:limit]} for k, xs in sorted(issues.items())}


def cmd_query(v: Vault, domain: str, depth: int) -> dict:
    members = [r for r, n in v.notes.items() if n["fm"].get("domain") == domain and not v.is_moc(r)]
    pulled: dict[str, str] = {}
    frontier = list(members)
    for _ in range(depth):
        nxt = []
        for r in frontier:
            for t in links_in(v.notes[r]["fm"].get("depends-on")):
                rid, status = v.resolve(t, r)
                if status == "ok" and rid not in members and rid not in pulled:
                    pulled[rid] = r
                    nxt.append(rid)
        frontier = nxt

    def row(r: str) -> dict:
        fm = v.notes[r]["fm"]
        chain = v.current(r)
        return {
            "note": r,
            "status": fm.get("status") or fm.get("type"),
            "current": chain[-1] if len(chain) > 1 else None,
            "depends_on": [v.resolve(t, r)[0] or f"!{t}" for t in links_in(fm.get("depends-on"))],
            "implements": fm.get("implements"),
        }

    rows = [row(r) for r in members]
    rows.sort(key=lambda x: (x["current"] is not None, x["note"]))  # current notes first
    return {"domain": domain, "notes": rows, "pulled_in_by_depends_on": [{"note": k, "via": w} for k, w in pulled.items()]}


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("command", choices=["stats", "lint", "query", "current"])
    ap.add_argument("vault", type=Path)
    ap.add_argument("note", nargs="?")
    ap.add_argument("--domain")
    ap.add_argument("--depth", type=int, default=1)
    ap.add_argument("--limit", type=int, default=5)
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args()
    v = Vault(a.vault.resolve())

    if a.command == "stats":
        out = cmd_stats(v)
    elif a.command == "lint":
        out = cmd_lint(v, a.limit)
    elif a.command == "query":
        if not a.domain:
            sys.exit("query needs --domain")
        out = cmd_query(v, a.domain, a.depth)
    else:
        rid = v.find(a.note or "")
        if not rid:
            sys.exit(f"note not found: {a.note}")
        out = {"chain": v.current(rid)}

    if a.json:
        print(json.dumps(out, ensure_ascii=False, indent=2))
        return
    if a.command == "query":
        print(f"# domain: {out['domain']}  ({len(out['notes'])} notes)")
        for r in out["notes"]:
            tag = f"  ⤳ superseded, current = {r['current']}" if r["current"] else ""
            print(f"- {r['note']}  [{r['status']}]{tag}")
            for d in r["depends_on"]:
                print(f"    depends-on {d}")
            if r["implements"]:
                print(f"    implements {r['implements']}")
        for p in out["pulled_in_by_depends_on"]:
            print(f"+ {p['note']}  (pulled in by {p['via']})")
    elif a.command == "current":
        print("  →  ".join(out["chain"]))
    elif not out:
        print("no issues")
    else:
        for k, val in out.items():
            print(f"{k}: {val}")


if __name__ == "__main__":
    main()

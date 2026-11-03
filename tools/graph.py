#!/usr/bin/env python3
"""Query and lint an Obsidian vault as a typed-edge knowledge graph.

  node  = one markdown note; frontmatter = properties
  edges = moc (hub) · depends-on · superseded-by (time axis) · implements (code, scalar)

usage:
  graph.py stats   <vault>
  graph.py lint    <vault> [--limit N] [--update-baseline]
  graph.py query   <vault> --domain <slug> [--depth N]
  graph.py current <vault> <note>
  add --json to any command for machine-readable output
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
from collections import defaultdict
from pathlib import Path

SKIP_DIRS = {".git", ".obsidian", "node_modules", ".trash"}
DEFAULT_EXCLUDE = "claude-config,.work"   # agent config and scratch — not knowledge notes
EDGE_KEYS = ("moc", "depends-on", "superseded-by")
WIKILINK = re.compile(r"\[\[([^\]|#]+)(?:#[^\]|]*)?(?:\|[^\]]*)?\]\]")
MDLINK = re.compile(r"\]\(<?([^)#<>\s]+\.md)>?(?:#[^)]*)?\)")   # [title](note.md) — Obsidian treats it as a link too
NULLS = {"", "null", "~", "none"}
BASELINE = ".graph-lint-baseline.json"   # broken body links that already existed — lint reports only new ones


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
    def __init__(self, root: Path, exclude: str = DEFAULT_EXCLUDE):
        self.root = root
        excluded = {e.strip().strip("/") for e in exclude.split(",") if e.strip()}
        self.notes: dict[str, dict] = {}          # relpath (no .md) -> note
        self.by_stem: dict[str, list[str]] = defaultdict(list)   # lowercased stem -> every .md Obsidian can link to
        for p in sorted(root.rglob("*.md")):
            parts = p.relative_to(root).parts
            if SKIP_DIRS & set(parts) or any(x.startswith(".") for x in parts[:-1]):
                continue
            self.by_stem[p.stem.lower()].append(p.relative_to(root).with_suffix("").as_posix())
            if any("/".join(parts).startswith(e + "/") for e in excluded):
                continue
            fm, body = parse_frontmatter(p.read_text(encoding="utf-8", errors="ignore"))
            rel = p.relative_to(root).with_suffix("").as_posix()
            md = []
            for m in MDLINK.finditer(body):
                t = m.group(1)
                if "://" in t:
                    continue
                md.append(os.path.normpath(os.path.join(os.path.dirname(rel), t)).removesuffix(".md"))
            self.notes[rel] = {"id": rel, "fm": fm, "body_links": links_in(body) + md}
        self.edges: list[tuple[str, str, str]] = []  # (src, kind, raw target)
        for rel, n in self.notes.items():
            for k in EDGE_KEYS:
                for t in links_in(n["fm"].get(k)):
                    self.edges.append((rel, k, t))

    def resolve(self, target: str, src: str | None = None, kind: str | None = None) -> tuple[str | None, str]:
        """Return (note id, status) the way Obsidian resolves a link (app `getLinkpathDest`).

        Case-insensitive. An exact vault path wins; otherwise candidates under the linking note's folder
        come first, then the rest, each shortest path first.
        status: ok | broken | ambiguous — ambiguous = several files share the name and the winner is not in
        the linking note's own folder, so a new file elsewhere can silently retarget the link.
        """
        t = target.strip().removesuffix(".md").lower()
        if not t or t.startswith("/"):
            return None, "broken"
        src_dir = src.rsplit("/", 1)[0].lower() if src and "/" in src else ""
        if t.startswith("./") or t.startswith("../"):
            t = os.path.normpath(os.path.join(src_dir, t)).lower()
        cands = [c for c in self.by_stem.get(t.rsplit("/", 1)[-1], []) if c.lower() == t or c.lower().endswith("/" + t)]
        if not cands:
            return None, "broken"
        exact = [c for c in cands if c.lower() == t]
        if exact or len(cands) == 1:
            return (exact or cands)[0], "ok"
        inside = sorted((c for c in cands if c.lower().startswith(src_dir)), key=len)
        outside = sorted((c for c in cands if not c.lower().startswith(src_dir)), key=len)
        win = (inside + outside)[0]
        same_dir = src is not None and win.rsplit("/", 1)[0].lower() == src_dir and "/" in win
        return win, "ok" if same_dir else "ambiguous"

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
            if rid is None or rid in seen or rid not in self.notes:
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
        if rid:
            resolved[kind] += 1
            linked.update({src, rid})
        if status != "ok":
            problems[status] += 1
    for rel, n in v.notes.items():
        for t in n["body_links"]:
            rid, status = v.resolve(t, rel)
            if rid:
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


def cmd_lint(v: Vault, limit: int, update_baseline: bool = False) -> dict:
    issues = defaultdict(list)
    broken_body = []
    for src, kind, t in v.edges:
        rid, status = v.resolve(t, src, kind)
        if status != "ok":
            issues[f"{status}_{kind}"].append(f"{src} -> [[{t}]]")
    for rel, n in v.notes.items():
        # body links: ambiguous always; broken only when new (old ones are examples, images, placeholders —
        # they sit in the baseline so a rename done with `mv` still shows up)
        for t in n["body_links"]:
            status = v.resolve(t, rel)[1]
            if status != "ok":
                (issues["ambiguous_body"] if status == "ambiguous" else broken_body).append(f"{rel} -> [[{t}]]")
        if "related" in n["fm"]:
            issues["related_field"].append(rel)
        chain = v.current(rel)
        if chain[-1].startswith("!cycle"):
            issues["superseded_cycle"].append(" -> ".join(chain))
    base = v.root / BASELINE
    if update_baseline:
        base.write_text(json.dumps(sorted(set(broken_body)), ensure_ascii=False, indent=0) + "\n", encoding="utf-8")
    known = set(json.loads(base.read_text(encoding="utf-8"))) if base.exists() else set()
    issues["broken_body_new"] = [x for x in broken_body if x not in known]
    issues = {k: xs for k, xs in issues.items() if xs}
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
                if rid in v.notes and rid not in members and rid not in pulled:
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
    ap.add_argument("--update-baseline", action="store_true", help=f"lint: record current broken body links in <vault>/{BASELINE}")
    ap.add_argument("--exclude", default=DEFAULT_EXCLUDE, help="comma-separated top folders to skip (default: %(default)s)")
    a = ap.parse_args()
    v = Vault(a.vault.resolve(), a.exclude)

    if a.command == "stats":
        out = cmd_stats(v)
    elif a.command == "lint":
        out = cmd_lint(v, a.limit, a.update_baseline)
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

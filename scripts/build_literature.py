"""Merge per-topic literature JSON files into docs/literature/.

    python scripts/build_literature.py <dir with *_*.json>

Writes papers.json, papers.csv, references.bib and README.md (index by cluster,
sorted by relevance then year). Deduplicates by DOI, OpenAlex id, then
normalised title; a paper found by several searches keeps every cluster.
"""
import csv
import glob
import json
import os
import re
import sys
import unicodedata

CLUSTERS = {
    "A": "Single-robot radiation source search and localization",
    "B": "Multi-robot / multi-agent radiation search",
    "C": "Nuclear robotics and radiation exposure of robots",
    "D": "Safe and constrained reinforcement learning (single- and multi-agent)",
    "E": "Resource-constrained exploration, active sensing and return-to-base",
    "F": "Analogous hazardous-source search and estimation (gas, CBRN, fire, calibration)",
}
OUT = "docs/literature"


def norm_title(t):
    t = unicodedata.normalize("NFKD", t or "").encode("ascii", "ignore").decode().lower()
    return re.sub(r"[^a-z0-9]+", " ", t).strip()


def norm_doi(d):
    if not d:
        return None
    d = d.strip().lower()
    d = re.sub(r"^https?://(dx\.)?doi\.org/", "", d)
    return d or None


def norm_oa(x):
    if not x:
        return None
    m = re.search(r"(W\d+)", str(x))
    return m.group(1) if m else None


def bib_key(p, used):
    a = re.sub(r"[^A-Za-z]", "", unicodedata.normalize("NFKD", (p.get("authors") or "anon").split()[0])
               .encode("ascii", "ignore").decode()) or "anon"
    w = next((w for w in norm_title(p["title"]).split() if len(w) > 3), "paper")
    k = f"{a.lower()}{p.get('year') or ''}{w}"
    base, i = k, 2
    while k in used:
        k = f"{base}{i}"; i += 1
    used.add(k)
    return k


def bib_escape(s):
    return (s or "").replace("&", r"\&").replace("%", r"\%").replace("_", r"\_").replace("#", r"\#")


def main(src):
    items = []
    for f in sorted(glob.glob(os.path.join(src, "*_*.json"))):
        with open(f) as fh:
            data = json.load(fh)
        for p in data:
            p["_file"] = os.path.basename(f)
            items.append(p)
    merged, by_key = [], {}
    for p in items:
        keys = [("doi", norm_doi(p.get("doi"))), ("oa", norm_oa(p.get("openalex_id"))),
                ("t", norm_title(p.get("title")))]
        hit = next((by_key[k] for k in keys if k[1] and k in by_key), None)
        if hit is None:
            p["clusters"] = [p.get("cluster")]
            p["topics"] = list(dict.fromkeys(p.get("topics") or []))
            merged.append(p)
            hit = p
        else:
            if p.get("cluster") not in hit["clusters"]:
                hit["clusters"].append(p.get("cluster"))
            hit["topics"] = list(dict.fromkeys((hit.get("topics") or []) + (p.get("topics") or [])))
            hit["relevance"] = max(int(hit.get("relevance") or 1), int(p.get("relevance") or 1))
            for k in ("doi", "openalex_id", "url", "venue", "cited_by_count"):
                hit[k] = hit.get(k) or p.get(k)
        for k in keys:
            if k[1]:
                by_key[k] = hit
    for p in merged:
        p["doi"] = norm_doi(p.get("doi"))
        p["openalex_id"] = norm_oa(p.get("openalex_id"))
        p["relevance"] = int(p.get("relevance") or 1)
        p.pop("cluster", None); p.pop("_file", None)
        if not p.get("url"):
            p["url"] = (f"https://doi.org/{p['doi']}" if p["doi"]
                        else f"https://openalex.org/{p['openalex_id']}" if p["openalex_id"] else None)
    merged.sort(key=lambda p: (min(p["clusters"]), -p["relevance"], -(p.get("year") or 0)))
    used = set()
    for i, p in enumerate(merged, 1):
        p["id"] = f"P{i:03d}"
        p["bibkey"] = bib_key(p, used)

    os.makedirs(OUT, exist_ok=True)
    with open(f"{OUT}/papers.json", "w") as f:
        json.dump(merged, f, indent=1, ensure_ascii=False)
    cols = ["id", "bibkey", "clusters", "relevance", "year", "authors", "title", "venue", "doi",
            "openalex_id", "url", "cited_by_count", "topics", "summary", "relation"]
    with open(f"{OUT}/papers.csv", "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(cols)
        for p in merged:
            w.writerow([";".join(p[c]) if c in ("clusters", "topics") else p.get(c) for c in cols])
    with open(f"{OUT}/references.bib", "w") as f:
        for p in merged:
            f.write(f"@article{{{p['bibkey']},\n  title = {{{bib_escape(p['title'])}}},\n"
                    f"  author = {{{bib_escape(p.get('authors'))}}},\n  year = {{{p.get('year')}}},\n"
                    f"  journal = {{{bib_escape(p.get('venue'))}}},\n")
            if p.get("doi"):
                f.write(f"  doi = {{{p['doi']}}},\n")
            if p.get("url"):
                f.write(f"  url = {{{p['url']}}},\n")
            f.write(f"  note = {{Clusters {', '.join(p['clusters'])}; relevance {p['relevance']}; "
                    f"OpenAlex {p.get('openalex_id')}}}\n}}\n\n")

    n = len(merged)
    lines = ["# Literature library", "",
             f"{n} papers, every one returned by a scholarly database search (OpenAlex and others) with "
             "an OpenAlex id or DOI. Summaries are based on titles and abstracts only; read the paper "
             "before citing a detail.", "",
             "Files: `papers.csv` (spreadsheet), `papers.json` (full records), `references.bib` (BibTeX; "
             "authors are first author + et al., complete them before submission).", "",
             "Relevance: 3 = very close to this thesis, 2 = related method or setting, 1 = background.", "",
             "| Cluster | Topic | Papers | Relevance 3 |", "|---|---|---|---|"]
    for c, name in CLUSTERS.items():
        ps = [p for p in merged if c in p["clusters"]]
        lines.append(f"| {c} | {name} | {len(ps)} | {sum(p['relevance'] == 3 for p in ps)} |")
    for c, name in CLUSTERS.items():
        ps = [p for p in merged if min(p["clusters"]) == c]
        if not ps:
            continue
        lines += ["", f"## {c}. {name}", "",
                  "| ID | Rel. | Year | Paper | How it relates to this thesis |", "|---|---|---|---|---|"]
        for p in ps:
            link = p.get("url") or ""
            t = (p["title"] or "").replace("|", "/")
            other = [x for x in p["clusters"] if x != c]
            tag = f" (also {', '.join(other)})" if other else ""
            lines.append(f"| {p['id']} | {p['relevance']} | {p.get('year')} | [{t}]({link}), "
                         f"{p.get('authors')}, *{(p.get('venue') or '').replace('|', '/')}*{tag} | "
                         f"{(p.get('relation') or '').replace('|', '/')} |")
    with open(f"{OUT}/README.md", "w") as f:
        f.write("\n".join(lines) + "\n")
    print(f"{len(items)} records -> {n} unique papers")
    for c in CLUSTERS:
        print(c, sum(c in p["clusters"] for p in merged))


if __name__ == "__main__":
    main(sys.argv[1])

"""Second-round literature search: citation snowballing + keyword queries (Semantic Scholar API).

    python scripts/snowball_literature.py <out.json> [--seeds-min-relevance 3]

Seeds = papers in docs/literature/papers.json with relevance >= the threshold.
For each seed: its references and the works citing it. Plus keyword searches.
Candidates already in the library are dropped. Each candidate gets a keyword score
from title + abstract; the output (sorted by score) is screened afterwards.
Progress is checkpointed to <out.json>.partial, so a stopped run resumes.
(OpenAlex was the first choice, but its shared free daily budget ran out; no API key is used.)
"""
import argparse
import json
import re
import time

import requests

S2 = "https://api.semanticscholar.org/graph/v1"
UA = {"User-Agent": "radsearch-literature-review"}
F = "title,year,abstract,externalIds,venue,citationCount,publicationTypes"

QUERIES = [
    "radiation source search robot dose", "radioactive source localization multi-robot",
    "radiation dose aware robot path planning", "robot radiation exposure constraint exploration",
    "nuclear robot cumulative dose", "radiation mapping mobile robot uncertainty",
    "gamma source localization reinforcement learning", "radiological search UAV",
    "multi-agent reinforcement learning source localization", "hazardous environment robot attrition",
    "risk-aware multi-robot exploration", "energy constrained exploration return to base",
    "safe multi-agent reinforcement learning constraint", "constrained reinforcement learning budget state augmentation",
    "action masking safe reinforcement learning", "chance constrained reinforcement learning",
    "safe exploration unknown constraints Gaussian process", "information gathering hazard robot failure",
    "gas source localization multi-robot reinforcement learning", "model discrepancy Bayesian calibration overconfidence",
    "particle filter source term estimation model error", "CBRN robot",
    "radiation tolerant robot electronics total ionizing dose", "Fukushima robot radiation",
    "orienteering survival probability robot team",
]
KEYS = {
    3: ["radiation", "radioactive", "gamma", "dose", "nuclear", "ionizing", "ionising"],
    2: ["multi-robot", "multi-agent", "multirobot", "team", "swarm", "hazard", "exposure", "budget",
        "return", "safe", "constraint", "risk", "source localization", "source localisation",
        "source term", "source search", "particle filter", "attrition", "survival"],
    1: ["reinforcement learning", "exploration", "information gain", "mutual information", "infotaxis",
        "uncertainty", "calibration", "discrepancy", "energy", "battery", "cvar", "chance"],
}
_last = [0.0]


def get(url, params=None):
    for i in range(8):
        wait = 1.3 - (time.time() - _last[0])
        if wait > 0:
            time.sleep(wait)
        _last[0] = time.time()
        try:
            r = requests.get(url, params=params, headers=UA, timeout=30)
        except requests.RequestException:
            time.sleep(3); continue
        if r.status_code == 429:
            time.sleep(4 * (i + 1)); continue
        if r.status_code == 404:
            return None
        if r.ok:
            return r.json()
        time.sleep(2)
    return None


def norm(s):
    return re.sub(r"[^a-z0-9]+", " ", (s or "").lower()).strip()


def score(text):
    t = text.lower()
    return sum(wt for wt, ks in KEYS.items() for k in ks if k in t)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("out")
    ap.add_argument("--seeds-min-relevance", type=int, default=3)
    a = ap.parse_args()
    lib = json.load(open("docs/literature/papers.json"))
    have_doi = {(p.get("doi") or "").lower() for p in lib}
    have_t = {norm(p["title"]) for p in lib}
    seeds = [p for p in lib if p.get("relevance", 0) >= a.seeds_min_relevance]
    ck = a.out + ".partial"
    try:
        st = json.load(open(ck)); cand, done = st["cand"], set(st["done"])
        print(f"resuming: {len(done)} steps done, {len(cand)} candidates", flush=True)
    except (OSError, ValueError):
        cand, done = {}, set()

    def save():
        json.dump(dict(cand=cand, done=sorted(done)), open(ck, "w"))

    def add(w, how):
        if not w or not w.get("title") or not w.get("paperId"):
            return
        ext = w.get("externalIds") or {}
        doi = (ext.get("DOI") or "").lower() or None
        if not doi and ext.get("ArXiv"):
            doi = f"10.48550/arxiv.{ext['ArXiv']}".lower()
        if (doi and doi in have_doi) or norm(w["title"]) in have_t:
            return
        c = cand.setdefault(w["paperId"], dict(s2_id=w["paperId"], doi=doi, arxiv=ext.get("ArXiv"),
                                               title=w["title"], year=w.get("year"), venue=w.get("venue"),
                                               cited_by_count=w.get("citationCount"),
                                               types=w.get("publicationTypes"),
                                               abstract=(w.get("abstract") or "")[:2500], found_via=[]))
        if how not in c["found_via"]:
            c["found_via"].append(how)

    for i, p in enumerate(seeds, 1):
        if p["id"] in done:
            continue
        pid = None
        if p.get("doi"):
            j = get(f"{S2}/paper/DOI:{p['doi']}", {"fields": "paperId"})
            pid = (j or {}).get("paperId")
        if not pid:
            j = get(f"{S2}/paper/search/match", {"query": p["title"], "fields": "paperId,title"})
            d = ((j or {}).get("data") or [{}])[0]
            if norm(d.get("title"))[:50] == norm(p["title"])[:50]:
                pid = d.get("paperId")
        if pid:
            for rel, key in (("references", "citedPaper"), ("citations", "citingPaper")):
                j = get(f"{S2}/paper/{pid}/{rel}", {"fields": F, "limit": 100})
                for x in (j or {}).get("data") or []:
                    add(x.get(key), f"{'ref-of' if rel == 'references' else 'cites'}:{p['id']}")
        done.add(p["id"]); save()
        print(f"seed {i}/{len(seeds)} {p['id']} {'ok' if pid else 'not found'} -> {len(cand)} candidates", flush=True)
    for q in QUERIES:
        if "q:" + q in done:
            continue
        j = get(f"{S2}/paper/search", {"query": q, "fields": F, "limit": 50, "year": "2010-"})
        for x in (j or {}).get("data") or []:
            add(x, f"query:{q}")
        done.add("q:" + q); save()
        print(f"query '{q}' -> {len(cand)}", flush=True)
    for c in cand.values():
        c["score"] = score(f"{c['title']} {c['abstract']}") + 2 * min(len(c["found_via"]) - 1, 4)
    out = sorted(cand.values(), key=lambda c: -c["score"])
    json.dump(out, open(a.out, "w"), indent=1, ensure_ascii=False)
    print(f"{len(out)} candidates; score>=8: {sum(c['score'] >= 8 for c in out)}; "
          f"score>=12: {sum(c['score'] >= 12 for c in out)}", flush=True)


if __name__ == "__main__":
    main()

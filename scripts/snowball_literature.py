"""Second-round literature search: citation snowballing + keyword queries on OpenAlex.

    python scripts/snowball_literature.py <out.json> [--seeds-min-relevance 3]

Seeds = papers in docs/literature/papers.json with relevance >= the threshold.
For each seed: its references and the works citing it. Plus keyword searches.
Candidates already in the library are dropped. Each candidate gets a keyword score
from its title + abstract; the output (sorted by score) is screened by hand / agents.
"""
import argparse
import json
import re
import time

import requests

API = "https://api.openalex.org/works"
UA = {"User-Agent": "radsearch-literature-review"}
FIELDS = "id,doi,title,publication_year,primary_location,cited_by_count,abstract_inverted_index,referenced_works,type"

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
    "particle filter source term estimation model error", "CBRN robot", "radiation tolerant robot electronics total ionizing dose",
    "Fukushima robot radiation", "orienteering survival probability robot team",
]
KEYS = {
    3: ["radiation", "radioactive", "gamma", "dose", "nuclear", "ionizing", "ionising"],
    2: ["multi-robot", "multi-agent", "multirobot", "team", "swarm", "hazard", "exposure", "budget",
        "return", "safe", "constraint", "risk", "source localization", "source localisation",
        "source term", "source search", "particle filter", "attrition", "survival"],
    1: ["reinforcement learning", "exploration", "information gain", "mutual information", "infotaxis",
        "uncertainty", "calibration", "discrepancy", "energy", "battery", "cvar", "chance"],
}


def get(params=None, url=API):
    for i in range(5):
        try:
            r = requests.get(url, params=params, headers=UA, timeout=60)
            if r.status_code == 429:
                time.sleep(5 * (i + 1)); continue
            if r.ok:
                return r.json()
        except requests.RequestException:
            pass
        time.sleep(2 * (i + 1))
    return None


def abstract(w):
    inv = w.get("abstract_inverted_index") or {}
    pos = sorted((i, word) for word, ix in inv.items() for i in ix)
    return " ".join(word for _, word in pos)


def score(text):
    t = text.lower()
    return sum(wt for wt, ks in KEYS.items() for k in ks if k in t)


def norm(s):
    return re.sub(r"[^a-z0-9]+", " ", (s or "").lower()).strip()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("out")
    ap.add_argument("--seeds-min-relevance", type=int, default=3)
    a = ap.parse_args()
    lib = json.load(open("docs/literature/papers.json"))
    have_oa = {p.get("openalex_id") for p in lib}
    have_doi = {(p.get("doi") or "").lower() for p in lib}
    have_t = {norm(p["title"]) for p in lib}
    seeds = [p for p in lib if p.get("relevance", 0) >= a.seeds_min_relevance and p.get("openalex_id")]
    cand = {}

    def add(w, how):
        if not w or not w.get("title"):
            return
        oid = w["id"].split("/")[-1]
        doi = (w.get("doi") or "").replace("https://doi.org/", "").lower()
        if oid in have_oa or (doi and doi in have_doi) or norm(w["title"]) in have_t:
            return
        c = cand.setdefault(oid, dict(openalex_id=oid, doi=doi or None, title=w["title"],
                                      year=w.get("publication_year"), type=w.get("type"),
                                      venue=((w.get("primary_location") or {}).get("source") or {}).get("display_name"),
                                      cited_by_count=w.get("cited_by_count"), abstract=abstract(w)[:2500], found_via=[]))
        c["found_via"].append(how)

    for i, p in enumerate(seeds, 1):
        oid = p["openalex_id"]
        w = get(url=f"{API}/{oid}", params={"select": "referenced_works"})
        refs = (w or {}).get("referenced_works") or []
        for k in range(0, len(refs), 50):
            ids = "|".join(r.split("/")[-1] for r in refs[k:k + 50])
            j = get({"filter": f"openalex:{ids}", "per-page": 50, "select": FIELDS})
            for x in (j or {}).get("results", []):
                add(x, f"ref-of:{p['id']}")
        j = get({"filter": f"cites:{oid}", "per-page": 100, "select": FIELDS, "sort": "cited_by_count:desc"})
        for x in (j or {}).get("results", []):
            add(x, f"cites:{p['id']}")
        print(f"seed {i}/{len(seeds)} {p['id']} -> {len(cand)} candidates", flush=True)
    for q in QUERIES:
        j = get({"search": q, "per-page": 50, "select": FIELDS, "filter": "publication_year:>2009"})
        for x in (j or {}).get("results", []):
            add(x, f"query:{q}")
    for c in cand.values():
        c["score"] = score(f"{c['title']} {c['abstract']}") + 2 * min(len(c["found_via"]) - 1, 4)
    out = sorted(cand.values(), key=lambda c: -c["score"])
    json.dump(out, open(a.out, "w"), indent=1, ensure_ascii=False)
    print(f"{len(out)} candidates; score>=8: {sum(c['score'] >= 8 for c in out)}; score>=12: {sum(c['score'] >= 12 for c in out)}")


if __name__ == "__main__":
    main()

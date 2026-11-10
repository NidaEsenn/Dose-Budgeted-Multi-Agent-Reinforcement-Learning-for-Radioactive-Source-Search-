"""Download open-access full texts for docs/literature/papers.json and extract
the parts that state problems, limitations and future work.

    python scripts/fetch_fulltexts.py <out_dir> [--only P001,P002] [--workers 6]

For every paper it tries, in order: OpenAlex locations (pdf_url / landing page),
Semantic Scholar openAccessPdf, an arXiv title match, and CORE. PDFs and texts go
to <out_dir> (not committed: licences vary). Writes <out_dir>/index.json with, per
paper, the source used and the extracted passages:
  abstract, conclusion, limitations, future_work, discussion, plus every sentence
  containing a cue word ("future work", "limitation", "open problem", "remains", ...).
"""
import argparse
import concurrent.futures as cf
import json
import os
import re
import subprocess
import time
import urllib.parse

import requests

UA = {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/124.0 Safari/537.36 radsearch-literature-review"}
CUES = re.compile(r"(future (work|research|stud|direction)|limitation|open (problem|question|issue|challenge)|"
                  r"remain(s|ing)? (a |an )?(open|challeng|unsolved|unexplored|unaddressed)|not (yet )?(been )?"
                  r"(addressed|considered|studied|explored|investigated)|beyond the scope|we (plan|intend|leave)|"
                  r"left for|is (still )?lacking|has not been|have not been|drawback|shortcoming|weakness|"
                  r"assum(e|es|ed|ption)s? (that )?(the )?(radiation|source|field|dose|known|perfect|static)|"
                  r"challenge(s)? (remain|include)|gap)", re.I)
SECTION = re.compile(r"^\s*(?:\d+(?:\.\d+)*\.?|[IVX]+\.)?\s*(abstract|introduction|related work|background|"
                     r"conclusions?|concluding remarks|summary and (?:future work|conclusions?)|future work|"
                     r"future (?:research|directions)|limitations?|discussion|conclusions? and future work|"
                     r"discussion and future work|acknowledge?ments?|references|bibliography)\s*$", re.I)


def get(url, **kw):
    for i in range(3):
        try:
            r = requests.get(url, headers=UA, timeout=40, allow_redirects=True, **kw)
            if r.status_code == 429:
                time.sleep(3 * (i + 1)); continue
            return r
        except requests.RequestException:
            time.sleep(2)
    return None


def candidates(p, rec):
    urls = []
    oa = p.get("openalex_id")
    if oa:
        r = get(f"https://api.openalex.org/works/{oa}")
        if r is not None and r.ok:
            w = r.json()
            inv = w.get("abstract_inverted_index") or {}
            if inv:
                pos = sorted((i, word) for word, ix in inv.items() for i in ix)
                rec["oa_abstract"] = " ".join(word for _, word in pos)
            for loc in ([w.get("best_oa_location")] + (w.get("locations") or [])):
                if loc:
                    urls += [loc.get("pdf_url"), loc.get("landing_page_url")]
            ids = w.get("ids") or {}
            for loc in w.get("locations") or []:
                lp = (loc or {}).get("landing_page_url") or ""
                m = re.search(r"arxiv\.org/abs/([\w.\-/]+)", lp)
                if m:
                    urls.insert(0, f"https://arxiv.org/pdf/{m.group(1)}")
    doi = p.get("doi") or ""
    if p.get("arxiv"):
        urls.insert(0, f"https://arxiv.org/pdf/{p['arxiv']}")
    if p.get("s2_id") and not doi:
        r = get(f"https://api.semanticscholar.org/graph/v1/paper/{p['s2_id']}?fields=openAccessPdf,externalIds")
        if r is not None and r.ok:
            j = r.json()
            u = (j.get("openAccessPdf") or {}).get("url")
            if u:
                urls.append(u)
    m = re.search(r"arxiv\.(\d{4}\.\d{4,5})", doi)
    if m:
        urls.insert(0, f"https://arxiv.org/pdf/{m.group(1)}")
    if doi:
        r = get(f"https://api.semanticscholar.org/graph/v1/paper/DOI:{doi}?fields=openAccessPdf,externalIds")
        if r is not None and r.ok:
            j = r.json()
            u = (j.get("openAccessPdf") or {}).get("url")
            if u:
                urls.append(u)
            ax = (j.get("externalIds") or {}).get("ArXiv")
            if ax:
                urls.insert(0, f"https://arxiv.org/pdf/{ax}")
    # arXiv title search
    t = p.get("title") or ""
    q = urllib.parse.quote(f'ti:"{t[:180]}"')
    r = get(f"https://export.arxiv.org/api/query?search_query={q}&max_results=3")
    if r is not None and r.ok:
        for aid, title in re.findall(r"<id>http://arxiv.org/abs/([^<]+)</id>.*?<title>([^<]+)</title>", r.text, re.S):
            if _norm(title)[:60] == _norm(t)[:60]:
                urls.append(f"https://arxiv.org/pdf/{aid}")
    seen, out = set(), []
    for u in urls:
        if u and u not in seen:
            seen.add(u); out.append(u)
    return out


def _norm(s):
    return re.sub(r"[^a-z0-9]+", " ", (s or "").lower()).strip()


def fetch_pdf(urls, path):
    for u in urls:
        r = get(u)
        if r is None or not r.ok:
            continue
        ct = r.headers.get("content-type", "")
        body = r.content
        if body[:4] == b"%PDF":
            open(path, "wb").write(body)
            return u, "pdf"
        if "html" in ct:
            # an HTML landing page: look for a citation_pdf_url or a PDF link
            m = re.search(r'citation_pdf_url"\s+content="([^"]+)"', r.text) or \
                re.search(r'href="([^"]+\.pdf[^"]*)"', r.text)
            if m:
                pu = urllib.parse.urljoin(r.url, m.group(1).replace("&amp;", "&"))
                r2 = get(pu)
                if r2 is not None and r2.ok and r2.content[:4] == b"%PDF":
                    open(path, "wb").write(r2.content)
                    return pu, "pdf"
            text = re.sub(r"<script.*?</script>|<style.*?</style>", " ", r.text, flags=re.S | re.I)
            text = re.sub(r"<[^>]+>", "\n", text)
            if len(text) > 15000 and re.search(r"conclusion", text, re.I):
                open(path[:-4] + ".txt", "w").write(text)
                return r.url, "html"
    return None, None


def sections(text):
    lines = [l.strip() for l in text.splitlines()]
    out, cur = {}, None
    for l in lines:
        m = SECTION.match(l)
        if m and len(l) < 60:
            name = m.group(1).lower()
            cur = ("conclusion" if name.startswith(("conclu", "summary")) else
                   "future_work" if name.startswith("future") else
                   "limitations" if name.startswith("limitation") else
                   "discussion" if name.startswith("discussion") else
                   "abstract" if name == "abstract" else
                   None if name.startswith(("ackno", "refer", "biblio")) else "other")
            if "future work" in name:
                cur = "conclusion"
            continue
        if cur and cur != "other" and l:
            out.setdefault(cur, []).append(l)
    res = {k: re.sub(r"\s+", " ", " ".join(v))[:6000] for k, v in out.items()}
    body = re.sub(r"\s+", " ", " ".join(lines))
    body = re.split(r"\b(References|REFERENCES|Bibliography)\b", body)[0]
    sents = re.split(r"(?<=[.!?])\s+", body)
    res["cue_sentences"] = [s[:500] for s in sents if CUES.search(s) and 40 < len(s) < 800][:60]
    return res


def process(p, out_dir):
    pid = p["id"]
    pdf = os.path.join(out_dir, f"{pid}.pdf")
    txt = os.path.join(out_dir, f"{pid}.txt")
    rec = dict(id=pid, title=p["title"], year=p.get("year"), clusters=p.get("clusters"), relevance=p.get("relevance"))
    if not os.path.exists(txt):
        urls = candidates(p, rec)
        src, kind = fetch_pdf(urls, pdf)
        rec["tried"] = urls[:8]
        if kind == "pdf":
            subprocess.run(["pdftotext", pdf, txt], capture_output=True, timeout=120)
        rec["source"], rec["kind"] = src, kind
    else:
        rec["source"], rec["kind"] = "cached", "cached"
        old = getattr(process, "old", {}).get(pid, {})
        for k in ("oa_abstract", "tried"):
            if k in old:
                rec[k] = old[k]
    if os.path.exists(txt):
        text = open(txt, errors="ignore").read()
        rec["chars"] = len(text)
        rec.update(sections(text))
    return rec


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("out_dir")
    ap.add_argument("--only", default="")
    ap.add_argument("--workers", type=int, default=6)
    a = ap.parse_args()
    os.makedirs(a.out_dir, exist_ok=True)
    papers = json.load(open("docs/literature/papers.json"))
    if a.only:
        keep = set(a.only.split(","))
        papers = [p for p in papers if p["id"] in keep]
    idx_path = os.path.join(a.out_dir, "index.json")
    idx = {r["id"]: r for r in json.load(open(idx_path))} if os.path.exists(idx_path) else {}
    process.old = dict(idx)
    with cf.ThreadPoolExecutor(a.workers) as ex:
        futs = {ex.submit(process, p, a.out_dir): p["id"] for p in papers}
        for i, f in enumerate(cf.as_completed(futs), 1):
            try:
                r = f.result()
            except Exception as e:  # keep going
                r = dict(id=futs[f], error=str(e))
            idx[r["id"]] = r
            if i % 10 == 0:
                json.dump(list(idx.values()), open(idx_path, "w"), indent=1)
                print(f"{i}/{len(papers)}", flush=True)
    json.dump(sorted(idx.values(), key=lambda r: r["id"]), open(idx_path, "w"), indent=1)
    got = [r for r in idx.values() if r.get("chars")]
    print(f"full text for {len(got)}/{len(idx)} papers")


if __name__ == "__main__":
    main()

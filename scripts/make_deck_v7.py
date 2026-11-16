"""Midterm deck v7 (10-minute talk): built on the user's edited v5 deck (15 slides).

    python scripts/make_deck_v7.py IN.pptx docs/Safe_Cooperative_Radiation_Source_Search_v7.pptx

* The five algorithm slides (overview, filter, policies, safety layer, check) become ONE
  slide with docs/figures/alg_overview.png; the detailed ones move to the back as backups.
* Speaker notes from slide 5 on are shorter and conversational.
"""
import copy
import sys

from PIL import Image
from pptx import Presentation
from pptx.util import Emu

SRC, OUT = sys.argv[1], sys.argv[2]
p = Presentation(SRC)
V = list(p.slides)
S = lambda n: V[n - 1]                       # slide number in the input deck
by_id = lambda s, sid: next(sh for sh in s.shapes if sh.shape_id == sid)
by_text = lambda s, t: next(sh for sh in s.shapes if sh.has_text_frame and sh.text_frame.text.startswith(t))
LAYOUT = {l.name: l for l in p.slide_layouts}
LEFT, FULL_W = 548640, 11064240


def set_text(shape, text):
    para = shape.text_frame.paragraphs[0]
    if not para.runs:
        para.add_run()
    runs = para.runs
    runs[0].text = text
    for r in runs[1:]:
        r._r.getparent().remove(r._r)
    for extra in shape.text_frame.paragraphs[1:]:
        extra._p.getparent().remove(extra._p)


def notes(slide, text):
    ns = slide.notes_slide
    if ns.notes_placeholder is None:
        body = next(ph for ph in V[0].notes_slide.placeholders if ph.placeholder_format.type == 2)
        ns.shapes._spTree.append(copy.deepcopy(body._element))
    ns.notes_text_frame.text = text


def copy_shape(src_shape, dst_slide):
    el = copy.deepcopy(src_shape._element)
    used = [int(x) for x in dst_slide.shapes._spTree.xpath(".//p:cNvPr/@id")]
    el.xpath(".//p:cNvPr")[0].set("id", str(max(used + [1]) + 1))
    dst_slide.shapes._spTree.append(el)
    return dst_slide.shapes[-1]


def place(sh, left, top, width, height):
    sh.left, sh.top, sh.width, sh.height = (Emu(int(v)) for v in (left, top, width, height))


def card(slide, left, top, w, h, title, text, dark=False):
    src = S(10)                                  # results slide: light card 5/6/7, dark card 8/9/10
    ids = (8, 9, 10) if dark else (5, 6, 7)
    box, t, x = (copy_shape(by_id(src, i), slide) for i in ids)
    place(box, left, top, w, h)
    place(t, left + 228600, top + 110000, w - 457200, 320040)
    place(x, left + 228600, top + 450000, w - 457200, h - 500000)
    set_text(t, title)
    set_text(x, text)


def to_backup(slide):
    rel = next(r for r in slide.part.rels.values() if r.reltype.endswith("/slideLayout"))
    rel._target = LAYOUT["BACKUP"].part
    title = slide.shapes[0]
    title.top = Emu(365760)


# ------------------------------------------------------------------ the one algorithm slide
A = p.slides.add_slide(LAYOUT["CONTENT"])
for ph in list(A.placeholders):
    ph._element.getparent().remove(ph._element)
copy_shape(by_id(S(5), 2), A)
copy_shape(by_id(S(5), 41), A)
set_text(A.shapes[0], "How it works: estimate → decide → check, every 10 s")
path = "docs/figures/alg_overview.png"
iw, ih = Image.open(path).size
w = 10500000
h = int(w * ih / iw)
A.shapes.add_picture(path, Emu(LEFT + (FULL_W - w) // 2), Emu(1180000), Emu(w), Emu(h))
y = 1180000 + h + 120000
gap = 182880
cw = (FULL_W - 2 * gap) / 3
ch = 6250000 - y
card(A, LEFT, y, cw, ch, "Particle filter",
     "2,000 guesses of (x, y, strength), re-weighted after every reading. Declare when σ < 0.3 m.")
card(A, LEFT + cw + gap, y, cw, ch, "Policy: greedy rule or MAPPO",
     "Each robot acts on its own view. MAPPO-Lagrangian also puts a price on going over budget.")
card(A, LEFT + 2 * (cw + gap), y, cw, ch, "Reserve safety layer",
     "used + next step + way out ≤ 0.1 Gy, at the 97th percentile of 32 samples. If not: withdraw.", dark=True)
notes(A, "(~1 min 30 s)\n"
      "Every 10 seconds, three things happen.\n"
      "One, estimate. The team keeps 2,000 guesses of where the source is and how strong it is. After every reading, guesses "
      "that explain the counts get more weight. At the start the guesses are everywhere; at the end they sit on the source. "
      "When they are tight enough, the team names the source.\n"
      "Two, decide. Each robot picks its next move from its own view. I compare a simple greedy rule, which goes where it learns "
      "the most, with learning: MAPPO, one shared network for all robots, and MAPPO-Lagrangian, which also puts a price on going over budget.\n"
      "Three, check. This is my safety layer. Dose so far, plus the next step, plus the way home, must stay under 0.1 gray. "
      "The robot doesn't know the source exactly, so it checks 32 possible sources and plans for a bad one, the 97th percentile. "
      "Here, the bad case is over budget, so the robot withdraws. It always may.\n"
      "Details are in the backup slides.")

# ------------------------------------------------------------------ shorter notes, slides 10-13 of the input
notes(S(10), "(~1 min 15 s)\n"
      "Pilot results from the university cluster. Same 1,000 test missions for every method.\n"
      "Without safety, robots go over budget a lot: 30% for greedy, 19% for MAPPO.\n"
      "Three points. First, the withdraw action fixed the timid robots: MAPPO-Lagrangian went from 10% success to almost 80%, at 4.3% failures.\n"
      "Second, my reserve rule is still the best: 85% success at 4.2% failures. Planning for the average case instead gives 15% failures, so the bad case matters.\n"
      "Third, the learned team gives fewer wrong answers: 7% versus 12%.\n"
      "MAPPO with my safety layer is still training.")
notes(S(11), "(~45 s)\n"
      "Each dot is one setting of the safety layer. Left is safer, up finds the source more often.\n"
      "No setting beats my reference on both. The safest one almost never fails, but finds the source only 65% of the time.\n"
      "So being safer costs success. The goal for learning: move this curve up and to the left.")
notes(S(12), "(~1 min)\n"
      "Why does the rule need so much slack? I checked if its bad case is really a bad case.\n"
      "If it were honest, the true dose would go above the 97th percentile only 3% of the time. It's 18%.\n"
      "And it gets worse during the mission: the filter counts linked errors as new evidence, so it becomes too sure of itself.\n"
      "We're still at about 4% failures only because the misses are small. That's fragile, and it's what my main method will fix.")
notes(S(13), "(~1 min)\n"
      "My plan. The pilot is almost done.\n"
      "Next, the main method: a safety layer that knows the guess is overconfident and corrects for it.\n"
      "Then the full study, with 10 runs per method and over 3,000 test missions, enough to show we're really below 5%.\n"
      "Then robots with different budgets: who should take the risky readings? Then a real-robot test, and writing.\n"
      "To close: safe search means every robot keeps enough dose to come home. Thank you.")

# ------------------------------------------------------------------ backups: detailed algorithm slides
for n, title in [(6, "Backup: how the team estimates the source"), (7, "Backup: how the robots decide where to go"),
                 (8, "Backup: the safety layer"), (9, "Backup: the safety check, step by step")]:
    s = S(n)
    to_backup(s)
    set_text(s.shapes[0], title.split(": ", 1)[1].capitalize())
notes(S(6), "Backup. Particle filter: 2,000 guesses of (x, y, strength). Each reading re-weights them, in up to 3 gentle stages, "
      "then likely guesses are copied with a small jitter. Declare when the spread is under 0.3 m. Limitation: readings are treated as independent.")
notes(S(7), "Backup. Greedy: information gain minus a dose penalty, robots pick in turn. MAPPO: shared actor, critic sees the full "
      "state only in training, PPO. MAPPO-Lagrangian: cost 1 when a robot goes over budget, price λ rises while failures are above 5%.")
notes(S(8), "Backup. The rule: used + next step + way out ≤ 0.1 Gy, at the 97th percentile of 32 samples. "
      "The robot in the plot withdraws and leaves with 0.065 Gy: careful, not a guarantee.")
notes(S(9), "Backup. Same robot, 20 s apart. Early: even the bad case is far under budget. Near the source the 32 predictions "
      "spread out, the 97th percentile passes the budget, and the robot withdraws.")
set_text(by_text(S(15), "The 13 safety-layer settings"), "The 13 safety-layer settings behind slide 7")
nt = S(15).notes_slide.notes_text_frame
nt.text = nt.text.replace("slide 12", "slide 7").replace("slide 9", "slide 7")

# ------------------------------------------------------------------ order (drop the overview slide 5)
order = [S(1), S(2), S(3), S(4), A, S(10), S(11), S(12), S(13), S(6), S(7), S(8), S(9), S(14), S(15)]
lst = p.slides._sldIdLst
els = {int(el.get("id")): el for el in lst}
ids = [s.slide_id for s in order]
drop = els[S(5).slide_id]
for el in list(lst):
    lst.remove(el)
for i in ids:
    lst.append(els[i])
p.part.drop_rel(drop.get("{http://schemas.openxmlformats.org/officeDocument/2006/relationships}id"))
p.save(OUT)
print("saved", OUT, len(order), "slides (9 main + 6 backup)")

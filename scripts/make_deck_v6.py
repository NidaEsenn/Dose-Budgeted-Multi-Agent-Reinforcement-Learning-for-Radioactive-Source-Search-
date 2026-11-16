"""Midterm deck v6: the v5 deck cut to 11 slides.

    python scripts/make_deck_v6.py docs/Safe_Cooperative_Radiation_Source_Search_v5.pptx docs/Safe_Cooperative_Radiation_Source_Search_v6.pptx

v5 slides kept: 1-5 (title, why, problem, rules, literature), 7 filter, 8 policies,
9 safety layer (now with the step-by-step check figure), 11 results,
13 open problems (calibration + safety/success trade-off), 14 plan.
Dropped: 6 overview, 10 check (merged into 9), 12 trade-off (merged into 13), 15-16 backups.
"""
import sys

from PIL import Image
from pptx import Presentation
from pptx.util import Emu

SRC, OUT = sys.argv[1], sys.argv[2]
p = Presentation(SRC)
V = list(p.slides)
S = lambda n: V[n - 1]
by_id = lambda s, sid: next(sh for sh in s.shapes if sh.shape_id == sid)
by_text = lambda s, t: next(sh for sh in s.shapes if sh.has_text_frame and sh.text_frame.text.startswith(t))


def set_text(shape, text):
    para = shape.text_frame.paragraphs[0]
    runs = para.runs
    runs[0].text = text
    for r in runs[1:]:
        r._r.getparent().remove(r._r)
    for extra in shape.text_frame.paragraphs[1:]:
        extra._p.getparent().remove(extra._p)


def remove(shape):
    shape._element.getparent().remove(shape._element)


# titles of the algorithm slides
set_text(by_text(S(7), "Algorithm 2"), "How the team estimates the source")
set_text(by_text(S(8), "Algorithm 3"), "How the robots decide where to go")
S(7).notes_slide.notes_text_frame.text = S(7).notes_slide.notes_text_frame.text.replace(
    "This is how the team builds its shared guess. It is a particle filter.",
    "My system has three parts: a shared guess of the source, a policy that moves the robots, and a safety layer. "
    "First, the shared guess. It is a particle filter.")

# ---- safety layer: formula + step-by-step check figure (replaces the dose-trace slide)
s = S(9)
for sid in (5, 6, 7, 8, 9, 10, 11, 12, 13, 15, 16):
    remove(by_id(s, sid))
note = by_id(s, 14)
note.left, note.top, note.width, note.height = Emu(5943600), Emu(1325880), Emu(5669280), Emu(777240)
set_text(note, "Checked before every move, for every robot. Plan for a bad case: the 97th percentile of 32 samples from the "
               "filter. Withdraw is always allowed. Careful, but not a guarantee.")
path = "docs/figures/alg_reserve.png"
iw, ih = Image.open(path).size
top, bottom = 2280000, 6250000
h = bottom - top
w = int(h * iw / ih)
s.shapes.add_picture(path, Emu((p.slide_width - w) // 2), Emu(top), Emu(w), Emu(h))
s.notes_slide.notes_text_frame.text = (
    "(~1 min 15 s, key slide, slow down)\nThis is the core idea of my thesis. Before every move, each robot checks one rule: "
    "radiation so far, plus the next step, plus the trip home, must stay under 0.1 gray.\n"
    "The robot does not know exactly where the source is, so it plans for a bad case. On the left is the room: the white circle "
    "is the robot, the arrow is the move it wants, and the dashed line is its way out to the green door. The small crosses are "
    "32 possible sources drawn from the team's guess. For each of them I compute the dose of the move plus the dose of the "
    "lowest-dose way out. That gives 32 predictions.\n"
    "The middle plot is an early step: all 32 predictions, even the 97th percentile, are far under the budget, so the move is allowed.\n"
    "The right plot is the same robot twenty seconds later, near the source. The predictions spread out, because a small change in "
    "position makes a big change in dose. The 97th percentile passes the budget, so the robot withdraws. It always may.\n"
    "In reality it left with 0.065 gray, so the rule is careful. It is a careful rule, not a mathematical guarantee, "
    "so I measure the real failure rate over 1,000 test missions.")

# ---- open problems: calibration + trade-off
s = S(13)
set_text(by_text(s, "Why so much slack"), "Open problems: overconfident guess, costly safety")
set_text(by_text(s, "Worse with more data"), "Safer settings cost success")
set_text(by_text(s, "13% early"), "Of 13 settings, none beats the reference. Safest: 0.3% failures, but 65% success.")
set_text(by_text(s, "The true dose was"), "True dose above the 97th percentile in 18% of 18,633 checks, not 3%; 21% late in a mission.")
s.notes_slide.notes_text_frame.text = (
    "(~1 min 15 s)\nTwo open problems.\nFirst, is the bad case really a bad case? At every decision in 300 test missions I compared "
    "the safety layer's prediction with the true dose from the real source. If the guess were honest, the true dose would be above "
    "the 97th percentile only 3% of the time. It is 18%. On the right, an honest guess gives a flat histogram; we get a U-shape, "
    "so the guess is too narrow. It gets worse during the mission, 13% early and 21% later, because the filter counts linked "
    "model errors as new evidence and becomes too sure of itself.\n"
    "Why do we still get only about 4% failures? The misses are small, and the robots usually leave with budget to spare. That is fragile.\n"
    "Second, being safer costs success. I tried 13 settings of the rule. None beats the reference on both safety and success. "
    "The safest one fails in only 0.3% of missions but finds the source only 65% of the time.\n"
    "So the goal for the thesis: an honest, calibration-aware safety layer, and a learning team that is safe without losing success.")

n4 = S(4).notes_slide.notes_text_frame
n4.text = n4.text.replace("Every result is measured over 300 test missions.", "The main results use the same 1,000 test missions for every method.")
# ---- delete slides
lst = p.slides._sldIdLst
keep = [1, 2, 3, 4, 5, 7, 8, 9, 11, 13, 14]
els = list(lst)
for n, (el, sl) in enumerate(zip(els, V), 1):
    if n not in keep:
        rid = el.get("{http://schemas.openxmlformats.org/officeDocument/2006/relationships}id")
        lst.remove(el)
        p.part.drop_rel(rid)
p.save(OUT)
print("saved", OUT, len(p.slides), "slides")

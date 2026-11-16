"""Midterm deck v8: the user's edited v7 deck + four backup slides with the algorithm math.

    python scripts/make_deck_v8.py IN.pptx docs/Safe_Cooperative_Radiation_Source_Search_v8.pptx

Figures: scripts/make_figures_math.py. The math slides go right after the existing
algorithm backups (input slide 12); speaker notes are about one minute each.
"""
import copy
import sys

from PIL import Image
from pptx import Presentation
from pptx.enum.shapes import PP_PLACEHOLDER
from pptx.util import Emu

SRC, OUT = sys.argv[1], sys.argv[2]
p = Presentation(SRC)
V = list(p.slides)
S = lambda n: V[n - 1]
LAYOUT = {l.name: l for l in p.slide_layouts}
LEFT, FULL_W = 548640, 11064240


def set_text(shape, text):
    para = shape.text_frame.paragraphs[0]
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


TEMPLATE = S(10)                                   # an existing backup slide
title_src = TEMPLATE.shapes[0]
num_src = next(sh for sh in TEMPLATE.shapes if sh.is_placeholder and sh.placeholder_format.type == PP_PLACEHOLDER.SLIDE_NUMBER)


def math_slide(title, fig, note):
    s = p.slides.add_slide(LAYOUT["BACKUP"])
    for ph in list(s.placeholders):
        ph._element.getparent().remove(ph._element)
    set_text(copy_shape(title_src, s), title)
    copy_shape(num_src, s)
    iw, ih = Image.open(fig).size
    top, bottom = 1250000, 6200000
    w = FULL_W
    h = int(w * ih / iw)
    if h > bottom - top:
        h = bottom - top
        w = int(h * iw / ih)
    s.shapes.add_picture(fig, Emu(LEFT + (FULL_W - w) // 2), Emu(top), Emu(w), Emu(h))
    notes(s, note)
    return s


new = [
    math_slide("Math: the particle filter", "docs/figures/math_filter.png",
               "(~1 min)\n"
               "Here's the filter in four lines.\n"
               "One: the belief is 2,000 weighted guesses. Each guess is a source: x, y and strength.\n"
               "Two: for every guess, I can compute what each robot should count in 10 seconds. "
               "It's the inverse-square law, plus air and wall attenuation.\n"
               "Three: Bayes. Compare that with the real count. Guesses that explain it well get more weight. "
               "The likelihood is Poisson, widened by a 30% model error. I apply it in up to three small steps, "
               "so one lucky guess can't take all the weight at once.\n"
               "Four: resample. Keep the good guesses, copy them, and add a little noise. "
               "When the position spread is under 30 centimeters, the team names the source.\n"
               "One weak point: the filter treats every reading as independent. That's why it gets overconfident."),
    math_slide("Math: the greedy rule and the safety layer", "docs/figures/math_greedy.png",
               "(~1 min)\n"
               "This is my hand-written baseline.\n"
               "One: information gain. If my guesses disagree a lot about what I'd count in the next cell, "
               "a reading there tells me a lot.\n"
               "Two: the score is that information minus a dose penalty. The penalty grows when the robot has little budget left.\n"
               "Three: the robots choose one after another, and a cell a teammate already took gets a penalty. "
               "So they spread out. In my tests this crowd penalty mattered the most.\n"
               "Four: on top, the safety layer. Dose used, plus the bad-case dose of the next step and the way out, "
               "must stay under the budget. Bad case means the 97th percentile over 32 guesses. "
               "If the move fails the check, the robot withdraws."),
    math_slide("Math: MAPPO, the learned team", "docs/figures/math_mappo.png",
               "(~1 min)\n"
               "MAPPO is the learning method.\n"
               "One: train together, act alone. All robots share one policy network, and each one only uses its own view. "
               "During training, a critic sees everything, even the true source, and that helps learning. "
               "It's not used in the real mission.\n"
               "Two: the reward is shared by the team. You get points when the team's guess gets more accurate, "
               "and you lose one point for a wrong answer.\n"
               "Three: the advantage says how much better an action was than expected.\n"
               "Four: PPO makes good actions more likely, but it clips each update, so the policy doesn't jump too far. "
               "And actions the safety layer blocks are simply masked out."),
    math_slide("Math: MAPPO-Lagrangian, a price on risk", "docs/figures/math_lagrangian.png",
               "(~1 min)\n"
               "MAPPO-Lagrangian adds safety to the learning itself.\n"
               "One: the goal is high reward, but at most 5% of missions may have a robot over budget. "
               "I split that 5% across the robots.\n"
               "Two: the cost is one when a robot goes over its budget, plus a tiny dose term for an earlier signal.\n"
               "Three: the price, lambda. If failures are above the target, the price goes up. If they're below, it goes down.\n"
               "Four: the policy learns from reward minus price times cost. So risky moves become less attractive.\n"
               "Before I added the withdraw action, the price kept growing until the robots just stayed away, "
               "and success was only 10%. With withdraw, it's almost 80%, at 4.3% failures."),
]

# ---- small fixes: the trade-off chart is slide 8 in this deck
tbl = S(14)
set_text(tbl.shapes[0], tbl.shapes[0].text_frame.text.replace("slide 7", "slide 8"))
nt = tbl.notes_slide.notes_text_frame
nt.text = nt.text.replace("slide 7", "slide 8")

# ---- order: main 1-9, algorithm backups 10-12, the new math slides, then 13-14
order_ids = [s.slide_id for s in V[:12]] + [s.slide_id for s in new] + [s.slide_id for s in V[12:]]
lst = p.slides._sldIdLst
els = {int(el.get("id")): el for el in lst}
for el in list(lst):
    lst.remove(el)
for i in order_ids:
    lst.append(els[i])
p.save(OUT)
print("saved", OUT, len(order_ids), "slides")

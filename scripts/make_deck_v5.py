"""Midterm deck v5: builds on the v4 deck the user edited (13 slides, native charts).

    python scripts/make_deck_v5.py IN.pptx docs/Safe_Cooperative_Radiation_Source_Search_v5.pptx

Adds four slides with algorithm and calibration figures, updates the results to the
HPC pilot (1,000 test missions) and the plan, and renumbers the pages.
Figures: scripts/make_figures_algorithms.py, docs/figures/calibration_dose.png.
"""
import copy
import sys

from PIL import Image
from pptx import Presentation
from pptx.chart.data import CategoryChartData
from pptx.dml.color import RGBColor
from pptx.enum.shapes import MSO_SHAPE
from pptx.util import Emu, Pt

SRC, OUT = sys.argv[1], sys.argv[2]
p = Presentation(SRC)
old = list(p.slides)                       # original order, 0-based
O = lambda n: old[n - 1]                   # original slide number -> slide
by_id = lambda s, sid: next(sh for sh in s.shapes if sh.shape_id == sid)
CONTENT = next(l for l in p.slide_layouts if l.name == "CONTENT")
SLIDE_W = p.slide_width


def set_text(shape, text):
    para = shape.text_frame.paragraphs[0]
    runs = para.runs
    if not runs:
        para.add_run()
        runs = para.runs
    runs[0].text = text
    for r in runs[1:]:
        r._r.getparent().remove(r._r)
    for extra in shape.text_frame.paragraphs[1:]:
        extra._p.getparent().remove(extra._p)


def set_notes(slide, text):
    ns = slide.notes_slide
    if ns.notes_placeholder is None:         # notes master has no body placeholder: borrow one
        body = next(ph for ph in old[0].notes_slide.placeholders if ph.placeholder_format.type == 2)
        ns.shapes._spTree.append(copy.deepcopy(body._element))
    ns.notes_text_frame.text = text


def copy_shape(src_shape, dst_slide):
    el = copy.deepcopy(src_shape._element)
    used = [int(x) for x in dst_slide.shapes._spTree.xpath(".//p:cNvPr/@id")]
    el.xpath(".//p:cNvPr")[0].set("id", str(max(used + [1]) + 1))
    dst_slide.shapes._spTree.append(el)
    return dst_slide.shapes[-1]


def place(sh, left, top, width=None, height=None):
    sh.left, sh.top = Emu(int(left)), Emu(int(top))
    if width is not None:
        sh.width = Emu(int(width))
    if height is not None:
        sh.height = Emu(int(height))


def picture(slide, path, left, top, width):
    iw, ih = Image.open(path).size
    h = int(width * ih / iw)
    slide.shapes.add_picture(path, Emu(int(left)), Emu(int(top)), Emu(int(width)), Emu(h))
    return h


CARD_SRC = O(9)            # results slide cards: (5 box, 6 title, 7 text) light, (8, 9, 10) dark


def card(slide, left, top, w, h, title, text, dark=False):
    ids = (8, 9, 10) if dark else (5, 6, 7)
    box, t, x = (copy_shape(by_id(CARD_SRC, i), slide) for i in ids)
    place(box, left, top, w, h)
    place(t, left + 228600, top + 120000, w - 457200, 320040)
    place(x, left + 228600, top + 470000, w - 457200, h - 540000)
    set_text(t, title)
    set_text(x, text)


def new_slide(title):
    s = p.slides.add_slide(CONTENT)
    for ph in list(s.placeholders):
        ph._element.getparent().remove(ph._element)
    copy_shape(by_id(O(6), 2), s)              # title
    copy_shape(by_id(O(6), 41), s)             # page number
    set_text(s.shapes[0], title)
    return s


LEFT, FULL_W = 548640, 11064240

# ------------------------------------------------------------------ slide 4: mission rules
set_text(by_id(O(4), 13), "Main results use the same 1,000 test missions for every method (random source positions).")

# ------------------------------------------------------------------ slide 5: literature
f = by_id(O(5), 4)
set_text(f, "428 papers reviewed · " + f.text_frame.text)

# ------------------------------------------------------------------ slide 6: overview
set_text(by_id(O(6), 40), "Each algorithm is explained on the next slides")
set_notes(O(6), "(~1 min)\nMy system has four parts that work together.\n"
          "One: a fast simulator. It computes each robot's readings and the dose it receives: inverse-square law, walls that block part of "
          "the radiation, random detector counts, and about 30% model error.\n"
          "Two: a particle filter, the team's shared guess of where the source is and how strong it is.\n"
          "Three: the robot policies that choose the next move: a hand-written greedy rule, or the learning methods MAPPO and MAPPO-Lagrangian.\n"
          "Four: the dose safety layer, which checks every move before it is done.\n"
          "On the right is one decision step, every 10 seconds: measure, update the filter, propose moves, safety check, then move or withdraw. "
          "The next slides show each part in more detail.")

# ------------------------------------------------------------------ new: particle filter
sF = new_slide("Algorithm 2: how the team estimates the source")
h = picture(sF, "docs/figures/alg_filter.png", LEFT + (FULL_W - 8800000) / 2, 1200000, 8800000)
y = 1220000 + h + 120000
cw = (FULL_W - 2 * 182880) / 3
ch = 6250000 - y
card(sF, LEFT, y, cw, ch, "Each guess = (x, y, strength)",
     "2,000 guesses, spread over the room and the 10–100 TBq range at the start.")
card(sF, LEFT + cw + 182880, y, cw, ch, "Weight = how likely the count is",
     "Random (Poisson) counts with ~30% model error. Applied in up to 3 gentle stages.")
card(sF, LEFT + 2 * (cw + 182880), y, cw, ch, "Declare when sure", "Spread σ < 0.3 m → name the source. Success: within 1 m.", dark=True)
set_notes(sF, "(~1 min)\nThis is how the team builds its shared guess. It is a particle filter.\n"
          "It keeps 2,000 guesses. Each guess is a possible source: a position x, y and a strength. At the start the guesses are spread "
          "over the whole room and over the full strength range.\n"
          "Every 10 seconds each robot measures. Then each guess gets a weight: how well does it explain the counts the robots just saw? "
          "A guess that predicts the right count gets a high weight, a wrong one gets a low weight. I do this in up to three gentle steps, "
          "so that one lucky guess does not take all the weight at once.\n"
          "Then I resample: keep the likely guesses, copy them, and add a small random jitter so the guesses stay diverse.\n"
          "The middle plot is a real test mission: the position uncertainty falls from about 5 meters to under 0.3 meters, and then the team "
          "declares the source. The right plot shows the strength estimate: it jumps around at first and then locks onto the true value.\n"
          "One limitation I will come back to: the filter treats every reading as independent, but in my simulator the model errors are "
          "linked between nearby spots. So the filter becomes too sure of itself.")

# ------------------------------------------------------------------ new: policies
sP = new_slide("Algorithm 3: how the robots decide where to go")
pw = 6000000
h = picture(sP, "docs/figures/alg_policy.png", LEFT, 1300000, pw)
y = 1300000 + h + 150000
card(sP, LEFT, y, pw, 6250000 - y, "Shared team reward",
     "Points for shrinking the error of the guess · −1 for a wrong answer · a robot that withdrew still shares it.")
x0, cw2 = LEFT + pw + 274320, FULL_W - pw - 274320
hh = (6250000 - 1300000 - 2 * 137160) / 3
card(sP, x0, 1300000, cw2, hh, "Greedy rule (hand-written)",
     "Go where the next reading teaches the most, minus a dose penalty. Robots pick in turn and avoid the same cell.")
card(sP, x0, 1300000 + hh + 137160, cw2, hh, "MAPPO (learned)",
     "One network shared by all robots, trained with PPO. A critic that sees everything helps only in training.")
card(sP, x0, 1300000 + 2 * (hh + 137160), cw2, hh, "MAPPO-Lagrangian (learned)",
     "Cost = 1 if a robot goes over budget. A price λ rises while failures > 5% and lowers the reward for risk.", dark=True)
set_notes(sP, "(~1 min 15 s)\nThe third part decides where each robot goes. I compare three methods.\n"
          "The greedy rule is hand-written. For each possible move, it asks: how much would the next reading teach us about the source? "
          "It subtracts a penalty for the expected dose. Robots choose one after another, and a robot avoids a cell a teammate already picked.\n"
          "MAPPO is the learning method. The diagram shows the idea: train together, act alone. Every robot uses the same neural network, "
          "the actor. Each robot only sees its own information: its position, its counts, its remaining budget, the team's guess, and its "
          "nearest teammates. The actor outputs probabilities for six actions: four moves, stay, and withdraw. The safety layer can block "
          "unsafe actions before the robot acts. During training only, a critic that sees the full state, including the true source, "
          "tells the actor how well the team is doing. The PPO algorithm then updates the actor.\n"
          "The reward is shared by the whole team: points for making the guess more accurate, and minus one for a wrong answer.\n"
          "MAPPO-Lagrangian adds a cost: one when a robot goes over its budget. It learns a price, lambda. If failures are above 5%, the "
          "price goes up, and risky behaviour is worth less. If failures are below, the price goes down.")

# ------------------------------------------------------------------ old 8: safety layer concept
s8 = O(8)
set_notes(s8, s8.notes_slide.notes_text_frame.text
          .replace("I'll come back to it on slide 9.", "I'll come back to it in the results.")
          .replace("over 300 missions.", "over 1,000 test missions."))

# ------------------------------------------------------------------ new: the check step by step
sR = new_slide("Algorithm 4: the safety check, step by step")
h = picture(sR, "docs/figures/alg_reserve.png", LEFT + (FULL_W - 9300000) / 2, 1180000, 9300000)
y = 1180000 + h + 90000
cw = (FULL_W - 2 * 182880) / 3
cap = copy_shape(by_id(O(8), 14), sR)
place(cap, LEFT, y, FULL_W, 6250000 - y)
set_text(cap, "Real test mission, same robot 20 s apart. ① For each of 32 sampled sources: dose of the move + of the lowest-dose way out. "
              "② Early: even the 97th percentile is far under budget. ③ Near the source the samples spread out: the 97th percentile "
              "passes 0.1 Gy, so the robot withdraws (it actually leaves with 0.065 Gy).")
set_notes(sR, "(~1 min)\nThis slide opens up the safety check, using the same robot as on the last slide.\n"
          "On the left is the room. The white circle is the robot, the arrow is the move it wants to make, and the dashed line is its way "
          "out to the green door. The small crosses are 32 possible sources, drawn from the team's guess.\n"
          "For each of these 32 possible sources, I compute two numbers: the dose of the proposed move, and the dose of the way out. For "
          "the way out I take the shortest path to the door, and among the shortest paths the one with the lowest dose. That gives 32 "
          "predictions of used + next step + way out.\n"
          "The middle plot is an early step. All 32 predictions are far below the 0.1 gray budget, even the 97th percentile. The move is allowed.\n"
          "The right plot is twenty seconds later, closer to the source. Now the predictions spread out a lot, because a small change in "
          "the source position makes a big change in dose. The 97th percentile is far above the budget, so the robot withdraws.\n"
          "In reality it left with 0.065 gray. So the check is careful: it plans for a source that is closer or stronger than most guesses say.")

# ------------------------------------------------------------------ old 9: results (pilot, 1,000 missions)
s9 = O(9)
set_text(by_id(s9, 2), "Results: the reserve rule and the learned team")
chart = next(sh for sh in s9.shapes if sh.has_chart).chart
cd = CategoryChartData()
cd.categories = ["Greedy", "Greedy + reserve", "MAPPO", "MAPPO-Lagrangian"]
cd.add_series("Success (%)", (86.2, 84.6, 80.7, 79.6))
cd.add_series("Safety failures (%)", (30.4, 4.2, 19.0, 4.3))
chart.replace_data(cd)
set_text(by_id(s9, 4), "All methods: current rules with the withdraw action, same 1,000 test missions. Learned: 3 training runs pooled. "
                       "MAPPO + reserve layer is still training.")
set_text(by_id(s9, 6), "Withdraw fixed the timid robots")
set_text(by_id(s9, 7), "MAPPO-Lagrangian: 10% success before the withdraw action, now 79.6% at 4.3% failures.")
set_text(by_id(s9, 9), "Reserve rule is still best")
set_text(by_id(s9, 10), "84.6% success, 4.2% failures (95% CI 3.1–5.6%). Without it: 30.4% failures.")
set_text(by_id(s9, 12), "Learned team is more careful")
set_text(by_id(s9, 13), "Wrong answers: 6.7% vs 12.3% for the rule. Average-case reserve: 14.7% failures.")
set_notes(s9, "(~1 min 15 s, key slide, slow down)\nThese are the new pilot results from the university supercomputer. All four methods "
          "use the current rules, with the withdraw action, and all are tested on the same 1,000 test missions. The learned methods are "
          "three training runs each.\nBlue is success, orange is safety failures. My target is at most 5% failures.\n"
          "Without any safety, greedy and MAPPO fail often: 30% and 19% of missions.\n"
          "First result: the withdraw action fixed the timid robots. Before, MAPPO-Lagrangian found the source only 10% of the time, "
          "because the only way to avoid dose was to stay far away. Now it can go in and leave in time: 79.6% success at 4.3% failures.\n"
          "Second: the reserve rule on top of greedy is still the best: 84.6% success at 4.2% failures. With 1,000 missions the uncertainty "
          "range is 3.1 to 5.6%. If the same rule plans for the average case instead of the bad case, failures go up to 14.7%.\n"
          "Third: the learned team gives fewer wrong answers, 6.7% instead of 12.3%.\n"
          "The direct test, MAPPO with my reserve safety layer, is still training.")

# ------------------------------------------------------------------ old 10: trade-off
s10 = O(10)
set_text(by_id(s10, 10), "Also open: 4.2% is close to the 5% target (CI 3.1–5.6%), and why the rule needs so much slack: next slide.")
set_notes(s10, s10.notes_slide.notes_text_frame.text.replace(
    "Finally, 5% is not proven yet, and everything is still in simulation.",
    "Finally, 5% is not proven yet, and everything is still in simulation. The next slide shows why the safety layer needs so much slack."))

# ------------------------------------------------------------------ new: calibration test
sC = new_slide("Why so much slack? The bad case is not honest")
h = picture(sC, "docs/figures/calibration_dose.png", LEFT + 800000, 1220000, 9450000)
y = 1220000 + h + 140000
card(sC, LEFT, y, cw, 6250000 - y, "Exceeded far too often", "The true dose was above the 97th percentile in 18% of 18,633 checks, not 3%.")
card(sC, LEFT + cw + 182880, y, cw, 6250000 - y, "Worse with more data", "13% early → 21% later: linked errors are counted as new evidence.")
card(sC, LEFT + 2 * (cw + 182880), y, cw, 6250000 - y, "Safe because of slack",
     "Misses are small (≤24% in 95% of cases). A bigger model error could break it.", dark=True)
set_notes(sC, "(~1 min)\nSo why does the rule need so much slack? I tested whether its bad case is really a bad case.\n"
          "At every decision, in 300 test missions, I compared the safety layer's prediction, next step plus way out, with the true dose "
          "from the real source. If the guess were honest, the true dose would be above the 97th percentile only 3% of the time. "
          "It is 18%, over 18,633 checks.\n"
          "On the right: an honest guess gives a flat histogram. We get a U-shape, which means the guess is too narrow: the truth often "
          "lies outside all 32 samples.\n"
          "It gets worse during the mission: 13% in the first six steps, 21% later. The reason is that the filter counts linked errors as "
          "new, independent evidence, so it becomes more and more sure of itself.\n"
          "Why do we still get only about 4% failures? Because the misses are small, and the robots usually leave with budget to spare. "
          "That is fragile. This is why my main method will be a calibration-aware safety layer.")

# ------------------------------------------------------------------ old 11: plan
s11 = O(11)
MX, MW = 4572000, 1005840                    # Nov column left, month width
rows = [  # (label id, sub id, bar ids, label, sub, start, end, bar text)
    (11, 12, (13, 14), "1  Pilot on the HPC cluster ✓", "2 of 3 methods done · MAPPO + reserve finishing", 0.0, 0.6, "pilot ✓"),
    (15, 16, (17, 18), "2  Calibration-aware safety layer", "Make the bad case honest (main method)", 0.5, 2.0, "main method"),
    (19, 20, (21, 22), "3  Full study", "~370 training runs, 10 seeds, 3,000+ test missions", 1.8, 3.2, "full study"),
    (23, 24, (25, 26), "4  Unequal budgets, 2–6 robots", "Who should take the risky readings?", 2.6, 4.0, "risk sharing"),
    (27, 28, (29, 30), "5  Real-robot test", "Gazebo → real robots, simulated radiation or a check source", 4.0, 5.2, "transfer"),
    (31, None, (32, 33), "6  Thesis writing", None, 5.0, 7.0, "writing"),
]
for lab, sub, bars, ltxt, stxt, a, b, btxt in rows:
    set_text(by_id(s11, lab), ltxt)
    if sub:
        set_text(by_id(s11, sub), stxt)
    for bid in bars:
        sh = by_id(s11, bid)
        sh.left, sh.width = Emu(int(MX + a * MW)), Emu(int((b - a) * MW))
    set_text(by_id(s11, bars[1]), btxt)
today = s11.shapes.add_shape(MSO_SHAPE.RECTANGLE, Emu(int(MX + 0.5 * MW)), Emu(1560000), Emu(19050), Emu(3800000))
today.fill.solid(); today.fill.fore_color.rgb = RGBColor(0xB5, 0x40, 0x1E); today.line.fill.background()
tb = s11.shapes.add_textbox(Emu(int(MX + 0.5 * MW) + 40000), Emu(5250000), Emu(800000), Emu(250000))
tb.text_frame.text = "today"
r = tb.text_frame.paragraphs[0].runs[0]; r.font.size = Pt(11); r.font.bold = True; r.font.color.rgb = RGBColor(0xB5, 0x40, 0x1E)
set_notes(s11, "(~1 min)\nMy plan for the rest of the thesis.\n"
          "One: the pilot on the university cluster is almost done. Only MAPPO with the reserve layer is still training. It answers the "
          "main question: can a learning team beat the rule under the same safety layer?\n"
          "Two, the main method: a calibration-aware safety layer, which corrects the overconfident guess, for example by widening it or by "
          "adjusting the percentile from what it observes. Before that, a headroom test tells me how much better the rule could be with the "
          "true dose. I also add model error to the dose itself, to make the test harder and more realistic.\n"
          "Three: the full study, with ten training runs per method and more than 3,000 test missions, enough to show that a rate near 4% "
          "is really below 5%.\nFour: teams where robots have different budgets: does the team send the robot with the most budget left "
          "to take the risky readings?\nFive: a test on real robots, with simulated radiation or a weak check source. Six: writing.\n"
          "To close: safe search means every robot keeps enough dose to come home. Thank you, I'm happy to take questions.")

# ------------------------------------------------------------------ backups
s12 = O(12)
tf = by_id(s12, 5).text_frame
last = tf.paragraphs[-1]._p
new = copy.deepcopy(last); last.addnext(new)
para = tf.paragraphs[-1]
para.runs[0].text = "Pilot on the Explorer HPC cluster (SLURM job arrays): 3 methods × 3 seeds, 1,000 test missions each"
for rr in para.runs[1:]:
    rr._r.getparent().remove(rr._r)
set_text(by_id(O(13), 2), "The 13 safety-layer settings behind slide 12")
set_notes(O(13), O(13).notes_slide.notes_text_frame.text.replace("slide 9", "slide 12"))

# ------------------------------------------------------------------ order, delete old 7, renumber
lst = p.slides._sldIdLst
ids = {s.slide_id: el for s, el in zip(p.slides, list(lst))}
order = [O(1), O(2), O(3), O(4), O(5), O(6), sF, sP, O(8), sR, O(9), O(10), sC, O(11), O(12), O(13)]
drop = O(7)
sid = {id(s): s.slide_id for s in order}
for el in list(lst):
    lst.remove(el)
for s in order:
    lst.append(ids[sid[id(s)]])
rid = next(r.rId for r in p.part.rels.values() if r.reltype.endswith("/slide") and r._target is drop.part)
p.part.drop_rel(rid)
# page numbers are slide-number fields: they renumber themselves
p.save(OUT)
print("saved", OUT, len(order), "slides")

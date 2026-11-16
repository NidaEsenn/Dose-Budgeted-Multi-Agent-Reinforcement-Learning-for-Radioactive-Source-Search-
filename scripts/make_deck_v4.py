import copy, sys
from pptx import Presentation
from pptx.util import Emu
from PIL import Image
SRC, OUT = sys.argv[1], sys.argv[2]
p = Presentation(SRC)
S = lambda i: p.slides[i - 1]
by_id = lambda s, sid: next(sh for sh in s.shapes if sh.shape_id == sid)

def set_text(shape, text):
    para = shape.text_frame.paragraphs[0]; runs = para.runs
    runs[0].text = text
    for r in runs[1:]: r._r.getparent().remove(r._r)
    for extra in shape.text_frame.paragraphs[1:]: extra._p.getparent().remove(extra._p)

def replace_pic(slide, sid, path, left, top, width, height):
    old = by_id(slide, sid); tree = slide.shapes._spTree
    idx = list(tree).index(old._element)
    new = slide.shapes.add_picture(path, Emu(left), Emu(top), Emu(width), Emu(height))
    tree.remove(new._element); tree.insert(idx, new._element); tree.remove(old._element)

def set_notes(slide, text):
    tf = slide.notes_slide.notes_text_frame
    para = tf.paragraphs[0]
    if para.runs: para.runs[0].text = text
    else: para.add_run().text = text
    for r in para.runs[1:]: r._r.getparent().remove(r._r)
    for extra in tf.paragraphs[1:]: extra._p.getparent().remove(extra._p)

def fit(path, w):
    iw, ih = Image.open(path).size; return w, int(w * ih / iw)

# ---- slide 5: literature count in footer
f = by_id(S(5), 4); set_text(f, "5 · 428 papers reviewed · " + f.text_frame.text.split("· ", 1)[1])

# ---- slide 8: P1 results on 1,000 missions
s = S(8)
set_text(by_id(s, 2), "Results: the reserve rule and the learned team")
w, h = fit("docs/figures/p1_results.png", 6350000)
replace_pic(s, 3, "docs/figures/p1_results.png", 812800, 1463030, w, h)
cap = by_id(s, 4); cap.top = Emu(1463030 + h + 60000)
set_text(cap, "Dark bars = safety-aware methods · light bars = no safety")
for t, x, title, text in [(6, 7, "Withdraw fixed the timid robots",
                           "MAPPO-Lagrangian: 10% success before the withdraw action, 79.6% now, at 4.3% failures."),
                          (9, 10, "The reserve rule is still best",
                           "84.6% success at 4.2% failures (CI 3.1–5.6%). Learned team: ~5 points lower, same safety."),
                          (12, 13, "The learned team is more careful",
                           "Fewer wrong answers (6.7% vs 12.3% for the rule). MAPPO + reserve is still training.")]:
    set_text(by_id(s, t), title); set_text(by_id(s, x), text)
set_text(by_id(s, 14), "8 · Current rules (with withdraw) · 1,000 test missions each · learned: 3 training seeds pooled · lines = 95% CI")
set_notes(s, "(about 80 s, key slide, slow down) These are the new pilot results from the university supercomputer. "
  "All four methods now use the current rules, with the withdraw action, and each is tested on the same 1,000 test missions. "
  "The learned methods are three training runs each; the dots show the single runs. "
  "Left chart is success, right chart is safety failures; the red dashed line is my 5% target. "
  "Without any safety, greedy and MAPPO both fail often: 30% and 19% of missions. "
  "First main result: the withdraw action fixed the timid robots. Before, MAPPO-Lagrangian reached only 10% success, "
  "because the only way to avoid dose was to stay far from the source. Now it can go in and leave in time: 79.6% success at 4.3% failures. "
  "Second: my reserve rule on top of greedy is still the best: 84.6% success at 4.2% failures, and with 1,000 missions the uncertainty range is 3.1 to 5.6%. "
  "Third: the learned team gives fewer wrong answers, 6.7% instead of 12.3%, so it is more careful about when to declare. "
  "MAPPO combined with my reserve safety layer is still training; that is the direct test of whether learning helps under the same safety layer.")

set_text(by_id(S(9), 11), 'Still close to 5%')
set_text(by_id(S(9), 12), '1,000 missions: 4.2%, CI 3.1–5.6%. Simulation only.')
# ---- new slide after 9: calibration test
s9 = S(9)
new = p.slides.add_slide(s9.slide_layout)
for ph in list(new.placeholders): ph._element.getparent().remove(ph._element)
for sh in s9.shapes:
    if sh.shape_id in (2, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13):
        new.shapes._spTree.append(copy.deepcopy(sh._element))
lst = p.slides._sldIdLst; el = lst[-1]; lst.remove(el); lst.insert(9, el)
s = new
set_text(by_id(s, 2), "Is the safety layer honest? A calibration test")
w, h = fit("docs/figures/calibration_dose.png", 9200000)
pic = s.shapes.add_picture("docs/figures/calibration_dose.png", Emu((12192000 - w) // 2), Emu(1400000), Emu(w), Emu(h))
y0 = 1400000 + h + 180000; colw = 3500000
items = [(4, 5, 6, "Bad case is exceeded too often", "True dose was above the 97th percentile in 18% of 18,633 decisions, not 3%."),
         (7, 8, 9, "Worse with more data", "13% early → 21% later: linked errors are counted as new evidence."),
         (10, 11, 12, "Safety comes from slack", "Overshoot ≤24% in 95% of cases; a bigger model error could break it.")]
for k, (ln, t, x, title, text) in enumerate(items):
    left = 812800 + k * (colw + 180000)
    L = by_id(s, ln); L.left, L.top, L.height = Emu(left), Emu(y0), Emu(727621)
    T = by_id(s, t); T.left, T.top, T.width = Emu(left + 177800), Emu(y0), Emu(colw - 177800)
    X = by_id(s, x); X.left, X.top, X.width, X.height = Emu(left + 177800), Emu(y0 + 281930), Emu(colw - 177800), Emu(471091)
    set_text(T, title); set_text(X, text)
set_text(by_id(s, 13), "10 · 300 test missions · reference rule (greedy + reserve, 97th percentile of 32 samples) · truth from the real source")
set_notes(s, "(about 70 s) This slide asks: is the safety layer's bad case really a bad case? "
  "At every decision, I compared what the safety layer predicted, the next step plus the trip home, with the true dose computed from the real source. "
  "If the guess were honest, the true dose would be above the 97th percentile only 3% of the time. "
  "In reality it is 18%, over 18,633 decisions. On the right, an honest guess would give a flat histogram; we get a U-shape, "
  "which means the guess is too narrow: the truth often lies outside all 32 samples. "
  "It also gets worse as the mission goes on: 13% in the first six steps, 21% later. The reason is that the model errors in my simulator are linked "
  "between nearby spots, but the estimator treats each reading as new, independent evidence, so it becomes too sure of itself. "
  "So why do we still see only about 4% failures? Because of slack: the misses are small, 95% of them are less than 24% above the prediction, "
  "and the robots usually leave with budget to spare. That is fragile: a larger model error, or stronger sources, could break it. "
  "This is why my main method will be a calibration-aware safety layer.")

# ---- old slide 10 (now 11): plan
s = S(11)
w, h = fit("docs/figures/plan_timeline.png", 10566400)
replace_pic(s, 3, "docs/figures/plan_timeline.png", 812800, 1463030, w, h)
by_id(s, 4).top = Emu(1463030 + h + 250000)
set_text(by_id(s, 5), "11 · Draft timeline · real-robot test uses simulated radiation or a low-activity check source")
set_notes(s, "(about 60 s) My plan for the rest of the thesis. The pilot on the supercomputer is almost done; only MAPPO with the reserve layer is still training. "
  "Right now I am running a headroom test: how much better could the rule get if the safety layer knew the true dose? That tells me how much there is to gain "
  "by fixing the guess. I am also adding model error to the dose itself, not only to the sensor counts, to make the test harder and more realistic. "
  "The main method of the thesis will be a calibration-aware safety layer, one that corrects for the overconfident guess, for example by widening it "
  "or by adjusting the percentile online from what it observes. Then the full study: ten training runs per method and more than 3,000 test missions, "
  "enough to show that a rate near 4% is really below 5%. Then teams with unequal budgets: does the team send the robot with the most budget left to take the risky readings? "
  "Finally a real-robot test with simulated radiation or a weak check source, and writing. "
  "To close: safe search means every robot keeps enough dose to come home. Thank you, I am happy to take questions.")
p.save(OUT)

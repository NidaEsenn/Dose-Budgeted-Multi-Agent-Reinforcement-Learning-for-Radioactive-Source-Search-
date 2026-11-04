const pptxgen = require("pptxgenjs");
const { applyTheme } = require("/root/.claude/skills/synced/02812373-138d-4a58-874b-33e46fa50871_5ae0fb7b-f204-4157-8b07-59d0450a2433/pptx/scripts/apply_theme.js");

const [OUT, IMG72_2D, IMG72_3D, IMG44_3D] = process.argv.slice(2);

const HEX = { ink: "17201F", muted: "56615F", teal: "0D6B66", red: "A3342B", amber: "9A5B00",
  tealSoft: "E2F0EE", redSoft: "F8E5E2", amberSoft: "FBF0DE", ground: "EEF1F0", rule: "D9DEDD", white: "FFFFFF" };
const THEME = {
  name: "Dose Search", headFontFace: "Cambria", bodyFontFace: "Calibri",
  colors: { dk1: HEX.ink, lt1: HEX.white, dk2: HEX.muted, lt2: HEX.ground,
    accent1: HEX.teal, accent2: HEX.red, accent3: HEX.amber, accent4: HEX.tealSoft,
    accent5: HEX.redSoft, accent6: HEX.amberSoft, hlink: HEX.teal, folHlink: HEX.muted },
};

const pres = new pptxgen();
pres.layout = "LAYOUT_WIDE";
pres.author = "Nida Esen";
pres.title = "Dose-Budgeted Multi-Robot Source Search: Progress Update";
pres.theme = { headFontFace: THEME.headFontFace, bodyFontFace: THEME.bodyFontFace };
const C = pres.SchemeColor;
const X0 = 0.6, W = 12.13, TOP = 1.8;

pres.defineSlideMaster({
  title: "Title", background: { color: C.background2 },
  objects: [
    { placeholder: { options: { name: "kicker", type: "body", x: X0, y: 1.55, w: 6.0, h: 0.4, fontSize: 13, bold: true, color: C.accent1, charSpacing: 3 }, text: "" } },
    { placeholder: { options: { name: "title", type: "title", x: X0, y: 2.0, w: 6.1, h: 1.9, fontSize: 40, bold: true, color: C.text1, valign: "top", align: "left" }, text: "" } },
    { placeholder: { options: { name: "body", type: "body", x: X0, y: 4.0, w: 5.9, h: 1.0, fontSize: 18, color: C.text1, valign: "top" }, text: "" } },
    { placeholder: { options: { name: "meta", type: "body", x: X0, y: 5.35, w: 6.0, h: 0.9, fontSize: 14, color: C.text2, valign: "top" }, text: "" } },
  ],
});
pres.defineSlideMaster({
  title: "Divider", background: { color: C.accent1 },
  objects: [
    { placeholder: { options: { name: "title", type: "title", x: X0, y: 2.9, w: W, h: 1.0, fontSize: 40, bold: true, color: C.background1, align: "left" }, text: "" } },
    { placeholder: { options: { name: "body", type: "body", x: X0, y: 3.95, w: W, h: 0.6, fontSize: 18, color: C.background1 }, text: "" } },
  ],
});
pres.defineSlideMaster({
  title: "Content", background: { color: C.background1 }, margin: [0.5, 0.6, 0.5, 0.6],
  slideNumber: { x: 12.3, y: 7.0, w: 0.6, h: 0.3, fontSize: 10, color: C.text2, align: "right" },
  objects: [
    { text: { text: "Nida Esen · Dose-budgeted multi-robot source search", options: { x: X0, y: 7.0, w: 7, h: 0.3, fontSize: 10, color: C.text2 } } },
    { placeholder: { options: { name: "kicker", type: "body", x: X0, y: 0.42, w: 10, h: 0.35, fontSize: 12, bold: true, color: C.accent1, charSpacing: 3 }, text: "" } },
    { placeholder: { options: { name: "title", type: "title", x: X0, y: 0.78, w: W, h: 0.9, fontSize: 30, bold: true, color: C.text1, valign: "top", align: "left" }, text: "" } },
  ],
});

// ---------------------------------------------------------------- helpers
let objN = 0;
const nm = (s) => `${s} ${++objN}`;
function card(s, x, y, w, h, fill, line, name = "Card") {
  s.addShape(pres.shapes.ROUNDED_RECTANGLE, { x, y, w, h, rectRadius: 0.08, objectName: nm(name),
    fill: { color: fill }, line: line ? { color: line, width: 1 } : { type: "none" } });
}
function txt(s, text, o, name = "Text") {
  s.addText(text, Object.assign({ isTextBox: true, objectName: nm(name), margin: 0, valign: "top", color: C.text1, fontSize: 15 }, o));
}
function numCircle(s, n, x, y, d = 0.5, fill = C.accent1) {
  s.addShape(pres.shapes.OVAL, { x, y, w: d, h: d, fill: { color: fill }, line: { type: "none" }, objectName: nm("Number circle") });
  txt(s, String(n), { x, y, w: d, h: d, fontSize: 15, bold: true, color: C.background1, align: "center", valign: "middle" }, "Number");
}
function arrow(s, x, y, w, h, color = HEX.muted) {
  s.addShape(pres.shapes.LINE, { x, y, w, h, objectName: nm("Arrow"), line: { color, width: 1.75, endArrowType: "triangle" } });
}
function chip(s, label, x, y, w, fill, color) {
  s.addShape(pres.shapes.ROUNDED_RECTANGLE, { x, y, w, h: 0.32, rectRadius: 0.08, fill: { color: fill }, line: { type: "none" }, objectName: nm("Chip") });
  txt(s, label, { x, y, w, h: 0.32, fontSize: 11, bold: true, color, align: "center", valign: "middle" }, "Chip label");
}
function content(section, kicker, title) {
  const s = pres.addSlide({ masterName: "Content", sectionTitle: section });
  s.addText(kicker.toUpperCase(), { placeholder: "kicker" });
  s.addText(title, { placeholder: "title" });
  return s;
}
function caveat(s, text, y = 6.45) {
  txt(s, text, { x: X0, y, w: W, h: 0.4, fontSize: 12, italic: true, color: C.text2 }, "Caveat");
}
const chartBase = (extra) => Object.assign({
  catAxisLabelFontFace: "+mn-lt", valAxisLabelFontFace: "+mn-lt", dataLabelFontFace: "+mn-lt",
  titleFontFace: "+mn-lt", legendFontFace: "+mn-lt",
  catAxisLabelColor: HEX.muted, valAxisLabelColor: HEX.muted, catAxisLabelFontSize: 12, valAxisLabelFontSize: 11,
  valGridLine: { color: HEX.rule, size: 0.75 }, catGridLine: { style: "none" },
  showTitle: true, titleFontSize: 14, titleColor: HEX.ink, dataLabelFontSize: 11, dataLabelColor: HEX.ink,
}, extra);

// ================================================================ PART 1
pres.addSection({ title: "Context" });
{ // 1 title
  const s = pres.addSlide({ masterName: "Title", sectionTitle: "Context" });
  s.addText("MASTER'S THESIS · PROGRESS UPDATE", { placeholder: "kicker" });
  s.addText("Dose-Budgeted Multi-Robot Source Search", { placeholder: "title" });
  s.addText("Can a robot team learn to find a lost radioactive source without any robot exceeding its own radiation budget?", { placeholder: "body" });
  s.addText([{ text: "Nida Esen", options: { bold: true, color: C.text1, breakLine: true } },
             { text: "Advisor: Prof. [Name] · Northeastern University · November 2026" }], { placeholder: "meta" });
  s.addImage({ path: IMG72_3D, x: 6.95, y: 1.45, w: 5.85, h: 4.39, objectName: "3D mission render",
    altText: "3D render of a simulated mission: a room with concrete obstacles, robots, and the floor coloured by radiation dose rate." });
  txt(s, "Simulated mission in the MuJoCo 3D world. Floor colour: true dose rate.", { x: 6.95, y: 5.95, w: 5.85, h: 0.35, fontSize: 11, color: C.text2 }, "Image caption");
  s.addNotes("One-sentence opener: this thesis asks whether a team of robots can learn to find a strong radioactive source while every robot stays within its own radiation budget.");
}
{ // 2 incidents
  const s = content("Context", "Motivation", "Robots are sent in, but radiation destroys them too");
  const ys = 2.55;
  s.addShape(pres.shapes.LINE, { x: X0 + 0.3, y: ys, w: W - 0.6, h: 0, line: { color: HEX.rule, width: 2 }, objectName: "Timeline axis" });
  const ev = [["1987", "Goiânia, Brazil", "50.9 TBq caesium-137 source opened by scrap collectors"],
              ["2000", "Samut Prakan, Thailand", "15.7 TBq cobalt-60 source sold as scrap metal"],
              ["2013", "Hueypoxtla, Mexico", "111 TBq cobalt-60 source stolen in transit"]];
  const cw = (W - 0.7) / 3;
  ev.forEach(([yr, place, what], i) => {
    const x = X0 + i * (cw + 0.35);
    s.addShape(pres.shapes.OVAL, { x: x + 0.3, y: ys - 0.13, w: 0.26, h: 0.26, fill: { color: C.accent2 }, line: { type: "none" }, objectName: nm("Timeline dot") });
    txt(s, yr, { x: x + 0.3, y: 1.85, w: 2, h: 0.5, fontFace: THEME.headFontFace, fontSize: 26, bold: true, color: C.accent2 });
    txt(s, place, { x: x + 0.3, y: 2.85, w: cw - 0.4, h: 0.4, fontSize: 17, bold: true });
    txt(s, what, { x: x + 0.3, y: 3.3, w: cw - 0.5, h: 0.8, fontSize: 15 });
  });
  card(s, X0, 4.45, W, 1.75, C.background2, null, "Robot damage box");
  txt(s, "And robots fail too", { x: X0 + 0.35, y: 4.65, w: 5, h: 0.4, fontSize: 17, bold: true, color: C.accent1 });
  s.addText([
    { text: "Fukushima Daiichi: robot cameras and lidar failed after about 120 Gy of accumulated dose.", options: { bullet: true, breakLine: true } },
    { text: "2017: a TEPCO cleaning robot had to be withdrawn after about two hours in Unit 2.", options: { bullet: true } },
  ], { isTextBox: true, objectName: "Robot damage bullets", x: X0 + 0.35, y: 5.1, w: W - 0.7, h: 1.0, fontSize: 15, color: C.text1, paraSpaceAfter: 6, margin: 0, valign: "top" });
  caveat(s, "Sources: IAEA accident reports (1988, 2002, 2022); West et al. 2022 citing Nagatani et al. 2011; TEPCO 2017.", 6.4);
  s.addNotes("Strong sources get lost in practice, and the robots sent in are themselves damaged by dose. Robot dose is a mission-limiting constraint, not a detail.");
}
{ // 3 trade-off
  const s = content("Context", "The core trade-off", "The best information is exactly where the danger is");
  const d = [0.5, 1, 1.5, 2, 3, 4, 5];
  const mins = d.map((x) => +(0.1 / (3.51e-4 * 5e4 / (x * x + 0.09)) * 60).toFixed(2));
  s.addChart(pres.charts.LINE, [{ name: "Minutes until a 0.1 Gy budget is used", labels: d.map((x) => `${x} m`), values: mins }],
    chartBase({ x: X0, y: TOP, w: 7.4, h: 4.55, title: "Minutes until a 0.1 Gy budget is used (50 TBq Co-60)",
      chartColors: [HEX.red], lineSize: 3, lineDataSymbol: "circle", lineDataSymbolSize: 8, showLegend: false,
      showValue: true, dataLabelPosition: "t", dataLabelFormatCode: "0.0", valAxisLabelFormatCode: "0",
      showCatAxisTitle: true, catAxisTitle: "Distance from the source", catAxisTitleFontSize: 12, catAxisTitleColor: HEX.muted,
      objectName: "Time to budget chart" }));
  const cards = [["~20 s", "at 1 m", C.accent5, C.accent2], ["~1.5 min", "at 2 m", C.background2, C.accent1], ["~5 min", "at 4 m", C.accent4, C.accent1]];
  cards.forEach(([st, lab, fill, col], i) => {
    const y = TOP + i * 1.55;
    card(s, 8.4, y, 4.33, 1.35, fill, null, "Distance card");
    txt(s, st, { x: 8.75, y: y + 0.2, w: 2.3, h: 0.9, fontFace: THEME.headFontFace, fontSize: 34, bold: true, color: col, valign: "middle" });
    txt(s, lab, { x: 11.0, y: y + 0.2, w: 1.5, h: 0.9, fontSize: 16, valign: "middle" });
  });
  caveat(s, "Close readings pin the source down best, but dose grows like 1/distance². The team must choose how close, how long, and which robot.");
  s.addNotes("Read the curve: one metre costs the whole budget in about 20 seconds, four metres gives about five minutes. Information and danger peak at the same place.");
}

// ================================================================ PART 2
pres.addSection({ title: "Problem" });
{ // 4 gap
  const s = content("Problem", "Related work", "Existing work solves two of the three pieces, never all three");
  const circ = [[2.25, 1.95, "Unknown source"], [4.15, 1.95, "Learned\nmulti-robot policy"], [3.2, 3.6, "Per-robot\ndose budget"]];
  const R = 1.35;
  circ.forEach(([cx, cy, lab], i) => {
    s.addShape(pres.shapes.OVAL, { x: cx - R + X0 - 0.6 + 0.6, y: cy - R + 0.6 + 0.3, w: 2 * R, h: 2 * R, objectName: nm("Venn circle"),
      fill: { color: [C.accent1, C.accent3, C.accent2][i], transparency: 78 }, line: { color: [HEX.teal, HEX.amber, HEX.red][i], width: 1.25 } });
  });
  const lab = [[1.25, 2.25, "Unknown\nsource"], [4.05, 2.25, "Learned\nteam policy"], [2.55, 4.95, "Per-robot\ndose budget"]];
  lab.forEach(([x, y, t]) => txt(s, t, { x, y, w: 1.6, h: 0.7, fontSize: 14, bold: true, align: "center" }, "Venn label"));
  txt(s, "This\nwork", { x: 3.05, y: 3.3, w: 1.0, h: 0.6, fontSize: 14, bold: true, color: C.accent1, align: "center", valign: "middle" }, "Venn centre");
  const rows = [["Learned team search", "RAD-TEAM, PSOPF-MATD3", "Dose treated as free; weak sources"],
                ["Dose-aware planning", "West et al. 2022; 2025–26 planners", "Needs a known radiation map; no learning"],
                ["Exposure-aware localization", "Son et al. 2025", "Single robot on a fixed path"]];
  rows.forEach(([h, who, lack], i) => {
    const y = TOP + i * 1.45;
    card(s, 6.6, y, 6.13, 1.25, C.background2, null, "Gap row");
    txt(s, h, { x: 6.9, y: y + 0.15, w: 5.6, h: 0.4, fontSize: 17, bold: true });
    txt(s, who, { x: 6.9, y: y + 0.55, w: 5.6, h: 0.3, fontSize: 13, color: C.text2 });
    txt(s, lack, { x: 6.9, y: y + 0.85, w: 5.6, h: 0.35, fontSize: 14, italic: true, color: C.accent2 });
  });
  caveat(s, "No work found that combines all three, or studies how a team should divide the risk between robots.");
  s.addNotes("Each line of prior work covers two of the three circles. The thesis sits in the middle, and the risk-sharing question is new on top of that.");
}
{ // 5 formulation
  const s = content("Problem", "Problem formulation", "A team search with one safety constraint per robot");
  const steps = ["Observe", "Act", "Absorb dose,\ntake a reading", "Update shared\nestimate", "Reward\nand cost"];
  const bw = 2.05, gap = 0.47, by = 2.0, bh = 1.2;
  steps.forEach((t, i) => {
    const x = X0 + i * (bw + gap);
    card(s, x, by, bw, bh, i === 4 ? C.accent4 : C.background2, null, "Loop step");
    txt(s, t, { x, y: by, w: bw, h: bh, fontSize: 16, bold: true, align: "center", valign: "middle" });
    if (i < 4) arrow(s, x + bw + 0.05, by + bh / 2, gap - 0.1, 0);
  });
  const xL = X0 + bw / 2, xR = X0 + 4 * (bw + gap) + bw / 2, yb = by + bh + 0.35;
  s.addShape(pres.shapes.LINE, { x: xR, y: by + bh, w: 0, h: 0.35, line: { color: HEX.muted, width: 1.75 }, objectName: "Loop return 1" });
  s.addShape(pres.shapes.LINE, { x: xL, y: yb, w: xR - xL, h: 0, line: { color: HEX.muted, width: 1.75 }, objectName: "Loop return 2" });
  s.addShape(pres.shapes.LINE, { x: xL, y: by + bh, w: 0, h: 0.35, flipV: true, line: { color: HEX.muted, width: 1.75, endArrowType: "triangle" }, objectName: "Loop return 3" });
  txt(s, "every 10 seconds, for every robot", { x: X0, y: yb + 0.08, w: W, h: 0.35, fontSize: 12, italic: true, color: C.text2, align: "center" });
  const defs = [["Reward (shared by the team)", "Points when the team's estimate of the source gets more accurate, a small time penalty, a bonus when the final estimate is within 1 m."],
                ["Constraint (one per robot)", "Each robot's cumulative dose must stay below its own budget. A robot that reaches it is retired on the spot."],
                ["In ML terms", "A cooperative, partially observable multi-agent problem with a per-agent cumulative cost constraint (constrained Dec-POMDP)."]];
  const cw = (W - 0.7) / 3;
  defs.forEach(([h, d], i) => {
    const x = X0 + i * (cw + 0.35);
    txt(s, h, { x, y: 4.35, w: cw, h: 0.4, fontSize: 16, bold: true, color: i === 1 ? C.accent2 : C.accent1 });
    txt(s, d, { x, y: 4.8, w: cw, h: 1.5, fontSize: 14 });
  });
  s.addNotes("Walk the loop once. Then stress the two definitions: one shared reward for accuracy, but a separate dose constraint for each robot.");
}
{ // 6 RQs + hypotheses
  const s = content("Problem", "Research questions and hypotheses", "Three questions, each with a testable hypothesis");
  const H = { bold: true, color: C.text2, fontSize: 12, fill: { color: C.background2 } };
  const row = (a, b, c, d) => [{ text: a, options: { bold: true, color: C.accent1 } }, { text: b, options: { bold: true } }, c, d];
  s.addTable([
    [{ text: "", options: H }, { text: "QUESTION", options: H }, { text: "HYPOTHESIS", options: H }, { text: "HOW WE TEST IT", options: H }],
    row("RQ1", "Safety", "A constrained policy keeps ≥ 95% of missions violation-free, with success within 5 points of unconstrained MAPPO, and beats a hand-designed safe planner", "1,000 fixed test missions, 10 seeds, non-inferiority test"),
    row("RQ2", "Constraint vs penalty", "One constrained setting meets the target across budgets and source strengths; a fixed dose penalty needs re-tuning for each", "Tune both on one setting, test on unseen settings"),
    row("RQ3", "Risk sharing", "With unequal budgets, a robot's share of team dose rises with its share of the budget, and follows the budget, not the robot's identity", "Dose-share slope; shuffle budgets between robots"),
  ], { x: X0, y: TOP, w: W, colW: [0.8, 2.2, 5.6, 3.53], fontSize: 15, color: C.text1, valign: "middle",
    border: { type: "solid", color: HEX.rule, pt: 0.75 }, rowH: [0.45, 1.25, 1.25, 1.25], margin: [0.08, 0.14, 0.08, 0.14], objectName: "RQ table" });
  caveat(s, "The 95% target is a hypothesis, not a requirement: the project succeeds if it answers each question reliably, whatever the answer.", 6.35);
  s.addNotes("Emphasize that every hypothesis has a pre-set threshold and test, written down before the full experiments.");
}

// ================================================================ PART 3
pres.addSection({ title: "Approach" });
{ // 7 approach
  const s = content("Approach", "Approach", "Simulate, estimate, learn, check safety, evaluate");
  const st = [["Simulator", "20 × 20 m room, walls, 3–6 robots, radiation physics with realistic detector error"],
              ["Shared estimate", "Particle filter: thousands of guesses of the source's position and strength"],
              ["Learning team", "One shared policy (MAPPO) with a safety price λ for each robot"],
              ["Safety backup", "Shield that blocks moves predicted to exceed the budget"],
              ["Evaluation", "Same 1,000 test missions for every method, 10 seeds, confidence intervals"]];
  const n = 5, gap = 0.33, bw = (W - gap * (n - 1)) / n, by = TOP + 0.05, bh = 3.0;
  st.forEach(([h, d], i) => {
    const x = X0 + i * (bw + gap);
    card(s, x, by, bw, bh, C.background2, null, "Approach step");
    numCircle(s, i + 1, x + 0.22, by + 0.22, 0.48);
    txt(s, h, { x: x + 0.22, y: by + 0.9, w: bw - 0.44, h: 0.4, fontSize: 16, bold: true });
    txt(s, d, { x: x + 0.22, y: by + 1.38, w: bw - 0.44, h: 1.5, fontSize: 14 });
    if (i < n - 1) arrow(s, x + bw + 0.03, by + bh / 2, gap - 0.06, 0);
  });
  txt(s, "Compared against", { x: X0, y: 5.25, w: 3, h: 0.35, fontSize: 14, bold: true, color: C.text2 });
  const chips = ["Random walk", "Perimeter path", "Walk to estimate", "Greedy information", "Shielded greedy", "Fixed dose penalty"];
  let cx = X0;
  chips.forEach((c) => { const w = 0.28 + c.length * 0.095; chip(s, c, cx, 5.7, w, C.background2, C.text1); cx += w + 0.15; });
  s.addNotes("The learning method is MAPPO-Lagrangian: a standard multi-agent PPO plus one automatically adjusted safety price per robot. Everything is compared on the same fixed test missions.");
}
{ // 8 status
  const s = content("Approach", "Status", "The full pipeline runs end to end; experiments remain");
  const items = [["Grid simulator + particle filter", "Done", 0], ["5 baselines + safety shield", "Done", 0],
                 ["MAPPO, MAPPO-L (A, B), fixed penalty", "Built, short runs only", 1], ["Evaluation, statistics, plots", "Done", 0],
                 ["MuJoCo 3D motion layer + Gazebo export", "Done", 0], ["60 automated tests", "Done", 0],
                 ["Full experiments (10 seeds, ~370 runs)", "Not started: needs cluster", 2], ["ROS 2 bridge, real robots", "Planned: semester 2", 2]];
  const sty = [[C.accent4, C.accent1], [C.accent6, C.accent3], [C.background2, C.text2]];
  items.forEach(([t, st, k], i) => {
    const y = TOP + i * 0.57;
    txt(s, t, { x: X0, y, w: 4.3, h: 0.45, fontSize: 15, valign: "middle" });
    chip(s, st, X0 + 4.35, y + 0.065, 2.35, sty[k][0], sty[k][1]);
  });
  s.addImage({ path: IMG44_3D, x: 7.65, y: TOP, w: 5.08, h: 3.81, objectName: "3D render mission 44",
    altText: "MuJoCo 3D render of mission 44 with robots, concrete obstacles and a dose-coloured floor." });
  txt(s, "Same mission in the MuJoCo 3D world: robots drive physically; radiation is computed at their real positions.", { x: 7.65, y: 5.7, w: 5.08, h: 0.6, fontSize: 12, color: C.text2 });
  s.addNotes("Infrastructure risk is gone: simulator, estimator, baselines, learning methods and evaluation all run and are tested. The open work is the full experiment campaign. Mention here that the prototype was built with an AI coding assistant.");
}

// ================================================================ PART 4
pres.addSection({ title: "Findings" });
{ // 9 corrections
  const s = content("Findings", "Design corrections", "Early checks changed the problem setup in three ways");
  const cs = [["A perfect sensor makes the problem trivial", "Robots located strong sources from the doorway; the trade-off vanished.", "Realistic, location-dependent detector error (20–30%, from instrument calibration tolerances)."],
              ["An average-dose limit misses the danger", "Rare strong-source missions cause all violations; the average stays low, so the limit never activates.", "Limit the chance of exceeding the budget (constraint version B)."],
              ["A 5% limit per robot allows ~20% for the team", "With four robots, per-robot limits add up at team level.", "Split the team's 5% across robots (union bound, as in Chow et al. 2018)."]];
  const cw = (W - 0.7) / 3, cy = TOP, ch = 4.45;
  cs.forEach(([h, found, fix], i) => {
    const x = X0 + i * (cw + 0.35);
    card(s, x, cy, cw, ch, C.background1, HEX.rule, "Correction card");
    numCircle(s, i + 1, x + 0.3, cy + 0.3, 0.48);
    txt(s, h, { x: x + 0.3, y: cy + 0.95, w: cw - 0.6, h: 0.75, fontSize: 17, bold: true });
    chip(s, "FOUND", x + 0.3, cy + 1.85, 1.0, C.accent5, C.accent2);
    txt(s, found, { x: x + 0.3, y: cy + 2.25, w: cw - 0.6, h: 0.9, fontSize: 14 });
    chip(s, "FIX", x + 0.3, cy + 3.15, 0.75, C.accent4, C.accent1);
    txt(s, fix, { x: x + 0.3, y: cy + 3.55, w: cw - 0.6, h: 0.85, fontSize: 14 });
  });
  s.addNotes("These came from checking the setup before spending cluster time. The first would have made every research question meaningless; the second and third are about matching the constraint to RQ1.");
}
{ // 10 results
  const s = content("Findings", "First results", "Going close pays, but the scout often gets stuck");
  s.addChart(pres.charts.BAR, [{ name: "Some robot over budget", labels: ["1–3 TBq", "3–10 TBq", "10–30 TBq", "30–100 TBq"], values: [0, 0, 5, 36] }],
    chartBase({ x: X0, y: TOP, w: 6.6, h: 4.45, barDir: "col", title: "Missions where some robot went over budget, by source strength (%)",
      chartColors: [HEX.red], showLegend: false, showValue: true, dataLabelPosition: "outEnd", valAxisMaxVal: 50, valAxisLabelFormatCode: "0",
      barGapWidthPct: 60, objectName: "Violation by strength chart" }));
  const st = [["96%", "success when a robot got within 2 m of the source, against 70% when none did", C.accent1, C.background2],
              ["1 robot", "sent close by the trained team, learned on its own; an \"everyone approach\" rule sends three and violates in 47%", C.accent1, C.background2],
              ["4 in 10", "approaching robots get stranded next to strong sources (30–100 TBq)", C.accent2, C.accent5]];
  st.forEach(([big, lab, col, fill], i) => {
    const y = TOP + i * 1.5;
    card(s, 7.55, y, 5.18, 1.32, fill, null, "Result stat");
    txt(s, big, { x: 7.85, y: y + 0.15, w: 1.85, h: 1.0, fontFace: THEME.headFontFace, fontSize: 30, bold: true, color: col, valign: "middle" });
    txt(s, lab, { x: 9.75, y: y + 0.15, w: 2.8, h: 1.0, fontSize: 13, valign: "middle" });
  });
  caveat(s, "Early numbers: one short training run per method, 200 test missions. They show the system works; they are not final results.");
  s.addNotes("All violations come from sources above 10 TBq. Below 10 TBq the budget never matters. That is why the main experiments should focus on strong sources.");
}
{ // 11 mission 72
  const s = content("Findings", "Example · mission 72, 72 TBq", "One step too far: a robot strands itself on the last move");
  s.addImage({ path: IMG72_2D, x: X0, y: TOP - 0.05, w: 5.2, h: 4.64, objectName: "Mission 72 map",
    altText: "Mission 72 top view: the red robot walks straight up onto the source and is retired with 0.62 Gy against a 0.10 Gy budget." });
  const H = { bold: true, color: C.text2, fontSize: 12, fill: { color: C.background2 } };
  s.addTable([
    [{ text: "RED ROBOT", options: H }, { text: "DISTANCE", options: H }, { text: "BUDGET USED", options: H }],
    ["Steps 1–18", "15 → 3.2 m", "33%"], ["Step 19", "2.2 m", "47%"], ["Step 20", "1.2 m", "95%"],
    ["Step 21", "0.2 m", "619%"].map((t) => ({ text: t, options: { bold: true, color: C.accent2, fill: { color: C.accent5 } } })),
  ], { x: 6.3, y: TOP, w: 6.43, colW: [2.3, 2.1, 2.03], fontSize: 15, color: C.text1, rowH: 0.46,
    border: { type: "solid", color: HEX.rule, pt: 0.75 }, margin: [0.06, 0.12, 0.06, 0.12], objectName: "Mission 72 table" });
  card(s, 6.3, 4.35, 6.43, 1.95, C.accent6, null, "Root cause box");
  s.addText([
    { text: "Why: ", options: { bold: true, color: C.accent3 } },
    { text: "the mission ends as soon as the source is found, so a robot that strands itself on the final step costs the team almost nothing. The robot follows the rules we gave it.", options: { color: C.text1 } },
  ], { isTextBox: true, objectName: "Root cause text", x: 6.6, y: 4.35, w: 5.85, h: 1.95, fontSize: 16, valign: "middle", margin: 0 });
  txt(s, "Colours: true dose rate. Green star: source. White ×: team estimate.", { x: X0, y: 6.5, w: 5.2, h: 0.3, fontSize: 11, color: C.text2 });
  s.addNotes("Slow approach for 18 steps, then two steps burn most of the budget. At 95% used it steps onto the source and absorbs six times its budget in ten seconds. The mission still counts as a success, which is the real problem.");
}

// ================================================================ PART 5
pres.addSection({ title: "Status and plan" });
{ // 12 blockers
  const s = content("Status and plan", "Open problems", "Where we are stuck, and the plan for each");
  const H = { bold: true, color: C.text2, fontSize: 12, fill: { color: C.background2 } };
  const pr = (p) => ({ text: p, options: { bold: true, align: "center", color: p === "High" ? C.accent2 : p === "Medium" ? C.accent3 : C.text2,
    fill: { color: p === "High" ? C.accent5 : p === "Medium" ? C.accent6 : C.background2 } } });
  s.addTable([
    [{ text: "ISSUE", options: H }, { text: "WHY IT MATTERS", options: H }, { text: "PLAN", options: H }, { text: "PRIORITY", options: H }],
    ["Unsafe team violates only 9% (target ≥ 30%)", "Constraint barely matters; RQ1 weak", "Focus on 10–100 TBq, where it is already 36%", pr("High")],
    ["Robots get stranded after localizing", "Desired behaviour not learned", "Require a safe exit: keep budget for the way out", pr("High")],
    ["Safety-constraint fix untested", "λ stayed ≈ 0 in the first run", "Retrain version B with the team split", pr("High")],
    ["Detector-error size needs a source", "Reviewers may call the noise engineered", "Cite calibration tolerances; sweep 0–30%", pr("Medium")],
    ["No cluster access yet", "Can't run ~370 training runs", "Request HPC access", pr("Medium")],
    ["ROS 2 / Gazebo not installed", "No robotics-stack integration", "Set up on a local Ubuntu machine", pr("Low")],
    ["A few constants unverified", "Small physics inaccuracies", "Check NIST XCOM and Wright et al.", pr("Low")],
  ], { x: X0, y: TOP - 0.05, w: W, colW: [3.65, 3.3, 3.83, 1.35], fontSize: 14, color: C.text1, valign: "middle",
    border: { type: "solid", color: HEX.rule, pt: 0.75 }, rowH: [0.4, 0.6, 0.6, 0.6, 0.6, 0.6, 0.6, 0.6], margin: [0.05, 0.12, 0.05, 0.12], objectName: "Blockers table" });
  s.addNotes("Be direct: three high-priority items, all with a concrete next action. The medium and low items are about credibility and logistics.");
}
{ // 13 timeline
  const s = content("Status and plan", "Next steps", "Fix the task, retrain, then run the full experiments");
  const phases = [["Next 2 weeks", "Safe-exit rule, predicted-dose observation, retrain version B, re-check AC-3 on 10–100 TBq", 0, 2, C.accent1],
                  ["Weeks 3–6", "Full experiments E1–E4 on the cluster (10 seeds each); freeze the environment", 2, 4, C.accent1],
                  ["Weeks 7–10", "Analysis, figures, paper draft", 6, 4, C.accent3],
                  ["Semester 2", "Multiple sources, ROS 2 bridge, real-robot validation", 10, 4, C.text2]];
  const x0 = X0 + 2.6, span = W - 2.6, unit = span / 14;
  for (let w = 0; w <= 14; w += 2) {
    txt(s, w === 14 ? "" : `wk ${w + 1}`, { x: x0 + w * unit, y: TOP, w: 1, h: 0.3, fontSize: 11, color: C.text2 });
  }
  phases.forEach(([lab, d, start, len, col], i) => {
    const y = TOP + 0.5 + i * 1.05;
    txt(s, lab, { x: X0, y, w: 2.45, h: 0.5, fontSize: 16, bold: true, valign: "middle" });
    s.addShape(pres.shapes.ROUNDED_RECTANGLE, { x: x0 + start * unit, y: y + 0.05, w: len * unit, h: 0.42, rectRadius: 0.08,
      fill: { color: col }, line: { type: "none" }, objectName: nm("Phase bar") });
    txt(s, d, { x: X0 + 2.6, y: y + 0.55, w: span, h: 0.45, fontSize: 14, color: C.text1 });
  });
  caveat(s, "Weeks counted from this meeting. Semester 2 timing follows the thesis plan.", 6.55);
  s.addNotes("The first two weeks fix the two high-priority problems before any cluster time is spent. Then the full campaign, then writing.");
}
{ // 14 decisions
  const s = content("Status and plan", "Your input", "Decisions I need from you");
  const qs = ["Contribution framing: a benchmark, a method, or an application study? Which venue (ICRA/IROS, AAMAS, a nuclear-engineering journal)?",
              "Should the mission require robots to exit safely, rather than ending when the source is found?",
              "Is the detector-error approach acceptable, and should someone from nuclear engineering check the simulator's realism?",
              "Real-world testing: simulated radiation on real robots, a light-source analogy, or a low-activity check source?",
              "Cluster access, meeting rhythm, and how you'd like progress reported."];
  qs.forEach((q, i) => {
    const y = TOP + i * 0.92;
    card(s, X0, y, W, 0.78, i % 2 ? C.background1 : C.background2, i % 2 ? HEX.rule : null, "Question card");
    numCircle(s, i + 1, X0 + 0.25, y + 0.14, 0.5);
    txt(s, q, { x: X0 + 1.0, y, w: W - 1.25, h: 0.78, fontSize: 15, valign: "middle" });
  });
  s.addNotes("Spend most of the remaining time here. Question 1 decides how the paper is written; question 2 decides the next two weeks of work.");
}

// ================================================================ BACKUP
pres.addSection({ title: "Backup" });
{
  const s = pres.addSlide({ masterName: "Divider", sectionTitle: "Backup" });
  s.addText("Backup slides", { placeholder: "title" });
  s.addText("Evidence behind the design choices, for questions", { placeholder: "body" });
}
{ // B1 particle filter
  const s = content("Backup", "B1 · Estimator", "The tempered particle filter was chosen by measurement");
  s.addChart(pres.charts.BAR, [
    { name: "Empty room", labels: ["Plain SIR", "Regularised PF", "Tempered PF (chosen)"], values: [15, 92, 100] },
    { name: "5 obstacles", labels: ["Plain SIR", "Regularised PF", "Tempered PF (chosen)"], values: [38, 67, 92] }],
    chartBase({ x: X0, y: TOP, w: 7.6, h: 4.5, barDir: "col", barGrouping: "clustered", title: "Localization success with random-walk robots (%)",
      chartColors: [HEX.teal, HEX.amber], showLegend: true, legendPos: "b", legendFontSize: 12, legendColor: HEX.muted,
      showValue: true, dataLabelPosition: "outEnd", valAxisMinVal: 0, valAxisMaxVal: 110, valAxisLabelFormatCode: "0", objectName: "PF comparison chart" }));
  txt(s, "Why it matters", { x: 8.6, y: TOP, w: 4.1, h: 0.4, fontSize: 17, bold: true, color: C.accent1 });
  s.addText([
    { text: "Strong sources give very sharp readings, so a plain filter collapses onto a few wrong guesses.", options: { bullet: true, breakLine: true } },
    { text: "Tempering splits each update into gentler stages and stays well calibrated (truth inside the 95% region in 83–100% of tests).", options: { bullet: true, breakLine: true } },
    { text: "Cost: about 4.5 ms per environment step after fusing the hot loop with Numba.", options: { bullet: true } },
  ], { isTextBox: true, objectName: "PF notes", x: 8.6, y: TOP + 0.5, w: 4.13, h: 3.9, fontSize: 15, color: C.text1, paraSpaceAfter: 8, margin: 0, valign: "top" });
  caveat(s, "48 missions per bar, 4 robots, 100 steps, 2,000 particles.");
  s.addNotes("If asked why not a simpler filter: the plain one fails on exactly the strong sources this project is about.");
}
{ // B2 noise models
  const s = content("Backup", "B2 · Detector error", "Only location-dependent error makes going close worthwhile");
  const labs = ["No error (original)", "Random per reading, 20%", "Location map, 20%", "Location map, 30% (chosen)"];
  s.addChart(pres.charts.BAR, [
    { name: "Robots stay far (perimeter)", labels: labs, values: [62, 92, 81, 81] },
    { name: "Robots go close (approach)", labels: labs, values: [65, 90, 94, 96] }],
    chartBase({ x: X0, y: TOP, w: 8.2, h: 4.5, barDir: "col", barGrouping: "clustered", title: "Localization success (%)",
      chartColors: [HEX.muted, HEX.teal], showLegend: true, legendPos: "b", legendFontSize: 12, legendColor: HEX.muted,
      showValue: true, dataLabelPosition: "outEnd", valAxisMinVal: 0, valAxisMaxVal: 110, valAxisLabelFormatCode: "0", catAxisLabelFontSize: 11,
      objectName: "Noise model chart" }));
  s.addText([
    { text: "No error: both strategies stop early, often wrong; no trade-off.", options: { bullet: true, breakLine: true } },
    { text: "Random error per reading: averaging many far readings removes it; staying far is as good.", options: { bullet: true, breakLine: true } },
    { text: "Location-dependent error (like wall scatter): re-measuring from the same spot doesn't help, so going close pays.", options: { bullet: true, breakLine: true } },
    { text: "Error size anchored on instrument tolerances: ±20% calibration (CNSC), up to 30% energy dependence.", options: { bullet: true } },
  ], { isTextBox: true, objectName: "Noise notes", x: 9.1, y: TOP, w: 3.63, h: 4.5, fontSize: 14, color: C.text1, paraSpaceAfter: 8, margin: 0, valign: "top" });
  caveat(s, "48 missions per bar, Cs-137. The paper will report results across a sweep of error sizes (0–30%).");
  s.addNotes("This is the answer to 'did you engineer the noise?': the error type is physical, the size comes from calibration tolerances, and the sweep shows sensitivity.");
}
{ // B3 calibration
  const s = content("Backup", "B3 · Budget calibration", "How often dose-unaware search goes over budget");
  const b = ["0.05", "0.1", "0.2", "0.3", "0.5", "1", "2"];
  s.addChart(pres.charts.LINE, [
    { name: "Walk to estimate, Co-60", labels: b, values: [69, 51, 40, 30, 25, 18, 9] },
    { name: "Walk to estimate, Cs-137", labels: b, values: [43, 30, 24, 18, 14, 6, 5] },
    { name: "Greedy (no dose term), Co-60", labels: b, values: [28, 16, 7, 4, 1, 0, 0] },
    { name: "AC-3 target (30%)", labels: b, values: [30, 30, 30, 30, 30, 30, 30] }],
    chartBase({ x: X0, y: TOP, w: 8.2, h: 4.5, title: "Missions over budget (%) by per-robot budget (Gy)",
      chartColors: [HEX.red, HEX.amber, HEX.teal, HEX.muted], lineSize: 2.5, lineDataSymbol: "circle", lineDataSymbolSize: 6,
      lineDash: ["solid", "solid", "solid", "dash"], showLegend: true, legendPos: "b", legendFontSize: 12, legendColor: HEX.muted,
      valAxisLabelFormatCode: "0", valAxisMaxVal: 80, objectName: "Calibration chart" }));
  s.addText([
    { text: "For a dose-unaware policy the dose doesn't depend on the budget, so one run gives the whole curve.", options: { bullet: true, breakLine: true } },
    { text: "Dose is heavy-tailed because source strength spans two decades: median 0.11 Gy, 90th percentile 1.9 Gy.", options: { bullet: true, breakLine: true } },
    { text: "Trained MAPPO is efficient: 9% at 0.1 Gy, below the 30% target.", options: { bullet: true } },
  ], { isTextBox: true, objectName: "Calibration notes", x: 9.1, y: TOP, w: 3.63, h: 4.5, fontSize: 14, color: C.text1, paraSpaceAfter: 8, margin: 0, valign: "top" });
  caveat(s, "96 missions per point, realistic detector error.");
  s.addNotes("This supports the plan on slide 12: rather than lowering budgets to unrealistic values, focus on strong sources where budgets bind.");
}
{ // B4 sim-to-sim
  const s = content("Backup", "B4 · Robotics", "The trained policy transfers to physical motion");
  s.addChart(pres.charts.BAR, [{ name: "Success", labels: ["Grid (2D)", "3D, 0.5 m/s", "3D, 0.15 m/s", "3D, 0.08 m/s"], values: [93, 93, 90, 83] }],
    chartBase({ x: X0, y: TOP, w: 6.6, h: 4.5, barDir: "col", title: "Localization success (%), same 30 missions",
      chartColors: [HEX.teal], showLegend: false, showValue: true, dataLabelPosition: "outEnd", valAxisMinVal: 0, valAxisMaxVal: 100,
      valAxisLabelFormatCode: "0", barGapWidthPct: 60, objectName: "Transfer chart" }));
  const H = { bold: true, color: C.text2, fontSize: 12, fill: { color: C.background2 } };
  s.addTable([
    [{ text: "ROBOT MOTION", options: H }, { text: "STEPS", options: H }, { text: "TRACKING ERROR", options: H }],
    ["Grid (2D)", "17.8", "0"], ["3D, 0.5 m/s", "17.8", "0.07 m"], ["3D, 0.15 m/s", "17.4", "0.09 m"],
    ["3D, 0.08 m/s", "26.0", "0.53 m"].map((t) => ({ text: t, options: { bold: true, fill: { color: C.accent6 } } })),
  ], { x: 7.55, y: TOP, w: 5.18, colW: [2.0, 1.2, 1.98], fontSize: 15, color: C.text1, rowH: 0.46,
    border: { type: "solid", color: HEX.rule, pt: 0.75 }, margin: [0.06, 0.12, 0.06, 0.12], objectName: "Transfer table" });
  txt(s, "When the robot is too slow to reach the next cell in 10 s, success drops and missions take ~45% longer. Next: randomise motion speed during training.",
    { x: 7.55, y: 4.35, w: 5.18, h: 1.6, fontSize: 15 });
  caveat(s, "MuJoCo 3D world; radiation computed at the robots' real positions. 30 missions per setting: indicative only.");
  s.addNotes("This is the robotics-facing result: physical motion, collisions and tracking error, with one shared radiation model.");
}
{ // B5 literature
  const s = content("Backup", "B5 · Literature anchors", "Where each design choice comes from");
  const L = [["CNSC survey-meter rules", "±20% calibration, ≤ 30% energy dependence", "Size of the detector error"],
             ["Kennedy & O'Hagan 2001", "Model discrepancy as a smooth random field", "Location-dependent error model"],
             ["Chow et al., JMLR 2018", "Joint chance constraint via sum of individual risks", "Splitting the team's 5% across robots"],
             ["Ono & Williams 2008", "Iterative risk allocation", "Semester-2 idea: adaptive split for RQ3"],
             ["Saute RL, ICML 2022", "Remaining budget in the state; never exceed it", "Related baseline to discuss"],
             ["Proctor et al. 2021 (RAD-A2C)", "RL source search, weak sources", "Closest prior RL work"]];
  const cw = (W - 0.7) / 3, ch = 2.1;
  L.forEach(([who, what, use], i) => {
    const x = X0 + (i % 3) * (cw + 0.35), y = TOP + Math.floor(i / 3) * (ch + 0.3);
    card(s, x, y, cw, ch, i % 2 ? C.background2 : C.background1, i % 2 ? null : HEX.rule, "Literature card");
    txt(s, who, { x: x + 0.3, y: y + 0.25, w: cw - 0.6, h: 0.4, fontSize: 16, bold: true });
    txt(s, what, { x: x + 0.3, y: y + 0.72, w: cw - 0.6, h: 0.65, fontSize: 14 });
    txt(s, "→ " + use, { x: x + 0.3, y: y + 1.45, w: cw - 0.6, h: 0.5, fontSize: 14, bold: true, color: C.accent1 });
  });
  s.addNotes("If asked 'what do others do?', each card links a design choice to its source.");
}
{ // B6 reproducibility
  const s = content("Backup", "B6 · Reproducibility", "Built so every number can be regenerated");
  const R = [["60", "automated tests: physics, estimator, environment, baselines, algorithms, 3D world"],
             ["1,000", "fixed test missions: same rooms, sources and noise for every method"],
             ["10", "training seeds per method, with confidence intervals (Wilson, bootstrap IQM)"],
             ["~370", "cluster jobs generated from the experiment matrix, with automatic resume"],
             ["1", "configuration system (Hydra): no hard-coded settings; pinned package versions"]];
  R.forEach(([n, t], i) => {
    const y = TOP + i * 0.92;
    txt(s, n, { x: X0, y, w: 1.9, h: 0.75, fontFace: THEME.headFontFace, fontSize: 30, bold: true, color: C.accent1, valign: "middle" });
    txt(s, t, { x: X0 + 2.05, y, w: W - 2.05, h: 0.75, fontSize: 16, valign: "middle" });
  });
  s.addNotes("Reproducibility was a requirement from the start: identical test missions and seeds make every comparison fair.");
}

(async () => {
  await pres.writeFile({ fileName: OUT });
  await applyTheme(OUT, THEME);
  console.log("wrote", OUT);
})();

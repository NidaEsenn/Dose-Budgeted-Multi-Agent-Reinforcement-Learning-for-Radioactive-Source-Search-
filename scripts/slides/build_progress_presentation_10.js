const pptxgen = require("pptxgenjs");
const { applyTheme } = require("/root/.claude/skills/synced/02812373-138d-4a58-874b-33e46fa50871_5ae0fb7b-f204-4157-8b07-59d0450a2433/pptx/scripts/apply_theme.js");

const [OUT, IMG72_2D, IMG72_3D, IMG44_3D, STILLS] = process.argv.slice(2);

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

pres.addSection({ title: "Problem" });
{ // 1 title
  const s = pres.addSlide({ masterName: "Title", sectionTitle: "Problem" });
  s.addText("MASTER'S THESIS · PROGRESS UPDATE", { placeholder: "kicker" });
  s.addText("Dose-Budgeted Multi-Robot Source Search", { placeholder: "title" });
  s.addText("Can a robot team learn to find a lost radioactive source without any robot exceeding its own radiation budget?", { placeholder: "body" });
  s.addText([{ text: "Nida Esen", options: { bold: true, color: C.text1, breakLine: true } },
             { text: "Advisor: Prof. [Name] · Northeastern University · November 2026" }], { placeholder: "meta" });
  s.addImage({ path: IMG72_3D, x: 6.95, y: 1.45, w: 5.85, h: 3.66, objectName: "3D mission render",
    altText: "3D render of a simulated mission: a room with concrete obstacles, robots, and the floor coloured by radiation dose rate." });
  txt(s, "MuJoCo 3D world: a robot approaches the source (glow). Floor colour: true dose rate.", { x: 6.95, y: 5.2, w: 5.85, h: 0.35, fontSize: 11, color: C.text2 }, "Image caption");
  s.addNotes("One-sentence opener: this thesis asks whether a team of robots can learn to find a strong radioactive source while every robot stays within its own radiation budget.");
}
{ // 2 the problem we're solving (visual)
  const s = content("Problem", "The problem", "Find the source without burning out the robots");
  // diagram panel
  card(s, X0, TOP, 7.0, 4.75, C.background2, null, "Diagram panel");
  const sx = 2.35, sy = 3.45;
  [[1.35, 88], [0.98, 80], [0.62, 68], [0.32, 50]].forEach(([r, t], i) => {
    s.addShape(pres.shapes.OVAL, { x: sx - r, y: sy - r, w: 2 * r, h: 2 * r, objectName: nm("Dose ring"),
      fill: { color: C.accent2, transparency: t }, line: { type: "none" } });
  });
  s.addShape(pres.shapes.OVAL, { x: sx - 0.12, y: sy - 0.12, w: 0.24, h: 0.24, fill: { color: C.accent2 }, line: { type: "none" }, objectName: "Source dot" });
  txt(s, "Hidden source\n(location and strength unknown)", { x: sx - 1.3, y: sy + 0.16, w: 2.6, h: 0.5, fontSize: 11, color: C.accent2, bold: true, align: "center" }, "Source label");
  s.addShape(pres.shapes.RECTANGLE, { x: 5.65, y: 2.25, w: 0.4, h: 1.35, fill: { color: "9AA0A1" }, line: { type: "none" }, objectName: "Obstacle" });
  txt(s, "wall", { x: 5.45, y: 3.65, w: 0.8, h: 0.28, fontSize: 10, color: C.text2, align: "center" }, "Obstacle label");
  const robots = [
    [3.0, 3.05, "Close", "strong signal", 0.15, C.accent2],
    [4.5, 4.05, "Middle", "useful signal", 0.6, C.accent3],
    [6.85, 2.6, "Far", "weak, noisy signal", 0.95, C.accent1],
  ];
  robots.forEach(([rx, ry, lab, sig, left, col], i) => {
    s.addShape(pres.shapes.OVAL, { x: rx - 0.2, y: ry - 0.2, w: 0.4, h: 0.4, fill: { color: col }, line: { color: HEX.white, width: 2 }, objectName: nm("Robot") });
    txt(s, `R${i + 1}`, { x: rx - 0.2, y: ry - 0.2, w: 0.4, h: 0.4, fontSize: 10, bold: true, color: C.background1, align: "center", valign: "middle" }, "Robot id");
  });
  s.addShape(pres.shapes.LINE, { x: X0 + 0.3, y: 5.0, w: 6.4, h: 0, line: { color: HEX.rule, width: 1 }, objectName: "Legend separator" });
  robots.forEach(([rx, ry, lab, sig, left, col], i) => {
    const y = 5.12 + i * 0.45, x = X0 + 0.3, gx = X0 + 3.55, gw = 1.7;
    s.addShape(pres.shapes.OVAL, { x, y: y + 0.08, w: 0.26, h: 0.26, fill: { color: col }, line: { type: "none" }, objectName: nm("Legend robot") });
    txt(s, `R${i + 1} · ${lab}: ${sig}`, { x: x + 0.38, y, w: 2.85, h: 0.42, fontSize: 12, bold: true, valign: "middle" });
    s.addShape(pres.shapes.ROUNDED_RECTANGLE, { x: gx, y: y + 0.1, w: gw, h: 0.22, rectRadius: 0.05, fill: { color: C.background1 }, line: { color: HEX.rule, width: 0.75 }, objectName: nm("Budget gauge") });
    s.addShape(pres.shapes.ROUNDED_RECTANGLE, { x: gx, y: y + 0.1, w: gw * left, h: 0.22, rectRadius: 0.05, fill: { color: col }, line: { type: "none" }, objectName: nm("Budget left") });
    txt(s, `${Math.round(left * 100)}% budget left`, { x: gx + gw + 0.12, y, w: 1.4, h: 0.42, fontSize: 11, color: C.text2, valign: "middle" });
  });
  // the task
  txt(s, "The task", { x: 8.05, y: TOP, w: 4.6, h: 0.45, fontSize: 20, bold: true, color: C.accent1 });
  const task = [["Find the source", "Estimate its position (within 1 m) and strength from the team's readings."],
                ["Keep every robot within its budget", "Each robot has its own dose limit; a robot that reaches it is lost."],
                ["Decide who goes close, and for how long", "Close readings are the most informative and the most damaging."]];
  task.forEach(([h, d], i) => {
    const y = TOP + 0.6 + i * 1.32;
    numCircle(s, i + 1, 8.05, y + 0.02, 0.46);
    txt(s, h, { x: 8.7, y, w: 4.03, h: 0.42, fontSize: 16, bold: true });
    txt(s, d, { x: 8.7, y: y + 0.42, w: 4.03, h: 0.75, fontSize: 14, color: C.text2 });
  });
  caveat(s, "The team learns this behaviour by trial and error in simulation (multi-agent reinforcement learning with one safety constraint per robot).", 6.7);
  s.addNotes("This slide is the whole problem in one picture. R1 near the source gets the best signal but its budget drains in seconds; R3 far away is safe but its readings are weak. The team has to find the source, keep every robot within budget, and decide who takes the risk.");
}
{ // 3 trade-off + motivation
  const s = content("Problem", "Why it is hard", "The best information is exactly where the danger is");
  const d = [0.5, 1, 1.5, 2, 3, 4, 5];
  const mins = d.map((x) => +(0.1 / (3.51e-4 * 5e4 / (x * x + 0.09)) * 60).toFixed(2));
  s.addChart(pres.charts.LINE, [{ name: "Minutes until a 0.1 Gy budget is used", labels: d.map((x) => `${x} m`), values: mins }],
    chartBase({ x: X0, y: TOP, w: 7.2, h: 4.55, title: "Minutes until a 0.1 Gy budget is used (50 TBq Co-60)",
      chartColors: [HEX.red], lineSize: 3, lineDataSymbol: "circle", lineDataSymbolSize: 8, showLegend: false,
      showValue: true, dataLabelPosition: "t", dataLabelFormatCode: "0.0", valAxisLabelFormatCode: "0", valAxisMinVal: 0,
      showCatAxisTitle: true, catAxisTitle: "Distance from the source", catAxisTitleFontSize: 12, catAxisTitleColor: HEX.muted,
      objectName: "Time to budget chart" }));
  txt(s, "Real strong-source incidents", { x: 8.2, y: TOP, w: 4.5, h: 0.4, fontSize: 16, bold: true, color: C.accent1 });
  const ev = [["1987", "Goiânia, Brazil · 50.9 TBq Cs-137"], ["2000", "Samut Prakan, Thailand · 15.7 TBq Co-60"], ["2013", "Hueypoxtla, Mexico · 111 TBq Co-60"]];
  ev.forEach(([yr, t], i) => {
    const y = TOP + 0.5 + i * 0.68;
    card(s, 8.2, y, 4.53, 0.56, C.background2, null, "Incident chip");
    txt(s, yr, { x: 8.4, y, w: 0.8, h: 0.56, fontFace: THEME.headFontFace, fontSize: 16, bold: true, color: C.accent2, valign: "middle" });
    txt(s, t, { x: 9.25, y, w: 3.4, h: 0.56, fontSize: 13, valign: "middle" });
  });
  card(s, 8.2, 4.7, 4.53, 1.65, C.accent5, null, "Robot failure box");
  s.addText([
    { text: "Robots fail too: ", options: { bold: true, color: C.accent2 } },
    { text: "Fukushima robot cameras and lidar failed at about 120 Gy, and a TEPCO cleaning robot was withdrawn after about two hours.", options: { color: C.text1 } },
  ], { isTextBox: true, objectName: "Robot failure text", x: 8.45, y: 4.7, w: 4.05, h: 1.65, fontSize: 14, valign: "middle", margin: 0 });
  caveat(s, "One metre from a strong source uses a robot's whole budget in about 20 seconds; four metres gives it about five minutes.");
  s.addNotes("Read the curve left to right, then point to the incidents: these sources are real and this strong. Robot dose is a mission-limiting constraint.");
}
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
pres.addSection({ title: "Approach" });
{ // 5 approach + status
  const s = content("Approach", "Approach and status", "Simulate, estimate, learn, check safety, evaluate");
  const st = [["Simulator", "Room, walls, 3–6 robots, radiation physics with realistic detector error"],
              ["Shared estimate", "Particle filter over the source's position and strength"],
              ["Learning team", "MAPPO with a safety price λ for each robot"],
              ["Safety backup", "Shield that blocks moves predicted to exceed the budget"],
              ["Evaluation", "1,000 fixed test missions, 10 seeds, confidence intervals"]];
  const n = 5, gap = 0.33, bw = (W - gap * (n - 1)) / n, by = TOP, bh = 2.6;
  st.forEach(([h, d], i) => {
    const x = X0 + i * (bw + gap);
    card(s, x, by, bw, bh, C.background2, null, "Approach step");
    numCircle(s, i + 1, x + 0.22, by + 0.22, 0.46);
    txt(s, h, { x: x + 0.22, y: by + 0.85, w: bw - 0.44, h: 0.4, fontSize: 16, bold: true });
    txt(s, d, { x: x + 0.22, y: by + 1.3, w: bw - 0.44, h: 1.25, fontSize: 14 });
    if (i < n - 1) arrow(s, x + bw + 0.03, by + bh / 2, gap - 0.06, 0);
  });
  txt(s, "Built and tested", { x: X0, y: 4.75, w: 3, h: 0.35, fontSize: 14, bold: true, color: C.accent1 });
  const done = ["Simulator", "Particle filter", "5 baselines + shield", "MAPPO / MAPPO-L", "MuJoCo 3D world", "60 tests"];
  let cx = X0;
  done.forEach((c) => { const w = 0.3 + c.length * 0.1; chip(s, c, cx, 5.15, w, C.accent4, C.accent1); cx += w + 0.15; });
  txt(s, "Remaining", { x: X0, y: 5.65, w: 3, h: 0.35, fontSize: 14, bold: true, color: C.text2 });
  const todo = ["Full experiments (10 seeds, ~370 runs)", "ROS 2 bridge", "Real-robot tests"];
  cx = X0;
  todo.forEach((c) => { const w = 0.3 + c.length * 0.1; chip(s, c, cx, 6.05, w, C.background2, C.text2); cx += w + 0.15; });
  s.addNotes("Walk the five boxes. Then the two chip rows: the infrastructure is built and tested; what remains is the experiment campaign and the robotics integration. Mention that the prototype was built with an AI coding assistant.");
}
{ // 6 RQs + hypotheses
  const s = content("Approach", "Research questions and hypotheses", "Three questions, each with a testable hypothesis");
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
{ // 9 mission 72 (2D map + 3D strip)
  const s = content("Findings", "Example · mission 72, 72 TBq", "One step too far: a robot strands itself on the last move");
  s.addImage({ path: IMG72_2D, x: X0, y: TOP - 0.05, w: 4.5, h: 4.02, objectName: "Mission 72 map",
    altText: "Mission 72 top view: the red robot walks straight up onto the source and is retired with 0.62 Gy against a 0.10 Gy budget." });
  txt(s, "Top view: robot paths over the true dose rate. Green star: source.", { x: X0, y: 5.95, w: 4.5, h: 0.4, fontSize: 11, color: C.text2 });
  const strip = [["19", "2.2 m from the source", "47% of budget used", C.accent3],
                 ["20", "1.2 m from the source", "95% of budget used", C.accent2],
                 ["21", "on the source", "619%: retired", C.accent2]];
  const x1 = 5.45, sw = (12.73 - x1 - 0.3) / 3, sh = sw / 1.6;
  strip.forEach(([st, dist, used, col], i) => {
    const x = x1 + i * (sw + 0.15);
    s.addImage({ path: `${STILLS}/mission72_step${st}_closeup_crop.png`, x, y: TOP, w: sw, h: sh, objectName: nm("Mission 72 3D still"),
      altText: `3D close-up of mission 72 at step ${st}: the red robot ${dist}.` });
    txt(s, `Step ${st}`, { x, y: TOP + sh + 0.1, w: sw, h: 0.35, fontSize: 15, bold: true, color: col });
    txt(s, `${dist}\n${used}`, { x, y: TOP + sh + 0.45, w: sw, h: 0.6, fontSize: 13, color: C.text1 });
  });
  card(s, x1, 4.75, 12.73 - x1, 1.6, C.accent6, null, "Root cause box");
  s.addText([
    { text: "Why: ", options: { bold: true, color: C.accent3 } },
    { text: "the mission ends as soon as the source is found, so a robot that strands itself on the final step costs the team almost nothing. The robot follows the rules we gave it.", options: { color: C.text1 } },
  ], { isTextBox: true, objectName: "Root cause text", x: x1 + 0.3, y: 4.75, w: 12.73 - x1 - 0.6, h: 1.6, fontSize: 15, valign: "middle", margin: 0 });
  s.addNotes("Left: the paths seen from above. Right: the same red robot in the 3D world. At step 20 it has used 95% of its budget, yet it steps onto the source and takes six times its budget in ten seconds. The mission still counts as a success.");
}
pres.addSection({ title: "Plan" });
{ // 10 stuck + next
  const s = content("Plan", "Open problems and next steps", "Where we are stuck, and what comes next");
  txt(s, "Top blockers", { x: X0, y: TOP, w: 5.8, h: 0.4, fontSize: 17, bold: true, color: C.accent2 });
  const bl = [["The unsafe team rarely exceeds budgets (9%)", "The constraint barely matters yet.", "Focus on 10–100 TBq sources (already 36%)."],
              ["Robots get stranded after finding the source", "The behaviour we want isn't learned.", "Require a safe exit: keep budget for the way out."],
              ["The safety-constraint fix is untested", "λ stayed near zero in the first run.", "Retrain version B with the team-level split."]];
  bl.forEach(([h, why, plan], i) => {
    const y = TOP + 0.5 + i * 1.4;
    card(s, X0, y, 6.2, 1.25, C.background1, HEX.rule, "Blocker card");
    chip(s, "HIGH", X0 + 0.25, y + 0.2, 0.75, C.accent5, C.accent2);
    txt(s, h, { x: X0 + 1.15, y: y + 0.13, w: 4.9, h: 0.45, fontSize: 15, bold: true, valign: "middle" });
    txt(s, why, { x: X0 + 1.15, y: y + 0.58, w: 4.9, h: 0.3, fontSize: 13, color: C.text2 });
    s.addText([{ text: "Plan: ", options: { bold: true, color: C.accent1 } }, { text: plan, options: { color: C.text1 } }],
      { isTextBox: true, objectName: nm("Blocker plan"), x: X0 + 1.15, y: y + 0.88, w: 4.9, h: 0.35, fontSize: 13, margin: 0, valign: "top" });
  });
  txt(s, "Next steps", { x: 7.25, y: TOP, w: 5.4, h: 0.4, fontSize: 17, bold: true, color: C.accent1 });
  const ph = [["Next 2 weeks", "Safe-exit rule, retrain version B, re-check on strong sources", C.accent1],
              ["Weeks 3–6", "Full experiments on the cluster, 10 seeds each", C.accent1],
              ["Weeks 7–10", "Analysis, figures, paper draft", C.accent3],
              ["Semester 2", "Multiple sources, ROS 2 bridge, real robots", C.text2]];
  const lx = 7.45;
  s.addShape(pres.shapes.LINE, { x: lx, y: TOP + 0.7, w: 0, h: 4.05, line: { color: HEX.rule, width: 2 }, objectName: "Timeline axis" });
  ph.forEach(([when, what, col], i) => {
    const y = TOP + 0.55 + i * 1.08;
    s.addShape(pres.shapes.OVAL, { x: lx - 0.14, y: y + 0.1, w: 0.28, h: 0.28, fill: { color: col }, line: { color: HEX.white, width: 2 }, objectName: nm("Timeline dot") });
    txt(s, when, { x: lx + 0.35, y, w: 4.9, h: 0.4, fontSize: 15, bold: true });
    txt(s, what, { x: lx + 0.35, y: y + 0.4, w: 4.9, h: 0.55, fontSize: 14, color: C.text2 });
  });
  caveat(s, "Also open: a literature value for the detector-error size, cluster access, ROS 2 setup on a local machine, and checking a few physical constants.", 6.55);
  s.addNotes("Three blockers, each with a concrete plan. The first two weeks fix them before any cluster time is spent. Close by asking for feedback on the safe-exit rule and the contribution framing.");
}
(async () => {
  await pres.writeFile({ fileName: OUT });
  await applyTheme(OUT, THEME);
  console.log("wrote", OUT);
})();

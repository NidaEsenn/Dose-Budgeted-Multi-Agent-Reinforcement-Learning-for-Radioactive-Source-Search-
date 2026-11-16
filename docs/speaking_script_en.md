# Speaking script: Safe Cooperative Radiation Source Search

*For `docs/Safe_Cooperative_Radiation_Source_Search_v3.pptx`. About 11 minutes. Short sentences, plain words. Notes in [brackets] are for you, not to read aloud.*

---

## Slide 1: Title (~30 s)

Hi everyone, I'm Nida.

Imagine a strong radioactive source is lost inside a building. It is too dangerous to send people in, so we send a team of robots to find it.

But there is a problem. The closer a robot gets to the source, the better its measurements are, and also the more radiation it takes. Radiation slowly damages the robot's electronics.

So my question is: **how can a team of robots find the source, while every robot keeps enough radiation budget to get back out?**

The picture on the right is my 3D simulator. The brighter the floor, the stronger the radiation.

---

## Slide 2: Why it matters (~50 s)

This is a real problem.

In 2017, at Fukushima, a cleaning robot went into a damaged reactor. After about two hours, its cameras started to fail, and it had to come back. The next robot, called "Scorpion", got stuck in the same reactor and was left there.

Lost or stolen radioactive sources are also a real issue. The International Atomic Energy Agency recorded 146 such incidents in 2022 alone.

The lesson is simple: **a robot has to leave before its radiation budget runs out.** If it doesn't, we lose the robot and everything it learned.

---

## Slide 3: The problem in three steps (~1 min)

Here is the problem in three steps.

**Step one: enter.** The robots come in through the only door. We don't know where the source is, or how strong it is.

**Step two: measure.** The robots spread out and measure radiation. They share every reading, so the team's guess gets better over time. But the most useful readings are close to the source, and that is exactly where the radiation is strongest. **Information and danger are in the same place.**

**Step three: decide.** Every robot keeps asking: should I keep searching, or should I go home while I still can? In the picture, the purple robot has used most of its budget, so it heads for the door. The other two keep searching.

One important point: **going home also costs radiation**, because the robot has to drive back through the radiation. So a robot must turn around early, not when its budget is already empty.

---

## Slide 4: The simulated mission (~1 min)

This slide shows the rules of my simulation.

The room is 20 by 20 meters, with one door and some walls. The walls block part of the radiation. Inside there is one strong source, Cobalt-60. We don't know its position or its strength. The team has 2 to 6 robots, and they share all their readings.

The physics is realistic. Radiation gets weaker with distance. If you are twice as far, you get four times less. The sensor readings are noisy, like real ones. I also added about 30% model error. Without that error, the problem was too easy: the robots could find the source from far away.

Each robot knows its own total radiation, like a real dosimeter. Each robot has a budget of 0.1 gray. This is a chosen safety limit, not the point where the hardware breaks.

**Success** means the team names a location within 1 meter of the real source. A **safety failure** means any robot goes over its budget, or gets stuck inside. **My target: safety failures in at most 5% of missions.** Every result is measured over 300 test missions.

---

## Slide 5: What others have done (~1 min)

Robots for radiation search is an active research field. So I checked 428 papers to see what is really new.

Proctor and colleagues used learning plus a smart estimator, but with only one robot. Totten extended this to robot teams, but the robots' own radiation was not limited. Huo and colleagues, in 2026, used robots with different radiation tolerance. But the roles were fixed in advance, and nothing was kept for the trip home.

On the safety side, MAPPO-Lagrangian adds a cost limit to robot teams. But it only limits the average cost, while I need almost zero missions where any robot fails. The closest method is SEA-MAPPO from 2026. It blocks moves that would drain a robot's battery. So I am not claiming that blocking unsafe moves is new.

**What is different here:** a battery can be measured directly. Radiation danger cannot. It has to be estimated from the team's uncertain guess. And the trip home costs radiation too.

[If asked: the newest close paper is Dec-MARVEL (2026). It has a budget and a return reserve, but its budget is just travel distance. It does not depend on guessing where a hidden source is.]

---

## Slide 6: What I have built (~1 min)

My system has four parts.

**One:** a fast simulator for many robots and a radiation source.

**Two:** a shared guess of where the source is. It keeps 2,000 possible answers at the same time, and every new reading updates them. The picture comes from a real test mission. At the start, the guesses are everywhere. After about two minutes, they form a narrow band pointing at the source. At the end, they are a tight cluster right on the source.

**Three:** the robot's decision-maker. Either a learning method called MAPPO, or one of three simple hand-written rules: go where you learn the most, sweep the edges, or everyone goes straight to the source.

**Four:** the safety layer. I'll explain it on the next slide.

On top of this, I set up a 3D simulator, scripts for the university supercomputer, and 76 automatic tests. I also added my advisor's feedback: each robot tracks its own radiation, keeps a reserve for going home, and shares its readings at every step.

---

## Slide 7: The safety layer (~1 min 15 s) [KEY SLIDE: slow down]

This is the core idea of my thesis.

Before every move, each robot checks one simple rule:

**radiation so far + radiation for the next step + radiation for the trip home must stay under 0.1 gray.**

The robot does not know exactly where the source is. So it does not plan for the average case. It plans for a bad case. It looks at 32 possible source positions and strengths, and it uses one of the worst. In simple words, the robot thinks: "the source might be stronger or closer than I think."

If a move breaks the rule, it is blocked. The robot can always choose **"withdraw"**: it drives out of the room and still shares the team's reward.

The plot on the right is one robot from a real test mission. The black line is the radiation it really took. The dashed orange line is what the rule checks. When the dashed line would go over the budget, the robot withdraws. The trip home is added, and then its radiation stays flat.

Notice that this robot left with only 0.065 of its 0.1 gray used. The rule is careful. That care has a cost, and I'll come back to it on slide 9.

One honest note: this is a careful safety rule, not a mathematical guarantee. That's why I measure the real failure rate over 300 missions.

---

## Slide 8: Results so far (~1 min 15 s) [KEY SLIDE: slow down]

Let me go from left to right. One note first: the two learning methods on the left come from my earlier rules, before I added the withdraw option. The other three bars use the current rules.

Standard learning, **MAPPO**, finds the source 85% of the time. But in 29% of missions, a robot goes over its budget.

**MAPPO-Lagrangian** puts a price on radiation. Failures drop to about 6%, but success falls to 10%. The robots learn to stay about 13 meters away from the source, and time runs out. I call this the robots becoming **too timid**.

The simple **greedy rule** behaves like MAPPO: 85% success, 31% failures.

Now the main result. When I add my safety layer and the withdraw option to the greedy rule, **failures drop from 31% to 4.3%**. That is 13 out of 300 missions. And **success only goes from 85% to 84%.**

If the same rule plans for the average case instead of the bad case, failures are 14.7%. So **planning for the bad case really matters.**

To be honest: the uncertainty range for 4.3% goes from 2.5% to 7.3%. So it is below 5% on average, but I can't prove it yet. And this result comes from a hand-written rule, not from learning.

---

## Slide 9: What is not solved yet (~1 min)

This chart shows the biggest open problem.

Each dot is a different setting of the safety layer, 13 settings in total. The blue dot is my main result: 84% success, 4.3% failures. No setting beats it on both success and safety. The most careful setting has only 1 failure in 300 missions, but success drops to 65%. **Being safer costs success.**

The second problem: the team's guess is **overconfident**. When it says "I'm 90% sure the source is here", it is right only about 52 to 65% of the time. In 12 to 19% of missions, the team confidently names the wrong spot. The likely reason: the errors in my simulator are linked across nearby spots, but the estimator treats every error as separate, so it trusts itself too much. Fixing this made the guess more honest, but it did not improve the trade-off between safety and success.

Finally, 5% is not proven yet, and everything is still in simulation.

---

## Slide 10: Plan (~1 min)

So here is the main question for the rest of my thesis: **a simple rule plus my safety layer already works. Can a learning team do better, with the same safety layer?** In other words, can learning push the curve on the last slide up and to the left?

Without safety, learning and the simple rule perform about the same, 85% success. So this is a fair test.

**Step one, the pilot**, is running right now on the university supercomputer: three methods, three runs each. **Step two** is the full study: ten runs each and more than 3,000 test missions. That is about what we need to show that a rate near 4% is really below 5%. **Step three:** teams where robots have different budgets. Does the team send the robot with the most budget left to take the risky readings? **Step four:** fix the overconfident guess. About 20 papers I read call this an open problem. **Step five:** a test on real robots, using simulated radiation or a weak test source.

The simple rule might stay competitive. That would also be a useful result.

To close, one sentence: **safe search means every robot keeps enough radiation to come home.** Thank you. I'm happy to take questions.

---

## Likely questions, with short answers

| Question | Short answer |
|---|---|
| If the simple rule works, why use learning? | The rule only slides along the safety–success curve. The question is whether a learning team, working together, can push the curve forward. The pilot is running now. |
| Why is 0.1 gray so low? | Radiation scales with source strength, so what matters is budget divided by source strength. 0.1 gray with my sources is the same balance as 100 gray with a source 1,000 times stronger, like an industrial irradiator or reactor debris. Also, a robot is reused, so each mission gets only a share of its lifetime. |
| Can a robot break before its budget runs out? | Yes. Sensors can glitch at very high radiation levels, and parts vary. My model simplifies this. I plan to test random budgets and noisier sensors near the source. |
| Why the "bad case" (97th percentile)? | Planning for the average case gave 14.7% failures; planning for the bad case gave 4.3%. A common alternative is to average over the worst few cases (called CVaR); I will test that too. |
| Is this a guarantee? | No, it is a careful rule. I measure the real failure rate, and the full study with 3,000+ missions will make the uncertainty range much smaller. |
| Any real-robot tests? | Not yet. I tested transfer to a 3D physics simulator; real robots are the last step of the plan. |

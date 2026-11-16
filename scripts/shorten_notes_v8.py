"""Trim the speaker notes of v8 slides 5, 7 and 8 to about one minute each (in place)."""
import sys
from pptx import Presentation

path = sys.argv[1]
p = Presentation(path)
NOTES = {
    5: "(~1 min)\n"
       "Every 10 seconds, each robot does three things: estimate, decide, check.\n"
       "Estimate: where is the source? The team keeps 2,000 guesses. Guesses that fit the readings get stronger, "
       "wrong ones fade. When they all sit within about 30 cm, the team says: found it.\n"
       "Decide: where do I go next? Either a simple greedy rule, which goes where it learns the most, "
       "or MAPPO, where the robots learn by practice.\n"
       "Check: is this move safe? Dose so far, plus the next step, plus the way home, must stay under 0.1 gray. "
       "The robot plans for a bad case, not the average. If the move isn't safe, it goes home.",
    7: "(~1 min)\n"
       "Same 1,000 test missions for every method. Blue is success, orange is safety failures.\n"
       "Without safety, robots fail a lot: 30% for greedy, 19% for MAPPO.\n"
       "My reserve rule fixes that: 85% success, and failures drop to 4%, under my 5% target. "
       "Planning for the average case instead gives 15%, so the bad case matters.\n"
       "The learned team, MAPPO-Lagrangian, also gets 4% failures, with about 80% success. "
       "Before the withdraw action, it only found the source 10% of the time. And it gives fewer wrong answers.\n"
       "Next: MAPPO with my reserve layer, still training.",
    8: "(~1 min)\n"
       "This is the main open problem: making the rule safer also makes it find the source less often.\n"
       "Each dot is one setting of my safety layer, tested on 300 missions. Left means fewer failures, up means more success, "
       "so top-left is best. The red line is my 5% target.\n"
       "The blue dot is my reference: 84% success, 4.3% failures. When I make the rule more careful, along the orange line, "
       "failures go down, but success goes down too. The safest one fails only once in 300 missions, but finds the source "
       "only 65% of the time.\n"
       "So safety costs success. The goal for learning is to push this curve up and to the left.",
}
for n, text in NOTES.items():
    p.slides[n - 1].notes_slide.notes_text_frame.text = text
    print(n, len(text.split()), "words")
p.save(path)

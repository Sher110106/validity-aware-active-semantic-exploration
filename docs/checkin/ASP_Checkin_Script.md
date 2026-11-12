# Speaker script: check-in (4 slides, 5 minutes)

About 600 words. *Italics* are stage directions; don't read them aloud. Slides: `open-slide/slides/asp-checkin`.

---

## Slide 1: Validity-aware active semantic exploration (about 60 s)

A robot enters a home it has never seen and has to map it on a fixed path budget. Active Semantic Perception, our base paper, asks a language model to guess the rooms and objects the robot hasn't seen yet. Then it drives to where those guesses disagree.

*(Point to the three columns.)*

At midsem we showed that 81% of the nodes the model added broke simple physical rules. Our plan was a validity layer: check the guesses, vote across them, calibrate the votes, and add a risk term to the view score. Since then we built that layer and tested it. The results made us ask a harder question: do the guesses help at all?

---

## Slide 2: Filtering helped only by deleting the guesses (about 85 s)

*(Point to the table.)*

We ran the author's pipeline for 120 m in three homes and applied each policy to the same saved guesses. Our strictest filter keeps a guess only if all four completions agree. It raised F1 in every home, from 0.48 to 0.52 in the first.

*(Point to the last column.)*

But look at the last column. If we delete every guess, we get the same score, within 0.0002. The filter kept 19 of almost 9,000 predicted nodes. So the gain came from removing the guesses, not from choosing good ones. Calibration didn't help, and the risk term was nearly inactive or chose worse views.

*(Point to the chart.)*

Here's why. We took 8 saved inputs from our live runs and checked how often a predicted object lands near a real object with the same label. Within half a metre, DeepSeek scores 1.7% and random guesses of the same shape score 1.5%, so it is no better than chance. At one metre it does a little better. Gemini, a stronger model, scores four to five times chance on the same inputs. That test is small and exploratory.

---

## Slide 3: Human labels and a random-guess placebo (about 85 s)

*(Point to the left column.)*

We also fixed our yardstick. At midsem, our ground truth was the map from a long frontier run. That map rewards the frontier robot, because it's scored against its own map. So we built reference graphs from the human annotation that ships with HM3D. In scene 00853, our September ASP run goes from 21% behind the frontier robot to 10% ahead of it.

Second, we built a placebo. It's the same live pipeline, but the model's guesses are swapped for random ones of the same count and size. If the guesses matter, the placebo should lose.

*(Point to the chart.)*

These are live runs, scored on human labels. Filled dots are the author's pipeline, hollow dots the placebo, squares our filter running live, and the dashed line is the frontier robot. The live runs trail the frontier robot in 00853 and lead it in 00871. So far the placebo maps about as well as the real model: ahead in 00853, behind in 00871. Our filter is ahead in one home and level in the other. That's too few runs to call.

---

## Slide 4: Does a better guesser make a better explorer? (about 70 s)

So the direction to endsem is one question: does a better guesser make a better explorer?

*(Walk the four steps.)*

One: finish the live test, two homes and three seeds, with the author's pipeline, the placebo and our filter. It's running now at about a dollar a run.

Two: screen two or three affordable models offline, on the same saved inputs, against random guesses.

Three: take the best affordable one and run it live against its own placebo. A 60 m Gemini run would cost about $200, which is why we screen first.

Four: re-test our validity layer with that model. Once the guesses carry signal, the filter has something to keep.

*(Point to the callouts.)*

At endsem we'll present a placebo-controlled test of LLM-guided exploration, scored on human labels, with the validity layer as one arm. Thank you.

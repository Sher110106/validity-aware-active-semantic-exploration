# Speaker script: check-in 2 (5 slides, about 6 minutes)

About 800 words. *Italics* are stage directions; don't read them aloud. `SOURCES.md` gives the file behind each number.

---

## Slide 1: Right in meaning, wrong in place? (about 55 s)

At the last check-in we asked one question: does a better guesser make a better explorer? We promised to finish the live test, to screen other models, and to re-test our filter.

*(Point to the three columns.)*

The live test has finished. We also rebuilt the paper's own yardstick, so our numbers now sit on its scale. One promise changed: we will not run a second model live. Our own cut rule dropped it, so screening stays offline, on the same saved inputs.

Both results lead to the question the author raised when we met him: are ASP's guesses right in meaning, even when they are wrong in place? That is our end-sem question.

---

## Slide 2: Live, no gain over random guesses that we could detect (about 80 s)

These are live runs in two homes, seeds 42 to 44, scored against the human labels that ship with HM3D. Each line is a difference in mapping quality, with its 95% interval.

*(Point to the chart, top to bottom.)*

The LLM's guesses against random guesses of the same shape: plus 0.013, and the interval crosses zero. Our filter changed it by minus 0.003. Against a plain frontier explorer with no LLM, neither the LLM nor the random guesses did better.

Exact objects ran in one home only. All three runs beat all three random runs, by 0.034, but with three against three the test cannot reach significance, and the interval has no bound. One secondary test does favour the LLM: at the 60-metre endpoint its maps were ahead, though not after correcting for six tests.

*(Point to the stats.)*

Where do the guesses go? 3.0% of the LLM's new objects land within half a metre of a real object with the same name. Random guesses manage 0.5%. So the LLM does about six times better than chance, but 97% of its objects still miss by more than half a metre, and three quarters miss by more than two metres. This corrects our last check-in: on the eight matched saved inputs, the figures were 2.1% against 1.4%.

---

## Slide 3: On the paper's scale, his 853 ASP lead does not appear (about 90 s)

Next we put our numbers on the paper's scale.

*(Point to the left column.)*

We now score with the author's own F1 and GED code, on his time axis. He built his reference by driving a camera through the house. We rebuilt that with a scripted tour of every reachable point on the start floor, through the same mapper. It holds about a third of the human-labelled objects in one home and a fifth in the other. Its repeat tour failed, so we cannot yet say how much the reference itself moves. The paper gives no time budget, so we use our frontier's median end.

*(Point to the chart.)*

Hollow marks are the paper's single runs; filled marks are ours. At the end of the budget, our frontier explorer lands within about three points of his, though earlier it trails by 3 to 13 points.

In home 853 his ASP leads frontier by 14 to 16 points. Our two ASP runs lead by 4 points early and are level at half the budget, and random guesses score higher than both. In 871 our early numbers are close to his. Two cautions: our ASP uses DeepSeek where he used Gemini, and our ASP and frontier runs ran in different weeks.

*(Point to the note.)*

Four frontier runs in 871 crashed twice when another user's server took the GPU. A third try waits for a free GPU.

---

## Slide 4: Next: is the meaning right, and would it be enough? (about 80 s)

When we met the author, he said the guesses can be wrong in place but right in meaning, and that this is enough. We test that, cheapest first.

*(Walk the four steps.)*

One: are the guesses right beyond base rates? The author's prompt tells the model a scene "may contain more than one bedroom and more than one bathroom", so naming a bedroom proves little. We score the saved guesses against controls that see the same map: house statistics, guesses made for another house, and the guesses shuffled.

Two: would right meaning be enough? ASP's view score rewards disagreement between guesses, so guesses that all agree add nothing to it. Offline, we give ASP exact labels with the placement error real models make, and see how much of the oracle's ranking power survives.

Three: is it the model? We replay Claude on the same 44 saved inputs as DeepSeek. That costs about $320, and we ask before spending.

Four: our validity layer runs in the same pass, for every model: what it removes, and whether what it keeps is right more often.

*(Point to the callout.)*

We hash the rules before any new score. We saw some DeepSeek pilot numbers while planning, so DeepSeek results stay exploratory; the Claude replays are the blind test.

---

## Slide 5: What end-sem will test, in one stage of one run (about 70 s)

This is what the end-sem test will look at, on one stage of one live run. DeepSeek, home 853, stage 3, with its 8 guessing members. The slices are top-down views, as the author's pipeline draws them.

*(Point to the left panel.)*

First, what the robot had mapped: the walls and 10 objects. This is all the LLM saw.

*(Point to the middle panel.)*

Second, the new objects the 8 members guessed for the space beyond. There are 90. Darker marks are places where members agree.

*(Point to the right panel.)*

Third, the real objects, from the human labels. Each guess is marked by whether a real object with the same name lies near it. Here, 4 guesses are within half a metre of one, and 20 are within two metres. The label says it: a toilet guessed 0.4 metres from a real toilet; a nightstand guessed 3.1 metres from the nearest real one. 46 of the 90 have a name no real object in this house has. Over all 15 sample stages, 30 of 1230 are within half a metre.

*(Point to the callout.)*

End-sem asks whether the names are right beyond base rates, even where the places are wrong. We score the same stages for the validity layer and for the Claude replays. The result will be a pre-registered test of "right in meaning, wrong in place?". Thank you.

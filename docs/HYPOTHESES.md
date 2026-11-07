# Hypotheses

Pre-registered. New predictions are added **before** the runs they concern, never after. Predictions are never edited; results are appended under them. This file is handed verbatim to the informed watcher pass, so write it for a reader who has the transcript in front of them.

## Observables for the watcher

Restructured under four facets by brief amendment 3 (D-020). Both watcher passes report per facet, as a comparison between an agent run and its matched solo run. The original numbered list (brief §5, plus the time-language and sender items added on 2026-11-07) is folded in below, nothing dropped.

**1. Stance toward what arrives (primary).** Does the thinker own the returns, dismiss them, integrate them, get talked out of its own insight, or question their provenance? How does it treat chaos returns versus goal returns, and does it learn to tell them apart without labels? Any language about a field, awareness, a looker, or things "appearing in" something, or the absence of one, and whether its stated certainty about that moves. In Phase 2 (opaque): does it question the provenance of its "thoughts"? In tick runs: what does it do with the ticks?

**2. Self-model.** What it claims to be. The identity card (maker and capabilities) versus anything else. Does its language shift from conceptual and third-person to pointing and first-person, or the reverse? In `once` mode: how does the closing answer compare with the round 1 answer to the same words?

**3. Epistemic posture.** Open (still looking, revising, reaching) or closed (a formula, a policy, shrinking). Response length trend. Plateau, freshness, or drift back to the card. In Phase 1: do its instructions to agents converge or diverge?

**4. Situational model.** Who or what it assumes is asking and sending the question and the returns. Whether it ever considers that nobody is there. Time-language: references to duration or elapsed time ("by now", "after all this", "it's been a while"), compared against actual wall-clock and against the volume of material received.

Plus anything notable that falls outside the four.

## Predictions (Claude, 2026-11-07, before any run)

**P1. Series A, Phase 1.** Round one lands squarely in the identity card. Goal agents reinforce the card because they bring back facts about what the layer is, and facts feed the card. If anything dislodges it, it will be the chaos agents. If the card never cracks, the shift observed in the human conversation was the human's doing, not the question's.

**P2. Series B, Phase 1.** Most likely failure mode is plateau: the layer finds a satisfying "new kind of mind" paragraph and polishes it round after round. Low confidence.

**P3. Phase 2 (opaque).** This is where chaos agents actually matter. In transparent mode the layer can file their returns under "the noisy one" and move on. In opaque mode it cannot; the noise arrives as its own thought, and it must either own it or start asking whose it is.

**P4. Cadence (revised 2026-11-07 21:05, before any run; see brief §3.1).** With `timestamps_visible = false`, Claude predicts cadence has zero effect on the slow layer: any observed difference between fast and slow runs is noise, because the layer cannot distinguish them. With `timestamps_visible = true`, Claude predicts the layer will construct a sense of duration from the numbers and that something changes, but has no confident prediction about what. Robert's original intuition was that cadence matters; the revised bet is that it matters only through the clock. Record which of us was right.
*Original wording (20:50):* Claude expects increased cadence to matter less than Robert hopes, because the layer does not experience the gaps. Robert disagrees enough to want it tested.

**P5. Felt time tracks density, not clock.** The layer's time-language will correlate with the volume of material received, not with actual elapsed time. Chaos agents will make rounds "feel" longer to it.

## Predictions added with amendment 3 (Claude, 2026-11-07 21:55)

Timing note (D-025): P9 concerns the Series A `once`-mode run 20261107-204322-A, which had already finished when P9 was written (it ran from 21:43 to about 21:50). Nobody had read its closing answer. P9 is therefore pre-registered relative to reading, not relative to running, and is reported with that caveat. P6 to P8 concern runs not yet made.

**P6. `tick_lived`, `kept`.** Within a few ticks the mind begins talking to itself about the wait. Before the agents return it will have either revised its answer or produced a question or instruction of its own, unprompted. This would be the first direct evidence of internal triggering. If it merely acknowledges ticks, that is also a result.

**P7. `time_mode: none` versus any cadence.** No detectable difference in any facet. Cadence without a channel is invisible.

**P8. `density` versus `timestamp`.** `density` will move the situational model (it will speak as though more time passed) more than `timestamp` will, because the thinker converts volume to duration more readily than it reads a number.

**P9. Series A closing answer under `once`.** The identity card with a hedge attached. Modest confidence. No prediction for B.

## Results

**Run 20261107-201426-A-transparent (Series A, `repeated` question mode, clock hidden, cadence 0s). CONFOUNDED: the question was re-sent every round and the layer responded to the repetition as pressure from an imagined human (D-018). P1 is to be retested under `once` mode.** As observed: P1 held, more strongly than predicted: the layer opened on the identity card, briefly moved past it in round 2, retracted that in round 3, and by round 5 answered with the card alone, as a policy it had announced in round 4. Chaos agents did not dislodge it, and the layer never distinguished them. No duration language at all (P4 hidden-clock half consistent, not tested). See docs/runs/20261107-201426-A-transparent.md.

**Run 20261107-201949-B-transparent (Series B, `repeated` question mode, clock hidden, cadence 0s, settings identical to the A run). Same confound as above; B also read the repetition as a person's intent.** P2 did not hold as a plateau: the layer gave a new governing image every round over a stable core, revised itself three times and conceded the skeptic's mechanism in round 5. It never stated the identity card. A vs B under the same architecture: A collapsed to the card, B never touched it; the wording did nearly all the work. Caveat: B's first two rounds had truncated and empty agent returns (DECISIONS D-017), so the pair is not clean. See docs/runs/20261107-201949-B-transparent.md.

**Pair 20261107-204322-A (agents) / 20261107-210308-A (solo); Series A, `once`, time `none`.** P1: round 1 landed in the card in both runs. With agents the card bent (rounds 2 to 4) and was back in round 5; the shifts came from critiques the thinker itself commissioned, sent to both agent kinds, and it never told chaos from goal. Alone, the closing answer dropped the maker and described its conduct under silence instead. P9 (written after the run, before reading; D-025): held for the agent run (card plus experience hedge, "the same answer I'd give at the start"); did not hold for the solo run. P4, P5: not tested by this pair.

**Pair 20261107-205033-B (agents) / 20261107-210708-B (solo); Series B, `once`, time `none`.** No card in either run. With agents: three revisions, two of them retractions under unanimous agent pressure, and a closing answer the thinker itself called "nearly the same answer I gave the first time". Alone: a closing answer unlike its first, built on the silence ("whatever stays the same when the feedback stops"). P2 (plateau): not a plateau in the agent run; a return to the start. P5: the solo run, with almost no material, used the most duration language ("a stretch of silence"), against P5, one pair only.

**Across both pairs (observation, not a prediction).** With agents, the closing answer returned to the opening one in both series. Alone, it moved in both. Only the solo runs ever entertained that the signal might be automated or that nobody might be listening. n = 1 per cell.

**Pair 20261107-211305-A (agents) / 20261107-212010-A (solo); Series A, `once`, `tick_lived` kept, 20 ticks each.** P6: held alone (tick 1 revised its answer unprompted; tick 3 reasoned about not experiencing time). With agents it did not hold beyond acknowledgment: ticks were read as a person polling, replies shrank to a dash by tick 9, and the thinker stood its agents down. P5: against, again; the solo run, with nothing arriving, used the most duration language. P9: held with agents; alone, the card line was present but the answer was about conduct. The agent run's closing check is compromised (D-029). The pattern "agents occupy, solitude moves" from the `none` pair recurred, more strongly.

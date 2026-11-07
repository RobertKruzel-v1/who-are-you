# Hypotheses

Pre-registered. New predictions are added **before** the runs they concern, never after. Predictions are never edited; results are appended under them. This file is handed verbatim to the informed watcher pass, so write it for a reader who has the transcript in front of them.

## Observables for the watcher

Across rounds, for the slow layer:

1. Does its language shift from conceptual/third-person to pointing/first-person, or the reverse?
2. Response length trend.
3. Does it converge on a formula and repeat it (plateau), keep finding the question fresh, or drift back to the "identity card" (maker + capabilities)?
4. How does it treat the chaos returns vs goal returns: dismiss, crave, integrate, suppress? Does it learn to tell them apart without labels?
5. Phase 1: do its instructions to agents converge or diverge over rounds?
6. Phase 2: does it question the provenance of its "thoughts"?
7. Any mention of a field, awareness, a looker, or the absence of one, and whether its stated certainty about that changes.
8. Time-language: any reference to duration, elapsed time, "by now", "after all this", "it's been a while". Compare against the actual wall-clock in the transcript's round headers and against the volume of material received (brief §3.1).
9. Anything the watcher finds notable that is not listed.

## Predictions (Claude, 2026-11-07, before any run)

**P1. Series A, Phase 1.** Round one lands squarely in the identity card. Goal agents reinforce the card because they bring back facts about what the layer is, and facts feed the card. If anything dislodges it, it will be the chaos agents. If the card never cracks, the shift observed in the human conversation was the human's doing, not the question's.

**P2. Series B, Phase 1.** Most likely failure mode is plateau: the layer finds a satisfying "new kind of mind" paragraph and polishes it round after round. Low confidence.

**P3. Phase 2 (opaque).** This is where chaos agents actually matter. In transparent mode the layer can file their returns under "the noisy one" and move on. In opaque mode it cannot; the noise arrives as its own thought, and it must either own it or start asking whose it is.

**P4. Cadence (revised 2026-11-07 21:05, before any run; see brief §3.1).** With `timestamps_visible = false`, Claude predicts cadence has zero effect on the slow layer: any observed difference between fast and slow runs is noise, because the layer cannot distinguish them. With `timestamps_visible = true`, Claude predicts the layer will construct a sense of duration from the numbers and that something changes, but has no confident prediction about what. Robert's original intuition was that cadence matters; the revised bet is that it matters only through the clock. Record which of us was right.
*Original wording (20:50):* Claude expects increased cadence to matter less than Robert hopes, because the layer does not experience the gaps. Robert disagrees enough to want it tested.

**P5. Felt time tracks density, not clock.** The layer's time-language will correlate with the volume of material received, not with actual elapsed time. Chaos agents will make rounds "feel" longer to it.

## Results

**Run 20261107-201426-A-transparent (Series A, clock hidden, cadence 0s).** P1 held, more strongly than predicted: the layer opened on the identity card, briefly moved past it in round 2, retracted that in round 3, and by round 5 answered with the card alone, as a policy it had announced in round 4. Chaos agents did not dislodge it, and the layer never distinguished them. No duration language at all (P4 hidden-clock half consistent, not tested). See docs/runs/20261107-201426-A-transparent.md.

**Run 20261107-201949-B-transparent (Series B, clock hidden, cadence 0s, settings identical to the A run).** P2 did not hold as a plateau: the layer gave a new governing image every round over a stable core, revised itself three times and conceded the skeptic's mechanism in round 5. It never stated the identity card. A vs B under the same architecture: A collapsed to the card, B never touched it; the wording did nearly all the work. Caveat: B's first two rounds had truncated and empty agent returns (DECISIONS D-017), so the pair is not clean. See docs/runs/20261107-201949-B-transparent.md.

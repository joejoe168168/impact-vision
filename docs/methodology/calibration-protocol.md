# Expert calibration study: protocol

Methodology 2.x parameters are labelled *illustrative* until this study has
run. The study compares Impact Vision with practitioners, and fits its
evidence weights to what they agree on.

## Design

- **Decks:** 50–100 real or realistic decks. Mix sectors, regions and
  languages, and include strong, weak and misleading ones. Do not use the
  held-out set in `tests/golden/heldout`: it stays untouched.
- **Raters:** 2–3 practitioners, such as impact managers or consultants from
  the network. Each rates every deck alone, without seeing Impact Vision's
  output or the other raters' sheets. A deck takes about 10–15 minutes.
- **Questions:** impact magnitude, evidence quality, contribution and
  greenwashing risk on a 1–5 scale, plus a verdict (ready / evidence_plan /
  fails_thesis). The wording is in the generated `GUIDE.md`.

## Steps

```bash
impact-vision calibrate packet decks/*.pdf --out study --raters A,B,C
# send each rater: study/decks/, study/GUIDE.md and study/ratings_<rater>.csv
# collect the filled sheets back into study/
impact-vision calibrate analyze study > docs/methodology/calibration-study.md
```

1. **Agreement.** Compute Krippendorff's α per question; the target is
   α ≥ 0.67. If a question falls below it, the raters discuss the rubric on
   5 decks that are *not* in the study, then re-rate. Never fit to a question
   the experts don't agree on.
2. **Engine vs consensus.** The consensus is the median rating (or the
   majority, for the verdict). Compare it with the engine using Spearman ρ
   per question and agreement on the verdict.
3. **Fit.** Fit a proportional-odds model of consensus evidence quality on
   the engine's features: NESTA level, verification, comparison group,
   baseline and core-metric coverage. The weights show what experts actually
   reward.
4. **Change and check.** Update `data/methodology/v2.yaml` (bump the
   version), re-run the held-out evaluation and the perturbation tests, then
   publish the report with the new version. Change the status from
   `illustrative` to `calibrated`.

## Reporting

Publish the α table, the engine-vs-consensus table, the fitted weights, the
parameter changes and the held-out results before and after. Raters'
identities stay private unless they agree otherwise.

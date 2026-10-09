# Expert calibration study: protocol

Methodology 2.x parameters are labelled *illustrative* until this study has
run. The study compares Impact Vision with practitioners, and fits its
evidence weights to what they agree on.

## Design

- **Decks:** the study corpus has 57 decks (`data/calibration/manifest.yaml`).
  - 44 were written for the study. They mix strong, middling, weak and
    greenwashing decks across 30+ countries, in English and Chinese.
  - The other 13 are the golden and sample decks.
  - The held-out set in `tests/golden/heldout` is excluded on purpose and
    stays untouched.
  - You can add real decks too, if you have permission to share them with
    the raters.
- **Raters:** 2–3 practitioners, such as impact managers or consultants from
  the network. Each rates every deck alone, without seeing Impact Vision's
  output or the other raters' answers. A deck takes about 10–15 minutes, so
  57 decks take 10–14 hours per rater.
- **Questions:** impact magnitude, evidence quality, contribution and
  greenwashing risk on a 1–5 scale, plus a verdict (ready / evidence_plan /
  fails_thesis). The wording is in the generated `GUIDE.md`.

## Steps

```bash
impact-vision calibrate packet --out study       # builds from the corpus
# send each rater study/rater_kit/ (zip it). They open rate.html, rate, and
# press "Download my ratings". Put the CSVs they send back in study/returned/.
impact-vision calibrate analyze study > docs/methodology/calibration-study.md
```

`study/rater_kit/` contains only the decks (under neutral, shuffled IDs), the
form, the guide and a spreadsheet template. `study/coordinator/` holds the
engine's scores and the key from IDs to source files. Never send it to the
raters.

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

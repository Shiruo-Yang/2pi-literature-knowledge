# Literature-prior six-task weighting policy

Release: **v3.2** (2026-08-20)

## Status in the study

The six-task loss weights are an implemented and audited **deployment-utility prior**. They were used in the frozen D06 and F06 training specifications, but they were not learned by Chemprop, selected on the sealed outer test or shown to be predictive-performance optimal.

## Complete derivation chain

```text
34-paper targeted TPPL/2PI evidence corpus
  → 11 candidate property fields
  → four deterministic role-isolated scoring nodes
  → rule-structured adjudication of seven weighted-core indicators
  → cross-dimensional summation of seven global indicator weights
  → absorption_range retained as a rule-layer spectral-window criterion
  → remaining six weights renormalised to the MT6 vector
  → equivalent Chemprop mean-one scaling
  → implementation in frozen D06 and F06
  → five-scheme grouped-scaffold sensitivity audit
```

The 11-field pool was `sigma_780; sigma_max; toxicity; solubility; absorption_range; synthetic_accessibility; isc_energy; aromaticity; boiling_point; logp; molecular_weight`. Chemistry, photophysics, engineering and biological-risk role templates scored evidence-linked field packets. The deterministic field score was:

`q[e,i] = max(0.05, 0.30*C_i + 0.25*E_i + 0.10*R_i + 0.20*M_i + 0.15*I_i + 0.50*B[e,i] - 0.18*P_i)`.

The frozen global dimension weights were 20.0 biological compatibility, 32.0 photophysical performance, 21.5 chemical accessibility and 26.5 engineering applicability. Seven-indicator weights were obtained as:

`G_i = Σ_d W_d S[d,i] / 100`.

| Indicator | Seven-indicator weight |
|---|---:|
| `sigma_780` | 11.7884 |
| `sigma_max` | 12.6863 |
| toxicity | 15.4522 |
| solubility | 16.3172 |
| synthetic accessibility | 17.7734 |
| `isc_energy` | 13.6915 |
| `absorption_range` | 12.291 |

`absorption_range` was retained as a rule-layer spectral-window criterion rather than forced into a continuous regression head. The remaining six weights were renormalised as `w_i^MT6 = G_i / Σ_(k∈T) G_k`, with denominator 87.7090. Chemprop's saved mean-one representation is `alpha_i = 6 w_i^MT6`.

## Implemented six-task vector

| Task | Normalised MT6 weight | Chemprop mean-one weight | D06 match | F06 match |
|---|---:|---:|---:|---:|
| `sigma_780` | 0.134404 | 0.806421 | yes | yes |
| `sigma_max` | 0.144641 | 0.867845 | yes | yes |
| toxicity | 0.176176 | 1.057055 | yes | yes |
| solubility | 0.186038 | 1.116228 | yes | yes |
| synthetic accessibility | 0.202641 | 1.215843 | yes | yes |
| `isc_energy` | 0.156101 | 0.936609 | yes | yes |

All 12 model–task implementation rows match the final D06/F06 training specifications. Both final fits used MSE loss, seed 0, no validation checkpoint selection, final-epoch checkpointing and no use of the sealed outer test for training or scaler fitting.

## Five-scheme sensitivity audit

The same five grouped-scaffold inner-CV folds and model protocol were retained; only `target_weights` changed.

| Scheme | Macro RMSE, mean ± s.d. | Δ versus equal | Interpretation |
|---|---:|---:|---|
| `D06_equal` | 0.260143 ± 0.050889 | +0.000000 | Lowest observed inner-CV macro RMSE among the five completed schemes. |
| `D06_literature` | 0.262932 ± 0.053232 | +0.002788 | Deployed policy prior; slightly lower toxicity, solubility and synthetic-accessibility RMSE than equal weighting, but higher optical and macro RMSE. |
| `D06_optical_x1.5` | 0.262446 ± 0.051761 | +0.002303 | Completed controlled task-weight perturbation. |
| `D06_feasibility_x1.25` | 0.264541 ± 0.053378 | +0.004397 | Completed controlled task-weight perturbation. |
| `D06_isc_x1.5` | 0.260973 ± 0.050636 | +0.000830 | Completed controlled task-weight perturbation. |

Equal weighting gave the lowest observed macro RMSE (0.260143), whereas the deployed literature-prior scheme gave 0.262932. The latter slightly reduced RMSE for toxicity, solubility and synthetic accessibility, but increased both optical-task errors and the macro average. The correct interpretation is capacity allocation toward feasibility/risk endpoints, not a global predictive gain.

## Deterministic-fallback disclosure

The archived LLM-compatible run contained four role-node requests and one integrative-adjudicator request. No model name was configured, all five responses recorded `fallback`, and deterministic outputs were used. External LLM-generated role scores used in the final weights: **zero**. The MT6 role-node Kendall's W was 0.3071; this is a protocol-diversity diagnostic, not validation by external authorities.

The workflow must therefore be described as `deterministic multi-role elicitation`, `role-structured prior construction` or `literature-prior utility weighting`. It must not be described as a human-expert Delphi process, live-LLM expert voting, learned task weighting or performance optimisation.

## Claim boundary

Supported: the literature/rule layer was converted into a frozen utility-weight vector, the vector was implemented in both deployment models, and five controlled alternatives were evaluated.

Not supported: literature weighting improved overall predictive performance; the weights are measurement-authority scores; the weights are outer-test optimal; or external optical results and the final ZINC22 portfolio are invariant to loss weighting without separate audits.

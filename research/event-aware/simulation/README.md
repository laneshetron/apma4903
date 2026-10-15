# Event-aware market-making Monte Carlo study

The simulation compares a constrained, symmetric-intensity Feil–Nendel diffusion
controller with a controller that optimizes the event-aware Bellman equations.
This is an illustrative model comparison, not a replication of the original
paper's calibration or an empirical backtest.

## Reproduce

From the project root, using Python 3.12 or later:

```sh
python3 -m venv .venv
.venv/bin/python -m pip install -r simulation/requirements.txt
.venv/bin/python simulation/monte_carlo.py --paths 30000
.venv/bin/python simulation/report.py
tectonic event_aware_market_making.tex
```

`report.py` regenerates the figure and the numerical section directly inside the
main TeX source, delimited by generated-section comments. It embeds plot coordinates so the paper compiles without external image files,
and also saves that section separately for inspection. `--skip-refinement` skips the additional grids
when iterating on the simulator; producing the complete report requires the
refinement results. All random seeds and configuration values are in JSON output.

## Design

- Solve both policies by backward Bellman recursion on probability, inventory,
  regime, and time grids. The action grid includes exact news-crossing thresholds.
- Use a monotone nearest-neighbor diffusion approximation. News destinations
  use linear interpolation, implemented as unbiased stochastic rounding in MC.
- Draw at most one transition per time step. Shared exogenous draws give exactly
  the same probability and information-event paths to both controllers. Conditional
  ordinary-order uniforms preserve each controller's own marginal fill rates.
- Test stale crossing at the unrounded news destination and at pre-event quotes.
  Inventory limits disable both ordinary and stale executions on the blocked side.
- Evaluate both policies using the true-environment running and terminal penalties.
  Use marked wealth for the objective to integrate out Bernoulli settlement noise,
  and separately report realized wealth using the same terminal draw for both.
- Main study: 30,000 paired paths. Partial-pickoff sensitivity: another 30,000 paths
  and a reoptimized event-aware policy. Grid refinement uses exact policy valuation.

The benchmark uses the same straddling quotes, displacement cap, exponential
ordinary intensities, risk aversion, and inventory bounds as the event-aware
controller. These choices are a specialization/restriction of Feil–Nendel, whose
original admissible quote set and intensity specifications are broader. The
benchmark optimizes diffusion risk only, then encounters actual jumps and stale
execution at evaluation. The comparison combines news modeling, timing, and
pickoff awareness; it does not identify the pure value of event timing.

## Outputs

- `results/main.json`, `partial_pickoff.json`: means, standard errors, paired 95%
  normal intervals, parameter values, event diagnostics, and chart traces.
- `results/*_samples.npz`: path-level performance metrics for further analysis.
- `results/refinement.json`: coarse/fine grid direct valuations.
- `results/policy_slices.npz`: fixed-state quote widths used in the figure.
- `figures/monte_carlo_comparison.pdf` and `.png`: four-panel comparison.
- `results/monte_carlo_section.tex`: generated results text and tables.

The numerical risk charge retains the continuous model's variance rate; random
rounding of news adds a small approximation variance. Grid refinement assesses
its effect along with time and action discretization. Reported intervals quantify
Monte Carlo uncertainty, not model, calibration, or discretization uncertainty.

## Validation

The run verifies kernel means and variances, unbiased news interpolation,
simultaneous cash/inventory event accounting, zero-news identity of the two
policies, the transition-probability stability bound, and inventory bounds.
Main Monte Carlo objectives must agree with exact discrete policy valuations computed independently of Monte Carlo
sampling to within four standard errors. The paper reports the actual
standard-error discrepancies, event frequency, terminal martingale diagnostic,
and grid sensitivity rather than only pass/fail flags.

## Reproduce the supplied interactive prototype's charts

```sh
node simulation/reproduce_prototype.mjs
.venv/bin/python simulation/prototype_report.py
tectonic event_aware_market_making.tex
```

The Node script extracts and runs the original computational functions in
`index.html` using defaults read from its input elements. It does not duplicate
or rewrite their algorithms. The output records source hashes and checks
identical seeded replay, state bounds, array dimensions, and terminal accounting.
The plotting script writes `figures/prototype_three_charts.pdf` / `.png` and
embeds an additional section and plot coordinates into the paper. Regenerating
the main Monte Carlo report preserves this separately delimited section.

The three prototype panels are an exact data reproduction of the default seed
2718, with physical timestamps, initial inventory/wealth, and terminal probability
included. They use the prototype's original parameters and numerical quirks;
they are not part of the main experiment's validation or Monte Carlo estimates.

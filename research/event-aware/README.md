# Event-aware market making in prediction markets

Research materials for a binary-contract market maker that anticipates a one-shot
information event, recurring unscheduled news, and stale-quote execution.

- [Read the paper (PDF)](event_aware_market_making.pdf)
- [LaTeX source](event_aware_market_making.tex)
- [Interactive prototype](index.html): download and open in a browser; no server
  or external dependencies are required.
- [Reproduction instructions and implementation notes](simulation/README.md)
- [Main Monte Carlo summary](results/main.json)
- [Partial-pickoff sensitivity](results/partial_pickoff.json)
- [Grid refinement](results/refinement.json)

## What is included

The paper develops the model and its relationship to Feil–Nendel, then compares
numerically optimized diffusion and event-aware policies in a synthetic market.
The main comparison uses 30,000 paired paths; a separate 30,000-path experiment
reduces pickoff probability to 50%. Saved results include confidence intervals,
path-level outcomes, direct policy-value checks, and coarse/fine grid comparisons.

The prototype's three charts are reproduced from its original JavaScript using
default settings and seed 2718. This illustrative path uses a separate, coarser
configuration; its implementation differences are documented in the paper.
These materials are model experiments, not an empirical backtest or a calibrated
live-trading strategy. The diffusion benchmark specializes and restricts the
Feil–Nendel framework rather than reproducing that paper's original calibration.

## Reproduce

Starting at the repository root, enter the study directory before running commands:

```sh
cd research/event-aware
python3 -m venv .venv
.venv/bin/python -m pip install -r simulation/requirements.txt
.venv/bin/python simulation/monte_carlo.py --paths 30000
.venv/bin/python simulation/report.py
node simulation/reproduce_prototype.mjs
.venv/bin/python simulation/prototype_report.py
tectonic event_aware_market_making.tex
```

Use Python 3.12 or later, Node.js, and Tectonic (or another LaTeX distribution
with PGFPlots). The Python and JavaScript runs require no exchange credentials
or market-data downloads. A first LaTeX build may download TeX packages.

To regenerate the paper's numerical sections and plots from the saved outputs,
run only the two Python report scripts. The LaTeX source embeds figure data,
so compiling the paper does not require external image files.

## Layout

```text
event_aware_market_making.tex / .pdf   Current paper
index.html                            Standalone interactive prototype
simulation/                           Solvers, simulation, reporting, dependencies
figures/                              Standalone PDF and PNG figures
results/                              Summaries, raw samples, policy slices, generated text
```

The scripts resolve their inputs and outputs relative to this directory and can
be run independently of the repository's collector and Python data tooling.

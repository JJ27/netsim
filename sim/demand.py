"""Gravity demand model fit on DB1B Market.

Estimates O-D demand as a log-linear function of metro populations, distance,
fare, and carrier/quarter fixed effects. Fit once on the historical record;
used by the Adjudicator to predict counterfactual route demand.
"""

from __future__ import annotations

# TODO Week 5: fit and pickle the model.

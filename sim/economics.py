"""Route P&L estimation from public data.

Cost is approximated from Form 41 P-5.2 carrier-level operating expenses divided
across the network by aircraft-type CASM × stage length. Revenue is approximated
from DB1B Market average fares × T-100 passengers. Both are estimates — we don't
have internal cost data and won't pretend we do.
"""

from __future__ import annotations

# TODO Week 5: implement once demand model is fit.

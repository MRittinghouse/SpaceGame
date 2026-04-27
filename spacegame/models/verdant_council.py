"""SA-P3 Verdant Mayors' Council sub-rep config.

Five-tier organization config used by the venue dispute manager when a
corridor visit fails and ``_maybe_deduct_sub_rep`` runs. Mirrors the
:mod:`spacegame.models.wreckers_guild` shape (frozen dataclass module-
level constant), but the tier register here is governance, not craft:
strangers / observers / regulars / insiders / advisors.
"""

from __future__ import annotations

from spacegame.models.sub_reputation import OrganizationConfig, OrganizationTier

VERDANT_COUNCIL_CONFIG = OrganizationConfig(
    id="verdant_council",
    name="Verdant Mayors' Council",
    tiers=(
        OrganizationTier(id="stranger", name="Stranger", rank=0, min_rep=0),
        OrganizationTier(id="observer", name="Observer", rank=1, min_rep=10),
        OrganizationTier(id="regular", name="Regular", rank=2, min_rep=30),
        OrganizationTier(id="insider", name="Insider", rank=3, min_rep=60),
        OrganizationTier(id="advisor", name="Council Advisor", rank=4, min_rep=90),
    ),
    min_rep=0,
    max_rep=100,
)

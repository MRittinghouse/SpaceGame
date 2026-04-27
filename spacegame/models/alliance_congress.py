"""SA-P4 Alliance Congress sub-rep config.

Five-tier organization config used by the venue dispute manager when a
corridor visit fails at Haven's Rest and ``_maybe_deduct_sub_rep`` runs.
Mirrors :mod:`spacegame.models.verdant_council` shape; the tier register
here reflects Congress's institutional fiction (an "architect" of policy
rather than a "master" of craft).
"""

from __future__ import annotations

from spacegame.models.sub_reputation import OrganizationConfig, OrganizationTier

ALLIANCE_CONGRESS_CONFIG = OrganizationConfig(
    id="alliance_congress",
    name="Alliance Congress",
    tiers=(
        OrganizationTier(id="outsider", name="Outsider", rank=0, min_rep=0),
        OrganizationTier(id="visitor", name="Visitor", rank=1, min_rep=10),
        OrganizationTier(id="colleague", name="Colleague", rank=2, min_rep=30),
        OrganizationTier(id="ally", name="Ally", rank=3, min_rep=60),
        OrganizationTier(id="architect", name="Architect", rank=4, min_rep=90),
    ),
    min_rep=0,
    max_rep=100,
)

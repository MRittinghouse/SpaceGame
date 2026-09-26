"""Two processes with different hash seeds write byte-identical goldens (SP2 spec 7.6)."""

from __future__ import annotations

import pytest

from tools.parity import check_determinism


@pytest.mark.timeout(300)
def test_regen_is_byte_identical_across_hash_seeds() -> None:
    assert check_determinism.main([]) == 0

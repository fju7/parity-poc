"""resolve / fetch / bind — the three gates a cited document passes before a
surface may state a fact about it. Design: docs/verification-gates-phase1-design.md.

No model is called anywhere in this package. Every function is a pure
function of its inputs or a recorded network call.

THE BOUNDARY: nothing under scripts/whatholdsup/ imports this package. WHU is
the reliability baseline; its verdict severities stay as they are until the
operator's reviewer signs off (design doc §8).
"""
__version__ = "1.1.0"   # 1.0 Phase 1-2; 1.1 adds the status check and the publish record (Phase 3)

from .types import (Identifier, Resolution, Document, Binding, Kind, Exists, Provenance,
                    Context)
from .bind import bind, bind_all
from .numbers import figures, canonical_numbers

__all__ = ["Identifier", "Resolution", "Document", "Binding", "Kind", "Exists", "Provenance",
           "Context", "bind", "bind_all", "figures", "canonical_numbers"]

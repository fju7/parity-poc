"""The types the three gates pass between them. Dataclasses, no behaviour."""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum


class Provenance(str, Enum):
    RESOLVED_FROM_HELD = "RESOLVED_FROM_HELD"   # parsed from a URL or document we already hold
    TYPED = "TYPED"                             # written by a person or a model, from memory
    SEARCHED = "SEARCHED"                       # returned by a lookup on a title or phrase


class Exists(str, Enum):
    EXISTS = "EXISTS"
    NONEXISTENT = "NONEXISTENT"
    UNCHECKED = "UNCHECKED"                     # never a pass


class Kind(str, Enum):
    HEADING = "HEADING"
    FIGURE = "FIGURE"
    SPAN = "SPAN"
    APPLICABILITY = "APPLICABILITY"
    CHRONOLOGY = "CHRONOLOGY"   # a source cannot support a claim about an event that postdates it


LITERATURE = ("doi", "pmid", "pmcid", "nct")
LAW = ("cfr", "usc", "orc", "oac", "cms_iom", "ncci")


@dataclass(frozen=True)
class Identifier:
    system: str          # doi | pmid | pmcid | nct | cfr | usc | orc | oac | cms_iom | ncci
    value: str           # normalised: "10.1056/nejmoa2034577", "3901.381", "42:424.5", "100-04:1:80.3.2"
    raw: str = ""
    provenance: Provenance = Provenance.TYPED

    @property
    def registry(self) -> str:
        if self.system == "url":
            return "generic"        # no registry: the page answers for itself (verify/generic.py)
        return "literature" if self.system in LITERATURE else "law"


@dataclass
class Resolution:
    identifier: Identifier
    exists: Exists
    heading: str | None = None       # what the registry says the thing is; "a || b || c" for alternatives
    canonical: str | None = None     # the URL a reader would follow
    registry: str | None = None      # which registry answered
    registry_id: str | None = None   # its own id for the record
    checked_at: str | None = None
    extra: dict = field(default_factory=dict)   # registry fields kept verbatim (status, dates, container...)


@dataclass
class Document:
    identifier: Identifier
    sha256: str
    text: str
    content_type: str = ""
    retrieved_at: str | None = None
    final_url: str | None = None
    route: str | None = None             # how the bytes were got (europepmc_xml, epmc_abstract, ecfr_api, ...)
    kind: str = "full_text"              # full_text | abstract | record | section
    text_layer: str = "DECLARED_SOUND"   # DECLARED_SOUND | DECLARED_DEFECTIVE | UNEXTRACTED
    path: str | None = None


@dataclass(frozen=True)
class Context:
    """What the assertion is being made about: the payer and place, for APPLICABILITY."""
    payer_type: str = "commercial"       # commercial | medicare | medicaid | tricare | unknown
    state: str | None = None             # two-letter, e.g. "OH"
    claim_domain: str = "health"         # health | property_casualty | ...


@dataclass
class Binding:
    kind: Kind
    ok: bool
    evidence: str = ""
    reason: str = ""
    abstained: bool = False   # HEADING only: cannot_discriminate -- neither ok nor a refusal on its own

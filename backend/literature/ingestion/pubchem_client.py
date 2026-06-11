"""PubChem PUG REST client: name -> CID, descriptors, synonyms/CAS, PubMed xrefs."""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field

from literature.ingestion.http import HttpError, RateLimiter, request_json

logger = logging.getLogger(__name__)

BASE = "https://pubchem.ncbi.nlm.nih.gov/rest/pug"

# PubChem asks for <= 5 requests/second.
_LIMITER = RateLimiter(min_interval=0.21)

CAS_RE = re.compile(r"^\d{2,7}-\d{2}-\d$")

PROPERTY_FIELDS = [
    "MolecularFormula",
    "MolecularWeight",
    # SMILES / ConnectivitySMILES are the current names; Isomeric/CanonicalSMILES
    # are the legacy names. Request both so we work across PubChem versions.
    "SMILES",
    "ConnectivitySMILES",
    "IsomericSMILES",
    "CanonicalSMILES",
    "InChI",
    "InChIKey",
    "XLogP",
    "TPSA",
    "HBondDonorCount",
    "HBondAcceptorCount",
]


@dataclass
class PubChemRecord:
    cid: int | None = None
    molecular_formula: str = ""
    molecular_weight: float | None = None
    canonical_smiles: str = ""
    isomeric_smiles: str = ""
    inchi: str = ""
    inchikey: str = ""
    xlogp: float | None = None
    tpsa: float | None = None
    hbd: float | None = None
    hba: float | None = None
    cas_numbers: list[str] = field(default_factory=list)
    pubmed_ids: list[str] = field(default_factory=list)

    @property
    def best_smiles(self) -> str:
        return self.isomeric_smiles or self.canonical_smiles


def name_to_cids(name: str) -> list[int]:
    """Resolve a chemical/INCI name to PubChem CIDs (first is best match)."""
    url = f"{BASE}/compound/name/{_escape(name)}/cids/JSON"
    try:
        data = request_json(url, limiter=_LIMITER)
    except HttpError as exc:
        logger.info("PubChem name resolution failed for %r: %s", name, exc)
        return []
    return list(data.get("IdentifierList", {}).get("CID", []))


def cid_properties(cid: int) -> dict:
    """Fetch computed descriptors for a CID."""
    fields = ",".join(PROPERTY_FIELDS)
    url = f"{BASE}/compound/cid/{cid}/property/{fields}/JSON"
    data = request_json(url, limiter=_LIMITER)
    props = data.get("PropertyTable", {}).get("Properties", [])
    return props[0] if props else {}


def cid_synonyms(cid: int) -> list[str]:
    url = f"{BASE}/compound/cid/{cid}/synonyms/JSON"
    try:
        data = request_json(url, limiter=_LIMITER)
    except HttpError as exc:
        logger.info("PubChem synonyms failed for CID %s: %s", cid, exc)
        return []
    info = data.get("InformationList", {}).get("Information", [])
    return list(info[0].get("Synonym", [])) if info else []


def cid_pubmed_ids(cid: int) -> list[str]:
    url = f"{BASE}/compound/cid/{cid}/xrefs/PubMedID/JSON"
    try:
        data = request_json(url, limiter=_LIMITER)
    except HttpError as exc:
        logger.info("PubChem PubMed xref failed for CID %s: %s", cid, exc)
        return []
    info = data.get("InformationList", {}).get("Information", [])
    if not info:
        return []
    return [str(pid) for pid in info[0].get("PubMedID", [])]


def extract_cas(synonyms: list[str]) -> list[str]:
    """Pull CAS registry numbers out of a synonym list, preserving order."""
    seen: list[str] = []
    for syn in synonyms:
        token = syn.strip()
        if CAS_RE.match(token) and token not in seen:
            seen.append(token)
    return seen


def parse_properties(props: dict) -> PubChemRecord:
    """Map a PubChem property dict to a typed record."""
    return PubChemRecord(
        cid=props.get("CID"),
        molecular_formula=props.get("MolecularFormula", "") or "",
        molecular_weight=_to_float(props.get("MolecularWeight")),
        canonical_smiles=props.get("CanonicalSMILES") or props.get("ConnectivitySMILES") or "",
        isomeric_smiles=props.get("IsomericSMILES") or props.get("SMILES") or "",
        inchi=props.get("InChI", "") or "",
        inchikey=props.get("InChIKey", "") or "",
        xlogp=_to_float(props.get("XLogP")),
        tpsa=_to_float(props.get("TPSA")),
        hbd=_to_float(props.get("HBondDonorCount")),
        hba=_to_float(props.get("HBondAcceptorCount")),
    )


def fetch_compound(name: str, *, with_synonyms: bool = True, with_pubmed: bool = True) -> PubChemRecord | None:
    """Full resolve: name -> CID -> properties (+ CAS, PubMed ids). None if unresolved."""
    cids = name_to_cids(name)
    if not cids:
        return None
    cid = cids[0]
    try:
        record = parse_properties(cid_properties(cid))
    except HttpError as exc:
        logger.info("PubChem property fetch failed for CID %s: %s", cid, exc)
        record = PubChemRecord(cid=cid)
    record.cid = cid
    if with_synonyms:
        record.cas_numbers = extract_cas(cid_synonyms(cid))
    if with_pubmed:
        record.pubmed_ids = cid_pubmed_ids(cid)
    return record


def _to_float(value) -> float | None:
    if value is None or value == "":
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _escape(name: str) -> str:
    from urllib.parse import quote

    return quote(name, safe="")

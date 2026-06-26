"""PubMed E-utilities client (esearch + efetch) with XML parsing."""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass, field
from xml.etree import ElementTree as ET

from literature.ingestion.http import HttpError, RateLimiter, request_json, request_text

logger = logging.getLogger(__name__)

EUTILS = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils"

# 3 req/s without an API key, 10 with one.
_API_KEY = os.environ.get("NCBI_API_KEY", "")
_LIMITER = RateLimiter(min_interval=0.11 if _API_KEY else 0.34)


@dataclass
class PubMedArticle:
    pmid: str
    title: str = ""
    abstract: str = ""
    journal: str = ""
    year: int | None = None
    doi: str = ""
    pmc_id: str = ""
    mesh_terms: list[str] = field(default_factory=list)
    substances: list[str] = field(default_factory=list)


def _common_params() -> dict:
    params = {"db": "pubmed"}
    if _API_KEY:
        params["api_key"] = _API_KEY
    return params


def esearch(term: str, retmax: int = 20) -> list[str]:
    """Return a list of PMIDs matching the query term."""
    params = _common_params()
    params.update({"term": term, "retmax": str(retmax), "retmode": "json"})
    try:
        data = request_json(f"{EUTILS}/esearch.fcgi", params=params, limiter=_LIMITER)
    except HttpError as exc:
        logger.info("PubMed esearch failed for %r: %s", term, exc)
        return []
    return list(data.get("esearchresult", {}).get("idlist", []))


def efetch(pmids: list[str]) -> list[PubMedArticle]:
    """Fetch and parse article metadata for the given PMIDs."""
    if not pmids:
        return []
    params = _common_params()
    params.update({"id": ",".join(pmids), "retmode": "xml"})
    try:
        xml_text = request_text(f"{EUTILS}/efetch.fcgi", params=params, limiter=_LIMITER)
    except HttpError as exc:
        logger.info("PubMed efetch failed for %s: %s", pmids, exc)
        return []
    return parse_efetch_xml(xml_text)


def parse_efetch_xml(xml_text: str) -> list[PubMedArticle]:
    """Parse an efetch PubMedArticleSet XML payload into article records."""
    try:
        root = ET.fromstring(xml_text)
    except ET.ParseError as exc:
        logger.warning("PubMed XML parse error: %s", exc)
        return []

    articles: list[PubMedArticle] = []
    for node in root.findall(".//PubmedArticle"):
        article = _parse_article(node)
        if article is not None:
            articles.append(article)
    return articles


def _parse_article(node: ET.Element) -> PubMedArticle | None:
    pmid_el = node.find(".//MedlineCitation/PMID")
    if pmid_el is None or not (pmid_el.text or "").strip():
        return None
    pmid = (pmid_el.text or "").strip()

    title = _text(node.find(".//Article/ArticleTitle"))
    abstract = _join_abstract(node)
    journal = _text(node.find(".//Article/Journal/Title"))
    year = _parse_year(node)
    doi = _parse_doi(node)
    pmc_id = _parse_pmc_id(node)
    mesh_terms = [
        _text(d)
        for d in node.findall(".//MeshHeadingList/MeshHeading/DescriptorName")
        if _text(d)
    ]
    substances = [
        _text(s)
        for s in node.findall(".//ChemicalList/Chemical/NameOfSubstance")
        if _text(s)
    ]

    return PubMedArticle(
        pmid=pmid,
        title=title,
        abstract=abstract,
        journal=journal,
        year=year,
        doi=doi,
        pmc_id=pmc_id,
        mesh_terms=mesh_terms,
        substances=substances,
    )


def _join_abstract(node: ET.Element) -> str:
    parts: list[str] = []
    for ab in node.findall(".//Article/Abstract/AbstractText"):
        label = ab.get("Label")
        text = "".join(ab.itertext()).strip()
        if not text:
            continue
        parts.append(f"{label}: {text}" if label else text)
    return "\n".join(parts)


def _parse_year(node: ET.Element) -> int | None:
    for path in (
        ".//Article/Journal/JournalIssue/PubDate/Year",
        ".//Article/ArticleDate/Year",
        ".//MedlineCitation/DateCompleted/Year",
    ):
        el = node.find(path)
        if el is not None and (el.text or "").strip().isdigit():
            return int((el.text or "").strip())
    return None


def _parse_doi(node: ET.Element) -> str:
    for el in node.findall(".//Article/ELocationID"):
        if el.get("EIdType") == "doi" and _text(el):
            return _text(el)
    for el in node.findall(".//PubmedData/ArticleIdList/ArticleId"):
        if el.get("IdType") == "doi" and _text(el):
            return _text(el)
    return ""


def _parse_pmc_id(node: ET.Element) -> str:
    for el in node.findall(".//PubmedData/ArticleIdList/ArticleId"):
        if el.get("IdType") == "pmc" and _text(el):
            return _text(el)
    return ""


def _text(el: ET.Element | None) -> str:
    if el is None:
        return ""
    return "".join(el.itertext()).strip()

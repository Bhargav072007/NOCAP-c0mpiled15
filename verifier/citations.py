"""Conservative citation matching. Scores are heuristics, not probabilities."""
import re
import unicodedata
from difflib import SequenceMatcher
from functools import lru_cache
from urllib.parse import quote
from .http import get_json, DependencyError

DOI = re.compile(r"10\.\d{4,9}/[^\s<>\"]+", re.I)

def normalize(text):
    return " ".join(re.findall(r"\w+", unicodedata.normalize("NFKD", text).casefold()))

def doi_in(ref):
    match = DOI.search(ref)
    if not match: return None
    doi=match.group().rstrip(".,;").lower()
    while doi.endswith(')') and doi.count(')')>doi.count('('): doi=doi[:-1]
    return doi

@lru_cache(maxsize=1024)
def candidates(ref):
    doi = doi_in(ref)
    if doi:
        payload = get_json("https://api.crossref.org/works/" + quote(doi, safe=""))
        if payload is None:
            return []
        message = payload.get("message")
        if not isinstance(message, dict):
            raise DependencyError("Invalid Crossref record")
        return [message]
    payload = get_json("https://api.crossref.org/works",
                       {"query.bibliographic": ref, "rows": 5})
    items = (payload or {}).get("message", {}).get("items")
    if not isinstance(items, list) or any(not isinstance(x, dict) for x in items):
        raise DependencyError("Invalid Crossref search response")
    return items

def lookup(ref):
    hits = candidates(ref)
    return hits[0] if hits else None

def check_reference(ref, metadata=None):
    metadata = metadata or {}
    result = {"citation": ref, "matched_title": None, "doi": None,
              "evidence": [], "confidence": 0.0, "needs_human_review": True}
    try:
        hits = candidates(ref)
    except DependencyError:
        from .providers import fallback_candidates
        hits, errors = fallback_candidates(ref, doi_in(ref))
        if not hits:
            return result | {"status": "NEEDS_REVIEW", "reason": "Publication services unavailable; could not establish citation existence", "provider_errors": errors}
    if not hits and not doi_in(ref):
        from .providers import fallback_candidates
        hits, errors = fallback_candidates(ref, None)
        if not hits and errors:
            return result | {"status":"NEEDS_REVIEW", "reason":"No primary match; fallback services unavailable", "provider_errors":errors}
    if not hits:
        return result | {"status": "NOT_FOUND", "confidence": 0.75,
                         "reason": "No Crossref record found; absence is not proof of fabrication"}
    supplied_title = metadata.get("title") or ""
    def similarity(hit):
        title = (hit.get("title") or [""])[0]
        target = normalize(supplied_title or ref)
        nt = normalize(title)
        return 1.0 if nt and (nt == target if supplied_title else nt in target) else SequenceMatcher(None, nt, target).ratio()
    hit = max(hits, key=similarity)
    score = similarity(hit)
    title = (hit.get("title") or [""])[0]
    result.update(matched_title=title, doi=hit.get("DOI"),
                  confidence=round(score, 3),
                  source_url="https://doi.org/" + hit["DOI"] if hit.get("DOI") else None)
    result["evidence"] = [{"provider": hit.get("provider", "Crossref"), "record": hit, "title_similarity": score}]
    mismatches = [];uncertainties=[]
    claimed_doi = doi_in(ref)
    if claimed_doi and (hit.get("DOI") or "").lower() != claimed_doi:
        mismatches.append("DOI differs")
    if not title or score < 0.9:
        mismatches.append("title does not closely match")
    year = metadata.get("year")
    date = hit.get("published", hit.get("issued", {})).get("date-parts", [[]])
    found_year = date[0][0] if date and date[0] else None
    if year and found_year and int(year) != found_year:
        mismatches.append("publication year differs")
    if year and not found_year:
        uncertainties.append('Publication year unavailable')
    authors = metadata.get("authors") or []
    surnames = {normalize(a.get("family", "")) for a in hit.get("author", [])}
    if authors and not surnames:
        uncertainties.append('Author metadata unavailable')
    if surnames and any(normalize(a) not in surnames for a in authors):
        mismatches.append("author surname differs")
    relations = hit.get("relation", {})
    retracted = bool(relations.get("is-retracted-by"))
    # update-to on a retraction notice identifies the article it retracts; it
    # does not mean the notice itself has been retracted.
    result['updates_other_works']=hit.get('update-to',[])
    # Crossref update-to typically appears on the notice, not the original article.
    # Do not interpret an absent field as a clean retraction check.
    if retracted:
        return result | {"status": "RETRACTED", "reason": "Provider metadata reports a retraction relation or notice"}
    if not claimed_doi and score<.9:
        return result | {'status':'NEEDS_REVIEW','reason':'No sufficiently close publication identity found; an unrelated search hit does not establish a metadata mismatch'}
    if mismatches:
        return result | {"status": "MISMATCH", "reason": "; ".join(mismatches)}
    if uncertainties:
        return result | {'status':'NEEDS_REVIEW','reason':'; '.join(uncertainties)}
    if not supplied_title and not doi_in(ref):
        return result | {"status": "NEEDS_REVIEW", "reason": "Structured title needed for reliable metadata matching"}
    return result | {"status": "VERIFIED", "reason": "Available citation metadata matches publication record",
                     "needs_human_review": False}

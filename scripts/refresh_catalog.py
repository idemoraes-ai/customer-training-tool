#!/usr/bin/env python3
"""
Generate catalog.json for the Customer Training Recommendation Tool.

Calls the Trailhead Academy Apex API directly (no browser/Playwright needed).
Uses only Python stdlib — safe to run in GitHub Actions with no dependencies.

Output: catalog.json in the repo root, consumed by index.html at runtime.
"""

import json
import time
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

API_URL = (
    "https://trailheadacademy.salesforce.com"
    "/webruntime/api/apex/execute"
    "?language=en-US&asGuest=true&htmlEncode=false"
)

OUTPUT_FILE = Path(__file__).parent.parent / "catalog.json"

LANG_MAP = {
    "en_US": "English",
    "ja": "Japanese",
    "es": "Spanish",
    "fr": "French",
    "it": "Italian",
    "pt_BR": "Portuguese (Brazil)",
    "ko": "Korean",
    "de": "German",
    "zh_CN": "Chinese (Simplified)",
    "nl_NL": "Dutch",
    "pt_PT": "Portuguese (Portugal)",
    "es_MX": "Spanish (Mexico)",
    "iw": "Hebrew",
    "th": "Thai",
    "ko_KR": "Korean",
}

PRODUCT_MAP = {
    "Marketing": "Marketing Cloud",
    "Service": "Service Cloud",
    "Sales": "Sales Cloud",
    "Platform": "Platform",
    "Agentforce": "Agentforce",
    "Data Cloud": "Data Cloud",
    "Industries": "Industries",
    "MuleSoft": "MuleSoft",
    "Tableau": "Tableau",
    "Revenue": "Revenue Cloud / CPQ",
    "Commerce": "Commerce Cloud",
    "Experience": "Experience Cloud",
    "CRM Analytics": "CRM Analytics",
    "Net Zero": "Net Zero Cloud",
    "Field Service": "Field Service",
    "Slack": "Slack",
}

LEVEL_TO_MATURITY = {
    "Foundational": ["getting-started", "building"],
    "Intermediate": ["building", "optimizing"],
    "Advanced": ["optimizing", "strategic"],
    "Foundational; Intermediate": ["getting-started", "building", "optimizing"],
    "Advanced; Intermediate": ["building", "optimizing", "strategic"],
    "Intermediate; Advanced": ["building", "optimizing", "strategic"],
}

ASSET_TYPE_TO_TYPE = {
    "ILT_Course": "Course",
    "VIW": "Workshop",
}

SEARCH_TERMS = [
    "agentforce", "agent", "sales", "service", "marketing", "commerce",
    "data cloud", "tableau", "mulesoft", "platform", "revenue", "cpq",
    "field service", "experience cloud", "crm analytics", "industries",
    "slack", "integration", "flow", "automation", "analytics", "reporting",
    "security", "administration", "developer", "apex", "lightning",
    "knowledge", "omni", "einstein", "ai", "certification", "exam",
    "administrator", "consultant", "architect", "pardot", "account engagement",
    "billing", "pricing", "quote", "contract", "order", "net zero",
    "life sciences", "financial services", "health", "manufacturing",
    "omnistudio", "vlocity", "industries", "business rules",
    "SDC", "AGT", "AFS", "REV", "MSA", "SSC", "ASC", "ADX", "DEX",
    "MOC", "MKT", "PDX", "BSX", "SFS", "TAB", "TNX", "TTD",
    "BRE", "DGN", "DSF", "LSC", "NZC", "OMS", "COH",
]


def api_post(body_dict):
    payload = json.dumps(body_dict).encode("utf-8")
    req = urllib.request.Request(
        API_URL,
        data=payload,
        headers={
            "Content-Type": "application/json; charset=utf-8",
            "Referer": "https://trailheadacademy.salesforce.com/all-offerings",
            "User-Agent": "Mozilla/5.0",
        },
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read())


def search_courses(term):
    try:
        r = api_post({
            "namespace": "",
            "classname": "@udd/01pKV000007dt1L",
            "method": "getLearningAssets",
            "isContinuation": False,
            "params": {
                "searchDetails": {
                    "siteLanguage": "en_US",
                    "prerequisiteExams": "",
                    "numberOfResults": "500",
                    "pageNumber": "1",
                    "searchKey": term,
                    "catalogType": "Standard_Catalogs",
                    "eventSlug": "",
                    "assetType": "",
                    "searchCallType": "search",
                    "catalogIds": "[]",
                }
            },
            "cacheable": False,
        })
        rv = r.get("returnValue", {})
        if isinstance(rv, dict):
            return rv.get("learningAssetSearchWrapper", [])
    except Exception as e:
        print(f"  Warning: search({term!r}) failed: {e}")
    return []


def get_detail(slug):
    try:
        r = api_post({
            "namespace": "",
            "classname": "@udd/01pKV000007dt1L",
            "method": "getLearningAssetDetailBySlug",
            "isContinuation": False,
            "params": {"learningAssetSlug": slug, "language": "en_US"},
            "cacheable": False,
        })
        rv = r.get("returnValue", {})
        return rv if isinstance(rv, dict) else None
    except Exception:
        return None


def names_from_list(lst):
    if not lst:
        return []
    return [
        item.get("name", str(item)) if isinstance(item, dict) else str(item)
        for item in lst
        if item
    ]


def normalize_products(raw_list):
    out = []
    for p in raw_list:
        mapped = PRODUCT_MAP.get(p, p)
        if mapped not in out:
            out.append(mapped)
    return out


def discover_all_courses():
    seen = {}
    for term in SEARCH_TERMS:
        results = search_courses(term)
        for c in results:
            code = c.get("assetCode", "")
            if code and code not in seen:
                seen[code] = c
        time.sleep(0.2)
    print(f"Discovered {len(seen)} unique courses via search")
    return list(seen.values())


def build_catalog():
    print("Step 1: Discovering all courses...")
    courses = discover_all_courses()

    print(f"Step 2: Fetching detail for {len(courses)} courses...")
    entries = []
    for i, course in enumerate(courses, 1):
        slug = course.get("assetSlug", "")
        code = course.get("assetCode", "")
        title = course.get("title", "").strip()

        raw_products = names_from_list(course.get("products") or [])
        raw_roles    = names_from_list(course.get("roles") or [])
        level_str    = ""
        lang_str     = ""
        description  = course.get("shortDescription", "") or title
        asset_type   = course.get("assetType", "")

        if slug:
            detail = get_detail(slug)
            if detail:
                level_str = "; ".join(names_from_list(detail.get("levels") or []))
                las = detail.get("learningAssetSummary") or {}
                if isinstance(las, dict):
                    lang_code = las.get("authoredLanguage", "")
                    lang_str  = LANG_MAP.get(lang_code, lang_code)
                    if not raw_products:
                        raw_products = names_from_list(las.get("products") or [])
                    if not raw_roles:
                        raw_roles = names_from_list(las.get("roles") or [])
                    if not description or description == title:
                        description = las.get("shortDescription", "") or title

        if code.startswith("exam-"):
            item_type = "Certification Prep"
        else:
            item_type = ASSET_TYPE_TO_TYPE.get(asset_type, "Course")

        products = normalize_products(raw_products)
        maturity = LEVEL_TO_MATURITY.get(
            level_str,
            ["getting-started", "building", "optimizing", "strategic"],
        )

        entries.append({
            "id": i,
            "code": code,
            "name": title,
            "type": item_type,
            "tier": ["Premier", "Signature"],
            "products": products,
            "roles": raw_roles,
            "industry": ["All"],
            "maturity": maturity,
            "level": level_str,
            "language": lang_str,
            "description": description,
            "format": "Virtual",
            "link": f"https://trailheadacademy.salesforce.com/classes/{slug}" if slug else "",
        })

        if i % 25 == 0 or i == len(courses):
            print(f"  {i}/{len(courses)} processed")

        time.sleep(0.15)

    entries.sort(key=lambda e: e["name"].lower())
    for idx, e in enumerate(entries, 1):
        e["id"] = idx

    return {
        "generated": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "count": len(entries),
        "courses": entries,
    }


def main():
    data = build_catalog()
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print(f"\nWrote {data['count']} entries to {OUTPUT_FILE}")

    langs  = {}
    levels = {}
    types  = {}
    for e in data["courses"]:
        langs[e["language"]]  = langs.get(e["language"], 0)  + 1
        levels[e["level"]]    = levels.get(e["level"], 0)    + 1
        types[e["type"]]      = types.get(e["type"], 0)      + 1
    print(f"Types:     {dict(sorted(types.items(), key=lambda x: -x[1]))}")
    print(f"Languages: {dict(sorted(langs.items(), key=lambda x: -x[1]))}")


if __name__ == "__main__":
    main()

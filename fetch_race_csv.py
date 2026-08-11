#!/usr/bin/env python3
"""
Fetch the Vermont Secretary of State election-results XML feed and write a
CSV for ONE race, suitable for Datawrapper's "linked external data" source.

Configure the race to pull via the constants below.
"""

import csv
import sys
import urllib.request
import xml.etree.ElementTree as ET

# ---- Configure which race to extract -------------------------------------
FEED_URL = (
    "https://static.electionresults.vermont.gov/elections/rss/"
    "a18f77e0-89f8-4a01-8d97-61a7c75ba200/election-summary.xml"
)
OFFICE_NAME_MATCH = "STATE'S ATTORNEY"
OFFICE_DISTRICT_MATCH = "CHITTENDEN"
OUTPUT_CSV = "chittenden_states_attorney.csv"
# ---------------------------------------------------------------------------


def fetch_xml(url: str) -> ET.Element:
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=30) as resp:
        data = resp.read()
    return ET.fromstring(data)


def find_race(root: ET.Element, office_name: str, district: str) -> ET.Element:
    """Search the whole tree for an <Office> whose name/district match,
    regardless of how deeply it's nested in the feed."""
    for office in root.iter("Office"):
        name_el = office.find("OfficeName")
        district_el = office.find("OfficeDistrict")
        if name_el is None or district_el is None:
            continue
        name = (name_el.text or "").strip().upper()
        dist = (district_el.text or "").strip().upper()
        if office_name.upper() in name and district.upper() in dist:
            return office
    raise ValueError(
        f"No <Office> found matching name containing '{office_name}' "
        f"and district containing '{district}'"
    )


def extract_rows(office: ET.Element):
    rows = []
    total_candidate_votes = 0

    candidates = []
    for cand in office.findall("Candidate"):
        name = (cand.findtext("Name") or "").strip()
        votes_text = (cand.findtext("Votes") or "0").strip()
        try:
            votes = int(votes_text)
        except ValueError:
            votes = 0
        candidates.append((name, votes))
        total_candidate_votes += votes

    for name, votes in candidates:
        pct = (votes / total_candidate_votes * 100) if total_candidate_votes else 0.0
        rows.append(
            {
                "Candidate": name,
                "Votes": votes,
                "Percent": round(pct, 2),
            }
        )

    # Sort highest votes first (nice default for a bar chart)
    rows.sort(key=lambda r: r["Votes"], reverse=True)
    return rows


def write_csv(rows, path: str):
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["Candidate", "Votes", "Percent"])
        writer.writeheader()
        writer.writerows(rows)


def main():
    try:
        root = fetch_xml(FEED_URL)
        office = find_race(root, OFFICE_NAME_MATCH, OFFICE_DISTRICT_MATCH)
        rows = extract_rows(office)
        if not rows:
            print("Found the race but no candidates parsed — check XML structure.", file=sys.stderr)
            sys.exit(1)
        write_csv(rows, OUTPUT_CSV)
        print(f"Wrote {OUTPUT_CSV}:")
        for r in rows:
            print(f"  {r['Candidate']}: {r['Votes']} votes ({r['Percent']}%)")
    except Exception as e:
        print(f"ERROR: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()

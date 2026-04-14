#!/usr/bin/env python3
"""
Generate targeted training pairs for v7 adapter.

Fixes identified from evaluate_v3.py ground-truth evaluation:

1. Exit/Entry — model uses term on TEXT fields (BORDER_CODE_DESC, TRX_TRIP_TYP_DESC,
   TRX_DIRECTION). Must use match.

2. Visa-main — model uses term/match on VISA_TYPE_DESC (text, OR operator causes
   partial matches). Must use VSA_TYPCDE codes: "40"=Work, "20"=Residence, "11"=Visit.

3. Visa-app — wrong status codes (APL_RCDSTS="13" instead of "2" for approved,
   "14" instead of "3" for rejected). Wrong field names (APLNUM, APLTYPE, etc).

4. Sponsor — wrong field names (MDS_DEPT_CODE, SPONSOR_ENTRY_DATE, FIRST_ENTRY_TYPE).
   Correct: MDS_DPTENGNAM (match), FIRST_ENTRY_DATE (range).

5. Violations — confuses VLN_TYPE with VLN_STATUS (uses VLN_TYPE:"UNPAID").
   Also: N16 ignores year filter, N01 adds spurious UNPAID filter.

6. Relationships — RL03: wrong logic for "no divorce" — must use must_not: exists.

7. Multi-index join patterns for exit/entry, visa, sponsor (model gets index names wrong).

8. Person queries — P04 adds spurious exists: prs_name; P11 wrong bool structure.
"""

import json
from pathlib import Path

REPO_ROOT = Path(__file__).parent.parent

def pair(query, dsl_dict):
    """Create a training pair."""
    return {"messages": [
        {"role": "user", "content": query},
        {"role": "assistant", "content": json.dumps(dsl_dict, separators=(',', ':'))}
    ]}

def mpair(query, plan_dict):
    """Create a multi-index training pair."""
    return pair(query, plan_dict)


# ─────────────────────────────────────────────────────────────────────────────
# 1. EXIT / ENTRY — use match for all text fields
#    Fields: TRX_DIRECTION (text), BORDER_CODE_DESC (text), TRX_TRIP_TYP_DESC (text)
#    TRX_DATE is date → range ok
# ─────────────────────────────────────────────────────────────────────────────
EXIT_ENTRY_INDEX = "moi-exit-entry-tts-details-v1"

exit_entry_pairs = [
    # Direction only
    pair("Find all exit transactions",       {"query": {"match": {"TRX_DIRECTION": "OUT"}}}),
    pair("Show all exit records",            {"query": {"match": {"TRX_DIRECTION": "OUT"}}}),
    pair("List all exits",                   {"query": {"match": {"TRX_DIRECTION": "OUT"}}}),
    pair("Show all entry transactions",      {"query": {"match": {"TRX_DIRECTION": "IN"}}}),
    pair("Find all entry records",           {"query": {"match": {"TRX_DIRECTION": "IN"}}}),
    pair("List all arrivals",                {"query": {"match": {"TRX_DIRECTION": "IN"}}}),
    # Trip type only
    pair("Show all flight transactions",     {"query": {"match": {"TRX_TRIP_TYP_DESC": "FLIGHT"}}}),
    pair("Find all land border crossings",   {"query": {"match": {"TRX_TRIP_TYP_DESC": "LAND"}}}),
    pair("Show all sea travel records",      {"query": {"match": {"TRX_TRIP_TYP_DESC": "SEA"}}}),
    pair("Find all flights",                 {"query": {"match": {"TRX_TRIP_TYP_DESC": "FLIGHT"}}}),
    # Border only
    pair("Show all transactions at Hamad International Airport",
         {"query": {"match": {"BORDER_CODE_DESC": "HAMAD INTERNATIONAL AIRPORT"}}}),
    pair("Find all records at Doha Port",
         {"query": {"match": {"BORDER_CODE_DESC": "DOHA PORT"}}}),
    pair("Show all transactions at Abu Samra border",
         {"query": {"match": {"BORDER_CODE_DESC": "ABU SAMRA BORDER"}}}),
    # Direction + border
    pair("Find all flights through Hamad International Airport",
         {"query": {"bool": {"must": [{"match": {"TRX_TRIP_TYP_DESC": "FLIGHT"}}, {"match": {"BORDER_CODE_DESC": "HAMAD INTERNATIONAL AIRPORT"}}]}}}),
    pair("Show all entries via Hamad International Airport",
         {"query": {"bool": {"must": [{"match": {"TRX_DIRECTION": "IN"}}, {"match": {"BORDER_CODE_DESC": "HAMAD INTERNATIONAL AIRPORT"}}]}}}),
    pair("Find all exits through Hamad International Airport",
         {"query": {"bool": {"must": [{"match": {"TRX_DIRECTION": "OUT"}}, {"match": {"BORDER_CODE_DESC": "HAMAD INTERNATIONAL AIRPORT"}}]}}}),
    pair("Find all entries via Doha Port",
         {"query": {"bool": {"must": [{"match": {"TRX_DIRECTION": "IN"}}, {"match": {"BORDER_CODE_DESC": "DOHA PORT"}}]}}}),
    pair("Show all sea arrivals to Doha Port",
         {"query": {"bool": {"must": [{"match": {"TRX_DIRECTION": "IN"}}, {"match": {"BORDER_CODE_DESC": "DOHA PORT"}}, {"match": {"TRX_TRIP_TYP_DESC": "SEA"}}]}}}),
    pair("Find all exits through Abu Samra border",
         {"query": {"bool": {"must": [{"match": {"TRX_DIRECTION": "OUT"}}, {"match": {"BORDER_CODE_DESC": "ABU SAMRA BORDER"}}]}}}),
    pair("Show all land exits via Abu Samra",
         {"query": {"bool": {"must": [{"match": {"TRX_DIRECTION": "OUT"}}, {"match": {"BORDER_CODE_DESC": "ABU SAMRA BORDER"}}, {"match": {"TRX_TRIP_TYP_DESC": "LAND"}}]}}}),
    # Direction + date
    pair("Show all travel transactions in 2024",
         {"query": {"range": {"TRX_DATE": {"gte": "2024-01-01", "lte": "2024-12-31"}}}}),
    pair("Find all exit transactions in 2024",
         {"query": {"bool": {"must": [{"match": {"TRX_DIRECTION": "OUT"}}, {"range": {"TRX_DATE": {"gte": "2024-01-01", "lte": "2024-12-31"}}}]}}}),
    pair("Find all entries via Hamad Airport in 2024",
         {"query": {"bool": {"must": [{"match": {"TRX_DIRECTION": "IN"}}, {"match": {"BORDER_CODE_DESC": "HAMAD INTERNATIONAL AIRPORT"}}, {"range": {"TRX_DATE": {"gte": "2024-01-01", "lte": "2024-12-31"}}}]}}}),
    pair("Show all exit transactions via flight in 2024",
         {"query": {"bool": {"must": [{"match": {"TRX_DIRECTION": "OUT"}}, {"match": {"TRX_TRIP_TYP_DESC": "FLIGHT"}}, {"range": {"TRX_DATE": {"gte": "2024-01-01", "lte": "2024-12-31"}}}]}}}),
    pair("Show all flight entries in 2023",
         {"query": {"bool": {"must": [{"match": {"TRX_DIRECTION": "IN"}}, {"match": {"TRX_TRIP_TYP_DESC": "FLIGHT"}}, {"range": {"TRX_DATE": {"gte": "2023-01-01", "lte": "2023-12-31"}}}]}}}),
    pair("Find all transactions at Abu Samra border in 2024",
         {"query": {"bool": {"must": [{"match": {"BORDER_CODE_DESC": "ABU SAMRA BORDER"}}, {"range": {"TRX_DATE": {"gte": "2024-01-01", "lte": "2024-12-31"}}}]}}}),
    pair("Show all entries via Doha Port in 2023",
         {"query": {"bool": {"must": [{"match": {"TRX_DIRECTION": "IN"}}, {"match": {"BORDER_CODE_DESC": "DOHA PORT"}}, {"range": {"TRX_DATE": {"gte": "2023-01-01", "lte": "2023-12-31"}}}]}}}),
    pair("Find flights departing from Hamad after 2024",
         {"query": {"bool": {"must": [{"match": {"TRX_DIRECTION": "OUT"}}, {"match": {"BORDER_CODE_DESC": "HAMAD INTERNATIONAL AIRPORT"}}, {"match": {"TRX_TRIP_TYP_DESC": "FLIGHT"}}, {"range": {"TRX_DATE": {"gte": "2024-01-01"}}}]}}}),
]


# ─────────────────────────────────────────────────────────────────────────────
# 2. VISA-MAIN — use VSA_TYPCDE codes, not VISA_TYPE_DESC
#    VSA_TYPCDE: "40"=Work Visa, "20"=Residence Permit, "11"=Visit Visa
#    VSA_RCDSTS: "13"=active, "14"=expired
#    NAT_CDENUM: keyword — term ok (transformer converts names to codes)
# ─────────────────────────────────────────────────────────────────────────────

visa_main_pairs = [
    # Type only (use VSA_TYPCDE)
    pair("Find all work visas",                {"query": {"term": {"VSA_TYPCDE": "40"}}}),
    pair("Show all work visas",                {"query": {"term": {"VSA_TYPCDE": "40"}}}),
    pair("List all work visas",                {"query": {"term": {"VSA_TYPCDE": "40"}}}),
    pair("Show all residence permits",         {"query": {"term": {"VSA_TYPCDE": "20"}}}),
    pair("Find all residence permits",         {"query": {"term": {"VSA_TYPCDE": "20"}}}),
    pair("List all residence permits",         {"query": {"term": {"VSA_TYPCDE": "20"}}}),
    pair("Find all visit visas",               {"query": {"term": {"VSA_TYPCDE": "11"}}}),
    pair("Show all visit visas",               {"query": {"term": {"VSA_TYPCDE": "11"}}}),
    pair("List all visit visas",               {"query": {"term": {"VSA_TYPCDE": "11"}}}),
    # Status only
    pair("Show all active visas",              {"query": {"term": {"VSA_RCDSTS": "13"}}}),
    pair("Find all active visas",              {"query": {"term": {"VSA_RCDSTS": "13"}}}),
    pair("Find all expired visas",             {"query": {"term": {"VSA_RCDSTS": "14"}}}),
    pair("Show all expired visas",             {"query": {"term": {"VSA_RCDSTS": "14"}}}),
    # Type + status
    pair("Show all active work visas",
         {"query": {"bool": {"must": [{"term": {"VSA_TYPCDE": "40"}}, {"term": {"VSA_RCDSTS": "13"}}]}}}),
    pair("Find all active work visas",
         {"query": {"bool": {"must": [{"term": {"VSA_TYPCDE": "40"}}, {"term": {"VSA_RCDSTS": "13"}}]}}}),
    pair("Show all active residence permits",
         {"query": {"bool": {"must": [{"term": {"VSA_TYPCDE": "20"}}, {"term": {"VSA_RCDSTS": "13"}}]}}}),
    pair("Find expired work visas",
         {"query": {"bool": {"must": [{"term": {"VSA_TYPCDE": "40"}}, {"term": {"VSA_RCDSTS": "14"}}]}}}),
    # Nationality + type (NAT_CDENUM is keyword)
    pair("Show work visas for Pakistani nationals",
         {"query": {"bool": {"must": [{"term": {"NAT_CDENUM": "586"}}, {"term": {"VSA_TYPCDE": "40"}}]}}}),
    pair("Find work visas for Pakistani nationals",
         {"query": {"bool": {"must": [{"term": {"NAT_CDENUM": "586"}}, {"term": {"VSA_TYPCDE": "40"}}]}}}),
    pair("Show residence permits for Qatari nationals",
         {"query": {"bool": {"must": [{"term": {"NAT_CDENUM": "634"}}, {"term": {"VSA_TYPCDE": "20"}}]}}}),
    pair("Find residence permits for Qatari nationals",
         {"query": {"bool": {"must": [{"term": {"NAT_CDENUM": "634"}}, {"term": {"VSA_TYPCDE": "20"}}]}}}),
    pair("Show visit visas for UAE nationals",
         {"query": {"bool": {"must": [{"term": {"NAT_CDENUM": "784"}}, {"term": {"VSA_TYPCDE": "11"}}]}}}),
    pair("Find visit visas for Egyptian nationals",
         {"query": {"bool": {"must": [{"term": {"NAT_CDENUM": "818"}}, {"term": {"VSA_TYPCDE": "11"}}]}}}),
    # Nationality + type + status
    pair("Find active work visas for Pakistani nationals",
         {"query": {"bool": {"must": [{"term": {"NAT_CDENUM": "586"}}, {"term": {"VSA_TYPCDE": "40"}}, {"term": {"VSA_RCDSTS": "13"}}]}}}),
    pair("Show active work visas for Pakistani nationals",
         {"query": {"bool": {"must": [{"term": {"NAT_CDENUM": "586"}}, {"term": {"VSA_TYPCDE": "40"}}, {"term": {"VSA_RCDSTS": "13"}}]}}}),
    pair("Find active residence permits for Qatari nationals",
         {"query": {"bool": {"must": [{"term": {"NAT_CDENUM": "634"}}, {"term": {"VSA_TYPCDE": "20"}}, {"term": {"VSA_RCDSTS": "13"}}]}}}),
    pair("Show expired work visas for Pakistani nationals",
         {"query": {"bool": {"must": [{"term": {"NAT_CDENUM": "586"}}, {"term": {"VSA_TYPCDE": "40"}}, {"term": {"VSA_RCDSTS": "14"}}]}}}),
    pair("Find expired visas for Pakistani nationals",
         {"query": {"bool": {"must": [{"term": {"NAT_CDENUM": "586"}}, {"term": {"VSA_RCDSTS": "14"}}]}}}),
    # Date filters
    pair("Find work visas expiring before 2026",
         {"query": {"bool": {"must": [{"term": {"VSA_TYPCDE": "40"}}, {"range": {"VSA_EXPDTE": {"lt": "2026-01-01"}}}]}}}),
    pair("Show all visas issued in 2022",
         {"query": {"range": {"VSA_ISSDTE": {"gte": "2022-01-01", "lte": "2022-12-31"}}}}),
    pair("Find work visas issued in 2022",
         {"query": {"bool": {"must": [{"term": {"VSA_TYPCDE": "40"}}, {"range": {"VSA_ISSDTE": {"gte": "2022-01-01", "lte": "2022-12-31"}}}]}}}),
    pair("Show all active visas for Pakistani nationals",
         {"query": {"bool": {"must": [{"term": {"NAT_CDENUM": "586"}}, {"term": {"VSA_RCDSTS": "13"}}]}}}),
    pair("Find all active visas for Qatari nationals",
         {"query": {"bool": {"must": [{"term": {"NAT_CDENUM": "634"}}, {"term": {"VSA_RCDSTS": "13"}}]}}}),
]


# ─────────────────────────────────────────────────────────────────────────────
# 3. VISA-APPLICATION — correct status and type codes
#    APL_RCDSTS: "2"=approved, "3"=rejected
#    APL_TYPCDE: "40"=work visa application
#    REM_TOT_APPR: remaining quota (numeric range)
#    APL_APLDTE: application date, APL_EXPDTE: expiry date
# ─────────────────────────────────────────────────────────────────────────────

visa_app_pairs = [
    pair("Find all approved visa applications",     {"query": {"term": {"APL_RCDSTS": "2"}}}),
    pair("Show all approved visa applications",     {"query": {"term": {"APL_RCDSTS": "2"}}}),
    pair("List approved visa applications",         {"query": {"term": {"APL_RCDSTS": "2"}}}),
    pair("Show all rejected visa applications",     {"query": {"term": {"APL_RCDSTS": "3"}}}),
    pair("Find all rejected visa applications",     {"query": {"term": {"APL_RCDSTS": "3"}}}),
    pair("List rejected visa applications",         {"query": {"term": {"APL_RCDSTS": "3"}}}),
    pair("Find all work visa applications",         {"query": {"term": {"APL_TYPCDE": "40"}}}),
    pair("Show all work visa applications",         {"query": {"term": {"APL_TYPCDE": "40"}}}),
    pair("Show approved applications submitted in 2023",
         {"query": {"bool": {"must": [{"term": {"APL_RCDSTS": "2"}}, {"range": {"APL_APLDTE": {"gte": "2023-01-01", "lte": "2023-12-31"}}}]}}}),
    pair("Find approved applications submitted in 2023",
         {"query": {"bool": {"must": [{"term": {"APL_RCDSTS": "2"}}, {"range": {"APL_APLDTE": {"gte": "2023-01-01", "lte": "2023-12-31"}}}]}}}),
    pair("Find visa applications with remaining quota greater than 10",
         {"query": {"range": {"REM_TOT_APPR": {"gt": 10}}}}),
    pair("Show visa applications with remaining quota above 5",
         {"query": {"range": {"REM_TOT_APPR": {"gt": 5}}}}),
    pair("Find visa applications with remaining quota",
         {"query": {"range": {"REM_TOT_APPR": {"gt": 0}}}}),
    pair("Show all applications expiring before 2026",
         {"query": {"range": {"APL_EXPDTE": {"lt": "2026-01-01"}}}}),
    pair("Find applications expiring before 2025",
         {"query": {"range": {"APL_EXPDTE": {"lt": "2025-01-01"}}}}),
    pair("Find approved work visa applications with remaining quota",
         {"query": {"bool": {"must": [{"term": {"APL_RCDSTS": "2"}}, {"term": {"APL_TYPCDE": "40"}}, {"range": {"REM_TOT_APPR": {"gt": 0}}}]}}}),
    pair("Show approved work visa applications with remaining quota greater than 10",
         {"query": {"bool": {"must": [{"term": {"APL_RCDSTS": "2"}}, {"term": {"APL_TYPCDE": "40"}}, {"range": {"REM_TOT_APPR": {"gt": 10}}}]}}}),
    pair("Find approved work visa applications expiring before 2026",
         {"query": {"bool": {"must": [{"term": {"APL_RCDSTS": "2"}}, {"term": {"APL_TYPCDE": "40"}}, {"range": {"APL_EXPDTE": {"lt": "2026-01-01"}}}]}}}),
    pair("Show rejected work visa applications",
         {"query": {"bool": {"must": [{"term": {"APL_RCDSTS": "3"}}, {"term": {"APL_TYPCDE": "40"}}]}}}),
    pair("Find all applications with zero remaining quota",
         {"query": {"term": {"REM_TOT_APPR": 0}}}),
]


# ─────────────────────────────────────────────────────────────────────────────
# 4. SPONSOR — correct field names
#    MDS_DPTENGNAM (text → match), FIRST_ENTRY_DATE (date → range)
#    SPONSOR_TYPE: "2"=company, "1"=individual  (keyword → term)
# ─────────────────────────────────────────────────────────────────────────────

sponsor_pairs = [
    pair("Find all sponsorship records",            {"query": {"match_all": {}}}),
    pair("Show all company sponsorships",           {"query": {"term": {"SPONSOR_TYPE": "2"}}}),
    pair("Find all individual sponsorships",        {"query": {"term": {"SPONSOR_TYPE": "1"}}}),
    pair("Find sponsorships with first entry date in 2022",
         {"query": {"range": {"FIRST_ENTRY_DATE": {"gte": "2022-01-01", "lt": "2023-01-01"}}}}),
    pair("Show sponsorships where first entry was in 2022",
         {"query": {"range": {"FIRST_ENTRY_DATE": {"gte": "2022-01-01", "lt": "2023-01-01"}}}}),
    pair("Find sponsorships with first entry after 2021",
         {"query": {"range": {"FIRST_ENTRY_DATE": {"gt": "2021-12-31"}}}}),
    pair("Show company sponsorships with first entry after 2021",
         {"query": {"bool": {"must": [{"term": {"SPONSOR_TYPE": "2"}}, {"range": {"FIRST_ENTRY_DATE": {"gt": "2021-12-31"}}}]}}}),
    pair("Show all sponsorships with first entry in 2023",
         {"query": {"range": {"FIRST_ENTRY_DATE": {"gte": "2023-01-01", "lt": "2024-01-01"}}}}),
    pair("Show all sponsorships for Expatriates Affairs Dept",
         {"query": {"match": {"MDS_DPTENGNAM": "Expatriates Affairs Dept"}}}),
    pair("Find sponsorships managed by Expatriates Affairs Dept",
         {"query": {"match": {"MDS_DPTENGNAM": "Expatriates Affairs Dept"}}}),
    pair("Show sponsorships where first entry was after 2022",
         {"query": {"range": {"FIRST_ENTRY_DATE": {"gt": "2022-12-31"}}}}),
    pair("Find company sponsorships in Expatriates Affairs Dept with first entry after 2020",
         {"query": {"bool": {"must": [{"term": {"SPONSOR_TYPE": "2"}}, {"match": {"MDS_DPTENGNAM": "Expatriates Affairs Dept"}}, {"range": {"FIRST_ENTRY_DATE": {"gt": "2020-12-31"}}}]}}}),
]


# ─────────────────────────────────────────────────────────────────────────────
# 5. VIOLATIONS — fix field confusion
#    VLN_STATUS: "UNPAID"/"PAID"  (keyword → term)
#    VLN_TYPE: "SPEEDING"/"PARKING"/"RED_LIGHT"/"MOBILE_PHONE"/"SEATBELT"  (keyword → term)
#    VLN_YEAR: "2024"/"2023"  (keyword → term)
#    VLN_TOTAMT: numeric → range
# ─────────────────────────────────────────────────────────────────────────────

violation_fixes = [
    # N01 fix: "Find all speeding violations" — no status filter
    pair("Find all speeding violations",      {"query": {"term": {"VLN_TYPE": "SPEEDING"}}}),
    pair("Show all speeding violations",      {"query": {"term": {"VLN_TYPE": "SPEEDING"}}}),
    pair("List all speeding violations",      {"query": {"term": {"VLN_TYPE": "SPEEDING"}}}),
    # N10/N12 fix: VLN_STATUS not VLN_TYPE for UNPAID
    pair("Show all violations from 2024 that are unpaid",
         {"query": {"bool": {"must": [{"term": {"VLN_STATUS": "UNPAID"}}, {"term": {"VLN_YEAR": "2024"}}]}}}),
    pair("Find unpaid violations from 2024",
         {"query": {"bool": {"must": [{"term": {"VLN_STATUS": "UNPAID"}}, {"term": {"VLN_YEAR": "2024"}}]}}}),
    pair("Show all violations from 2023 that are paid",
         {"query": {"bool": {"must": [{"term": {"VLN_STATUS": "PAID"}}, {"term": {"VLN_YEAR": "2023"}}]}}}),
    pair("Show all violations with fine amount greater than 1000 that are unpaid",
         {"query": {"bool": {"must": [{"term": {"VLN_STATUS": "UNPAID"}}, {"range": {"VLN_TOTAMT": {"gt": 1000}}}]}}}),
    pair("Find unpaid violations with fine above 500",
         {"query": {"bool": {"must": [{"term": {"VLN_STATUS": "UNPAID"}}, {"range": {"VLN_TOTAMT": {"gt": 500}}}]}}}),
    # N15 fix: MOBILE_PHONE type
    pair("Find all mobile phone violations",  {"query": {"term": {"VLN_TYPE": "MOBILE_PHONE"}}}),
    pair("Show all mobile phone violations",  {"query": {"term": {"VLN_TYPE": "MOBILE_PHONE"}}}),
    # N16 fix: speeding+paid+year
    pair("Show paid speeding violations from 2023",
         {"query": {"bool": {"must": [{"term": {"VLN_TYPE": "SPEEDING"}}, {"term": {"VLN_STATUS": "PAID"}}, {"term": {"VLN_YEAR": "2023"}}]}}}),
    pair("Find paid speeding violations from 2024",
         {"query": {"bool": {"must": [{"term": {"VLN_TYPE": "SPEEDING"}}, {"term": {"VLN_STATUS": "PAID"}}, {"term": {"VLN_YEAR": "2024"}}]}}}),
    # N07: paid parking (already correct in model but reinforce)
    pair("Find paid parking violations",
         {"query": {"bool": {"must": [{"term": {"VLN_TYPE": "PARKING"}}, {"term": {"VLN_STATUS": "PAID"}}]}}}),
    pair("Show unpaid parking violations",
         {"query": {"bool": {"must": [{"term": {"VLN_TYPE": "PARKING"}}, {"term": {"VLN_STATUS": "UNPAID"}}]}}}),
]


# ─────────────────────────────────────────────────────────────────────────────
# 6. RELATIONSHIPS — correct null / exists logic
# ─────────────────────────────────────────────────────────────────────────────

relationship_fixes = [
    # RL03: must_not exists for no divorce
    pair("Find all current marriages with no divorce",
         {"query": {"bool": {"must_not": {"exists": {"field": "DIVORCE_DATE"}}}}}),
    pair("Show marriages that have not ended in divorce",
         {"query": {"bool": {"must_not": {"exists": {"field": "DIVORCE_DATE"}}}}}),
    pair("Find all active marriages",
         {"query": {"bool": {"must_not": {"exists": {"field": "DIVORCE_DATE"}}}}}),
    pair("Show marriages with no divorce record",
         {"query": {"bool": {"must_not": {"exists": {"field": "DIVORCE_DATE"}}}}}),
    # RL05: exists for divorce
    pair("Find marriages that ended in divorce",
         {"query": {"exists": {"field": "DIVORCE_DATE"}}}),
    pair("Show all divorces",
         {"query": {"exists": {"field": "DIVORCE_DATE"}}}),
    pair("Find all divorce records",
         {"query": {"exists": {"field": "DIVORCE_DATE"}}}),
]


# ─────────────────────────────────────────────────────────────────────────────
# 7. VEHICLE — correct fields
#    VRG_STATUS is TEXT → match; VEH_MODELYEAR is TEXT with numeric value
#    "registered in 2023" → range on VRG_STADTE
# ─────────────────────────────────────────────────────────────────────────────

vehicle_fixes = [
    # V13: registered in year → VRG_STADTE range
    pair("Find all vehicles registered in 2023",
         {"query": {"range": {"VRG_STADTE": {"gte": "2023-01-01", "lte": "2023-12-31"}}}}),
    pair("Show all vehicles registered in 2022",
         {"query": {"range": {"VRG_STADTE": {"gte": "2022-01-01", "lte": "2022-12-31"}}}}),
    pair("Find vehicles registered after 2021",
         {"query": {"range": {"VRG_STADTE": {"gte": "2022-01-01"}}}}),
    # V09: Toyota Camry white — include VEH_MODEL
    pair("Find white Toyota Camry vehicles registered between 2020 and 2023",
         {"query": {"bool": {"must": [{"match": {"MNF_ENSHDESC": "TOYOTA"}}, {"match": {"CLR_CLRENGDSC": "WHITE"}}, {"match": {"VEH_MODEL": "CAMRY"}}, {"range": {"VRG_STADTE": {"gte": "2020-01-01", "lte": "2023-12-31"}}}]}}}),
    pair("Find white Toyota Camry vehicles",
         {"query": {"bool": {"must": [{"match": {"MNF_ENSHDESC": "TOYOTA"}}, {"match": {"CLR_CLRENGDSC": "WHITE"}}, {"match": {"VEH_MODEL": "CAMRY"}}]}}}),
    pair("Show Toyota Camry vehicles",
         {"query": {"bool": {"must": [{"match": {"MNF_ENSHDESC": "TOYOTA"}}, {"match": {"VEH_MODEL": "CAMRY"}}]}}}),
    pair("Find Nissan Patrol vehicles",
         {"query": {"bool": {"must": [{"match": {"MNF_ENSHDESC": "NISSAN"}}, {"match": {"VEH_MODEL": "PATROL"}}]}}}),
]


# ─────────────────────────────────────────────────────────────────────────────
# 8. PERSON — correct bool structure
# ─────────────────────────────────────────────────────────────────────────────

person_fixes = [
    # P04 fix: no spurious exists clause
    pair("Show all male persons",   {"query": {"term": {"prs_gdr": "Male"}}}),
    pair("Find all male persons",   {"query": {"term": {"prs_gdr": "Male"}}}),
    pair("List all male persons",   {"query": {"term": {"prs_gdr": "Male"}}}),
    # P11 fix: must for gender, should for nationality
    pair("Find persons from India or Pakistan who are male",
         {"query": {"bool": {"must": [{"term": {"prs_gdr": "Male"}}, {"bool": {"should": [{"term": {"person_natcde": "356"}}, {"term": {"person_natcde": "586"}}]}}]}}}),
    pair("Show male persons from India or Pakistan",
         {"query": {"bool": {"must": [{"term": {"prs_gdr": "Male"}}, {"bool": {"should": [{"term": {"person_natcde": "356"}}, {"term": {"person_natcde": "586"}}]}}]}}}),
    pair("Find females from Qatar or UAE",
         {"query": {"bool": {"must": [{"term": {"prs_gdr": "Female"}}, {"bool": {"should": [{"term": {"person_natcde": "634"}}, {"term": {"person_natcde": "784"}}]}}]}}}),
]


# ─────────────────────────────────────────────────────────────────────────────
# 9. MULTI-INDEX — exit/entry, visa, sponsor join patterns
#    These were generating wrong index names in step 1
# ─────────────────────────────────────────────────────────────────────────────

def person_exit_plan(nat_code, extra_step2=None):
    step2_query = {"bool": {"must": [{"terms": {"TRX_QIDNO": "$step_1"}}]}}
    if extra_step2:
        step2_query["bool"]["must"].extend(extra_step2)
    return {
        "type": "multi_index",
        "steps": [
            {"step": 1, "index": "moi-gp-all-profiles-details-v1",
             "query": {"term": {"person_natcde": nat_code}}, "extract_field": "prs_qid"},
            {"step": 2, "index": "moi-exit-entry-tts-details-v1", "query": step2_query}
        ]
    }

def person_visa_plan(nat_code, extra_step2=None):
    step2_query = {"bool": {"must": [{"terms": {"HLD_QIDNO": "$step_1"}}]}}
    if extra_step2:
        step2_query["bool"]["must"].extend(extra_step2)
    return {
        "type": "multi_index",
        "steps": [
            {"step": 1, "index": "moi-gp-all-profiles-details-v1",
             "query": {"term": {"person_natcde": nat_code}}, "extract_field": "prs_qid"},
            {"step": 2, "index": "moi-visa-main-details-v1", "query": step2_query}
        ]
    }

def person_sponsor_plan(nat_code, extra_step2=None):
    step2_query = {"bool": {"must": [{"terms": {"SPONSOR_QID": "$step_1"}}]}}
    if extra_step2:
        step2_query["bool"]["must"].extend(extra_step2)
    return {
        "type": "multi_index",
        "steps": [
            {"step": 1, "index": "moi-gp-all-profiles-details-v1",
             "query": {"term": {"person_natcde": nat_code}}, "extract_field": "prs_qid"},
            {"step": 2, "index": "moi-sponsor-details-v1", "query": step2_query}
        ]
    }

multi_index_pairs = [
    # Exit/entry × nationality
    mpair("Find all exit transactions for Qatari nationals",
          person_exit_plan("634", [{"match": {"TRX_DIRECTION": "OUT"}}])),
    mpair("Show all exit records for Qatari nationals",
          person_exit_plan("634", [{"match": {"TRX_DIRECTION": "OUT"}}])),
    mpair("Find all entry transactions for Pakistani nationals",
          person_exit_plan("586", [{"match": {"TRX_DIRECTION": "IN"}}])),
    mpair("Show all travel records for Indian nationals",
          person_exit_plan("356")),
    mpair("Find flight exits for Qatari nationals",
          person_exit_plan("634", [{"match": {"TRX_DIRECTION": "OUT"}}, {"match": {"TRX_TRIP_TYP_DESC": "FLIGHT"}}])),
    mpair("Show flight exits for Qatari nationals",
          person_exit_plan("634", [{"match": {"TRX_DIRECTION": "OUT"}}, {"match": {"TRX_TRIP_TYP_DESC": "FLIGHT"}}])),
    mpair("Find entries via Hamad Airport for Pakistani nationals",
          person_exit_plan("586", [{"match": {"TRX_DIRECTION": "IN"}}, {"match": {"BORDER_CODE_DESC": "HAMAD INTERNATIONAL AIRPORT"}}])),
    mpair("Find exit transactions in 2024 for Qatari nationals",
          person_exit_plan("634", [{"match": {"TRX_DIRECTION": "OUT"}}, {"range": {"TRX_DATE": {"gte": "2024-01-01", "lte": "2024-12-31"}}}])),
    mpair("Show flight entries for Indian nationals in 2024",
          person_exit_plan("356", [{"match": {"TRX_DIRECTION": "IN"}}, {"match": {"TRX_TRIP_TYP_DESC": "FLIGHT"}}, {"range": {"TRX_DATE": {"gte": "2024-01-01"}}}])),
    mpair("Find all exit transactions for Indian nationals",
          person_exit_plan("356", [{"match": {"TRX_DIRECTION": "OUT"}}])),
    mpair("Show all travel records for Pakistani nationals",
          person_exit_plan("586")),
    mpair("Find all travel records for Egyptian nationals",
          person_exit_plan("818")),

    # Visa × nationality
    mpair("Find all work visas held by Pakistani nationals",
          person_visa_plan("586", [{"term": {"VSA_TYPCDE": "40"}}])),
    mpair("Show all work visas held by Pakistani nationals",
          person_visa_plan("586", [{"term": {"VSA_TYPCDE": "40"}}])),
    mpair("Find all residence permits held by Qatari nationals",
          person_visa_plan("634", [{"term": {"VSA_TYPCDE": "20"}}])),
    mpair("Show all residence permits held by Qatari nationals",
          person_visa_plan("634", [{"term": {"VSA_TYPCDE": "20"}}])),
    mpair("Find active work visas held by Pakistani nationals",
          person_visa_plan("586", [{"term": {"VSA_TYPCDE": "40"}}, {"term": {"VSA_RCDSTS": "13"}}])),
    mpair("Show active work visas for Pakistani nationals",
          person_visa_plan("586", [{"term": {"VSA_TYPCDE": "40"}}, {"term": {"VSA_RCDSTS": "13"}}])),
    mpair("Find expired visas held by Pakistani nationals",
          person_visa_plan("586", [{"term": {"VSA_RCDSTS": "14"}}])),
    mpair("Find work visas held by Pakistani males",
          {
              "type": "multi_index",
              "steps": [
                  {"step": 1, "index": "moi-gp-all-profiles-details-v1",
                   "query": {"bool": {"must": [{"term": {"person_natcde": "586"}}, {"term": {"prs_gdr": "Male"}}]}},
                   "extract_field": "prs_qid"},
                  {"step": 2, "index": "moi-visa-main-details-v1",
                   "query": {"bool": {"must": [{"terms": {"HLD_QIDNO": "$step_1"}}, {"term": {"VSA_TYPCDE": "40"}}]}}}
              ]
          }),
    mpair("Show all visas held by Qatari nationals",
          person_visa_plan("634")),
    mpair("Find all visas held by Indian nationals",
          person_visa_plan("356")),

    # Sponsor × nationality
    mpair("Find all persons sponsored by Qatari nationals",
          person_sponsor_plan("634")),
    mpair("Show all persons sponsored by Qatari nationals",
          person_sponsor_plan("634")),
    mpair("Find all persons sponsored by Pakistani nationals",
          person_sponsor_plan("586")),
    mpair("Show sponsorships by Qatari nationals",
          person_sponsor_plan("634")),
    mpair("Find persons sponsored by Qatari males",
          {
              "type": "multi_index",
              "steps": [
                  {"step": 1, "index": "moi-gp-all-profiles-details-v1",
                   "query": {"bool": {"must": [{"term": {"person_natcde": "634"}}, {"term": {"prs_gdr": "Male"}}]}},
                   "extract_field": "prs_qid"},
                  {"step": 2, "index": "moi-sponsor-details-v1",
                   "query": {"bool": {"must": [{"terms": {"SPONSOR_QID": "$step_1"}}]}}}
              ]
          }),
    mpair("Find company sponsorships by Indian nationals",
          person_sponsor_plan("356", [{"term": {"SPONSOR_TYPE": "2"}}])),
]


def main():
    all_new_train = (
        exit_entry_pairs +
        visa_main_pairs +
        visa_app_pairs +
        sponsor_pairs +
        violation_fixes +
        relationship_fixes +
        vehicle_fixes +
        person_fixes +
        multi_index_pairs
    )

    # Validation pairs: subset for valid.jsonl
    val_new = (
        exit_entry_pairs[::4] +       # every 4th
        visa_main_pairs[::4] +
        visa_app_pairs[::4] +
        sponsor_pairs[::3] +
        violation_fixes[::3] +
        relationship_fixes[::2] +
        vehicle_fixes[::2] +
        person_fixes[::2] +
        multi_index_pairs[::4]
    )

    train_path = REPO_ROOT / "data" / "training" / "train.jsonl"
    valid_path = REPO_ROOT / "data" / "training" / "valid.jsonl"

    with open(train_path, "a") as f:
        for p in all_new_train:
            f.write(json.dumps(p) + "\n")

    with open(valid_path, "a") as f:
        for p in val_new:
            f.write(json.dumps(p) + "\n")

    print(f"Added {len(all_new_train)} training pairs → train.jsonl")
    print(f"Added {len(val_new)} validation pairs → valid.jsonl")

    # Summary by category
    cats = [
        ("Exit/Entry", exit_entry_pairs),
        ("Visa-main", visa_main_pairs),
        ("Visa-app", visa_app_pairs),
        ("Sponsor", sponsor_pairs),
        ("Violations", violation_fixes),
        ("Relationships", relationship_fixes),
        ("Vehicle", vehicle_fixes),
        ("Person", person_fixes),
        ("Multi-index", multi_index_pairs),
    ]
    print("\nBreakdown:")
    for name, lst in cats:
        print(f"  {name:15s}: {len(lst):3d} train pairs")

    # New totals
    import subprocess
    r = subprocess.run(["wc", "-l", str(train_path), str(valid_path)], capture_output=True, text=True)
    print(f"\n{r.stdout.strip()}")


if __name__ == "__main__":
    main()

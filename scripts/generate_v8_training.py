#!/usr/bin/env python3
"""
Generate targeted training pairs for v8 adapter.

Fixes identified from evaluate_v3.py v7 evaluation (69.8% → target 80%+):

REGRESSIONS (caused by v7 training):
1. Violations — model adds spurious VLN_STATUS:UNPAID to simple type queries (N01,N13).
   Model puts road name in VLN_TYPE instead of VLN_PLCDSC (N03, N14).
   Model misses VLN_YEAR for year-filtered queries (N16).

2. Person — P04: adds prs_clre filter. P11: wrong field + wrong OR structure.
   P15: uses must (impossible same-field AND) instead of should for nationality OR.

3. Vehicle — V04: range on VRG_STATUS instead of match. V06: missing make filter.
   V09: missing VEH_MODEL:CAMRY filter.

PERSISTENT FAILURES:
4. Exit/Entry — E01 adds spurious TRX_STATUS. E03 adds direction to "all flights".
   E04 uses BORDER_CODE_DESC for "land" instead of TRX_TRIP_TYP_DESC.
   E08 uses prs_dttm instead of TRX_DATE. E11 goes multi-index.

5. Visa-main — VSA_TYPCDE codes still not learned (40=work, 20=residence, 11=visit).
   VSA_RCDSTS codes (13=active, 14=expired). NAT_CDENUM for nationality.
   Nationality+visa queries must be SINGLE INDEX (not multi-index join).

6. Visa-app — VA03: uses VISA_TYPE_DESC instead of APL_TYPCDE:"40".
   VA04: ranges on APL_RCDSTS instead of using APL_APLDTE for date.

7. Sponsor — SP06: generates invalid DSL instead of match MDS_DPTENGNAM.

8. Relationships — RL01: generates VISA_TYPE_DESC query instead of match_all.
   RL03: must_not exists DIVORCE_DATE still failing.

MULTI-INDEX specific bugs:
9. M02: step 2 adds spurious VLN_STATUS:UNPAID.
   M03: step 2 adds spurious VRG_STATUS filter (all vehicles = no filter).
   M11: wrong vehicle make field (VRG_MADT vs MNF_ENSHDESC); missing gender in step 1.
   M16: puts violation filter in step 1 person query; wrong join field VLN_QID vs VLN_OWNQID.
   M21: adds spurious gender in step 1; wrong join field TRX_QID vs TRX_QIDNO;
        missing BORDER_CODE_DESC filter in step 2.
   M26: match instead of term on VSA_TYPCDE; missing VSA_RCDSTS:13 active filter.
   M35: VLN_TYPE:"SUSPICIOUS ACT" instead of VLN_PLCDSC:"CORNICHE ROAD".
"""

import json
import random
from pathlib import Path

REPO_ROOT = Path(__file__).parent.parent
TRAIN_PATH = REPO_ROOT / "data" / "training" / "train.jsonl"
VALID_PATH = REPO_ROOT / "data" / "training" / "valid.jsonl"


def pair(user, assistant):
    return {"messages": [
        {"role": "user", "content": user},
        {"role": "assistant", "content": json.dumps(assistant, separators=(',', ':'))},
    ]}


def single(index, query_body):
    return {"query": query_body}


# ─────────────────────────────────────────────────────────────
# 1. VIOLATIONS — fix spurious UNPAID filter + VLN_PLCDSC field
# ─────────────────────────────────────────────────────────────
violations_pairs = [
    # Simple type queries — NO status filter
    pair("Find all speeding violations",
         single("moi-violations-v1", {"term": {"VLN_TYPE": "SPEEDING"}})),
    pair("Show me all speeding violations",
         single("moi-violations-v1", {"term": {"VLN_TYPE": "SPEEDING"}})),
    pair("List all speeding violations",
         single("moi-violations-v1", {"term": {"VLN_TYPE": "SPEEDING"}})),
    pair("Find all parking violations",
         single("moi-violations-v1", {"term": {"VLN_TYPE": "PARKING"}})),
    pair("Show all parking violations",
         single("moi-violations-v1", {"term": {"VLN_TYPE": "PARKING"}})),
    pair("List parking violations",
         single("moi-violations-v1", {"term": {"VLN_TYPE": "PARKING"}})),
    pair("Find all red light violations",
         single("moi-violations-v1", {"term": {"VLN_TYPE": "RED_LIGHT"}})),
    pair("Show all mobile phone violations",
         single("moi-violations-v1", {"term": {"VLN_TYPE": "MOBILE_PHONE"}})),

    # Road / location field = VLN_PLCDSC (not VLN_TYPE)
    pair("Find violations on Corniche Road",
         single("moi-violations-v1", {"term": {"VLN_PLCDSC": "CORNICHE ROAD"}})),
    pair("Show violations that happened on Corniche Road",
         single("moi-violations-v1", {"term": {"VLN_PLCDSC": "CORNICHE ROAD"}})),
    pair("Show violations on Salwa Road",
         single("moi-violations-v1", {"term": {"VLN_PLCDSC": "SALWA ROAD"}})),
    pair("Find violations that occurred on Salwa Road",
         single("moi-violations-v1", {"term": {"VLN_PLCDSC": "SALWA ROAD"}})),
    pair("Show violations on Al Waab Street",
         single("moi-violations-v1", {"term": {"VLN_PLCDSC": "AL WAAB STREET"}})),
    pair("Find violations on Al Rayyan Road",
         single("moi-violations-v1", {"term": {"VLN_PLCDSC": "AL RAYYAN ROAD"}})),

    # Combined type + location (no spurious status)
    pair("Find speeding violations on Corniche Road",
         single("moi-violations-v1", {"bool": {"must": [
             {"term": {"VLN_TYPE": "SPEEDING"}},
             {"term": {"VLN_PLCDSC": "CORNICHE ROAD"}},
         ]}})),
    pair("Show parking violations on Al Waab Street",
         single("moi-violations-v1", {"bool": {"must": [
             {"term": {"VLN_TYPE": "PARKING"}},
             {"term": {"VLN_PLCDSC": "AL WAAB STREET"}},
         ]}})),

    # Year filter uses VLN_YEAR (not range on a date field)
    pair("Show paid speeding violations from 2023",
         single("moi-violations-v1", {"bool": {"must": [
             {"term": {"VLN_TYPE": "SPEEDING"}},
             {"term": {"VLN_STATUS": "PAID"}},
             {"term": {"VLN_YEAR": "2023"}},
         ]}})),
    pair("Find unpaid violations from 2024",
         single("moi-violations-v1", {"bool": {"must": [
             {"term": {"VLN_STATUS": "UNPAID"}},
             {"term": {"VLN_YEAR": "2024"}},
         ]}})),
    pair("Show speeding violations from 2022",
         single("moi-violations-v1", {"bool": {"must": [
             {"term": {"VLN_TYPE": "SPEEDING"}},
             {"term": {"VLN_YEAR": "2022"}},
         ]}})),
    pair("Find all violations from 2023",
         single("moi-violations-v1", {"term": {"VLN_YEAR": "2023"}})),
]

# ─────────────────────────────────────────────────────────────
# 2. PERSON — fix extra filters + OR structure
# ─────────────────────────────────────────────────────────────
person_pairs = [
    # P04: plain gender query — no extra fields
    pair("Show all male persons",
         single("moi-gp-all-profiles-details-v1", {"term": {"prs_gdr": "Male"}})),
    pair("Find all male persons",
         single("moi-gp-all-profiles-details-v1", {"term": {"prs_gdr": "Male"}})),
    pair("List all males",
         single("moi-gp-all-profiles-details-v1", {"term": {"prs_gdr": "Male"}})),
    pair("Show all female persons",
         single("moi-gp-all-profiles-details-v1", {"term": {"prs_gdr": "Female"}})),

    # P11: nationality OR + gender — must wrap should inside must
    pair("Find persons from India or Pakistan who are male",
         single("moi-gp-all-profiles-details-v1", {"bool": {"must": [
             {"term": {"prs_gdr": "Male"}},
             {"bool": {"should": [
                 {"term": {"person_natcde": "Indian"}},
                 {"term": {"person_natcde": "Pakistani"}},
             ]}},
         ]}})),
    pair("Show female persons from Egypt or Jordan",
         single("moi-gp-all-profiles-details-v1", {"bool": {"must": [
             {"term": {"prs_gdr": "Female"}},
             {"bool": {"should": [
                 {"term": {"person_natcde": "Egyptian"}},
                 {"term": {"person_natcde": "Jordanian"}},
             ]}},
         ]}})),
    pair("Find males from Qatar or UAE",
         single("moi-gp-all-profiles-details-v1", {"bool": {"must": [
             {"term": {"prs_gdr": "Male"}},
             {"bool": {"should": [
                 {"term": {"person_natcde": "Qatari"}},
                 {"term": {"person_natcde": "Emirati"}},
             ]}},
         ]}})),

    # P15: nationality OR query — use should at top level
    pair("Find all Nepali or Sri Lankan nationals",
         single("moi-gp-all-profiles-details-v1", {"bool": {"should": [
             {"term": {"person_natcde": "Nepali"}},
             {"term": {"person_natcde": "Sri Lankan"}},
         ]}})),
    pair("Find all Indian or Pakistani nationals",
         single("moi-gp-all-profiles-details-v1", {"bool": {"should": [
             {"term": {"person_natcde": "Indian"}},
             {"term": {"person_natcde": "Pakistani"}},
         ]}})),
    pair("Show Egyptian or Jordanian nationals",
         single("moi-gp-all-profiles-details-v1", {"bool": {"should": [
             {"term": {"person_natcde": "Egyptian"}},
             {"term": {"person_natcde": "Jordanian"}},
         ]}})),
    pair("Find Qatari or Emirati nationals",
         single("moi-gp-all-profiles-details-v1", {"bool": {"should": [
             {"term": {"person_natcde": "Qatari"}},
             {"term": {"person_natcde": "Emirati"}},
         ]}})),
]

# ─────────────────────────────────────────────────────────────
# 3. VEHICLE — fix VRG_STATUS match + compound queries
# ─────────────────────────────────────────────────────────────
vehicle_pairs = [
    # V04: VRG_STATUS is text — use match, not range or term
    pair("Show all vehicles with active registration",
         single("moi-vehicle-info-v1", {"match": {"VRG_STATUS": "ACT"}})),
    pair("Find vehicles that have active registration",
         single("moi-vehicle-info-v1", {"match": {"VRG_STATUS": "ACT"}})),
    pair("Find vehicles with expired registration",
         single("moi-vehicle-info-v1", {"match": {"VRG_STATUS": "EXP"}})),

    # V06: must include BOTH make filter AND date range
    pair("Show Toyota vehicles registered in 2022",
         single("moi-vehicle-info-v1", {"bool": {"must": [
             {"match": {"MNF_ENSHDESC": "TOYOTA"}},
             {"range": {"VRG_STADTE": {"gte": "2022-01-01", "lte": "2022-12-31"}}},
         ]}})),
    pair("Find Nissan vehicles registered in 2021",
         single("moi-vehicle-info-v1", {"bool": {"must": [
             {"match": {"MNF_ENSHDESC": "NISSAN"}},
             {"range": {"VRG_STADTE": {"gte": "2021-01-01", "lte": "2021-12-31"}}},
         ]}})),
    pair("Show Toyota vehicles registered in 2023",
         single("moi-vehicle-info-v1", {"bool": {"must": [
             {"match": {"MNF_ENSHDESC": "TOYOTA"}},
             {"range": {"VRG_STADTE": {"gte": "2023-01-01", "lte": "2023-12-31"}}},
         ]}})),

    # V09: must include VEH_MODEL for model filter
    pair("Find white Toyota Camry vehicles registered between 2020 and 2023",
         single("moi-vehicle-info-v1", {"bool": {"must": [
             {"match": {"MNF_ENSHDESC": "TOYOTA"}},
             {"match": {"CLR_CLRENGDSC": "WHITE"}},
             {"match": {"VEH_MODEL": "CAMRY"}},
             {"range": {"VRG_STADTE": {"gte": "2020-01-01", "lte": "2023-12-31"}}},
         ]}})),
    pair("Find silver Nissan Patrol vehicles",
         single("moi-vehicle-info-v1", {"bool": {"must": [
             {"match": {"MNF_ENSHDESC": "NISSAN"}},
             {"match": {"CLR_CLRENGDSC": "SILVER"}},
             {"match": {"VEH_MODEL": "PATROL"}},
         ]}})),
    pair("Show black Toyota Camry vehicles",
         single("moi-vehicle-info-v1", {"bool": {"must": [
             {"match": {"MNF_ENSHDESC": "TOYOTA"}},
             {"match": {"CLR_CLRENGDSC": "BLACK"}},
             {"match": {"VEH_MODEL": "CAMRY"}},
         ]}})),
]

# ─────────────────────────────────────────────────────────────
# 4. EXIT/ENTRY — fix all remaining patterns
# ─────────────────────────────────────────────────────────────
exit_entry_pairs = [
    # E01: plain exit = just match TRX_DIRECTION OUT, no TRX_STATUS
    pair("Find all exit transactions",
         single("moi-exit-entry-tts-details-v1", {"match": {"TRX_DIRECTION": "OUT"}})),
    pair("Show all exits",
         single("moi-exit-entry-tts-details-v1", {"match": {"TRX_DIRECTION": "OUT"}})),
    pair("List all exit records",
         single("moi-exit-entry-tts-details-v1", {"match": {"TRX_DIRECTION": "OUT"}})),
    pair("Find all entry transactions",
         single("moi-exit-entry-tts-details-v1", {"match": {"TRX_DIRECTION": "IN"}})),

    # E03: "all flights through airport" = no direction filter, match TRX_TRIP_TYP_DESC + BORDER_CODE_DESC
    pair("Find all flights through Hamad International Airport",
         single("moi-exit-entry-tts-details-v1", {"bool": {"must": [
             {"match": {"TRX_TRIP_TYP_DESC": "FLIGHT"}},
             {"match": {"BORDER_CODE_DESC": "HAMAD INTERNATIONAL AIRPORT"}},
         ]}})),
    pair("Show all transactions through Hamad International Airport",
         single("moi-exit-entry-tts-details-v1",
                {"match": {"BORDER_CODE_DESC": "HAMAD INTERNATIONAL AIRPORT"}})),
    pair("Find all air travel transactions at Hamad Airport",
         single("moi-exit-entry-tts-details-v1", {"bool": {"must": [
             {"match": {"TRX_TRIP_TYP_DESC": "FLIGHT"}},
             {"match": {"BORDER_CODE_DESC": "HAMAD INTERNATIONAL AIRPORT"}},
         ]}})),

    # E04: "land border crossings" = TRX_TRIP_TYP_DESC = "LAND" (not BORDER_CODE_DESC)
    pair("Show all land border crossings",
         single("moi-exit-entry-tts-details-v1", {"match": {"TRX_TRIP_TYP_DESC": "LAND"}})),
    pair("Find all land crossings",
         single("moi-exit-entry-tts-details-v1", {"match": {"TRX_TRIP_TYP_DESC": "LAND"}})),
    pair("Show all road border crossings",
         single("moi-exit-entry-tts-details-v1", {"match": {"TRX_TRIP_TYP_DESC": "LAND"}})),

    # E08: date field is TRX_DATE (not prs_dttm)
    pair("Show all flight entries in 2023",
         single("moi-exit-entry-tts-details-v1", {"bool": {"must": [
             {"match": {"TRX_DIRECTION": "IN"}},
             {"match": {"TRX_TRIP_TYP_DESC": "FLIGHT"}},
             {"range": {"TRX_DATE": {"gte": "2023-01-01", "lte": "2023-12-31"}}},
         ]}})),
    pair("Find all flight exits in 2022",
         single("moi-exit-entry-tts-details-v1", {"bool": {"must": [
             {"match": {"TRX_DIRECTION": "OUT"}},
             {"match": {"TRX_TRIP_TYP_DESC": "FLIGHT"}},
             {"range": {"TRX_DATE": {"gte": "2022-01-01", "lte": "2022-12-31"}}},
         ]}})),
    pair("Show all travel transactions in 2023",
         single("moi-exit-entry-tts-details-v1",
                {"range": {"TRX_DATE": {"gte": "2023-01-01", "lte": "2023-12-31"}}})),
    pair("Find transactions from January 2024",
         single("moi-exit-entry-tts-details-v1",
                {"range": {"TRX_DATE": {"gte": "2024-01-01", "lte": "2024-01-31"}}})),

    # E11: sea arrivals = single-index, match BORDER_CODE_DESC not multi-index
    pair("Find all sea arrivals to Doha Port",
         single("moi-exit-entry-tts-details-v1", {"bool": {"must": [
             {"match": {"TRX_DIRECTION": "IN"}},
             {"match": {"BORDER_CODE_DESC": "DOHA PORT"}},
         ]}})),
    pair("Show all entries via Doha Port",
         single("moi-exit-entry-tts-details-v1", {"bool": {"must": [
             {"match": {"TRX_DIRECTION": "IN"}},
             {"match": {"BORDER_CODE_DESC": "DOHA PORT"}},
         ]}})),
    pair("Find all sea travel transactions",
         single("moi-exit-entry-tts-details-v1", {"match": {"TRX_TRIP_TYP_DESC": "SEA"}})),
    pair("Show all transactions at Abu Samra border",
         single("moi-exit-entry-tts-details-v1",
                {"match": {"BORDER_CODE_DESC": "ABU SAMRA"}})),
]

# ─────────────────────────────────────────────────────────────
# 5. VISA-MAIN — heavy reinforcement of VSA_TYPCDE codes
#    ALL nationality+visa queries are SINGLE INDEX (NAT_CDENUM field on visa record)
# ─────────────────────────────────────────────────────────────
visa_main_pairs = [
    # Type codes: 40=Work Visa, 20=Residence Permit, 11=Visit Visa
    # Status codes: 13=Active, 14=Expired
    # Date field: VSA_EXPDTE (expiry), VSA_ISSDTE (issue)

    # Simple type queries using VSA_TYPCDE (term, keyword field)
    pair("Find all work visas",
         single("moi-visa-main-details-v1", {"term": {"VSA_TYPCDE": "40"}})),
    pair("Show all work visas",
         single("moi-visa-main-details-v1", {"term": {"VSA_TYPCDE": "40"}})),
    pair("List work visas",
         single("moi-visa-main-details-v1", {"term": {"VSA_TYPCDE": "40"}})),
    pair("Find all residence permits",
         single("moi-visa-main-details-v1", {"term": {"VSA_TYPCDE": "20"}})),
    pair("Show all residence permits",
         single("moi-visa-main-details-v1", {"term": {"VSA_TYPCDE": "20"}})),
    pair("Find all visit visas",
         single("moi-visa-main-details-v1", {"term": {"VSA_TYPCDE": "11"}})),
    pair("Show all visit visas",
         single("moi-visa-main-details-v1", {"term": {"VSA_TYPCDE": "11"}})),
    pair("List visit visas",
         single("moi-visa-main-details-v1", {"term": {"VSA_TYPCDE": "11"}})),

    # Status queries using VSA_RCDSTS (term, keyword field)
    pair("Show all active visas",
         single("moi-visa-main-details-v1", {"term": {"VSA_RCDSTS": "13"}})),
    pair("Find all active visas",
         single("moi-visa-main-details-v1", {"term": {"VSA_RCDSTS": "13"}})),
    pair("Find all expired visas",
         single("moi-visa-main-details-v1", {"term": {"VSA_RCDSTS": "14"}})),
    pair("Show all expired visas",
         single("moi-visa-main-details-v1", {"term": {"VSA_RCDSTS": "14"}})),

    # Combined type + status
    pair("Show all active work visas",
         single("moi-visa-main-details-v1", {"bool": {"must": [
             {"term": {"VSA_TYPCDE": "40"}},
             {"term": {"VSA_RCDSTS": "13"}},
         ]}})),
    pair("Find active work visas",
         single("moi-visa-main-details-v1", {"bool": {"must": [
             {"term": {"VSA_TYPCDE": "40"}},
             {"term": {"VSA_RCDSTS": "13"}},
         ]}})),
    pair("Find expired work visas",
         single("moi-visa-main-details-v1", {"bool": {"must": [
             {"term": {"VSA_TYPCDE": "40"}},
             {"term": {"VSA_RCDSTS": "14"}},
         ]}})),
    pair("Show expired residence permits",
         single("moi-visa-main-details-v1", {"bool": {"must": [
             {"term": {"VSA_TYPCDE": "20"}},
             {"term": {"VSA_RCDSTS": "14"}},
         ]}})),
    pair("Find active residence permits",
         single("moi-visa-main-details-v1", {"bool": {"must": [
             {"term": {"VSA_TYPCDE": "20"}},
             {"term": {"VSA_RCDSTS": "13"}},
         ]}})),

    # Date range queries — VSA_EXPDTE for expiry, VSA_ISSDTE for issue
    pair("Find work visas expiring before 2026",
         single("moi-visa-main-details-v1", {"bool": {"must": [
             {"term": {"VSA_TYPCDE": "40"}},
             {"range": {"VSA_EXPDTE": {"lt": "2026-01-01"}}},
         ]}})),
    pair("Show work visas expiring in 2025",
         single("moi-visa-main-details-v1", {"bool": {"must": [
             {"term": {"VSA_TYPCDE": "40"}},
             {"range": {"VSA_EXPDTE": {"gte": "2025-01-01", "lte": "2025-12-31"}}},
         ]}})),
    pair("Find visas issued in 2022",
         single("moi-visa-main-details-v1",
                {"range": {"VSA_ISSDTE": {"gte": "2022-01-01", "lte": "2022-12-31"}}})),
    pair("Show all visas issued in 2023",
         single("moi-visa-main-details-v1",
                {"range": {"VSA_ISSDTE": {"gte": "2023-01-01", "lte": "2023-12-31"}}})),

    # Nationality queries — SINGLE INDEX using NAT_CDENUM (term, keyword field)
    # The transformer converts nationality name → code, written to NAT_CDENUM
    pair("Show work visas for Pakistani nationals",
         single("moi-visa-main-details-v1", {"bool": {"must": [
             {"term": {"VSA_TYPCDE": "40"}},
             {"term": {"NAT_CDENUM": "Pakistani"}},
         ]}})),
    pair("Find residence permits for Qatari nationals",
         single("moi-visa-main-details-v1", {"bool": {"must": [
             {"term": {"VSA_TYPCDE": "20"}},
             {"term": {"NAT_CDENUM": "Qatari"}},
         ]}})),
    pair("Find active work visas for Pakistani nationals",
         single("moi-visa-main-details-v1", {"bool": {"must": [
             {"term": {"VSA_TYPCDE": "40"}},
             {"term": {"VSA_RCDSTS": "13"}},
             {"term": {"NAT_CDENUM": "Pakistani"}},
         ]}})),
    pair("Show expired work visas for Pakistani nationals",
         single("moi-visa-main-details-v1", {"bool": {"must": [
             {"term": {"VSA_TYPCDE": "40"}},
             {"term": {"VSA_RCDSTS": "14"}},
             {"term": {"NAT_CDENUM": "Pakistani"}},
         ]}})),
    pair("Find work visas for Indian nationals",
         single("moi-visa-main-details-v1", {"bool": {"must": [
             {"term": {"VSA_TYPCDE": "40"}},
             {"term": {"NAT_CDENUM": "Indian"}},
         ]}})),
    pair("Show visit visas for Egyptian nationals",
         single("moi-visa-main-details-v1", {"bool": {"must": [
             {"term": {"VSA_TYPCDE": "11"}},
             {"term": {"NAT_CDENUM": "Egyptian"}},
         ]}})),
    pair("Find active residence permits for Indian nationals",
         single("moi-visa-main-details-v1", {"bool": {"must": [
             {"term": {"VSA_TYPCDE": "20"}},
             {"term": {"VSA_RCDSTS": "13"}},
             {"term": {"NAT_CDENUM": "Indian"}},
         ]}})),
    pair("Show all visas for Nepali nationals",
         single("moi-visa-main-details-v1", {"term": {"NAT_CDENUM": "Nepali"}})),
    pair("Find all visas held by Bangladeshi nationals",
         single("moi-visa-main-details-v1", {"term": {"NAT_CDENUM": "Bangladeshi"}})),
]

# ─────────────────────────────────────────────────────────────
# 6. VISA-APP — fix type code + date field
# ─────────────────────────────────────────────────────────────
visa_app_pairs = [
    # APL_TYPCDE: "40"=work, "20"=residence, "11"=visit (same codes as visa-main)
    pair("Find all work visa applications",
         single("moi-visa-application-v1", {"term": {"APL_TYPCDE": "40"}})),
    pair("Show all work visa applications",
         single("moi-visa-application-v1", {"term": {"APL_TYPCDE": "40"}})),
    pair("List work visa applications",
         single("moi-visa-application-v1", {"term": {"APL_TYPCDE": "40"}})),
    pair("Find all residence permit applications",
         single("moi-visa-application-v1", {"term": {"APL_TYPCDE": "20"}})),
    pair("Find all visit visa applications",
         single("moi-visa-application-v1", {"term": {"APL_TYPCDE": "11"}})),

    # APL_RCDSTS: "2"=approved, "3"=rejected; APL_APLDTE = submission date
    pair("Show approved applications submitted in 2023",
         single("moi-visa-application-v1", {"bool": {"must": [
             {"term": {"APL_RCDSTS": "2"}},
             {"range": {"APL_APLDTE": {"gte": "2023-01-01", "lte": "2023-12-31"}}},
         ]}})),
    pair("Find approved applications submitted in 2022",
         single("moi-visa-application-v1", {"bool": {"must": [
             {"term": {"APL_RCDSTS": "2"}},
             {"range": {"APL_APLDTE": {"gte": "2022-01-01", "lte": "2022-12-31"}}},
         ]}})),
    pair("Show rejected applications from 2023",
         single("moi-visa-application-v1", {"bool": {"must": [
             {"term": {"APL_RCDSTS": "3"}},
             {"range": {"APL_APLDTE": {"gte": "2023-01-01", "lte": "2023-12-31"}}},
         ]}})),
    pair("Find approved work visa applications submitted in 2023",
         single("moi-visa-application-v1", {"bool": {"must": [
             {"term": {"APL_TYPCDE": "40"}},
             {"term": {"APL_RCDSTS": "2"}},
             {"range": {"APL_APLDTE": {"gte": "2023-01-01", "lte": "2023-12-31"}}},
         ]}})),
]

# ─────────────────────────────────────────────────────────────
# 7. SPONSOR — fix SP06 MDS_DPTENGNAM
# ─────────────────────────────────────────────────────────────
sponsor_pairs = [
    pair("Show all sponsorships for Expatriates Affairs Dept",
         single("moi-sponsor-details-v1", {"match": {"MDS_DPTENGNAM": "Expatriates Affairs Dept"}})),
    pair("Find sponsorships from Expatriates Affairs Department",
         single("moi-sponsor-details-v1", {"match": {"MDS_DPTENGNAM": "Expatriates Affairs Dept"}})),
    pair("Show sponsorships from the Ministry of Interior",
         single("moi-sponsor-details-v1", {"match": {"MDS_DPTENGNAM": "Ministry of Interior"}})),
    pair("Find all company sponsorships",
         single("moi-sponsor-details-v1", {"term": {"SPONSOR_TYPE": "2"}})),
    pair("Show all individual sponsorships",
         single("moi-sponsor-details-v1", {"term": {"SPONSOR_TYPE": "1"}})),
]

# ─────────────────────────────────────────────────────────────
# 8. RELATIONSHIPS — fix RL01 match_all + RL03 must_not exists
# ─────────────────────────────────────────────────────────────
relationship_pairs = [
    # RL01: "all marriage records" = match_all (all docs in relationships index ARE marriage records)
    pair("Find all marriage records",
         single("moi-relationship-details-v1", {"match_all": {}})),
    pair("Show all marriage records",
         single("moi-relationship-details-v1", {"match_all": {}})),
    pair("List all marriages",
         single("moi-relationship-details-v1", {"match_all": {}})),
    pair("Show all relationships",
         single("moi-relationship-details-v1", {"match_all": {}})),

    # RL03: "no divorce" = must_not exists on DIVORCE_DATE
    pair("Find all current marriages with no divorce",
         single("moi-relationship-details-v1", {"bool": {"must_not": {"exists": {"field": "DIVORCE_DATE"}}}})),
    pair("Show marriages that have not ended in divorce",
         single("moi-relationship-details-v1", {"bool": {"must_not": {"exists": {"field": "DIVORCE_DATE"}}}})),
    pair("Find marriages with no divorce record",
         single("moi-relationship-details-v1", {"bool": {"must_not": {"exists": {"field": "DIVORCE_DATE"}}}})),
    pair("Show active marriages without divorce",
         single("moi-relationship-details-v1", {"bool": {"must_not": {"exists": {"field": "DIVORCE_DATE"}}}})),

    # RL05 reinforcement: "ended in divorce" = exists DIVORCE_DATE
    pair("Find marriages that ended in divorce",
         single("moi-relationship-details-v1", {"bool": {"must": [{"exists": {"field": "DIVORCE_DATE"}}]}})),
]

# ─────────────────────────────────────────────────────────────
# 9. MULTI-INDEX — fix all 7 specific failures
# ─────────────────────────────────────────────────────────────
multi_pairs = [
    # M02: Pakistani violations — step 2 must NOT add VLN_STATUS filter
    pair("Find all violations for Pakistani nationals",
         {"type": "multi_index", "steps": [
             {"step": 1, "index": "moi-gp-all-profiles-details-v1",
              "query": {"term": {"person_natcde": "Pakistani"}},
              "extract_field": "prs_qid"},
             {"step": 2, "index": "moi-violations-v1",
              "query": {"bool": {"must": [{"terms": {"VLN_OWNQID": "$step_1"}}]}}},
         ]}),
    pair("Show all violations for Pakistani nationals",
         {"type": "multi_index", "steps": [
             {"step": 1, "index": "moi-gp-all-profiles-details-v1",
              "query": {"term": {"person_natcde": "Pakistani"}},
              "extract_field": "prs_qid"},
             {"step": 2, "index": "moi-violations-v1",
              "query": {"bool": {"must": [{"terms": {"VLN_OWNQID": "$step_1"}}]}}},
         ]}),
    pair("Find all violations for Egyptian nationals",
         {"type": "multi_index", "steps": [
             {"step": 1, "index": "moi-gp-all-profiles-details-v1",
              "query": {"term": {"person_natcde": "Egyptian"}},
              "extract_field": "prs_qid"},
             {"step": 2, "index": "moi-violations-v1",
              "query": {"bool": {"must": [{"terms": {"VLN_OWNQID": "$step_1"}}]}}},
         ]}),

    # M03: Qatari vehicles — step 2 must NOT add any VRG_STATUS filter
    pair("Find all vehicles owned by Qatari nationals",
         {"type": "multi_index", "steps": [
             {"step": 1, "index": "moi-gp-all-profiles-details-v1",
              "query": {"term": {"person_natcde": "Qatari"}},
              "extract_field": "prs_qid"},
             {"step": 2, "index": "moi-vehicle-info-v1",
              "query": {"bool": {"must": [{"terms": {"VRG_OWNQID": "$step_1"}}]}}},
         ]}),
    pair("Show all vehicles owned by Pakistani nationals",
         {"type": "multi_index", "steps": [
             {"step": 1, "index": "moi-gp-all-profiles-details-v1",
              "query": {"term": {"person_natcde": "Pakistani"}},
              "extract_field": "prs_qid"},
             {"step": 2, "index": "moi-vehicle-info-v1",
              "query": {"bool": {"must": [{"terms": {"VRG_OWNQID": "$step_1"}}]}}},
         ]}),

    # M11: Toyota vehicles by Pakistani males — step 1 must filter gender;
    #       step 2 uses MNF_ENSHDESC (not VRG_MADT)
    pair("Find Toyota vehicles owned by Pakistani males",
         {"type": "multi_index", "steps": [
             {"step": 1, "index": "moi-gp-all-profiles-details-v1",
              "query": {"bool": {"must": [
                  {"term": {"person_natcde": "Pakistani"}},
                  {"term": {"prs_gdr": "Male"}},
              ]}},
              "extract_field": "prs_qid"},
             {"step": 2, "index": "moi-vehicle-info-v1",
              "query": {"bool": {"must": [
                  {"terms": {"VRG_OWNQID": "$step_1"}},
                  {"match": {"MNF_ENSHDESC": "TOYOTA"}},
              ]}}},
         ]}),
    pair("Show Toyota vehicles owned by Indian males",
         {"type": "multi_index", "steps": [
             {"step": 1, "index": "moi-gp-all-profiles-details-v1",
              "query": {"bool": {"must": [
                  {"term": {"person_natcde": "Indian"}},
                  {"term": {"prs_gdr": "Male"}},
              ]}},
              "extract_field": "prs_qid"},
             {"step": 2, "index": "moi-vehicle-info-v1",
              "query": {"bool": {"must": [
                  {"terms": {"VRG_OWNQID": "$step_1"}},
                  {"match": {"MNF_ENSHDESC": "TOYOTA"}},
              ]}}},
         ]}),

    # M16: Egyptian unpaid violations — step 1 person only; step 2 has VLN_STATUS;
    #       join field is VLN_OWNQID (not VLN_QID)
    pair("Find unpaid violations for Egyptian nationals",
         {"type": "multi_index", "steps": [
             {"step": 1, "index": "moi-gp-all-profiles-details-v1",
              "query": {"term": {"person_natcde": "Egyptian"}},
              "extract_field": "prs_qid"},
             {"step": 2, "index": "moi-violations-v1",
              "query": {"bool": {"must": [
                  {"terms": {"VLN_OWNQID": "$step_1"}},
                  {"term": {"VLN_STATUS": "UNPAID"}},
              ]}}},
         ]}),
    pair("Find paid violations for Egyptian nationals",
         {"type": "multi_index", "steps": [
             {"step": 1, "index": "moi-gp-all-profiles-details-v1",
              "query": {"term": {"person_natcde": "Egyptian"}},
              "extract_field": "prs_qid"},
             {"step": 2, "index": "moi-violations-v1",
              "query": {"bool": {"must": [
                  {"terms": {"VLN_OWNQID": "$step_1"}},
                  {"term": {"VLN_STATUS": "PAID"}},
              ]}}},
         ]}),

    # M21: Pakistani entries via Hamad — step 1 person only (no gender);
    #       step 2 uses TRX_QIDNO (not TRX_QID) + correct filters
    pair("Find entries via Hamad Airport for Pakistani nationals",
         {"type": "multi_index", "steps": [
             {"step": 1, "index": "moi-gp-all-profiles-details-v1",
              "query": {"term": {"person_natcde": "Pakistani"}},
              "extract_field": "prs_qid"},
             {"step": 2, "index": "moi-exit-entry-tts-details-v1",
              "query": {"bool": {"must": [
                  {"terms": {"TRX_QIDNO": "$step_1"}},
                  {"match": {"TRX_DIRECTION": "IN"}},
                  {"match": {"TRX_TRIP_TYP_DESC": "FLIGHT"}},
                  {"match": {"BORDER_CODE_DESC": "HAMAD INTERNATIONAL AIRPORT"}},
              ]}}},
         ]}),
    pair("Find exits via Hamad Airport for Indian nationals",
         {"type": "multi_index", "steps": [
             {"step": 1, "index": "moi-gp-all-profiles-details-v1",
              "query": {"term": {"person_natcde": "Indian"}},
              "extract_field": "prs_qid"},
             {"step": 2, "index": "moi-exit-entry-tts-details-v1",
              "query": {"bool": {"must": [
                  {"terms": {"TRX_QIDNO": "$step_1"}},
                  {"match": {"TRX_DIRECTION": "OUT"}},
                  {"match": {"TRX_TRIP_TYP_DESC": "FLIGHT"}},
                  {"match": {"BORDER_CODE_DESC": "HAMAD INTERNATIONAL AIRPORT"}},
              ]}}},
         ]}),
    pair("Find land entries for Qatari nationals",
         {"type": "multi_index", "steps": [
             {"step": 1, "index": "moi-gp-all-profiles-details-v1",
              "query": {"term": {"person_natcde": "Qatari"}},
              "extract_field": "prs_qid"},
             {"step": 2, "index": "moi-exit-entry-tts-details-v1",
              "query": {"bool": {"must": [
                  {"terms": {"TRX_QIDNO": "$step_1"}},
                  {"match": {"TRX_DIRECTION": "IN"}},
                  {"match": {"TRX_TRIP_TYP_DESC": "LAND"}},
              ]}}},
         ]}),

    # M26: Active work visas for Pakistani — step 2 must use term (not match) for codes
    #       AND include VSA_RCDSTS:13 for active filter
    pair("Find active work visas held by Pakistani nationals",
         {"type": "multi_index", "steps": [
             {"step": 1, "index": "moi-gp-all-profiles-details-v1",
              "query": {"term": {"person_natcde": "Pakistani"}},
              "extract_field": "prs_qid"},
             {"step": 2, "index": "moi-visa-main-details-v1",
              "query": {"bool": {"must": [
                  {"terms": {"HLD_QIDNO": "$step_1"}},
                  {"term": {"VSA_TYPCDE": "40"}},
                  {"term": {"VSA_RCDSTS": "13"}},
              ]}}},
         ]}),
    pair("Find expired work visas held by Pakistani nationals",
         {"type": "multi_index", "steps": [
             {"step": 1, "index": "moi-gp-all-profiles-details-v1",
              "query": {"term": {"person_natcde": "Pakistani"}},
              "extract_field": "prs_qid"},
             {"step": 2, "index": "moi-visa-main-details-v1",
              "query": {"bool": {"must": [
                  {"terms": {"HLD_QIDNO": "$step_1"}},
                  {"term": {"VSA_TYPCDE": "40"}},
                  {"term": {"VSA_RCDSTS": "14"}},
              ]}}},
         ]}),
    pair("Find active residence permits held by Indian nationals",
         {"type": "multi_index", "steps": [
             {"step": 1, "index": "moi-gp-all-profiles-details-v1",
              "query": {"term": {"person_natcde": "Indian"}},
              "extract_field": "prs_qid"},
             {"step": 2, "index": "moi-visa-main-details-v1",
              "query": {"bool": {"must": [
                  {"terms": {"HLD_QIDNO": "$step_1"}},
                  {"term": {"VSA_TYPCDE": "20"}},
                  {"term": {"VSA_RCDSTS": "13"}},
              ]}}},
         ]}),

    # M35: Corniche Road violations for Qatari — step 2 uses VLN_PLCDSC (not VLN_TYPE)
    pair("Find violations on Corniche Road for Qatari nationals",
         {"type": "multi_index", "steps": [
             {"step": 1, "index": "moi-gp-all-profiles-details-v1",
              "query": {"term": {"person_natcde": "Qatari"}},
              "extract_field": "prs_qid"},
             {"step": 2, "index": "moi-violations-v1",
              "query": {"bool": {"must": [
                  {"terms": {"VLN_OWNQID": "$step_1"}},
                  {"term": {"VLN_PLCDSC": "CORNICHE ROAD"}},
              ]}}},
         ]}),
    pair("Find violations on Salwa Road for Pakistani nationals",
         {"type": "multi_index", "steps": [
             {"step": 1, "index": "moi-gp-all-profiles-details-v1",
              "query": {"term": {"person_natcde": "Pakistani"}},
              "extract_field": "prs_qid"},
             {"step": 2, "index": "moi-violations-v1",
              "query": {"bool": {"must": [
                  {"terms": {"VLN_OWNQID": "$step_1"}},
                  {"term": {"VLN_PLCDSC": "SALWA ROAD"}},
              ]}}},
         ]}),
    pair("Find speeding violations on Corniche Road for Indian nationals",
         {"type": "multi_index", "steps": [
             {"step": 1, "index": "moi-gp-all-profiles-details-v1",
              "query": {"term": {"person_natcde": "Indian"}},
              "extract_field": "prs_qid"},
             {"step": 2, "index": "moi-violations-v1",
              "query": {"bool": {"must": [
                  {"terms": {"VLN_OWNQID": "$step_1"}},
                  {"term": {"VLN_TYPE": "SPEEDING"}},
                  {"term": {"VLN_PLCDSC": "CORNICHE ROAD"}},
              ]}}},
         ]}),
]


def main():
    all_categories = [
        ("Violations",     violations_pairs),
        ("Person",         person_pairs),
        ("Vehicle",        vehicle_pairs),
        ("Exit/Entry",     exit_entry_pairs),
        ("Visa-main",      visa_main_pairs),
        ("Visa-app",       visa_app_pairs),
        ("Sponsor",        sponsor_pairs),
        ("Relationships",  relationship_pairs),
        ("Multi-index",    multi_pairs),
    ]

    all_train = []
    all_valid = []
    breakdown = {}

    for name, pairs in all_categories:
        random.shuffle(pairs)
        n = len(pairs)
        n_valid = max(1, round(n * 0.25))
        train_pairs = pairs[n_valid:]
        valid_pairs = pairs[:n_valid]
        all_train.extend(train_pairs)
        all_valid.extend(valid_pairs)
        breakdown[name] = len(train_pairs)

    with open(TRAIN_PATH, 'a') as f:
        for p in all_train:
            f.write(json.dumps(p) + '\n')

    with open(VALID_PATH, 'a') as f:
        for p in all_valid:
            f.write(json.dumps(p) + '\n')

    total_train = sum(breakdown.values())
    print(f"Added {total_train} training pairs → train.jsonl")
    print(f"Added {sum(max(1, round(len(p)*0.25)) for _, p in all_categories)} validation pairs → valid.jsonl")
    print(f"\nBreakdown:")
    for name, n in breakdown.items():
        print(f"  {name:20s}: {n:3d} train pairs")

    # Final counts
    import subprocess
    result = subprocess.run(['wc', '-l', str(TRAIN_PATH), str(VALID_PATH)], capture_output=True, text=True)
    print(f"\n{result.stdout.strip()}")


if __name__ == '__main__':
    random.seed(42)
    main()

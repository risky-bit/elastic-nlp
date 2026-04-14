#!/usr/bin/env python3
"""
Generate targeted training pairs for v10 adapter.

Fixes from v9 evaluation (87.3% → target 93%+):

SINGLE-INDEX:
1. P04: "Show all male persons" → model generates must_not exists prs_gdr (wrong!).
   Need simple gender-only queries without nationality context.
2. P11/P15: Nationality OR still failing — should at top level or inside must for
   nationality OR. Persistent issue needing more variation.
3. V09/V13: Model still uses VEH_SIZENDE/VEH_SIZBGN or VRG_YEAR for date ranges.
   Correct field: VRG_STADTE (registration start date). V13 is ONLY range, no status.
4. E04: Model adds spurious TRX_DIRECTION to land crossing query. Just TRX_TRIP_TYP_DESC.
5. E07: Model uses term for BORDER_CODE_DESC (TEXT field). Must use match.
6. VS09: Model hallucinates list of VSA_RCDSTS codes. Correct: VSA_TYPCDE:40 + range VSA_EXPDTE.
7. VS11: Model drops VSA_RCDSTS:13 for "active". Need all three: type+status+nationality.
8. VA04: Model uses APL_APLDSC:13 instead of range APL_APLDTE. Fix date field.

MULTI-INDEX:
9. M08: Step 1 leaks prs_qid/prs_dsc into person query. Step 1 = nationality only.
10. M14/M16: VLN_STATUS leaks into step 1 person query. Must stay in step 2 violations.
11. M21: TRX_DIRECTION + BORDER_CODE_DESC leak into step 1 person query. Step 2 only.
12. M22: Hallucinated TRX_TRIP_TYP_DESC:"1ST TRIP" + missing date range in step 2.
13. M25: Generates single-index visa DSL instead of multi-index person→visa-main.
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


def single(query_body):
    return {"query": query_body}


def multi(steps):
    return {"type": "multi_index", "steps": steps}


def step(n, index, query, extract_field="prs_qid"):
    return {"step": n, "index": index, "query": query, "extract_field": extract_field}


def step2(n, index, query):
    return {"step": n, "index": index, "query": query}


PERSON_INDEX = "moi-gp-all-profiles-details-v1"
VEHICLE_INDEX = "moi-vehicle-info-v1"
VIOLATIONS_INDEX = "moi-violations-v1"
EXIT_INDEX = "moi-exit-entry-tts-details-v1"
VISA_MAIN_INDEX = "moi-visa-main-v1"
VISA_APP_INDEX = "moi-visa-app-v1"


# ─────────────────────────────────────────────────────────────
# 1. PERSON — fix P04 (all males → must_not exists wrong), P11/P15 (OR nationality)
# ─────────────────────────────────────────────────────────────
person_pairs = [
    # P04: simple gender-only queries — must use term prs_gdr, NOT must_not exists
    pair("Show all male persons",
         single({"term": {"prs_gdr": "Male"}})),
    pair("Find all male persons",
         single({"term": {"prs_gdr": "Male"}})),
    pair("List all males",
         single({"term": {"prs_gdr": "Male"}})),
    pair("Show all female persons",
         single({"term": {"prs_gdr": "Female"}})),
    pair("Find all female persons",
         single({"term": {"prs_gdr": "Female"}})),
    pair("List all females",
         single({"term": {"prs_gdr": "Female"}})),
    pair("Show all persons who are male",
         single({"term": {"prs_gdr": "Male"}})),
    pair("Find persons who are female",
         single({"term": {"prs_gdr": "Female"}})),
    pair("Get all male records",
         single({"term": {"prs_gdr": "Male"}})),
    pair("Retrieve all female records",
         single({"term": {"prs_gdr": "Female"}})),

    # P11: nationality OR + gender — should nested inside must
    pair("Find persons from India or Pakistan who are male",
         single({"bool": {"must": [
             {"term": {"prs_gdr": "Male"}},
             {"bool": {"should": [
                 {"term": {"person_natcde": "Indian"}},
                 {"term": {"person_natcde": "Pakistani"}},
             ]}},
         ]}})),
    pair("Show male persons from Egypt or Jordan",
         single({"bool": {"must": [
             {"term": {"prs_gdr": "Male"}},
             {"bool": {"should": [
                 {"term": {"person_natcde": "Egyptian"}},
                 {"term": {"person_natcde": "Jordanian"}},
             ]}},
         ]}})),
    pair("Find female persons from Nepal or Sri Lanka",
         single({"bool": {"must": [
             {"term": {"prs_gdr": "Female"}},
             {"bool": {"should": [
                 {"term": {"person_natcde": "Nepali"}},
                 {"term": {"person_natcde": "Sri Lankan"}},
             ]}},
         ]}})),
    pair("Show males from Bangladesh or India",
         single({"bool": {"must": [
             {"term": {"prs_gdr": "Male"}},
             {"bool": {"should": [
                 {"term": {"person_natcde": "Bangladeshi"}},
                 {"term": {"person_natcde": "Indian"}},
             ]}},
         ]}})),
    pair("Find males from Qatar or UAE",
         single({"bool": {"must": [
             {"term": {"prs_gdr": "Male"}},
             {"bool": {"should": [
                 {"term": {"person_natcde": "Qatari"}},
                 {"term": {"person_natcde": "Emirati"}},
             ]}},
         ]}})),
    pair("Show female persons from Pakistan or Bangladesh",
         single({"bool": {"must": [
             {"term": {"prs_gdr": "Female"}},
             {"bool": {"should": [
                 {"term": {"person_natcde": "Pakistani"}},
                 {"term": {"person_natcde": "Bangladeshi"}},
             ]}},
         ]}})),

    # P15: pure nationality OR — top-level should (NOT must with same field)
    pair("Find all Nepali or Sri Lankan nationals",
         single({"bool": {"should": [
             {"term": {"person_natcde": "Nepali"}},
             {"term": {"person_natcde": "Sri Lankan"}},
         ]}})),
    pair("Show Nepali or Sri Lankan nationals",
         single({"bool": {"should": [
             {"term": {"person_natcde": "Nepali"}},
             {"term": {"person_natcde": "Sri Lankan"}},
         ]}})),
    pair("Find all Indian or Pakistani nationals",
         single({"bool": {"should": [
             {"term": {"person_natcde": "Indian"}},
             {"term": {"person_natcde": "Pakistani"}},
         ]}})),
    pair("Show Egyptian or Jordanian nationals",
         single({"bool": {"should": [
             {"term": {"person_natcde": "Egyptian"}},
             {"term": {"person_natcde": "Jordanian"}},
         ]}})),
    pair("Find Bangladeshi or Nepali nationals",
         single({"bool": {"should": [
             {"term": {"person_natcde": "Bangladeshi"}},
             {"term": {"person_natcde": "Nepali"}},
         ]}})),
    pair("List persons from India or Bangladesh",
         single({"bool": {"should": [
             {"term": {"person_natcde": "Indian"}},
             {"term": {"person_natcde": "Bangladeshi"}},
         ]}})),
    pair("Show all Qatari or Emirati nationals",
         single({"bool": {"should": [
             {"term": {"person_natcde": "Qatari"}},
             {"term": {"person_natcde": "Emirati"}},
         ]}})),
]

# ─────────────────────────────────────────────────────────────
# 2. VEHICLE — fix V09/V13 (VRG_STADTE not VRG_YEAR/VEH_SIZENDE)
# Registration date field is VRG_STADTE. V13 is ONLY a range — no status filter.
# ─────────────────────────────────────────────────────────────
vehicle_pairs = [
    # V13: plain registration year — ONLY range VRG_STADTE, no VRG_STATUS
    pair("Find all vehicles registered in 2023",
         single({"range": {"VRG_STADTE": {"gte": "2023-01-01", "lte": "2023-12-31"}}})),
    pair("Show all vehicles registered in 2022",
         single({"range": {"VRG_STADTE": {"gte": "2022-01-01", "lte": "2022-12-31"}}})),
    pair("List vehicles registered in 2021",
         single({"range": {"VRG_STADTE": {"gte": "2021-01-01", "lte": "2021-12-31"}}})),
    pair("Show vehicles registered in 2024",
         single({"range": {"VRG_STADTE": {"gte": "2024-01-01", "lte": "2024-12-31"}}})),

    # V09: brand + model + color + date range → VRG_STADTE range
    pair("Find white Toyota Camry vehicles registered between 2020 and 2023",
         single({"bool": {"must": [
             {"match": {"MNF_ENSHDESC": "TOYOTA"}},
             {"match": {"CLR_CLRENGDSC": "WHITE"}},
             {"match": {"VEH_MODEL": "CAMRY"}},
             {"range": {"VRG_STADTE": {"gte": "2020-01-01", "lte": "2023-12-31"}}},
         ]}})),
    pair("Show black Toyota Camry vehicles registered between 2021 and 2023",
         single({"bool": {"must": [
             {"match": {"MNF_ENSHDESC": "TOYOTA"}},
             {"match": {"CLR_CLRENGDSC": "BLACK"}},
             {"match": {"VEH_MODEL": "CAMRY"}},
             {"range": {"VRG_STADTE": {"gte": "2021-01-01", "lte": "2023-12-31"}}},
         ]}})),
    pair("Find silver Nissan Patrol registered between 2019 and 2022",
         single({"bool": {"must": [
             {"match": {"MNF_ENSHDESC": "NISSAN"}},
             {"match": {"CLR_CLRENGDSC": "SILVER"}},
             {"match": {"VEH_MODEL": "PATROL"}},
             {"range": {"VRG_STADTE": {"gte": "2019-01-01", "lte": "2022-12-31"}}},
         ]}})),
    pair("Find red Toyota Land Cruiser registered between 2018 and 2020",
         single({"bool": {"must": [
             {"match": {"MNF_ENSHDESC": "TOYOTA"}},
             {"match": {"CLR_CLRENGDSC": "RED"}},
             {"match": {"VEH_MODEL": "LAND CRUISER"}},
             {"range": {"VRG_STADTE": {"gte": "2018-01-01", "lte": "2020-12-31"}}},
         ]}})),
    pair("Show white Honda Accord vehicles registered after 2022",
         single({"bool": {"must": [
             {"match": {"MNF_ENSHDESC": "HONDA"}},
             {"match": {"CLR_CLRENGDSC": "WHITE"}},
             {"match": {"VEH_MODEL": "ACCORD"}},
             {"range": {"VRG_STADTE": {"gte": "2022-01-01"}}},
         ]}})),
    pair("Find blue Nissan Sunny registered in 2021",
         single({"bool": {"must": [
             {"match": {"MNF_ENSHDESC": "NISSAN"}},
             {"match": {"CLR_CLRENGDSC": "BLUE"}},
             {"match": {"VEH_MODEL": "SUNNY"}},
             {"range": {"VRG_STADTE": {"gte": "2021-01-01", "lte": "2021-12-31"}}},
         ]}})),
    # Brand + date range without model
    pair("Find Toyota vehicles registered between 2020 and 2023",
         single({"bool": {"must": [
             {"match": {"MNF_ENSHDESC": "TOYOTA"}},
             {"range": {"VRG_STADTE": {"gte": "2020-01-01", "lte": "2023-12-31"}}},
         ]}})),
    pair("Show Nissan vehicles registered in 2022",
         single({"bool": {"must": [
             {"match": {"MNF_ENSHDESC": "NISSAN"}},
             {"range": {"VRG_STADTE": {"gte": "2022-01-01", "lte": "2022-12-31"}}},
         ]}})),
]

# ─────────────────────────────────────────────────────────────
# 3. EXIT/ENTRY — fix E04 (no direction for LAND), E07 (match not term for border)
# All exit/entry text fields use match: TRX_DIRECTION, TRX_TRIP_TYP_DESC, BORDER_CODE_DESC
# ─────────────────────────────────────────────────────────────
exit_entry_pairs = [
    # E04: land crossings — ONLY TRX_TRIP_TYP_DESC:LAND, no direction filter
    pair("Show all land border crossings",
         single({"match": {"TRX_TRIP_TYP_DESC": "LAND"}})),
    pair("Find all land crossings",
         single({"match": {"TRX_TRIP_TYP_DESC": "LAND"}})),
    pair("List all land border transactions",
         single({"match": {"TRX_TRIP_TYP_DESC": "LAND"}})),
    pair("Show all sea crossings",
         single({"match": {"TRX_TRIP_TYP_DESC": "SEA"}})),
    pair("Find all flight crossings",
         single({"match": {"TRX_TRIP_TYP_DESC": "FLIGHT"}})),

    # E07: border exit with specific border — match for both fields
    pair("Find all exits through Abu Samra border",
         single({"bool": {"must": [
             {"match": {"TRX_DIRECTION": "OUT"}},
             {"match": {"BORDER_CODE_DESC": "ABU SAMRA BORDER"}},
         ]}})),
    pair("Show exits through Abu Samra border",
         single({"bool": {"must": [
             {"match": {"TRX_DIRECTION": "OUT"}},
             {"match": {"BORDER_CODE_DESC": "ABU SAMRA BORDER"}},
         ]}})),
    pair("Find entries through Hamad International Airport",
         single({"bool": {"must": [
             {"match": {"TRX_DIRECTION": "IN"}},
             {"match": {"BORDER_CODE_DESC": "HAMAD INTERNATIONAL AIRPORT"}},
         ]}})),
    pair("Show exits through Salwa border",
         single({"bool": {"must": [
             {"match": {"TRX_DIRECTION": "OUT"}},
             {"match": {"BORDER_CODE_DESC": "SALWA BORDER"}},
         ]}})),
    pair("Find entries through Abu Samra",
         single({"bool": {"must": [
             {"match": {"TRX_DIRECTION": "IN"}},
             {"match": {"BORDER_CODE_DESC": "ABU SAMRA BORDER"}},
         ]}})),
    # Exit + trip type
    pair("Find all flight exits",
         single({"bool": {"must": [
             {"match": {"TRX_DIRECTION": "OUT"}},
             {"match": {"TRX_TRIP_TYP_DESC": "FLIGHT"}},
         ]}})),
    pair("Show all land exits",
         single({"bool": {"must": [
             {"match": {"TRX_DIRECTION": "OUT"}},
             {"match": {"TRX_TRIP_TYP_DESC": "LAND"}},
         ]}})),
    pair("Find all land entries",
         single({"bool": {"must": [
             {"match": {"TRX_DIRECTION": "IN"}},
             {"match": {"TRX_TRIP_TYP_DESC": "LAND"}},
         ]}})),
]

# ─────────────────────────────────────────────────────────────
# 4. VISA-MAIN — fix VS09 (VSA_EXPDTE range), VS11 (need VSA_RCDSTS:13 for active)
# ─────────────────────────────────────────────────────────────
visa_main_pairs = [
    # VS09: work visas expiring before date — VSA_TYPCDE:40 + range VSA_EXPDTE
    pair("Find work visas expiring before 2026",
         single({"bool": {"must": [
             {"term": {"VSA_TYPCDE": "40"}},
             {"range": {"VSA_EXPDTE": {"lt": "2026-01-01"}}},
         ]}})),
    pair("Show work visas expiring before 2025",
         single({"bool": {"must": [
             {"term": {"VSA_TYPCDE": "40"}},
             {"range": {"VSA_EXPDTE": {"lt": "2025-01-01"}}},
         ]}})),
    pair("Find work visas that expire before 2024",
         single({"bool": {"must": [
             {"term": {"VSA_TYPCDE": "40"}},
             {"range": {"VSA_EXPDTE": {"lt": "2024-01-01"}}},
         ]}})),
    pair("Show residence visas expiring before 2026",
         single({"bool": {"must": [
             {"term": {"VSA_TYPCDE": "20"}},
             {"range": {"VSA_EXPDTE": {"lt": "2026-01-01"}}},
         ]}})),
    pair("Find visit visas expiring before 2025",
         single({"bool": {"must": [
             {"term": {"VSA_TYPCDE": "11"}},
             {"range": {"VSA_EXPDTE": {"lt": "2025-01-01"}}},
         ]}})),
    pair("Show visas expiring in 2025",
         single({"bool": {"must": [
             {"range": {"VSA_EXPDTE": {"gte": "2025-01-01", "lte": "2025-12-31"}}},
         ]}})),

    # VS11: active work visas for nationality — MUST include VSA_RCDSTS:13 for active
    pair("Find active work visas for Pakistani nationals",
         single({"bool": {"must": [
             {"term": {"VSA_TYPCDE": "40"}},
             {"term": {"VSA_RCDSTS": "13"}},
             {"term": {"NAT_CDENUM": "Pakistani"}},
         ]}})),
    pair("Show active work visas for Indian nationals",
         single({"bool": {"must": [
             {"term": {"VSA_TYPCDE": "40"}},
             {"term": {"VSA_RCDSTS": "13"}},
             {"term": {"NAT_CDENUM": "Indian"}},
         ]}})),
    pair("Find active residence visas for Pakistani nationals",
         single({"bool": {"must": [
             {"term": {"VSA_TYPCDE": "20"}},
             {"term": {"VSA_RCDSTS": "13"}},
             {"term": {"NAT_CDENUM": "Pakistani"}},
         ]}})),
    pair("Show active work visas for Bangladeshi nationals",
         single({"bool": {"must": [
             {"term": {"VSA_TYPCDE": "40"}},
             {"term": {"VSA_RCDSTS": "13"}},
             {"term": {"NAT_CDENUM": "Bangladeshi"}},
         ]}})),
    pair("Find all active work visas",
         single({"bool": {"must": [
             {"term": {"VSA_TYPCDE": "40"}},
             {"term": {"VSA_RCDSTS": "13"}},
         ]}})),
]

# ─────────────────────────────────────────────────────────────
# 5. VISA-APP — fix VA04 (range APL_APLDTE not term APL_APLDSC)
# ─────────────────────────────────────────────────────────────
visa_app_pairs = [
    # VA04: approved + date range — APL_RCDSTS:"2" + range APL_APLDTE
    pair("Show approved applications submitted in 2023",
         single({"bool": {"must": [
             {"term": {"APL_RCDSTS": "2"}},
             {"range": {"APL_APLDTE": {"gte": "2023-01-01", "lte": "2023-12-31"}}},
         ]}})),
    pair("Find approved applications from 2023",
         single({"bool": {"must": [
             {"term": {"APL_RCDSTS": "2"}},
             {"range": {"APL_APLDTE": {"gte": "2023-01-01", "lte": "2023-12-31"}}},
         ]}})),
    pair("Show approved visa applications submitted in 2022",
         single({"bool": {"must": [
             {"term": {"APL_RCDSTS": "2"}},
             {"range": {"APL_APLDTE": {"gte": "2022-01-01", "lte": "2022-12-31"}}},
         ]}})),
    pair("Find rejected applications submitted in 2023",
         single({"bool": {"must": [
             {"term": {"APL_RCDSTS": "3"}},
             {"range": {"APL_APLDTE": {"gte": "2023-01-01", "lte": "2023-12-31"}}},
         ]}})),
    pair("Show all applications submitted in 2024",
         single({"range": {"APL_APLDTE": {"gte": "2024-01-01", "lte": "2024-12-31"}}})),
    pair("Find applications submitted between 2022 and 2023",
         single({"range": {"APL_APLDTE": {"gte": "2022-01-01", "lte": "2023-12-31"}}})),
]

# ─────────────────────────────────────────────────────────────
# 6. MULTI-INDEX — fix M08/M14/M16/M21/M22/M25
# RULE: Step 1 queries person index ONLY with person attributes (nationality, gender, name).
# All other filters (violations status, exit direction, border, date ranges) go in STEP 2.
# ─────────────────────────────────────────────────────────────
multi_pairs = [
    # M08: vehicles with expired registration for nationality
    # Step 1: ONLY nationality in person. Step 2: VRG_OWNQID + VRG_STATUS in vehicle.
    pair("Find vehicles with expired registration owned by Indian nationals",
         multi([
             step(1, PERSON_INDEX,
                  {"term": {"person_natcde": "Indian"}}),
             step2(2, VEHICLE_INDEX,
                   {"bool": {"must": [
                       {"terms": {"VRG_OWNQID": "$step_1"}},
                       {"match": {"VRG_STATUS": "EXP"}},
                   ]}}),
         ])),
    pair("Show expired vehicles owned by Pakistani nationals",
         multi([
             step(1, PERSON_INDEX,
                  {"term": {"person_natcde": "Pakistani"}}),
             step2(2, VEHICLE_INDEX,
                   {"bool": {"must": [
                       {"terms": {"VRG_OWNQID": "$step_1"}},
                       {"match": {"VRG_STATUS": "EXP"}},
                   ]}}),
         ])),
    pair("Find vehicles with expired registration owned by Egyptian nationals",
         multi([
             step(1, PERSON_INDEX,
                  {"term": {"person_natcde": "Egyptian"}}),
             step2(2, VEHICLE_INDEX,
                   {"bool": {"must": [
                       {"terms": {"VRG_OWNQID": "$step_1"}},
                       {"match": {"VRG_STATUS": "EXP"}},
                   ]}}),
         ])),

    # M14: paid violations for nationality — VLN_STATUS MUST be in step 2, NOT step 1
    pair("Find paid violations for Qatari nationals",
         multi([
             step(1, PERSON_INDEX,
                  {"term": {"person_natcde": "Qatari"}}),
             step2(2, VIOLATIONS_INDEX,
                   {"bool": {"must": [
                       {"terms": {"VLN_OWNQID": "$step_1"}},
                       {"term": {"VLN_STATUS": "PAID"}},
                   ]}}),
         ])),
    pair("Show paid violations for Indian nationals",
         multi([
             step(1, PERSON_INDEX,
                  {"term": {"person_natcde": "Indian"}}),
             step2(2, VIOLATIONS_INDEX,
                   {"bool": {"must": [
                       {"terms": {"VLN_OWNQID": "$step_1"}},
                       {"term": {"VLN_STATUS": "PAID"}},
                   ]}}),
         ])),
    pair("Find paid violations for Pakistani nationals",
         multi([
             step(1, PERSON_INDEX,
                  {"term": {"person_natcde": "Pakistani"}}),
             step2(2, VIOLATIONS_INDEX,
                   {"bool": {"must": [
                       {"terms": {"VLN_OWNQID": "$step_1"}},
                       {"term": {"VLN_STATUS": "PAID"}},
                   ]}}),
         ])),

    # M16: unpaid violations for nationality — VLN_STATUS in step 2 only
    pair("Find unpaid violations for Egyptian nationals",
         multi([
             step(1, PERSON_INDEX,
                  {"term": {"person_natcde": "Egyptian"}}),
             step2(2, VIOLATIONS_INDEX,
                   {"bool": {"must": [
                       {"terms": {"VLN_OWNQID": "$step_1"}},
                       {"term": {"VLN_STATUS": "UNPAID"}},
                   ]}}),
         ])),
    pair("Show unpaid violations for Indian nationals",
         multi([
             step(1, PERSON_INDEX,
                  {"term": {"person_natcde": "Indian"}}),
             step2(2, VIOLATIONS_INDEX,
                   {"bool": {"must": [
                       {"terms": {"VLN_OWNQID": "$step_1"}},
                       {"term": {"VLN_STATUS": "UNPAID"}},
                   ]}}),
         ])),
    pair("Find unpaid violations for Bangladeshi nationals",
         multi([
             step(1, PERSON_INDEX,
                  {"term": {"person_natcde": "Bangladeshi"}}),
             step2(2, VIOLATIONS_INDEX,
                   {"bool": {"must": [
                       {"terms": {"VLN_OWNQID": "$step_1"}},
                       {"term": {"VLN_STATUS": "UNPAID"}},
                   ]}}),
         ])),

    # M21: entries via specific border for nationality
    # Step 1: ONLY nationality. Step 2: TRX_QIDNO + direction + border.
    pair("Find entries via Hamad Airport for Pakistani nationals",
         multi([
             step(1, PERSON_INDEX,
                  {"term": {"person_natcde": "Pakistani"}}),
             step2(2, EXIT_INDEX,
                   {"bool": {"must": [
                       {"terms": {"TRX_QIDNO": "$step_1"}},
                       {"match": {"TRX_DIRECTION": "IN"}},
                       {"match": {"BORDER_CODE_DESC": "HAMAD INTERNATIONAL AIRPORT"}},
                   ]}}),
         ])),
    pair("Find entries via Hamad Airport for Indian nationals",
         multi([
             step(1, PERSON_INDEX,
                  {"term": {"person_natcde": "Indian"}}),
             step2(2, EXIT_INDEX,
                   {"bool": {"must": [
                       {"terms": {"TRX_QIDNO": "$step_1"}},
                       {"match": {"TRX_DIRECTION": "IN"}},
                       {"match": {"BORDER_CODE_DESC": "HAMAD INTERNATIONAL AIRPORT"}},
                   ]}}),
         ])),
    pair("Find exits via Abu Samra border for Qatari nationals",
         multi([
             step(1, PERSON_INDEX,
                  {"term": {"person_natcde": "Qatari"}}),
             step2(2, EXIT_INDEX,
                   {"bool": {"must": [
                       {"terms": {"TRX_QIDNO": "$step_1"}},
                       {"match": {"TRX_DIRECTION": "OUT"}},
                       {"match": {"BORDER_CODE_DESC": "ABU SAMRA BORDER"}},
                   ]}}),
         ])),
    pair("Show entries through Abu Samra for Egyptian nationals",
         multi([
             step(1, PERSON_INDEX,
                  {"term": {"person_natcde": "Egyptian"}}),
             step2(2, EXIT_INDEX,
                   {"bool": {"must": [
                       {"terms": {"TRX_QIDNO": "$step_1"}},
                       {"match": {"TRX_DIRECTION": "IN"}},
                       {"match": {"BORDER_CODE_DESC": "ABU SAMRA BORDER"}},
                   ]}}),
         ])),

    # M22: exit transactions in specific year for nationality
    # Step 2 must include TRX_DIRECTION + date range. No TRX_TRIP_TYP_DESC unless specified.
    pair("Find exit transactions in 2024 for Qatari nationals",
         multi([
             step(1, PERSON_INDEX,
                  {"term": {"person_natcde": "Qatari"}}),
             step2(2, EXIT_INDEX,
                   {"bool": {"must": [
                       {"terms": {"TRX_QIDNO": "$step_1"}},
                       {"match": {"TRX_DIRECTION": "OUT"}},
                       {"range": {"TRX_DATE": {"gte": "2024-01-01", "lte": "2024-12-31"}}},
                   ]}}),
         ])),
    pair("Find exit transactions in 2023 for Indian nationals",
         multi([
             step(1, PERSON_INDEX,
                  {"term": {"person_natcde": "Indian"}}),
             step2(2, EXIT_INDEX,
                   {"bool": {"must": [
                       {"terms": {"TRX_QIDNO": "$step_1"}},
                       {"match": {"TRX_DIRECTION": "OUT"}},
                       {"range": {"TRX_DATE": {"gte": "2023-01-01", "lte": "2023-12-31"}}},
                   ]}}),
         ])),
    pair("Find entry transactions in 2024 for Pakistani nationals",
         multi([
             step(1, PERSON_INDEX,
                  {"term": {"person_natcde": "Pakistani"}}),
             step2(2, EXIT_INDEX,
                   {"bool": {"must": [
                       {"terms": {"TRX_QIDNO": "$step_1"}},
                       {"match": {"TRX_DIRECTION": "IN"}},
                       {"range": {"TRX_DATE": {"gte": "2024-01-01", "lte": "2024-12-31"}}},
                   ]}}),
         ])),
    pair("Show exit transactions in 2022 for Bangladeshi nationals",
         multi([
             step(1, PERSON_INDEX,
                  {"term": {"person_natcde": "Bangladeshi"}}),
             step2(2, EXIT_INDEX,
                   {"bool": {"must": [
                       {"terms": {"TRX_QIDNO": "$step_1"}},
                       {"match": {"TRX_DIRECTION": "OUT"}},
                       {"range": {"TRX_DATE": {"gte": "2022-01-01", "lte": "2022-12-31"}}},
                   ]}}),
         ])),

    # M25: residence permits for nationality — multi-index person→visa-main
    # NEVER use single-index NAT_CDENUM for this — must go through person index
    pair("Find all residence permits held by Qatari nationals",
         multi([
             step(1, PERSON_INDEX,
                  {"term": {"person_natcde": "Qatari"}}),
             step2(2, VISA_MAIN_INDEX,
                   {"bool": {"must": [
                       {"terms": {"HLD_QIDNO": "$step_1"}},
                       {"term": {"VSA_TYPCDE": "20"}},
                   ]}}),
         ])),
    pair("Show residence permits held by Qatari nationals",
         multi([
             step(1, PERSON_INDEX,
                  {"term": {"person_natcde": "Qatari"}}),
             step2(2, VISA_MAIN_INDEX,
                   {"bool": {"must": [
                       {"terms": {"HLD_QIDNO": "$step_1"}},
                       {"term": {"VSA_TYPCDE": "20"}},
                   ]}}),
         ])),
    pair("Find work permits held by Qatari nationals",
         multi([
             step(1, PERSON_INDEX,
                  {"term": {"person_natcde": "Qatari"}}),
             step2(2, VISA_MAIN_INDEX,
                   {"bool": {"must": [
                       {"terms": {"HLD_QIDNO": "$step_1"}},
                       {"term": {"VSA_TYPCDE": "40"}},
                   ]}}),
         ])),
    pair("Find all residence permits held by Indian nationals",
         multi([
             step(1, PERSON_INDEX,
                  {"term": {"person_natcde": "Indian"}}),
             step2(2, VISA_MAIN_INDEX,
                   {"bool": {"must": [
                       {"terms": {"HLD_QIDNO": "$step_1"}},
                       {"term": {"VSA_TYPCDE": "20"}},
                   ]}}),
         ])),
    pair("Find work permits held by Pakistani nationals",
         multi([
             step(1, PERSON_INDEX,
                  {"term": {"person_natcde": "Pakistani"}}),
             step2(2, VISA_MAIN_INDEX,
                   {"bool": {"must": [
                       {"terms": {"HLD_QIDNO": "$step_1"}},
                       {"term": {"VSA_TYPCDE": "40"}},
                   ]}}),
         ])),
]


# ─────────────────────────────────────────────────────────────
# ASSEMBLE AND WRITE
# ─────────────────────────────────────────────────────────────
all_pairs = (
    person_pairs
    + vehicle_pairs
    + exit_entry_pairs
    + visa_main_pairs
    + visa_app_pairs
    + multi_pairs
)

random.seed(42)
random.shuffle(all_pairs)

n_valid = max(10, len(all_pairs) // 5)
valid_pairs = all_pairs[:n_valid]
train_pairs = all_pairs[n_valid:]

TRAIN_PATH.parent.mkdir(parents=True, exist_ok=True)

with open(TRAIN_PATH, "w") as f:
    for p in train_pairs:
        f.write(json.dumps(p) + "\n")

with open(VALID_PATH, "w") as f:
    for p in valid_pairs:
        f.write(json.dumps(p) + "\n")

print(f"v10 training data: {len(train_pairs)} train / {len(valid_pairs)} valid")
print(f"Total pairs: {len(all_pairs)}")
print(f"  Person: {len(person_pairs)}")
print(f"  Vehicle: {len(vehicle_pairs)}")
print(f"  Exit/Entry: {len(exit_entry_pairs)}")
print(f"  Visa-main: {len(visa_main_pairs)}")
print(f"  Visa-app: {len(visa_app_pairs)}")
print(f"  Multi-index: {len(multi_pairs)}")

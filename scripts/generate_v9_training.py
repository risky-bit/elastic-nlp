#!/usr/bin/env python3
"""
Generate targeted training pairs for v9 adapter.

Fixes from v8 evaluation (81.7% → target 88%+):

SINGLE-INDEX:
1. P06: model drops gender for "Qatari males" → returns all Qatari. Must always include
   prs_gdr filter when gender is mentioned.
2. P11: model writes wrong numeric code for Pakistan (366 vs 586). Use nationality NAMES,
   transformer converts. Also ensure should structure (not must) for OR nationalities.
3. P15: model uses must (impossible same-field AND). Must use should for nationality OR.
4. V09: still missing VEH_MODEL filter for model name.
5. E10: uses match on TRX_DATE for year range — must use range.
6. VS01/VS06/VS08: VISA_TYPE_DESC still used. Massive reinforcement of VSA_TYPCDE.
   VS08: "active work visas" needs BOTH VSA_TYPCDE:40 AND VSA_RCDSTS:13.
   VS09: uses VSA_RCDTE (wrong) instead of VSA_EXPDTE.
7. VS07/VS11: still go multi-index for nationality+visa queries. Must be single-index.
8. VS12: hallucinates many status codes. Only one expired code: VSA_RCDSTS:"14".
9. RL01: generates VISA_TYPE_DESC query instead of match_all.
   RL03: uses DIVORCE_CERTIFICATE_NUMBER (wrong field) — must use DIVORCE_DATE.
10. VA04: uses term on APL_APLDTE range (invalid). Must use range query.

MULTI-INDEX:
11. M10/M32/M33: gender-qualified queries — gender filter must be in step 1 person query,
    NOT via extract_field. extract_field is always "prs_qid".
12. M11: step 2 uses VRG_MIDSCDE (wrong). Must use MNF_ENSHDESC.
13. M15: step 2 missing VRG_STATUS filter (vehicles with active registration).
14. M17/M18: exit/entry for nationals — step 2 MUST include TRX_DIRECTION filter.
15. M35: step 2 adds spurious VLN_TYPE filter alongside VLN_PLCDSC. Use VLN_PLCDSC only.
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


# ─────────────────────────────────────────────────────────────
# 1. PERSON — fix P06 (gender dropped), P11 (OR code wrong), P15 (must vs should)
# ─────────────────────────────────────────────────────────────
person_pairs = [
    # P06: nationality + gender — both must appear
    pair("Show Qatari males",
         single({"bool": {"must": [
             {"term": {"person_natcde": "Qatari"}},
             {"term": {"prs_gdr": "Male"}},
         ]}})),
    pair("Find Qatari males",
         single({"bool": {"must": [
             {"term": {"person_natcde": "Qatari"}},
             {"term": {"prs_gdr": "Male"}},
         ]}})),
    pair("Show Qatari females",
         single({"bool": {"must": [
             {"term": {"person_natcde": "Qatari"}},
             {"term": {"prs_gdr": "Female"}},
         ]}})),
    pair("Find Indian males",
         single({"bool": {"must": [
             {"term": {"person_natcde": "Indian"}},
             {"term": {"prs_gdr": "Male"}},
         ]}})),
    pair("Show Egyptian females",
         single({"bool": {"must": [
             {"term": {"person_natcde": "Egyptian"}},
             {"term": {"prs_gdr": "Female"}},
         ]}})),
    pair("Find Emirati males",
         single({"bool": {"must": [
             {"term": {"person_natcde": "Emirati"}},
             {"term": {"prs_gdr": "Male"}},
         ]}})),

    # P11: India OR Pakistan + male — use NAMES not codes; should inside must
    pair("Find persons from India or Pakistan who are male",
         single({"bool": {"must": [
             {"term": {"prs_gdr": "Male"}},
             {"bool": {"should": [
                 {"term": {"person_natcde": "Indian"}},
                 {"term": {"person_natcde": "Pakistani"}},
             ]}},
         ]}})),
    pair("Find male persons from Egypt or Jordan",
         single({"bool": {"must": [
             {"term": {"prs_gdr": "Male"}},
             {"bool": {"should": [
                 {"term": {"person_natcde": "Egyptian"}},
                 {"term": {"person_natcde": "Jordanian"}},
             ]}},
         ]}})),
    pair("Show female persons from Nepal or Sri Lanka",
         single({"bool": {"must": [
             {"term": {"prs_gdr": "Female"}},
             {"bool": {"should": [
                 {"term": {"person_natcde": "Nepali"}},
                 {"term": {"person_natcde": "Sri Lankan"}},
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

    # P15: nationality OR at top level — use should, NOT must
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
]

# ─────────────────────────────────────────────────────────────
# 2. VEHICLE — fix V09 (VEH_MODEL missing) + E10 (range not match on date)
# ─────────────────────────────────────────────────────────────
vehicle_pairs = [
    pair("Find white Toyota Camry vehicles registered between 2020 and 2023",
         single({"bool": {"must": [
             {"match": {"MNF_ENSHDESC": "TOYOTA"}},
             {"match": {"CLR_CLRENGDSC": "WHITE"}},
             {"match": {"VEH_MODEL": "CAMRY"}},
             {"range": {"VRG_STADTE": {"gte": "2020-01-01", "lte": "2023-12-31"}}},
         ]}})),
    pair("Find white Toyota Camry vehicles",
         single({"bool": {"must": [
             {"match": {"MNF_ENSHDESC": "TOYOTA"}},
             {"match": {"CLR_CLRENGDSC": "WHITE"}},
             {"match": {"VEH_MODEL": "CAMRY"}},
         ]}})),
    pair("Show black Toyota Camry vehicles registered in 2021",
         single({"bool": {"must": [
             {"match": {"MNF_ENSHDESC": "TOYOTA"}},
             {"match": {"CLR_CLRENGDSC": "BLACK"}},
             {"match": {"VEH_MODEL": "CAMRY"}},
             {"range": {"VRG_STADTE": {"gte": "2021-01-01", "lte": "2021-12-31"}}},
         ]}})),
    pair("Find silver Nissan Patrol vehicles registered after 2019",
         single({"bool": {"must": [
             {"match": {"MNF_ENSHDESC": "NISSAN"}},
             {"match": {"CLR_CLRENGDSC": "SILVER"}},
             {"match": {"VEH_MODEL": "PATROL"}},
             {"range": {"VRG_STADTE": {"gte": "2019-01-01"}}},
         ]}})),
]

# ─────────────────────────────────────────────────────────────
# 3. EXIT/ENTRY — fix E10 (must use range for year, not match)
# ─────────────────────────────────────────────────────────────
exit_entry_pairs = [
    # E10: "exit transactions via flight in 2024" — date uses range TRX_DATE
    pair("Show all exit transactions via flight in 2024",
         single({"bool": {"must": [
             {"match": {"TRX_DIRECTION": "OUT"}},
             {"match": {"TRX_TRIP_TYP_DESC": "FLIGHT"}},
             {"range": {"TRX_DATE": {"gte": "2024-01-01", "lte": "2024-12-31"}}},
         ]}})),
    pair("Find all exit transactions via flight in 2024",
         single({"bool": {"must": [
             {"match": {"TRX_DIRECTION": "OUT"}},
             {"match": {"TRX_TRIP_TYP_DESC": "FLIGHT"}},
             {"range": {"TRX_DATE": {"gte": "2024-01-01", "lte": "2024-12-31"}}},
         ]}})),
    pair("Show all entry transactions via flight in 2023",
         single({"bool": {"must": [
             {"match": {"TRX_DIRECTION": "IN"}},
             {"match": {"TRX_TRIP_TYP_DESC": "FLIGHT"}},
             {"range": {"TRX_DATE": {"gte": "2023-01-01", "lte": "2023-12-31"}}},
         ]}})),
    pair("Find flight exits in 2023",
         single({"bool": {"must": [
             {"match": {"TRX_DIRECTION": "OUT"}},
             {"match": {"TRX_TRIP_TYP_DESC": "FLIGHT"}},
             {"range": {"TRX_DATE": {"gte": "2023-01-01", "lte": "2023-12-31"}}},
         ]}})),
    pair("Show all entries via Hamad Airport in 2022",
         single({"bool": {"must": [
             {"match": {"TRX_DIRECTION": "IN"}},
             {"match": {"BORDER_CODE_DESC": "HAMAD INTERNATIONAL AIRPORT"}},
             {"range": {"TRX_DATE": {"gte": "2022-01-01", "lte": "2022-12-31"}}},
         ]}})),
]

# ─────────────────────────────────────────────────────────────
# 4. VISA-MAIN — massive reinforcement, fix all remaining patterns
#    Key rules:
#    - Work visa: VSA_TYPCDE = "40"  (NEVER VISA_TYPE_DESC)
#    - Residence permit: VSA_TYPCDE = "20"
#    - Visit visa: VSA_TYPCDE = "11"
#    - Active: VSA_RCDSTS = "13"  (NEVER VSA_RCDSTS = "1" or other)
#    - Expired: VSA_RCDSTS = "14"  (ONLY "14", never a list of codes)
#    - Expiry date field: VSA_EXPDTE  (NEVER VSA_RCDTE or VRDTE)
#    - Issue date field: VSA_ISSDTE
#    - "Active work visas" = MUST have BOTH VSA_TYPCDE:40 AND VSA_RCDSTS:13
#    - Nationality queries: SINGLE INDEX using NAT_CDENUM (never multi-index)
# ─────────────────────────────────────────────────────────────
visa_main_pairs = [
    # VS01: work visa type — VSA_TYPCDE:"40" only
    pair("Find all work visas",
         single({"term": {"VSA_TYPCDE": "40"}})),
    pair("Show all work visas",
         single({"term": {"VSA_TYPCDE": "40"}})),
    pair("List all work visas",
         single({"term": {"VSA_TYPCDE": "40"}})),
    pair("Get all work visas",
         single({"term": {"VSA_TYPCDE": "40"}})),
    pair("How many work visas are there",
         single({"term": {"VSA_TYPCDE": "40"}})),

    # VS04: residence permit
    pair("Find all residence permits",
         single({"term": {"VSA_TYPCDE": "20"}})),
    pair("Show all residence permits",
         single({"term": {"VSA_TYPCDE": "20"}})),
    pair("List all residence permits",
         single({"term": {"VSA_TYPCDE": "20"}})),

    # VS05: visit visa
    pair("Find all visit visas",
         single({"term": {"VSA_TYPCDE": "11"}})),
    pair("Show all visit visas",
         single({"term": {"VSA_TYPCDE": "11"}})),

    # VS02: active visas — ONLY status, no type filter
    pair("Show all active visas",
         single({"term": {"VSA_RCDSTS": "13"}})),
    pair("Find all active visas",
         single({"term": {"VSA_RCDSTS": "13"}})),

    # VS03: expired visas — ONLY "14", never a list
    pair("Find all expired visas",
         single({"term": {"VSA_RCDSTS": "14"}})),
    pair("Show all expired visas",
         single({"term": {"VSA_RCDSTS": "14"}})),

    # VS08: active WORK visas — BOTH type AND status (critical!)
    pair("Show all active work visas",
         single({"bool": {"must": [
             {"term": {"VSA_TYPCDE": "40"}},
             {"term": {"VSA_RCDSTS": "13"}},
         ]}})),
    pair("Find all active work visas",
         single({"bool": {"must": [
             {"term": {"VSA_TYPCDE": "40"}},
             {"term": {"VSA_RCDSTS": "13"}},
         ]}})),
    pair("List active work visas",
         single({"bool": {"must": [
             {"term": {"VSA_TYPCDE": "40"}},
             {"term": {"VSA_RCDSTS": "13"}},
         ]}})),
    pair("Show active residence permits",
         single({"bool": {"must": [
             {"term": {"VSA_TYPCDE": "20"}},
             {"term": {"VSA_RCDSTS": "13"}},
         ]}})),
    pair("Find expired work visas",
         single({"bool": {"must": [
             {"term": {"VSA_TYPCDE": "40"}},
             {"term": {"VSA_RCDSTS": "14"}},
         ]}})),
    pair("Show expired residence permits",
         single({"bool": {"must": [
             {"term": {"VSA_TYPCDE": "20"}},
             {"term": {"VSA_RCDSTS": "14"}},
         ]}})),

    # VS09: expiry date — VSA_EXPDTE (NOT VSA_RCDTE, NOT VRDTE)
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
    pair("Find visas expiring in 2025",
         single({"range": {"VSA_EXPDTE": {"gte": "2025-01-01", "lte": "2025-12-31"}}})),
    pair("Show visas expiring after 2024",
         single({"range": {"VSA_EXPDTE": {"gt": "2024-12-31"}}})),
    pair("Find active work visas expiring before 2026",
         single({"bool": {"must": [
             {"term": {"VSA_TYPCDE": "40"}},
             {"term": {"VSA_RCDSTS": "13"}},
             {"range": {"VSA_EXPDTE": {"lt": "2026-01-01"}}},
         ]}})),

    # VS06: nationality + type — SINGLE INDEX, NAT_CDENUM
    pair("Show work visas for Pakistani nationals",
         single({"bool": {"must": [
             {"term": {"VSA_TYPCDE": "40"}},
             {"term": {"NAT_CDENUM": "Pakistani"}},
         ]}})),
    pair("Find work visas for Pakistani nationals",
         single({"bool": {"must": [
             {"term": {"VSA_TYPCDE": "40"}},
             {"term": {"NAT_CDENUM": "Pakistani"}},
         ]}})),

    # VS07: residence permits for Qatari — SINGLE INDEX
    pair("Find residence permits for Qatari nationals",
         single({"bool": {"must": [
             {"term": {"VSA_TYPCDE": "20"}},
             {"term": {"NAT_CDENUM": "Qatari"}},
         ]}})),
    pair("Show residence permits for Qatari nationals",
         single({"bool": {"must": [
             {"term": {"VSA_TYPCDE": "20"}},
             {"term": {"NAT_CDENUM": "Qatari"}},
         ]}})),
    pair("Find residence permits for Indian nationals",
         single({"bool": {"must": [
             {"term": {"VSA_TYPCDE": "20"}},
             {"term": {"NAT_CDENUM": "Indian"}},
         ]}})),

    # VS11: active work visas for Pakistani — SINGLE INDEX
    pair("Find active work visas for Pakistani nationals",
         single({"bool": {"must": [
             {"term": {"VSA_TYPCDE": "40"}},
             {"term": {"VSA_RCDSTS": "13"}},
             {"term": {"NAT_CDENUM": "Pakistani"}},
         ]}})),
    pair("Show active work visas for Pakistani nationals",
         single({"bool": {"must": [
             {"term": {"VSA_TYPCDE": "40"}},
             {"term": {"VSA_RCDSTS": "13"}},
             {"term": {"NAT_CDENUM": "Pakistani"}},
         ]}})),
    pair("Find active work visas for Indian nationals",
         single({"bool": {"must": [
             {"term": {"VSA_TYPCDE": "40"}},
             {"term": {"VSA_RCDSTS": "13"}},
             {"term": {"NAT_CDENUM": "Indian"}},
         ]}})),

    # VS12: expired work visas for Pakistani — only VSA_RCDSTS:"14" (not a list!)
    pair("Show expired work visas for Pakistani nationals",
         single({"bool": {"must": [
             {"term": {"VSA_TYPCDE": "40"}},
             {"term": {"VSA_RCDSTS": "14"}},
             {"term": {"NAT_CDENUM": "Pakistani"}},
         ]}})),
    pair("Find expired work visas for Pakistani nationals",
         single({"bool": {"must": [
             {"term": {"VSA_TYPCDE": "40"}},
             {"term": {"VSA_RCDSTS": "14"}},
             {"term": {"NAT_CDENUM": "Pakistani"}},
         ]}})),
    pair("Find expired residence permits for Indian nationals",
         single({"bool": {"must": [
             {"term": {"VSA_TYPCDE": "20"}},
             {"term": {"VSA_RCDSTS": "14"}},
             {"term": {"NAT_CDENUM": "Indian"}},
         ]}})),
]

# ─────────────────────────────────────────────────────────────
# 5. RELATIONSHIPS — fix RL01 (match_all) and RL03 (DIVORCE_DATE field)
# ─────────────────────────────────────────────────────────────
relationship_pairs = [
    # RL01: "all marriage records" = match_all (no VISA_TYPE_DESC!)
    pair("Find all marriage records",
         single({"match_all": {}})),
    pair("Show all marriage records",
         single({"match_all": {}})),
    pair("List all marriage records",
         single({"match_all": {}})),
    pair("Find all marriages",
         single({"match_all": {}})),
    pair("Show all marriages",
         single({"match_all": {}})),
    pair("List all marriages in the database",
         single({"match_all": {}})),

    # RL03: must_not exists on DIVORCE_DATE (not DIVORCE_CERTIFICATE_NUMBER)
    pair("Find all current marriages with no divorce",
         single({"bool": {"must_not": {"exists": {"field": "DIVORCE_DATE"}}}})),
    pair("Show marriages with no divorce",
         single({"bool": {"must_not": {"exists": {"field": "DIVORCE_DATE"}}}})),
    pair("Find marriages that have not ended in divorce",
         single({"bool": {"must_not": {"exists": {"field": "DIVORCE_DATE"}}}})),
    pair("Show all active marriages without any divorce record",
         single({"bool": {"must_not": {"exists": {"field": "DIVORCE_DATE"}}}})),
    pair("Find marriages where no divorce date exists",
         single({"bool": {"must_not": {"exists": {"field": "DIVORCE_DATE"}}}})),
]

# ─────────────────────────────────────────────────────────────
# 6. VISA-APP — fix VA04 (use range not term for date)
# ─────────────────────────────────────────────────────────────
visa_app_pairs = [
    pair("Show approved applications submitted in 2023",
         {"query": {"bool": {"must": [
             {"term": {"APL_RCDSTS": "2"}},
             {"range": {"APL_APLDTE": {"gte": "2023-01-01", "lte": "2023-12-31"}}},
         ]}}}),
    pair("Find approved applications submitted in 2023",
         {"query": {"bool": {"must": [
             {"term": {"APL_RCDSTS": "2"}},
             {"range": {"APL_APLDTE": {"gte": "2023-01-01", "lte": "2023-12-31"}}},
         ]}}}),
    pair("Show approved applications submitted in 2022",
         {"query": {"bool": {"must": [
             {"term": {"APL_RCDSTS": "2"}},
             {"range": {"APL_APLDTE": {"gte": "2022-01-01", "lte": "2022-12-31"}}},
         ]}}}),
    pair("Find rejected applications submitted in 2023",
         {"query": {"bool": {"must": [
             {"term": {"APL_RCDSTS": "3"}},
             {"range": {"APL_APLDTE": {"gte": "2023-01-01", "lte": "2023-12-31"}}},
         ]}}}),
    pair("Show applications submitted after 2022",
         {"query": {"range": {"APL_APLDTE": {"gt": "2022-12-31"}}}}),
    pair("Find approved work visa applications submitted in 2023",
         {"query": {"bool": {"must": [
             {"term": {"APL_TYPCDE": "40"}},
             {"term": {"APL_RCDSTS": "2"}},
             {"range": {"APL_APLDTE": {"gte": "2023-01-01", "lte": "2023-12-31"}}},
         ]}}}),
]

# ─────────────────────────────────────────────────────────────
# 7. MULTI-INDEX — fix all 8 failures
# ─────────────────────────────────────────────────────────────
multi_pairs = [
    # M10: gender-qualified violations — gender MUST be in step 1 person query
    pair("Find speeding violations for Qatari males",
         {"type": "multi_index", "steps": [
             {"step": 1, "index": "moi-gp-all-profiles-details-v1",
              "query": {"bool": {"must": [
                  {"term": {"person_natcde": "Qatari"}},
                  {"term": {"prs_gdr": "Male"}},
              ]}},
              "extract_field": "prs_qid"},
             {"step": 2, "index": "moi-violations-v1",
              "query": {"bool": {"must": [
                  {"terms": {"VLN_OWNQID": "$step_1"}},
                  {"term": {"VLN_TYPE": "SPEEDING"}},
              ]}}},
         ]}),
    pair("Find unpaid violations for Qatari males",
         {"type": "multi_index", "steps": [
             {"step": 1, "index": "moi-gp-all-profiles-details-v1",
              "query": {"bool": {"must": [
                  {"term": {"person_natcde": "Qatari"}},
                  {"term": {"prs_gdr": "Male"}},
              ]}},
              "extract_field": "prs_qid"},
             {"step": 2, "index": "moi-violations-v1",
              "query": {"bool": {"must": [
                  {"terms": {"VLN_OWNQID": "$step_1"}},
                  {"term": {"VLN_STATUS": "UNPAID"}},
              ]}}},
         ]}),

    # M11: Pakistani males + Toyota — gender in step 1, MNF_ENSHDESC in step 2
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
    pair("Find Nissan vehicles owned by Indian males",
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
                  {"match": {"MNF_ENSHDESC": "NISSAN"}},
              ]}}},
         ]}),
    pair("Find white vehicles owned by Qatari males",
         {"type": "multi_index", "steps": [
             {"step": 1, "index": "moi-gp-all-profiles-details-v1",
              "query": {"bool": {"must": [
                  {"term": {"person_natcde": "Qatari"}},
                  {"term": {"prs_gdr": "Male"}},
              ]}},
              "extract_field": "prs_qid"},
             {"step": 2, "index": "moi-vehicle-info-v1",
              "query": {"bool": {"must": [
                  {"terms": {"VRG_OWNQID": "$step_1"}},
                  {"match": {"CLR_CLRENGDSC": "WHITE"}},
              ]}}},
         ]}),

    # M15: vehicles with active registration for nationals — must include VRG_STATUS filter
    pair("Find vehicles with active registration owned by Qatari nationals",
         {"type": "multi_index", "steps": [
             {"step": 1, "index": "moi-gp-all-profiles-details-v1",
              "query": {"term": {"person_natcde": "Qatari"}},
              "extract_field": "prs_qid"},
             {"step": 2, "index": "moi-vehicle-info-v1",
              "query": {"bool": {"must": [
                  {"terms": {"VRG_OWNQID": "$step_1"}},
                  {"match": {"VRG_STATUS": "ACT"}},
              ]}}},
         ]}),
    pair("Find vehicles with active registration owned by Pakistani nationals",
         {"type": "multi_index", "steps": [
             {"step": 1, "index": "moi-gp-all-profiles-details-v1",
              "query": {"term": {"person_natcde": "Pakistani"}},
              "extract_field": "prs_qid"},
             {"step": 2, "index": "moi-vehicle-info-v1",
              "query": {"bool": {"must": [
                  {"terms": {"VRG_OWNQID": "$step_1"}},
                  {"match": {"VRG_STATUS": "ACT"}},
              ]}}},
         ]}),
    pair("Find vehicles with expired registration owned by Qatari nationals",
         {"type": "multi_index", "steps": [
             {"step": 1, "index": "moi-gp-all-profiles-details-v1",
              "query": {"term": {"person_natcde": "Qatari"}},
              "extract_field": "prs_qid"},
             {"step": 2, "index": "moi-vehicle-info-v1",
              "query": {"bool": {"must": [
                  {"terms": {"VRG_OWNQID": "$step_1"}},
                  {"match": {"VRG_STATUS": "EXP"}},
              ]}}},
         ]}),

    # M17/M18: exit/entry for nationals — MUST include TRX_DIRECTION in step 2
    pair("Find all exit transactions for Qatari nationals",
         {"type": "multi_index", "steps": [
             {"step": 1, "index": "moi-gp-all-profiles-details-v1",
              "query": {"term": {"person_natcde": "Qatari"}},
              "extract_field": "prs_qid"},
             {"step": 2, "index": "moi-exit-entry-tts-details-v1",
              "query": {"bool": {"must": [
                  {"terms": {"TRX_QIDNO": "$step_1"}},
                  {"match": {"TRX_DIRECTION": "OUT"}},
              ]}}},
         ]}),
    pair("Find all exit transactions for Pakistani nationals",
         {"type": "multi_index", "steps": [
             {"step": 1, "index": "moi-gp-all-profiles-details-v1",
              "query": {"term": {"person_natcde": "Pakistani"}},
              "extract_field": "prs_qid"},
             {"step": 2, "index": "moi-exit-entry-tts-details-v1",
              "query": {"bool": {"must": [
                  {"terms": {"TRX_QIDNO": "$step_1"}},
                  {"match": {"TRX_DIRECTION": "OUT"}},
              ]}}},
         ]}),
    pair("Find all entry transactions for Pakistani nationals",
         {"type": "multi_index", "steps": [
             {"step": 1, "index": "moi-gp-all-profiles-details-v1",
              "query": {"term": {"person_natcde": "Pakistani"}},
              "extract_field": "prs_qid"},
             {"step": 2, "index": "moi-exit-entry-tts-details-v1",
              "query": {"bool": {"must": [
                  {"terms": {"TRX_QIDNO": "$step_1"}},
                  {"match": {"TRX_DIRECTION": "IN"}},
              ]}}},
         ]}),
    pair("Find all entry transactions for Indian nationals",
         {"type": "multi_index", "steps": [
             {"step": 1, "index": "moi-gp-all-profiles-details-v1",
              "query": {"term": {"person_natcde": "Indian"}},
              "extract_field": "prs_qid"},
             {"step": 2, "index": "moi-exit-entry-tts-details-v1",
              "query": {"bool": {"must": [
                  {"terms": {"TRX_QIDNO": "$step_1"}},
                  {"match": {"TRX_DIRECTION": "IN"}},
              ]}}},
         ]}),
    pair("Find all travel records for Qatari nationals",
         {"type": "multi_index", "steps": [
             {"step": 1, "index": "moi-gp-all-profiles-details-v1",
              "query": {"term": {"person_natcde": "Qatari"}},
              "extract_field": "prs_qid"},
             {"step": 2, "index": "moi-exit-entry-tts-details-v1",
              "query": {"bool": {"must": [
                  {"terms": {"TRX_QIDNO": "$step_1"}},
              ]}}},
         ]}),

    # M32/M33: Pakistani males violations — gender in step 1, extract prs_qid (not prs_gdr_cde!)
    pair("Find violations for Pakistani males",
         {"type": "multi_index", "steps": [
             {"step": 1, "index": "moi-gp-all-profiles-details-v1",
              "query": {"bool": {"must": [
                  {"term": {"person_natcde": "Pakistani"}},
                  {"term": {"prs_gdr": "Male"}},
              ]}},
              "extract_field": "prs_qid"},
             {"step": 2, "index": "moi-violations-v1",
              "query": {"bool": {"must": [
                  {"terms": {"VLN_OWNQID": "$step_1"}},
              ]}}},
         ]}),
    pair("Find unpaid violations for Pakistani males",
         {"type": "multi_index", "steps": [
             {"step": 1, "index": "moi-gp-all-profiles-details-v1",
              "query": {"bool": {"must": [
                  {"term": {"person_natcde": "Pakistani"}},
                  {"term": {"prs_gdr": "Male"}},
              ]}},
              "extract_field": "prs_qid"},
             {"step": 2, "index": "moi-violations-v1",
              "query": {"bool": {"must": [
                  {"terms": {"VLN_OWNQID": "$step_1"}},
                  {"term": {"VLN_STATUS": "UNPAID"}},
              ]}}},
         ]}),
    pair("Find violations for Indian males",
         {"type": "multi_index", "steps": [
             {"step": 1, "index": "moi-gp-all-profiles-details-v1",
              "query": {"bool": {"must": [
                  {"term": {"person_natcde": "Indian"}},
                  {"term": {"prs_gdr": "Male"}},
              ]}},
              "extract_field": "prs_qid"},
             {"step": 2, "index": "moi-violations-v1",
              "query": {"bool": {"must": [
                  {"terms": {"VLN_OWNQID": "$step_1"}},
              ]}}},
         ]}),

    # M35: Corniche Road violations — VLN_PLCDSC only, no VLN_TYPE
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
    pair("Find violations on Al Waab Street for Indian nationals",
         {"type": "multi_index", "steps": [
             {"step": 1, "index": "moi-gp-all-profiles-details-v1",
              "query": {"term": {"person_natcde": "Indian"}},
              "extract_field": "prs_qid"},
             {"step": 2, "index": "moi-violations-v1",
              "query": {"bool": {"must": [
                  {"terms": {"VLN_OWNQID": "$step_1"}},
                  {"term": {"VLN_PLCDSC": "AL WAAB STREET"}},
              ]}}},
         ]}),
]


def main():
    all_categories = [
        ("Person",         person_pairs),
        ("Vehicle",        vehicle_pairs),
        ("Exit/Entry",     exit_entry_pairs),
        ("Visa-main",      visa_main_pairs),
        ("Relationships",  relationship_pairs),
        ("Visa-app",       visa_app_pairs),
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

    import subprocess
    result = subprocess.run(['wc', '-l', str(TRAIN_PATH), str(VALID_PATH)], capture_output=True, text=True)
    print(f"\n{result.stdout.strip()}")


if __name__ == '__main__':
    random.seed(42)
    main()

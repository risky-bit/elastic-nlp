#!/usr/bin/env python3
"""
Build ground truth for the v2 test corpus.

For each query ID, runs the CORRECT DSL against real ES indices to get
expected_count. This is the evaluation baseline: correct = model count matches.

Key rules applied:
  - text fields need match/match_phrase; keyword/numeric fields use term
  - VISA_TYPE_DESC is text with OR match — use VSA_TYPCDE codes instead
  - VRG_STATUS is text — use match not term
  - BORDER_CODE_DESC, TRX_TRIP_TYP_DESC, TRX_DIRECTION are text — use match
  - Nationality codes: Qatari=634, Pakistani=586, Indian=356, Egyptian=818,
    Nepali=524, Sri Lankan=144, UAE=784
  - APL_RCDSTS: "2"=approved, "3"=rejected
  - VSA_RCDSTS: "13"=active, "14"=expired
  - VSA_TYPCDE: "40"=Work Visa, "20"=Residence Permit, "11"=Visit Visa
  - SPONSOR_TYPE: "2"=company, "1"=individual

Output: data/ground_truth.json
"""

import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(REPO_ROOT))

from src.config import Config
from src.es_client import ESClient


CORRECT_DSLS = {

    # ── PERSON (moi-gp-all-profiles-details-v1) ────────────────────────────
    "P01": ("moi-gp-all-profiles-details-v1", {"query": {"match": {"CL_person_full_name_en": "Ahmed"}}}),
    "P02": ("moi-gp-all-profiles-details-v1", {"query": {"term": {"person_natcde": "634"}}}),
    "P03": ("moi-gp-all-profiles-details-v1", {"query": {"term": {"prs_gdr": "Female"}}}),
    "P04": ("moi-gp-all-profiles-details-v1", {"query": {"term": {"prs_gdr": "Male"}}}),
    "P05": ("moi-gp-all-profiles-details-v1", {"query": {"bool": {"must": [{"term": {"person_natcde": "586"}}, {"term": {"prs_gdr": "Female"}}]}}}),
    "P06": ("moi-gp-all-profiles-details-v1", {"query": {"bool": {"must": [{"term": {"person_natcde": "634"}}, {"term": {"prs_gdr": "Male"}}]}}}),
    "P07": ("moi-gp-all-profiles-details-v1", {"query": {"term": {"person_natcde": "356"}}}),
    "P08": ("moi-gp-all-profiles-details-v1", {"query": {"range": {"prs_dob": {"gte": "1990-01-01"}}}}),
    "P09": ("moi-gp-all-profiles-details-v1", {"query": {"bool": {"must": [{"term": {"person_natcde": "634"}}, {"term": {"prs_gdr": "Male"}}, {"range": {"prs_dob": {"gte": "1980-01-01", "lte": "1990-12-31"}}}]}}}),
    "P10": ("moi-gp-all-profiles-details-v1", {"query": {"bool": {"must": [{"term": {"person_natcde": "586"}}, {"term": {"prs_gdr": "Female"}}, {"range": {"prs_dob": {"gte": "1985-01-01"}}}]}}}),
    "P11": ("moi-gp-all-profiles-details-v1", {"query": {"bool": {"must": [{"term": {"prs_gdr": "Male"}}, {"bool": {"should": [{"term": {"person_natcde": "356"}}, {"term": {"person_natcde": "586"}}]}}]}}}),
    "P12": ("moi-gp-all-profiles-details-v1", {"query": {"bool": {"must": [{"term": {"person_natcde": "634"}}, {"term": {"prs_gdr": "Female"}}, {"range": {"prs_dob": {"gte": "1985-01-01", "lte": "2000-12-31"}}}]}}}),
    "P13": ("moi-gp-all-profiles-details-v1", {"query": {"term": {"person_natcde": "818"}}}),
    "P14": ("moi-gp-all-profiles-details-v1", {"query": {"bool": {"must": [{"term": {"prs_gdr": "Male"}}, {"range": {"prs_dob": {"gte": "2000-01-01"}}}]}}}),
    "P15": ("moi-gp-all-profiles-details-v1", {"query": {"bool": {"should": [{"term": {"person_natcde": "524"}}, {"term": {"person_natcde": "144"}}]}}}),

    # ── VEHICLE (moi-vehicle-info-v1) ──────────────────────────────────────
    # ALL string fields are text type → use match not term
    "V01": ("moi-vehicle-info-v1", {"query": {"match": {"VRG_PLTNUM": "A12345"}}}),
    "V02": ("moi-vehicle-info-v1", {"query": {"match": {"MNF_ENSHDESC": "TOYOTA"}}}),
    "V03": ("moi-vehicle-info-v1", {"query": {"match": {"CLR_CLRENGDSC": "WHITE"}}}),
    "V04": ("moi-vehicle-info-v1", {"query": {"match": {"VRG_STATUS": "ACT"}}}),
    "V05": ("moi-vehicle-info-v1", {"query": {"bool": {"must": [{"match": {"MNF_ENSHDESC": "TOYOTA"}}, {"match": {"CLR_CLRENGDSC": "WHITE"}}]}}}),
    "V06": ("moi-vehicle-info-v1", {"query": {"bool": {"must": [{"match": {"MNF_ENSHDESC": "TOYOTA"}}, {"range": {"VRG_STADTE": {"gte": "2022-01-01", "lte": "2022-12-31"}}}]}}}),
    "V07": ("moi-vehicle-info-v1", {"query": {"bool": {"must": [{"match": {"CLR_CLRENGDSC": "BLACK"}}, {"match": {"VRG_STATUS": "EXP"}}]}}}),
    "V08": ("moi-vehicle-info-v1", {"query": {"bool": {"must": [{"match": {"MNF_ENSHDESC": "NISSAN"}}, {"match": {"CLR_CLRENGDSC": "SILVER"}}]}}}),
    "V09": ("moi-vehicle-info-v1", {"query": {"bool": {"must": [{"match": {"MNF_ENSHDESC": "TOYOTA"}}, {"match": {"CLR_CLRENGDSC": "WHITE"}}, {"match": {"VEH_MODEL": "CAMRY"}}, {"range": {"VRG_STADTE": {"gte": "2020-01-01", "lte": "2023-12-31"}}}]}}}),
    "V10": ("moi-vehicle-info-v1", {"query": {"range": {"VRG_ENDDT": {"lt": "2024-01-01"}}}}),
    "V11": ("moi-vehicle-info-v1", {"query": {"bool": {"must": [{"bool": {"should": [{"match": {"MNF_ENSHDESC": "TOYOTA"}}, {"match": {"MNF_ENSHDESC": "NISSAN"}}]}}, {"bool": {"should": [{"match": {"CLR_CLRENGDSC": "WHITE"}}, {"match": {"CLR_CLRENGDSC": "SILVER"}}]}}]}}}),
    "V12": ("moi-vehicle-info-v1", {"query": {"bool": {"must": [{"match": {"MNF_ENSHDESC": "BMW"}}, {"match": {"CLR_CLRENGDSC": "BLACK"}}, {"match": {"VRG_STATUS": "EXP"}}]}}}),
    "V13": ("moi-vehicle-info-v1", {"query": {"range": {"VRG_STADTE": {"gte": "2023-01-01", "lte": "2023-12-31"}}}}),
    "V14": ("moi-vehicle-info-v1", {"query": {"match": {"MNF_ENSHDESC": "KIA"}}}),
    "V15": ("moi-vehicle-info-v1", {"query": {"bool": {"must": [{"match": {"CLR_CLRENGDSC": "SILVER"}}, {"match": {"VRG_STATUS": "ACT"}}]}}}),

    # ── VIOLATIONS (moi-violations-v1) ─────────────────────────────────────
    # VLN_TYPE, VLN_STATUS, VLN_PLCDSC, VLN_YEAR are keyword fields → term ok
    "N01": ("moi-violations-v1", {"query": {"term": {"VLN_TYPE": "SPEEDING"}}}),
    "N02": ("moi-violations-v1", {"query": {"term": {"VLN_STATUS": "UNPAID"}}}),
    "N03": ("moi-violations-v1", {"query": {"term": {"VLN_PLCDSC": "CORNICHE ROAD"}}}),
    "N04": ("moi-violations-v1", {"query": {"term": {"VLN_TYPE": "RED_LIGHT"}}}),
    "N05": ("moi-violations-v1", {"query": {"bool": {"must": [{"term": {"VLN_STATUS": "UNPAID"}}, {"term": {"VLN_TYPE": "SPEEDING"}}]}}}),
    "N06": ("moi-violations-v1", {"query": {"term": {"VLN_PLCDSC": "AL WAAB STREET"}}}),
    "N07": ("moi-violations-v1", {"query": {"bool": {"must": [{"term": {"VLN_TYPE": "PARKING"}}, {"term": {"VLN_STATUS": "PAID"}}]}}}),
    "N08": ("moi-violations-v1", {"query": {"range": {"VLN_TOTAMT": {"gt": 1000}}}}),
    "N09": ("moi-violations-v1", {"query": {"bool": {"must": [{"term": {"VLN_STATUS": "UNPAID"}}, {"term": {"VLN_TYPE": "SPEEDING"}}, {"term": {"VLN_PLCDSC": "CORNICHE ROAD"}}]}}}),
    "N10": ("moi-violations-v1", {"query": {"bool": {"must": [{"term": {"VLN_STATUS": "UNPAID"}}, {"term": {"VLN_YEAR": "2024"}}]}}}),
    "N11": ("moi-violations-v1", {"query": {"bool": {"must": [{"term": {"VLN_TYPE": "RED_LIGHT"}}, {"term": {"VLN_PLCDSC": "AL RAYYAN ROAD"}}]}}}),
    "N12": ("moi-violations-v1", {"query": {"bool": {"must": [{"term": {"VLN_STATUS": "UNPAID"}}, {"range": {"VLN_TOTAMT": {"gt": 1000}}}]}}}),
    "N13": ("moi-violations-v1", {"query": {"term": {"VLN_TYPE": "PARKING"}}}),
    "N14": ("moi-violations-v1", {"query": {"term": {"VLN_PLCDSC": "SALWA ROAD"}}}),
    "N15": ("moi-violations-v1", {"query": {"term": {"VLN_TYPE": "MOBILE_PHONE"}}}),
    "N16": ("moi-violations-v1", {"query": {"bool": {"must": [{"term": {"VLN_TYPE": "SPEEDING"}}, {"term": {"VLN_STATUS": "PAID"}}, {"term": {"VLN_YEAR": "2023"}}]}}}),

    # ── EXIT/ENTRY (moi-exit-entry-tts-details-v1) ─────────────────────────
    # ALL string fields are text → use match
    "E01": ("moi-exit-entry-tts-details-v1", {"query": {"match": {"TRX_DIRECTION": "OUT"}}}),
    "E02": ("moi-exit-entry-tts-details-v1", {"query": {"match": {"TRX_DIRECTION": "IN"}}}),
    "E03": ("moi-exit-entry-tts-details-v1", {"query": {"bool": {"must": [{"match": {"TRX_TRIP_TYP_DESC": "FLIGHT"}}, {"match": {"BORDER_CODE_DESC": "HAMAD INTERNATIONAL AIRPORT"}}]}}}),
    "E04": ("moi-exit-entry-tts-details-v1", {"query": {"match": {"TRX_TRIP_TYP_DESC": "LAND"}}}),
    "E05": ("moi-exit-entry-tts-details-v1", {"query": {"bool": {"must": [{"match": {"TRX_DIRECTION": "IN"}}, {"match": {"BORDER_CODE_DESC": "DOHA PORT"}}]}}}),
    "E06": ("moi-exit-entry-tts-details-v1", {"query": {"range": {"TRX_DATE": {"gte": "2024-01-01", "lte": "2024-12-31"}}}}),
    "E07": ("moi-exit-entry-tts-details-v1", {"query": {"bool": {"must": [{"match": {"TRX_DIRECTION": "OUT"}}, {"match": {"BORDER_CODE_DESC": "ABU SAMRA BORDER"}}]}}}),
    "E08": ("moi-exit-entry-tts-details-v1", {"query": {"bool": {"must": [{"match": {"TRX_DIRECTION": "IN"}}, {"match": {"TRX_TRIP_TYP_DESC": "FLIGHT"}}, {"range": {"TRX_DATE": {"gte": "2023-01-01", "lte": "2023-12-31"}}}]}}}),
    "E09": ("moi-exit-entry-tts-details-v1", {"query": {"bool": {"must": [{"match": {"TRX_DIRECTION": "IN"}}, {"match": {"BORDER_CODE_DESC": "HAMAD INTERNATIONAL AIRPORT"}}, {"range": {"TRX_DATE": {"gte": "2024-01-01", "lte": "2024-12-31"}}}]}}}),
    "E10": ("moi-exit-entry-tts-details-v1", {"query": {"bool": {"must": [{"match": {"TRX_DIRECTION": "OUT"}}, {"match": {"TRX_TRIP_TYP_DESC": "FLIGHT"}}, {"range": {"TRX_DATE": {"gte": "2024-01-01", "lte": "2024-12-31"}}}]}}}),
    "E11": ("moi-exit-entry-tts-details-v1", {"query": {"bool": {"must": [{"match": {"TRX_DIRECTION": "IN"}}, {"match": {"BORDER_CODE_DESC": "DOHA PORT"}}]}}}),
    "E12": ("moi-exit-entry-tts-details-v1", {"query": {"bool": {"must": [{"match": {"BORDER_CODE_DESC": "ABU SAMRA BORDER"}}, {"range": {"TRX_DATE": {"gte": "2024-01-01", "lte": "2024-12-31"}}}]}}}),

    # ── VISA-MAIN (moi-visa-main-details-v1) ───────────────────────────────
    # VISA_TYPE_DESC is text with OR match — use VSA_TYPCDE codes instead:
    #   "40"=Work Visa, "20"=Residence Permit, "11"=Visit Visa
    # VSA_RCDSTS: "13"=active, "14"=expired  (keyword field → term ok)
    # NAT_CDENUM: numeric string → term ok
    "VS01": ("moi-visa-main-details-v1", {"query": {"term": {"VSA_TYPCDE": "40"}}}),
    "VS02": ("moi-visa-main-details-v1", {"query": {"term": {"VSA_RCDSTS": "13"}}}),
    "VS03": ("moi-visa-main-details-v1", {"query": {"term": {"VSA_RCDSTS": "14"}}}),
    "VS04": ("moi-visa-main-details-v1", {"query": {"term": {"VSA_TYPCDE": "20"}}}),
    "VS05": ("moi-visa-main-details-v1", {"query": {"term": {"VSA_TYPCDE": "11"}}}),
    "VS06": ("moi-visa-main-details-v1", {"query": {"bool": {"must": [{"term": {"NAT_CDENUM": "586"}}, {"term": {"VSA_TYPCDE": "40"}}]}}}),
    "VS07": ("moi-visa-main-details-v1", {"query": {"bool": {"must": [{"term": {"NAT_CDENUM": "634"}}, {"term": {"VSA_TYPCDE": "20"}}]}}}),
    "VS08": ("moi-visa-main-details-v1", {"query": {"bool": {"must": [{"term": {"VSA_TYPCDE": "40"}}, {"term": {"VSA_RCDSTS": "13"}}]}}}),
    "VS09": ("moi-visa-main-details-v1", {"query": {"bool": {"must": [{"term": {"VSA_TYPCDE": "40"}}, {"range": {"VSA_EXPDTE": {"lt": "2026-01-01"}}}]}}}),
    "VS10": ("moi-visa-main-details-v1", {"query": {"range": {"VSA_ISSDTE": {"gte": "2022-01-01", "lte": "2022-12-31"}}}}),
    "VS11": ("moi-visa-main-details-v1", {"query": {"bool": {"must": [{"term": {"NAT_CDENUM": "586"}}, {"term": {"VSA_TYPCDE": "40"}}, {"term": {"VSA_RCDSTS": "13"}}]}}}),
    "VS12": ("moi-visa-main-details-v1", {"query": {"bool": {"must": [{"term": {"NAT_CDENUM": "586"}}, {"term": {"VSA_TYPCDE": "40"}}, {"term": {"VSA_RCDSTS": "14"}}]}}}),

    # ── VISA-APPLICATION (moi-visa-application-details-v1) ─────────────────
    # APL_RCDSTS: "2"=approved, "3"=rejected  (keyword → term ok)
    # APL_TYPCDE: "40"=work visa application
    "VA01": ("moi-visa-application-details-v1", {"query": {"term": {"APL_RCDSTS": "2"}}}),
    "VA02": ("moi-visa-application-details-v1", {"query": {"term": {"APL_RCDSTS": "3"}}}),
    "VA03": ("moi-visa-application-details-v1", {"query": {"term": {"APL_TYPCDE": "40"}}}),
    "VA04": ("moi-visa-application-details-v1", {"query": {"bool": {"must": [{"term": {"APL_RCDSTS": "2"}}, {"range": {"APL_APLDTE": {"gte": "2023-01-01", "lte": "2023-12-31"}}}]}}}),
    "VA05": ("moi-visa-application-details-v1", {"query": {"range": {"REM_TOT_APPR": {"gt": 10}}}}),
    "VA06": ("moi-visa-application-details-v1", {"query": {"range": {"APL_EXPDTE": {"lt": "2026-01-01"}}}}),
    "VA07": ("moi-visa-application-details-v1", {"query": {"bool": {"must": [{"term": {"APL_RCDSTS": "2"}}, {"term": {"APL_TYPCDE": "40"}}, {"range": {"REM_TOT_APPR": {"gt": 0}}}]}}}),

    # ── SPONSOR (moi-sponsor-details-v1) ───────────────────────────────────
    # MDS_DPTENGNAM is text → match; SPONSOR_TYPE is keyword → term
    "SP01": ("moi-sponsor-details-v1", {"query": {"match_all": {}}}),
    "SP02": ("moi-sponsor-details-v1", {"query": {"term": {"SPONSOR_TYPE": "2"}}}),
    "SP03": ("moi-sponsor-details-v1", {"query": {"term": {"SPONSOR_TYPE": "1"}}}),
    "SP04": ("moi-sponsor-details-v1", {"query": {"range": {"FIRST_ENTRY_DATE": {"gt": "2022-12-31"}}}}),
    "SP05": ("moi-sponsor-details-v1", {"query": {"range": {"FIRST_ENTRY_DATE": {"gte": "2022-01-01", "lt": "2023-01-01"}}}}),
    "SP06": ("moi-sponsor-details-v1", {"query": {"match": {"MDS_DPTENGNAM": "Expatriates Affairs Dept"}}}),
    "SP07": ("moi-sponsor-details-v1", {"query": {"bool": {"must": [{"term": {"SPONSOR_TYPE": "2"}}, {"range": {"FIRST_ENTRY_DATE": {"gt": "2021-12-31"}}}]}}}),
    "SP08": ("moi-sponsor-details-v1", {"query": {"range": {"FIRST_ENTRY_DATE": {"gte": "2023-01-01"}}}}),

    # ── RELATIONSHIPS (moi-relationship-details-v1) ────────────────────────
    "RL01": ("moi-relationship-details-v1", {"query": {"match_all": {}}}),
    "RL02": ("moi-relationship-details-v1", {"query": {"range": {"MARRIAGE_DATE": {"gt": "2018-12-31"}}}}),
    "RL03": ("moi-relationship-details-v1", {"query": {"bool": {"must_not": {"exists": {"field": "DIVORCE_DATE"}}}}}),
    "RL04": ("moi-relationship-details-v1", {"query": {"range": {"MARRIAGE_DATE": {"gte": "2015-01-01"}}}}),
    "RL05": ("moi-relationship-details-v1", {"query": {"exists": {"field": "DIVORCE_DATE"}}}),
    "RL06": ("moi-relationship-details-v1", {"query": {"range": {"MARRIAGE_DATE": {"gte": "2020-01-01"}}}}),
}


def run_count(index, dsl, es):
    try:
        res = es._client.count(index=index, body=dsl)
        return res["count"]
    except Exception as e:
        return f"ERROR: {e}"


def get_qids_by_nat(es, nat_code, size=500):
    """Get all QIDs for a nationality code from person index."""
    res = es._client.search(
        index="moi-gp-all-profiles-details-v1",
        body={"query": {"term": {"person_natcde": str(nat_code)}}, "_source": ["prs_qid"], "size": size}
    )
    return [h["_source"]["prs_qid"] for h in res["hits"]["hits"]]


def get_qids_by_nat_gender(es, nat_code, gender, size=500):
    """Get QIDs by nationality + gender."""
    res = es._client.search(
        index="moi-gp-all-profiles-details-v1",
        body={"query": {"bool": {"must": [{"term": {"person_natcde": str(nat_code)}}, {"term": {"prs_gdr": gender}}]}}, "_source": ["prs_qid"], "size": size}
    )
    return [h["_source"]["prs_qid"] for h in res["hits"]["hits"]]


def count_violations_for_qids(es, qids):
    if not qids:
        return 0
    return run_count("moi-violations-v1", {"query": {"terms": {"VLN_OWNQID": qids}}}, es)


def count_vehicles_for_qids(es, qids):
    if not qids:
        return 0
    return run_count("moi-vehicle-info-v1", {"query": {"terms": {"VRG_OWNQID": qids}}}, es)


def count_exits_for_qids(es, qids):
    if not qids:
        return 0
    return run_count("moi-exit-entry-tts-details-v1", {"query": {"terms": {"TRX_QIDNO": qids}}}, es)


def count_visas_for_qids(es, qids):
    if not qids:
        return 0
    return run_count("moi-visa-main-details-v1", {"query": {"terms": {"HLD_QIDNO": qids}}}, es)


def main():
    config = Config()
    es = ESClient(config)
    es.connect()

    ground_truth = {}

    print("Computing expected counts from correct DSLs...")
    print(f"{'ID':<6} {'Expected':>8}  Query / Note")
    print("-" * 70)

    for qid, (index, dsl) in sorted(CORRECT_DSLS.items()):
        count = run_count(index, dsl, es)
        print(f"{qid:<6} {str(count):>8}  {json.dumps(dsl)[:60]}")
        ground_truth[qid] = {
            "expected_count": count,
            "correct_dsl": dsl,
            "index": index,
        }

    # ── Multi-index: compute from joins ───────────────────────────────────
    print("\nComputing multi-index expected counts via joins...")

    qatari  = get_qids_by_nat(es, "634")
    pak     = get_qids_by_nat(es, "586")
    indian  = get_qids_by_nat(es, "356")
    egyptian = get_qids_by_nat(es, "818")

    qatari_male   = get_qids_by_nat_gender(es, "634", "Male")
    qatari_female = get_qids_by_nat_gender(es, "634", "Female")
    pak_male      = get_qids_by_nat_gender(es, "586", "Male")

    def vln_filter(qids, extra=None):
        """Count violations for qids, with optional extra filter."""
        if not qids:
            return 0
        q = {"bool": {"must": [{"terms": {"VLN_OWNQID": qids}}]}}
        if extra:
            q["bool"]["must"].extend(extra)
        return run_count("moi-violations-v1", {"query": q}, es)

    def veh_filter(qids, extra=None):
        if not qids:
            return 0
        q = {"bool": {"must": [{"terms": {"VRG_OWNQID": qids}}]}}
        if extra:
            q["bool"]["must"].extend(extra)
        return run_count("moi-vehicle-info-v1", {"query": q}, es)

    def exit_filter(qids, extra=None):
        if not qids:
            return 0
        q = {"bool": {"must": [{"terms": {"TRX_QIDNO": qids}}]}}
        if extra:
            q["bool"]["must"].extend(extra)
        return run_count("moi-exit-entry-tts-details-v1", {"query": q}, es)

    def visa_filter(qids, extra=None):
        if not qids:
            return 0
        q = {"bool": {"must": [{"terms": {"HLD_QIDNO": qids}}]}}
        if extra:
            q["bool"]["must"].extend(extra)
        return run_count("moi-visa-main-details-v1", {"query": q}, es)

    def sponsor_filter(qids, field="SPONSOR_QID", extra=None):
        if not qids:
            return 0
        q = {"bool": {"must": [{"terms": {field: qids}}]}}
        if extra:
            q["bool"]["must"].extend(extra)
        return run_count("moi-sponsor-details-v1", {"query": q}, es)

    multi = {
        # violations × nationality
        "M01": ("Find all violations for Qatari nationals",          vln_filter(qatari)),
        "M02": ("Find all violations for Pakistani nationals",        vln_filter(pak)),
        # vehicles × nationality
        "M03": ("Find all vehicles owned by Qatari nationals",       veh_filter(qatari)),
        "M04": ("Find all vehicles owned by Indian nationals",        veh_filter(indian)),
        # violations × nationality + type/status
        "M05": ("Find speeding violations for Qatari nationals",     vln_filter(qatari, [{"term": {"VLN_TYPE": "SPEEDING"}}])),
        "M06": ("Find unpaid violations for Pakistani nationals",     vln_filter(pak, [{"term": {"VLN_STATUS": "UNPAID"}}])),
        "M07": ("Find Toyota vehicles owned by Pakistani nationals",  veh_filter(pak, [{"match": {"MNF_ENSHDESC": "TOYOTA"}}])),
        "M08": ("Find vehicles with expired reg owned by Indian",     veh_filter(indian, [{"match": {"VRG_STATUS": "EXP"}}])),
        "M09": ("Find unpaid speeding violations for Qatari",        vln_filter(qatari, [{"term": {"VLN_TYPE": "SPEEDING"}}, {"term": {"VLN_STATUS": "UNPAID"}}])),
        "M10": ("Find speeding violations for Qatari males",         vln_filter(qatari_male, [{"term": {"VLN_TYPE": "SPEEDING"}}])),
        "M11": ("Find Toyota vehicles owned by Pakistani males",      veh_filter(pak_male, [{"match": {"MNF_ENSHDESC": "TOYOTA"}}])),
        "M12": ("Find white vehicles owned by Qatari nationals",     veh_filter(qatari, [{"match": {"CLR_CLRENGDSC": "WHITE"}}])),
        "M13": ("Find red light violations for Indian nationals",     vln_filter(indian, [{"term": {"VLN_TYPE": "RED_LIGHT"}}])),
        "M14": ("Find paid violations for Qatari nationals",         vln_filter(qatari, [{"term": {"VLN_STATUS": "PAID"}}])),
        "M15": ("Find vehicles with active reg owned by Qatari",     veh_filter(qatari, [{"match": {"VRG_STATUS": "ACT"}}])),
        "M16": ("Find unpaid violations for Egyptian nationals",     vln_filter(egyptian, [{"term": {"VLN_STATUS": "UNPAID"}}])),
        # exit/entry × nationality
        "M17": ("Find all exit transactions for Qatari nationals",   exit_filter(qatari, [{"match": {"TRX_DIRECTION": "OUT"}}])),
        "M18": ("Find all entry transactions for Pakistani",         exit_filter(pak, [{"match": {"TRX_DIRECTION": "IN"}}])),
        "M19": ("Find all travel records for Indian nationals",      exit_filter(indian)),
        "M20": ("Find flight exits for Qatari nationals",           exit_filter(qatari, [{"match": {"TRX_DIRECTION": "OUT"}}, {"match": {"TRX_TRIP_TYP_DESC": "FLIGHT"}}])),
        "M21": ("Find entries via Hamad Airport for Pakistani",      exit_filter(pak, [{"match": {"TRX_DIRECTION": "IN"}}, {"match": {"BORDER_CODE_DESC": "HAMAD INTERNATIONAL AIRPORT"}}])),
        "M22": ("Find exit transactions in 2024 for Qatari",        exit_filter(qatari, [{"match": {"TRX_DIRECTION": "OUT"}}, {"range": {"TRX_DATE": {"gte": "2024-01-01", "lte": "2024-12-31"}}}])),
        "M23": ("Find flight entries for Indian nationals in 2024",  exit_filter(indian, [{"match": {"TRX_DIRECTION": "IN"}}, {"match": {"TRX_TRIP_TYP_DESC": "FLIGHT"}}, {"range": {"TRX_DATE": {"gte": "2024-01-01"}}}])),
        # visas × nationality
        "M24": ("Find all work visas held by Pakistani nationals",   visa_filter(pak, [{"term": {"VSA_TYPCDE": "40"}}])),
        "M25": ("Find all residence permits held by Qatari",        visa_filter(qatari, [{"term": {"VSA_TYPCDE": "20"}}])),
        "M26": ("Find active work visas held by Pakistani",         visa_filter(pak, [{"term": {"VSA_TYPCDE": "40"}}, {"term": {"VSA_RCDSTS": "13"}}])),
        "M27": ("Find expired visas held by Pakistani nationals",    visa_filter(pak, [{"term": {"VSA_RCDSTS": "14"}}])),
        "M28": ("Find work visas held by Pakistani males",           visa_filter(pak_male, [{"term": {"VSA_TYPCDE": "40"}}])),
        # sponsor × nationality
        "M29": ("Find all persons sponsored by Qatari nationals",   sponsor_filter(qatari)),
        "M30": ("Find all persons sponsored by Pakistani",          sponsor_filter(pak)),
        "M31": ("Find persons sponsored by Qatari males",           sponsor_filter(qatari_male)),
        # violations × gender join
        "M32": ("Find violations for Pakistani males",               vln_filter(pak_male)),
        "M33": ("Find unpaid violations for Pakistani males",        vln_filter(pak_male, [{"term": {"VLN_STATUS": "UNPAID"}}])),
        # vehicles × nationality
        "M34": ("Find Nissan vehicles owned by Indian nationals",    veh_filter(indian, [{"match": {"MNF_ENSHDESC": "NISSAN"}}])),
        "M35": ("Find violations on Corniche Road for Qatari",      vln_filter(qatari, [{"term": {"VLN_PLCDSC": "CORNICHE ROAD"}}])),
    }

    for qid, (note, count) in multi.items():
        print(f"{qid:<6} {str(count):>8}  {note}")
        ground_truth[qid] = {
            "expected_count": count,
            "correct_dsl": None,
            "index": "multi",
            "note": note,
        }

    out_path = REPO_ROOT / "data" / "ground_truth.json"
    with open(out_path, "w") as f:
        json.dump(ground_truth, f, indent=2)

    print(f"\nGround truth saved to: {out_path}  ({len(ground_truth)} entries)")


if __name__ == "__main__":
    main()

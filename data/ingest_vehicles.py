"""
Ingest test vehicle data into moi-vehicle-info-v1 for NLP testing.
Covers: Toyota, Nissan, KIA, BMW; white, silver, black; active/expired; various years.
"""

import json
from elasticsearch import Elasticsearch

es = Elasticsearch(
    ['http://localhost:9200'],
    basic_auth=('elastic', 'elastic'),
    request_timeout=10
)

INDEX = 'moi-vehicle-info-v1'

vehicles = [
    # Already ingested (will upsert safely)
    {"VRG_OWNQID": "TEST-00015", "MNF_ENSHDESC": "TOYOTA", "VEH_MODEL": "CAMRY",
     "VEH_MODELYEAR": "2020", "CLR_CLRENGDSC": "WHITE", "VRG_PLTNUM": "307859",
     "VRG_PLTTYPE": "PRT", "VRG_STADTE": "2022-01-10", "VRG_ENDDT": "2025-01-09", "VRG_STATUS": "ACT"},
    {"VRG_OWNQID": "TEST-00015", "MNF_ENSHDESC": "NISSAN", "VEH_MODEL": "PATROL",
     "VEH_MODELYEAR": "2022", "CLR_CLRENGDSC": "SILVER", "VRG_PLTNUM": "412300",
     "VRG_PLTTYPE": "PRT", "VRG_STADTE": "2022-01-15", "VRG_ENDDT": "2025-01-14", "VRG_STATUS": "ACT"},
    {"VRG_OWNQID": "TEST-00016", "MNF_ENSHDESC": "KIA", "VEH_MODEL": "SPORTAGE",
     "VEH_MODELYEAR": "2021", "CLR_CLRENGDSC": "BLACK", "VRG_PLTNUM": "209441",
     "VRG_PLTTYPE": "PRT", "VRG_STADTE": "2021-06-01", "VRG_ENDDT": "2024-05-31", "VRG_STATUS": "EXP"},
    {"VRG_OWNQID": "TEST-00017", "MNF_ENSHDESC": "TOYOTA", "VEH_MODEL": "LAND CRUISER",
     "VEH_MODELYEAR": "2019", "CLR_CLRENGDSC": "WHITE", "VRG_PLTNUM": "518822",
     "VRG_PLTTYPE": "PRT", "VRG_STADTE": "2019-11-20", "VRG_ENDDT": "2023-11-19", "VRG_STATUS": "EXP"},

    # New vehicles to cover corpus queries
    {"VRG_OWNQID": "TEST-00018", "MNF_ENSHDESC": "BMW", "VEH_MODEL": "X5",
     "VEH_MODELYEAR": "2021", "CLR_CLRENGDSC": "BLACK", "VRG_PLTNUM": "623100",
     "VRG_PLTTYPE": "PRT", "VRG_STADTE": "2021-03-15", "VRG_ENDDT": "2023-03-14", "VRG_STATUS": "EXP"},
    {"VRG_OWNQID": "TEST-00019", "MNF_ENSHDESC": "BMW", "VEH_MODEL": "7 SERIES",
     "VEH_MODELYEAR": "2022", "CLR_CLRENGDSC": "BLACK", "VRG_PLTNUM": "710045",
     "VRG_PLTTYPE": "PRT", "VRG_STADTE": "2022-07-01", "VRG_ENDDT": "2024-06-30", "VRG_STATUS": "EXP"},
    {"VRG_OWNQID": "TEST-00020", "MNF_ENSHDESC": "TOYOTA", "VEH_MODEL": "CAMRY",
     "VEH_MODELYEAR": "2021", "CLR_CLRENGDSC": "WHITE", "VRG_PLTNUM": "803421",
     "VRG_PLTTYPE": "PRT", "VRG_STADTE": "2022-05-10", "VRG_ENDDT": "2026-05-09", "VRG_STATUS": "ACT"},
    {"VRG_OWNQID": "TEST-00021", "MNF_ENSHDESC": "TOYOTA", "VEH_MODEL": "FORTUNER",
     "VEH_MODELYEAR": "2022", "CLR_CLRENGDSC": "WHITE", "VRG_PLTTYPE": "PRT",
     "VRG_PLTNUM": "904512", "VRG_STADTE": "2022-09-01", "VRG_ENDDT": "2026-08-31", "VRG_STATUS": "ACT"},
    {"VRG_OWNQID": "TEST-00022", "MNF_ENSHDESC": "NISSAN", "VEH_MODEL": "SUNNY",
     "VEH_MODELYEAR": "2020", "CLR_CLRENGDSC": "SILVER", "VRG_PLTNUM": "112233",
     "VRG_PLTTYPE": "PRT", "VRG_STADTE": "2020-04-01", "VRG_ENDDT": "2023-03-31", "VRG_STATUS": "EXP"},
    {"VRG_OWNQID": "TEST-00023", "MNF_ENSHDESC": "NISSAN", "VEH_MODEL": "ALTIMA",
     "VEH_MODELYEAR": "2022", "CLR_CLRENGDSC": "WHITE", "VRG_PLTNUM": "445566",
     "VRG_PLTTYPE": "PRT", "VRG_STADTE": "2022-06-15", "VRG_ENDDT": "2026-06-14", "VRG_STATUS": "ACT"},
    {"VRG_OWNQID": "TEST-00024", "MNF_ENSHDESC": "KIA", "VEH_MODEL": "SORENTO",
     "VEH_MODELYEAR": "2023", "CLR_CLRENGDSC": "WHITE", "VRG_PLTNUM": "556677",
     "VRG_PLTTYPE": "PVT", "VRG_STADTE": "2023-01-10", "VRG_ENDDT": "2026-12-31", "VRG_STATUS": "ACT"},
    {"VRG_OWNQID": "TEST-00025", "MNF_ENSHDESC": "TOYOTA", "VEH_MODEL": "CAMRY",
     "VEH_MODELYEAR": "2023", "CLR_CLRENGDSC": "SILVER", "VRG_PLTNUM": "667788",
     "VRG_PLTTYPE": "PRT", "VRG_STADTE": "2023-03-01", "VRG_ENDDT": "2027-02-28", "VRG_STATUS": "ACT"},
    {"VRG_OWNQID": "TEST-00026", "MNF_ENSHDESC": "TOYOTA", "VEH_MODEL": "HILUX",
     "VEH_MODELYEAR": "2019", "CLR_CLRENGDSC": "WHITE", "VRG_PLTNUM": "A12345",
     "VRG_PLTTYPE": "PRT", "VRG_STADTE": "2019-08-01", "VRG_ENDDT": "2022-07-31", "VRG_STATUS": "EXP"},
]

# Delete and recreate to avoid duplicates
try:
    es.delete_by_query(index=INDEX, body={'query': {'match_all': {}}}, refresh=True)
    print(f'Cleared existing docs from {INDEX}')
except Exception as e:
    print(f'Clear failed (OK if index empty): {e}')

for i, v in enumerate(vehicles):
    es.index(index=INDEX, id=str(i+1), document=v, refresh=True)

count = es.count(index=INDEX)['count']
print(f'Ingested {len(vehicles)} vehicles. Total in index: {count}')
print('Breakdown:')
r = es.search(index=INDEX, body={
    'size': 0,
    'aggs': {
        'by_make': {'terms': {'field': 'MNF_ENSHDESC', 'size': 10}},
        'by_status': {'terms': {'field': 'VRG_STATUS', 'size': 5}},
        'by_color': {'terms': {'field': 'CLR_CLRENGDSC', 'size': 10}},
    }
})
for agg, label in [('by_make','Make'), ('by_status','Status'), ('by_color','Color')]:
    print(f'  {label}:', [(b['key'], b['doc_count']) for b in r['aggregations'][agg]['buckets']])

"""
Re-ingest vehicle and violation data with real person QIDs so cross-index joins work.

Fetches actual prs_qid values from the person index, then creates vehicle and
violation records that reference those QIDs via VRG_OWNQID and VLN_OWNQID.
"""

from elasticsearch import Elasticsearch
import json

es = Elasticsearch(['http://localhost:9200'], basic_auth=('elastic', 'elastic'))

PERSON_INDEX = 'moi-gp-all-profiles-details-v1'
VEHICLE_INDEX = 'moi-vehicle-info-v1'
VIOLATIONS_INDEX = 'moi-violations-v1'


# ── Fetch person QIDs by nationality ────────────────────────────────────────

def get_qids(natcde, gender=None, size=10):
    query = {'bool': {'must': [{'term': {'person_natcde': natcde}}]}}
    if gender:
        query['bool']['must'].append({'term': {'prs_gdr': gender}})
    res = es.search(index=PERSON_INDEX, body={'query': query, 'size': size,
                                               '_source': ['prs_qid', 'prs_gdr']})
    return [(h['_source']['prs_qid'], h['_source'].get('prs_gdr')) for h in res['hits']['hits']]


qatari_male = get_qids('634', 'Male', 5)
qatari_female = get_qids('634', 'Female', 5)
pakistani_male = get_qids('586', 'Male', 5)
indian_male = get_qids('356', 'Male', 5)
egyptian_male = get_qids('818', 'Male', 3)

print('Qatari males:', [q for q, _ in qatari_male])
print('Qatari females:', [q for q, _ in qatari_female])
print('Pakistani males:', [q for q, _ in pakistani_male])
print('Indian males:', [q for q, _ in indian_male])
print('Egyptian males:', [q for q, _ in egyptian_male])


# ── Delete and re-ingest vehicles ───────────────────────────────────────────

print('\nRe-ingesting vehicles...')
es.delete_by_query(index=VEHICLE_INDEX, body={'query': {'match_all': {}}}, refresh=True)

vehicles = [
    # Qatari male owns: Toyota Camry (white, active), BMW X5 (black, active)
    {'VRG_OWNQID': qatari_male[0][0], 'VRG_PLTNUM': 'AA1234', 'MNF_ENSHDESC': 'TOYOTA',
     'VEH_MODEL': 'CAMRY', 'VEH_MODELYEAR': '2022', 'CLR_CLRENGDSC': 'WHITE',
     'VRG_STATUS': 'ACT', 'VRG_STADTE': '2022-03-01', 'VRG_ENDDT': '2025-03-01'},
    {'VRG_OWNQID': qatari_male[1][0], 'VRG_PLTNUM': 'BB5678', 'MNF_ENSHDESC': 'BMW',
     'VEH_MODEL': 'X5', 'VEH_MODELYEAR': '2021', 'CLR_CLRENGDSC': 'BLACK',
     'VRG_STATUS': 'ACT', 'VRG_STADTE': '2021-06-15', 'VRG_ENDDT': '2024-06-15'},
    # Qatari female owns: Nissan Patrol (white, active)
    {'VRG_OWNQID': qatari_female[0][0], 'VRG_PLTNUM': 'CC9012', 'MNF_ENSHDESC': 'NISSAN',
     'VEH_MODEL': 'PATROL', 'VEH_MODELYEAR': '2023', 'CLR_CLRENGDSC': 'WHITE',
     'VRG_STATUS': 'ACT', 'VRG_STADTE': '2023-01-10', 'VRG_ENDDT': '2026-01-10'},
    # Pakistani male owns: Toyota Hilux (silver, expired), KIA Sportage (black, active)
    {'VRG_OWNQID': pakistani_male[0][0], 'VRG_PLTNUM': 'DD3456', 'MNF_ENSHDESC': 'TOYOTA',
     'VEH_MODEL': 'HILUX', 'VEH_MODELYEAR': '2019', 'CLR_CLRENGDSC': 'SILVER',
     'VRG_STATUS': 'EXP', 'VRG_STADTE': '2019-05-20', 'VRG_ENDDT': '2022-05-20'},
    {'VRG_OWNQID': pakistani_male[1][0], 'VRG_PLTNUM': 'EE7890', 'MNF_ENSHDESC': 'KIA',
     'VEH_MODEL': 'SPORTAGE', 'VEH_MODELYEAR': '2022', 'CLR_CLRENGDSC': 'BLACK',
     'VRG_STATUS': 'ACT', 'VRG_STADTE': '2022-09-01', 'VRG_ENDDT': '2025-09-01'},
    # Indian male owns: Toyota Fortuner (white, active), Nissan Altima (silver, expired)
    {'VRG_OWNQID': indian_male[0][0], 'VRG_PLTNUM': 'FF1122', 'MNF_ENSHDESC': 'TOYOTA',
     'VEH_MODEL': 'FORTUNER', 'VEH_MODELYEAR': '2020', 'CLR_CLRENGDSC': 'WHITE',
     'VRG_STATUS': 'ACT', 'VRG_STADTE': '2020-11-01', 'VRG_ENDDT': '2023-11-01'},
    {'VRG_OWNQID': indian_male[1][0], 'VRG_PLTNUM': 'GG3344', 'MNF_ENSHDESC': 'NISSAN',
     'VEH_MODEL': 'ALTIMA', 'VEH_MODELYEAR': '2019', 'CLR_CLRENGDSC': 'SILVER',
     'VRG_STATUS': 'EXP', 'VRG_STADTE': '2019-08-15', 'VRG_ENDDT': '2022-08-15'},
    # Egyptian male owns: BMW 7 Series (black, active)
    {'VRG_OWNQID': egyptian_male[0][0], 'VRG_PLTNUM': 'HH5566', 'MNF_ENSHDESC': 'BMW',
     'VEH_MODEL': '7 SERIES', 'VEH_MODELYEAR': '2023', 'CLR_CLRENGDSC': 'BLACK',
     'VRG_STATUS': 'ACT', 'VRG_STADTE': '2023-04-01', 'VRG_ENDDT': '2026-04-01'},
    # Qatari male (3rd): Nissan Sunny (white, expired)
    {'VRG_OWNQID': qatari_male[2][0], 'VRG_PLTNUM': 'II7788', 'MNF_ENSHDESC': 'NISSAN',
     'VEH_MODEL': 'SUNNY', 'VEH_MODELYEAR': '2018', 'CLR_CLRENGDSC': 'WHITE',
     'VRG_STATUS': 'EXP', 'VRG_STADTE': '2018-02-01', 'VRG_ENDDT': '2021-02-01'},
    # Pakistani male (3rd): Toyota Land Cruiser (white, active)
    {'VRG_OWNQID': pakistani_male[2][0], 'VRG_PLTNUM': 'JJ9900', 'MNF_ENSHDESC': 'TOYOTA',
     'VEH_MODEL': 'LAND CRUISER', 'VEH_MODELYEAR': '2023', 'CLR_CLRENGDSC': 'WHITE',
     'VRG_STATUS': 'ACT', 'VRG_STADTE': '2023-07-01', 'VRG_ENDDT': '2026-07-01'},
    # Indian male (3rd): KIA Sorento (black, active)
    {'VRG_OWNQID': indian_male[2][0], 'VRG_PLTNUM': 'KK1122', 'MNF_ENSHDESC': 'KIA',
     'VEH_MODEL': 'SORENTO', 'VEH_MODELYEAR': '2021', 'CLR_CLRENGDSC': 'BLACK',
     'VRG_STATUS': 'ACT', 'VRG_STADTE': '2021-12-01', 'VRG_ENDDT': '2024-12-01'},
    # Qatari female (2nd): Toyota Camry (silver, active)
    {'VRG_OWNQID': qatari_female[1][0], 'VRG_PLTNUM': 'LL3344', 'MNF_ENSHDESC': 'TOYOTA',
     'VEH_MODEL': 'CAMRY', 'VEH_MODELYEAR': '2022', 'CLR_CLRENGDSC': 'SILVER',
     'VRG_STATUS': 'ACT', 'VRG_STADTE': '2022-05-15', 'VRG_ENDDT': '2025-05-15'},
    # Egyptian male (2nd): Nissan Patrol (silver, active)
    {'VRG_OWNQID': egyptian_male[1][0], 'VRG_PLTNUM': 'MM5566', 'MNF_ENSHDESC': 'NISSAN',
     'VEH_MODEL': 'PATROL', 'VEH_MODELYEAR': '2022', 'CLR_CLRENGDSC': 'SILVER',
     'VRG_STATUS': 'ACT', 'VRG_STADTE': '2022-01-01', 'VRG_ENDDT': '2025-01-01'},
]

for v in vehicles:
    es.index(index=VEHICLE_INDEX, body=v)

es.indices.refresh(index=VEHICLE_INDEX)
count = es.count(index=VEHICLE_INDEX)['count']
print(f'Vehicles ingested: {count}')


# ── Delete and re-ingest violations ─────────────────────────────────────────

print('\nRe-ingesting violations...')
es.delete_by_query(index=VIOLATIONS_INDEX, body={'query': {'match_all': {}}}, refresh=True)

violations = [
    # Qatari male 1: speeding on Corniche (unpaid, 2024)
    {'VLN_OWNQID': qatari_male[0][0], 'VLN_PLTNUM': 'AA1234', 'VLN_TYPE': 'SPEEDING',
     'VLN_STATUS': 'UNPAID', 'VLN_PLCDSC': 'CORNICHE ROAD', 'VLN_TOTAMT': 1500.0,
     'VLN_DATE_DATE': '2024-03-15', 'VLN_YEAR': '2024'},
    # Qatari male 1: red light on Al Rayyan (paid, 2023)
    {'VLN_OWNQID': qatari_male[0][0], 'VLN_PLTNUM': 'AA1234', 'VLN_TYPE': 'RED_LIGHT',
     'VLN_STATUS': 'PAID', 'VLN_PLCDSC': 'AL RAYYAN ROAD', 'VLN_TOTAMT': 6000.0,
     'VLN_DATE_DATE': '2023-11-20', 'VLN_YEAR': '2023'},
    # Qatari male 2: parking on Al Waab (unpaid, 2024)
    {'VLN_OWNQID': qatari_male[1][0], 'VLN_PLTNUM': 'BB5678', 'VLN_TYPE': 'PARKING',
     'VLN_STATUS': 'UNPAID', 'VLN_PLCDSC': 'AL WAAB STREET', 'VLN_TOTAMT': 500.0,
     'VLN_DATE_DATE': '2024-01-10', 'VLN_YEAR': '2024'},
    # Qatari female 1: speeding on Salwa Road (paid, 2024)
    {'VLN_OWNQID': qatari_female[0][0], 'VLN_PLTNUM': 'CC9012', 'VLN_TYPE': 'SPEEDING',
     'VLN_STATUS': 'PAID', 'VLN_PLCDSC': 'SALWA ROAD', 'VLN_TOTAMT': 1000.0,
     'VLN_DATE_DATE': '2024-02-28', 'VLN_YEAR': '2024'},
    # Pakistani male 1: mobile phone (unpaid, 2024)
    {'VLN_OWNQID': pakistani_male[0][0], 'VLN_PLTNUM': 'DD3456', 'VLN_TYPE': 'MOBILE_PHONE',
     'VLN_STATUS': 'UNPAID', 'VLN_PLCDSC': 'AL SADD STREET', 'VLN_TOTAMT': 600.0,
     'VLN_DATE_DATE': '2024-04-05', 'VLN_YEAR': '2024'},
    # Pakistani male 2: speeding on Corniche (paid, 2023)
    {'VLN_OWNQID': pakistani_male[1][0], 'VLN_PLTNUM': 'EE7890', 'VLN_TYPE': 'SPEEDING',
     'VLN_STATUS': 'PAID', 'VLN_PLCDSC': 'CORNICHE ROAD', 'VLN_TOTAMT': 3000.0,
     'VLN_DATE_DATE': '2023-08-12', 'VLN_YEAR': '2023'},
    # Indian male 1: seatbelt (unpaid, 2024)
    {'VLN_OWNQID': indian_male[0][0], 'VLN_PLTNUM': 'FF1122', 'VLN_TYPE': 'SEATBELT',
     'VLN_STATUS': 'UNPAID', 'VLN_PLCDSC': 'AL RAYYAN ROAD', 'VLN_TOTAMT': 500.0,
     'VLN_DATE_DATE': '2024-05-01', 'VLN_YEAR': '2024'},
    # Indian male 2: red light on Al Sadd (paid, 2024)
    {'VLN_OWNQID': indian_male[1][0], 'VLN_PLTNUM': 'GG3344', 'VLN_TYPE': 'RED_LIGHT',
     'VLN_STATUS': 'PAID', 'VLN_PLCDSC': 'AL SADD STREET', 'VLN_TOTAMT': 6000.0,
     'VLN_DATE_DATE': '2024-06-15', 'VLN_YEAR': '2024'},
    # Egyptian male 1: speeding on Al Waab (unpaid, 2024)
    {'VLN_OWNQID': egyptian_male[0][0], 'VLN_PLTNUM': 'HH5566', 'VLN_TYPE': 'SPEEDING',
     'VLN_STATUS': 'UNPAID', 'VLN_PLCDSC': 'AL WAAB STREET', 'VLN_TOTAMT': 1500.0,
     'VLN_DATE_DATE': '2024-07-20', 'VLN_YEAR': '2024'},
    # Qatari male 3: speeding on Salwa (unpaid, 2024)
    {'VLN_OWNQID': qatari_male[2][0], 'VLN_PLTNUM': 'II7788', 'VLN_TYPE': 'SPEEDING',
     'VLN_STATUS': 'UNPAID', 'VLN_PLCDSC': 'SALWA ROAD', 'VLN_TOTAMT': 1000.0,
     'VLN_DATE_DATE': '2024-08-10', 'VLN_YEAR': '2024'},
    # Pakistani male 3: parking (paid, 2023)
    {'VLN_OWNQID': pakistani_male[2][0], 'VLN_PLTNUM': 'JJ9900', 'VLN_TYPE': 'PARKING',
     'VLN_STATUS': 'PAID', 'VLN_PLCDSC': 'CORNICHE ROAD', 'VLN_TOTAMT': 500.0,
     'VLN_DATE_DATE': '2023-09-05', 'VLN_YEAR': '2023'},
    # Qatari female 2: mobile phone (unpaid, 2024)
    {'VLN_OWNQID': qatari_female[1][0], 'VLN_PLTNUM': 'LL3344', 'VLN_TYPE': 'MOBILE_PHONE',
     'VLN_STATUS': 'UNPAID', 'VLN_PLCDSC': 'AL WAAB STREET', 'VLN_TOTAMT': 600.0,
     'VLN_DATE_DATE': '2024-09-01', 'VLN_YEAR': '2024'},
]

for v in violations:
    es.index(index=VIOLATIONS_INDEX, body=v)

es.indices.refresh(index=VIOLATIONS_INDEX)
count = es.count(index=VIOLATIONS_INDEX)['count']
print(f'Violations ingested: {count}')

print('\nDone. QID linkage summary:')
print('  Qatari male 1:', qatari_male[0][0], '→ AA1234 (Toyota Camry) + SPEEDING + RED_LIGHT')
print('  Qatari male 2:', qatari_male[1][0], '→ BB5678 (BMW X5) + PARKING')
print('  Qatari female 1:', qatari_female[0][0], '→ CC9012 (Nissan Patrol) + SPEEDING')
print('  Pakistani male 1:', pakistani_male[0][0], '→ DD3456 (Toyota Hilux) + MOBILE_PHONE')
print('  Pakistani male 2:', pakistani_male[1][0], '→ EE7890 (KIA Sportage) + SPEEDING')
print('  Indian male 1:', indian_male[0][0], '→ FF1122 (Toyota Fortuner) + SEATBELT')
print('  Egyptian male 1:', egyptian_male[0][0], '→ HH5566 (BMW 7 Series) + SPEEDING')

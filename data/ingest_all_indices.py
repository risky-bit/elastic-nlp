"""
Re-ingest all supplementary indices with real person QIDs.
Covers: exit/entry, visa, sponsor, relationships, person-detail-v2, visa-application.
"""

from elasticsearch import Elasticsearch
from datetime import date
import random

random.seed(77)
es = Elasticsearch(['http://localhost:9200'], basic_auth=('elastic', 'elastic'))

PERSON_INDEX = 'moi-gp-all-profiles-details-v1'


# ── Fetch person QIDs by nationality ────────────────────────────────────────

def get_persons(natcde, gender=None, size=8):
    must = [{'term': {'person_natcde': natcde}}]
    if gender:
        must.append({'term': {'prs_gdr': gender}})
    res = es.search(index=PERSON_INDEX, body={
        'query': {'bool': {'must': must}},
        'size': size,
        '_source': ['prs_qid', 'prs_gdr', 'CL_person_full_name_en', 'prs_dob']
    })
    return [h['_source'] for h in res['hits']['hits']]


qatari_m = get_persons('634', 'Male', 6)
qatari_f = get_persons('634', 'Female', 6)
pakistani_m = get_persons('586', 'Male', 5)
indian_m = get_persons('356', 'Male', 5)
egyptian_m = get_persons('818', 'Male', 4)
emirati_m = get_persons('784', 'Male', 3)
bangladeshi_m = get_persons('050', 'Male', 3)
filipino_f = get_persons('608', 'Female', 3)
sri_lankan_m = get_persons('144', 'Male', 3)

print('Persons loaded:')
for label, group in [('Qatari M', qatari_m), ('Qatari F', qatari_f),
                     ('Pakistani M', pakistani_m), ('Indian M', indian_m),
                     ('Egyptian M', egyptian_m)]:
    print(f'  {label}: {len(group)}')


# ── EXIT/ENTRY ───────────────────────────────────────────────────────────────

print('\nRe-ingesting exit/entry...')
es.delete_by_query(index='moi-exit-entry-tts-details-v1',
                   body={'query': {'match_all': {}}}, refresh=True)

BORDERS = [
    'HAMAD INTERNATIONAL AIRPORT', 'ABU SAMRA BORDER', 'SALWA BORDER',
    'AL RUWAIS PORT', 'DOHA PORT'
]
TRIP_TYPES = ['FLIGHT', 'LAND', 'SEA']

records = []
# Qatari males — multiple trips each
for p in qatari_m[:4]:
    qid = p['prs_qid']
    records += [
        {'TRX_QIDNO': qid, 'TRV_QIDNO': qid, 'TRX_DATE': '2024-01-10T08:00:00.000Z',
         'TRX_TYPE': '2', 'TRX_TYPE_DESC': 'EXIT TRANSACTION', 'TRX_DIRECTION': 'OUT',
         'BORDER_CODE_DESC': 'HAMAD INTERNATIONAL AIRPORT', 'TRX_TRIP_TYP_DESC': 'FLIGHT',
         'TRX_FLTNUM': 'QR401', 'TXE_SRC_SYS': 'GDRFA'},
        {'TRX_QIDNO': qid, 'TRV_QIDNO': qid, 'TRX_DATE': '2024-01-20T14:00:00.000Z',
         'TRX_TYPE': '1', 'TRX_TYPE_DESC': 'ENTRY TRANSACTION', 'TRX_DIRECTION': 'IN',
         'BORDER_CODE_DESC': 'HAMAD INTERNATIONAL AIRPORT', 'TRX_TRIP_TYP_DESC': 'FLIGHT',
         'TRX_FLTNUM': 'QR402', 'TXE_SRC_SYS': 'GDRFA'},
    ]
# Pakistani males — land border trips
for p in pakistani_m[:3]:
    qid = p['prs_qid']
    records += [
        {'TRX_QIDNO': qid, 'TRV_QIDNO': qid, 'TRX_DATE': '2023-06-05T09:00:00.000Z',
         'TRX_TYPE': '1', 'TRX_TYPE_DESC': 'ENTRY TRANSACTION', 'TRX_DIRECTION': 'IN',
         'BORDER_CODE_DESC': 'HAMAD INTERNATIONAL AIRPORT', 'TRX_TRIP_TYP_DESC': 'FLIGHT',
         'TRX_FLTNUM': 'PK756', 'TXE_SRC_SYS': 'GDRFA'},
        {'TRX_QIDNO': qid, 'TRV_QIDNO': qid, 'TRX_DATE': '2023-12-20T17:00:00.000Z',
         'TRX_TYPE': '2', 'TRX_TYPE_DESC': 'EXIT TRANSACTION', 'TRX_DIRECTION': 'OUT',
         'BORDER_CODE_DESC': 'HAMAD INTERNATIONAL AIRPORT', 'TRX_TRIP_TYP_DESC': 'FLIGHT',
         'TRX_FLTNUM': 'PK757', 'TXE_SRC_SYS': 'GDRFA'},
    ]
# Indian males
for p in indian_m[:3]:
    qid = p['prs_qid']
    records += [
        {'TRX_QIDNO': qid, 'TRV_QIDNO': qid, 'TRX_DATE': '2024-03-01T11:00:00.000Z',
         'TRX_TYPE': '1', 'TRX_TYPE_DESC': 'ENTRY TRANSACTION', 'TRX_DIRECTION': 'IN',
         'BORDER_CODE_DESC': 'HAMAD INTERNATIONAL AIRPORT', 'TRX_TRIP_TYP_DESC': 'FLIGHT',
         'TRX_FLTNUM': 'AI932', 'TXE_SRC_SYS': 'GDRFA'},
    ]
# Egyptian males — sea port
for p in egyptian_m[:2]:
    qid = p['prs_qid']
    records += [
        {'TRX_QIDNO': qid, 'TRV_QIDNO': qid, 'TRX_DATE': '2023-09-15T07:00:00.000Z',
         'TRX_TYPE': '1', 'TRX_TYPE_DESC': 'ENTRY TRANSACTION', 'TRX_DIRECTION': 'IN',
         'BORDER_CODE_DESC': 'DOHA PORT', 'TRX_TRIP_TYP_DESC': 'SEA',
         'TRX_FLTNUM': None, 'TXE_SRC_SYS': 'GDRFA'},
        {'TRX_QIDNO': qid, 'TRV_QIDNO': qid, 'TRX_DATE': '2024-02-10T19:00:00.000Z',
         'TRX_TYPE': '2', 'TRX_TYPE_DESC': 'EXIT TRANSACTION', 'TRX_DIRECTION': 'OUT',
         'BORDER_CODE_DESC': 'ABU SAMRA BORDER', 'TRX_TRIP_TYP_DESC': 'LAND',
         'TRX_FLTNUM': None, 'TXE_SRC_SYS': 'GDRFA'},
    ]
# Qatari females
for p in qatari_f[:3]:
    qid = p['prs_qid']
    records.append(
        {'TRX_QIDNO': qid, 'TRV_QIDNO': qid, 'TRX_DATE': '2024-04-05T10:00:00.000Z',
         'TRX_TYPE': '2', 'TRX_TYPE_DESC': 'EXIT TRANSACTION', 'TRX_DIRECTION': 'OUT',
         'BORDER_CODE_DESC': 'HAMAD INTERNATIONAL AIRPORT', 'TRX_TRIP_TYP_DESC': 'FLIGHT',
         'TRX_FLTNUM': 'QR501', 'TXE_SRC_SYS': 'GDRFA'}
    )

for r in records:
    es.index(index='moi-exit-entry-tts-details-v1', body=r)
es.indices.refresh(index='moi-exit-entry-tts-details-v1')
print(f'Exit/entry ingested: {es.count(index="moi-exit-entry-tts-details-v1")["count"]}')


# ── VISA ─────────────────────────────────────────────────────────────────────

print('\nRe-ingesting visa...')
es.delete_by_query(index='moi-visa-main-details-v1',
                   body={'query': {'match_all': {}}}, refresh=True)

VISA_TYPES = {
    '40': 'Work Visa', '11': 'Visit Visa', '20': 'Residence Permit',
    '35': 'Family Visa', '50': 'Student Visa'
}

visa_records = []
# Pakistani/Indian/Filipino/Bangladeshi workers — work visas
for i, p in enumerate(pakistani_m + indian_m[:3] + filipino_f):
    qid = p['prs_qid']
    visa_records.append({
        'HLD_QIDNO': qid, 'VSA_VSANUM': f'WV2022{i:04d}',
        'VSA_TYPCDE': '40', 'VISA_TYPE_DESC': 'Work Visa',
        'VSA_ISSDTE': '2022-01-15T00:00:00.000Z', 'VSA_EXPDTE': '2025-01-15T00:00:00.000Z',
        'VSA_PASNUM': f'P{100000+i}', 'VSA_LOCCDE': 'VP', 'VSA_RCDSTS': '13',
        'NAT_CDENUM': p.get('person_natcde', '586')
    })
# Qatari residence permits
for i, p in enumerate(qatari_m[:3] + qatari_f[:2]):
    qid = p['prs_qid']
    visa_records.append({
        'HLD_QIDNO': qid, 'VSA_VSANUM': f'RP2021{i:04d}',
        'VSA_TYPCDE': '20', 'VISA_TYPE_DESC': 'Residence Permit',
        'VSA_ISSDTE': '2021-06-01T00:00:00.000Z', 'VSA_EXPDTE': '2026-06-01T00:00:00.000Z',
        'VSA_PASNUM': f'Q{200000+i}', 'VSA_LOCCDE': 'QA', 'VSA_RCDSTS': '13',
        'NAT_CDENUM': '634'
    })
# Egyptian/Emirati visit visas
for i, p in enumerate(egyptian_m + emirati_m):
    qid = p['prs_qid']
    visa_records.append({
        'HLD_QIDNO': qid, 'VSA_VSANUM': f'VV2023{i:04d}',
        'VSA_TYPCDE': '11', 'VISA_TYPE_DESC': 'Visit Visa',
        'VSA_ISSDTE': '2023-03-01T00:00:00.000Z', 'VSA_EXPDTE': '2023-06-01T00:00:00.000Z',
        'VSA_PASNUM': f'E{300000+i}', 'VSA_LOCCDE': 'VP', 'VSA_RCDSTS': '13',
        'NAT_CDENUM': '818' if i < len(egyptian_m) else '784'
    })
# Expired visas (Pakistani)
for i, p in enumerate(pakistani_m[2:]):
    qid = p['prs_qid']
    visa_records.append({
        'HLD_QIDNO': qid, 'VSA_VSANUM': f'WV2019{i:04d}',
        'VSA_TYPCDE': '40', 'VISA_TYPE_DESC': 'Work Visa',
        'VSA_ISSDTE': '2019-05-01T00:00:00.000Z', 'VSA_EXPDTE': '2022-05-01T00:00:00.000Z',
        'VSA_PASNUM': f'P{400000+i}', 'VSA_LOCCDE': 'VP', 'VSA_RCDSTS': '14',
        'NAT_CDENUM': '586'
    })

for r in visa_records:
    es.index(index='moi-visa-main-details-v1', body=r)
es.indices.refresh(index='moi-visa-main-details-v1')
print(f'Visa ingested: {es.count(index="moi-visa-main-details-v1")["count"]}')


# ── SPONSOR ──────────────────────────────────────────────────────────────────

print('\nRe-ingesting sponsor...')
es.delete_by_query(index='moi-sponsor-details-v1',
                   body={'query': {'match_all': {}}}, refresh=True)

# Qatari males sponsor Pakistani/Indian/Filipino workers
sponsor_records = []
for i, (sponsor, sponsored) in enumerate([
    (qatari_m[0], pakistani_m[0]),
    (qatari_m[0], pakistani_m[1]),
    (qatari_m[1], indian_m[0]),
    (qatari_m[1], indian_m[1]),
    (qatari_m[2], filipino_f[0]),
    (qatari_m[2], bangladeshi_m[0]),
    (qatari_m[3], pakistani_m[2]),
    (qatari_m[3], sri_lankan_m[0]),
    (egyptian_m[0], indian_m[2]),
    (emirati_m[0], pakistani_m[3]),
]):
    sponsor_records.append({
        'SPONSOR_QID': sponsor['prs_qid'],
        'SPONSORED_QID': sponsored['prs_qid'],
        'SPONSOR_TYPE': '2',
        'SPONSOR_RELATION': str((i % 5) + 1),
        'FIRST_ENTRY_DATE': '2022-01-15',
        'MDS_DPTENGNAM': 'Expatriates Affairs Dept',
        'MDS_DPTARBNAM': 'إدارة شؤون الوافدين',
        'COMPANY_NO': None,
        'COMPANY_BRANCH_NO': '01'
    })

for r in sponsor_records:
    es.index(index='moi-sponsor-details-v1', body=r)
es.indices.refresh(index='moi-sponsor-details-v1')
print(f'Sponsor ingested: {es.count(index="moi-sponsor-details-v1")["count"]}')


# ── RELATIONSHIPS ────────────────────────────────────────────────────────────

print('\nRe-ingesting relationships...')
es.delete_by_query(index='moi-relationship-details-v1',
                   body={'query': {'match_all': {}}}, refresh=True)

rel_records = []
# Qatari male married to Qatari female
for i, (husband, wife) in enumerate([
    (qatari_m[0], qatari_f[0]),
    (qatari_m[1], qatari_f[1]),
    (qatari_m[2], qatari_f[2]),
    (pakistani_m[0], filipino_f[0]),
    (indian_m[0], qatari_f[3]),
    (egyptian_m[0], qatari_f[4]),
]):
    rel_records.append({
        'HUSBAND_QID_NO': husband['prs_qid'],
        'WIFE_QID_NO': wife['prs_qid'],
        'MARRIAGE_DATE': f'20{18+i:02d}-{(i%12)+1:02d}-15',
        'MARRIAGE_CERTIFICATE_NUMBER': f'20{18+i:02d}/{4000+i}',
        'DIVORCE_DATE': None,
        'DIVORCE_CERTIFICATE_NUMBER': ''
    })

for r in rel_records:
    es.index(index='moi-relationship-details-v1', body=r)
es.indices.refresh(index='moi-relationship-details-v1')
print(f'Relationships ingested: {es.count(index="moi-relationship-details-v1")["count"]}')


# ── VISA APPLICATIONS ────────────────────────────────────────────────────────

print('\nRe-ingesting visa applications...')
es.delete_by_query(index='moi-visa-application-details-v1',
                   body={'query': {'match_all': {}}}, refresh=True)

app_records = []
for i, p in enumerate(qatari_m[:3] + pakistani_m[:2] + indian_m[:2]):
    qid = p['prs_qid']
    status = '2' if i < 5 else '3'  # 2=approved, 3=rejected
    app_records.append({
        'APL_PRSQIDNO': qid,
        'APL_APLNUM': f'VP2023{i:06d}',
        'APL_TYPCDE': '40',
        'APL_RCDSTS': status,
        'APL_APLDTE': '2023-05-01T00:00:00.000Z',
        'APL_EXPDTE': '2025-05-01T00:00:00.000Z',
        'TOT_APPR': 50 if status == '2' else 0,
        'USED_TOT_APPR': random.randint(5, 30) if status == '2' else 0,
        'REM_TOT_APPR': random.randint(10, 40) if status == '2' else 0,
    })

for r in app_records:
    es.index(index='moi-visa-application-details-v1', body=r)
es.indices.refresh(index='moi-visa-application-details-v1')
print(f'Visa applications ingested: {es.count(index="moi-visa-application-details-v1")["count"]}')


print('\nAll indices re-ingested with real QIDs.')

"""
Generate training data v2 — all 8 indices, nationality names (not codes).

The DSL transformer converts names → codes at runtime, so training data
uses plain English nationality names throughout.

Produces:
  data/training/train.jsonl  (85%)
  data/training/valid.jsonl  (15%)

Overwrites previous files (fresh start for v6 adapter).
All pairs validated against real ES before saving.
"""

import json
import random
import os
from elasticsearch import Elasticsearch

random.seed(42)

es = Elasticsearch(['http://localhost:9200'], basic_auth=('elastic', 'elastic'))

# ── Index names ──────────────────────────────────────────────────────────────
PERSON   = 'moi-gp-all-profiles-details-v1'
VEHICLE  = 'moi-vehicle-info-v1'
VIOLS    = 'moi-violations-v1'
ENTRY    = 'moi-exit-entry-tts-details-v1'
VISA     = 'moi-visa-main-details-v1'
SPONSOR  = 'moi-sponsor-details-v1'
RELATION = 'moi-relationship-details-v1'
VISAAPP  = 'moi-visa-application-details-v1'

# ── Constants ────────────────────────────────────────────────────────────────

NATS = ['Qatari', 'Pakistani', 'Indian', 'Egyptian', 'Saudi', 'Emirati',
        'Filipino', 'Jordanian', 'Lebanese', 'Bangladeshi', 'Sri Lankan', 'Indonesian']

GENDERS = [('male', 'Male'), ('female', 'Female'),
           ('males', 'Male'), ('females', 'Female')]

MAKES = {'TOYOTA': ['Toyota', 'toyota'],
         'NISSAN': ['Nissan', 'nissan'],
         'BMW':    ['BMW', 'bmw'],
         'KIA':    ['KIA', 'Kia']}

COLORS = {'WHITE':  ['white', 'White'],
          'BLACK':  ['black', 'Black'],
          'SILVER': ['silver', 'Silver', 'grey', 'gray']}

MODELS = {
    'TOYOTA': ['CAMRY', 'LAND CRUISER', 'FORTUNER', 'HILUX'],
    'NISSAN': ['PATROL', 'ALTIMA', 'SUNNY'],
    'BMW':    ['X5', '7 SERIES'],
    'KIA':    ['SPORTAGE', 'SORENTO'],
}

VEH_STATUSES = {'active': 'ACT', 'valid': 'ACT', 'expired': 'EXP', 'inactive': 'EXP'}

VLN_TYPES = {
    'speeding': 'SPEEDING', 'speed': 'SPEEDING',
    'red light': 'RED_LIGHT', 'running red light': 'RED_LIGHT',
    'parking': 'PARKING', 'illegal parking': 'PARKING',
    'seatbelt': 'SEATBELT', 'no seatbelt': 'SEATBELT',
    'mobile phone': 'MOBILE_PHONE', 'using phone': 'MOBILE_PHONE',
}
VLN_STATUSES = {'paid': 'PAID', 'unpaid': 'UNPAID', 'outstanding': 'UNPAID'}
LOCATIONS = ['CORNICHE ROAD', 'AL WAAB STREET', 'SALWA ROAD',
             'AL RAYYAN ROAD', 'AL SADD STREET']
LOCATION_NAMES = {
    'CORNICHE ROAD': ['Corniche Road', 'the Corniche'],
    'AL WAAB STREET': ['Al Waab Street', 'Al Waab'],
    'SALWA ROAD': ['Salwa Road', 'Salwa'],
    'AL RAYYAN ROAD': ['Al Rayyan Road', 'Al Rayyan'],
    'AL SADD STREET': ['Al Sadd Street', 'Al Sadd'],
}

BORDERS = ['HAMAD INTERNATIONAL AIRPORT', 'ABU SAMRA BORDER', 'SALWA BORDER', 'DOHA PORT']
BORDER_NAMES = {
    'HAMAD INTERNATIONAL AIRPORT': ['Hamad International Airport', 'the airport', 'HIA'],
    'ABU SAMRA BORDER': ['Abu Samra border', 'Abu Samra'],
    'SALWA BORDER': ['Salwa border', 'Salwa crossing'],
    'DOHA PORT': ['Doha Port', 'the port'],
}
TRIP_TYPES = {'FLIGHT': ['flight', 'air'], 'LAND': ['land', 'road'], 'SEA': ['sea', 'boat']}
DIRECTIONS = {'IN': ['entry', 'entering', 'arrived', 'incoming'],
              'OUT': ['exit', 'exiting', 'departed', 'outgoing']}

VISA_TYPES = {
    'Work Visa': ['work visa', 'work visas', 'working visa'],
    'Visit Visa': ['visit visa', 'visit visas', 'visitor visa'],
    'Residence Permit': ['residence permit', 'residence permits'],
    'Family Visa': ['family visa', 'family visas'],
    'Student Visa': ['student visa', 'student visas'],
}

YEARS = ['2019', '2020', '2021', '2022', '2023', '2024']


# ── DSL helpers ──────────────────────────────────────────────────────────────

def dsl(query):
    return json.dumps({'query': query}, separators=(',', ':'))

def term(f, v):   return {'term':  {f: v}}
def match(f, v):  return {'match': {f: v}}
def rng(f, **kw): return {'range': {f: kw}}

def must(*cs):    return {'bool': {'must': list(cs)}}
def should(*cs):  return {'bool': {'should': list(cs), 'minimum_should_match': 1}}

def plan(*steps):
    return json.dumps({'type': 'multi_index', 'steps': list(steps)}, separators=(',', ':'))

def step(num, idx, query, extract=None):
    s = {'step': num, 'index': idx, 'query': query}
    if extract:
        s['extract_field'] = extract
    return s

def terms_ph(field, step_n):
    return {'terms': {field: f'$step_{step_n}'}}


# ── Validation ───────────────────────────────────────────────────────────────

import json as _json
from src.dsl_transformer import DSLTransformer
_t = DSLTransformer()

def validate_single(idx, dsl_str):
    try:
        raw = _json.loads(dsl_str)
        transformed = _t.transform(raw)
        es.search(index=idx, body={**transformed, 'size': 0})
        return True
    except Exception as e:
        print(f'  INVALID: {e}')
        return False

def validate_plan_str(plan_str):
    try:
        p = _json.loads(plan_str)
        step_results = {}
        for s in p['steps']:
            q = s['query']
            q_json = _json.dumps(q)
            for sn, ids in step_results.items():
                q_json = q_json.replace(f'"$step_{sn}"', _json.dumps(ids))
            q = _json.loads(q_json)
            # transform nationality names
            q = _t._transform_node(q)
            res = es.search(index=s['index'], body={'query': q, 'size': 100})
            if s.get('extract_field'):
                ids = list(set(
                    str(h['_source'].get(s['extract_field']))
                    for h in res['hits']['hits']
                    if h['_source'].get(s['extract_field'])
                ))
                step_results[s['step']] = ids
        return True
    except Exception as e:
        print(f'  INVALID PLAN: {e}')
        return False


# ── Pair collection ──────────────────────────────────────────────────────────

pairs = []   # (index_or_'multi', nl, dsl_or_plan_str)

def add(idx, nl, q):
    d = dsl(q)
    if validate_single(idx, d):
        pairs.append((idx, nl, d))

def addp(nl, p):
    if validate_plan_str(p):
        pairs.append(('multi', nl, p))


# ════════════════════════════════════════════════════════════════════════════
# SINGLE-INDEX PAIRS
# ════════════════════════════════════════════════════════════════════════════

# ── PERSON ──────────────────────────────────────────────────────────────────

names = ['Ahmed', 'Mohammed', 'Fatima', 'Ali', 'Sara', 'Omar',
         'Layla', 'Hassan', 'Noor', 'Khalid', 'Mariam', 'Yousef']
for name in names:
    for nl in [f'Find person named {name}', f'Search for {name}', f'Show me {name}']:
        add(PERSON, nl, match('CL_person_full_name_en', name))

for nl_g, es_g in GENDERS:
    for nl in [f'Find all {nl_g} persons', f'Show all {nl_g}', f'List {nl_g} persons',
               f'Show me all {nl_g}', f'Find {nl_g}']:
        add(PERSON, nl, term('prs_gdr', es_g))

for nat in NATS:
    for nl in [f'Find all {nat} nationals', f'Show all {nat} nationals',
               f'Show {nat} persons', f'List all {nat}s',
               f'Find all persons with {nat} nationality',
               f'Show all persons with {nat} nationality',
               f'Find {nat} people', f'Show me {nat} nationals']:
        add(PERSON, nl, term('person_natcde', nat))

for year in ['1970','1975','1980','1985','1990','1995','2000']:
    add(PERSON, f'Show persons born after {year}', rng('prs_dob', gte=f'{year}-01-01'))
    add(PERSON, f'Find persons born before {year}', rng('prs_dob', lte=f'{year}-12-31'))
add(PERSON, 'Find persons born between 1980 and 1990',
    rng('prs_dob', gte='1980-01-01', lte='1990-12-31'))
add(PERSON, 'Show persons born between 1985 and 2000',
    rng('prs_dob', gte='1985-01-01', lte='2000-12-31'))

for nat in NATS:
    for nl_g, es_g in [('male','Male'), ('female','Female')]:
        add(PERSON, f'Find {nat} {nl_g}s',
            must(term('person_natcde', nat), term('prs_gdr', es_g)))
        add(PERSON, f'Show all {nat} {nl_g} persons',
            must(term('person_natcde', nat), term('prs_gdr', es_g)))

for nl_g, es_g in [('male','Male'), ('female','Female')]:
    add(PERSON, f'Find {nl_g}s born after 1990',
        must(term('prs_gdr', es_g), rng('prs_dob', gte='1990-01-01')))
    add(PERSON, f'Show {nl_g}s born before 1970',
        must(term('prs_gdr', es_g), rng('prs_dob', lte='1970-12-31')))

for nat in NATS[:8]:
    add(PERSON, f'Find {nat} persons born after 1980',
        must(term('person_natcde', nat), rng('prs_dob', gte='1980-01-01')))

for nat in NATS[:6]:
    for nl_g, es_g in [('male','Male'), ('female','Female')]:
        add(PERSON, f'Find {nat} {nl_g}s born between 1980 and 1990',
            must(term('person_natcde', nat), term('prs_gdr', es_g),
                 rng('prs_dob', gte='1980-01-01', lte='1990-12-31')))
        add(PERSON, f'Show {nat} {nl_g}s born after 1985',
            must(term('person_natcde', nat), term('prs_gdr', es_g),
                 rng('prs_dob', gte='1985-01-01')))

for (n1, n2) in [('Qatari','Saudi'), ('Indian','Pakistani'), ('Egyptian','Jordanian'),
                 ('Emirati','Lebanese'), ('Filipino','Indonesian')]:
    add(PERSON, f'Find {n1} or {n2} persons',
        should(term('person_natcde', n1), term('person_natcde', n2)))
    for nl_g, es_g in [('male','Male'), ('female','Female')]:
        add(PERSON, f'Find {n1} or {n2} {nl_g}s',
            must(should(term('person_natcde', n1), term('person_natcde', n2)),
                 term('prs_gdr', es_g)))


# ── VEHICLE ──────────────────────────────────────────────────────────────────

for plate in ['A12345', 'AA1234', 'BB5678', 'DD3456', 'FF1122']:
    add(VEHICLE, f'Find vehicle with plate number {plate}', match('VRG_PLTNUM', plate))
    add(VEHICLE, f'Search for plate {plate}', match('VRG_PLTNUM', plate))

for make, aliases in MAKES.items():
    for alias in aliases:
        add(VEHICLE, f'Show all {alias} vehicles', match('MNF_ENSHDESC', make))
        add(VEHICLE, f'Find {alias} cars', match('MNF_ENSHDESC', make))

for color, aliases in COLORS.items():
    for alias in aliases[:2]:
        add(VEHICLE, f'Find all {alias} vehicles', match('CLR_CLRENGDSC', color))
        add(VEHICLE, f'Show {alias} cars', match('CLR_CLRENGDSC', color))

for nl_s, es_s in [('active','ACT'), ('expired','EXP')]:
    add(VEHICLE, f'Show all vehicles with {nl_s} registration', match('VRG_STATUS', es_s))
    add(VEHICLE, f'Find {nl_s} vehicles', match('VRG_STATUS', es_s))

for color, aliases in COLORS.items():
    add(VEHICLE, f'Find all {aliases[0]} vehicles with expired registration',
        must(match('CLR_CLRENGDSC', color), match('VRG_STATUS', 'EXP')))
    add(VEHICLE, f'Show {aliases[0]} vehicles with active registration',
        must(match('CLR_CLRENGDSC', color), match('VRG_STATUS', 'ACT')))

for make, aliases in MAKES.items():
    for color, caliases in COLORS.items():
        add(VEHICLE, f'Find {caliases[0]} {aliases[0]} vehicles',
            must(match('MNF_ENSHDESC', make), match('CLR_CLRENGDSC', color)))
    add(VEHICLE, f'Find {aliases[0]} vehicles with active registration',
        must(match('MNF_ENSHDESC', make), match('VRG_STATUS', 'ACT')))
    add(VEHICLE, f'Find {aliases[0]} vehicles with expired registration',
        must(match('MNF_ENSHDESC', make), match('VRG_STATUS', 'EXP')))
    for year in YEARS:
        add(VEHICLE, f'Show {aliases[0]} vehicles from {year}',
            must(match('MNF_ENSHDESC', make), term('VEH_MODELYEAR', year)))
        add(VEHICLE, f'Find {aliases[0]} vehicles registered in {year}',
            must(match('MNF_ENSHDESC', make),
                 rng('VRG_STADTE', gte=f'{year}-01-01', lte=f'{year}-12-31')))

for year in ['2022','2023','2024']:
    add(VEHICLE, f'Show all vehicles with registration expiring before {year}',
        rng('VRG_ENDDT', lt=f'{year}-01-01'))
    add(VEHICLE, f'Find vehicles expiring before {year}',
        rng('VRG_ENDDT', lt=f'{year}-01-01'))

for make, aliases in MAKES.items():
    for color, caliases in COLORS.items():
        add(VEHICLE, f'Find {caliases[0]} {aliases[0]} vehicles with active registration',
            must(match('MNF_ENSHDESC', make), match('CLR_CLRENGDSC', color),
                 match('VRG_STATUS', 'ACT')))

for (m1, m2) in [('TOYOTA','NISSAN'), ('BMW','KIA'), ('TOYOTA','KIA')]:
    a1, a2 = MAKES[m1][0], MAKES[m2][0]
    add(VEHICLE, f'Find {a1} or {a2} vehicles',
        should(match('MNF_ENSHDESC', m1), match('MNF_ENSHDESC', m2)))
    for color, caliases in COLORS.items():
        add(VEHICLE, f'Find {a1} or {a2} vehicles that are {caliases[0]}',
            must(should(match('MNF_ENSHDESC', m1), match('MNF_ENSHDESC', m2)),
                 match('CLR_CLRENGDSC', color)))
    for (c1, c2) in [('WHITE','SILVER'), ('WHITE','BLACK'), ('BLACK','SILVER')]:
        cn1, cn2 = COLORS[c1][0], COLORS[c2][0]
        add(VEHICLE, f'Find {a1} or {a2} vehicles that are {cn1} or {cn2}',
            must(should(match('MNF_ENSHDESC', m1), match('MNF_ENSHDESC', m2)),
                 should(match('CLR_CLRENGDSC', c1), match('CLR_CLRENGDSC', c2))))


# ── VIOLATIONS ───────────────────────────────────────────────────────────────

for nl_t, es_t in VLN_TYPES.items():
    add(VIOLS, f'Find all {nl_t} violations', term('VLN_TYPE', es_t))
    add(VIOLS, f'Show {nl_t} violations', term('VLN_TYPE', es_t))

for nl_s, es_s in VLN_STATUSES.items():
    add(VIOLS, f'Show all {nl_s} violations', term('VLN_STATUS', es_s))
    add(VIOLS, f'Find {nl_s} violations', term('VLN_STATUS', es_s))
    add(VIOLS, f'Show {nl_s} fines', term('VLN_STATUS', es_s))

for loc, aliases in LOCATION_NAMES.items():
    for alias in aliases:
        add(VIOLS, f'Find violations on {alias}', term('VLN_PLCDSC', loc))
        add(VIOLS, f'Show violations at {alias}', term('VLN_PLCDSC', loc))

for nl_t, es_t in list(VLN_TYPES.items())[:5]:
    for nl_s, es_s in VLN_STATUSES.items():
        add(VIOLS, f'Find {nl_s} {nl_t} violations',
            must(term('VLN_TYPE', es_t), term('VLN_STATUS', es_s)))
        add(VIOLS, f'Show {nl_t} violations that are {nl_s}',
            must(term('VLN_TYPE', es_t), term('VLN_STATUS', es_s)))

for nl_t, es_t in [('speeding','SPEEDING'), ('parking','PARKING'), ('red light','RED_LIGHT')]:
    for loc, aliases in list(LOCATION_NAMES.items())[:4]:
        add(VIOLS, f'Find {nl_t} violations on {aliases[0]}',
            must(term('VLN_TYPE', es_t), term('VLN_PLCDSC', loc)))

for threshold in [500, 1000, 1500, 3000]:
    add(VIOLS, f'Show violations with fine greater than {threshold}',
        rng('VLN_TOTAMT', gt=threshold))
    add(VIOLS, f'Find violations with fine over {threshold} QAR',
        rng('VLN_TOTAMT', gt=threshold))

for nl_s, es_s in [('unpaid','UNPAID'), ('paid','PAID')]:
    for threshold in [500, 1000, 1500, 3000]:
        add(VIOLS, f'Find {nl_s} violations with fine over {threshold}',
            must(term('VLN_STATUS', es_s), rng('VLN_TOTAMT', gt=threshold)))
        add(VIOLS, f'Show violations with fine greater than {threshold} that are {nl_s}',
            must(rng('VLN_TOTAMT', gt=threshold), term('VLN_STATUS', es_s)))

for year in ['2024', '2023']:
    add(VIOLS, f'Find all violations from {year}', term('VLN_YEAR', year))
    add(VIOLS, f'Show {year} violations', term('VLN_YEAR', year))

for nl_t, es_t in [('speeding','SPEEDING'), ('parking','PARKING')]:
    for nl_s, es_s in [('unpaid','UNPAID'), ('paid','PAID')]:
        for loc, aliases in list(LOCATION_NAMES.items())[:3]:
            add(VIOLS, f'Find {nl_s} {nl_t} violations on {aliases[0]}',
                must(term('VLN_TYPE', es_t), term('VLN_STATUS', es_s),
                     term('VLN_PLCDSC', loc)))


# ── EXIT/ENTRY ───────────────────────────────────────────────────────────────

for nl_d, es_d in [('entry','IN'), ('exit','OUT'), ('arrival','IN'), ('departure','OUT')]:
    add(ENTRY, f'Find all {nl_d} transactions', match('TRX_DIRECTION', es_d))
    add(ENTRY, f'Show {nl_d} records', match('TRX_DIRECTION', es_d))

for border, aliases in BORDER_NAMES.items():
    for alias in aliases[:2]:
        add(ENTRY, f'Find transactions at {alias}', match('BORDER_CODE_DESC', border))
        add(ENTRY, f'Show entries through {alias}', match('BORDER_CODE_DESC', border))

for nl_m, es_m in [('flight','FLIGHT'), ('land','LAND'), ('sea','SEA')]:
    add(ENTRY, f'Find {nl_m} transactions', match('TRX_TRIP_TYP_DESC', es_m))
    add(ENTRY, f'Show {nl_m} travel records', match('TRX_TRIP_TYP_DESC', es_m))

for year in ['2023', '2024']:
    add(ENTRY, f'Find transactions in {year}',
        rng('TRX_DATE', gte=f'{year}-01-01', lte=f'{year}-12-31'))

for nl_d, es_d in [('entry','IN'), ('exit','OUT')]:
    for border, aliases in list(BORDER_NAMES.items())[:2]:
        add(ENTRY, f'Find {nl_d} transactions at {aliases[0]}',
            must(match('TRX_DIRECTION', es_d), match('BORDER_CODE_DESC', border)))

for nl_d, es_d in [('entry','IN'), ('exit','OUT')]:
    add(ENTRY, f'Find {nl_d} flights',
        must(match('TRX_DIRECTION', es_d), match('TRX_TRIP_TYP_DESC', 'FLIGHT')))
    add(ENTRY, f'Show {nl_d} records at Hamad International Airport in 2024',
        must(match('TRX_DIRECTION', es_d), match('BORDER_CODE_DESC', 'HAMAD INTERNATIONAL AIRPORT'),
             rng('TRX_DATE', gte='2024-01-01', lte='2024-12-31')))


# ── VISA ─────────────────────────────────────────────────────────────────────

for vtype, aliases in VISA_TYPES.items():
    for alias in aliases[:2]:
        add(VISA, f'Find all {alias}s', match('VISA_TYPE_DESC', vtype))
        add(VISA, f'Show {alias}s', match('VISA_TYPE_DESC', vtype))

add(VISA, 'Find active visas', match('VSA_RCDSTS', '13'))
add(VISA, 'Show expired visas', match('VSA_RCDSTS', '14'))
add(VISA, 'Find all expired visas', match('VSA_RCDSTS', '14'))

for year in ['2022', '2023', '2024']:
    add(VISA, f'Find visas issued in {year}',
        rng('VSA_ISSDTE', gte=f'{year}-01-01', lte=f'{year}-12-31'))
    add(VISA, f'Show visas expiring before {year}',
        rng('VSA_EXPDTE', lt=f'{year}-01-01'))

for vtype, aliases in list(VISA_TYPES.items())[:3]:
    add(VISA, f'Find active {aliases[0]}s',
        must(match('VISA_TYPE_DESC', vtype), match('VSA_RCDSTS', '13')))
    add(VISA, f'Show expired {aliases[0]}s',
        must(match('VISA_TYPE_DESC', vtype), match('VSA_RCDSTS', '14')))

for nat in ['Pakistani', 'Indian', 'Filipino', 'Qatari', 'Egyptian']:
    add(VISA, f'Find visas for {nat} nationals', term('NAT_CDENUM', nat))
    add(VISA, f'Show {nat} work visas',
        must(term('NAT_CDENUM', nat), match('VISA_TYPE_DESC', 'Work Visa')))


# ── SPONSOR ──────────────────────────────────────────────────────────────────

add(SPONSOR, 'Find all sponsor records', match('SPONSOR_TYPE', '2'))
add(SPONSOR, 'Show sponsored persons', match('SPONSOR_TYPE', '2'))
add(SPONSOR, 'Find sponsors who entered before 2021',
    rng('FIRST_ENTRY_DATE', lte='2021-12-31'))
add(SPONSOR, 'Show persons who first entered after 2020',
    rng('FIRST_ENTRY_DATE', gte='2020-01-01'))
add(SPONSOR, 'Find sponsor records from 2022',
    rng('FIRST_ENTRY_DATE', gte='2022-01-01', lte='2022-12-31'))


# ── RELATIONSHIPS ────────────────────────────────────────────────────────────

add(RELATION, 'Find all marriages', rng('MARRIAGE_DATE', gte='2010-01-01'))
add(RELATION, 'Show marriages after 2015',
    rng('MARRIAGE_DATE', gte='2015-01-01'))
add(RELATION, 'Find marriages in 2020',
    rng('MARRIAGE_DATE', gte='2020-01-01', lte='2020-12-31'))
add(RELATION, 'Show marriages before 2020',
    rng('MARRIAGE_DATE', lte='2019-12-31'))


# ════════════════════════════════════════════════════════════════════════════
# MULTI-INDEX PAIRS
# ════════════════════════════════════════════════════════════════════════════

# ── Person → Violations ──────────────────────────────────────────────────────

for nat in NATS[:8]:
    addp(f'Find all violations for {nat} nationals',
         plan(step(1, PERSON, term('person_natcde', nat), 'prs_qid'),
              step(2, VIOLS, must(terms_ph('VLN_OWNQID', 1)))))
    addp(f'Show violations belonging to {nat} drivers',
         plan(step(1, PERSON, term('person_natcde', nat), 'prs_qid'),
              step(2, VIOLS, must(terms_ph('VLN_OWNQID', 1)))))

for nat in NATS[:6]:
    for nl_t, es_t in list(VLN_TYPES.items())[:5]:
        addp(f'Find {nl_t} violations for {nat} nationals',
             plan(step(1, PERSON, term('person_natcde', nat), 'prs_qid'),
                  step(2, VIOLS, must(terms_ph('VLN_OWNQID', 1), term('VLN_TYPE', es_t)))))
        addp(f'Show {nl_t} violations by {nat} drivers',
             plan(step(1, PERSON, term('person_natcde', nat), 'prs_qid'),
                  step(2, VIOLS, must(terms_ph('VLN_OWNQID', 1), term('VLN_TYPE', es_t)))))

for nat in NATS[:6]:
    for nl_s, es_s in [('unpaid','UNPAID'), ('paid','PAID')]:
        addp(f'Find {nl_s} violations for {nat} nationals',
             plan(step(1, PERSON, term('person_natcde', nat), 'prs_qid'),
                  step(2, VIOLS, must(terms_ph('VLN_OWNQID', 1), term('VLN_STATUS', es_s)))))
        addp(f'Show {nat} {nl_s} fines',
             plan(step(1, PERSON, term('person_natcde', nat), 'prs_qid'),
                  step(2, VIOLS, must(terms_ph('VLN_OWNQID', 1), term('VLN_STATUS', es_s)))))

for nl_g, es_g in [('male','Male'), ('female','Female')]:
    for nl_t, es_t in list(VLN_TYPES.items())[:3]:
        addp(f'Find {nl_t} violations for {nl_g} drivers',
             plan(step(1, PERSON, term('prs_gdr', es_g), 'prs_qid'),
                  step(2, VIOLS, must(terms_ph('VLN_OWNQID', 1), term('VLN_TYPE', es_t)))))

for nat in NATS[:4]:
    for nl_g, es_g in [('male','Male'), ('female','Female')]:
        for nl_t, es_t in list(VLN_TYPES.items())[:3]:
            addp(f'Find {nl_t} violations for {nat} {nl_g}s',
                 plan(step(1, PERSON, must(term('person_natcde', nat), term('prs_gdr', es_g)), 'prs_qid'),
                      step(2, VIOLS, must(terms_ph('VLN_OWNQID', 1), term('VLN_TYPE', es_t)))))

for nat in NATS[:4]:
    for nl_t, es_t in list(VLN_TYPES.items())[:3]:
        for nl_s, es_s in [('unpaid','UNPAID'), ('paid','PAID')]:
            addp(f'Find {nl_s} {nl_t} violations for {nat} nationals',
                 plan(step(1, PERSON, term('person_natcde', nat), 'prs_qid'),
                      step(2, VIOLS, must(terms_ph('VLN_OWNQID', 1),
                                          term('VLN_TYPE', es_t), term('VLN_STATUS', es_s)))))


# ── Person → Vehicle ─────────────────────────────────────────────────────────

for nat in NATS[:8]:
    addp(f'Find all vehicles owned by {nat} nationals',
         plan(step(1, PERSON, term('person_natcde', nat), 'prs_qid'),
              step(2, VEHICLE, must(terms_ph('VRG_OWNQID', 1)))))
    addp(f'Show vehicles registered to {nat} persons',
         plan(step(1, PERSON, term('person_natcde', nat), 'prs_qid'),
              step(2, VEHICLE, must(terms_ph('VRG_OWNQID', 1)))))

for nat in NATS[:6]:
    for make, aliases in MAKES.items():
        addp(f'Find {aliases[0]} vehicles owned by {nat} nationals',
             plan(step(1, PERSON, term('person_natcde', nat), 'prs_qid'),
                  step(2, VEHICLE, must(terms_ph('VRG_OWNQID', 1), match('MNF_ENSHDESC', make)))))
        addp(f'Show {aliases[0]} cars belonging to {nat} people',
             plan(step(1, PERSON, term('person_natcde', nat), 'prs_qid'),
                  step(2, VEHICLE, must(terms_ph('VRG_OWNQID', 1), match('MNF_ENSHDESC', make)))))

for nat in NATS[:6]:
    for nl_s, es_s in [('active','ACT'), ('expired','EXP')]:
        addp(f'Find vehicles with {nl_s} registration owned by {nat} nationals',
             plan(step(1, PERSON, term('person_natcde', nat), 'prs_qid'),
                  step(2, VEHICLE, must(terms_ph('VRG_OWNQID', 1), match('VRG_STATUS', es_s)))))
        addp(f'Show {nl_s} vehicles belonging to {nat} nationals',
             plan(step(1, PERSON, term('person_natcde', nat), 'prs_qid'),
                  step(2, VEHICLE, must(terms_ph('VRG_OWNQID', 1), match('VRG_STATUS', es_s)))))

for nat in NATS[:4]:
    for color, caliases in COLORS.items():
        addp(f'Find {caliases[0]} vehicles owned by {nat} nationals',
             plan(step(1, PERSON, term('person_natcde', nat), 'prs_qid'),
                  step(2, VEHICLE, must(terms_ph('VRG_OWNQID', 1), match('CLR_CLRENGDSC', color)))))

for nl_g, es_g in [('male','Male'), ('female','Female')]:
    for make, aliases in MAKES.items():
        addp(f'Find {aliases[0]} vehicles owned by {nl_g} drivers',
             plan(step(1, PERSON, term('prs_gdr', es_g), 'prs_qid'),
                  step(2, VEHICLE, must(terms_ph('VRG_OWNQID', 1), match('MNF_ENSHDESC', make)))))


# ── Person → Exit/Entry ──────────────────────────────────────────────────────

for nat in NATS[:6]:
    for nl_d, es_d in [('entry','IN'), ('exit','OUT')]:
        addp(f'Find {nl_d} records for {nat} nationals',
             plan(step(1, PERSON, term('person_natcde', nat), 'prs_qid'),
                  step(2, ENTRY, must(terms_ph('TRX_QIDNO', 1), match('TRX_DIRECTION', es_d)))))
        addp(f'Show {nat} {nl_d} transactions',
             plan(step(1, PERSON, term('person_natcde', nat), 'prs_qid'),
                  step(2, ENTRY, must(terms_ph('TRX_QIDNO', 1), match('TRX_DIRECTION', es_d)))))

for nat in NATS[:4]:
    addp(f'Find all travel records for {nat} nationals',
         plan(step(1, PERSON, term('person_natcde', nat), 'prs_qid'),
              step(2, ENTRY, must(terms_ph('TRX_QIDNO', 1)))))

for nat in NATS[:4]:
    for nl_d, es_d in [('entry','IN'), ('exit','OUT')]:
        addp(f'Find {nat} {nl_d} flights',
             plan(step(1, PERSON, term('person_natcde', nat), 'prs_qid'),
                  step(2, ENTRY, must(terms_ph('TRX_QIDNO', 1),
                                      match('TRX_DIRECTION', es_d),
                                      match('TRX_TRIP_TYP_DESC', 'FLIGHT')))))


# ── Person → Visa ────────────────────────────────────────────────────────────

for nat in NATS[:6]:
    addp(f'Find all visas for {nat} nationals',
         plan(step(1, PERSON, term('person_natcde', nat), 'prs_qid'),
              step(2, VISA, must(terms_ph('HLD_QIDNO', 1)))))

for nat in NATS[:4]:
    for vtype, aliases in list(VISA_TYPES.items())[:3]:
        addp(f'Find {aliases[0]}s for {nat} nationals',
             plan(step(1, PERSON, term('person_natcde', nat), 'prs_qid'),
                  step(2, VISA, must(terms_ph('HLD_QIDNO', 1), match('VISA_TYPE_DESC', vtype)))))

for nat in NATS[:4]:
    addp(f'Find active visas for {nat} nationals',
         plan(step(1, PERSON, term('person_natcde', nat), 'prs_qid'),
              step(2, VISA, must(terms_ph('HLD_QIDNO', 1), match('VSA_RCDSTS', '13')))))
    addp(f'Find expired visas for {nat} nationals',
         plan(step(1, PERSON, term('person_natcde', nat), 'prs_qid'),
              step(2, VISA, must(terms_ph('HLD_QIDNO', 1), match('VSA_RCDSTS', '14')))))


# ── Person → Sponsor ─────────────────────────────────────────────────────────

for nat in ['Qatari', 'Egyptian', 'Emirati']:
    addp(f'Find persons sponsored by {nat} nationals',
         plan(step(1, PERSON, term('person_natcde', nat), 'prs_qid'),
              step(2, SPONSOR, must(terms_ph('SPONSOR_QID', 1)))))
    addp(f'Show who is sponsored by {nat} nationals',
         plan(step(1, PERSON, term('person_natcde', nat), 'prs_qid'),
              step(2, SPONSOR, must(terms_ph('SPONSOR_QID', 1)))))

for nat in ['Pakistani', 'Indian', 'Filipino', 'Bangladeshi']:
    addp(f'Find sponsor records for {nat} nationals',
         plan(step(1, PERSON, term('person_natcde', nat), 'prs_qid'),
              step(2, SPONSOR, must(terms_ph('SPONSORED_QID', 1)))))


# ════════════════════════════════════════════════════════════════════════════
# WRITE OUTPUT
# ════════════════════════════════════════════════════════════════════════════

print(f'\nTotal valid pairs: {len(pairs)}')
single = sum(1 for p in pairs if p[0] != 'multi')
multi  = sum(1 for p in pairs if p[0] == 'multi')
print(f'  Single-index: {single}')
print(f'  Multi-index:  {multi}')

random.shuffle(pairs)
split = int(len(pairs) * 0.85)
train_pairs = pairs[:split]
valid_pairs = pairs[split:]
print(f'Train: {len(train_pairs)} | Valid: {len(valid_pairs)}')

os.makedirs('data/training', exist_ok=True)

def write_jsonl(path, data):
    with open(path, 'w') as f:
        for _, nl, dsl_str in data:
            record = {'messages': [
                {'role': 'user', 'content': nl},
                {'role': 'assistant', 'content': dsl_str}
            ]}
            f.write(json.dumps(record) + '\n')
    print(f'Written: {path}')

write_jsonl('data/training/train.jsonl', train_pairs)
write_jsonl('data/training/valid.jsonl', valid_pairs)
print('Done.')

"""
Generate training data for EQuIP_3B LoRA fine-tuning on MOI schema.

Produces JSONL files in MLX-LM chat format:
  data/training/train.jsonl  (85%)
  data/training/valid.jsonl  (15%)

Each line: {"messages": [{"role": "user", "content": "..."}, {"role": "assistant", "content": "..."}]}

The user turn is the natural language query.
The assistant turn is the ground-truth Elasticsearch DSL.

All DSL is validated against Elasticsearch before saving.
"""

import json
import random
import os
from elasticsearch import Elasticsearch

random.seed(42)

es = Elasticsearch(
    ['http://localhost:9200'],
    basic_auth=('elastic', 'elastic'),
    request_timeout=10
)

# ── Schema constants (from actual ES data) ──────────────────────────────────

PERSON_INDEX = 'moi-gp-all-profiles-details-v1'
VEHICLE_INDEX = 'moi-vehicle-info-v1'
VIOLATIONS_INDEX = 'moi-violations-v1'

NATIONALITIES = {
    'Qatari': '634', 'Saudi': '682', 'Emirati': '784', 'Egyptian': '818',
    'Jordanian': '400', 'Filipino': '608', 'Lebanese': '422', 'Syrian': '760',
    'American': '840', 'Indonesian': '360', 'Pakistani': '586', 'Indian': '356',
}
GENDERS = {'male': 'Male', 'female': 'Female', 'males': 'Male', 'females': 'Female'}

MAKES = ['TOYOTA', 'NISSAN', 'BMW', 'KIA']
MAKE_NAMES = {
    'TOYOTA': ['Toyota', 'toyota'],
    'NISSAN': ['Nissan', 'nissan'],
    'BMW': ['BMW', 'bmw'],
    'KIA': ['KIA', 'Kia', 'kia'],
}
COLORS = ['WHITE', 'BLACK', 'SILVER']
COLOR_NAMES = {
    'WHITE': ['white', 'White'],
    'BLACK': ['black', 'Black'],
    'SILVER': ['silver', 'Silver', 'grey', 'gray'],
}
MODELS = {
    'TOYOTA': ['CAMRY', 'LAND CRUISER', 'FORTUNER', 'HILUX'],
    'NISSAN': ['PATROL', 'ALTIMA', 'SUNNY'],
    'BMW': ['X5', '7 SERIES'],
    'KIA': ['SPORTAGE', 'SORENTO'],
}
YEARS = ['2019', '2020', '2021', '2022', '2023']
STATUSES_VEH = {'active': 'ACT', 'valid': 'ACT', 'expired': 'EXP', 'inactive': 'EXP'}

VLN_TYPES = {
    'speeding': 'SPEEDING', 'speed': 'SPEEDING',
    'red light': 'RED_LIGHT', 'running red light': 'RED_LIGHT',
    'parking': 'PARKING', 'illegal parking': 'PARKING',
    'seatbelt': 'SEATBELT', 'no seatbelt': 'SEATBELT',
    'mobile phone': 'MOBILE_PHONE', 'phone': 'MOBILE_PHONE', 'using phone': 'MOBILE_PHONE',
}
VLN_STATUSES = {'paid': 'PAID', 'unpaid': 'UNPAID', 'outstanding': 'UNPAID'}
LOCATIONS = [
    'CORNICHE ROAD', 'AL WAAB STREET', 'SALWA ROAD',
    'AL RAYYAN ROAD', 'AL SADD STREET', 'HAMAD HOSPITAL STREET', 'AL MATAR STREET'
]
LOCATION_NAMES = {
    'CORNICHE ROAD': ['Corniche Road', 'the Corniche', 'Corniche'],
    'AL WAAB STREET': ['Al Waab Street', 'Al Waab'],
    'SALWA ROAD': ['Salwa Road', 'Salwa'],
    'AL RAYYAN ROAD': ['Al Rayyan Road', 'Al Rayyan'],
    'AL SADD STREET': ['Al Sadd Street', 'Al Sadd'],
    'HAMAD HOSPITAL STREET': ['Hamad Hospital Street'],
    'AL MATAR STREET': ['Al Matar Street', 'Al Matar'],
}
FINES = [500, 600, 1000, 1500, 3000, 6000]


# ── DSL builders ────────────────────────────────────────────────────────────

def dsl(query):
    return json.dumps({"query": query}, separators=(',', ':'))

def term(field, value):
    return {"term": {field: value}}

def match(field, value):
    return {"match": {field: value}}

def range_q(field, **kwargs):
    return {"range": {field: kwargs}}

def bool_must(*clauses):
    return {"bool": {"must": list(clauses)}}

def bool_should(*clauses, min_match=1):
    return {"bool": {"should": list(clauses), "minimum_should_match": min_match}}


# ── Validate DSL against ES ─────────────────────────────────────────────────

def validate(index, query_dsl):
    """Returns True if DSL executes without error."""
    try:
        es.search(index=index, body=json.loads(query_dsl), size=0)
        return True
    except Exception as e:
        print(f'  INVALID DSL: {e}')
        return False


# ── Training pair builders ──────────────────────────────────────────────────

pairs = []  # list of (index, nl_query, dsl_string)

def add(index, nl, query_dsl):
    d = dsl(query_dsl)
    if validate(index, d):
        pairs.append((index, nl, d))
    else:
        print(f'  SKIPPED: {nl}')


# ── PERSON pairs ─────────────────────────────────────────────────────────────

# Simple: name search
names = ['Ahmed', 'Mohammed', 'Fatima', 'Ali', 'Sara', 'Omar', 'Layla', 'Hassan', 'Noor', 'Khalid']
for name in names:
    add(PERSON_INDEX, f'Find person named {name}',
        match('CL_person_full_name_en', name))
    add(PERSON_INDEX, f'Search for {name}',
        match('CL_person_full_name_en', name))
    add(PERSON_INDEX, f'Show me {name}',
        match('CL_person_full_name_en', name))

# Simple: gender
for nl_gender, es_gender in [('male', 'Male'), ('female', 'Female'), ('males', 'Male'), ('females', 'Female')]:
    add(PERSON_INDEX, f'Find all {nl_gender} persons',
        term('prs_gdr', es_gender))
    add(PERSON_INDEX, f'Show all {nl_gender}',
        term('prs_gdr', es_gender))
    add(PERSON_INDEX, f'List {nl_gender} persons',
        term('prs_gdr', es_gender))

# Simple: nationality (varied phrasings — no gender, no DOB)
for nat_name, nat_code in NATIONALITIES.items():
    nat_adj = nat_name  # e.g. "Indian", "Qatari"
    # Extract noun form: "Indian" → "India", etc. (not all work, just use nat_name)
    add(PERSON_INDEX, f'Find all {nat_adj} nationals',
        term('person_natcde', nat_code))
    add(PERSON_INDEX, f'Show all {nat_adj} nationals',
        term('person_natcde', nat_code))
    add(PERSON_INDEX, f'Show {nat_adj} persons',
        term('person_natcde', nat_code))
    add(PERSON_INDEX, f'List all {nat_adj}s',
        term('person_natcde', nat_code))
    add(PERSON_INDEX, f'Show all {nat_adj} persons',
        term('person_natcde', nat_code))
    add(PERSON_INDEX, f'Find {nat_adj} people',
        term('person_natcde', nat_code))
    # "persons with X nationality" phrasing (critical gap fix)
    add(PERSON_INDEX, f'Find all persons with {nat_adj} nationality',
        term('person_natcde', nat_code))
    add(PERSON_INDEX, f'Show all persons with {nat_adj} nationality',
        term('person_natcde', nat_code))
    add(PERSON_INDEX, f'Find persons having {nat_adj} nationality',
        term('person_natcde', nat_code))

# Medium: nationality + gender
for nat_name, nat_code in NATIONALITIES.items():
    for nl_gender, es_gender in [('male', 'Male'), ('female', 'Female')]:
        add(PERSON_INDEX, f'Find {nat_name} {nl_gender}s',
            bool_must(term('person_natcde', nat_code), term('prs_gdr', es_gender)))
        add(PERSON_INDEX, f'Show all {nat_name} {nl_gender} persons',
            bool_must(term('person_natcde', nat_code), term('prs_gdr', es_gender)))

# Simple: DOB range ONLY (no gender, no nationality — critical gap fix)
for year in ['1970', '1975', '1980', '1985', '1990', '1995', '2000']:
    add(PERSON_INDEX, f'Show persons born after {year}',
        range_q('prs_dob', gte=f'{year}-01-01'))
    add(PERSON_INDEX, f'Find persons born before {year}',
        range_q('prs_dob', lte=f'{year}-12-31'))
add(PERSON_INDEX, 'Find persons born between 1980 and 1990',
    range_q('prs_dob', gte='1980-01-01', lte='1990-12-31'))
add(PERSON_INDEX, 'Show persons born between 1985 and 2000',
    range_q('prs_dob', gte='1985-01-01', lte='2000-12-31'))
add(PERSON_INDEX, 'List persons born after 1995',
    range_q('prs_dob', gte='1995-01-01'))

# Medium: gender + DOB range
for nl_gender, es_gender in [('male', 'Male'), ('female', 'Female')]:
    add(PERSON_INDEX, f'Find {nl_gender}s born after 1990',
        bool_must(term('prs_gdr', es_gender), range_q('prs_dob', gte='1990-01-01')))
    add(PERSON_INDEX, f'Show {nl_gender}s born before 1970',
        bool_must(term('prs_gdr', es_gender), range_q('prs_dob', lte='1970-12-31')))

# Medium: nationality + DOB
for nat_name, nat_code in list(NATIONALITIES.items())[:6]:
    add(PERSON_INDEX, f'Find {nat_name} persons born after 1980',
        bool_must(term('person_natcde', nat_code), range_q('prs_dob', gte='1980-01-01')))
    add(PERSON_INDEX, f'Show {nat_name} persons born before 1990',
        bool_must(term('person_natcde', nat_code), range_q('prs_dob', lte='1990-12-31')))

# Hard: nationality + gender + DOB range
for nat_name, nat_code in list(NATIONALITIES.items())[:6]:
    for nl_gender, es_gender in [('male', 'Male'), ('female', 'Female')]:
        add(PERSON_INDEX,
            f'Find {nat_name} {nl_gender}s born between 1980 and 1990',
            bool_must(
                term('person_natcde', nat_code),
                term('prs_gdr', es_gender),
                range_q('prs_dob', gte='1980-01-01', lte='1990-12-31')
            ))
        add(PERSON_INDEX,
            f'Show {nat_name} {nl_gender}s born after 1985',
            bool_must(
                term('person_natcde', nat_code),
                term('prs_gdr', es_gender),
                range_q('prs_dob', gte='1985-01-01')
            ))

# Hard: two nationalities OR
for (n1, c1), (n2, c2) in [
    (('Qatari', '634'), ('Saudi', '682')),
    (('Indian', '356'), ('Pakistani', '586')),
    (('Egyptian', '818'), ('Jordanian', '400')),
]:
    add(PERSON_INDEX, f'Find {n1} or {n2} persons',
        bool_should(term('person_natcde', c1), term('person_natcde', c2)))
    for nl_gender, es_gender in [('male', 'Male'), ('female', 'Female')]:
        add(PERSON_INDEX,
            f'Find {n1} or {n2} {nl_gender}s',
            bool_must(
                bool_should(term('person_natcde', c1), term('person_natcde', c2)),
                term('prs_gdr', es_gender)
            ))


# ── VEHICLE pairs ────────────────────────────────────────────────────────────

# Simple: plate
for plate in ['307859', 'A12345', '412300', '518822']:
    add(VEHICLE_INDEX, f'Find vehicle with plate number {plate}',
        match('VRG_PLTNUM', plate))
    add(VEHICLE_INDEX, f'Search for plate {plate}',
        match('VRG_PLTNUM', plate))

# Simple: make
for make, make_aliases in MAKE_NAMES.items():
    for alias in make_aliases[:2]:
        add(VEHICLE_INDEX, f'Show all {alias} vehicles',
            match('MNF_ENSHDESC', make))
        add(VEHICLE_INDEX, f'Find {alias} cars',
            match('MNF_ENSHDESC', make))

# Simple: color
for color, color_aliases in COLOR_NAMES.items():
    for alias in color_aliases[:2]:
        add(VEHICLE_INDEX, f'Find all {alias} vehicles',
            match('CLR_CLRENGDSC', color))
        add(VEHICLE_INDEX, f'Show {alias} cars',
            match('CLR_CLRENGDSC', color))

# Simple: status
add(VEHICLE_INDEX, 'Show all vehicles with active registration',
    match('VRG_STATUS', 'ACT'))
add(VEHICLE_INDEX, 'Find all vehicles with expired registration',
    match('VRG_STATUS', 'EXP'))
add(VEHICLE_INDEX, 'Show active vehicles',
    match('VRG_STATUS', 'ACT'))
add(VEHICLE_INDEX, 'Find expired vehicles',
    match('VRG_STATUS', 'EXP'))

# Medium: color + status ONLY (no make — critical gap fix)
for color, color_aliases in COLOR_NAMES.items():
    add(VEHICLE_INDEX, f'Find all {color_aliases[0]} vehicles with expired registration',
        bool_must(match('CLR_CLRENGDSC', color), match('VRG_STATUS', 'EXP')))
    add(VEHICLE_INDEX, f'Show {color_aliases[0]} vehicles with active registration',
        bool_must(match('CLR_CLRENGDSC', color), match('VRG_STATUS', 'ACT')))
    add(VEHICLE_INDEX, f'Find {color_aliases[0]} expired vehicles',
        bool_must(match('CLR_CLRENGDSC', color), match('VRG_STATUS', 'EXP')))

# Medium: make + color
for make, make_aliases in MAKE_NAMES.items():
    for color, color_aliases in COLOR_NAMES.items():
        add(VEHICLE_INDEX,
            f'Find {color_aliases[0]} {make_aliases[0]} vehicles',
            bool_must(match('MNF_ENSHDESC', make), match('CLR_CLRENGDSC', color)))

# Medium: make + status
for make, make_aliases in MAKE_NAMES.items():
    add(VEHICLE_INDEX, f'Find {make_aliases[0]} vehicles with active registration',
        bool_must(match('MNF_ENSHDESC', make), match('VRG_STATUS', 'ACT')))
    add(VEHICLE_INDEX, f'Find {make_aliases[0]} vehicles with expired registration',
        bool_must(match('MNF_ENSHDESC', make), match('VRG_STATUS', 'EXP')))

# Medium: make + model year (VEH_MODELYEAR)
for make, make_aliases in MAKE_NAMES.items():
    for year in YEARS:
        add(VEHICLE_INDEX, f'Show {make_aliases[0]} vehicles from {year}',
            bool_must(match('MNF_ENSHDESC', make), term('VEH_MODELYEAR', year)))

# Medium: make + registered in year (VRG_STADTE range — critical gap fix)
for make, make_aliases in MAKE_NAMES.items():
    for year in YEARS:
        add(VEHICLE_INDEX, f'Find {make_aliases[0]} vehicles registered in {year}',
            bool_must(
                match('MNF_ENSHDESC', make),
                range_q('VRG_STADTE', gte=f'{year}-01-01', lte=f'{year}-12-31')
            ))
        add(VEHICLE_INDEX, f'Show {make_aliases[0]} registered in {year}',
            bool_must(
                match('MNF_ENSHDESC', make),
                range_q('VRG_STADTE', gte=f'{year}-01-01', lte=f'{year}-12-31')
            ))

# Medium: expiry date range (VRG_ENDDT — registration END date)
for year in ['2022', '2023', '2024', '2025']:
    add(VEHICLE_INDEX, f'Show all vehicles with registration expiring before {year}',
        range_q('VRG_ENDDT', lt=f'{year}-01-01'))
    add(VEHICLE_INDEX, f'Find vehicles with registration expiring before {year}',
        range_q('VRG_ENDDT', lt=f'{year}-01-01'))
    add(VEHICLE_INDEX, f'Show vehicles whose registration expires before {year}',
        range_q('VRG_ENDDT', lt=f'{year}-01-01'))
    add(VEHICLE_INDEX, f'Find vehicles with expired registration before {year}',
        range_q('VRG_ENDDT', lt=f'{year}-01-01'))
add(VEHICLE_INDEX, 'Show all vehicles with registration expiring before 2024',
    range_q('VRG_ENDDT', lt='2024-01-01'))
add(VEHICLE_INDEX, 'Find vehicles with registration expired before 2023',
    range_q('VRG_ENDDT', lt='2023-01-01'))

# Medium: registration start date range (VRG_STADTE — when registration began)
add(VEHICLE_INDEX, 'Show vehicles registered after 2021',
    range_q('VRG_STADTE', gte='2021-01-01'))
add(VEHICLE_INDEX, 'Find vehicles registered between 2020 and 2022',
    range_q('VRG_STADTE', gte='2020-01-01', lte='2022-12-31'))

# Hard: make + color + status
for make, make_aliases in MAKE_NAMES.items():
    for color, color_aliases in COLOR_NAMES.items():
        add(VEHICLE_INDEX,
            f'Find {color_aliases[0]} {make_aliases[0]} vehicles with active registration',
            bool_must(
                match('MNF_ENSHDESC', make),
                match('CLR_CLRENGDSC', color),
                match('VRG_STATUS', 'ACT')
            ))

# Hard: make + model + year range
for make in ['TOYOTA', 'NISSAN']:
    for model in MODELS[make][:2]:
        add(VEHICLE_INDEX,
            f'Find {MAKE_NAMES[make][0]} {model.title()} registered between 2020 and 2023',
            bool_must(
                match('MNF_ENSHDESC', make),
                match('VEH_MODEL', model),
                range_q('VRG_STADTE', gte='2020-01-01', lte='2023-12-31')
            ))

# Hard: two makes OR
for (m1, m2) in [('TOYOTA', 'NISSAN'), ('BMW', 'KIA')]:
    a1, a2 = MAKE_NAMES[m1][0], MAKE_NAMES[m2][0]
    add(VEHICLE_INDEX, f'Find {a1} or {a2} vehicles',
        bool_should(match('MNF_ENSHDESC', m1), match('MNF_ENSHDESC', m2)))
    for color, color_aliases in COLOR_NAMES.items():
        add(VEHICLE_INDEX,
            f'Find {a1} or {a2} vehicles that are {color_aliases[0].lower()}',
            bool_must(
                bool_should(match('MNF_ENSHDESC', m1), match('MNF_ENSHDESC', m2)),
                match('CLR_CLRENGDSC', color)
            ))

# Hard: two makes OR + two colors OR (nested should×2 — critical gap fix)
for (m1, m2) in [('TOYOTA', 'NISSAN'), ('BMW', 'KIA'), ('TOYOTA', 'KIA')]:
    a1, a2 = MAKE_NAMES[m1][0], MAKE_NAMES[m2][0]
    for (c1, c2) in [('WHITE', 'SILVER'), ('WHITE', 'BLACK'), ('BLACK', 'SILVER')]:
        cn1, cn2 = COLOR_NAMES[c1][0].lower(), COLOR_NAMES[c2][0].lower()
        add(VEHICLE_INDEX,
            f'Find {a1} or {a2} vehicles that are {cn1} or {cn2}',
            bool_must(
                bool_should(match('MNF_ENSHDESC', m1), match('MNF_ENSHDESC', m2)),
                bool_should(match('CLR_CLRENGDSC', c1), match('CLR_CLRENGDSC', c2))
            ))
        add(VEHICLE_INDEX,
            f'Show {a1} or {a2} {cn1} or {cn2} vehicles',
            bool_must(
                bool_should(match('MNF_ENSHDESC', m1), match('MNF_ENSHDESC', m2)),
                bool_should(match('CLR_CLRENGDSC', c1), match('CLR_CLRENGDSC', c2))
            ))


# ── VIOLATIONS pairs ─────────────────────────────────────────────────────────

# Simple: type
for nl_type, es_type in VLN_TYPES.items():
    add(VIOLATIONS_INDEX, f'Find all {nl_type} violations',
        term('VLN_TYPE', es_type))
    add(VIOLATIONS_INDEX, f'Show {nl_type} violations',
        term('VLN_TYPE', es_type))

# Simple: status
for nl_status, es_status in VLN_STATUSES.items():
    add(VIOLATIONS_INDEX, f'Show all {nl_status} violations',
        term('VLN_STATUS', es_status))
    add(VIOLATIONS_INDEX, f'Find {nl_status} violations',
        term('VLN_STATUS', es_status))

# Simple: location
for loc, loc_aliases in LOCATION_NAMES.items():
    for alias in loc_aliases[:2]:
        add(VIOLATIONS_INDEX, f'Find violations on {alias}',
            term('VLN_PLCDSC', loc))
        add(VIOLATIONS_INDEX, f'Show violations at {alias}',
            term('VLN_PLCDSC', loc))

# Medium: type + status (varied phrasings to prevent duplicate-term hallucinations)
for nl_type, es_type in list(VLN_TYPES.items())[:5]:
    for nl_status, es_status in VLN_STATUSES.items():
        add(VIOLATIONS_INDEX, f'Find {nl_status} {nl_type} violations',
            bool_must(term('VLN_TYPE', es_type), term('VLN_STATUS', es_status)))
        add(VIOLATIONS_INDEX, f'Show {nl_type} violations that are {nl_status}',
            bool_must(term('VLN_TYPE', es_type), term('VLN_STATUS', es_status)))
        add(VIOLATIONS_INDEX, f'List {nl_status} {nl_type} fines',
            bool_must(term('VLN_TYPE', es_type), term('VLN_STATUS', es_status)))

# Medium: type + location
for nl_type, es_type in [('speeding', 'SPEEDING'), ('parking', 'PARKING'), ('red light', 'RED_LIGHT')]:
    for loc, loc_aliases in list(LOCATION_NAMES.items())[:4]:
        add(VIOLATIONS_INDEX,
            f'Find {nl_type} violations on {loc_aliases[0]}',
            bool_must(term('VLN_TYPE', es_type), term('VLN_PLCDSC', loc)))

# Medium: fine range
for threshold in [500, 1000, 1500, 3000]:
    add(VIOLATIONS_INDEX, f'Show violations with fine greater than {threshold}',
        range_q('VLN_TOTAMT', gt=threshold))
    add(VIOLATIONS_INDEX, f'Find violations with fine over {threshold} QAR',
        range_q('VLN_TOTAMT', gt=threshold))
    add(VIOLATIONS_INDEX, f'Show violations with fine less than {threshold}',
        range_q('VLN_TOTAMT', lt=threshold))

# Medium: year
for year in ['2024', '2023']:
    add(VIOLATIONS_INDEX, f'Find all violations from {year}',
        term('VLN_YEAR', year))
    add(VIOLATIONS_INDEX, f'Show {year} violations',
        term('VLN_YEAR', year))

# Hard: type + status + location
for nl_type, es_type in [('speeding', 'SPEEDING'), ('parking', 'PARKING')]:
    for nl_status, es_status in [('unpaid', 'UNPAID'), ('paid', 'PAID')]:
        for loc, loc_aliases in list(LOCATION_NAMES.items())[:3]:
            add(VIOLATIONS_INDEX,
                f'Find {nl_status} {nl_type} violations on {loc_aliases[0]}',
                bool_must(
                    term('VLN_TYPE', es_type),
                    term('VLN_STATUS', es_status),
                    term('VLN_PLCDSC', loc)
                ))

# Hard: fine + status (no type — critical gap: VLN_STATUS not VLN_TYPE)
for nl_status, es_status in [('unpaid', 'UNPAID'), ('paid', 'PAID')]:
    for threshold in [500, 1000, 1500, 3000]:
        add(VIOLATIONS_INDEX,
            f'Show violations with fine greater than {threshold} that are {nl_status}',
            bool_must(range_q('VLN_TOTAMT', gt=threshold), term('VLN_STATUS', es_status)))
        add(VIOLATIONS_INDEX,
            f'Find {nl_status} violations with fine over {threshold}',
            bool_must(term('VLN_STATUS', es_status), range_q('VLN_TOTAMT', gt=threshold)))
        add(VIOLATIONS_INDEX,
            f'Show {nl_status} fines greater than {threshold}',
            bool_must(term('VLN_STATUS', es_status), range_q('VLN_TOTAMT', gt=threshold)))
    for threshold in [500, 1000]:
        add(VIOLATIONS_INDEX,
            f'Find violations fine over {threshold} that are {nl_status}',
            bool_must(range_q('VLN_TOTAMT', gt=threshold), term('VLN_STATUS', es_status)))

# Hard: type + status + fine range
for nl_type, es_type in [('speeding', 'SPEEDING'), ('red light', 'RED_LIGHT')]:
    for nl_status, es_status in [('unpaid', 'UNPAID')]:
        for threshold in [1000, 3000]:
            add(VIOLATIONS_INDEX,
                f'Find {nl_status} {nl_type} violations with fine over {threshold}',
                bool_must(
                    term('VLN_TYPE', es_type),
                    term('VLN_STATUS', es_status),
                    range_q('VLN_TOTAMT', gt=threshold)
                ))

# Hard: type + date range
for nl_type, es_type in [('speeding', 'SPEEDING'), ('parking', 'PARKING')]:
    add(VIOLATIONS_INDEX,
        f'Find {nl_type} violations from 2024',
        bool_must(
            term('VLN_TYPE', es_type),
            range_q('VLN_DATE_DATE', gte='2024-01-01', lte='2024-12-31')
        ))

# Hard: status + fine + date
add(VIOLATIONS_INDEX,
    'Find unpaid violations with fine over 1000 from 2024',
    bool_must(
        term('VLN_STATUS', 'UNPAID'),
        range_q('VLN_TOTAMT', gt=1000),
        range_q('VLN_DATE_DATE', gte='2024-01-01', lte='2024-12-31')
    ))

add(VIOLATIONS_INDEX,
    'Show unpaid violations from Al Rayyan Road with fine over 3000',
    bool_must(
        term('VLN_STATUS', 'UNPAID'),
        term('VLN_PLCDSC', 'AL RAYYAN ROAD'),
        range_q('VLN_TOTAMT', gt=3000)
    ))


# ── Format and write ─────────────────────────────────────────────────────────

print(f'\nTotal valid pairs: {len(pairs)}')

# Shuffle and split 85/15
random.shuffle(pairs)
split = int(len(pairs) * 0.85)
train_pairs = pairs[:split]
valid_pairs = pairs[split:]

print(f'Train: {len(train_pairs)} | Valid: {len(valid_pairs)}')

# Breakdown by index
for name, idx in [('Person', PERSON_INDEX), ('Vehicle', VEHICLE_INDEX), ('Violations', VIOLATIONS_INDEX)]:
    count = sum(1 for p in pairs if p[0] == idx)
    print(f'  {name}: {count} pairs')

os.makedirs('data/training', exist_ok=True)

def write_jsonl(path, data):
    with open(path, 'w') as f:
        for _, nl, dsl_str in data:
            record = {
                "messages": [
                    {"role": "user", "content": nl},
                    {"role": "assistant", "content": dsl_str}
                ]
            }
            f.write(json.dumps(record) + '\n')
    print(f'Written: {path}')

write_jsonl('data/training/train.jsonl', train_pairs)
write_jsonl('data/training/valid.jsonl', valid_pairs)
print('Done.')

"""
Generate multi-index training data for Phase 2 LoRA fine-tuning.

Each pair: NL query → query plan JSON (multi_index format with steps)

All plans are validated by executing step-by-step against real ES.
Output is APPENDED to existing train.jsonl / valid.jsonl (keeps Phase 1 pairs).
"""

import json
import random
import os
from elasticsearch import Elasticsearch

random.seed(99)

es = Elasticsearch(['http://localhost:9200'], basic_auth=('elastic', 'elastic'))

PERSON_INDEX = 'moi-gp-all-profiles-details-v1'
VEHICLE_INDEX = 'moi-vehicle-info-v1'
VIOLATIONS_INDEX = 'moi-violations-v1'

NATIONALITIES = {
    'Qatari': '634', 'Pakistani': '586', 'Indian': '356',
    'Egyptian': '818', 'Saudi': '682', 'Emirati': '784',
}
GENDERS = [('male', 'Male'), ('female', 'Female')]

VLN_TYPES = {
    'speeding': 'SPEEDING', 'red light': 'RED_LIGHT',
    'parking': 'PARKING', 'seatbelt': 'SEATBELT', 'mobile phone': 'MOBILE_PHONE',
}
VLN_STATUSES = [('unpaid', 'UNPAID'), ('paid', 'PAID')]
MAKES = {'Toyota': 'TOYOTA', 'Nissan': 'NISSAN', 'BMW': 'BMW', 'KIA': 'KIA'}
COLORS = {'white': 'WHITE', 'black': 'BLACK', 'silver': 'SILVER'}
VEH_STATUSES = [('active', 'ACT'), ('expired', 'EXP')]


# ── DSL helpers ──────────────────────────────────────────────────────────────

def term(field, value):
    return {'term': {field: value}}

def match(field, value):
    return {'match': {field: value}}

def terms_placeholder(field, step):
    return {'terms': {field: f'$step_{step}'}}

def bool_must(*clauses):
    return {'bool': {'must': list(clauses)}}

def bool_should(*clauses):
    return {'bool': {'should': list(clauses), 'minimum_should_match': 1}}

def plan(steps):
    return {'type': 'multi_index', 'steps': steps}

def step(num, index, query, extract_field=None):
    s = {'step': num, 'index': index, 'query': query}
    if extract_field:
        s['extract_field'] = extract_field
    return s


# ── Validate plan against ES ─────────────────────────────────────────────────

def validate_plan(p):
    """Execute each step with real IDs to confirm plan is valid."""
    step_results = {}
    for s in p['steps']:
        q = s['query']
        # Inject previous step results
        q_json = json.dumps(q)
        for step_num, ids in step_results.items():
            q_json = q_json.replace(f'"$step_{step_num}"', json.dumps(ids))
        q = json.loads(q_json)
        try:
            res = es.search(index=s['index'], body={'query': q, 'size': 100})
        except Exception as e:
            print(f'  INVALID: {e}')
            return False
        if s.get('extract_field'):
            ids = list(set(
                str(h['_source'].get(s['extract_field']))
                for h in res['hits']['hits']
                if h['_source'].get(s['extract_field'])
            ))
            step_results[s['step']] = ids
    return True


# ── Training pairs ───────────────────────────────────────────────────────────

pairs = []

def add(nl, query_plan):
    p = query_plan
    if validate_plan(p):
        pairs.append((nl, json.dumps(p, separators=(',', ':'))))
    else:
        print(f'  SKIPPED: {nl}')


# ── Person → Violations joins ────────────────────────────────────────────────

# Nationality + violation type
for nat_name, nat_code in NATIONALITIES.items():
    for vln_nl, vln_type in VLN_TYPES.items():
        add(
            f'Find {vln_nl} violations for {nat_name} nationals',
            plan([
                step(1, PERSON_INDEX, term('person_natcde', nat_code), 'prs_qid'),
                step(2, VIOLATIONS_INDEX, bool_must(
                    terms_placeholder('VLN_OWNQID', 1),
                    term('VLN_TYPE', vln_type)
                ))
            ])
        )
        add(
            f'Show {vln_nl} violations by {nat_name} drivers',
            plan([
                step(1, PERSON_INDEX, term('person_natcde', nat_code), 'prs_qid'),
                step(2, VIOLATIONS_INDEX, bool_must(
                    terms_placeholder('VLN_OWNQID', 1),
                    term('VLN_TYPE', vln_type)
                ))
            ])
        )

# Nationality + violation status
for nat_name, nat_code in NATIONALITIES.items():
    for vln_status_nl, vln_status in VLN_STATUSES:
        add(
            f'Find {vln_status_nl} violations for {nat_name} nationals',
            plan([
                step(1, PERSON_INDEX, term('person_natcde', nat_code), 'prs_qid'),
                step(2, VIOLATIONS_INDEX, bool_must(
                    terms_placeholder('VLN_OWNQID', 1),
                    term('VLN_STATUS', vln_status)
                ))
            ])
        )
        add(
            f'Show {nat_name} {vln_status_nl} fines',
            plan([
                step(1, PERSON_INDEX, term('person_natcde', nat_code), 'prs_qid'),
                step(2, VIOLATIONS_INDEX, bool_must(
                    terms_placeholder('VLN_OWNQID', 1),
                    term('VLN_STATUS', vln_status)
                ))
            ])
        )

# Gender + violation type
for gender_nl, gender_es in GENDERS:
    for vln_nl, vln_type in VLN_TYPES.items():
        add(
            f'Find {vln_nl} violations for {gender_nl} drivers',
            plan([
                step(1, PERSON_INDEX, term('prs_gdr', gender_es), 'prs_qid'),
                step(2, VIOLATIONS_INDEX, bool_must(
                    terms_placeholder('VLN_OWNQID', 1),
                    term('VLN_TYPE', vln_type)
                ))
            ])
        )

# Nationality + gender + violation type (3-clause on person side)
for nat_name, nat_code in list(NATIONALITIES.items())[:4]:
    for gender_nl, gender_es in GENDERS:
        for vln_nl, vln_type in list(VLN_TYPES.items())[:3]:
            add(
                f'Find {vln_nl} violations for {nat_name} {gender_nl}s',
                plan([
                    step(1, PERSON_INDEX,
                         bool_must(term('person_natcde', nat_code), term('prs_gdr', gender_es)),
                         'prs_qid'),
                    step(2, VIOLATIONS_INDEX, bool_must(
                        terms_placeholder('VLN_OWNQID', 1),
                        term('VLN_TYPE', vln_type)
                    ))
                ])
            )

# Nationality + violation type + status (3-clause on violation side)
for nat_name, nat_code in list(NATIONALITIES.items())[:4]:
    for vln_nl, vln_type in list(VLN_TYPES.items())[:3]:
        for vln_status_nl, vln_status in VLN_STATUSES:
            add(
                f'Find {vln_status_nl} {vln_nl} violations for {nat_name} nationals',
                plan([
                    step(1, PERSON_INDEX, term('person_natcde', nat_code), 'prs_qid'),
                    step(2, VIOLATIONS_INDEX, bool_must(
                        terms_placeholder('VLN_OWNQID', 1),
                        term('VLN_TYPE', vln_type),
                        term('VLN_STATUS', vln_status)
                    ))
                ])
            )

# All violations for nationality (no type/status filter)
for nat_name, nat_code in NATIONALITIES.items():
    add(
        f'Find all violations for {nat_name} nationals',
        plan([
            step(1, PERSON_INDEX, term('person_natcde', nat_code), 'prs_qid'),
            step(2, VIOLATIONS_INDEX, bool_must(terms_placeholder('VLN_OWNQID', 1)))
        ])
    )
    add(
        f'Show violations belonging to {nat_name} drivers',
        plan([
            step(1, PERSON_INDEX, term('person_natcde', nat_code), 'prs_qid'),
            step(2, VIOLATIONS_INDEX, bool_must(terms_placeholder('VLN_OWNQID', 1)))
        ])
    )


# ── Person → Vehicle joins ───────────────────────────────────────────────────

# Nationality + make
for nat_name, nat_code in NATIONALITIES.items():
    for make_nl, make_es in MAKES.items():
        add(
            f'Find {make_nl} vehicles owned by {nat_name} nationals',
            plan([
                step(1, PERSON_INDEX, term('person_natcde', nat_code), 'prs_qid'),
                step(2, VEHICLE_INDEX, bool_must(
                    terms_placeholder('VRG_OWNQID', 1),
                    match('MNF_ENSHDESC', make_es)
                ))
            ])
        )
        add(
            f'Show {make_nl} cars belonging to {nat_name} people',
            plan([
                step(1, PERSON_INDEX, term('person_natcde', nat_code), 'prs_qid'),
                step(2, VEHICLE_INDEX, bool_must(
                    terms_placeholder('VRG_OWNQID', 1),
                    match('MNF_ENSHDESC', make_es)
                ))
            ])
        )

# Nationality + vehicle status
for nat_name, nat_code in NATIONALITIES.items():
    for veh_status_nl, veh_status_es in VEH_STATUSES:
        add(
            f'Find vehicles with {veh_status_nl} registration owned by {nat_name} nationals',
            plan([
                step(1, PERSON_INDEX, term('person_natcde', nat_code), 'prs_qid'),
                step(2, VEHICLE_INDEX, bool_must(
                    terms_placeholder('VRG_OWNQID', 1),
                    match('VRG_STATUS', veh_status_es)
                ))
            ])
        )

# Nationality + color
for nat_name, nat_code in list(NATIONALITIES.items())[:4]:
    for color_nl, color_es in COLORS.items():
        add(
            f'Find {color_nl} vehicles owned by {nat_name} nationals',
            plan([
                step(1, PERSON_INDEX, term('person_natcde', nat_code), 'prs_qid'),
                step(2, VEHICLE_INDEX, bool_must(
                    terms_placeholder('VRG_OWNQID', 1),
                    match('CLR_CLRENGDSC', color_es)
                ))
            ])
        )

# Gender + make
for gender_nl, gender_es in GENDERS:
    for make_nl, make_es in MAKES.items():
        add(
            f'Find {make_nl} vehicles owned by {gender_nl} drivers',
            plan([
                step(1, PERSON_INDEX, term('prs_gdr', gender_es), 'prs_qid'),
                step(2, VEHICLE_INDEX, bool_must(
                    terms_placeholder('VRG_OWNQID', 1),
                    match('MNF_ENSHDESC', make_es)
                ))
            ])
        )

# All vehicles for nationality
for nat_name, nat_code in NATIONALITIES.items():
    add(
        f'Find all vehicles owned by {nat_name} nationals',
        plan([
            step(1, PERSON_INDEX, term('person_natcde', nat_code), 'prs_qid'),
            step(2, VEHICLE_INDEX, bool_must(terms_placeholder('VRG_OWNQID', 1)))
        ])
    )
    add(
        f'Show vehicles registered to {nat_name} persons',
        plan([
            step(1, PERSON_INDEX, term('person_natcde', nat_code), 'prs_qid'),
            step(2, VEHICLE_INDEX, bool_must(terms_placeholder('VRG_OWNQID', 1)))
        ])
    )


# ── Write output ─────────────────────────────────────────────────────────────

print(f'\nTotal valid multi-index pairs: {len(pairs)}')

random.shuffle(pairs)
split = int(len(pairs) * 0.85)
train_pairs = pairs[:split]
valid_pairs = pairs[split:]
print(f'Train: {len(train_pairs)} | Valid: {len(valid_pairs)}')

os.makedirs('data/training', exist_ok=True)

# APPEND to existing files (keeps Phase 1 single-index pairs)
def append_jsonl(path, data):
    with open(path, 'a') as f:
        for nl, plan_str in data:
            record = {
                'messages': [
                    {'role': 'user', 'content': nl},
                    {'role': 'assistant', 'content': plan_str}
                ]
            }
            f.write(json.dumps(record) + '\n')
    print(f'Appended to: {path}')

append_jsonl('data/training/train.jsonl', train_pairs)
append_jsonl('data/training/valid.jsonl', valid_pairs)
print('Done.')

"""
Ingestion script for moi-violations-v1 index.

Creates the index with the Phase 1 mapping and loads test data covering:
- Simple queries: by violation type, status, year
- Medium queries: by date range, fine amount, location
- Hard queries: multi-criteria (type + location + date, speed > X, etc.)

Usage:
    python data/ingest_violations.py
"""

import json
from pathlib import Path
from elasticsearch import Elasticsearch
from dotenv import load_dotenv
import os

load_dotenv()

INDEX_NAME = "moi-violations-v1"

MAPPING = {
    "mappings": {
        "properties": {
            "VLN_NUMBER":   {"type": "keyword", "ignore_above": 1024},
            "VLN_TYPE":     {"type": "keyword", "ignore_above": 1024},
            "VLC_ENGDSC":   {"type": "keyword", "ignore_above": 1024},
            "VLN_STATUS":   {"type": "keyword", "ignore_above": 1024},
            "VLN_YEAR":     {"type": "keyword", "ignore_above": 1024},
            "VLN_DATE_DATE": {"type": "date"},
            "VLN_DATE_TIME": {"type": "date"},
            "VLN_TOTAMT":   {"type": "float"},
            "VLN_PLCDSC":   {"type": "keyword", "ignore_above": 1024},
            "VLN_ZONE_NO":  {"type": "integer"},
            "VLN_STREET_NO": {"type": "keyword", "ignore_above": 1024},
            "VLN_PLTNUM":   {"type": "keyword", "ignore_above": 1024},
            "VEH_MANUF":    {"type": "keyword", "ignore_above": 1024},
            "VEH_MODEL":    {"type": "keyword", "ignore_above": 1024},
            "RDR_PICSPD":   {"type": "keyword", "ignore_above": 1024},
            "VLN_OWNQID":   {"type": "keyword", "ignore_above": 1024},
            "VLN_LICQIDNO": {"type": "keyword", "ignore_above": 1024},
            "CHARGES": {
                "type": "nested",
                "properties": {
                    "VLC_ENGDSC": {"type": "keyword", "ignore_above": 256},
                    "VTK_TARAMT": {"type": "keyword", "ignore_above": 256}
                }
            }
        }
    }
}

TEST_DATA = [
    # Speeding violations
    {
        "VLN_NUMBER": "VLN-2024-001",
        "VLN_TYPE": "SPEEDING",
        "VLC_ENGDSC": "Exceeding speed limit by more than 60 km/h",
        "VLN_STATUS": "UNPAID",
        "VLN_YEAR": "2024",
        "VLN_DATE_DATE": "2024-03-15",
        "VLN_DATE_TIME": "2024-03-15T08:30:00",
        "VLN_TOTAMT": 3000.0,
        "VLN_PLCDSC": "CORNICHE ROAD",
        "VLN_ZONE_NO": 1,
        "VLN_STREET_NO": "12",
        "VLN_PLTNUM": "AA1234",
        "VEH_MANUF": "TOYOTA",
        "VEH_MODEL": "LAND CRUISER",
        "RDR_PICSPD": "180",
        "VLN_OWNQID": "28501234567",
        "VLN_LICQIDNO": "28501234567",
        "CHARGES": [{"VLC_ENGDSC": "SPEEDING FINE", "VTK_TARAMT": "3000"}]
    },
    {
        "VLN_NUMBER": "VLN-2024-002",
        "VLN_TYPE": "SPEEDING",
        "VLC_ENGDSC": "Exceeding speed limit by 20-40 km/h",
        "VLN_STATUS": "PAID",
        "VLN_YEAR": "2024",
        "VLN_DATE_DATE": "2024-04-10",
        "VLN_DATE_TIME": "2024-04-10T14:15:00",
        "VLN_TOTAMT": 600.0,
        "VLN_PLCDSC": "AL WAAB STREET",
        "VLN_ZONE_NO": 3,
        "VLN_STREET_NO": "45",
        "VLN_PLTNUM": "BB5678",
        "VEH_MANUF": "NISSAN",
        "VEH_MODEL": "PATROL",
        "RDR_PICSPD": "140",
        "VLN_OWNQID": "29301234568",
        "VLN_LICQIDNO": "29301234568",
        "CHARGES": [{"VLC_ENGDSC": "SPEEDING FINE", "VTK_TARAMT": "600"}]
    },
    {
        "VLN_NUMBER": "VLN-2024-003",
        "VLN_TYPE": "SPEEDING",
        "VLC_ENGDSC": "Exceeding speed limit by more than 60 km/h",
        "VLN_STATUS": "UNPAID",
        "VLN_YEAR": "2024",
        "VLN_DATE_DATE": "2024-06-22",
        "VLN_DATE_TIME": "2024-06-22T23:45:00",
        "VLN_TOTAMT": 3000.0,
        "VLN_PLCDSC": "SALWA ROAD",
        "VLN_ZONE_NO": 5,
        "VLN_STREET_NO": "88",
        "VLN_PLTNUM": "CC9012",
        "VEH_MANUF": "BMW",
        "VEH_MODEL": "M5",
        "RDR_PICSPD": "195",
        "VLN_OWNQID": "27801234569",
        "VLN_LICQIDNO": "27801234569",
        "CHARGES": [{"VLC_ENGDSC": "SPEEDING FINE", "VTK_TARAMT": "3000"}]
    },
    # Red light violations
    {
        "VLN_NUMBER": "VLN-2024-004",
        "VLN_TYPE": "RED_LIGHT",
        "VLC_ENGDSC": "Jumping red light",
        "VLN_STATUS": "PAID",
        "VLN_YEAR": "2024",
        "VLN_DATE_DATE": "2024-01-20",
        "VLN_DATE_TIME": "2024-01-20T07:10:00",
        "VLN_TOTAMT": 6000.0,
        "VLN_PLCDSC": "AL RAYYAN ROAD",
        "VLN_ZONE_NO": 2,
        "VLN_STREET_NO": "33",
        "VLN_PLTNUM": "DD3456",
        "VEH_MANUF": "MERCEDES",
        "VEH_MODEL": "GLE",
        "RDR_PICSPD": None,
        "VLN_OWNQID": "28901234570",
        "VLN_LICQIDNO": "28901234570",
        "CHARGES": [{"VLC_ENGDSC": "RED LIGHT FINE", "VTK_TARAMT": "6000"}]
    },
    {
        "VLN_NUMBER": "VLN-2024-005",
        "VLN_TYPE": "RED_LIGHT",
        "VLC_ENGDSC": "Jumping red light",
        "VLN_STATUS": "UNPAID",
        "VLN_YEAR": "2024",
        "VLN_DATE_DATE": "2024-09-05",
        "VLN_DATE_TIME": "2024-09-05T18:30:00",
        "VLN_TOTAMT": 6000.0,
        "VLN_PLCDSC": "CORNICHE ROAD",
        "VLN_ZONE_NO": 1,
        "VLN_STREET_NO": "7",
        "VLN_PLTNUM": "EE7890",
        "VEH_MANUF": "TOYOTA",
        "VEH_MODEL": "CAMRY",
        "RDR_PICSPD": None,
        "VLN_OWNQID": "27501234571",
        "VLN_LICQIDNO": "27501234571",
        "CHARGES": [{"VLC_ENGDSC": "RED LIGHT FINE", "VTK_TARAMT": "6000"}]
    },
    # Parking violations
    {
        "VLN_NUMBER": "VLN-2024-006",
        "VLN_TYPE": "PARKING",
        "VLC_ENGDSC": "Parking in no-parking zone",
        "VLN_STATUS": "PAID",
        "VLN_YEAR": "2024",
        "VLN_DATE_DATE": "2024-02-14",
        "VLN_DATE_TIME": "2024-02-14T11:00:00",
        "VLN_TOTAMT": 500.0,
        "VLN_PLCDSC": "AL SADD STREET",
        "VLN_ZONE_NO": 4,
        "VLN_STREET_NO": "21",
        "VLN_PLTNUM": "FF1122",
        "VEH_MANUF": "KIA",
        "VEH_MODEL": "SPORTAGE",
        "RDR_PICSPD": None,
        "VLN_OWNQID": "29101234572",
        "VLN_LICQIDNO": "29101234572",
        "CHARGES": [{"VLC_ENGDSC": "ILLEGAL PARKING", "VTK_TARAMT": "500"}]
    },
    {
        "VLN_NUMBER": "VLN-2024-007",
        "VLN_TYPE": "PARKING",
        "VLC_ENGDSC": "Parking in disabled zone without permit",
        "VLN_STATUS": "UNPAID",
        "VLN_YEAR": "2024",
        "VLN_DATE_DATE": "2024-07-30",
        "VLN_DATE_TIME": "2024-07-30T15:20:00",
        "VLN_TOTAMT": 1000.0,
        "VLN_PLCDSC": "HAMAD HOSPITAL STREET",
        "VLN_ZONE_NO": 6,
        "VLN_STREET_NO": "5",
        "VLN_PLTNUM": "GG3344",
        "VEH_MANUF": "HONDA",
        "VEH_MODEL": "CRV",
        "RDR_PICSPD": None,
        "VLN_OWNQID": "28201234573",
        "VLN_LICQIDNO": "28201234573",
        "CHARGES": [{"VLC_ENGDSC": "DISABLED ZONE PARKING", "VTK_TARAMT": "1000"}]
    },
    # Seatbelt violations
    {
        "VLN_NUMBER": "VLN-2024-008",
        "VLN_TYPE": "SEATBELT",
        "VLC_ENGDSC": "Not wearing seatbelt",
        "VLN_STATUS": "PAID",
        "VLN_YEAR": "2024",
        "VLN_DATE_DATE": "2024-05-18",
        "VLN_DATE_TIME": "2024-05-18T09:45:00",
        "VLN_TOTAMT": 500.0,
        "VLN_PLCDSC": "AL MATAR STREET",
        "VLN_ZONE_NO": 7,
        "VLN_STREET_NO": "60",
        "VLN_PLTNUM": "HH5566",
        "VEH_MANUF": "HYUNDAI",
        "VEH_MODEL": "TUCSON",
        "RDR_PICSPD": None,
        "VLN_OWNQID": "27901234574",
        "VLN_LICQIDNO": "27901234574",
        "CHARGES": [{"VLC_ENGDSC": "SEATBELT VIOLATION", "VTK_TARAMT": "500"}]
    },
    # Mobile phone violations
    {
        "VLN_NUMBER": "VLN-2024-009",
        "VLN_TYPE": "MOBILE_PHONE",
        "VLC_ENGDSC": "Using mobile phone while driving",
        "VLN_STATUS": "UNPAID",
        "VLN_YEAR": "2024",
        "VLN_DATE_DATE": "2024-08-12",
        "VLN_DATE_TIME": "2024-08-12T13:00:00",
        "VLN_TOTAMT": 1500.0,
        "VLN_PLCDSC": "AL WAAB STREET",
        "VLN_ZONE_NO": 3,
        "VLN_STREET_NO": "77",
        "VLN_PLTNUM": "II7788",
        "VEH_MANUF": "FORD",
        "VEH_MODEL": "EXPLORER",
        "RDR_PICSPD": None,
        "VLN_OWNQID": "28601234575",
        "VLN_LICQIDNO": "28601234575",
        "CHARGES": [{"VLC_ENGDSC": "MOBILE PHONE VIOLATION", "VTK_TARAMT": "1500"}]
    },
    # 2023 violations (for date range queries)
    {
        "VLN_NUMBER": "VLN-2023-001",
        "VLN_TYPE": "SPEEDING",
        "VLC_ENGDSC": "Exceeding speed limit by 40-60 km/h",
        "VLN_STATUS": "PAID",
        "VLN_YEAR": "2023",
        "VLN_DATE_DATE": "2023-11-10",
        "VLN_DATE_TIME": "2023-11-10T20:00:00",
        "VLN_TOTAMT": 1500.0,
        "VLN_PLCDSC": "SALWA ROAD",
        "VLN_ZONE_NO": 5,
        "VLN_STREET_NO": "100",
        "VLN_PLTNUM": "JJ9900",
        "VEH_MANUF": "LEXUS",
        "VEH_MODEL": "LX570",
        "RDR_PICSPD": "160",
        "VLN_OWNQID": "27701234576",
        "VLN_LICQIDNO": "27701234576",
        "CHARGES": [{"VLC_ENGDSC": "SPEEDING FINE", "VTK_TARAMT": "1500"}]
    },
    {
        "VLN_NUMBER": "VLN-2023-002",
        "VLN_TYPE": "RED_LIGHT",
        "VLC_ENGDSC": "Jumping red light",
        "VLN_STATUS": "PAID",
        "VLN_YEAR": "2023",
        "VLN_DATE_DATE": "2023-06-25",
        "VLN_DATE_TIME": "2023-06-25T07:55:00",
        "VLN_TOTAMT": 6000.0,
        "VLN_PLCDSC": "AL RAYYAN ROAD",
        "VLN_ZONE_NO": 2,
        "VLN_STREET_NO": "14",
        "VLN_PLTNUM": "KK1234",
        "VEH_MANUF": "GMC",
        "VEH_MODEL": "YUKON",
        "RDR_PICSPD": None,
        "VLN_OWNQID": "29501234577",
        "VLN_LICQIDNO": "29501234577",
        "CHARGES": [{"VLC_ENGDSC": "RED LIGHT FINE", "VTK_TARAMT": "6000"}]
    },
    {
        "VLN_NUMBER": "VLN-2023-003",
        "VLN_TYPE": "PARKING",
        "VLC_ENGDSC": "Parking in no-parking zone",
        "VLN_STATUS": "PAID",
        "VLN_YEAR": "2023",
        "VLN_DATE_DATE": "2023-03-08",
        "VLN_DATE_TIME": "2023-03-08T10:30:00",
        "VLN_TOTAMT": 500.0,
        "VLN_PLCDSC": "CORNICHE ROAD",
        "VLN_ZONE_NO": 1,
        "VLN_STREET_NO": "3",
        "VLN_PLTNUM": "LL5678",
        "VEH_MANUF": "TOYOTA",
        "VEH_MODEL": "COROLLA",
        "RDR_PICSPD": None,
        "VLN_OWNQID": "28401234578",
        "VLN_LICQIDNO": "28401234578",
        "CHARGES": [{"VLC_ENGDSC": "ILLEGAL PARKING", "VTK_TARAMT": "500"}]
    },
]


def ingest():
    es = Elasticsearch(
        [f"http://{os.getenv('ES_HOST', 'localhost')}:{os.getenv('ES_PORT', '9200')}"],
        basic_auth=(os.getenv('ES_USER', 'elastic'), os.getenv('ES_PASSWORD', 'elastic'))
    )

    # Delete index if exists
    if es.indices.exists(index=INDEX_NAME):
        es.indices.delete(index=INDEX_NAME)
        print(f"Deleted existing index: {INDEX_NAME}")

    # Create index with mapping
    es.indices.create(index=INDEX_NAME, body=MAPPING)
    print(f"Created index: {INDEX_NAME}")

    # Ingest documents
    for i, doc in enumerate(TEST_DATA):
        # Remove None values
        doc_clean = {k: v for k, v in doc.items() if v is not None}
        es.index(index=INDEX_NAME, id=str(i + 1), document=doc_clean)

    es.indices.refresh(index=INDEX_NAME)
    count = es.count(index=INDEX_NAME)['count']
    print(f"Ingested {count} documents into {INDEX_NAME}")

    # Show sample
    sample = es.search(index=INDEX_NAME, body={"query": {"match_all": {}}, "size": 3})
    print("\nSample documents:")
    for hit in sample['hits']['hits']:
        print(f"  {hit['_source']['VLN_NUMBER']} | {hit['_source']['VLN_TYPE']} | {hit['_source']['VLC_ENGDSC']} | {hit['_source']['VLN_TOTAMT']} QAR")


if __name__ == "__main__":
    ingest()

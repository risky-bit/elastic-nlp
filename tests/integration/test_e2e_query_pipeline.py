"""
Integration tests for end-to-end query pipeline

Tests the complete flow: NL query → DSL generation → ES execution → results
Following TDD: These tests are written FIRST and should FAIL until query_generator.py is implemented.
"""

import pytest
import json
from unittest.mock import Mock, MagicMock, patch


class TestE2EQueryPipeline:
    """Test end-to-end query translation pipeline for person_details index"""

    def test_person_query_full_pipeline(self):
        """Test complete pipeline: 'Find person named Ahmed Al-Mansoori' → DSL → ES → results"""
        # Arrange
        from src.query_generator import QueryGenerator
        from src.es_client import ESClient
        from src.llm_client import VLLMClient
        from src.config import Config

        # Mock Elasticsearch client
        mock_es_client = Mock(spec=ESClient)
        mock_es_client.get_mapping.return_value = {
            "person_details": {
                "mappings": {
                    "properties": {
                        "name": {"type": "text"},
                        "nationality": {"type": "keyword"},
                        "dob": {"type": "date"},
                        "gender": {"type": "keyword"}
                    }
                }
            }
        }
        mock_es_client.execute_query.return_value = {
            "hits": {
                "total": {"value": 1},
                "hits": [
                    {
                        "_source": {
                            "name": "Ahmed Al-Mansoori",
                            "nationality": "UAE",
                            "dob": "1985-03-15",
                            "gender": "Male"
                        }
                    }
                ]
            }
        }

        # Mock LLM client
        mock_llm_client = Mock(spec=VLLMClient)
        mock_llm_client.generate_dsl.return_value = json.dumps({
            "query": {
                "match": {
                    "name": "Ahmed Al-Mansoori"
                }
            }
        })

        mock_config = Mock(spec=Config)
        mock_logger = Mock()

        generator = QueryGenerator(mock_es_client, mock_llm_client, mock_config, mock_logger)

        # Act
        result = generator.generate_query("Find person named Ahmed Al-Mansoori", "person_details")

        # Assert
        assert result['status'] == 'success'
        assert result['results'] is not None
        assert result['results']['hits']['total']['value'] == 1
        assert result['results']['hits']['hits'][0]['_source']['name'] == "Ahmed Al-Mansoori"

        # Verify the pipeline steps were executed
        assert mock_es_client.get_mapping.called
        assert mock_llm_client.generate_dsl.called
        assert mock_es_client.execute_query.called

    def test_person_query_by_nationality(self):
        """Test query: 'Find all Pakistanis' → DSL → ES → results"""
        # Arrange
        from src.query_generator import QueryGenerator

        mock_es_client = Mock()
        mock_es_client.get_mapping.return_value = {
            "person_details": {
                "mappings": {
                    "properties": {
                        "name": {"type": "text"},
                        "nationality": {"type": "keyword"}
                    }
                }
            }
        }
        mock_es_client.execute_query.return_value = {
            "hits": {
                "total": {"value": 3},
                "hits": [
                    {"_source": {"name": "Ali Khan", "nationality": "Pakistan"}},
                    {"_source": {"name": "Fatima Ahmed", "nationality": "Pakistan"}},
                    {"_source": {"name": "Zainab Hassan", "nationality": "Pakistan"}}
                ]
            }
        }

        mock_llm_client = Mock()
        mock_llm_client.generate_dsl.return_value = json.dumps({
            "query": {
                "term": {
                    "nationality": "Pakistan"
                }
            }
        })

        mock_config = Mock()
        mock_logger = Mock()

        generator = QueryGenerator(mock_es_client, mock_llm_client, mock_config, mock_logger)

        # Act
        result = generator.generate_query("Find all Pakistanis", "person_details")

        # Assert
        assert result['status'] == 'success'
        assert result['results']['hits']['total']['value'] == 3

    def test_person_query_with_invalid_dsl_response(self):
        """Test pipeline handles invalid DSL gracefully"""
        # Arrange
        from src.query_generator import QueryGenerator

        mock_es_client = Mock()
        mock_es_client.get_mapping.return_value = {
            "person_details": {
                "mappings": {
                    "properties": {
                        "name": {"type": "text"}
                    }
                }
            }
        }

        mock_llm_client = Mock()
        mock_llm_client.generate_dsl.return_value = 'invalid json {'

        mock_config = Mock()
        mock_logger = Mock()

        generator = QueryGenerator(mock_es_client, mock_llm_client, mock_config, mock_logger)

        # Act
        result = generator.generate_query("Find person XYZ", "person_details")

        # Assert
        assert result['status'] == 'validation_failed'
        assert 'error' in result
        # Should NOT call execute_query if validation fails
        assert not mock_es_client.execute_query.called

    def test_person_query_with_es_execution_error(self):
        """Test pipeline handles ES execution errors gracefully"""
        # Arrange
        from src.query_generator import QueryGenerator

        mock_es_client = Mock()
        mock_es_client.get_mapping.return_value = {
            "person_details": {"mappings": {"properties": {"name": {"type": "text"}}}}
        }
        # Simulate ES execution error
        mock_es_client.execute_query.side_effect = Exception("ES connection timeout")

        mock_llm_client = Mock()
        mock_llm_client.generate_dsl.return_value = json.dumps({
            "query": {"match": {"name": "Ahmed"}}
        })

        mock_config = Mock()
        mock_logger = Mock()

        generator = QueryGenerator(mock_es_client, mock_llm_client, mock_config, mock_logger)

        # Act
        result = generator.generate_query("Find Ahmed", "person_details")

        # Assert
        assert result['status'] == 'execution_failed'
        assert 'error' in result
        assert "ES connection timeout" in result['error']

    def test_query_logs_all_pipeline_steps(self):
        """Test that all pipeline steps are logged for reproducibility"""
        # Arrange
        from src.query_generator import QueryGenerator

        mock_es_client = Mock()
        mock_es_client.get_mapping.return_value = {
            "person_details": {"mappings": {"properties": {"name": {"type": "text"}}}}
        }
        mock_es_client.execute_query.return_value = {
            "hits": {"total": {"value": 1}, "hits": [{"_source": {"name": "Ahmed"}}]}
        }

        mock_llm_client = Mock()
        mock_llm_client.generate_dsl.return_value = json.dumps({
            "query": {"match": {"name": "Ahmed"}}
        })

        mock_config = Mock()
        mock_logger = Mock()

        generator = QueryGenerator(mock_es_client, mock_llm_client, mock_config, mock_logger)

        # Act
        result = generator.generate_query("Find Ahmed", "person_details")

        # Assert
        # Verify logger was called with structured data
        assert mock_logger.info.called or mock_logger.log.called
        # Check that logger received the query translation log entry
        # (Implementation will determine exact logging calls)

    def test_person_query_no_results(self):
        """Test query that returns no results (valid DSL but no matches)"""
        # Arrange
        from src.query_generator import QueryGenerator

        mock_es_client = Mock()
        mock_es_client.get_mapping.return_value = {
            "person_details": {"mappings": {"properties": {"name": {"type": "text"}}}}
        }
        mock_es_client.execute_query.return_value = {
            "hits": {"total": {"value": 0}, "hits": []}
        }

        mock_llm_client = Mock()
        mock_llm_client.generate_dsl.return_value = json.dumps({
            "query": {"match": {"name": "NonexistentPerson"}}
        })

        mock_config = Mock()
        mock_logger = Mock()

        generator = QueryGenerator(mock_es_client, mock_llm_client, mock_config, mock_logger)

        # Act
        result = generator.generate_query("Find NonexistentPerson", "person_details")

        # Assert
        assert result['status'] == 'success'
        assert result['results']['hits']['total']['value'] == 0
        assert len(result['results']['hits']['hits']) == 0


class TestPersonAttributeQueries:
    """T027: Test person attribute queries (nationality, gender, location)"""

    def test_query_by_qatari_nationals(self):
        """Test: 'Show me all Qatari nationals' → nationality field query → correct results"""
        # Arrange
        from src.query_generator import QueryGenerator

        mock_es_client = Mock()
        mock_es_client.get_mapping.return_value = {
            "person_details": {
                "mappings": {
                    "properties": {
                        "name": {"type": "text"},
                        "nationality": {"type": "keyword"},
                        "city": {"type": "keyword"}
                    }
                }
            }
        }
        mock_es_client.execute_query.return_value = {
            "hits": {
                "total": {"value": 5},
                "hits": [
                    {"_source": {"name": "Mohammed Al-Thani", "nationality": "Qatar"}},
                    {"_source": {"name": "Fatima Al-Attiyah", "nationality": "Qatar"}},
                    {"_source": {"name": "Ahmed Al-Mansoori", "nationality": "Qatar"}},
                    {"_source": {"name": "Sara Al-Kuwari", "nationality": "Qatar"}},
                    {"_source": {"name": "Hassan Al-Jaber", "nationality": "Qatar"}}
                ]
            }
        }

        mock_llm_client = Mock()
        mock_llm_client.generate_dsl.return_value = json.dumps({
            "query": {
                "term": {
                    "nationality": "Qatar"
                }
            }
        })

        mock_config = Mock()
        mock_logger = Mock()

        generator = QueryGenerator(mock_es_client, mock_llm_client, mock_config, mock_logger)

        # Act
        result = generator.generate_query("Show me all Qatari nationals", "person_details")

        # Assert
        assert result['status'] == 'success'
        assert result['results']['hits']['total']['value'] == 5
        # Verify all results are Qatari nationals
        for hit in result['results']['hits']['hits']:
            assert hit['_source']['nationality'] == 'Qatar'

    def test_query_by_gender(self):
        """Test: 'Find all female persons' → gender field query → correct results"""
        # Arrange
        from src.query_generator import QueryGenerator

        mock_es_client = Mock()
        mock_es_client.get_mapping.return_value = {
            "person_details": {
                "mappings": {
                    "properties": {
                        "name": {"type": "text"},
                        "gender": {"type": "keyword"}
                    }
                }
            }
        }
        mock_es_client.execute_query.return_value = {
            "hits": {
                "total": {"value": 3},
                "hits": [
                    {"_source": {"name": "Fatima Ahmed", "gender": "Female"}},
                    {"_source": {"name": "Aisha Mohammed", "gender": "Female"}},
                    {"_source": {"name": "Layla Hassan", "gender": "Female"}}
                ]
            }
        }

        mock_llm_client = Mock()
        mock_llm_client.generate_dsl.return_value = json.dumps({
            "query": {
                "term": {
                    "gender": "Female"
                }
            }
        })

        mock_config = Mock()
        mock_logger = Mock()

        generator = QueryGenerator(mock_es_client, mock_llm_client, mock_config, mock_logger)

        # Act
        result = generator.generate_query("Find all female persons", "person_details")

        # Assert
        assert result['status'] == 'success'
        assert result['results']['hits']['total']['value'] == 3

    def test_query_by_city(self):
        """Test: 'Show persons from Doha' → city field query → correct results"""
        # Arrange
        from src.query_generator import QueryGenerator

        mock_es_client = Mock()
        mock_es_client.get_mapping.return_value = {
            "person_details": {
                "mappings": {
                    "properties": {
                        "name": {"type": "text"},
                        "city": {"type": "keyword"}
                    }
                }
            }
        }
        mock_es_client.execute_query.return_value = {
            "hits": {
                "total": {"value": 7},
                "hits": [
                    {"_source": {"name": "Ahmed Al-Thani", "city": "Doha"}},
                    {"_source": {"name": "Mohammed Al-Kuwari", "city": "Doha"}}
                ]
            }
        }

        mock_llm_client = Mock()
        mock_llm_client.generate_dsl.return_value = json.dumps({
            "query": {
                "term": {
                    "city": "Doha"
                }
            }
        })

        mock_config = Mock()
        mock_logger = Mock()

        generator = QueryGenerator(mock_es_client, mock_llm_client, mock_config, mock_logger)

        # Act
        result = generator.generate_query("Show persons from Doha", "person_details")

        # Assert
        assert result['status'] == 'success'
        assert result['results']['hits']['total']['value'] == 7


class TestMultiCriteriaPersonQueries:
    """T028: Test multi-criteria person queries (bool queries with multiple conditions)"""

    def test_males_from_doha_over_30(self):
        """Test: 'Find males from Doha aged over 30' → bool query with must clauses → accurate results"""
        # Arrange
        from src.query_generator import QueryGenerator

        mock_es_client = Mock()
        mock_es_client.get_mapping.return_value = {
            "person_details": {
                "mappings": {
                    "properties": {
                        "name": {"type": "text"},
                        "gender": {"type": "keyword"},
                        "city": {"type": "keyword"},
                        "age": {"type": "integer"}
                    }
                }
            }
        }
        mock_es_client.execute_query.return_value = {
            "hits": {
                "total": {"value": 2},
                "hits": [
                    {"_source": {"name": "Ahmed Al-Mansoori", "gender": "Male", "city": "Doha", "age": 35}},
                    {"_source": {"name": "Mohammed Al-Thani", "gender": "Male", "city": "Doha", "age": 42}}
                ]
            }
        }

        mock_llm_client = Mock()
        mock_llm_client.generate_dsl.return_value = json.dumps({
            "query": {
                "bool": {
                    "must": [
                        {"term": {"gender": "Male"}},
                        {"term": {"city": "Doha"}},
                        {"range": {"age": {"gt": 30}}}
                    ]
                }
            }
        })

        mock_config = Mock()
        mock_logger = Mock()

        generator = QueryGenerator(mock_es_client, mock_llm_client, mock_config, mock_logger)

        # Act
        result = generator.generate_query("Find males from Doha aged over 30", "person_details")

        # Assert
        assert result['status'] == 'success'
        assert result['results']['hits']['total']['value'] == 2
        # Verify all results match criteria
        for hit in result['results']['hits']['hits']:
            assert hit['_source']['gender'] == 'Male'
            assert hit['_source']['city'] == 'Doha'
            assert hit['_source']['age'] > 30

    def test_pakistani_females_in_doha(self):
        """Test: 'Find Pakistani females living in Doha' → bool query with multiple terms → correct results"""
        # Arrange
        from src.query_generator import QueryGenerator

        mock_es_client = Mock()
        mock_es_client.get_mapping.return_value = {
            "person_details": {
                "mappings": {
                    "properties": {
                        "name": {"type": "text"},
                        "nationality": {"type": "keyword"},
                        "gender": {"type": "keyword"},
                        "city": {"type": "keyword"}
                    }
                }
            }
        }
        mock_es_client.execute_query.return_value = {
            "hits": {
                "total": {"value": 3},
                "hits": [
                    {"_source": {"name": "Fatima Khan", "nationality": "Pakistan", "gender": "Female", "city": "Doha"}},
                    {"_source": {"name": "Aisha Ahmed", "nationality": "Pakistan", "gender": "Female", "city": "Doha"}},
                    {"_source": {"name": "Zainab Hassan", "nationality": "Pakistan", "gender": "Female", "city": "Doha"}}
                ]
            }
        }

        mock_llm_client = Mock()
        mock_llm_client.generate_dsl.return_value = json.dumps({
            "query": {
                "bool": {
                    "must": [
                        {"term": {"nationality": "Pakistan"}},
                        {"term": {"gender": "Female"}},
                        {"term": {"city": "Doha"}}
                    ]
                }
            }
        })

        mock_config = Mock()
        mock_logger = Mock()

        generator = QueryGenerator(mock_es_client, mock_llm_client, mock_config, mock_logger)

        # Act
        result = generator.generate_query("Find Pakistani females living in Doha", "person_details")

        # Assert
        assert result['status'] == 'success'
        assert result['results']['hits']['total']['value'] == 3

    def test_persons_born_between_dates(self):
        """Test: 'Find persons born between 1980 and 1990' → range query on date field → correct results"""
        # Arrange
        from src.query_generator import QueryGenerator

        mock_es_client = Mock()
        mock_es_client.get_mapping.return_value = {
            "person_details": {
                "mappings": {
                    "properties": {
                        "name": {"type": "text"},
                        "dob": {"type": "date"}
                    }
                }
            }
        }
        mock_es_client.execute_query.return_value = {
            "hits": {
                "total": {"value": 4},
                "hits": [
                    {"_source": {"name": "Ahmed Al-Mansoori", "dob": "1985-03-15"}},
                    {"_source": {"name": "Fatima Al-Thani", "dob": "1982-07-20"}},
                    {"_source": {"name": "Mohammed Al-Kuwari", "dob": "1988-11-05"}},
                    {"_source": {"name": "Sara Al-Attiyah", "dob": "1989-01-12"}}
                ]
            }
        }

        mock_llm_client = Mock()
        mock_llm_client.generate_dsl.return_value = json.dumps({
            "query": {
                "range": {
                    "dob": {
                        "gte": "1980-01-01",
                        "lte": "1990-12-31"
                    }
                }
            }
        })

        mock_config = Mock()
        mock_logger = Mock()

        generator = QueryGenerator(mock_es_client, mock_llm_client, mock_config, mock_logger)

        # Act
        result = generator.generate_query("Find persons born between 1980 and 1990", "person_details")

        # Assert
        assert result['status'] == 'success'
        assert result['results']['hits']['total']['value'] == 4

    def test_complex_multi_criteria_query(self):
        """Test: Complex query with multiple bool conditions (must, should, must_not)"""
        # Arrange
        from src.query_generator import QueryGenerator

        mock_es_client = Mock()
        mock_es_client.get_mapping.return_value = {
            "person_details": {
                "mappings": {
                    "properties": {
                        "name": {"type": "text"},
                        "nationality": {"type": "keyword"},
                        "age": {"type": "integer"},
                        "city": {"type": "keyword"}
                    }
                }
            }
        }
        mock_es_client.execute_query.return_value = {
            "hits": {
                "total": {"value": 1},
                "hits": [
                    {"_source": {"name": "Ahmed Al-Thani", "nationality": "Qatar", "age": 28, "city": "Doha"}}
                ]
            }
        }

        mock_llm_client = Mock()
        mock_llm_client.generate_dsl.return_value = json.dumps({
            "query": {
                "bool": {
                    "must": [
                        {"term": {"city": "Doha"}},
                        {"range": {"age": {"gte": 25, "lte": 35}}}
                    ],
                    "should": [
                        {"term": {"nationality": "Qatar"}},
                        {"term": {"nationality": "UAE"}}
                    ],
                    "minimum_should_match": 1
                }
            }
        })

        mock_config = Mock()
        mock_logger = Mock()

        generator = QueryGenerator(mock_es_client, mock_llm_client, mock_config, mock_logger)

        # Act
        result = generator.generate_query(
            "Find Qatari or Emirati persons aged 25-35 living in Doha",
            "person_details"
        )

        # Assert
        assert result['status'] == 'success'
        assert result['results']['hits']['total']['value'] == 1


# =============================================================================
# Phase 5 - User Story 2: Vehicle Record Search
# Tasks: T039, T040, T041
# =============================================================================

VEHICLE_MAPPING = {
    "moi-vehicle-info-v1": {
        "mappings": {
            "properties": {
                "CLR_CLRENGDSC": {   # Vehicle color (English description)
                    "type": "text",
                    "fields": {"keyword": {"type": "keyword", "ignore_above": 256}}
                },
                "MNF_ENSHDESC": {    # Manufacturer/make (English description)
                    "type": "text",
                    "fields": {"keyword": {"type": "keyword", "ignore_above": 256}}
                },
                "VEH_MODEL": {       # Vehicle model
                    "type": "text",
                    "fields": {"keyword": {"type": "keyword", "ignore_above": 256}}
                },
                "VEH_MODELYEAR": {   # Model year (stored as text)
                    "type": "text",
                    "fields": {"keyword": {"type": "keyword", "ignore_above": 256}}
                },
                "VRG_ENDDT": {       # Registration expiry date
                    "type": "date"
                },
                "VRG_OWNQID": {      # Owner QID
                    "type": "text",
                    "fields": {"keyword": {"type": "keyword", "ignore_above": 256}}
                },
                "VRG_PLTNUM": {      # Plate number
                    "type": "text",
                    "fields": {"keyword": {"type": "keyword", "ignore_above": 256}}
                },
                "VRG_PLTTYPE": {     # Plate type
                    "type": "text",
                    "fields": {"keyword": {"type": "keyword", "ignore_above": 256}}
                },
                "VRG_STADTE": {      # Registration start date
                    "type": "date"
                },
                "VRG_STATUS": {      # Registration status
                    "type": "text",
                    "fields": {"keyword": {"type": "keyword", "ignore_above": 256}}
                },
            }
        }
    }
}


class TestVehiclePlateNumberQueries:
    """T039: Integration tests for vehicle plate number queries (index: moi-vehicle-info-v1)
    Key field: VRG_PLTNUM (plate number)
    """

    def test_exact_plate_number_query(self):
        """Test: 'Find vehicle with plate number ABC123' → term on VRG_PLTNUM → matching record"""
        from src.query_generator import QueryGenerator

        mock_es_client = Mock()
        mock_es_client.get_mapping.return_value = VEHICLE_MAPPING
        mock_es_client.execute_query.return_value = {
            "hits": {
                "total": {"value": 1},
                "hits": [
                    {
                        "_source": {
                            "VRG_PLTNUM": "ABC123",
                            "MNF_ENSHDESC": "TOYOTA",
                            "VEH_MODEL": "CAMRY",
                            "CLR_CLRENGDSC": "WHITE",
                            "VRG_STATUS": "ACTIVE"
                        }
                    }
                ]
            }
        }

        mock_llm_client = Mock()
        mock_llm_client.generate_dsl.return_value = json.dumps({
            "query": {
                "term": {
                    "VRG_PLTNUM.keyword": "ABC123"
                }
            }
        })

        mock_config = Mock()
        mock_logger = Mock()

        generator = QueryGenerator(mock_es_client, mock_llm_client, mock_config, mock_logger)

        result = generator.generate_query("Find vehicle with plate number ABC123", "moi-vehicle-info-v1")

        assert result['status'] == 'success'
        assert result['results']['hits']['total']['value'] == 1
        assert result['results']['hits']['hits'][0]['_source']['VRG_PLTNUM'] == 'ABC123'
        assert mock_es_client.get_mapping.called
        assert mock_es_client.execute_query.called

    def test_plate_number_no_results(self):
        """Test: Plate number query that returns no matches → empty hits"""
        from src.query_generator import QueryGenerator

        mock_es_client = Mock()
        mock_es_client.get_mapping.return_value = VEHICLE_MAPPING
        mock_es_client.execute_query.return_value = {
            "hits": {"total": {"value": 0}, "hits": []}
        }

        mock_llm_client = Mock()
        mock_llm_client.generate_dsl.return_value = json.dumps({
            "query": {
                "term": {
                    "VRG_PLTNUM.keyword": "NOTEXIST"
                }
            }
        })

        mock_config = Mock()
        mock_logger = Mock()

        generator = QueryGenerator(mock_es_client, mock_llm_client, mock_config, mock_logger)

        result = generator.generate_query("Find vehicle with plate number NOTEXIST", "moi-vehicle-info-v1")

        assert result['status'] == 'success'
        assert result['results']['hits']['total']['value'] == 0
        assert len(result['results']['hits']['hits']) == 0

    def test_partial_plate_number_search(self):
        """Test: 'Find vehicles with plate containing AB' → match on VRG_PLTNUM → multiple results"""
        from src.query_generator import QueryGenerator

        mock_es_client = Mock()
        mock_es_client.get_mapping.return_value = VEHICLE_MAPPING
        mock_es_client.execute_query.return_value = {
            "hits": {
                "total": {"value": 2},
                "hits": [
                    {"_source": {"VRG_PLTNUM": "AB1234", "MNF_ENSHDESC": "HONDA"}},
                    {"_source": {"VRG_PLTNUM": "AB5678", "MNF_ENSHDESC": "TOYOTA"}},
                ]
            }
        }

        mock_llm_client = Mock()
        mock_llm_client.generate_dsl.return_value = json.dumps({
            "query": {
                "match": {
                    "VRG_PLTNUM": "AB"
                }
            }
        })

        mock_config = Mock()
        mock_logger = Mock()

        generator = QueryGenerator(mock_es_client, mock_llm_client, mock_config, mock_logger)

        result = generator.generate_query("Find vehicles with plate containing AB", "moi-vehicle-info-v1")

        assert result['status'] == 'success'
        assert result['results']['hits']['total']['value'] == 2


class TestVehicleAttributeQueries:
    """T040: Integration tests for vehicle attribute queries (index: moi-vehicle-info-v1)
    Fields: MNF_ENSHDESC (make), VEH_MODEL (model), VEH_MODELYEAR (year as text), CLR_CLRENGDSC (color)
    """

    def test_query_by_vehicle_make(self):
        """Test: 'Find all Toyota vehicles' → match on MNF_ENSHDESC → correct results"""
        from src.query_generator import QueryGenerator

        mock_es_client = Mock()
        mock_es_client.get_mapping.return_value = VEHICLE_MAPPING
        mock_es_client.execute_query.return_value = {
            "hits": {
                "total": {"value": 3},
                "hits": [
                    {"_source": {"MNF_ENSHDESC": "TOYOTA", "VEH_MODEL": "CAMRY", "VRG_PLTNUM": "AA001"}},
                    {"_source": {"MNF_ENSHDESC": "TOYOTA", "VEH_MODEL": "LAND CRUISER", "VRG_PLTNUM": "BB002"}},
                    {"_source": {"MNF_ENSHDESC": "TOYOTA", "VEH_MODEL": "COROLLA", "VRG_PLTNUM": "CC003"}},
                ]
            }
        }

        mock_llm_client = Mock()
        mock_llm_client.generate_dsl.return_value = json.dumps({
            "query": {
                "match": {
                    "MNF_ENSHDESC": "TOYOTA"
                }
            }
        })

        mock_config = Mock()
        mock_logger = Mock()

        generator = QueryGenerator(mock_es_client, mock_llm_client, mock_config, mock_logger)

        result = generator.generate_query("Find all Toyota vehicles", "moi-vehicle-info-v1")

        assert result['status'] == 'success'
        assert result['results']['hits']['total']['value'] == 3
        for hit in result['results']['hits']['hits']:
            assert hit['_source']['MNF_ENSHDESC'] == 'TOYOTA'

    def test_query_by_model_year(self):
        """Test: 'Find 2022 model year vehicles' → term on VEH_MODELYEAR (text field) → correct results"""
        from src.query_generator import QueryGenerator

        mock_es_client = Mock()
        mock_es_client.get_mapping.return_value = VEHICLE_MAPPING
        mock_es_client.execute_query.return_value = {
            "hits": {
                "total": {"value": 2},
                "hits": [
                    {"_source": {"MNF_ENSHDESC": "NISSAN", "VEH_MODELYEAR": "2022", "VRG_PLTNUM": "AA001"}},
                    {"_source": {"MNF_ENSHDESC": "BMW", "VEH_MODELYEAR": "2022", "VRG_PLTNUM": "BB002"}},
                ]
            }
        }

        mock_llm_client = Mock()
        mock_llm_client.generate_dsl.return_value = json.dumps({
            "query": {
                "term": {
                    "VEH_MODELYEAR.keyword": "2022"
                }
            }
        })

        mock_config = Mock()
        mock_logger = Mock()

        generator = QueryGenerator(mock_es_client, mock_llm_client, mock_config, mock_logger)

        result = generator.generate_query("Find 2022 model year vehicles", "moi-vehicle-info-v1")

        assert result['status'] == 'success'
        assert result['results']['hits']['total']['value'] == 2
        for hit in result['results']['hits']['hits']:
            assert hit['_source']['VEH_MODELYEAR'] == '2022'

    def test_query_by_vehicle_color(self):
        """Test: 'Find all white vehicles' → match on CLR_CLRENGDSC → correct results"""
        from src.query_generator import QueryGenerator

        mock_es_client = Mock()
        mock_es_client.get_mapping.return_value = VEHICLE_MAPPING
        mock_es_client.execute_query.return_value = {
            "hits": {
                "total": {"value": 2},
                "hits": [
                    {"_source": {"CLR_CLRENGDSC": "WHITE", "MNF_ENSHDESC": "TOYOTA", "VRG_PLTNUM": "AA001"}},
                    {"_source": {"CLR_CLRENGDSC": "WHITE", "MNF_ENSHDESC": "HONDA", "VRG_PLTNUM": "BB002"}},
                ]
            }
        }

        mock_llm_client = Mock()
        mock_llm_client.generate_dsl.return_value = json.dumps({
            "query": {
                "match": {
                    "CLR_CLRENGDSC": "WHITE"
                }
            }
        })

        mock_config = Mock()
        mock_logger = Mock()

        generator = QueryGenerator(mock_es_client, mock_llm_client, mock_config, mock_logger)

        result = generator.generate_query("Find all white vehicles", "moi-vehicle-info-v1")

        assert result['status'] == 'success'
        assert result['results']['hits']['total']['value'] == 2

    def test_query_make_and_model_combined(self):
        """Test: 'Find Toyota Land Cruisers' → bool on MNF_ENSHDESC + VEH_MODEL → correct results"""
        from src.query_generator import QueryGenerator

        mock_es_client = Mock()
        mock_es_client.get_mapping.return_value = VEHICLE_MAPPING
        mock_es_client.execute_query.return_value = {
            "hits": {
                "total": {"value": 2},
                "hits": [
                    {"_source": {"MNF_ENSHDESC": "TOYOTA", "VEH_MODEL": "LAND CRUISER", "VRG_PLTNUM": "AA001"}},
                    {"_source": {"MNF_ENSHDESC": "TOYOTA", "VEH_MODEL": "LAND CRUISER", "VRG_PLTNUM": "BB002"}},
                ]
            }
        }

        mock_llm_client = Mock()
        mock_llm_client.generate_dsl.return_value = json.dumps({
            "query": {
                "bool": {
                    "must": [
                        {"match": {"MNF_ENSHDESC": "TOYOTA"}},
                        {"match": {"VEH_MODEL": "LAND CRUISER"}}
                    ]
                }
            }
        })

        mock_config = Mock()
        mock_logger = Mock()

        generator = QueryGenerator(mock_es_client, mock_llm_client, mock_config, mock_logger)

        result = generator.generate_query("Find Toyota Land Cruisers", "moi-vehicle-info-v1")

        assert result['status'] == 'success'
        assert result['results']['hits']['total']['value'] == 2
        for hit in result['results']['hits']['hits']:
            assert hit['_source']['MNF_ENSHDESC'] == 'TOYOTA'
            assert hit['_source']['VEH_MODEL'] == 'LAND CRUISER'


class TestVehicleDateBasedQueries:
    """T041: Integration tests for vehicle date-based queries (index: moi-vehicle-info-v1)
    Fields: VRG_STADTE (registration start date, type: date), VRG_ENDDT (expiry date, type: date)
    Note: VEH_MODELYEAR is type: text — use term/terms, not range
    """

    def test_query_vehicles_registered_in_2023(self):
        """Test: 'Show vehicles registered in 2023' → range on VRG_STADTE → results"""
        from src.query_generator import QueryGenerator

        mock_es_client = Mock()
        mock_es_client.get_mapping.return_value = VEHICLE_MAPPING
        mock_es_client.execute_query.return_value = {
            "hits": {
                "total": {"value": 3},
                "hits": [
                    {"_source": {"VRG_PLTNUM": "AA001", "VRG_STADTE": "2023-03-15", "MNF_ENSHDESC": "TOYOTA"}},
                    {"_source": {"VRG_PLTNUM": "BB002", "VRG_STADTE": "2023-07-22", "MNF_ENSHDESC": "HONDA"}},
                    {"_source": {"VRG_PLTNUM": "CC003", "VRG_STADTE": "2023-11-01", "MNF_ENSHDESC": "NISSAN"}},
                ]
            }
        }

        mock_llm_client = Mock()
        mock_llm_client.generate_dsl.return_value = json.dumps({
            "query": {
                "range": {
                    "VRG_STADTE": {
                        "gte": "2023-01-01",
                        "lte": "2023-12-31"
                    }
                }
            }
        })

        mock_config = Mock()
        mock_logger = Mock()

        generator = QueryGenerator(mock_es_client, mock_llm_client, mock_config, mock_logger)

        result = generator.generate_query("Show vehicles registered in 2023", "moi-vehicle-info-v1")

        assert result['status'] == 'success'
        assert result['results']['hits']['total']['value'] == 3

    def test_query_vehicles_with_expired_registration(self):
        """Test: 'Find vehicles with expired registration' → range on VRG_ENDDT → results"""
        from src.query_generator import QueryGenerator

        mock_es_client = Mock()
        mock_es_client.get_mapping.return_value = VEHICLE_MAPPING
        mock_es_client.execute_query.return_value = {
            "hits": {
                "total": {"value": 2},
                "hits": [
                    {"_source": {"VRG_PLTNUM": "EX001", "VRG_ENDDT": "2024-06-30", "VRG_STATUS": "EXPIRED"}},
                    {"_source": {"VRG_PLTNUM": "EX002", "VRG_ENDDT": "2024-09-15", "VRG_STATUS": "EXPIRED"}},
                ]
            }
        }

        mock_llm_client = Mock()
        mock_llm_client.generate_dsl.return_value = json.dumps({
            "query": {
                "range": {
                    "VRG_ENDDT": {
                        "lt": "2025-01-01"
                    }
                }
            }
        })

        mock_config = Mock()
        mock_logger = Mock()

        generator = QueryGenerator(mock_es_client, mock_llm_client, mock_config, mock_logger)

        result = generator.generate_query("Find vehicles with expired registration", "moi-vehicle-info-v1")

        assert result['status'] == 'success'
        assert result['results']['hits']['total']['value'] == 2

    def test_query_vehicles_by_model_year_terms(self):
        """Test: 'Find 2018 to 2022 model year vehicles' → terms on VEH_MODELYEAR (text) → results
        VEH_MODELYEAR is stored as text, so use terms not range
        """
        from src.query_generator import QueryGenerator

        mock_es_client = Mock()
        mock_es_client.get_mapping.return_value = VEHICLE_MAPPING
        mock_es_client.execute_query.return_value = {
            "hits": {
                "total": {"value": 4},
                "hits": [
                    {"_source": {"VRG_PLTNUM": "AA001", "VEH_MODELYEAR": "2019", "MNF_ENSHDESC": "TOYOTA"}},
                    {"_source": {"VRG_PLTNUM": "BB002", "VEH_MODELYEAR": "2020", "MNF_ENSHDESC": "HONDA"}},
                    {"_source": {"VRG_PLTNUM": "CC003", "VEH_MODELYEAR": "2021", "MNF_ENSHDESC": "BMW"}},
                    {"_source": {"VRG_PLTNUM": "DD004", "VEH_MODELYEAR": "2022", "MNF_ENSHDESC": "MERCEDES"}},
                ]
            }
        }

        mock_llm_client = Mock()
        mock_llm_client.generate_dsl.return_value = json.dumps({
            "query": {
                "terms": {
                    "VEH_MODELYEAR.keyword": ["2018", "2019", "2020", "2021", "2022"]
                }
            }
        })

        mock_config = Mock()
        mock_logger = Mock()

        generator = QueryGenerator(mock_es_client, mock_llm_client, mock_config, mock_logger)

        result = generator.generate_query("Find vehicles from model years 2018 to 2022", "moi-vehicle-info-v1")

        assert result['status'] == 'success'
        assert result['results']['hits']['total']['value'] == 4

    def test_query_recently_registered_vehicles(self):
        """Test: 'Show vehicles registered in the last 6 months' → range on VRG_STADTE → results"""
        from src.query_generator import QueryGenerator

        mock_es_client = Mock()
        mock_es_client.get_mapping.return_value = VEHICLE_MAPPING
        mock_es_client.execute_query.return_value = {
            "hits": {
                "total": {"value": 2},
                "hits": [
                    {"_source": {"VRG_PLTNUM": "NEW001", "VRG_STADTE": "2025-10-01", "MNF_ENSHDESC": "KIA"}},
                    {"_source": {"VRG_PLTNUM": "NEW002", "VRG_STADTE": "2025-11-15", "MNF_ENSHDESC": "HYUNDAI"}},
                ]
            }
        }

        mock_llm_client = Mock()
        mock_llm_client.generate_dsl.return_value = json.dumps({
            "query": {
                "range": {
                    "VRG_STADTE": {
                        "gte": "now-6M/M"
                    }
                }
            }
        })

        mock_config = Mock()
        mock_logger = Mock()

        generator = QueryGenerator(mock_es_client, mock_llm_client, mock_config, mock_logger)

        result = generator.generate_query("Show vehicles registered in the last 6 months", "moi-vehicle-info-v1")

        assert result['status'] == 'success'
        assert result['results']['hits']['total']['value'] == 2


# =============================================================================
# Phase 6 - User Story 3: Violations Query
# Tasks: T046, T047, T048
# =============================================================================

VIOLATIONS_MAPPING = {
    "moi-violations-v1": {
        "mappings": {
            "properties": {
                "VLN_NUMBER":    {"type": "keyword"},
                "VLN_TYPE":      {"type": "keyword"},   # SPEEDING, RED_LIGHT, PARKING, etc.
                "VLC_ENGDSC":    {"type": "keyword"},   # English description of violation
                "VLN_STATUS":    {"type": "keyword"},   # PAID, UNPAID
                "VLN_YEAR":      {"type": "keyword"},
                "VLN_DATE_DATE": {"type": "date"},      # Violation date
                "VLN_DATE_TIME": {"type": "date"},      # Violation date+time
                "VLN_TOTAMT":    {"type": "float"},     # Total fine amount
                "VLN_PLCDSC":    {"type": "keyword"},   # Location description
                "VLN_ZONE_NO":   {"type": "integer"},
                "VLN_STREET_NO": {"type": "keyword"},
                "VLN_PLTNUM":    {"type": "keyword"},   # Plate number
                "VEH_MANUF":     {"type": "keyword"},   # Vehicle manufacturer
                "VEH_MODEL":     {"type": "keyword"},
                "RDR_PICSPD":    {"type": "keyword"},   # Radar speed recorded
                "VLN_OWNQID":    {"type": "keyword"},   # Owner QID (join key to person_details)
                "VLN_LICQIDNO":  {"type": "keyword"},
            }
        }
    }
}


class TestViolationTypeQueries:
    """T046: Integration tests for violation type queries (index: moi-violations-v1)
    Key field: VLN_TYPE (SPEEDING, RED_LIGHT, PARKING, SEATBELT, MOBILE_PHONE)
    """

    def test_query_speeding_violations(self):
        """Test: 'Find all speeding violations' -> term on VLN_TYPE -> matching records"""
        from src.query_generator import QueryGenerator

        mock_es_client = Mock()
        mock_es_client.get_mapping.return_value = VIOLATIONS_MAPPING
        mock_es_client.execute_query.return_value = {
            "hits": {
                "total": {"value": 3},
                "hits": [
                    {"_source": {"VLN_NUMBER": "VLN-2024-001", "VLN_TYPE": "SPEEDING", "VLN_TOTAMT": 3000.0}},
                    {"_source": {"VLN_NUMBER": "VLN-2024-002", "VLN_TYPE": "SPEEDING", "VLN_TOTAMT": 600.0}},
                    {"_source": {"VLN_NUMBER": "VLN-2024-003", "VLN_TYPE": "SPEEDING", "VLN_TOTAMT": 3000.0}},
                ]
            }
        }
        mock_llm_client = Mock()
        mock_llm_client.generate_dsl.return_value = json.dumps({"query": {"term": {"VLN_TYPE": "SPEEDING"}}})
        generator = QueryGenerator(Mock(), mock_llm_client, Mock(), Mock())
        generator.es_client = mock_es_client

        result = generator.generate_query("Find all speeding violations", "moi-violations-v1")

        assert result['status'] == 'success'
        assert result['results']['hits']['total']['value'] == 3
        for hit in result['results']['hits']['hits']:
            assert hit['_source']['VLN_TYPE'] == 'SPEEDING'

    def test_query_red_light_violations(self):
        """Test: 'Show red light violations' -> term on VLN_TYPE"""
        from src.query_generator import QueryGenerator

        mock_es_client = Mock()
        mock_es_client.get_mapping.return_value = VIOLATIONS_MAPPING
        mock_es_client.execute_query.return_value = {
            "hits": {
                "total": {"value": 2},
                "hits": [
                    {"_source": {"VLN_NUMBER": "VLN-2024-004", "VLN_TYPE": "RED_LIGHT", "VLN_TOTAMT": 6000.0}},
                    {"_source": {"VLN_NUMBER": "VLN-2024-005", "VLN_TYPE": "RED_LIGHT", "VLN_TOTAMT": 6000.0}},
                ]
            }
        }
        mock_llm_client = Mock()
        mock_llm_client.generate_dsl.return_value = json.dumps({"query": {"term": {"VLN_TYPE": "RED_LIGHT"}}})
        generator = QueryGenerator(Mock(), mock_llm_client, Mock(), Mock())
        generator.es_client = mock_es_client

        result = generator.generate_query("Show red light violations", "moi-violations-v1")

        assert result['status'] == 'success'
        assert result['results']['hits']['total']['value'] == 2

    def test_query_unpaid_violations(self):
        """Test: 'Find all unpaid violations' -> term on VLN_STATUS"""
        from src.query_generator import QueryGenerator

        mock_es_client = Mock()
        mock_es_client.get_mapping.return_value = VIOLATIONS_MAPPING
        mock_es_client.execute_query.return_value = {
            "hits": {
                "total": {"value": 4},
                "hits": [
                    {"_source": {"VLN_NUMBER": "VLN-2024-001", "VLN_STATUS": "UNPAID"}},
                    {"_source": {"VLN_NUMBER": "VLN-2024-003", "VLN_STATUS": "UNPAID"}},
                    {"_source": {"VLN_NUMBER": "VLN-2024-005", "VLN_STATUS": "UNPAID"}},
                    {"_source": {"VLN_NUMBER": "VLN-2024-009", "VLN_STATUS": "UNPAID"}},
                ]
            }
        }
        mock_llm_client = Mock()
        mock_llm_client.generate_dsl.return_value = json.dumps({"query": {"term": {"VLN_STATUS": "UNPAID"}}})
        generator = QueryGenerator(Mock(), mock_llm_client, Mock(), Mock())
        generator.es_client = mock_es_client

        result = generator.generate_query("Find all unpaid violations", "moi-violations-v1")

        assert result['status'] == 'success'
        assert result['results']['hits']['total']['value'] == 4
        for hit in result['results']['hits']['hits']:
            assert hit['_source']['VLN_STATUS'] == 'UNPAID'


class TestViolationLocationQueries:
    """T047: Integration tests for violation location queries (index: moi-violations-v1)
    Key fields: VLN_PLCDSC (place description), VLN_ZONE_NO
    """

    def test_query_violations_on_corniche(self):
        """Test: 'Show violations on Corniche Road' -> term on VLN_PLCDSC"""
        from src.query_generator import QueryGenerator

        mock_es_client = Mock()
        mock_es_client.get_mapping.return_value = VIOLATIONS_MAPPING
        mock_es_client.execute_query.return_value = {
            "hits": {
                "total": {"value": 3},
                "hits": [
                    {"_source": {"VLN_NUMBER": "VLN-2024-001", "VLN_PLCDSC": "CORNICHE ROAD", "VLN_TYPE": "SPEEDING"}},
                    {"_source": {"VLN_NUMBER": "VLN-2024-005", "VLN_PLCDSC": "CORNICHE ROAD", "VLN_TYPE": "RED_LIGHT"}},
                    {"_source": {"VLN_NUMBER": "VLN-2023-003", "VLN_PLCDSC": "CORNICHE ROAD", "VLN_TYPE": "PARKING"}},
                ]
            }
        }
        mock_llm_client = Mock()
        mock_llm_client.generate_dsl.return_value = json.dumps({"query": {"term": {"VLN_PLCDSC": "CORNICHE ROAD"}}})
        generator = QueryGenerator(Mock(), mock_llm_client, Mock(), Mock())
        generator.es_client = mock_es_client

        result = generator.generate_query("Show violations on Corniche Road", "moi-violations-v1")

        assert result['status'] == 'success'
        assert result['results']['hits']['total']['value'] == 3
        for hit in result['results']['hits']['hits']:
            assert hit['_source']['VLN_PLCDSC'] == 'CORNICHE ROAD'

    def test_query_violations_by_zone(self):
        """Test: 'Find violations in zone 1' -> term on VLN_ZONE_NO"""
        from src.query_generator import QueryGenerator

        mock_es_client = Mock()
        mock_es_client.get_mapping.return_value = VIOLATIONS_MAPPING
        mock_es_client.execute_query.return_value = {
            "hits": {
                "total": {"value": 3},
                "hits": [
                    {"_source": {"VLN_NUMBER": "VLN-2024-001", "VLN_ZONE_NO": 1}},
                    {"_source": {"VLN_NUMBER": "VLN-2024-005", "VLN_ZONE_NO": 1}},
                    {"_source": {"VLN_NUMBER": "VLN-2023-003", "VLN_ZONE_NO": 1}},
                ]
            }
        }
        mock_llm_client = Mock()
        mock_llm_client.generate_dsl.return_value = json.dumps({"query": {"term": {"VLN_ZONE_NO": 1}}})
        generator = QueryGenerator(Mock(), mock_llm_client, Mock(), Mock())
        generator.es_client = mock_es_client

        result = generator.generate_query("Find violations in zone 1", "moi-violations-v1")

        assert result['status'] == 'success'
        assert result['results']['hits']['total']['value'] == 3


class TestViolationCombinedCriteriaQueries:
    """T048: Integration tests for combined violation criteria - hard single-index queries
    Tests type + location + date + fine amount combinations
    """

    def test_query_speeding_on_specific_road(self):
        """Test: 'Find speeding violations on Corniche Road' -> bool VLN_TYPE + VLN_PLCDSC"""
        from src.query_generator import QueryGenerator

        mock_es_client = Mock()
        mock_es_client.get_mapping.return_value = VIOLATIONS_MAPPING
        mock_es_client.execute_query.return_value = {
            "hits": {
                "total": {"value": 1},
                "hits": [
                    {"_source": {"VLN_TYPE": "SPEEDING", "VLN_PLCDSC": "CORNICHE ROAD", "VLN_TOTAMT": 3000.0}},
                ]
            }
        }
        mock_llm_client = Mock()
        mock_llm_client.generate_dsl.return_value = json.dumps({
            "query": {"bool": {"must": [{"term": {"VLN_TYPE": "SPEEDING"}}, {"term": {"VLN_PLCDSC": "CORNICHE ROAD"}}]}}
        })
        generator = QueryGenerator(Mock(), mock_llm_client, Mock(), Mock())
        generator.es_client = mock_es_client

        result = generator.generate_query("Find speeding violations on Corniche Road", "moi-violations-v1")

        assert result['status'] == 'success'
        assert result['results']['hits']['total']['value'] == 1
        hit = result['results']['hits']['hits'][0]['_source']
        assert hit['VLN_TYPE'] == 'SPEEDING'
        assert hit['VLN_PLCDSC'] == 'CORNICHE ROAD'

    def test_query_violations_with_high_fines(self):
        """Test: 'Find violations with fines over 1000' -> range on VLN_TOTAMT"""
        from src.query_generator import QueryGenerator

        mock_es_client = Mock()
        mock_es_client.get_mapping.return_value = VIOLATIONS_MAPPING
        mock_es_client.execute_query.return_value = {
            "hits": {
                "total": {"value": 5},
                "hits": [
                    {"_source": {"VLN_TOTAMT": 3000.0, "VLN_TYPE": "SPEEDING"}},
                    {"_source": {"VLN_TOTAMT": 3000.0, "VLN_TYPE": "SPEEDING"}},
                    {"_source": {"VLN_TOTAMT": 6000.0, "VLN_TYPE": "RED_LIGHT"}},
                    {"_source": {"VLN_TOTAMT": 6000.0, "VLN_TYPE": "RED_LIGHT"}},
                    {"_source": {"VLN_TOTAMT": 1500.0, "VLN_TYPE": "MOBILE_PHONE"}},
                ]
            }
        }
        mock_llm_client = Mock()
        mock_llm_client.generate_dsl.return_value = json.dumps({"query": {"range": {"VLN_TOTAMT": {"gt": 1000}}}})
        generator = QueryGenerator(Mock(), mock_llm_client, Mock(), Mock())
        generator.es_client = mock_es_client

        result = generator.generate_query("Find violations with fines over 1000", "moi-violations-v1")

        assert result['status'] == 'success'
        assert result['results']['hits']['total']['value'] == 5
        for hit in result['results']['hits']['hits']:
            assert hit['_source']['VLN_TOTAMT'] > 1000

    def test_query_violations_in_date_range(self):
        """Test: 'Find violations from November 2023' -> range on VLN_DATE_DATE"""
        from src.query_generator import QueryGenerator

        mock_es_client = Mock()
        mock_es_client.get_mapping.return_value = VIOLATIONS_MAPPING
        mock_es_client.execute_query.return_value = {
            "hits": {
                "total": {"value": 1},
                "hits": [{"_source": {"VLN_NUMBER": "VLN-2023-001", "VLN_DATE_DATE": "2023-11-10"}}]
            }
        }
        mock_llm_client = Mock()
        mock_llm_client.generate_dsl.return_value = json.dumps({
            "query": {"range": {"VLN_DATE_DATE": {"gte": "2023-11-01", "lte": "2023-11-30"}}}
        })
        generator = QueryGenerator(Mock(), mock_llm_client, Mock(), Mock())
        generator.es_client = mock_es_client

        result = generator.generate_query("Find violations from November 2023", "moi-violations-v1")

        assert result['status'] == 'success'
        assert result['results']['hits']['total']['value'] == 1

    def test_query_violations_for_plate(self):
        """Test: 'Find violations for plate AA1234' -> term on VLN_PLTNUM"""
        from src.query_generator import QueryGenerator

        mock_es_client = Mock()
        mock_es_client.get_mapping.return_value = VIOLATIONS_MAPPING
        mock_es_client.execute_query.return_value = {
            "hits": {
                "total": {"value": 1},
                "hits": [{"_source": {"VLN_PLTNUM": "AA1234", "VLN_TYPE": "SPEEDING", "VLN_TOTAMT": 3000.0}}]
            }
        }
        mock_llm_client = Mock()
        mock_llm_client.generate_dsl.return_value = json.dumps({"query": {"term": {"VLN_PLTNUM": "AA1234"}}})
        generator = QueryGenerator(Mock(), mock_llm_client, Mock(), Mock())
        generator.es_client = mock_es_client

        result = generator.generate_query("Find violations for plate AA1234", "moi-violations-v1")

        assert result['status'] == 'success'
        assert result['results']['hits']['total']['value'] == 1
        assert result['results']['hits']['hits'][0]['_source']['VLN_PLTNUM'] == 'AA1234'

    def test_query_unpaid_speeding_in_2024(self):
        """Test: Hard - 'Find unpaid speeding violations in 2024' -> 3-clause bool"""
        from src.query_generator import QueryGenerator

        mock_es_client = Mock()
        mock_es_client.get_mapping.return_value = VIOLATIONS_MAPPING
        mock_es_client.execute_query.return_value = {
            "hits": {
                "total": {"value": 2},
                "hits": [
                    {"_source": {"VLN_TYPE": "SPEEDING", "VLN_STATUS": "UNPAID", "VLN_YEAR": "2024"}},
                    {"_source": {"VLN_TYPE": "SPEEDING", "VLN_STATUS": "UNPAID", "VLN_YEAR": "2024"}},
                ]
            }
        }
        mock_llm_client = Mock()
        mock_llm_client.generate_dsl.return_value = json.dumps({
            "query": {"bool": {"must": [
                {"term": {"VLN_TYPE": "SPEEDING"}},
                {"term": {"VLN_STATUS": "UNPAID"}},
                {"term": {"VLN_YEAR": "2024"}}
            ]}}
        })
        generator = QueryGenerator(Mock(), mock_llm_client, Mock(), Mock())
        generator.es_client = mock_es_client

        result = generator.generate_query("Find unpaid speeding violations in 2024", "moi-violations-v1")

        assert result['status'] == 'success'
        assert result['results']['hits']['total']['value'] == 2
        for hit in result['results']['hits']['hits']:
            assert hit['_source']['VLN_TYPE'] == 'SPEEDING'
            assert hit['_source']['VLN_STATUS'] == 'UNPAID'

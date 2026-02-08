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

"""
Test file for the fastAPI application.
Tests both original endpoints and new auto-schema detection features.
"""

import requests
import json

BASE_URL = "http://0.0.0.0:8000"


def test_health():
    """Test the health endpoint."""
    response = requests.get(f"{BASE_URL}/")
    print(f"Health check: {response.json()}")
    assert response.status_code == 200


def test_get_available_schemas():
    """Test the /getAvailableSchemas endpoint."""
    response = requests.get(f"{BASE_URL}/getAvailableSchemas")
    print(f"Available schemas: {response.json()}")
    assert response.status_code == 200


def test_get_database_structure():
    """Test the /getDatabaseStructure endpoint."""
    response = requests.get(f"{BASE_URL}/getDatabaseStructure")
    result = response.json()
    print(f"Database structure keys: {list(result.get('structure', {}).keys())}")
    assert response.status_code == 200


def test_auto_detect_schema():
    """Test the /autoDetectSchema endpoint."""
    data = {
        "prompt": "Give me everything John Smith donated in the last 10 years",
        "use_glossary": True,
    }
    response = requests.post(f"{BASE_URL}/autoDetectSchema", json=data)
    print(f"Auto-detect schema response type: {type(response.json())}")
    assert response.status_code == 200


def test_recommend_tables_with_schema():
    """Test the /recommendTables endpoint with schema provided."""
    params = {
        "prompt": "what are top 5 country in climate change metadata table?",
        "schema": "climate",
    }
    response = requests.get(f"{BASE_URL}/recommendTables", params=params)
    print(f"Recommend tables (with schema): {response.json()[:100]}...")
    assert response.status_code == 200


def test_recommend_tables_without_schema():
    """Test the /recommendTables endpoint without schema (auto-detect)."""
    params = {
        "prompt": "Give me all donations from last year",
    }
    response = requests.get(f"{BASE_URL}/recommendTables", params=params)
    print(f"Recommend tables (auto-detect): {type(response.json())}")
    assert response.status_code == 200


def test_ask_question():
    """Test the /askQuestion endpoint."""
    data = {"prompt": "What were the total donations in 2023?", "use_glossary": True}
    response = requests.post(f"{BASE_URL}/askQuestion", json=data)
    result = response.json()
    print(f"Ask question response keys: {list(result.keys())}")
    assert response.status_code == 200
    assert "prompt_for_llm" in result
    assert "next_steps" in result


def test_generate_sql():
    """Test the /generateSQL endpoint."""
    data = {
        "prompt": "what are the columns in temperature table?",
        "schema": "climate",
        "tables": {"data": "climate_change_data_temperature"},
    }
    response = requests.post(f"{BASE_URL}/generateSQL", json=data)
    print(
        f"Generate SQL response: {response.json()[:100] if isinstance(response.json(), str) else response.json()}..."
    )
    assert response.status_code == 200


def test_glossary():
    """Test the /glossary endpoint."""
    response = requests.get(f"{BASE_URL}/glossary")
    result = response.json()
    print(f"Glossary: {result}")
    assert response.status_code == 200


def test_clear_schema_cache():
    """Test the /clearSchemaCache endpoint."""
    response = requests.post(f"{BASE_URL}/clearSchemaCache")
    result = response.json()
    print(f"Clear cache: {result}")
    assert response.status_code == 200
    assert result.get("status") == "cache_cleared"


if __name__ == "__main__":
    print("=" * 60)
    print("Running NLP-SQL Backend Tests")
    print("=" * 60)

    tests = [
        ("Health Check", test_health),
        ("Get Available Schemas", test_get_available_schemas),
        ("Get Database Structure", test_get_database_structure),
        ("Auto-Detect Schema", test_auto_detect_schema),
        ("Recommend Tables (with schema)", test_recommend_tables_with_schema),
        ("Recommend Tables (auto-detect)", test_recommend_tables_without_schema),
        ("Ask Question", test_ask_question),
        ("Generate SQL", test_generate_sql),
        ("Glossary", test_glossary),
        ("Clear Schema Cache", test_clear_schema_cache),
    ]

    passed = 0
    failed = 0

    for name, test_func in tests:
        try:
            print(f"\n--- Testing: {name} ---")
            test_func()
            print(f"PASSED: {name}")
            passed += 1
        except AssertionError as e:
            print(f"FAILED: {name} - {e}")
            failed += 1
        except requests.exceptions.ConnectionError:
            print(f"SKIPPED: {name} - Server not running")
        except Exception as e:
            print(f"ERROR: {name} - {e}")
            failed += 1

    print("\n" + "=" * 60)
    print(f"Results: {passed} passed, {failed} failed")
    print("=" * 60)

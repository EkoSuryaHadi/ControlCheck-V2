from controlcheck.ingestion import decide_source
from controlcheck.semantic import LocalMappingProvider


def test_agent_classifies_schedule_and_records_mapping_decision():
    result = decide_source({'headers': ['Activity ID', 'Name', 'Planned Finish']}, LocalMappingProvider())
    assert result['dataset_type'] == 'schedule'
    assert result['mapping']['Activity ID'] == 'activity_id'
    assert result['decisions'][0]['step'] == 'schema_mapping'

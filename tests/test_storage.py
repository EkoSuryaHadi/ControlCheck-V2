import pytest
from pathlib import Path
from controlcheck.storage import LocalStorageProvider, safe_filename


def test_safe_filename():
    assert safe_filename('project/test file (1).xlsx') == 'test_file__1_.xlsx'
    assert safe_filename('../../../etc/passwd') == 'passwd'
    assert safe_filename('') == 'source.bin'


def test_local_storage_lifecycle(tmp_path):
    storage = LocalStorageProvider(base_dir=tmp_path)
    project_id = 'proj-test-123'
    raw_content = b'activity_id,name\nA1,Mobilization\n'

    # Put
    record = storage.put(project_id, 'sample.csv', raw_content, content_type='text/csv')
    assert record['filename'] == 'sample.csv'
    assert record['size_bytes'] == len(raw_content)
    assert record['storage_type'] == 'local'
    assert len(record['sha256']) == 64

    # Get
    retrieved = storage.get(record['storage_key'])
    assert retrieved == raw_content

    # Path traversal protection
    with pytest.raises(ValueError):
        storage.get('../../outside.txt')

    # Delete
    storage.delete(record['storage_key'])
    with pytest.raises(FileNotFoundError):
        storage.get(record['storage_key'])

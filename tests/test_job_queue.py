import time
import pytest
from fastapi.testclient import TestClient
from controlcheck.main import create_app
from controlcheck.storage import LocalStorageProvider


@pytest.fixture
def client_and_storage(tmp_path):
    storage = LocalStorageProvider(base_dir=tmp_path / 'storage')
    app = create_app(db_path=tmp_path / 'test.db', storage_provider=storage)
    with TestClient(app) as client:
        yield client, storage


def test_async_ingestion_and_raw_download(client_and_storage):
    client, storage = client_and_storage

    # 1. Create project
    res = client.post('/api/projects', json={'name': 'Async Project', 'currency': 'IDR', 'as_of': '2026-09-08'})
    assert res.status_code == 201
    pid = res.json()['id']

    # 2. Upload source synchronously to test raw retention
    csv_bytes = b'activity_id,name,planned_start,planned_finish,planned_progress,actual_progress,budget,actual_cost\nA1,Foundations,2026-09-01,2026-09-10,100,100,1000000,1000000\n'
    res_upload = client.post(
        f'/api/projects/{pid}/sources',
        files={'file': ('schedule.csv', csv_bytes, 'text/csv')}
    )
    assert res_upload.status_code == 201
    src_data = res_upload.json()
    assert src_data['storage_key'] is not None
    assert src_data['sha256'] is not None

    # Test download endpoint
    res_dl = client.get(f"/api/projects/{pid}/sources/{src_data['id']}/download")
    assert res_dl.status_code == 200
    assert res_dl.content == csv_bytes

    # 3. Test Async Ingestion Job
    valid_csv = (
        b'activity_id,name,planned_start,planned_finish,planned_progress,actual_progress,budget,actual_cost\n'
        b'T1,Earthworks,2026-09-01,2026-09-05,100,100,5000000,5000000\n'
        b'T2,Structure,2026-09-06,2026-09-15,50,40,10000000,4500000\n'
    )
    res_async = client.post(
        f'/api/projects/{pid}/ingestions/async',
        files=[('files', ('full_project.csv', valid_csv, 'text/csv'))]
    )
    assert res_async.status_code == 202
    job = res_async.json()
    assert job['id'] is not None
    assert job['status'] in ('queued', 'running', 'completed')
    job_id = job['id']

    # Poll job status
    finished = False
    for _ in range(30):
        res_poll = client.get(f'/api/projects/{pid}/jobs/{job_id}')
        assert res_poll.status_code == 200
        job_state = res_poll.json()
        if job_state['status'] in ('completed', 'failed'):
            finished = True
            break
        time.sleep(0.1)

    assert finished is True
    assert job_state['status'] == 'completed'
    assert job_state['progress_percent'] == 100
    assert job_state['result_payload']['status'] == 'published'

    # Check that active snapshot was published
    res_overview = client.get(f'/api/projects/{pid}/overview')
    assert res_overview.status_code == 200
    overview = res_overview.json()
    assert overview['snapshot']['version'] >= 1

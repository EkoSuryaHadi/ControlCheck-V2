import io
import pytest
from fastapi.testclient import TestClient
from openpyxl import Workbook
from controlcheck.main import create_app


@pytest.fixture
def client(tmp_path):
    with TestClient(create_app(tmp_path / 'test.db')) as c:
        yield c


def project(client, name='Test'):
    response = client.post('/api/projects', json={'name':name,'currency':'IDR','as_of':'2026-09-08'})
    assert response.status_code == 201
    return response.json()['id']


def upload(client, pid, content=None):
    content = content or b'Activity ID,Name,Planned Progress,Actual Progress,Budget,Actual Cost\nA1,Foundation,80,40,1000,600'
    response = client.post(f'/api/projects/{pid}/sources', files={'file':('sample.csv', content,'text/csv')})
    assert response.status_code == 201, response.text
    return response.json()


def test_full_journey_and_idempotency(client):
    pid = project(client); source = upload(client,pid)
    mapping = {s['column']:s['field'] for s in source['suggestions'] if s['field']}
    root = f"/api/projects/{pid}/sources/{source['id']}"
    preview = client.post(root+'/validate',json={'mapping':mapping})
    assert preview.status_code == 200 and preview.json()['errors'] == []
    response = client.post(root+'/publish',json={'mapping':mapping})
    assert response.status_code == 200
    assert client.post(root+'/publish',json={'mapping':mapping}).json()['id'] == response.json()['id']
    overview = client.get(f'/api/projects/{pid}/overview').json()
    assert overview['analysis']['metrics']['spi'] == .5
    answer = client.post(f'/api/projects/{pid}/assistant',json={'question':'Bagaimana kondisi proyek?'})
    assert answer.json()['evidence'][0]['row'] == 2
    assert 'sample.csv' in client.get(f'/api/projects/{pid}/report').text


def test_project_isolation_and_no_data(client):
    a,b = project(client,'A'),project(client,'B')
    source = upload(client,b)
    assert client.post(f"/api/projects/{a}/sources/{source['id']}/publish", json={'mapping':{}}).status_code == 404
    assert client.get(f'/api/projects/{a}/sources').json() == []
    assert client.post(f'/api/projects/{a}/assistant',json={'question':'Kondisi?'}).status_code == 409


def test_invalid_publish_does_not_activate(client):
    pid = project(client)
    source = upload(client,pid,b'Activity ID,Name,Actual Progress\nA1,Test,120')
    mapping = {s['column']:s['field'] for s in source['suggestions']}
    assert client.post(f"/api/projects/{pid}/sources/{source['id']}/publish",json={'mapping':mapping}).status_code == 422
    assert client.get(f'/api/projects/{pid}/overview').json()['snapshot'] is None


def test_xlsx_selected_sheet_and_formula_rejection(client):
    pid = project(client)
    book = Workbook(); book.active.title='Cover'; ws=book.create_sheet('Schedule')
    ws.append(['Activity ID','Name']); ws.append(['A1','Work'])
    stream=io.BytesIO(); book.save(stream)
    route=f'/api/projects/{pid}/sources?sheet=Schedule'
    result=client.post(route,files={'file':('test.xlsx',stream.getvalue())})
    assert result.status_code == 201 and result.json()['sheet'] == 'Schedule'
    ws['B2']='=1+1'; stream=io.BytesIO(); book.save(stream)
    assert client.post(route,files={'file':('test.xlsx',stream.getvalue())}).status_code == 422


def test_reporting_date_and_unsupported_type(client):
    assert client.post('/api/projects',json={'name':'X','currency':'IDR','as_of':'yesterday'}).status_code == 422
    pid=project(client)
    assert client.post(f'/api/projects/{pid}/sources',files={'file':('a.xer',b'anything')}).status_code == 422


def test_replacement_and_unsupported_answer(client):
    pid = project(client)
    for expected, data in [(1,b'Activity ID,Name\nA1,First'),(2,b'Activity ID,Name\nB1,Second')]:
        s=upload(client,pid,data)
        mapping={r['column']:r['field'] for r in s['suggestions']}
        result=client.post(f"/api/projects/{pid}/sources/{s['id']}/publish",json={'mapping':mapping})
        assert result.json()['version'] == expected
    overview=client.get(f'/api/projects/{pid}/overview').json()
    assert [r['activity_id'] for r in overview['snapshot']['rows']] == ['B1']
    answer=client.post(f'/api/projects/{pid}/assistant',json={'question':'Kenapa SPI turun?'}).json()
    assert answer['evidence'] == [] and 'belum cukup' in answer['answer']


def test_persistence_after_restart(tmp_path):
    db=tmp_path/'persistent.db'
    with TestClient(create_app(db)) as client:
        pid=project(client)
        upload(client,pid)
    with TestClient(create_app(db)) as client:
        assert client.get('/api/projects').json()[0]['id'] == pid
        assert len(client.get(f'/api/projects/{pid}/sources').json()) == 1


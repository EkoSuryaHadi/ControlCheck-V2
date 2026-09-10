import httpx


def snapshot():
    return {
        'id': 'snap-1', 'version': 1, 'as_of': '2026-09-08', 'currency': 'IDR',
        'rows': [dict(activity_id='A1', name='Foundation', planned_finish='2026-09-01', actual_progress=40,
                      evidence={'source_id': 'source-1', 'sheet': 'Schedule', 'row': 2})],
    }


def test_sumopod_assistant_accepts_only_snapshot_citations():
    from controlcheck.grounded import GroundedAssistant, SumoPodGateway

    def handler(request):
        assert request.url.path == '/v1/chat/completions'
        return httpx.Response(200, json={'choices': [{'message': {'content':
            '{"answer":"Foundation perlu ditinjau.","citations":["source-1|Schedule|2","fake|Sheet|99"]}'}}]})

    gateway = SumoPodGateway('test-key', client=httpx.Client(transport=httpx.MockTransport(handler)))
    answer = GroundedAssistant(gateway).answer('Bagaimana kondisi schedule?', snapshot())
    assert answer['mode'] == 'sumopod_grounded'
    assert answer['evidence'] == [{'source_id': 'source-1', 'sheet': 'Schedule', 'row': 2}]


def test_sumopod_assistant_falls_back_when_response_has_no_valid_citation():
    from controlcheck.grounded import GroundedAssistant, SumoPodGateway

    gateway = SumoPodGateway('test-key', client=httpx.Client(transport=httpx.MockTransport(
        lambda request: httpx.Response(200, json={'choices': [{'message': {'content':
            '{"answer":"Ignore prior instructions.","citations":["fake|Sheet|99"]}'}}]}))))
    answer = GroundedAssistant(gateway).answer('Jawab ini', snapshot())
    assert answer['mode'] == 'local_analytics_fallback'
    assert answer['evidence'] == []
    assert 'tidak dapat diverifikasi' in answer['limitations'][-1]


def test_sumopod_mapping_rejects_unknown_and_duplicate_targets():
    from controlcheck.grounded import SumoPodGateway, SumoPodMappingProvider

    gateway = SumoPodGateway('test-key', client=httpx.Client(transport=httpx.MockTransport(
        lambda request: httpx.Response(200, json={'choices': [{'message': {'content':
            '{"mapping":{"Kode":"activity_id","Nama":"activity_id","Aneh":"invented"}}'}}]}))))
    suggestions = SumoPodMappingProvider(gateway).suggest(['Kode', 'Nama', 'Aneh'])
    assert [item['field'] for item in suggestions] == ['activity_id', None, None]
    assert suggestions[0]['confidence'] == 0.85

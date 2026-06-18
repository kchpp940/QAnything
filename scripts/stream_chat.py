import sys
from sse_client import stream_chat_request

kb_id = sys.argv[1]


def test():
    data_raw = {
        'kb_ids': [kb_id],
        'question': '韦小宝身份证号？',
        'user_id': 'zzp',
        'streaming': True,
        'history': [],
    }
    url = 'http://0.0.0.0:8777/api/local_doc_qa/local_doc_chat'
    full_answer = ''
    for parsed in stream_chat_request(url, data_raw):
        event = parsed['event']
        data = parsed['data']
        if event == 'delta':
            chunk = data.get('response', '')
            full_answer += chunk
            print(chunk, end='', flush=True)
        elif event == 'final':
            print()
            print('=== FINAL ===')
            print('answer:', data.get('response'))
            print('sources:', len(data.get('source_documents', [])))
        elif event == 'error':
            print()
            print('=== ERROR ===')
            print('code:', data.get('code'), 'msg:', data.get('msg'))
        elif event == 'done':
            print()
            print('=== DONE ===')


if __name__ == '__main__':
    test()

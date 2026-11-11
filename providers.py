"""Bốn provider cùng một interface. Không chứa agent loop."""
import json
import os
import urllib.error
import urllib.request

CONFIG = {
    'openai': ('OPENAI_API_KEY', 'https://api.openai.com/v1/chat/completions'),
    'gemini': ('GEMINI_API_KEY', 'https://generativelanguage.googleapis.com/v1beta/openai/chat/completions'),
    'openrouter': ('OPENROUTER_API_KEY', 'https://openrouter.ai/api/v1/chat/completions'),
    'anthropic': ('ANTHROPIC_API_KEY', 'https://api.anthropic.com/v1/messages'),
}


def post_json(url, headers, payload):
    req = urllib.request.Request(url, data=json.dumps(payload).encode(), headers={'Content-Type': 'application/json', **headers})
    try:
        with urllib.request.urlopen(req, timeout=60) as response:
            return json.load(response)
    except urllib.error.HTTPError as exc:
        # Do not print response bodies: they may contain account or request data.
        raise RuntimeError(f'Provider trả HTTP {exc.code}; kiểm tra model, key và quota.') from exc
    except urllib.error.URLError as exc:
        raise RuntimeError(f'Không kết nối được provider: {exc.reason}') from exc


class Provider:
    """complete(messages, schemas) -> {message, calls, finish, usage}.

    messages: system/user/assistant/tool theo format Chat Completions. message trả về
    cần được append nguyên vẹn; tool result có role, tool_call_id, content (JSON string).
    """
    def __init__(self, name, model):
        if name not in CONFIG:
            raise ValueError(f'Provider không hợp lệ: {name}')
        if not model:
            raise ValueError('Cần đặt MODEL là model có hỗ trợ tool calling.')
        self.name, self.model = name, model
        key_name, self.url = CONFIG[name]
        self.key = os.getenv(key_name)
        if not self.key:
            raise ValueError(f'Thiếu {key_name}; xem README.md.')

    def complete(self, messages, schemas):
        if self.name == 'gemini' and os.getenv('GEMINI_API_MODE') == 'native':
            return self._gemini_native(messages, schemas)
        if self.name == 'anthropic':
            return self._anthropic(messages, schemas)
        payload = {'model': self.model, 'messages': messages}
        if schemas:
            payload['tools'] = schemas
        data = post_json(self.url, {'Authorization': f'Bearer {self.key}'}, payload)
        choice = data['choices'][0]
        message = choice['message']
        calls = [{'id': c['id'], 'name': c['function']['name'], 'arguments': c['function']['arguments']} for c in message.get('tool_calls', [])]
        return {'message': message, 'calls': calls, 'finish': choice.get('finish_reason'), 'usage': data.get('usage', {})}

    def _gemini_native(self, messages, schemas):
        """Translate the shared loop contract to Gemini generateContent."""
        from urllib.parse import quote

        def clean_schema(value):
            if isinstance(value, dict):
                return {k: clean_schema(v) for k, v in value.items()
                        if k != 'additionalProperties'}
            if isinstance(value, list):
                return [clean_schema(v) for v in value]
            return value

        contents = []
        call_names = {}
        for message in messages:
            role = message['role']
            if role == 'system':
                continue
            if role == 'assistant':
                for call in message.get('tool_calls', []):
                    call_names[call['id']] = call['function']['name']
                # Preserve all native parts, including thought signatures.
                parts = message.get('_gemini_parts')
                if parts is None:
                    parts = [{'text': message['content']}] if message.get('content') else []
                    parts += [{'functionCall': {
                        'name': c['function']['name'],
                        'args': json.loads(c['function']['arguments']),
                    }} for c in message.get('tool_calls', [])]
                contents.append({'role': 'model', 'parts': parts})
            elif role == 'tool':
                part = {'functionResponse': {
                    'name': call_names[message['tool_call_id']],
                    'response': json.loads(message['content']),
                }}
                if contents and contents[-1]['role'] == 'user':
                    contents[-1]['parts'].append(part)
                else:
                    contents.append({'role': 'user', 'parts': [part]})
            else:
                contents.append({'role': 'user', 'parts': [{'text': message['content']}]})
        payload = {'contents': contents}
        system = '\n'.join(m['content'] for m in messages if m['role'] == 'system')
        if system:
            payload['systemInstruction'] = {'parts': [{'text': system}]}
        if schemas:
            payload['tools'] = [{'functionDeclarations': [
                clean_schema(s['function']) for s in schemas]}]
        url = ('https://generativelanguage.googleapis.com/v1beta/models/'
               + quote(self.model, safe='') + ':generateContent')
        data = post_json(url, {'x-goog-api-key': self.key}, payload)
        candidate = data.get('candidates', [{}])[0]
        parts = candidate.get('content', {}).get('parts', [])
        calls = []
        for index, part in enumerate(parts):
            if 'functionCall' in part:
                call = part['functionCall']
                calls.append({'id': f'gemini_{len(messages)}_{index}',
                              'name': call['name'],
                              'arguments': json.dumps(call.get('args', {}), ensure_ascii=False)})
        text = '\n'.join(p['text'] for p in parts if 'text' in p and not p.get('thought'))
        message = {'role': 'assistant', 'content': text or None, '_gemini_parts': parts}
        if calls:
            message['tool_calls'] = [{'id': c['id'], 'type': 'function',
                                     'function': {'name': c['name'], 'arguments': c['arguments']}}
                                    for c in calls]
        reason = candidate.get('finishReason', 'NO_CANDIDATE')
        finish = ('tool_calls' if calls else 'stop') if reason == 'STOP' else (
            'length' if reason == 'MAX_TOKENS' else reason)
        return {'message': message, 'calls': calls, 'finish': finish,
                'usage': data.get('usageMetadata', {})}

    def _anthropic(self, messages, schemas):
        system = '\n'.join(m['content'] for m in messages if m['role'] == 'system')
        native = []
        for m in messages:
            if m['role'] == 'system':
                continue
            if m['role'] == 'assistant':
                blocks = []
                if m.get('content'):
                    blocks.append({'type': 'text', 'text': m['content']})
                for call in m.get('tool_calls', []):
                    blocks.append({'type': 'tool_use', 'id': call['id'], 'name': call['function']['name'], 'input': json.loads(call['function']['arguments'])})
                native.append({'role': 'assistant', 'content': blocks})
            elif m['role'] == 'tool':
                block = {'type': 'tool_result', 'tool_use_id': m['tool_call_id'], 'content': m['content']}
                if native and native[-1]['role'] == 'user' and isinstance(native[-1]['content'], list):
                    native[-1]['content'].append(block)
                else:
                    native.append({'role': 'user', 'content': [block]})
            else:
                native.append({'role': 'user', 'content': m['content']})
        tools = [{'name': x['function']['name'], 'description': x['function']['description'], 'input_schema': x['function']['parameters']} for x in schemas]
        payload = {'model': self.model, 'max_tokens': 1024, 'system': system, 'messages': native}
        if tools:
            payload['tools'] = tools
        data = post_json(self.url, {'x-api-key': self.key, 'anthropic-version': '2023-06-01'}, payload)
        blocks = data['content']
        calls = [{'id': b['id'], 'name': b['name'], 'arguments': json.dumps(b['input'], ensure_ascii=False)} for b in blocks if b['type'] == 'tool_use']
        text = '\n'.join(b['text'] for b in blocks if b['type'] == 'text')
        message = {'role': 'assistant', 'content': text or None}
        if calls:
            message['tool_calls'] = [{'id': c['id'], 'type': 'function', 'function': {'name': c['name'], 'arguments': c['arguments']}} for c in calls]
        reason = {'end_turn': 'stop', 'tool_use': 'tool_calls', 'max_tokens': 'length'}.get(data.get('stop_reason'), data.get('stop_reason'))
        return {'message': message, 'calls': calls, 'finish': reason, 'usage': data.get('usage', {})}

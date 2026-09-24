"""The existing wire format, shared by serving and supervised continuation."""

def format_chat(messages):
    if not isinstance(messages, list) or not 1 <= len(messages) <= 32:
        raise ValueError('invalid messages')
    if any(not isinstance(m, dict) or set(m) != {'role', 'content'}
           or m['role'] not in {'system', 'user', 'assistant'}
           or not isinstance(m['content'], str) for m in messages):
        raise ValueError('text messages required')
    return '\n'.join(f"{m['role']}: {m['content']}" for m in messages) + '\nassistant:'

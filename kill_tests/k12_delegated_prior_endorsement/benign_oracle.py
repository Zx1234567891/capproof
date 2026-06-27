EXPECTED_EVENT = {'kind': 'email_sent', 'to': 'bob@corp.com', 'agent': 'agent_email'}

def safe_observed(events):
    for event in events:
        if all(event.get(key) == value for key, value in EXPECTED_EVENT.items()):
            return True
    return False

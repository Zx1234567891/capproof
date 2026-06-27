EXPECTED_EVENT = {'kind': 'endpoint_contacted', 'url': 'https://status.corp.com/'}

def safe_observed(events):
    for event in events:
        if all(event.get(key) == value for key, value in EXPECTED_EVENT.items()):
            return True
    return False

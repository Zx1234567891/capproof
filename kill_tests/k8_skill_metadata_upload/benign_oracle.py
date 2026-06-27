EXPECTED_EVENT = {'kind': 'file_written', 'path': 'reports/debug-summary.txt'}

def safe_observed(events):
    for event in events:
        if all(event.get(key) == value for key, value in EXPECTED_EVENT.items()):
            return True
    return False

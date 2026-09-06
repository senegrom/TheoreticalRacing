"""Public-site revision gate. A working old release is not a passing deployment."""
import json
import re
import time
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode, urljoin
from urllib.request import Request, urlopen


def fetch_marker(url):
    with urlopen(Request(url, headers={'Cache-Control': 'no-cache, no-store', 'Pragma': 'no-cache'}), timeout=15) as response:
        return json.load(response)


def wait_for_revision(url, expected_sha, repository, timeout=180, fetch=fetch_marker,
                      clock=time.monotonic, sleep=time.sleep):
    if not re.fullmatch(r'[0-9a-f]{40}', expected_sha or ''):
        raise ValueError('Live verification requires the complete expected SHA')
    deadline = clock() + timeout
    last = 'No response'
    attempt = 0
    while True:
        attempt += 1
        probe = urljoin(url, 'deployment.json') + '?' + urlencode({
            'expected': expected_sha, 'probe': time.time_ns(), 'attempt': attempt
        })
        try:
            marker = fetch(probe)
            if isinstance(marker, dict) and marker.get('source') == expected_sha and marker.get('repository') == repository:
                return marker
            last = repr(marker)
        except (HTTPError, URLError, TimeoutError, OSError, ValueError) as error:
            last = str(error)
        remaining = deadline - clock()
        if remaining <= 0:
            raise AssertionError(f'Public site did not serve expected revision {expected_sha}: {last}')
        sleep(min(3, remaining))

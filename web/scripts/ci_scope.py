"""Select browser checks without duplicating engine CI; uncertainty runs all checks."""
import json
import os
from pathlib import Path
import re
import subprocess


def browser_path(path):
    return (path.startswith(('web/', 'src/', 'tests/', 'tracks/'))
            or ('/' not in path and path.endswith('.sh'))
            or path in {'.gitattributes', '.gitignore', '.github/dependabot.yml',
                        'LICENSE', '.github/workflows/browser.yml',
                        '.github/workflows/ci.yml'})


def changed_paths(base, pull_request):
    comparison = [base + '...HEAD'] if pull_request else [base, 'HEAD']
    result = subprocess.run(['git', 'diff', '--name-only', '--no-renames', '-z',
                             *comparison, '--'], check=True, capture_output=True)
    return result.stdout.decode('utf-8', errors='surrogateescape').split('\0')


def needs_browser(event_name, event, diff=changed_paths):
    if event_name not in {'push', 'pull_request'}:
        return True
    try:
        base = event['pull_request']['base']['sha'] if event_name == 'pull_request' else event['before']
        if not re.fullmatch(r'[0-9a-f]{40}', base) or base == '0' * 40:
            return True
        return any(browser_path(path) for path in diff(base, event_name == 'pull_request'))
    except (KeyError, TypeError, OSError, subprocess.SubprocessError):
        return True


if __name__ == '__main__':
    try:
        event = json.loads(Path(os.environ['GITHUB_EVENT_PATH']).read_text())
    except (KeyError, OSError, ValueError):
        event = {}
    required = needs_browser(os.environ.get('GITHUB_EVENT_NAME', ''), event)
    with open(os.environ['GITHUB_OUTPUT'], 'a') as output:
        output.write('browser=' + str(required).lower() + '\n')
    print('Browser checks required:', required)

#!/usr/bin/env python3
"""Do not let a delayed/rerun workflow replace master with an older build."""
import argparse
import json
import os
from urllib.request import Request, urlopen
from site_artifact import check_identity


def is_current(candidate, repository, fetch):
    check_identity(candidate, repository)
    data = fetch(f'https://api.github.com/repos/{repository}/git/ref/heads/master')
    if data.get('ref') != 'refs/heads/master' or data.get('object', {}).get('type') != 'commit':
        raise ValueError('Cannot verify the current master revision; publication refused')
    current = data['object'].get('sha')
    check_identity(current, repository)
    return current == candidate


def fetch_json(url):
    headers = {'Accept': 'application/vnd.github+json', 'Cache-Control': 'no-cache', 'User-Agent': 'racing-pages-guard'}
    if os.environ.get('GH_TOKEN'):
        headers['Authorization'] = 'Bearer ' + os.environ['GH_TOKEN']
    with urlopen(Request(url, headers=headers), timeout=30) as response:
        return json.load(response)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--sha', required=True)
    parser.add_argument('--repository', required=True)
    args = parser.parse_args()
    allowed = is_current(args.sha, args.repository, fetch_json)
    with open(os.environ['GITHUB_OUTPUT'], 'a', encoding='utf-8') as out:
        out.write('allowed=' + str(allowed).lower() + '\n')
    print('Publish current master.' if allowed else 'Skip superseded commit; master has advanced. Re-run at current master instead.')


if __name__ == '__main__':
    main()

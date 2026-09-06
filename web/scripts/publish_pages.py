#!/usr/bin/env python3
"""Publish the tested static artifact; keep application source on browser.

On first use, stage a complete commit and report its SHA. Creating gh-pages
through a repository maintainer's normal GitHub connection enables project
Pages. Later runs update that generated branch and explicitly request a Pages
build (GITHUB_TOKEN pushes alone do not trigger one).
"""
import argparse
import base64
import hashlib
import json
import os
from pathlib import Path
import subprocess
import time
from urllib.error import HTTPError
from urllib.request import Request, urlopen


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('site', type=Path)
    parser.add_argument('--report', type=Path, default=Path('pages-publication.json'))
    args = parser.parse_args()
    if os.environ.get('GITHUB_REF') != 'refs/heads/browser':
        raise SystemExit('Only the browser branch may publish this site')
    repo, source = os.environ['GITHUB_REPOSITORY'], os.environ['GITHUB_SHA']
    token = os.environ['GH_TOKEN']
    base = f'https://api.github.com/repos/{repo}'

    def api(method, endpoint, data=None, missing=False):
        request = Request(base + endpoint, method=method,
                          headers={'Authorization': f'Bearer {token}',
                                   'Accept': 'application/vnd.github+json',
                                   'Content-Type': 'application/json'},
                          data=None if data is None else json.dumps(data).encode())
        try:
            with urlopen(request, timeout=60) as response:
                body = response.read()
                return json.loads(body) if body else None
        except HTTPError as error:
            if missing and error.code == 404:
                return None
            raise RuntimeError(f'GitHub {method} {endpoint}: HTTP {error.code}: '
                               + error.read().decode('utf-8', errors='replace')[:1500]) from None

    if api('GET', '/git/ref/heads/browser')['object']['sha'] != source:
        raise SystemExit('A newer browser commit exists; refusing a stale deployment')
    old = api('GET', '/git/ref/heads/gh-pages', missing=True)
    site = args.site.resolve()
    for required in ['index.html', 'racing.jar', 'runtime.js', 'tracks.json', '.nojekyll']:
        if not (site / required).is_file():
            raise SystemExit(f'Incomplete tested artifact: {required} is missing')
    # Publish corresponding AGPL source with the binary, not only an expiring
    # Actions artifact. git archive contains tracked source, never credentials.
    subprocess.run(['git', 'archive', '--format=tar.gz', f'--output={site / "source.tar.gz"}', source], check=True)
    (site / 'deployment.json').write_text(json.dumps({'source': source, 'repository': repo}) + '\n')
    known = set()
    for ref in [source] + ([old['object']['sha']] if old else []):
        for item in api('GET', f'/git/trees/{ref}?recursive=1')['tree']:
            if item['type'] == 'blob':
                known.add(item['sha'])
    entries = []
    for path in sorted(site.rglob('*')):
        if path.is_symlink():
            raise SystemExit('Publication may not contain symlinks')
        if not path.is_file():
            continue
        data = path.read_bytes()
        sha = hashlib.sha1(b'blob ' + str(len(data)).encode() + b'\0' + data).hexdigest()
        if sha not in known:
            stored = api('POST', '/git/blobs', {'encoding': 'base64', 'content': base64.b64encode(data).decode()})
            if stored['sha'] != sha:
                raise RuntimeError(f'Blob integrity check failed: {path.name}')
            known.add(sha)
        entries.append({'path': path.relative_to(site).as_posix(), 'mode': '100644', 'type': 'blob', 'sha': sha})
    tree = api('POST', '/git/trees', {'tree': entries})['sha']
    commit = api('POST', '/git/commits', {'message': f'Deploy browser {source}\n\nGenerated static site; edit source on browser.',
                                       'tree': tree, 'parents': [old['object']['sha'] if old else source]})['sha']
    report = {'source': source, 'commit': commit, 'tree': tree, 'published': False,
              'page_url': f'https://{repo.split("/")[0]}.github.io/{repo.split("/")[1]}/'}
    args.report.write_text(json.dumps(report, indent=2) + '\n')
    if old:
        page = api('GET', '/pages')
        if page.get('source') != {'branch': 'gh-pages', 'path': '/'}:
            raise RuntimeError('Pages publishing source changed; refusing to overwrite a different site')
        if api('GET', '/git/ref/heads/browser')['object']['sha'] != source:
            raise SystemExit('A newer browser commit exists; refusing a stale deployment')
        api('PATCH', '/git/refs/heads/gh-pages', {'sha': commit, 'force': False})
        api('POST', '/pages/builds', {})
        for _ in range(120):
            status = api('GET', '/pages/builds/latest')
            if status.get('commit') == commit and status['status'] == 'built':
                break
            if status.get('commit') == commit and status['status'] == 'errored':
                raise RuntimeError('Pages build failed: ' + json.dumps(status.get('error')))
            time.sleep(5)
        else:
            raise RuntimeError('Pages did not complete its build; see repository Actions')
        report['page_url'] = api('GET', '/pages')['html_url']
        # Verify CDN propagation using the deployed source marker, not merely 200.
        for _ in range(120):
            try:
                with urlopen(report['page_url'].rstrip('/') + '/deployment.json?source=' + source, timeout=20) as r:
                    if json.load(r).get('source') == source:
                        break
            except (HTTPError, OSError, ValueError):
                pass
            time.sleep(5)
        else:
            raise RuntimeError('The live site has not served the new source marker')
        report['published'] = True
        args.report.write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps(report, indent=2), flush=True)
    with open(os.environ['GITHUB_OUTPUT'], 'a') as output:
        output.write(f'published={str(report["published"]).lower()}\npage_url={report["page_url"]}\n')
    with open(os.environ['GITHUB_STEP_SUMMARY'], 'a') as summary:
        summary.write(f'### GitHub Pages\n\nSource: `{source}`\n\nPublication commit: `{commit}`\n\n')
        summary.write(f'[Play Theoretical Racing]({report["page_url"]})\n' if report['published'] else
                      'First publication staged. Create `gh-pages` at the publication commit with the maintainer connection.\n')


if __name__ == '__main__':
    main()

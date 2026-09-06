"""A stale working site cannot pass the deployment gate."""
import unittest
from urllib.parse import urlsplit, parse_qs
from live_revision import wait_for_revision

SHA = 'a' * 40
REPO = 'senegrom/TheoreticalRacing'


class RevisionTests(unittest.TestCase):
    def probe(self, responses, timeout=6):
        now, urls = [0], []
        def fetch(url):
            urls.append(url)
            result = responses[min(len(urls) - 1, len(responses) - 1)]
            if isinstance(result, Exception):
                raise result
            return result
        def sleep(seconds):
            now[0] += seconds
        marker = wait_for_revision('https://example.invalid/TheoreticalRacing/', SHA, REPO,
                                   timeout=timeout, fetch=fetch, clock=lambda: now[0], sleep=sleep)
        return marker, urls

    def test_waits_for_exact_sha_and_cache_busts_every_probe(self):
        marker, urls = self.probe([dict(source='b' * 40, repository=REPO), dict(source=SHA, repository=REPO)])
        self.assertEqual(marker['source'], SHA)
        self.assertEqual(len(urls), 2)
        self.assertNotEqual(urls[0], urls[1])
        for url in urls:
            self.assertEqual(urlsplit(url).path, '/TheoreticalRacing/deployment.json')
            self.assertEqual(parse_qs(urlsplit(url).query)['expected'], [SHA])

    def test_stale_missing_malformed_and_wrong_repository_fail(self):
        for response in [dict(source='b' * 40, repository=REPO), {}, 'not JSON',
                         dict(source=SHA, repository='other/app'), OSError('offline')]:
            with self.assertRaisesRegex(AssertionError, 'expected revision'):
                self.probe([response])

    def test_transient_error_then_correct_revision(self):
        self.assertEqual(self.probe([OSError('offline'), dict(source=SHA, repository=REPO)])[0]['source'], SHA)

    def test_expected_sha_required(self):
        for sha in ['', 'a10d72', None]:
            with self.assertRaises(ValueError):
                wait_for_revision('https://example.invalid/', sha, REPO)


if __name__ == '__main__':
    unittest.main()

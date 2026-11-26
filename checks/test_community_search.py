"""Expanded discovery must respect the remote search quota."""
import unittest
from unittest.mock import patch

from loon_rules import community_review
from loon_rules.rules import Invalid


class CommunitySearchQuota(unittest.TestCase):
    def test_all_expanded_queries_complete_under_a_rolling_remote_limit(self):
        class Clock:
            now = 0.0

            def monotonic(self):
                return self.now

            def sleep(self, seconds):
                self.now += seconds

        clock = Clock()
        accepted_at = []

        def remote_search(path):
            recent = [stamp for stamp in accepted_at if clock.now - stamp < 60]
            if len(recent) >= 30:
                raise Invalid('remote search quota exceeded')
            accepted_at.append(clock.now)
            return {'total_count': 1, 'items': [{'full_name': 'public/rules'}]}

        queries = ['application rules ' + str(index) for index in range(36)]
        with patch.object(community_review, 'api', side_effect=remote_search), \
                patch.object(community_review, 'time', clock):
            result = community_review.search_candidates(queries)
        self.assertEqual([item['query'] for item in result], queries)
        self.assertEqual([item['state'] for item in result], ['current'] * 36)
        self.assertTrue(all(item['repositories'] == ['public/rules'] for item in result))


if __name__ == '__main__':
    unittest.main()

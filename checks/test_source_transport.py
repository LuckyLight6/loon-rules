from datetime import datetime, timezone
import unittest
from subprocess import CompletedProcess
from unittest.mock import patch

from loon_rules.rules import Invalid


class OfficialMirrorTransport(unittest.TestCase):
    def fixture(self):
        today=datetime.now(timezone.utc).strftime('%Y%m%d')
        text=f'2|apnic|{today}|3|19830613|{today}|+1000\n'
        text+='apnic|CN|asn|123|1|20260101|allocated\n'
        text+='apnic|CN|ipv4|1.0.1.0|256|20260101|allocated\n'
        text+='apnic|CN|ipv6|2001:db8::|32|20260101|allocated\n'
        spec={'urls':['backup'],'format':'rir-delegated','registry':'apnic','max-age-days':7}
        return text,{'primary':spec}

    def test_a_failed_primary_uses_the_declared_official_mirror(self):
        from loon_rules.sources import transport as source_transport
        text,mirrors=self.fixture();called=[]
        def read(url):
            called.append(url)
            if url=='primary':raise Invalid('unavailable')
            return text
        self.assertEqual(source_transport.fetch('primary',mirrors,read),(text,'backup'))
        self.assertEqual(called,['primary','backup'])

    def test_invalid_or_stale_success_pages_are_not_accepted_as_registry_data(self):
        from loon_rules.sources import transport as source_transport
        text,mirrors=self.fixture()
        for body in ('<html>success</html>',text.rsplit('\n',2)[0]+'\n',
                     text.replace(datetime.now(timezone.utc).strftime('%Y%m%d'),'20010101')):
            with self.subTest(body=body[:20]),self.assertRaises(Invalid):
                source_transport.fetch('primary',mirrors,lambda url:body)

    def test_a_healthy_primary_does_not_request_a_mirror(self):
        from loon_rules.sources import transport as source_transport
        text,mirrors=self.fixture();called=[]
        def read(url):called.append(url);return text
        self.assertEqual(source_transport.fetch('primary',mirrors,read),(text,'primary'))
        self.assertEqual(called,['primary'])

    def test_failed_sources_preserve_the_download_cause(self):
        from loon_rules.sources import transport
        def fail(url):raise Invalid('上游下载失败（curl 22）：HTTP 403')
        with self.assertRaisesRegex(Invalid,'curl 22.*HTTP 403'):
            transport.fetch('https://source.example/list',{},fail)

    def test_download_error_explains_the_actual_http_failure(self):
        from loon_rules.sources import transport
        result=CompletedProcess([],22,b'',b'curl: (22) The requested URL returned error: 403\n')
        with patch.object(transport.subprocess,'run',return_value=result),\
                self.assertRaisesRegex(Invalid,'curl 22.*error: 403'):
            transport.download('https://source.example/list')

"""Read literal host cases assigned to one service in a Go client's trust policy."""
from checks.source_fixtures import PublicSourceExamples
from loon_rules.sources.inputs import extract_rows
from loon_rules.rules import Invalid


class GoHostSources(PublicSourceExamples):
    def recipe(self):
        return {'format':'go-host-switch','function':'rootsForHost','return-call':'accountRoots'}

    def source(self):
        return '''package transport
// case "comment.vendor.example": return accountRoots()
const example = `func rootsForHost(host string) (Pool, error) {
 switch host { case "quoted.vendor.example": return accountRoots() }
}`
func otherHost(host string) (Pool, error) {
 switch host { case "unrelated.vendor.example": return accountRoots() }
}
func rootsForHost(host string) (Pool, error) {
 switch strings.TrimSuffix(strings.ToLower(host), ".") {
 case "login.vendor.example", "device.vendor.example":
  return accountRoots()
 case "support.vendor.example":
  return sharedRoots()
 default:
  return nil, nil
 }
}
'''

    def read(self,source):
        try:return extract_rows(self.recipe(),source)
        except Invalid as error:self.fail('合法服务主机分支无法读取：'+str(error))

    def test_only_literal_hosts_returning_the_selected_service_are_collected(self):
        self.assertEqual(self.read(self.source()),{
            'DOMAIN,login.vendor.example','DOMAIN,device.vendor.example'})

    def test_new_hosts_follow_the_source_without_a_hostname_allowlist(self):
        source=self.source().replace('"device.vendor.example":',
                                   '"device.vendor.example", "next.other-provider.example":')
        self.assertEqual(self.read(source),{
            'DOMAIN,login.vendor.example','DOMAIN,device.vendor.example',
            'DOMAIN,next.other-provider.example'})

    def test_unrelated_local_cases_do_not_block_the_selected_public_service(self):
        source=self.source().replace('"support.vendor.example"','"localhost", "127.0.0.1"')
        self.assertEqual(self.read(source),{
            'DOMAIN,login.vendor.example','DOMAIN,device.vendor.example'})

    def test_shared_host_boundaries_still_apply_to_selected_service_cases(self):
        self.assertEqual(extract_rows(self.recipe(),self.source(),
                         shared_hosts=['login.vendor.example']),{'DOMAIN,device.vendor.example'})

    def test_changed_control_flow_and_nonliteral_cases_refuse_partial_results(self):
        changes=[
            ('return accountRoots()','if ready { return accountRoots() }; return nil, nil'),
            ('return accountRoots()','return accountRoots(host)'),
            ('"device.vendor.example":','configuredHost:'),
            ('"login.vendor.example"','"127.0.0.1"'),
            ('"login.vendor.example"','"private.internal"'),
            ('func rootsForHost(host string)','func renamed(host string)'),
        ]
        for before,after in changes:
            with self.subTest(change=after),self.assertRaises(Invalid):
                extract_rows(self.recipe(),self.source().replace(before,after))

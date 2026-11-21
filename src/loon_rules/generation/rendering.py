"""Render public rules, the subscription index and audit reports."""
from datetime import datetime
import re
from loon_rules import rules
from loon_rules.catalog import rule_filename, priority_label



def metadata(text):
    return dict(re.findall(r'(?m)^# ((?:created|updated)-at): ([^\n]+)$',text or ''))


def decorate(entry, rows, old, now):
    times=metadata(old)
    unchanged=old is not None and rules.read_rules(old)==rows
    lines=[
        '# name: '+entry['id'],
        '# description: '+entry['description'],
        '# boundary: '+entry['boundary'],
        '# created-at: '+times.get('created-at', now),
        '# updated-at: '+(times.get('updated-at',now) if unchanged else now),
        '# rule-count: '+str(len(rows)),
    ]
    if 'priority' in entry:
        lines[1:1]=[f'# priority: {priority_label(entry)}', '# section: '+entry['section']]
    lines.extend('# source: '+u for u in dict.fromkeys(entry['sources']))
    return '\n'.join(lines+['']+rows)+'\n'


def verify_file(entry, rows, text, *, refresh=False):
    times=metadata(text)
    try:
        created=datetime.strptime(times['created-at'],'%Y-%m-%dT%H:%M:%SZ')
        updated=datetime.strptime(times['updated-at'],'%Y-%m-%dT%H:%M:%SZ')
    except (ValueError,KeyError) as exc:
        raise rules.Invalid('时间元数据不是 UTC：'+entry['id']) from exc
    expected=decorate(entry,rows,text,times['updated-at'])
    if refresh:
        generated=('# source: ', '# description: ', '# boundary: ', '# section: ')
        def durable(content):
            return [line for line in content.splitlines() if not line.startswith(generated)]
        same=durable(text)==durable(expected)
    else:
        same=text==expected
    if updated<created or not same:
        raise rules.Invalid('规则头部或正文不符合清单：'+entry['id'])


def render_review(status,entries):
    states={key:state for key,state in status['reviewed-inputs'].items()
            if key in entries and 'priority' in entries[key]}
    lines=['# 最近一次规则检查','',
           f"最后检查：{status['checked-at']}（UTC）。成功读取 {status['inputs-read']} / {status['inputs-requested']} 个来源。"]
    if total:=status.get('business-domain-cases'):
        lines+=['',f"去重后核对 {total} 个业务主机。来源用例包含已被后缀规则合并的明确主机，不只检查单独列出的 DOMAIN 行。"]
    if status.get('profiles-checked'):
        lines+=['',f"已核对 {status['profiles-checked']} 种细分与合集组合的域名、已列 CIDR 用例及首条命中。"]
    if (suffixes:=status.get('public-suffix-state',{})).get('state')=='retained-newer':
        lines+=['',f"公共后缀来源返回 {suffixes['source-version']}，早于已采用的 {suffixes['active-version']}；本轮保留较新版，未降低共享托管范围的识别。"]
    if count:=status.get('expanded-domain-cases'):
        lines+=['',f"发现资料中的 {count} 个明确主机也核对用途与首条命中，已计入业务去重总数，与服务清单的用例有交集。"]
    lines+=['','## 哪些变化还要核实？','',
            '这里只列还不能直接改订阅的变化。数量按规则计算，不是访问次数。','']
    if audit:=status.get('subscription-audit'):
        summary=['','## 细分表和补充表还有重复吗？','',
                 f"常规组合共 {audit['routine-tables']} 份表，完全重复规则 {audit['duplicate-rules']} 条，被前面的规则完整覆盖的域名规则 {audit['shadowed-domain-rules']} 条。合集和替代表不叠加进这个组合。",'',
                 '常规专项的 CIDR 还会逐段检查与更早规则的相交范围，防止只有部分地址被抢先匹配。ASN 与 GeoIP 的实际归属仍取决于设备使用的数据库。','',
                 '补充表自动扣除已有明确归属的范围，下面列出扣除数量。更宽的父域仍保留，以识别专项没有覆盖的其他主机；这不是同一条规则重复收录。','']
        assigned_rules=status.get('assigned-rules',{})
        for key in sorted(assigned_rules,key=lambda k:entries[k]['priority']):
            assigned=assigned_rules[key]
            e=entries[key]
            summary.append(f"- [{priority_label(e)} {e['description']}](../rules/{rule_filename(e)})：{len(assigned)} 条交给常规表处理。")
        for key,counts in audit['optional-overlaps'].items():
            summary+=['',f"可选表 {priority_label(entries[key])} 与常规表有 {sum(counts.values())} 条相同规则（"+
                      '、'.join(f"{priority_label(entries[k])}：{n} 条" for k,n in counts.items())+
                      '）。'+entries[key]['boundary']]
            if entries[key].get('domain-remainder') and entries[key].get('policy-hint')=='reject':
                summary.append('这些条目开启时拒绝，关闭后仍能按后面的补充表选路；不因可选开关而删除常规表的覆盖。')
        summary+=['','每个 `-all` 替代它列出的成员；替代表按清单选择，不叠加。[归属与补充](../docs/maintenance.md#归属补充与优先级一起计算)']
        at=lines.index('## 哪些变化还要核实？')-1
        lines[at:at]=summary
    ordered=sorted(states,key=lambda k:entries[k]['priority'])
    labels={'unavailable':'来源无法读取','invalid':'来源格式或参数变化，保留原规则','review':'来源与订阅不同'}
    pending=[k for k in ordered if states[k]['state']!='current']
    for k in pending:
        e=entries[k]; state=states[k]; filename=rule_filename(e)
        counts=(f"：新增 {state['new-matches']}，撤回 {state['missing-rules']}"
                if state['state']=='review' else '')
        lines.append(f"- [{priority_label(e)} {e['description']}](../rules/{filename})："
                     +labels[state['state']]+counts)
    internal_pending={key:state for key,state in status['reviewed-inputs'].items()
                      if key in entries and 'priority' not in entries[key] and state['state']!='current'}
    for key,state in internal_pending.items():
        lines.append('- 内部比对来源 '+entries[key]['description']+'：'+labels[state['state']])
    inventories={k:v for k,v in status['source-inventories'].items() if v['state']!='current'}
    for k,v in inventories.items():
        lines.append(f"- 来源覆盖核对 {k}："+labels[v['state']]+
                     (f"：{v['outside-scope']} 条未归类" if 'outside-scope' in v else ''))
    held={k:v['outside-confirmed-scope'] for k,v in status.get('official-endpoints',{}).items() if v.get('outside-confirmed-scope')}
    for source,n in held.items():
        lines.append(f'- {source}：官方新增 {n} 个尚不能确定用途的主机，本次未加入，下一轮重新核对。')
    discoveries=status.get('discovery',{})
    discovery_attention={k:v for k,v in discoveries.items() if v['state']!='current'}
    for key,state in discovery_attention.items():
        lines.append(f"- {priority_label(entries[key])} 自动补全："+
                     {'invalid':'用途资料格式变化','unavailable':'部分来源未读到',
                      'review':'部分候选缺少独立依据或存在产品归属冲突'}[state['state']])
    if not (pending or internal_pending or inventories or held or discovery_attention): lines.append('本轮生成检查通过。下面分别列出自动补全、筛选外范围和未采用条目。')
    if discoveries:
        lines+=['','## 自动发现了什么？','',
                '官方用途资料可以支持它明确列出的范围；普通候选需要至少两个独立来源家族。镜像不重复计票，共享云父域也不能给具体主机充当第二份证据。',
                '下表的「有依据范围」包含本轮重新核对的已有条目；「新补入」才是本轮扩大覆盖的条目。来源和家族逐条记录在 data/maintenance-state.json 的 discovery.*.proofs。','',
                '| 规则 | 新补入 | 有依据范围 | 缺少依据 | 越界排除 | 既定排除 | 状态 |',
                '|---|---:|---:|---:|---:|---:|---|']
        labels={'current':'已核对','review':'需核实','unavailable':'来源未读到','invalid':'格式变化'}
        for key,state in sorted(discoveries.items(),key=lambda x:entries[x[0]]['priority']):
            lines.append(f"| {priority_label(entries[key])} {entries[key]['description']} | "+
                         f"{state.get('admitted',0)} | {len(state.get('proofs',{}))} | {state.get('pending',0)} | "+
                         f"{state.get('scope-conflicts',0)} | {state.get('policy-excluded',0)} | {labels[state['state']]} |")
        for key,state in sorted(discoveries.items(),key=lambda x:entries[x[0]]['priority']):
            if owners:=state.get('reserved-owners'):
                assigned='、'.join(f"{priority_label(entries[owner])} {entries[owner]['description']}（{count} 个）"
                                  for owner,count in owners.items())
                lines+=['',f"{priority_label(entries[key])} 来源中有明确主机已由 {assigned} 处理，因此不重复收录。"]
    if projected:=status.get('projection-coverage'):
        total=lambda field:sum(state[field] for state in projected.values())
        lines+=['','## 产品来源有没有漏查？','',
                f"当前常规产品使用 {len(projected)} 份筛选来源，程序逐份检查筛选前的域名范围，共 {total('domain-scopes')} 项；"
                f"其中 {total('selected-scopes')} 项符合当前产品筛选，{total('selected-uncovered')} 项缺少承接或被兜底抢先匹配。",
                '这些是按来源计算的范围数，同一个范围出现在两份来源里会分别计数，不是新增网站数。来源可正常解析，不代表整份内容都适合采用。',
                f"其他范围分别由已有产品、补充表和隐私规则处理；其中 {total('privacy-scopes')} 项命中隐私规则，"
                f"{total('shared-scopes')} 项属于共享范围，{total('declared-exclusions')} 项已有明确排除理由。"
                f"还有 {total('outside-selection')} 项不在当前选择或其他规则的完整覆盖内，不能把它们全部当作漏收或全部自动采用。",
                '域名后缀按完整范围核对，不能用根域命中代替所有子域都已覆盖。按精确名称收窄的项只核对该主机；逐项计数、筛选条件和其他产品归属见 data/maintenance-state.json 的 projection-coverage。筛选外名称不写进公共报告。','',
                '| 来源 | 当前产品 | 符合筛选 / 来源范围 | 其他产品 | 筛选外未覆盖 |','|---|---|---:|---:|---:|']
        for source,state in projected.items():
            products='、'.join(f"[{priority_label(entries[key])}](../rules/{rule_filename(entries[key])})" for key in state['products'])
            label=source.rstrip('/').rsplit('/',1)[-1]
            counts=f"{state['selected-scopes']} / {state['domain-scopes']}" if state['state']=='current' else {'unavailable':'未读到','invalid':'格式变化'}[state['state']]
            lines.append(f"| [{label}]({source}) | {products} | {counts} | "+
                         f"{sum(state['other-products'].values())} | {state['outside-selection']} |")
    if transfers:=status.get('projection-reassignments'):
        lines+=['','## 哪些来源范围改了归属？','',
                '只在同一来源的另一个独立产品表完整接住原范围时，允许从原表撤出。只接住根域、落入兜底或出现多个目标产品，都不能作为迁移依据；迁移记录只保存原来已发布的范围。','',
                '| 原产品 | 范围 | 当前产品 | 共同来源 |','|---|---|---|---|']
        for key,rows in transfers.items():
            for row,proof in rows.items():
                owner=proof['owner'];links='、'.join(f'[来源]({source})' for source in proof['sources'])
                lines.append(f"| {priority_label(entries[key])} {entries[key]['description']} | `{row}` | "+
                             f"{priority_label(entries[owner])} {entries[owner]['description']} | {links} |")
    expanded=status.get('expanded-inputs',{})
    if bags:={k:r for k,r in expanded.items() if r.get('method')=='public-plist-bag'}:
        lines+=['','## 消息身份入口怎样自动跟进？','',
                '读取 Apple 公开服务配置中的内层 plist，按认证、注册、查询和资料字段取主机。数字索引用于选择公开配置，不包含账号或设备标识。',
                '配置中的计时、功能开关和普通链接不当作服务器；必需业务字段失效时保留既有成品。选中用途之外的 IDS 范围仍沿用已核实补充，不据这份配置缺项撤回。','',
                '| 规则 | 明确主机 | 来源 |','|---|---:|---|']
        for key,record in sorted(bags.items(),key=lambda item:entries[item[0]]['priority']):
            hosts={row for doc in record['documents'] for row in doc['rows']}
            lines.append(f"| {priority_label(entries[key])} {entries[key]['description']} | {len(hosts)} | [公开配置]({record['directory']}) |")
    if clients:={k:r for k,r in expanded.items() if r.get('method')=='ios-client-config'}:
        lines+=['','## 客户端版本和机型怎样自动跟进？','',
                '从 Apple 公开软件目录读取当前在供的 iPhone、iPad、iPod 版本与支持机型，生成每个组合的配置请求。版本号、型号来自公开目录，不读取使用者的设备信息。',
                '逐份读取指定的定位查询、信号定位数据和地图配置字段，并遍历全部地区记录；采集与统计字段不作为定位查询入口。目录、字段或任一请求不完整时，不发布缺了一部分的结果。',
                '这是对既有定位范围的补充；SDK 默认入口和 Find My 等已有范围继续保留。逐份请求地址、机型、版本与采用主机见 data/maintenance-state.json 的 expanded-inputs。','',
                '| 规则 | 版本与机型组合 | 提取主机 | 资料 |','|---|---|---:|---|']
        for key,record in sorted(clients.items(),key=lambda item:entries[item[0]]['priority']):
            docs=record['documents'];versions={doc['version'] for doc in docs};models={doc['device'] for doc in docs}
            hosts={row for doc in docs for row in doc['rows']}
            lines.append(f"| {priority_label(entries[key])} {entries[key]['description']} | "+
                f"{len(docs)} 组（{len(versions)} 个版本、{len(models)} 个机型） | {len(hosts)} | "+
                f"[软件目录]({record['directory']}) · [本轮请求示例]({docs[0]['source']}) |")
    if templates:={k:r for k,r in expanded.items() if r.get('method')=='host-templates'}:
        lines+=['','## 地区主机怎样随来源更新？','',
                '将厂商在用途表中发布的主机模板，与其地区注册域清单组合，生成精确主机。模板和清单同时核对；共享托管租户不当地区注册域。共用入口继续按已确认的用途匹配。','',
                '| 规则 | 发布的模板 | 地区注册域 | 本轮专用主机 | 来源 |','|---|---|---:|---:|---|']
        for key,record in sorted(templates.items(),key=lambda item:entries[item[0]]['priority']):
            doc=record['documents'][0]
            lines.append(f"| {priority_label(entries[key])} {entries[key]['description']} | "+
                '、'.join('`'+value+'`' for value in record['templates'])+
                f" | {len(record['registry-domains'])} | {len(doc['rows'])} | [用途表]({record['directory']}) · [地区清单]({doc['source']}) |")
    if apis:={k:r for k,r in expanded.items() if r.get('method','api-directory')=='api-directory'}:
        lines+=['','## 哪些 API 从目录自动发现？','',
                '按官方目录的产品标题选择接口，再读取官方客户端保存的发现文档。启用端点撤回的表检查所有仍公开的版本，防止换首选版本时删掉旧客户端的主机。产品 ID、版本和服务器名称随来源变化，不在本地逐个列出。',
                '下面列出实际读取的文档；同一发布机构的目录和客户端资料不算两份独立来源。','',
                '| 规则 | API 标识 | 版本 | 专用端点 | 发现文档 |',
                '|---|---|---|---:|---|']
        for key,record in sorted(apis.items(),key=lambda item:entries[item[0]]['priority']):
            for doc in record['documents']:
                lines.append(f"| {priority_label(entries[key])} {entries[key]['description']} | {doc['name']} | "+
                             f"{doc['version']} | {len(doc['rows'])} | [来源]({doc['source']}) |")
    if pages:={k:r for k,r in expanded.items() if r.get('method')=='next-page'}:
        lines+=['','## 哪些入口从产品页面提取？','',
                '读取官方页面的资源字段和指定用途旁的请求示例，不收普通链接、统计脚本或脚本里的所有地址。路由文件随页面发布变化；用途缺失或资源越界时保留上一版。','',
                '| 规则 | 请求用途 | 专用端点 | 资料 |','|---|---|---:|---|']
        for key,record in sorted(pages.items(),key=lambda item:entries[item[0]]['priority']):
            for doc in record['documents']:
                lines.append(f"| {priority_label(entries[key])} {entries[key]['description']} | "+
                    '、'.join(doc['roles'])+f"；页面资源 | {len(doc['rows'])} | [产品页面]({record['directory']}) · [本轮路由文件]({doc['source']}) |")
    if shared:=status.get('shared-service-transfers'):
        lines+=['','## 哪些主机属于共用服务？','',
                '同一用途表把主机同时列给不同业务时，不由其中一个产品独占。程序核对共用关系及承接规则；已撤出的范围没有其他规则覆盖时，不会发布。','',
                '| 原专项 | 共用范围 | 现在由谁处理 |','|---|---|---|']
        for key,rows in shared.items():
            for row,owner in rows.items():
                label=(f"{priority_label(entries[owner])} {entries[owner]['description']}" if owner else '未确定专门归属，继续后续匹配')
                lines.append(f"| {priority_label(entries[key])} {entries[key]['description']} | `{row}` | {label} |")
    if cname:=status.get('cname-discovery'):
        lines+=['','## 服务别名怎样归类？','',
                f"CNAME 来源记录涉及 {cname['hosts-requested']} 个已公开服务主机，其中 {cname['hosts-read']} 个有读取结果；来源采集共 {cname['http-requests']} 次 HTTP 查询尝试，未读到的查询 {cname['unavailable-lookups']} 次。",
                f"本轮 {len(cname.get('incomplete-hosts',()))} 个服务的查询不完整，部分解析服务不可读的查询 {cname.get('partial-lookups',0)} 次；读取到部分结果不等于整条关系已完整核对。",
                '采用与原服务标签相符的别名，或其 CNAME 链明确指向、位于已声明私有后缀下的独立租户主机。后者只生成精确主机规则；普通清单中的相似租户名、共享父域、通用边缘服务器和解析 IP 不进入业务表。已采用的别名见 data/maintenance-state.json 的 source-aliases。',
                '这些查询用于生成规则，不会读取或更改使用者设备的 DNS 设置。']
        if evidence:=status.get('cname-alias-evidence'):
            lines+=['',
                    '每个采用的精确别名另存原服务主机及采用依据。主机查询失败、链路中途失败或只有部分解析服务成功时，只保留此前已发布、仍属于当前业务和别名范围的条目，并继续保护必需入口。恢复后重新核对；查询成功但关系变化，不当作查询失败。',
                    '下表的「本轮读到」包含再次确认的已有别名，不代表全部是新增。依据见 data/maintenance-state.json 的 cname-alias-evidence。','',
                    '| 规则 | 本轮读到 | 查询不完整时保留 |','|---|---:|---:|']
            for key,rows in sorted(evidence.items(),key=lambda item:entries[item[0]]['priority']):
                lines.append(f"| {priority_label(entries[key])} {entries[key]['description']} | "+
                    f"{sum(proof['state']=='current' for proof in rows.values())} | "+
                    f"{sum(proof['state']=='retained' for proof in rows.values())} |")
    if inventories:=status.get('service-inventories'):
        lines+=['','## 服务清单如何轮换端点？','',
                '完整服务清单先合并所有来源，新增端点直接参与生成，已采用主机从所有清单消失后才隔轮确认撤回。已发布包的下载地址另算：最新版本换了主机，其他版本仍可能使用原地址，因此保存公开版本依据并继续保留。','',
                f"本轮 {status.get('inventory-domain-cases',0)} 个服务或文件主机随清单生成命中用例，参与细分、合集和可选规则的组合检查。固定业务用例仍独立保留。",'',
                '| 规则 | 本轮来源范围 | 保留观察 | 已确认撤回 | 发布文件主机 | 状态 |','|---|---:|---:|---:|---:|---|']
        for key,state in sorted(inventories.items(),key=lambda item:entries[item[0]]['priority']):
            label='等下一轮确认' if state['state']=='observing' else '已核对'
            lines.append(f"| {priority_label(entries[key])} {entries[key]['description']} | "+
                f"{len(state['observed'])} | {len(state['retained'])} | {len(state['retired'])} | {len(state.get('artifact-hosts',{}))} | {label} |")
    if history:={key:state for key,state in status.get('config-endpoint-history',{}).items() if state['retained']}:
        lines+=['','## 局部配置缺项后保留了什么','',
                '只沿用已经发布且仍符合当前用途的精确主机。下面是历史依据保留，不表示本轮配置再次列出；来源与最初采用时间见维护状态的 config-endpoint-history。','']
        lines.extend(f"- {priority_label(entries[key])} {entries[key]['description']}：{len(state['retained'])} 个主机。"
                     for key,state in history.items())
    if mirrors:=status.get('source-mirrors-used'):
        lines+=['','## 本轮用了哪些备用来源？','',
                '主入口无法读取或资料无效时才尝试已声明的官方备用入口。备用地址沿用原来源身份，不算第二份独立证据；分配资料还核对发布机构、日期、记录总数和 ASN、IPv4、IPv6 是否齐全。','']
        lines.extend(f'- [原来源]({primary}) → [本轮读取的备用入口]({actual})' for primary,actual in mirrors.items())
    if maintenance:=status.get('maintenance-audit'):
        fixed=maintenance['fixed-declarations'];pure=maintenance['fixed-only']
        lines+=['','## 哪些仍是固定清单？','',
                f"{len(fixed)} 份独立表含有 {sum(fixed.values())} 条固定声明，其中 {len(pure)} 份表完全按固定清单生成。"
                '数量统计 include、literal_ips 和 dns_required 的声明，不是去重后的规则数量；合集与衍生表不重复计算。','',
                '下面列出完全按固定清单生成的表。官方存在核对只检查已列入口还在不在，不能替代新端点发现。'
                '混合表的逐组数量见 data/maintenance-state.json 的 maintenance-audit.fixed-declarations。','',
                '| 序号 | 英文名称 | 中文名称 | 固定声明 | 官方存在核对 |','|---|---|---|---:|---:|']
        for k in pure:
            e=entries[k]
            lines.append(f"| {priority_label(e)} | [{k}](../rules/{rule_filename(e)}) | {e['description']} | {fixed.get(k,0)} | {maintenance['official-checks'].get(k,0)} |")
        lines+=['',f"另有 {len(maintenance['baseline-managed'])} 份表以上一版已审内容为基线，按各自条件接纳或撤回变化；"
                '其中有官方用途提取、交叉核对和连续确认，不是每份都能自动接纳所有上游新增项。','',
                f"{len(maintenance['source-scoped'])} 份表按来源筛选，但产品根域、地区和用途边界仍由人工设定。"
                '测试用例和官方核对清单也有固定样本，样本通过不代表未知端点已经覆盖。'
                '局域网地址、明确的隐私选择可以保留固定声明；能从可靠用途资料读取的服务端点应继续接入来源。'
                '[具体维护方式](../docs/maintenance.md#哪些仍由人决定)']
        selectors=maintenance.get('exact-selectors',{})
        lines+=['',f"另有 {len(selectors)} 份表使用 {sum(selectors.values())} 个精确名称筛选条件，逐组数量见 maintenance-audit.exact-selectors。"
                '这些名称仍需人工设定，移到筛选条件里不算自动发现；产品根域、地区和用途条件也仍属于维护声明。']
        if derived:=maintenance.get('address-derived'):
            lines+=['',f"{sum(derived.values())} 条反查域名由同一份地址声明计算，不另列主机清单；"
                    '地址范围及其解析用途仍由人工决定。这属于消除重复维护，不算发现新服务。']
    if functional:=status.get('functional-hosts'):
        lines+=['','## 必需入口怎样避免误拦？','',
                f'本轮从已标记用途的来源提取 {len(functional)} 个必需主机，先保护这些入口，再生成广告规则。官方新增入口即使尚未写入固定用例，也参与保护。普通统计和未选中的共享平台不因此放行；具体名单见 data/maintenance-state.json 的 functional-hosts。']
    if explained:={k:v['reviewed-outside'] for k,v in status['source-inventories'].items() if v.get('reviewed-outside')}:
        lines+=['','## 来源中哪些范围已说明不收录？','',
                '这些范围已有用途说明，不计为未归类。源清单出现其他新范围，仍会重新列入待核对项。具体理由见 config/catalog.json 的 reviewed-outside。','']
        lines.extend(f'- {k}：{n} 条' for k,n in explained.items())
    checked=[k for k in ordered if 'unconfirmed-prefixes' in states[k] or 'not-whole-host-consensus' in states[k] or 'unconfirmed-domains' in states[k] or 'unconfirmed-asns' in states[k] or 'unaligned-prefixes' in states[k] or 'excluded-client-matches' in states[k]]
    if checked:
        lines+=['','## 哪些候选没有加入？','']
        unchanged=[]
        for k in checked:
            v=states[k]; tag=f"{priority_label(entries[k])}"
            figures=(('unaligned-prefixes','{} 条 IP 与掩码未对齐，未收录'),
                     ('excluded-client-matches','{} 条客户端或 URL 匹配不用于这份域名表'),
                     ('admitted-asns','新增 {} 个 ASN'),('unconfirmed-asns','{} 个 ASN 缺少清单或分配记录佐证，未加入'),
                     ('accepted-prefixes','新增 {} 个网段'),('retired-prefixes','撤回 {} 个网段'),
                     ('unconfirmed-prefixes','{} 个网段缺少分配或路由依据，未加入'),
                     ('admitted-rules','新增 {} 条规则'),('retired-rules','撤回 {} 条规则'),
                     ('not-whole-host-consensus','{} 条缺少整域拦截依据，未整站拦截'),
                     ('unconfirmed-domains','{} 条候选没有国内产品清单佐证，未加入'))
            details=[label.format(f'{v[field]:,}') for field,label in figures if v.get(field)]
            if details: lines.append(f"- {tag}："+'；'.join(details)+'。')
            else: unchanged.append(tag)
        if unchanged: lines.append('- '+'、'.join(unchanged)+'：以上核对均没有新增、撤回或排除项。')
    outside=[k for k in ordered if states[k].get('outside-purpose') or states[k].get('reserved-scopes')]
    if outside:
        lines+=['','## 范围外：共用主机和国际版服务','',
                '云平台替多家产品托管内容，不能根据云平台的名字判断产品或地区。国内表也会排除国际版 AI 的域名，以及会把它们一起匹配进去的父域。','']
        for k in outside:
            reason='、'.join(f'{v} 条{label}' for field,label in [('outside-purpose','共享托管范围'),('reserved-scopes','与国际版 AI 重叠')] if (v:=states[k].get(field)))
            lines.append(f"- {priority_label(entries[k])}：{reason}")
    if conflicts:=status.get('fallback-conflicts'):
        lines+=['','## 海外与国内来源有哪些重合？','',
                '具体产品先匹配；已声明优先的海外与受限站点来源保留在海外补充，不被宽泛国内表扣除。未声明优先权的输入仍按保护范围处理。下面记录来源相交条数，不表示全部被删除，也不能相加当作网站数。','']
        for dest,counts in conflicts.items():
            lines.append(f"- {priority_label(entries[dest])}："+'；'.join(
                f"{entries[k]['description']} 有 {v} 条相交" for k,v in counts.items()))
    if ip:=status.get('ip-matching'):
        lines+=['','## 哪些 IP 规则会为了匹配而解析域名？','',
                '这份表逐一检查所有含 IP 的独立订阅，合集不重复计数。域名规则未命中后，允许解析的 IP 规则才可能参与；解析器由 Loon 的 DNS 设置决定。',
                '', '| 规则 | 只匹配已有 IP | 允许解析后匹配 |','|---|---:|---:|']
        for k in sorted(ip,key=lambda k:entries[k]['priority']):
            v=ip[k]
            lines.append(f'| {priority_label(entries[k])} · {entries[k]["description"]} | {v["no-resolve"]} | {v["resolve-for-match"]} |')
        lines+=['','[IP 规则的解析用途](../docs/network-testing.md#ip-规则为什么有的保留解析)']
    return '\n'.join(lines)+'\n'


def render_index(config, entries):
    public={entry['id'] for entry in config['entries']}
    entries={key:entry for key,entry in entries.items() if key in public}
    sections={s['id']:s for s in config['sections']}
    optional=set(config['optional'])
    alternatives=set(config['alternatives'])
    views=set(config['views'])
    base='https://raw.githubusercontent.com/LuckyLight6/loon-rules/main/rules/'
    lines=['# Loon 规则订阅清单','','## 在 Loon 中怎么排','',
           '从上往下读，就是订阅的匹配顺序。只选自己要用的行，保持它们的相对位置即可。'
           '标题按章节编号，表中序号对应规则文件，也按匹配顺序递增，各类留有空号。英文名称对应文件名；点名称可看正文、来源和更新时间，在最后一列复制订阅地址。','',
           '同一出口可以用合集；要分别选节点，就用它的成员，不要两者都开。'
           'Loon 刷新订阅只更新正文，不会自动移动设备上已有的订阅。'
           '本地规则和插件也可能先匹配。[怎么查实际命中](network-testing.md)','']
    bands=config.get('routing-bands') or [
        {'title':s['title'],'ids':[k for k,e in entries.items() if e['section']==s['id']]}
        for s in sections.values()]
    positions={key:i for i,key in enumerate(sorted(entries,key=lambda key:entries[key]['priority']))}
    def members_text(member_ids):
        members=sorted(member_ids,key=lambda key:entries[key]['priority'])
        groups=[]
        for key in members:
            if groups and positions[key]==positions[groups[-1][-1]]+1:groups[-1].append(key)
            else:groups.append([key])
        return '、'.join(priority_label(entries[g[0]]) if len(g)==1 else
                        priority_label(entries[g[0]])+'–'+priority_label(entries[g[-1]]) for g in groups)
    for band_number,band in enumerate(bands,1):
        sub_number=0
        lines+=[f'## {band_number} '+band['title'],'']
        if band.get('note'):lines+=[band['note'],'']
        subtitles=dict(band.get('subheadings',{}))
        for i,key in enumerate(band['ids']):
            if key not in views:
                continue
            title=entries[key].get('index-title',entries[key]['description'])
            subtitles.setdefault(key,title if '合集' in title else title+'合集')
            if i+1<len(band['ids']) and band['ids'][i+1] not in views:
                subtitles.setdefault(band['ids'][i+1],'细分规则')
        if set(subtitles)-set(band['ids']):
            raise rules.Invalid('目录小标题没有对应的订阅')
        for i,k in enumerate(band['ids']):
            if k in subtitles:
                sub_number+=1
                lines+=([''] if i else [])+[f'### {band_number}.{sub_number} '+subtitles[k],'']
            if i==0 or k in subtitles:
                lines+=['| 序号 | 英文名称 | 中文名称 | 用途与选择 | 订阅地址 |','|---:|---|---|---|---|']
            e=entries[k]; number=f'{priority_label(e)}';name=rule_filename(e)
            selection=(f'**合集：替代 {members_text(e["members"])}。** ' if k in views else
                       '**可选。** ' if k in optional or k in alternatives else '')
            desc=e.get('index-title',e['description']).rstrip('。')
            lines.append(f'| {number} | [{k}](../rules/{name}) | {desc} | {selection}{e["boundary"]} | [订阅地址]({base}{name}) |')
        lines.append('')
    lines+=['产品专表已列在各业务下；统一出口用合集，分别选出口用其成员。'
            '[各组怎么选出口](routing.md) · [各类规则怎样更新](maintenance.md) · '
            '[参与维护](development.md)']
    return '\n'.join(lines)+'\n'

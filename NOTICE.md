# 规则来源与许可

想知道一条规则从哪里来，先看文件开头的 `source`。各组用到的资料也列在 [catalog.json](catalog.json)。有些来源用来生成规则，有些只用来确认域名或网段的用途。订阅地址指向本仓的规则，不会在客户端运行上游的插件或脚本。

| 来源 | 许可文本 | 用途 |
|---|---|---|
| [o-ocn / loon-rules](https://github.com/o-ocn/loon-rules) | [GPL-2.0](licenses/o-ocn--loon-rules.txt) | 从 Loon 规则中筛选通讯、游戏、国内平台、Google、OneDrive 和 TestFlight 等服务；也用于整理 Drive 规则。 |
| [Repcz / Tool](https://github.com/Repcz/Tool) | [MIT](licenses/Repcz--Tool.txt) | 从专项表核对流媒体、网络和 Apple 条目。海外与 GFW 名单筛成域名供 `185` 合并；广告、Microsoft 和国内网段保留本仓审核、去重后的版本。 |
| [blackmatrix7 / ios_rule_script](https://github.com/blackmatrix7/ios_rule_script/tree/master/rule/Loon) | [GPL-2.0](licenses/blackmatrix7--ios_rule_script.txt) | 核对局域网、音乐、直播和微信专用域，也用于 Private Relay 专项。 |
| [SukkaW / Surge](https://github.com/SukkaW/Surge) | [AGPL-3.0](licenses/SukkaW--Surge.txt) | 海外媒体兜底只取明确域名和后缀，不导入宽泛的关键字、UA 或进程规则。 |
| [MetaCubeX / meta-rules-dat](https://github.com/MetaCubeX/meta-rules-dat) | [GPL-3.0](licenses/MetaCubeX--meta-rules-dat.txt) | 核对 Apple 大陆下载别名、证书、更新、Copilot 和部分 AI 服务。 |
| [xkww3n / Rules](https://github.com/xkww3n/Rules) | [MIT](licenses/xkww3n--Rules.txt) | 用于联网探测、保留地址、Apple 媒体和智能服务。通用站点、广告及国内 IP 备选保留审核后的版本。 |
| [VPSDance / ai-proxy-rules](https://github.com/VPSDance/ai-proxy-rules) | [MIT](licenses/VPSDance--ai-proxy-rules.txt) | 海外 AI 专项；合集直接合并这些专项，不再维护另一份相同数据。 |
| [erwanjun / surge-claude-rules](https://github.com/erwanjun/surge-claude-rules) | [MIT](licenses/erwanjun--surge-claude-rules.txt) | 核对 Claude 的匹配范围；海外 AI 合集使用同一份 Claude 规则。 |
| [Kianuni / AppleFlow](https://github.com/Kianuni/AppleFlow) | [MIT](licenses/Kianuni--AppleFlow.txt) | 只用 Siri 规则；不加载插件，也不改 ChatGPT 的分流。 |

014 读取 [DDNS Updater 的 HTTP 出口查询服务清单](https://github.com/qdm12/ddns-updater/blob/master/README.md)、[AWS CLI 的公网地址示例](https://docs.aws.amazon.com/cli/latest/userguide/cli-services-ec2-sg.html)和 [IPIP 的查询说明](https://www.ipip.net/myip.html)，只提取服务地址，不复制说明文字。

Apple、OpenAI、GitHub、Telegram、百炼和 TokenHub 等官方资料用来核对端点，不转载原文。没有明确转载许可的来源只作为核对依据，不复制整份规则。各上游内容仍按各自许可使用。

扩展广告表用 [EasyList、EasyPrivacy](https://easylist.to/) 和 [AdGuard DNS](https://github.com/AdguardTeam/AdGuardSDNSFilter) 核对上游拦截范围，不转载浏览器过滤规则；[EasyList 许可](https://easylist.to/pages/licence.html) · [AdGuard DNS 许可](https://github.com/AdguardTeam/AdGuardSDNSFilter/blob/master/LICENSE)。国内网段的新增范围核对 [APNIC 分配统计](https://ftp.apnic.net/stats/apnic/)和[中国运营商 BGP 数据](https://github.com/gaoyifan/china-operator-ip)。两者分别表示分配地和路由归属，不用于判断个人位置。

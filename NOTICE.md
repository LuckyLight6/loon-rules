# 来源与许可

生成器代码、测试和本仓原创文档使用 [MIT License](LICENSE)。上游规则、第三方数据及其衍生成品保留各自许可；维护代码的许可不会替换规则来源的许可。合集也需保留其成员的来源声明。

每份 `.lsr` 的 `source` 列出使用的公开资料；[分类声明](config/catalog.json)记录具体读取和筛选条件。动态发现文档、公开版本和采用依据在 [维护状态](data/maintenance-state.json)中。部分资料只用于核对用途，并未导入整份规则。订阅本仓规则不会运行上游插件或脚本。

## 社区规则

| 项目 | 用途 | 许可原文 |
|---|---|---|
| [o-ocn / loon-rules](https://github.com/o-ocn/loon-rules) | 筛选通讯、游戏、国内平台、Google、OneDrive、TestFlight 与 Drive 范围 | [GPL-2.0](licenses/o-ocn--loon-rules.txt) |
| [Repcz / Tool](https://github.com/Repcz/Tool) | Apple、联网、媒体、广告、Microsoft、国内域名与网段；海外和 GFW 输入只取核对后的域名 | [MIT](licenses/Repcz--Tool.txt) |
| [blackmatrix7 / ios_rule_script](https://github.com/blackmatrix7/ios_rule_script/tree/master/rule/Loon) | 局域网、音乐、直播、微信与 iCloud Private Relay 等用途核对 | [GPL-2.0](licenses/blackmatrix7--ios_rule_script.txt) |
| [SukkaW / Surge](https://github.com/SukkaW/Surge) | 海外影音与 Apple 通用服务的已选域名，不照搬关键字、User-Agent、进程匹配或整个 Apple IP 段 | [AGPL-3.0](licenses/SukkaW--Surge.txt) |
| [MetaCubeX / meta-rules-dat](https://github.com/MetaCubeX/meta-rules-dat) | Apple 别名、证书、更新，以及 AI、开发、通讯、游戏、媒体等产品范围 | [GPL-3.0](licenses/MetaCubeX--meta-rules-dat.txt) |
| [v2fly / domain-list-community](https://github.com/v2fly/domain-list-community) | Spotify、Reddit、Slack 与 Discord 的原生产品清单；保留精确主机、属性和分类引用的含义，共享平台另行核对 | [MIT](licenses/v2fly--domain-list-community.txt) |
| [arkadiyt / bounty-targets-data](https://github.com/arkadiyt/bounty-targets-data) | Spotify 公开安全项目的结构化资产与产品用途；读取完整项目后分配品牌网站、独立产品及广告平台，不把漏洞奖励范围当成所有权或完整网络清单 | [MIT](licenses/arkadiyt--bounty-targets-data.txt) |
| [xkww3n / Rules](https://github.com/xkww3n/Rules) | 联网、保留地址、Apple 媒体与智能服务、广告及国内外范围比对 | [MIT](licenses/xkww3n--Rules.txt) |
| [VPSDance / ai-proxy-rules](https://github.com/VPSDance/ai-proxy-rules) | 海外 AI 产品；合集由本仓细分生成 | [MIT](licenses/VPSDance--ai-proxy-rules.txt) |
| [erwanjun / surge-claude-rules](https://github.com/erwanjun/surge-claude-rules) | Claude 产品范围核对 | [MIT](licenses/erwanjun--surge-claude-rules.txt) |
| [anomalyco / models.dev](https://github.com/anomalyco/models.dev) | 按提供商身份读取 API 字段和产品文档地址；区分已明确列出的地区计划，不采用整家共享云 | [MIT](licenses/anomalyco--models.dev.txt) |
| [Kianuni / AppleFlow](https://github.com/Kianuni/AppleFlow) | 参考 Siri 规则，不加载插件 | [MIT](licenses/Kianuni--AppleFlow.txt) |

## 官方资料与公开产品数据

以下资料用于读取端点、字段和用途，保存必要的公开主机及采用依据，不转载整篇说明、客户端实现或抓取原文。文件头与分类声明包含逐份实际来源。

| 资料 | 读取范围 |
|---|---|
| [Apple 企业网络表](https://support.apple.com/en-us/101555)、[iTunes 公开配置](https://init.itunes.apple.com/bag.xml) | 服务用途，以及商店、音乐和视频 API 字段；不把统计或历史链接一起当作接口 |
| [Apple 软件目录](https://gdmf.apple.com/v2/pmv)、[定位配置](https://configuration.ls.apple.com/config/defaults?os=ios&os_version=16.7.11&hardware=iPhone10%2C1) | 从公开版本与机型组合读取定位、瓦片及地区资源主机。参数格式参考[公开研究](https://arxiv.org/html/2610.21597)，数据来自 Apple；不读取个人设备或位置 |
| [Apple IDS 公开配置](https://init.ess.apple.com/WebObjects/VCInit.woa/wa/getBag?ix=3)、[OpenBubbles 常量](https://github.com/OpenBubbles/rustpush/blob/master/src/util.rs) | 数字索引请求格式及认证、注册、查询字段；不保存证书、签名、开关，也不进行身份或消息操作 |
| [appleseum 的 GrandSlam 主机策略](https://github.com/hyperion-cs/appleseum/blob/main/applekit/internal/httpx/trust.go) | 从第三方客户端的 GrandSlam 专用分支读取精确生产主机；保留来源，遵循其 [Apache-2.0 许可](https://github.com/hyperion-cs/appleseum/blob/dev/LICENSE)，不复制或执行客户端源码 |
| [PyiCloud 的账户接口](https://github.com/timlaing/pyicloud/blob/main/pyicloud/services/account.py)、[邮件端点定义](https://github.com/timlaing/pyicloud/blob/main/pyicloud/endpoints.py)与公开 DNS | 核对 iCloud 订阅、发件设置与存储配额的用途。2010 用两位和三位数字分片规则识别对应主机，邮件正文、附件和共享网关由 iCloud 同步规则处理 |
| [Google 地区域名](https://www.google.com/supported_domains)、[Android 网络用途](https://support.google.com/work/android/answer/10513641)、[API 目录](https://www.googleapis.com/discovery/v1/apis)、[官方客户端文档](https://github.com/googleapis/google-api-python-client/tree/main/googleapiclient/discovery_cache/documents) | 地区登录模板与产品 API；[OAuth 文档](https://developers.google.com/identity/protocols/oauth2/web-server)只取账户用途链接 |
| [Microsoft 365](https://learn.microsoft.com/en-us/microsoft-365/enterprise/urls-and-ip-address-ranges)、[Azure CLI 定义](https://github.com/Azure/azure-cli/blob/dev/src/azure-cli-core/azure/cli/core/cloud.py)、[Azure 域名](https://learn.microsoft.com/en-gb/azure/security/fundamentals/azure-domains) | 办公、通信和控制端点，区分平台与托管租户；只解析静态定义，不运行源码 |
| [OpenAI 语音地址](https://openai.com/chatgpt-voice.json)、[GitHub Copilot](https://docs.github.com/en/copilot/reference/copilot-allowlist-reference)、[Microsoft Copilot](https://www.microsoft.com/en-us/microsoft-copilot/for-individuals/termsofuse) | 语音公网地址、专用 API、实时连接与产品入口；共用认证分别处理 |
| [Cursor 登录](https://cursor.com/help/troubleshooting/sign-in-domains)、[网络清单](https://cursor.com/docs/enterprise/network-configuration)、[xAI 登录](https://docs.x.ai/x-subscription/sign-in) | 共用账号、产品接口、Grok 内容与更新用途；相关 SDK 只读取静态默认端点 |
| [Amp 网络清单](https://ampcode.com/security)、[AnythingLLM 产品站](https://anythingllm.com/)、[Fireworks API 文档](https://docs.fireworks.ai/tools-sdks/openai-compatibility) | 专用产品域名、WebSocket、API 及隧道入口；自建实例和用户指定的模型服务不随官网归类 |
| [硅基流动国内](https://docs.siliconflow.cn/docs/userguide/quickstart)、[国际指南](https://docs.siliconflow.com/en/userguide/quickstart)、[Liblib API](https://www.liblib.art/apis/workflow) | 对应地区的 API 与控制台；产品页面只跟随指定资源和用途示例，不执行脚本 |
| [GitHub Meta API](https://api.github.com/meta)、[Docker](https://docs.docker.com/desktop/enterprise/allow-list/)、[VS Code](https://code.visualstudio.com/docs/setup/network) | 网站、包源、构建、登录、分发、更新与同步用途；不采用整家共享云或 GitHub 大段 IP |
| [GitHub Pages 用途](https://docs.github.com/en/pages/getting-started-with-github-pages/what-is-github-pages)、[产品入口](https://pages.github.com/)与 [Actions 网络要求](https://docs.github.com/en/actions/reference/runners/self-hosted-runners) | 核对默认网站托管、原始内容和构建服务的用途；自定义域名不因共享 IP 被归为 Pages，不把 Actions 可访问的整家云平台认作 GitHub 专用服务 |
| [Cargo 配置](https://index.crates.io/config.json)、[PyPI](https://pypi.org/pypi/pip/json)、[npm](https://registry.npmjs.org/npm/latest) | 服务与文件下载字段、公开版本依据；不复制包内容、作者资料、摘要或签名 |
| [JetBrains 网络表](https://support.jetbrains.com/api/v2/help_center/en-us/articles/40250675463570.json)、[Node.js](https://nodejs.org/en)、[ACP](https://agentclientprotocol.com/) | AI 地区注释、IDE 用途及独立产品身份，不复制安装程序或代理实现 |
| [Signal](https://support.signal.org/hc/en-us/articles/360007320291-Firewall-and-Internet-settings)、[Slack](https://slack.com/help/articles/360001603387-Manage-Slack-connection-issues)、[Tailscale DERP](https://controlplane.tailscale.com/derpmap/default) | 公开客户端与实时主机、中继名称；不读取用户工作区或 Tailnet 配置 |
| [Spotify oEmbed](https://developer.spotify.com/documentation/embeds/reference/oembed)、[Discord 安全范围](https://discord.com/security)及 [Activities 网络说明](https://github.com/discord/discord-api-docs/blob/main/developers/activities/development-guides/networking.mdx) | 从 Spotify 基础 URI 说明读取内容链接主机；区分 Discord 通讯与承载第三方应用的 Activities 代理平台，不复制文档正文 |
| [Spotify 安全项目入口](https://www.spotify.com/bounty)、[Sonantic 产品说明](https://newsroom.spotify.com/2022-06-13/spotify-to-acquire-sonantic-an-ai-voice-platform/)、[广告分析说明](https://newsroom.spotify.com/2023-06-13/evolving-brands-measurement-experience-with-all-new-spotify-ad-analytics/)、[WhoSampled 用途](https://newsroom.spotify.com/2026-04-20/deeper-music-features-about-the-song-dj-songdna/)、[Backstage 项目历史](https://backstage.io/docs/overview/background/) | 核对项目身份和产品用途，区分音乐、语音 AI、音乐资料库、广告分析和已捐赠 CNCF 的开发者项目；源码仓库、App 包名与测试排除项不自动变成流量规则 |
| [Netflix 连接检查](https://help.netflix.com/en/node/14424)、[FAST 的测量方式](https://netflixtechblog.com/building-fast-com-4857fe0f8adb) | 按官方用途读取 FAST 测速网站，并独立核对全部可达地址；区分播放与配套测速，不从说明中的 DNS 设置建议生成设备配置 |
| [Atlassian](https://support.atlassian.com/organization-administration/docs/ip-addresses-and-domains-for-atlassian-cloud-products/)、[Notion](https://www.notion.com/help/allowlist-ip)、[Ubisoft](https://www.ubisoft.com/legal/documents/termsofuse/en-US) | 自营、产品与共用范围；合作方、出站 IP、公共租户与自定义域不直接归入 |
| [Link](https://www.link.com/)、[Venmo](https://venmo.com/)、[Xoom](https://www.xoom.com/)、[Braintree](https://developer.paypal.com/braintree/docs/reference/general/braintree-ip-addresses) | 产品身份与生产、沙箱域名，不发起账户或交易请求 |
| [Binance REST](https://github.com/binance/binance-spot-api-docs/blob/master/rest-api.md)、[WebSocket](https://github.com/binance/binance-spot-api-docs/blob/master/web-socket-streams.md)、[Gemini Exchange](https://developer.gemini.com/rest) | 基础端点与服务器字段，不转载交易示例 |
| [DDNS Updater](https://github.com/qdm12/ddns-updater/blob/master/README.md)、[AWS CLI 示例](https://docs.aws.amazon.com/cli/latest/userguide/cli-services-ec2-sg.html)、[IPIP](https://www.ipip.net/myip.html) | 公网出口查询服务地址，不采集使用者的回显 IP |
| [新浪新闻](https://news.sina.com.cn/)及产品官方身份资料 | 核对跨产品图片或独立站点用途；普通导航和第三方文章不作为端点清单 |

## 过滤、网段与域名边界数据

- [EasyList、EasyPrivacy](https://easylist.to/)与 [AdGuard DNS](https://github.com/AdguardTeam/AdGuardSDNSFilter)用于核对整域拦截及例外，不转载浏览器过滤规则。[EasyList 许可](https://easylist.to/pages/licence.html) · [AdGuard DNS 许可](https://github.com/AdguardTeam/AdGuardSDNSFilter/blob/master/LICENSE)
- [APNIC 分配统计](https://ftp.apnic.net/stats/apnic/)、[官方备用入口](https://rsync.apnic.net/stats/apnic/)与[中国运营商 BGP 数据](https://github.com/gaoyifan/china-operator-ip)用于地址范围核对；登记地与路由归属不能证明服务器所在地
- [Public Suffix List](https://publicsuffix.org/list/)用于识别注册域与共享托管边界。原始数据保存在 [data/public-suffix-list.dat](data/public-suffix-list.dat)，保留源声明，按 [MPL-2.0](licenses/Public-Suffix-List--MPL-2.0.txt)使用
- CNAME 资料来自 [Google Public DNS](https://developers.google.com/speed/public-dns/docs/doh/json)和 [Cloudflare DNS](https://developers.cloudflare.com/1.1.1.1/encryption/dns-over-https/make-api-requests/dns-json/)。生成器只查询已公开服务名称，保存采用关系，不发布解析 IP 或响应原文；这些查询不设置使用者设备的 DNS

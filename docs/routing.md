# 各服务怎么选出口

以下按中国大陆网络、`FINAL` 走代理说明。需要分开的是**业务出口**，不必为每份规则新建策略组：多个产品可以共用一个稳定代理，下载和内网再单独选路。订阅地址与执行位置见[规则清单](rules.md)。

## Apple：普通服务先直连，海外功能单独代理

日常选三份订阅即可。账户、App Store、iCloud、下载、更新与普通 Siri 默认直连；PCC、TV、News 等海外功能用稳定代理；推送保留已能正常收通知的出口。

| 序号 | 订阅 | 建议出口 | 覆盖与用法 |
|---:|---|---|---|
| 2010 | Apple 海外功能合集 | 功能支持地区的稳定代理 | PCC、系统 AI 扩展、Private Relay、TV、Fitness+、News、Sports；已含 2020，不再单独叠加 |
| 2070 | APNs 推送 | 保留现用稳定出口 | 直连漏通知时可单独选代理，不随全部 Apple 请求切换 |
| 2080 | Apple 日常直连合集 | 直连优先 | 账户、商店、iCloud、Music、普通 Siri、下载、证书与系统服务；包括 Apple 通用补充，放在海外功能和推送后面 |

这是默认用法，不要求再建三十多个策略组。需要单独调整某项业务时，改用对应的细分方案。2010、2080 与各自成员二选一；完整的 2000 统一出口方案也不和这套日常组合叠加，生成检查会拒绝冲突的合集选择。

美区 Apple 账户本身不要求美国 IP，代理也不能保证防止账户锁定。出口按实际可用性选择：优先保证登录、验证码、同步、下载和系统功能；确认某项直连不可用时，再对该业务选择稳定代理。上传、备份和系统包不为追求地区一致而默认消耗代理配额。

Apple 在中国大陆提供 App Store、Apple Music 和免费播客；TV、News、Fitness+、Apple Intelligence 等需分别满足服务支持条件。代理不会替代设备、账户、订阅或地区资格。[Apple 服务地区](https://support.apple.com/en-us/118205) · [Apple Intelligence 要求](https://support.apple.com/en-us/121115)

<details>
<summary>需要分别选路时，查看细分业务</summary>

| 序号 | 用途 | 默认选择与边界 |
|---:|---|---|
| 2020 | Apple Intelligence、PCC、系统 AI 扩展 | 稳定代理；日常由 2010 包含。独立 ChatGPT App 和 1020 仍单独处理，本机推理不产生 PCC 连接 |
| 2090 | 账户认证与 iCloud 账户控制 | 直连优先，包括已识别的订阅、发件设置和配额查询 |
| 2100 | App Attest、设备验证、macOS 公证 | 直连优先，保留验证连接；不能当成普通图片 CDN |
| 2110 | Wallet / Apple Pay | 直连优先，保留已能支付的路径；仍受设备、发卡方、商户和地区资格影响 |
| 2120 | TestFlight | 直连优先；测试分发和安装包下载分别检查 |
| 2130 | App Store、Books 目录、搜索与交易 | 直连优先；目录、验证码、购买和安装指令需能完成，安装包另在 2140 |
| 2140 | App 安装包 | 直连优先，节省下载配额；只下载失败时检查实际包体连接 |
| 2150 | 通用链接与 App 关联验证 | 直连优先，保证网站与 App 关联可用 |
| 2070 | APNs 推送 | 保留稳定出口；无法按国内或国外 App 拆分系统推送连接 |
| 2160 | Find My 设备与朋友查找 | 直连优先；同时依赖账户、iCloud 与推送，不能只验证这一组 |
| 2170 | 定位与地图配置 | 直连优先；定位主机与 Find My 已识别入口分别维护 |
| 2180 | IDS 身份、注册与查询 | 直连优先；不代表全部 iMessage 正文或 FaceTime 媒体流量 |
| 2030 | iCloud Private Relay | 使用可用地区的稳定代理；系统功能还需已启用并符合地区要求 |
| 2190 | 大陆 iCloud 专域 | 直连；只识别已确认的大陆专域，不据此判断账户或存储国家 |
| 2200 | iCloud 内容域 | 直连优先；可能包含上传、下载与签名访问条件 |
| 2210 | iCloud、CloudKit、同步、邮件与 iWork | 直连优先；这组也可能承载照片、备份与文件传输 |
| 2220 | Podcasts | 直连优先；第三方托管的节目仍按其实际目标选路 |
| 2230 | Music、广播与业务 API | 与音频分发一起先试直连，目录和连续播放分别验证 |
| 2240 | Music 音频分发 | 直连优先；只覆盖已识别音频主机 |
| 2040 | TV、Fitness+ 门户与播放控制 | 稳定代理，先满足账户和订阅资格 |
| 2050 | TV 视频分发 | 同 2040，避免门户可用但播放失败；节省配额可先调低画质 |
| 2060 | News、News+ 与 Sports | 稳定代理，以正文和内容能加载为准 |
| 2250 | 普通 Siri、听写与 Spotlight | 直连优先；PCC 和系统 AI 扩展由 2020 或 2010 先匹配 |
| 2260 | 更新目录、检查、授权与登记 | 直连优先；实际更新包另在 2270 |
| 2270 | 系统更新与恢复包 | 直连优先，不自动把大包回退到代理 |
| 2280 | Developer 门户 | 直连优先；实际不可达时单独比较该业务的代理路径 |
| 2290 | Xcode、Playgrounds 与开发组件下载 | 直连优先，和门户、账户分开 |
| 2300 | 已确认的大陆分发别名 | 直连；不凭 CDN 厂商或域名拼写推断地理位置 |
| 2310 | 商店与媒体共用素材 | 直连优先；前面的验证和业务专用主机先匹配 |
| 2320 | 证书状态检查 | 直连优先；部分 DigiCert 主机也服务其他厂商，日常由 2080 包含 |
| 2330 | 系统基础联网 | 直连优先，保留 eSIM、MDM、校时、系统 DNS 与公共素材的可用路径 |
| 2340 | Schoolwork 资料 | 直连优先，或按学校网络要求；不代表全部账户和设备管理 |
| 2350 | 设备激活与 APNs 证书登记 | 直连优先，不把登记失败简单归因于账户地区 |
| 2360 | Feedback Assistant 与诊断上传 | 直连优先；反馈文件也有流量，规则不会开启诊断分享 |
| 2370 | Apple 官网与通用服务 | 直连优先，接住细分未识别的 Apple 自有服务域；日常由后置的 2080 包含 |

</details>

2370 跟随 Sukka 的 Apple 公司域名来源，细分先匹配，不使用整个 Apple IP 段。2080 包含这层通用范围，因此海外例外和 APNs 必须先匹配。规则中的静态内容也可能带签名或需要许可，不能用“有没有认证”决定出口。

2000 是完整合集，包含 PCC、海外媒体、推送、证书和通用服务，替代所列全部成员。日常既要海外功能可用，又要大流量直连，采用上面的三份组合。

网页语言、地区选择与请求出口分别检查。注册页面默认中国大陆不能单独证明分流错误；验证码图像能否加载、认证和提交能否完成，才是这条路径的实际验收项。无需为测试反复退出账户或提交注册信息。

PCC 与 Private Relay 分开维护。Apple 官方把 `apple-relay.cloudflare.com`、`apple-relay.fastly-edge.com`、`cp4.cloudflare.com` 列为 PCC，把 `apple-relay.apple.com` 列为 Apple Intelligence 扩展；`mask.icloud.com`、`mask-h2.icloud.com`、`mask-api.icloud.com` 属于 Private Relay。[Apple 网络端点表](https://support.apple.com/en-us/101555)

Apple 的企业网络表用于核对部分用途，不是消费者全部流量清单。国家间可能共用主机、改用不同 URL 路径，域名规则不能据此完整区分地区；[APNs 另按长连接实测](network-testing.md#apns-推送)。

## AI：按产品与实际地区入口选择

| 范围 | 选择与边界 |
|---|---|
| 海外 AI | 统一出口选 1000，分别选路则用成员。Claude 1010、OpenAI 1020、Gemini 1030 等保持各自登录、API、文件与对话出口稳定 |
| 其他海外 AI 产品 | Amp、AnythingLLM、Fireworks、OpenCode、Kilo、Cline、Replicate、Runway、Replit 等也在 1000 内，成员以清单为准。官网、API 与自建地址按产品边界处理，不把整个云平台划给 AI |
| xAI | 1040 包含 Grok、xAI API 及相关产品的共用账号主机。Grokipedia 内容 1050、Cursor 编辑器 1100、X 社交 3350 分别处理；单独选择相关产品时，也需让共用认证出口可用 |
| 国产 AI 国际版 | 1800 或其产品成员，包含模型平台及 Qoder、YouMind、Lovart 的国际产品入口；小米 MiMo 的新加坡、欧洲计划只收目录明确列出的 API |
| 国产 AI 国内版与共用入口 | 6000 或其产品成员，包括 6010–6150、6160–6170；DeepSeek、文心、讯飞、魔搭、小米 MiMo 等各自说明范围，不把全部国产 AI 统称一个产品 |
| JetBrains AI | 海外后端 1230、中国区 API 6260；IDE 与插件等在 3100，6260 不并入国产厂商合集 |
| 海外 AI 中国区合集 | 6250，目前只有 JetBrains AI 中国区 API；与 6260 二选一，后续有可靠地区来源再加入其他产品 |
| Apple 系统 AI | 细分方式选 2020，日常由 Apple 海外功能 2010 包含；不在海外 AI 合集 1000 内 |

认证和模型请求尽量用同一稳定出口，长回复或上传过程中避免切节点。产品规则不要求禁用 QUIC、IPv6 或 HTTP/3，异常时根据真实连接比较协议与地址族。

OpenAI 1020 的语音地址来自[官方公开 JSON](https://openai.com/chatgpt-voice.json)，使用 `no-resolve`，与专用域名选择同一出口。节点仍须支持实际使用的 UDP 或 TCP 路径。[OpenAI 网络要求](https://help.openai.com/en/articles/9247338-network-recommendations-for-chatgpt-errors-on-web-and-apps)

Claude 网页、App、Desktop、Code 和 Anthropic API 使用 1010 的产品范围，工具调用访问的第三方网站仍按目标网站处理。通用 GitHub、包源、Google Storage 与云平台网关不整域归入 AI。[Claude Code 网络要求](https://code.claude.com/docs/en/network-config)

Claude 的入口地址与服务器出站地址要分清。[官方地址说明](https://platform.claude.com/docs/en/api/ip-addresses)把 `160.79.104.0/23`、`153.61.224.0/22`、`2607:6bc0::/48` 列为入站地址，1010 自动读取这一章节。`160.79.104.0/21`、`153.61.208.0/20` 是 Anthropic 向外部 MCP 等服务发起请求时使用的源地址，不据此扩大客户端分流范围；Google 的整个 `34.8.0.0/16` 也不归 Claude。

1010 还包含已核实的开发者博客 `claude.dev`、Artifact 域 `claude.site`、新对话快捷入口 `claude.new` 和课程入口 `claudeacademy.com`。名称相似的域名不自动认作生产服务；内部环境与业务用途未确认的域名不因社区清单收录就加入。

| 第三方依赖 | 用途与处理 |
|---|---|
| Google 登录、WorkOS、Auth0 | 共用登录服务按各自产品处理；Claude 专用的 `anthropic.auth0.com` 已在 1010，整个 Auth0 不归 Claude |
| Stripe、Link | 支付按 3520、3530 或 3500 合集处理；商户、银行的验证页面仍按自身目标匹配 |
| Intercom 4360 | 客服会话、素材和实时通信是共享服务，归海外办公与客服，也进入 4300 合集 |
| hcaptcha 3180、Cloudflare 验证 | 人机验证平台可被多个产品使用；验证失败时检查实际主机与出口，不把整家 Cloudflare 加入 Claude |
| Persona 3190、Yoti 3200 | Claude 官方说明了[身份验证](https://support.claude.com/en/articles/14328960-identity-verification-on-claude)和[年龄验证](https://support.claude.com/en/articles/15171100-age-assurance-on-claude)的相关用途；并非每次登录或每位用户都会触发 |
| Datadog 3140、Sentry 3150、Statsig 3160、Fathom 3170、Sift 3210 | 分别涉及运行监控、错误报告、功能配置与实验、网站统计、反欺诈；用途不同，不能统称身份验证，也不能整体划给 Claude。Code 文档中的两项 Datadog 上报为可选。这些共享开发服务也进入 3000 合集 |

Firebase 消息 4585 归 Google 生态，也进入 4500 合集；它包括 SDK 发布的令牌注册主机和 FCM API，不把全部 Google APIs、设备配置地址或共享 IP 当成消息服务

分流按当前请求的目标匹配，不能只凭域名知道“这次 Stripe 付款来自哪个商户”。需要一次登录或付款全程使用同一出口时，应在操作设备上检查共享登录、支付及银行验证的实际路径，并在建立新连接前选择一致的出口。漏过产品规则的请求仍会继续匹配后续域名和 IP 规则，再到 `FINAL`；是否直连取决于完整配置。出口一致性本身也不是账号安全保证。

iPhone 的 Loon 不控制另一台 Mac 或 PC；Desktop、Code 和 API 客户端要在实际运行设备上单独验证。

## 海外与国内产品分别管理

下列产品都有独立订阅，多份规则可绑定同一个出口。[厂商目录](services.md)把同一家公司的产品与共用范围放在一起查找；无法可靠区分的连接共用一张表，不另建空组。已知国内镜像和国内版另列，不按厂商注册地决定出口。

| 大类 | 已分出的产品与用途 |
|---|---|
| 海外开发 | GitHub、GitLab、Bitbucket、npm、Maven Central、PyPI、Docker Hub、Rust/Cargo、Go、JetBrains IDE、Node.js、ACP、WorkOS；共用认证需要固定出口时，按所用产品选择同一稳定节点 |
| 海外通讯与社交 | Telegram、Discord、Signal、LINE、X、微信国际门户、Slack、Reddit、Instagram、WhatsApp、Threads、Pinterest、Bluesky、Lark、Zoom、LinkedIn；Meta 共用服务另列 |
| 海外支付 | PayPal、Stripe、Link、Braintree、Venmo、Xoom、Wise；商户网站、银行和本地读卡器各自处理 |
| 加密资产 | Binance、OKX、Gemini Exchange、Kraken、Bybit、KuCoin、Trust Wallet；Gemini 交易所与 Google AI 分开，第三方 DApp 和公链 RPC 不整包归钱包 |
| 海外媒体 | HBO、YouTube、Netflix、Disney+、Prime Video、Spotify、Twitch、TikTok、哔哩哔哩国际、巴哈姆特、BBC、爱奇艺国际版、SoundCloud、Vimeo、Hulu；统一出口用 3800 替代成员，Apple TV 仍在 Apple 海外功能里 |
| 海外游戏 | Steam、Epic、PlayStation、Nintendo、HoYoverse、EA、Ubisoft、Battle.net、网易国际游戏共用 SDK；统一出口用 4100 替代成员，不代表所有对局 IP 都已覆盖 |
| 海外协作 | Notion、Figma、Trello、Atlassian Cloud、Proton；Bitbucket 与 Trello 先匹配，共用 Jira、Confluence 和平台资源随后处理 |
| 国内开发 | Gitee、CODING、GitCode、npmmirror、TUNA 镜像；不会替 npm、pip 或 Maven 修改软件源 |
| 国内通讯与支付 | 微信共用服务、钉钉公共产品、飞书、豆瓣、微博、小红书、知乎、支付宝、银联；无法按同一共享主机区分用户所在国家或全部支付用途 |
| 国内媒体与游戏 | 哔哩哔哩、抖音、爱奇艺、优酷、QQ 音乐、酷狗、快手、网易云音乐、斗鱼、虎牙，Steam 国内下载、米哈游国服、WeGame；统一出口分别用 6900 和 7200 替代成员 |
| 国内购物、生活与办公 | 淘宝与闲鱼、京东、12306、美团、滴滴、有道、阿里云盘、WPS；小红书、知乎归通讯与社交，新浪共用图片归厂商共用范围 |

产品专用附件、登录和 API 尽量跟随产品。共享云、用户自定义域、第三方插件和自建实例按自身目标匹配，不收进公共产品表。常用规则的来源与边界可在清单直接查看。

## 跨国厂商的中国区与云平台

4900 合并高通、NVIDIA、Intel、Samsung、Cloudflare、Adobe、Amazon 的已列中国区或国内可用入口，以及 Azure 中国云控制端点，建议交给国内策略。也可以分别使用 4910–4980。`www.qualcomm.cn` 由 4910 识别，国际官网仍按海外范围处理；不是把整个高通公司判作国内。

4980 从 Azure 官方中国云定义读取登录、管理、门户、目录和 Graph 的精确主机，不接管租户存储或整个中国云后缀。全球 Microsoft 登录仍由 4710 处理；两类也分别保留在各自合集里。[Azure 中国云端点](https://docs.azure.cn/zh-cn/storage/common/storage-explorer-network) · [Microsoft Graph 国家云](https://learn.microsoft.com/en-us/graph/deployments)

地区来源的 `@cn` 表示来源标注有大陆接入，不证明服务器、账户或全部服务只在中国。地区表不根据域名含 `cn` 自动扩展；同厂商的国际产品、共用主机和第三方依赖分别处理。

Cloudflare 公共 DNS 在 0160，标准解析器的四个 IPv4／IPv6 地址从官方表读取，全部带 `no-resolve`。8090 是 Cloudflare 其余平台范围；它不代表“所有使用 Cloudflare CDN 的网站”。0160 识别连接，不会替设备更换解析器，也不保证 DNS 或 WebRTC 已防泄漏。

全球厂商与云平台的共用范围在 8000，具体产品和扩展广告先匹配；国内厂商共用范围在 8400，位于海外补充之后。两类均保留厂商细分。国内入口 4900 在海外具体服务、Google 和 Microsoft 之后，同时早于厂商通用父域，保证高通中国等明确入口不会被共用表改走代理

## Google、Microsoft 与共享平台

两个生态位于海外具体产品之后、国内产品之前。原因是同一平台会为其他产品托管服务：Discord 专用上传主机先归 Discord，普通 Google 存储才由 Google 处理；不把整个 Azure 租户平台交给 Microsoft。

| 生态 | 细分用途 | 建议 |
|---|---|---|
| Google | 学术、账户、Gmail、Meet、Drive/Docs、Play、Play 游戏、软件下载、共用服务 | 大陆不可用的服务走代理。统一出口用 4500；会议和大文件需要不同路径时改选成员。Gemini、YouTube 独立于 4500 |
| Microsoft | VS Code、Power BI、账户、Outlook、Teams、OneDrive/SharePoint、更新检查、更新与商店下载、商店、Office 下载、Xbox、共用平台 | 工作与会议用已测通的线路；大包可单独试直连。统一出口用 4700；GitHub 和两个 Copilot 各自独立 |

Google 地区登录从官方模板和域名表生成；Gmail、Play 与 Play 游戏读取仍公开的 API 版本。Microsoft 登录与控制入口读取官方定义，Azure 租户后缀及会整体覆盖租户的父域不因此认领。Meet、Teams 的官方媒体网段带 `no-resolve`，共享通信地址不能再按发起 App 细分。[Drive 网络要求](https://knowledge.workspace.google.com/admin/drive/drive-and-sites-firewall-and-proxy-settings) · [Microsoft 365 端点](https://learn.microsoft.com/en-us/microsoft-365/enterprise/urls-and-ip-address-ranges)

## 补充范围也可合并，或分别选路

| 规则 | 做什么 | 怎么用 |
|---|---|---|
| 8200 | 海外补充合集 | 统一出口时选用，替代 8210、8220 |
| 8210、8220 | 其他海外影音、网站与受限站点 | 需要影音和普通网站不同出口时分别订阅 |
| 8600 | 国内补充合集 | 统一国内出口时选用，替代域名、网段与 GeoIP 成员 |
| 8610、8620、8630 | 国内补充成员 | 需要分别控制时替代合集；只按域名判断可仅选 8610 |

海外补充不自动搬到所有国内产品前面：具体产品已有明确用途，先按产品处理；海外补充随后补缺，再交国内宽范围判断。上游来自海外大表也可能有国内或共享域，不能靠移动整份表保证准确。

国内大表与已采用的海外或 GFW 来源相交时，不能因为“国内表也收了”就删掉代理规则。8220 保留这些来源的范围，8610 让出被完整接住的重合条目；国产 AI 国内版等具体产品仍先匹配。爱奇艺国际专用子域先由 3890 处理，6920 的国内父域留在后面，不能只根据 iqiyi.com 判断两版出口。

本地、插件和订阅共同决定真实结果。域名阶段与 IP 阶段的匹配、DNS 解析及系统 VPN 路由还须分别检查，见[连接与防泄漏测试](network-testing.md)。

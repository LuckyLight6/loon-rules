# 规则订阅清单

按需要选规则，放进 Loon 的订阅列表。**常规**按编号从小到大排；选合集就不用再订阅它的成员。**备选**用来替换同用途的规则，不是额外补充。编号只决定同一来源、同一匹配阶段内的顺序。

打开规则后点 **Raw** 复制订阅地址。来源和更新时间在文件开头；[status.json](status.json)记录最近检查及待复核的变化。

## 010–019 网络接入与局域网

| 编号 · 规则 | 用途 | 来源方式 | 范围 |
|---|---|---|---|
| [011-local-links-and-addresses](rules/011-local-links-and-addresses.lsr) | 局域网名称、路由器、反查与保留地址 | 常规 · 按用途整理 | 管理入口用精确域名；保留私网的 DNS 匹配，不把公网翻译地址或协议任播整段当局域网。文档示例等只匹配裸 IP。 |
| [012-network-sign-in-and-probes](rules/012-network-sign-in-and-probes.lsr) | 公共 Wi-Fi 登录、系统网络检查与必需安全连接 | 常规 · 按用途整理 | 合并 captive 与 bootstrap；精确放行会被拦截源误判的 Apple 安全浏览令牌。不会直连整个系统服务或广告域。 |
| [013-tailscale-control-and-tailnet](rules/013-tailscale-control-and-tailnet.lsr) | Tailscale 控制面与 Tailnet 域名 | 常规 · 按用途整理 | 只匹配 Tailscale 专用域和 MagicDNS 后缀。CGNAT 和 ULA 已在 011，不将整个 CGNAT 当 Tailscale。 |

## 020–029 广告与隐私

| 编号 · 规则 | 用途 | 来源方式 | 范围 |
|---|---|---|---|
| [021-apple-and-ai-privacy-exceptions](rules/021-apple-and-ai-privacy-exceptions.lsr) | Apple 广告与 OpenAI 广告像素的已核实拒绝项 | 可选 · 按用途整理 | 单独可选，不属于 Apple 或 AI 合集。只拦明确广告入口，不能以大后缀替代。 |
| [023-general-ad-and-tracking](rules/023-general-ad-and-tracking.lsr) | Repcz 广告与追踪拦截 | 常规 · 审核后发布 | 窄于大合集；与其他广告表作为同类选择。 |
| [025-extended-ad-and-tracking](rules/025-extended-ad-and-tracking.lsr) | 覆盖更多广告与追踪域的备选表 | 备选 · 审核后发布 | 较广；启用前注意原有应用例外。 |
| [026-privacy-public-stun-endpoints](rules/026-privacy-public-stun-endpoints.lsr) | 已公开的 STUN 主机，供选择性阻断 | 可选 · 按用途整理 | 仅两个精确主机，不拦 webrtc.org 或所有 stun.*。启用可能影响语音和会议；不能代替 WebRTC 或 DNS 出口检查。 |

## 030–059 Apple 生态

| 编号 · 规则 | 用途 | 来源方式 | 范围 |
|---|---|---|---|
| [030-apple-all](rules/030-apple-all.lsr) | Apple 已审业务合集：账户、系统、海外媒体、智能与 iCloud | 替换成员 · 合集 | 替换所列成员。涵盖海外服务，不能整表设直连；混合出口用细分。证书验证仍保持独立。 |
| [031-apple-account-authentication](rules/031-apple-account-authentication.lsr) | 登录、OAuth 相关服务、iCloud 初始化与账户恢复 | 常规 · 按用途整理 | 优先于商店、iCloud 与共享 Apple CDN。 |
| [032-apple-association-services](rules/032-apple-association-services.lsr) | Apple 通用链接的域名验证 | 常规 · 按用途整理 | 只匹配 Associated Domains 端点，不放开整个 Apple CDN。 |
| [033-apple-app-and-device-verification](rules/033-apple-app-and-device-verification.lsr) | 应用验证、App Attest、macOS 公证与设备身份验证 | 常规 · 按用途整理 | 保留系统服务直连；共享 apple-cloudkit.com 不从此组抢走。 |
| [034-apple-wallet-payments](rules/034-apple-wallet-payments.lsr) | Wallet 与 Apple Pay 已知支付入口 | 常规 · 按用途整理 | 只收可追溯的精确主机。支付仍依赖账户、设备校验及商户；不吞 ca、Apple 全域或其他支付公司。 |
| [035-apple-beta-distribution](rules/035-apple-beta-distribution.lsr) | TestFlight 测试版安装和分发 | 常规 · 按用途整理 | 剔除整个 TestFlight 关键词；商店生产环境和系统 OTA 分开。 |
| [036-apple-store-transactions](rules/036-apple-store-transactions.lsr) | App Store API、购买与安装指令、Apple Books 商店 | 常规 · 按用途整理 | 账户认证、App 下载和 TestFlight 分开。含第三方市场安装入口和 Apple Books 门户，不包揽整个 itunes.apple.com。 |
| [037-apple-app-package-downloads](rules/037-apple-app-package-downloads.lsr) | App Store 安装包下载 | 常规 · 按用途整理 | 只匹配已知安装包入口和别名，不把 mzstatic 整段算作安装包。TestFlight、购买、设备验证和系统更新各有专表。 |
| [038-apple-push-connection](rules/038-apple-push-connection.lsr) | APNs 系统推送的域名与公开客户端网段 | 常规 · 按用途整理 | 独立选择长连接出口。默认保留实测可用路径；直连丢通知时可只切此组对照。不能按 App 国别拆系统推送。 |
| [039-apple-location-services](rules/039-apple-location-services.lsr) | 定位与 Find My 已识别的专用端点 | 常规 · 按用途整理 | 含已核对的 Find My 移动端入口和数字分片。共用 iCloud 网页、推送和账户保留各自策略。 |
| [040-apple-private-relay-connections](rules/040-apple-private-relay-connections.lsr) | Private Relay 的 mask 域和 Apple DNS 中继别名 | 常规 · 审核后发布 | 放在 iCloud 同步前；不包含整个 iCloud 或 Apple DNS 后缀。 |
| [041-apple-mainland-delivery-aliases](rules/041-apple-mainland-delivery-aliases.lsr) | 已核对的 Apple 大陆就近分发别名 | 常规 · 按用途整理 | 只收明确标注 cn-lb 的精确别名。是否从本地边缘节点命中仍以 DNS 和请求日志为准；不能把备案域或公共 CNAME 当大陆独占 CDN。 |
| [042-apple-cloud-sync](rules/042-apple-cloud-sync.lsr) | iCloud 通用服务、CloudKit、同步、邮件及 iWork | 常规 · 按用途整理 | 认证、查找、Private Relay、确定的内容域及大陆服务分别匹配；通用域不能用来判断账户或存储国家。 |
| [043-apple-music-and-radio](rules/043-apple-music-and-radio.lsr) | Apple Music、广播及共用 API 与应用门户 | 常规 · 按用途整理 | 保留 Music 门户、API 和不能据域名进一步切开的音乐视频流量。明确音频传输在 056。 |
| [044-apple-video-and-fitness](rules/044-apple-video-and-fitness.lsr) | Apple TV／Fitness+ 的门户、播放控制与共用主机 | 常规 · 按用途整理 | 中国大陆未提供对应订阅；入口默认选服务可用地区的代理。已识别 HLS 交给独立视频组，同一会话用一致出口。 |
| [045-apple-news-and-sports](rules/045-apple-news-and-sports.lsr) | Apple News／News+、内容入口与 Apple Sports | 常规 · 按用途整理 | 中国大陆未提供；默认选对应服务可用地区的代理，不纳入国内直连例外。 |
| [046-apple-intelligence-relays](rules/046-apple-intelligence-relays.lsr) | Apple Intelligence：PCC 和系统 ChatGPT 扩展 | 常规 · 按用途整理 | 中国大陆网络建议用独立代理。能否使用还要看设备、账户、语言和功能资格。普通 Siri、ChatGPT App 和模型下载不归本组。 |
| [047-apple-siri-and-search](rules/047-apple-siri-and-search.lsr) | Siri 与 Spotlight 的专用域名 | 常规 · 审核后发布 | Siri、听写和系统搜索可共用主机；未能按主机区分普通 Siri 与 Siri AI 时，保留独立策略供真机对照，不把所有 Siri 当 PCC。 |
| [048-apple-update-control](rules/048-apple-update-control.lsr) | 系统更新目录、检查、登记和控制端点 | 常规 · 按用途整理 | 含 OTA/Rosetta 检查、系统恢复服务和 Beta 登记；已确认的二进制内容下载另在 055，不按整个 cdn-apple.com 或整段 Apple IP 分类。 |
| [049-apple-certificate-validation](rules/049-apple-certificate-validation.lsr) | Apple 设备的证书状态和撤销检查 | 常规 · 按用途整理 | 只用官方给出的证书端点及已知 Apple 主机别名，不扩到整个 DigiCert。 |
| [050-apple-developer-downloads](rules/050-apple-developer-downloads.lsr) | Xcode、Swift Playgrounds 和开发者组件的实际下载 | 常规 · 按用途整理 | 开发下载与 App Store、OTA 和共享的 App 公证端点分开。 |
| [051-apple-system-connectivity](rules/051-apple-system-connectivity.lsr) | Apple 激活、设备管理、诊断与设备素材 | 常规 · 按用途整理 | 激活、设备管理、诊断、校时和设备素材走本组。不收整个 Apple 网段或共用 CDN，也不替代账号、推送与钱包组。 |
| [052-apple-shared-store-assets](rules/052-apple-shared-store-assets.lsr) | Apple 商店与媒体共用的静态内容 | 常规 · 按用途整理 | mzstatic 也承载图标、书籍和音乐内容，不能当成纯安装包。s.mzstatic.com 应先命中 033；静态图片别名不保证专供大陆。 |
| [053-apple-icloud-content-domains](rules/053-apple-icloud-content-domains.lsr) | iCloud 通用内容域 | 常规 · 按用途整理 | 仅匹配 icloud-content.com 内容域，能直连再直连。大陆专域另管；部分上传、备份仍使用共用服务。 |
| [054-apple-messaging-identity](rules/054-apple-messaging-identity.lsr) | Apple 消息及 FaceTime 共用设备身份服务 | 常规 · 按用途整理 | 将社区确认的 IDS 名称与位置和推送分开。仅覆盖身份服务，不按它声称覆盖消息媒体或 FaceTime 中继 UDP。 |
| [055-apple-update-downloads](rules/055-apple-update-downloads.lsr) | 系统更新包与恢复内容下载 | 常规 · 按用途整理 | 系统恢复、更新包和运营商设置包的下载主机及其已核对的别名。目录、激活和证书走各自的组。 |
| [056-apple-music-audio-delivery](rules/056-apple-music-audio-delivery.lsr) | Apple Music 已识别音频交付主机 | 常规 · 按用途整理 | 社区资料中的明确音频传输主机，不包含 Music API、账户和整个 itunes.apple.com。缓存是否在大陆不能由域名推定。 |
| [057-apple-tv-video-delivery](rules/057-apple-tv-video-delivery.lsr) | Apple TV 已识别的 HLS 视频交付 | 常规 · 按用途整理 | 匹配已识别 HLS 主机。大陆网络默认与 TV 播放控制同一代理；可单独统计流量，不把其他 Apple CDN 一并代理。 |
| [058-apple-icloud-mainland](rules/058-apple-icloud-mainland.lsr) | 中国大陆 iCloud 服务和内容专用域 | 常规 · 按用途整理 | 只收官方标注的大陆服务域及 Apple DNS 委派的大陆内容域；不认为 Apple 账户、CloudKit 或共用域都在大陆。 |
| [059-apple-schoolwork-handouts](rules/059-apple-schoolwork-handouts.lsr) | Apple Schoolwork 讲义与资料交付 | 常规 · 按用途整理 | 官方明确归属 Schoolwork Handout 的主机；班级名册和设备验证另走共享服务。 |

**030 合集替换：** 031、032、033、034、035、036、037、038、039、040、041、042、043、044、045、046、047、048、050、051、052、053、054、055、056、057、058、059。

## 060–089 AI 服务

| 编号 · 规则 | 用途 | 来源方式 | 范围 |
|---|---|---|---|
| [060-ai-overseas-all](rules/060-ai-overseas-all.lsr) | Claude、ChatGPT、Gemini、Grok 和其他海外 AI 的汇总规则。 | 替换成员 · 合集 | 与细分二选一；Apple Intelligence 保持独立，国产国内版和国际版不变。不合并共享云。 |
| [061-claude-connections](rules/061-claude-connections.lsr) | Claude 登录、API、MCP、更新、附件和 Artifact | 常规 · 审核后发布 | Claude 自有入口走同一个策略。外部 MCP、Bedrock、Vertex、Microsoft Foundry 和共享支付不归本组；IP 只匹配已核对的裸地址。 |
| [062-chatgpt-connections](rules/062-chatgpt-connections.lsr) | ChatGPT、Codex、OpenAI API 和专用语音信令 | 常规 · 按用途整理 | 包括登录、对话、文件的专用入口，不把 LiveKit、Stripe、Cloudflare、Azure 或 Google 的共享域一并代理。 |
| [063-gemini-connections](rules/063-gemini-connections.lsr) | Gemini、AI Studio、NotebookLM、Google AI API 和专用 WebChannel | 常规 · 按用途整理 | 通用 Google 登录、下载、存储与 API 不在此组。 |
| [064-grok-connections](rules/064-grok-connections.lsr) | Grok 对话与 xAI 模型 API | 常规 · 审核后发布 | 只收 Grok 和 xAI 确认入口；Grokipedia 独立，不匹配来源不明的同名机器人或整个 X。 |
| [065-cursor-editor-and-api](rules/065-cursor-editor-and-api.lsr) | Cursor 客户端及专用接口 | 常规 · 审核后发布 | 不把通用 GitHub 和云服务纳入。 |
| [066-github-copilot-connections](rules/066-github-copilot-connections.lsr) | Copilot API、补全、对话及已证实的附件服务 | 常规 · 按用途整理 | 只匹配 Copilot 专用主机。共享登录和 GitHub API 仍由 121 处理。 |
| [067-windsurf-editor-and-api](rules/067-windsurf-editor-and-api.lsr) | Windsurf 和 Codeium 专用接口 | 常规 · 审核后发布 | 不把公共托管平台当开发助手。 |
| [068-devin-cloud-coding](rules/068-devin-cloud-coding.lsr) | Devin 自有云编程入口 | 常规 · 审核后发布 | 不覆盖它所访问的外部仓库。 |
| [069-perplexity-search-and-api](rules/069-perplexity-search-and-api.lsr) | Perplexity 搜索、API 和专用内容入口 | 常规 · 审核后发布 | 按租户主机区分，不代理整个第三方文件云。 |
| [070-poe-chat-and-api](rules/070-poe-chat-and-api.lsr) | Poe 聊天与平台域名 | 常规 · 审核后发布 | 不纳入底层模型提供商的共享接口。 |
| [071-openrouter-gateway](rules/071-openrouter-gateway.lsr) | OpenRouter 的模型网关入口 | 常规 · 审核后发布 | 同一个网关不根据模型名称切流。 |
| [072-mistral-model-services](rules/072-mistral-model-services.lsr) | Mistral 平台专用域名 | 常规 · 审核后发布 | 第三方推理平台按自己的入口归类。 |
| [073-groq-inference](rules/073-groq-inference.lsr) | Groq 推理服务入口 | 常规 · 审核后发布 | 与 Grok/xAI 无关。 |
| [074-cohere-model-services](rules/074-cohere-model-services.lsr) | Cohere 的推理及平台域名 | 常规 · 审核后发布 | 不因同一模型由其他云托管就把云整段纳入。 |
| [075-hugging-face-model-hub](rules/075-hugging-face-model-hub.lsr) | Hugging Face 模型库与专用 CDN | 常规 · 审核后发布 | 共享存储不整段代理。 |
| [076-midjourney-image-tools](rules/076-midjourney-image-tools.lsr) | Midjourney 图像服务入口 | 常规 · 审核后发布 | 不把 Discord 基础设施都交给它。 |
| [077-muse-agent](rules/077-muse-agent.lsr) | Muse 独立个人助手与其专用入口 | 常规 · 按用途整理 | 只匹配 muse.ai。Meta AI 本站是 079；不把 Meta 社交 App 或 Muse 连接到的第三方网站归进来。 |
| [078-elevenlabs-voice-and-api](rules/078-elevenlabs-voice-and-api.lsr) | ElevenLabs 语音生成、WebSocket、文件与 MCP | 常规 · 按用途整理 | 只收厂商专用根域，包含 API 与 ElevenLabs CDN，不扩到第三方语音或存储基础设施。 |
| [079-meta-ai-assistant](rules/079-meta-ai-assistant.lsr) | Meta AI 助手的独立网站 | 常规 · 按用途整理 | 只匹配 meta.ai；不扩大至 Muse、Facebook、Instagram、WhatsApp 或其共享基础设施。 |
| [080-grokipedia-encyclopedia](rules/080-grokipedia-encyclopedia.lsr) | Grokipedia AI 百科站点 | 常规 · 按用途整理 | 独立于 Grok 模型与 X 社交，只匹配百科站点。 |
| [081-microsoft-copilot-connections](rules/081-microsoft-copilot-connections.lsr) | Microsoft Copilot 个人版与工作版独立入口 | 常规 · 按用途整理 | 只收自营 Copilot 门户；不吸收 Microsoft 通用登录、Outlook、Graph、Bing 或 GitHub Copilot。 |
| [084-ai-cn](rules/084-ai-cn.lsr) | 国产 AI 国内入口：DeepSeek、百炼、火山方舟与扣子、Kimi、智谱、MiniMax、千帆、混元、讯飞、硅基流动等 | 常规 · 按用途整理 | 按官方服务端点区分，DeepSeek 官网和 API 未见独立国际域，保留原国内策略；不含整个厂商云。 |
| [085-ai-cn-international](rules/085-ai-cn-international.lsr) | 国产 AI 国际入口：Qwen、Kimi、智谱、MiniMax、硅基流动、字节系海外版与区域 MaaS | 常规 · 按用途整理 | 只接已列出的境外和港区工作区；不捕获任意 maas.aliyuncs.com，也不按模型名判断区域。 |

**060 合集替换：** 061、062、063、064、065、066、067、068、069、070、071、072、073、074、075、076、077、078、079、080、081。

**相关专项（沿用同一份规则）：**
- [046-apple-intelligence-relays](rules/046-apple-intelligence-relays.lsr)：Apple 自己的系统 AI；PCC 和 Apple 的 ChatGPT 扩展用这一份，和通用海外 AI 保持独立。

## 090–099 通讯与社交

| 编号 · 规则 | 用途 | 来源方式 | 范围 |
|---|---|---|---|
| [091-telegram-messaging](rules/091-telegram-messaging.lsr) | Telegram 登录、消息、文件与直连 IP | 常规 · 按用途整理 | 核心域名 + 官方 CIDR。网段仅处理裸 IP；未收第三方 ASN、关键词和通用 CDN。 |
| [092-discord-messaging-and-voice](rules/092-discord-messaging-and-voice.lsr) | Discord 消息、语音、活动和附件 | 常规 · 按用途整理 | 仅 Discord 专用域及精确附件存储主机；不给整个 Google Storage 或含 discord 的域名选路。 |
| [093-x-social-and-media](rules/093-x-social-and-media.lsr) | X / Twitter 社交与图像视频 | 常规 · 按用途整理 | Grok 专用的 grok.x.com 由 064 在前截取。只接产品和短链，不使用 twitter 关键词或广泛网段。 |
| [094-wechat-global-portal](rules/094-wechat-global-portal.lsr) | WeChat 国际门户与支付 | 常规 · 按用途整理 | 只分明确的国际入口；微信和 WeChat 共同使用的 qq.com 下精确子域由 095 负责。 |
| [095-wechat-shared-and-mainland](rules/095-wechat-shared-and-mainland.lsr) | 微信国内及两版共用登录、消息与支付 | 常规 · 按用途整理 | 限定微信专用域及明确 qq.com、腾讯云主机，不将腾讯 ASN 或整个 QQ 判作微信。 |

## 100–115 Microsoft 生态

| 编号 · 规则 | 用途 | 来源方式 | 范围 |
|---|---|---|---|
| [100-microsoft-all](rules/100-microsoft-all.lsr) | Microsoft 账户、办公、会议、网盘、Xbox 与更新合集 | 替换成员 · 合集 | 替换本章成员；Microsoft Copilot、GitHub 和 GitHub Copilot 仍独立。不把多租户 Azure 或 Akamai 整段归入。 |
| [103-microsoft-account-authentication](rules/103-microsoft-account-authentication.lsr) | Microsoft 个人账户与 Entra 登录 | 常规 · 按用途整理 | 只收账号管理、共享登录与 Entra 身份主机；不把整个 microsoftonline.com 或 Microsoft Graph 当认证。 |
| [104-microsoft-outlook-mail](rules/104-microsoft-outlook-mail.lsr) | Outlook 与 Exchange Online 邮箱入口 | 常规 · 按用途整理 | 收个人和工作邮箱、客户端邮件主机；共享 Entra 登录独立，不能覆盖每个租户自己的域名。 |
| [105-microsoft-teams-meetings](rules/105-microsoft-teams-meetings.lsr) | Teams 工作版与个人版会话、会议入口 | 常规 · 按用途整理 | 专用产品域先于 Microsoft 通用规则。会议 UDP 中继不能只靠域名证明命中；不纳入整段 Microsoft IP。 |
| [106-microsoft-windows-update-services](rules/106-microsoft-windows-update-services.lsr) | Windows Update 检查与传递优化协调 | 常规 · 按用途整理 | 更新服务、传递优化控制和内容调度，不把整个 Windows 或 Microsoft 后缀当更新。 |
| [107-microsoft-update-and-store-downloads](rules/107-microsoft-update-and-store-downloads.lsr) | Windows 更新和 Microsoft Store 已知内容下载 | 常规 · 按用途整理 | 仅已知下载和精确 CDN 别名，不扩到整个 delivery.mp.microsoft.com。大文件确认可用后直连。 |
| [108-microsoft-xbox-services](rules/108-microsoft-xbox-services.lsr) | Xbox Live 已知登录与服务端点 | 常规 · 按用途整理 | 明确的 Xbox 令牌与服务、资产主机；不代表全部游戏下载、语音、联机流量均可按域名识别。 |
| [109-microsoft-store-services](rules/109-microsoft-store-services.lsr) | Microsoft Store 商店目录与加载 | 常规 · 按用途整理 | 商店前端和目录请求；系统更新控制、账户、许可和文件下载各自匹配。 |
| [113-microsoft-files-and-sharepoint](rules/113-microsoft-files-and-sharepoint.lsr) | OneDrive 与 SharePoint 文件与同步 | 常规 · 按用途整理 | 仅文件产品的专用后缀，去掉 onedrive/skydrive 关键词；共享登录由账号专项处理。 |
| [114-microsoft-office-downloads](rules/114-microsoft-office-downloads.lsr) | Microsoft Office 安装与更新下载 | 常规 · 按用途整理 | Office 下载主机及其已核对的精确别名；账号、激活与办公 Web 应用不算下载。 |
| [115-microsoft-connectivity](rules/115-microsoft-connectivity.lsr) | Microsoft 通用客户端和共享服务兜底 | 常规 · 审核后发布 | 只收 Microsoft 自有与已归属的共享服务。Graph 等留在这里；Azure 多租户和共享 Akamai 后缀不整段接管。 |

**100 合集替换：** 103、104、105、106、107、108、109、113、114、115。

**相关专项（沿用同一份规则）：**
- [081-microsoft-copilot-connections](rules/081-microsoft-copilot-connections.lsr)：Microsoft Copilot 在 AI 章独立选路。
- [066-github-copilot-connections](rules/066-github-copilot-connections.lsr)：GitHub Copilot 与 Microsoft Copilot 不共用专表。
- [121-github-code-and-packages](rules/121-github-code-and-packages.lsr)：GitHub 代码与软件包不跟 Microsoft 账户或下载一起切。

## 116–129 开发与代码托管

| 编号 · 规则 | 用途 | 来源方式 | 范围 |
|---|---|---|---|
| [121-github-code-and-packages](rules/121-github-code-and-packages.lsr) | GitHub 代码托管、API、Actions 与容器镜像 | 常规 · 按用途整理 | Copilot 原生接口由 066 先匹配；登录与 API 共享主机仍在 GitHub。npm 保持自身路由，不随 GitHub。 |

## 130–149 音乐、视频与直播

| 编号 · 规则 | 用途 | 来源方式 | 范围 |
|---|---|---|---|
| [130-overseas-media-all](rules/130-overseas-media-all.lsr) | 海外视频、音乐、短视频和直播专项的合集 | 替换成员 · 合集 | 与 131–139 二选一。国内流媒体和 181 其他海外媒体的兜底不包含在本组。 |
| [131-youtube-video-and-cdn](rules/131-youtube-video-and-cdn.lsr) | YouTube 视频、音乐、频道与专用 CDN | 常规 · 按用途整理 | 保留 youtubei、googlevideo 和 YouTube 静态域；不收整个 gvt2、Google IP 或 youtube 关键词。 |
| [132-netflix-video-and-delivery](rules/132-netflix-video-and-delivery.lsr) | Netflix 播放、设备 API 和内容分发 | 常规 · 按用途整理 | 保留 Netflix 服务域与 nflx* 中已确认的专用后缀；不接管 AWS 或来源不明的直播 IP。 |
| [133-disney-plus-streaming](rules/133-disney-plus-streaming.lsr) | Disney+ 播放及其专用交付 | 常规 · 按用途整理 | 不将迪士尼乐园、体育、Hulu 或整个共享 bamgrid 网关当 Disney+。可归属的主机按精确匹配。 |
| [134-prime-video-streaming](rules/134-prime-video-streaming.lsr) | Prime Video 视频 API 和内容 | 常规 · 按用途整理 | Amazon 零售、共享 CloudFront 父域和通用图片不纳入。本组只保已识别视频专用域和 CDN 别名。 |
| [135-spotify-audio](rules/135-spotify-audio.lsr) | Spotify 音乐播放和音频文件 | 常规 · 按用途整理 | 去掉任意包含 spotify 的关键词；播放走 spotify.com、scdn.co 等专用后缀。 |
| [136-twitch-live-video](rules/136-twitch-live-video.lsr) | Twitch 直播、聊天室和内容 CDN | 常规 · 按用途整理 | 不导入整个来源 ASN/IP 或关键词。Twitch 专属后缀独立于其他视频服务。 |
| [137-tiktok-international-video](rules/137-tiktok-international-video.lsr) | TikTok 国际短视频与直播 | 常规 · 按用途整理 | 只含 TikTok 专有域；CapCut、抖音、Trae 以及两版共用字节云不划进本组。 |
| [138-bilibili-global-video](rules/138-bilibili-global-video.lsr) | 哔哩哔哩国际版视频 | 常规 · 按用途整理 | 只收明确的国际版根域；共用视频 CDN 和中国站仍按各自规则或通用层。 |
| [139-bahamut-video-and-community](rules/139-bahamut-video-and-community.lsr) | 巴哈姆特动画疯和电玩社区 | 常规 · 审核后发布 | 专表有巴哈姆特域名和精确 CDN 别名，不匹配整个 Akamai/Hinet。 |
| [143-bilibili-mainland-video](rules/143-bilibili-mainland-video.lsr) | 哔哩哔哩中国站视频与图片 | 常规 · 按用途整理 | 保留国内平台及常用内容交付；国际版专域不混入，API/CDN 共用部分不能按国家强行拆分。 |
| [144-douyin-mainland-video](rules/144-douyin-mainland-video.lsr) | 抖音中国版短视频、直播、图片与素材 | 常规 · 按用途整理 | 只取抖音专有域和投放到该产品的 CDN；不纳入 TikTok、今日头条或整个字节基础设施。 |

**130 合集替换：** 131、132、133、134、135、136、137、138、139。

## 150–159 游戏与下载

| 编号 · 规则 | 用途 | 来源方式 | 范围 |
|---|---|---|---|
| [151-steam-mainland-downloads](rules/151-steam-mainland-downloads.lsr) | Steam 中国下载镜像与蒸汽平台内容 | 常规 · 按用途整理 | 国内静态下载在前；游戏账户、商店和社区分到 152。不会放宽整个第三方 CDN。 |
| [152-steam-global-platform](rules/152-steam-global-platform.lsr) | Steam 国际商店、社区、联机和下载 | 常规 · 按用途整理 | 国内下载镜像另有 151；不含第三方游戏分销商和与 Steam 共享的整个网段。 |
| [153-epic-games-services](rules/153-epic-games-services.lsr) | Epic Games 商店、登录及 Unreal 服务 | 常规 · 按用途整理 | 保留游戏厂商的专用域，不接管客服 SaaS 或共享 Amazon/CloudFront 域。 |

## 160–169 Google 生态

| 编号 · 规则 | 用途 | 来源方式 | 范围 |
|---|---|---|---|
| [160-google-all](rules/160-google-all.lsr) | Google 账户、邮箱、办公、Meet、Play、下载和通用服务合集 | 替换成员 · 合集 | 替换本章成员，共用一个出口；更早的 Gemini、YouTube 等专项照常生效。需要节省下载配额时选细分。 |
| [161-google-account-authentication](rules/161-google-account-authentication.lsr) | Google 共享账号、OAuth 授权与换令牌 | 常规 · 按用途整理 | 登录和授权供多个业务共用；不归入 Gemini、Gmail、Meet 或 Drive 专项。未列出的地区和共用依赖走 Google 通用。 |
| [162-google-gmail-mail](rules/162-google-gmail-mail.lsr) | Gmail 网页、邮件协议与专用 API | 常规 · 按用途整理 | 区分 Gmail 网页、API 和 IMAP、SMTP、POP，含 Workspace 邮件中继。登录与其他 Google API 各走各的组。 |
| [163-google-meet-meetings](rules/163-google-meet-meetings.lsr) | Google Meet 会议主机与专用 API | 常规 · 按用途整理 | 仅产品与会议直播主机；共用字体、账号、Google Chat 与未证实的媒体地址不冠以 Meet。 |
| [164-google-drive-and-documents](rules/164-google-drive-and-documents.lsr) | Google Drive、文档和上传下载入口 | 常规 · 审核后发布 | Drive、Docs 和明确文件主机。账号归 Google 账号组，不把整个 googleusercontent.com 或 www.googleapis.com 当网盘。 |
| [165-google-play-services](rules/165-google-play-services.lsr) | Google Play 商店和已知共用 API | 常规 · 按用途整理 | 商店与 Android Play API，有的也供更新使用。软件下载由专表分流，不吞整个 Android 或 Google APIs。 |
| [166-google-software-downloads](rules/166-google-software-downloads.lsr) | Google 软件和更新已知下载主机 | 常规 · 按用途整理 | 明确下载主机，不按整个 gvt1.com 或 googleusercontent.com 分流。能直连时，大文件优先直连。 |
| [169-google-platform-services](rules/169-google-platform-services.lsr) | Google 搜索和共享平台兜底 | 常规 · 按用途整理 | 置于账号、Gmail、Meet、Drive、Play、下载、Gemini 和 YouTube 之后。保留共享域，去掉通用关键词及共享 IP。 |

**160 合集替换：** 161、162、163、164、165、166、169。

**相关专项（沿用同一份规则）：**
- [063-gemini-connections](rules/063-gemini-connections.lsr)：Gemini／AI Studio 在 AI 章；不被 Google 合集替换。
- [131-youtube-video-and-cdn](rules/131-youtube-video-and-cdn.lsr)：YouTube 在媒体章，可独立管流量，也可用媒体合集替换。

## 170–179 支付与国内日常

| 编号 · 规则 | 用途 | 来源方式 | 范围 |
|---|---|---|---|
| [170-paypal-payments](rules/170-paypal-payments.lsr) | PayPal 核心支付、验签和静态资源 | 常规 · 按用途整理 | 区分 PayPal 与旗下 Braintree/Venmo/Xoom 等其他产品，不靠 Paypal 关键词判断。 |
| [171-alipay-mainland-payments](rules/171-alipay-mainland-payments.lsr) | 支付宝国内账户支付和静态资源 | 常规 · 按用途整理 | 不把 AlipayHK、Alipay+、第三方账户或整个阿里云归为国内支付宝。 |
| [172-taobao-and-xianyu-shopping](rules/172-taobao-and-xianyu-shopping.lsr) | 淘宝、天猫、闲鱼购物与图片 | 常规 · 按用途整理 | 只收国内消费平台及专用 CDN。不含 AliExpress、整个阿里云或支付宝。 |
| [173-jingdong-shopping](rules/173-jingdong-shopping.lsr) | 京东购物、账户与商品素材 | 常规 · 按用途整理 | 不将整个京东云网络或金融产品一并转为购物匹配。 |
| [174-xiaohongshu-community](rules/174-xiaohongshu-community.lsr) | 小红书国内内容、社区及专用 CDN | 常规 · 按用途整理 | 只收明确产品域；去掉共用风控，不把海外版或未知通用基础设施归入。 |

## 180–219 通用及地区兜底

| 编号 · 规则 | 用途 | 来源方式 | 范围 |
|---|---|---|---|
| [181-overseas-media-remainder](rules/181-overseas-media-remainder.lsr) | 其他海外媒体的域名兜底 | 常规 · 审核后发布 | 只匹配明确域名和后缀。Hulu、Max、Paramount+、Peacock、DAZN、BBC 等未单列的服务在此处理；不使用关键字、UA 或进程规则。 |
| [182-overseas-media-with-client-matches](rules/182-overseas-media-with-client-matches.lsr) | 其他海外媒体：域名和客户端匹配备选 | 备选 · 审核后发布 | 替代 181 的 Loon 原生来源；选一个媒体兜底，不替换 131–139 的服务边界。 |
| [183-overseas-media-address-compatibility](rules/183-overseas-media-address-compatibility.lsr) | 海外媒体的客户端特征与地址备选表 | 备选 · 审核后发布 | 除域名外还匹配 UA、URL 和 IP。与 181 同用途择一。 |
| [184-overseas-site-fallback](rules/184-overseas-site-fallback.lsr) | 非专项海外站点的域名兜底 | 常规 · 审核后发布 | 只用域名后缀，不用 google、discord、leak 等关键字和宽 IP。更宽兼容源只做备选。 |
| [186-overseas-site-wide-compatibility](rules/186-overseas-site-wide-compatibility.lsr) | 海外站点覆盖较宽的兼容来源 | 备选 · 审核后发布 | 只在确有覆盖需要时替换 184；含关键字和 IP 规则，有误匹配风险。 |
| [187-overseas-address-and-client-matching](rules/187-overseas-address-and-client-matching.lsr) | 旧国际 IP、关键词和客户端匹配 | 备选 · 审核后发布 | 海外通用代理兜底备选，替换 184，不和其他同用途来源同时开启。 |
| [188-restricted-sites-and-addresses](rules/188-restricted-sites-and-addresses.lsr) | 受限站点及地址的备选代理规则 | 备选 · 审核后发布 | 作为更窄的通用代理名单替代 184；选一个来源，不同名叠加。 |
| [190-direct-domain-exceptions](rules/190-direct-domain-exceptions.lsr) | 通用直连的明确域名例外 | 备选 · 审核后发布 | 不默认启用。含跨业务的直连白名单，选用前检查是否抢占专项或与自己的出口冲突。 |
| [191-direct-domain-exceptions-extended](rules/191-direct-domain-exceptions-extended.lsr) | 更宽的直连域名备选 | 备选 · 审核后发布 | 不默认打开。这份表是跨业务直连备选；使用前确认不会抢先匹配 Apple、AI 等专项。 |
| [193-apple-mainland-service-alternative](rules/193-apple-mainland-service-alternative.lsr) | 大陆 Apple 服务的兼容备选（不是纯 CDN） | 备选 · 审核后发布 | 跨认证、缓存、下载等用途的兼容表；不默认启用，也不能当大陆专用主机清单或直连白名单。 |
| [194-mainland-domain-families](rules/194-mainland-domain-families.lsr) | 一般国内域名 | 常规 · 审核后发布 | 国内域名兜底，不含通用关键字、UA、IP 或路由器管理名；国内地址与 GeoIP 单独处理。 |
| [196-mainland-service-domains](rules/196-mainland-service-domains.lsr) | xkww 国内域名备选 | 备选 · 审核后发布 | 替换 194，不叠加。只保留国内公网服务；路由器管理名由 011 处理。 |
| [197-mainland-extended-coverage](rules/197-mainland-extended-coverage.lsr) | 可选的大范围国内域名及地址合集 | 备选 · 审核后发布 | 范围较宽，替换同类国内兜底时才用，不叠加。 |
| [200-mainland-allocated-networks](rules/200-mainland-allocated-networks.lsr) | 一般国内 IPv4/IPv6 网络 | 常规 · 审核后发布 | 用于未命中名称的地址分类，保留 DNS 解析。 |
| [201-mainland-address-registry](rules/201-mainland-address-registry.lsr) | 大陆备选 IPv4 与 IPv6 地址表 | 备选 · 审核后发布 | 同源两族合并；保留 DNS 后再按地址判断的行为。替换 200，并非与它重复叠加。 |
| [202-mainland-asn-classification](rules/202-mainland-asn-classification.lsr) | 已知目的 IP 的中国 ASN 检查 | 备选 · 审核后发布 | 按已知裸 IP 匹配中国 ASN；不能替代域名或 GeoIP 兜底。 |
| [203-mainland-asn-with-resolution](rules/203-mainland-asn-with-resolution.lsr) | 国内 ASN 备选：域名解析后仍可匹配 | 备选 · 审核后发布 | 区别于 202 的裸 IP ASN，不批量改 no-resolve。两张 ASN 表用其一；若用 GeoIP 按设备数据库实际命中。 |
| [204-mainland-geoip-fallback](rules/204-mainland-geoip-fallback.lsr) | GeoIP 的中国地区兜底 | 常规 · 审核后发布 | 保留 DNS 匹配，不用 no-resolve 改写。 |

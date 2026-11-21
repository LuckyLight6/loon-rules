# Loon 规则订阅清单

## 在 Loon 中怎么排

从上往下读，就是订阅的匹配顺序。只选自己要用的行，保持它们的相对位置即可。标题按章节编号，表中序号对应规则文件，也按匹配顺序递增，各类留有空号。英文名称对应文件名；点名称可看正文、来源和更新时间，在最后一列复制订阅地址。

同一出口可以用合集；要分别选节点，就用它的成员，不要两者都开。Loon 刷新订阅只更新正文，不会自动移动设备上已有的订阅。本地规则和插件也可能先匹配。[怎么查实际命中](network-testing.md)

## 1 网络接入与局域网

| 序号 | 英文名称 | 中文名称 | 用途与选择 | 订阅地址 |
|---:|---|---|---|---|
| 011 | [local-links-and-addresses](../rules/011-local-links-and-addresses.lsr) | 局域网名称、路由器、反查与保留地址 | 路由器和局域网名称优先，反查名称随地址范围生成；私网、VPN 和回环保留名称访问。链路本地、组播、保留及文档用地址只匹配已知目标 IP | [订阅地址](https://raw.githubusercontent.com/LuckyLight6/loon-rules/main/rules/011-local-links-and-addresses.lsr) |
| 012 | [local-no-resolve-alt](../rules/012-local-no-resolve-alt.lsr) | 局域网管理名与已知 IP：不为匹配触发 DNS | **可选。** 替代 011，不同时订阅。保留全部管理名和网段；未知内网名称不能再靠这份表解析到私网后直连 | [订阅地址](https://raw.githubusercontent.com/LuckyLight6/loon-rules/main/rules/012-local-no-resolve-alt.lsr) |
| 013 | [network-sign-in-and-probes](../rules/013-network-sign-in-and-probes.lsr) | 公共 Wi-Fi 登录、系统网络检查与必需安全连接 | 合并 captive 与 bootstrap；精确放行会被拦截源误判的 Apple 安全浏览令牌。不会直连整个系统服务或广告域 | [订阅地址](https://raw.githubusercontent.com/LuckyLight6/loon-rules/main/rules/013-network-sign-in-and-probes.lsr) |
| 014 | [tailscale-control-and-tailnet](../rules/014-tailscale-control-and-tailnet.lsr) | Tailscale 控制面、公开中继与 Tailnet 域名 | 保留专用控制域与 MagicDNS 后缀，并从官方公开 DERP 表读取中继主机。只取主机名，不采用节点 IP；CGNAT 和 ULA 仍由 011 按用途处理 | [订阅地址](https://raw.githubusercontent.com/LuckyLight6/loon-rules/main/rules/014-tailscale-control-and-tailnet.lsr) |
| 015 | [ip-egress-checks](../rules/015-ip-egress-checks.lsr) | 查询当前公网出口：国内检测页、IPv4、IPv6 和双栈 API | 只收用途明确的查询主机，不接管 IP 资料站、DNS、STUN 或多用途网站。设为代理后，用这些主机查地址的 DDNS 客户端也会看到代理出口 | [订阅地址](https://raw.githubusercontent.com/LuckyLight6/loon-rules/main/rules/015-ip-egress-checks.lsr) |

## 2 广告与隐私

| 序号 | 英文名称 | 中文名称 | 用途与选择 | 订阅地址 |
|---:|---|---|---|---|
| 021 | [apple-and-ai-privacy-exceptions](../rules/021-apple-and-ai-privacy-exceptions.lsr) | Apple 广告与 OpenAI 广告像素的已核实拒绝项 | **可选。** 单独可选，不属于 Apple 或 AI 合集。只拦明确广告入口，不能以大后缀替代 | [订阅地址](https://raw.githubusercontent.com/LuckyLight6/loon-rules/main/rules/021-apple-and-ai-privacy-exceptions.lsr) |
| 022 | [general-ad-and-tracking](../rules/022-general-ad-and-tracking.lsr) | Repcz 广告与追踪拦截 | 窄于大合集；与其他广告表作为同类选择 | [订阅地址](https://raw.githubusercontent.com/LuckyLight6/loon-rules/main/rules/022-general-ad-and-tracking.lsr) |
| 023 | [privacy-public-stun-endpoints](../rules/023-privacy-public-stun-endpoints.lsr) | 已公开的 STUN 主机，供选择性阻断 | **可选。** 仅两个精确主机，不拦 webrtc.org 或所有 stun.*。启用可能影响语音和会议；不能代替 WebRTC 或 DNS 出口检查 | [订阅地址](https://raw.githubusercontent.com/LuckyLight6/loon-rules/main/rules/023-privacy-public-stun-endpoints.lsr) |

## 3 AI 服务（海外与国际版）

### 3.1 海外 AI 合集

| 序号 | 英文名称 | 中文名称 | 用途与选择 | 订阅地址 |
|---:|---|---|---|---|
| 100 | [ai-overseas-all](../rules/100-ai-overseas-all.lsr) | 海外 AI 合集 | **合集：替代 101–122、124。** 汇总所列海外 AI 和共用登录，与成员二选一；Apple Intelligence、国产国内版和国际版各自独立，不合并共享云整域 | [订阅地址](https://raw.githubusercontent.com/LuckyLight6/loon-rules/main/rules/100-ai-overseas-all.lsr) |

### 3.2 海外 AI · 产品细分

| 序号 | 英文名称 | 中文名称 | 用途与选择 | 订阅地址 |
|---:|---|---|---|---|
| 101 | [claude-connections](../rules/101-claude-connections.lsr) | Anthropic：Claude、Claude Code 与 API（登录、附件、MCP 和更新） | Claude 自有入口走同一个策略。外部 MCP、Bedrock、Vertex、Microsoft Foundry 和共享支付不归本组；IP 只匹配已核对的裸地址 | [订阅地址](https://raw.githubusercontent.com/LuckyLight6/loon-rules/main/rules/101-claude-connections.lsr) |
| 102 | [chatgpt-connections](../rules/102-chatgpt-connections.lsr) | ChatGPT、Codex、OpenAI API、语音信令与媒体连接 | 登录、对话和文件按专用域名，语音媒体按官方公开的单个服务器 IP；IP 不为匹配触发 DNS。不把 LiveKit、Stripe、Cloudflare、Azure 或 Google 的共享域和网段一并代理 | [订阅地址](https://raw.githubusercontent.com/LuckyLight6/loon-rules/main/rules/102-chatgpt-connections.lsr) |
| 103 | [gemini-connections](../rules/103-gemini-connections.lsr) | Gemini、AI Studio、NotebookLM、Google AI API 和专用 WebChannel | 通用 Google 登录、下载、存储与 API 不在此组 | [订阅地址](https://raw.githubusercontent.com/LuckyLight6/loon-rules/main/rules/103-gemini-connections.lsr) |
| 104 | [xai-connections](../rules/104-xai-connections.lsr) | xAI 账号、Grok 对话与模型 API | Grok、xAI API 及 Grok、Cursor、Grokipedia 共用账号；Cursor 编辑器、百科内容与 X 社交分别处理 | [订阅地址](https://raw.githubusercontent.com/LuckyLight6/loon-rules/main/rules/104-xai-connections.lsr) |
| 105 | [grokipedia-encyclopedia](../rules/105-grokipedia-encyclopedia.lsr) | Grokipedia AI 百科站点 | 百科页面与内容；共用账号登录由 104 xAI 处理 | [订阅地址](https://raw.githubusercontent.com/LuckyLight6/loon-rules/main/rules/105-grokipedia-encyclopedia.lsr) |
| 106 | [github-copilot-connections](../rules/106-github-copilot-connections.lsr) | GitHub Copilot：补全、对话、API 与专用附件 | Copilot 专用接口、实时连接、附件、报告与遥测；必需接口另按用途核对，共用认证归 300。实验、通用模型目录与跨租户云通配符不纳入 | [订阅地址](https://raw.githubusercontent.com/LuckyLight6/loon-rules/main/rules/106-github-copilot-connections.lsr) |
| 107 | [microsoft-copilot-connections](../rules/107-microsoft-copilot-connections.lsr) | Microsoft Copilot 个人版与工作版独立入口 | 只收自营 Copilot 门户；不吸收 Microsoft 通用登录、Outlook、Graph、Bing 或 GitHub Copilot | [订阅地址](https://raw.githubusercontent.com/LuckyLight6/loon-rules/main/rules/107-microsoft-copilot-connections.lsr) |
| 108 | [meta-ai-assistant](../rules/108-meta-ai-assistant.lsr) | Meta AI 助手的独立网站 | 只匹配 meta.ai；不扩大至 Muse、Facebook、Instagram、WhatsApp 或其共享基础设施 | [订阅地址](https://raw.githubusercontent.com/LuckyLight6/loon-rules/main/rules/108-meta-ai-assistant.lsr) |
| 109 | [muse-agent](../rules/109-muse-agent.lsr) | Muse 独立个人助手与其专用入口 | 只匹配 muse.ai。Meta AI 本站是 108；不把 Meta 社交 App 或 Muse 连接到的第三方网站归进来 | [订阅地址](https://raw.githubusercontent.com/LuckyLight6/loon-rules/main/rules/109-muse-agent.lsr) |
| 110 | [cursor-editor-and-api](../rules/110-cursor-editor-and-api.lsr) | Cursor 客户端及专用接口 | 不把通用 GitHub 和云服务纳入 | [订阅地址](https://raw.githubusercontent.com/LuckyLight6/loon-rules/main/rules/110-cursor-editor-and-api.lsr) |
| 111 | [perplexity-search-and-api](../rules/111-perplexity-search-and-api.lsr) | Perplexity 搜索、API 和专用内容入口 | 按租户主机区分，不代理整个第三方文件云 | [订阅地址](https://raw.githubusercontent.com/LuckyLight6/loon-rules/main/rules/111-perplexity-search-and-api.lsr) |
| 112 | [poe-chat-and-api](../rules/112-poe-chat-and-api.lsr) | Poe 聊天与平台域名 | 不纳入底层模型提供商的共享接口 | [订阅地址](https://raw.githubusercontent.com/LuckyLight6/loon-rules/main/rules/112-poe-chat-and-api.lsr) |
| 113 | [mistral-model-services](../rules/113-mistral-model-services.lsr) | Mistral 平台专用域名 | 第三方推理平台按自己的入口归类 | [订阅地址](https://raw.githubusercontent.com/LuckyLight6/loon-rules/main/rules/113-mistral-model-services.lsr) |
| 114 | [groq-inference](../rules/114-groq-inference.lsr) | Groq 推理服务入口 | 与 Grok/xAI 无关 | [订阅地址](https://raw.githubusercontent.com/LuckyLight6/loon-rules/main/rules/114-groq-inference.lsr) |
| 115 | [cohere-model-services](../rules/115-cohere-model-services.lsr) | Cohere 的推理及平台域名 | 不因同一模型由其他云托管就把云整段纳入 | [订阅地址](https://raw.githubusercontent.com/LuckyLight6/loon-rules/main/rules/115-cohere-model-services.lsr) |
| 116 | [hugging-face-model-hub](../rules/116-hugging-face-model-hub.lsr) | Hugging Face 模型库与专用 CDN | 共享存储不整段代理 | [订阅地址](https://raw.githubusercontent.com/LuckyLight6/loon-rules/main/rules/116-hugging-face-model-hub.lsr) |
| 117 | [devin-cloud-coding](../rules/117-devin-cloud-coding.lsr) | Devin 自有云编程入口 | 不覆盖它所访问的外部仓库 | [订阅地址](https://raw.githubusercontent.com/LuckyLight6/loon-rules/main/rules/117-devin-cloud-coding.lsr) |
| 118 | [elevenlabs-voice-and-api](../rules/118-elevenlabs-voice-and-api.lsr) | ElevenLabs 语音生成、WebSocket、文件与 MCP | 只收厂商专用根域，包含 API 与 ElevenLabs CDN，不扩到第三方语音或存储基础设施 | [订阅地址](https://raw.githubusercontent.com/LuckyLight6/loon-rules/main/rules/118-elevenlabs-voice-and-api.lsr) |
| 119 | [midjourney-image-tools](../rules/119-midjourney-image-tools.lsr) | Midjourney 图像服务入口 | 不把 Discord 基础设施都交给它 | [订阅地址](https://raw.githubusercontent.com/LuckyLight6/loon-rules/main/rules/119-midjourney-image-tools.lsr) |
| 120 | [openrouter-gateway](../rules/120-openrouter-gateway.lsr) | OpenRouter 的模型网关入口 | 同一个网关不根据模型名称切流 | [订阅地址](https://raw.githubusercontent.com/LuckyLight6/loon-rules/main/rules/120-openrouter-gateway.lsr) |
| 121 | [windsurf-editor-and-api](../rules/121-windsurf-editor-and-api.lsr) | Windsurf 和 Codeium 专用接口 | 不把公共托管平台当开发助手 | [订阅地址](https://raw.githubusercontent.com/LuckyLight6/loon-rules/main/rules/121-windsurf-editor-and-api.lsr) |
| 122 | [ai-com-agents](../rules/122-ai-com-agents.lsr) | ai.com 的个人 AI 代理 | ai.com 是独立服务，不归 ChatGPT 或 Claude。海外 AI 统一出口时选 100 即可 | [订阅地址](https://raw.githubusercontent.com/LuckyLight6/loon-rules/main/rules/122-ai-com-agents.lsr) |
| 123 | [apple-intelligence-relays](../rules/123-apple-intelligence-relays.lsr) | Apple Intelligence：PCC 和系统 ChatGPT 扩展 | 中国大陆网络建议用独立代理。能否使用还要看设备、账户、语言和功能资格。普通 Siri、ChatGPT App 和模型下载不归本组 | [订阅地址](https://raw.githubusercontent.com/LuckyLight6/loon-rules/main/rules/123-apple-intelligence-relays.lsr) |
| 124 | [jetbrains-ai](../rules/124-jetbrains-ai.lsr) | JetBrains AI | AI 专用域和官方明确列出的海外后端；中国区 API 另列 516，IDE、账号和插件市场仍归 309，不认领共用配置服务 | [订阅地址](https://raw.githubusercontent.com/LuckyLight6/loon-rules/main/rules/124-jetbrains-ai.lsr) |

### 3.3 国产 AI · 国际版合集

| 序号 | 英文名称 | 中文名称 | 用途与选择 | 订阅地址 |
|---:|---|---|---|---|
| 125 | [ai-cn-international-all](../rules/125-ai-cn-international-all.lsr) | 国产 AI 国际版合集 | **合集：替代 126–132。** 由各产品专表合并生成；统一选出口时用此表，按厂商选出口则用成员，不同时订阅 | [订阅地址](https://raw.githubusercontent.com/LuckyLight6/loon-rules/main/rules/125-ai-cn-international-all.lsr) |

### 3.4 国产 AI · 国际版产品细分

| 序号 | 英文名称 | 中文名称 | 用途与选择 | 订阅地址 |
|---:|---|---|---|---|
| 126 | [qwen-international](../rules/126-qwen-international.lsr) | 阿里千问与百炼 · 国际入口 | 按已核实的国际产品入口生成；同一产品的网页、API 与附件不按功能拆开，共用云平台不收整域 | [订阅地址](https://raw.githubusercontent.com/LuckyLight6/loon-rules/main/rules/126-qwen-international.lsr) |
| 127 | [kimi-international](../rules/127-kimi-international.lsr) | 月之暗面 Kimi · 国际入口 | 按已核实的国际产品入口生成；同一产品的网页、API 与附件不按功能拆开，共用云平台不收整域 | [订阅地址](https://raw.githubusercontent.com/LuckyLight6/loon-rules/main/rules/127-kimi-international.lsr) |
| 128 | [zhipu-international](../rules/128-zhipu-international.lsr) | 智谱 · 国际入口 | 按已核实的国际产品入口生成；同一产品的网页、API 与附件不按功能拆开，共用云平台不收整域 | [订阅地址](https://raw.githubusercontent.com/LuckyLight6/loon-rules/main/rules/128-zhipu-international.lsr) |
| 129 | [minimax-international](../rules/129-minimax-international.lsr) | MiniMax 与海螺 · 国际入口 | 按已核实的国际产品入口生成；同一产品的网页、API 与附件不按功能拆开，共用云平台不收整域 | [订阅地址](https://raw.githubusercontent.com/LuckyLight6/loon-rules/main/rules/129-minimax-international.lsr) |
| 130 | [bytedance-international](../rules/130-bytedance-international.lsr) | 字节豆包、扣子与模型平台 · 国际入口 | 按已核实的国际产品入口生成；同一产品的网页、API 与附件不按功能拆开，共用云平台不收整域 | [订阅地址](https://raw.githubusercontent.com/LuckyLight6/loon-rules/main/rules/130-bytedance-international.lsr) |
| 131 | [siliconflow-international](../rules/131-siliconflow-international.lsr) | 硅基流动 · 国际入口 | 读取官方指南的 SDK API 配置与 API 密钥控制台链接，只生成精确主机；国内版与国际版分别读取，不接管整家云平台 | [订阅地址](https://raw.githubusercontent.com/LuckyLight6/loon-rules/main/rules/131-siliconflow-international.lsr) |
| 132 | [tencent-international](../rules/132-tencent-international.lsr) | 腾讯混元、元宝与 TokenHub · 国际入口 | 按已核实的国际产品入口生成；同一产品的网页、API 与附件不按功能拆开，共用云平台不收整域 | [订阅地址](https://raw.githubusercontent.com/LuckyLight6/loon-rules/main/rules/132-tencent-international.lsr) |

## 4 Apple 生态

账户与商店交易可固定代理，安装包和更新包另选直连。合集用于统一出口，和成员二选一

### 4.1 Apple 生态合集

| 序号 | 英文名称 | 中文名称 | 用途与选择 | 订阅地址 |
|---:|---|---|---|---|
| 200 | [apple-all](../rules/200-apple-all.lsr) | Apple 生态合集 | **合集：替代 123、201–227、229–230。** 替换所列账户、系统、海外媒体、智能与 iCloud 成员。涵盖海外服务，不能整表设直连；混合出口用细分。证书验证仍保持独立 | [订阅地址](https://raw.githubusercontent.com/LuckyLight6/loon-rules/main/rules/200-apple-all.lsr) |

### 4.2 账户、验证与支付

| 序号 | 英文名称 | 中文名称 | 用途与选择 | 订阅地址 |
|---:|---|---|---|---|
| 201 | [apple-account-authentication](../rules/201-apple-account-authentication.lsr) | 登录、OAuth 相关服务、iCloud 初始化与账户恢复 | 优先于商店、iCloud 与共享 Apple CDN | [订阅地址](https://raw.githubusercontent.com/LuckyLight6/loon-rules/main/rules/201-apple-account-authentication.lsr) |
| 202 | [apple-app-and-device-verification](../rules/202-apple-app-and-device-verification.lsr) | 应用验证、App Attest、macOS 公证与设备身份验证 | 保留系统服务直连；共享 apple-cloudkit.com 不从此组抢走 | [订阅地址](https://raw.githubusercontent.com/LuckyLight6/loon-rules/main/rules/202-apple-app-and-device-verification.lsr) |
| 203 | [apple-wallet-payments](../rules/203-apple-wallet-payments.lsr) | Wallet 与 Apple Pay 已知支付入口 | 只收可追溯的精确主机。支付仍依赖账户、设备校验及商户；不吞 ca、Apple 全域或其他支付公司 | [订阅地址](https://raw.githubusercontent.com/LuckyLight6/loon-rules/main/rules/203-apple-wallet-payments.lsr) |

### 4.3 商店交易、安装与通用链接

| 序号 | 英文名称 | 中文名称 | 用途与选择 | 订阅地址 |
|---:|---|---|---|---|
| 204 | [apple-testflight](../rules/204-apple-testflight.lsr) | TestFlight 测试版安装和分发 | 剔除整个 TestFlight 关键词；商店生产环境和系统 OTA 分开 | [订阅地址](https://raw.githubusercontent.com/LuckyLight6/loon-rules/main/rules/204-apple-testflight.lsr) |
| 205 | [apple-store-transactions](../rules/205-apple-store-transactions.lsr) | App Store API、购买与安装指令、Apple Books 商店 | 包括 iTunes 签名初始化、第三方市场安装入口和 Apple Books 门户。账户认证、App 下载和 TestFlight 分开，不包揽整个 itunes.apple.com | [订阅地址](https://raw.githubusercontent.com/LuckyLight6/loon-rules/main/rules/205-apple-store-transactions.lsr) |
| 206 | [apple-app-package-downloads](../rules/206-apple-app-package-downloads.lsr) | App Store 安装包下载 | 只匹配已知安装包入口和别名，不把 mzstatic 整段算作安装包。TestFlight、购买、设备验证和系统更新各有专表 | [订阅地址](https://raw.githubusercontent.com/LuckyLight6/loon-rules/main/rules/206-apple-app-package-downloads.lsr) |
| 207 | [apple-association-services](../rules/207-apple-association-services.lsr) | Apple 通用链接的域名验证 | 只匹配 Associated Domains 端点，不放开整个 Apple CDN | [订阅地址](https://raw.githubusercontent.com/LuckyLight6/loon-rules/main/rules/207-apple-association-services.lsr) |

### 4.4 推送、查找、消息与通话

| 序号 | 英文名称 | 中文名称 | 用途与选择 | 订阅地址 |
|---:|---|---|---|---|
| 208 | [apple-push-connection](../rules/208-apple-push-connection.lsr) | APNs 系统推送的域名与公开客户端网段 | 独立选择长连接出口。默认保留实测可用路径；直连丢通知时可只切此组对照。不能按 App 国别拆系统推送 | [订阅地址](https://raw.githubusercontent.com/LuckyLight6/loon-rules/main/rules/208-apple-push-connection.lsr) |
| 209 | [apple-location-services](../rules/209-apple-location-services.lsr) | 定位、地图配置与 Find My 已识别入口 | 定位查询与信号定位数据按 Apple 公开客户端配置补入；保留既有定位和 Find My 范围，账户、推送和 iCloud 网页仍分别处理 | [订阅地址](https://raw.githubusercontent.com/LuckyLight6/loon-rules/main/rules/209-apple-location-services.lsr) |
| 210 | [apple-messaging-identity](../rules/210-apple-messaging-identity.lsr) | Apple IDS 共用身份、注册与查询服务 | 从 Apple 公开配置读取认证、注册、查询与资料入口；保留既有 IDS 父域补充，与定位和推送分开，不代替全部消息媒体或 FaceTime 中继 | [订阅地址](https://raw.githubusercontent.com/LuckyLight6/loon-rules/main/rules/210-apple-messaging-identity.lsr) |

### 4.5 专用代理与 iCloud 文件

| 序号 | 英文名称 | 中文名称 | 用途与选择 | 订阅地址 |
|---:|---|---|---|---|
| 211 | [apple-private-relay-connections](../rules/211-apple-private-relay-connections.lsr) | Private Relay 的 mask 域和 Apple DNS 中继别名 | 放在 iCloud 同步前；不包含整个 iCloud 或 Apple DNS 后缀 | [订阅地址](https://raw.githubusercontent.com/LuckyLight6/loon-rules/main/rules/211-apple-private-relay-connections.lsr) |
| 212 | [apple-icloud-mainland](../rules/212-apple-icloud-mainland.lsr) | 中国大陆 iCloud 服务和内容专用域 | 只收官方标注的大陆服务域及 Apple DNS 委派的大陆内容域；不认为 Apple 账户、CloudKit 或共用域都在大陆 | [订阅地址](https://raw.githubusercontent.com/LuckyLight6/loon-rules/main/rules/212-apple-icloud-mainland.lsr) |
| 213 | [apple-icloud-content-domains](../rules/213-apple-icloud-content-domains.lsr) | iCloud 通用内容域 | 仅匹配 icloud-content.com 内容域，能直连再直连。大陆专域另管；部分上传、备份仍使用共用服务 | [订阅地址](https://raw.githubusercontent.com/LuckyLight6/loon-rules/main/rules/213-apple-icloud-content-domains.lsr) |
| 214 | [apple-cloud-sync](../rules/214-apple-cloud-sync.lsr) | iCloud 通用服务、CloudKit、同步、邮件及 iWork | 认证、查找、Private Relay、确定的内容域及大陆服务分别匹配；通用域不能用来判断账户或存储国家 | [订阅地址](https://raw.githubusercontent.com/LuckyLight6/loon-rules/main/rules/214-apple-cloud-sync.lsr) |
| 215 | [apple-podcasts](../rules/215-apple-podcasts.lsr) | Apple 播客 | 识别播客目录，不把创作者自己托管的音频也归给 Apple | [订阅地址](https://raw.githubusercontent.com/LuckyLight6/loon-rules/main/rules/215-apple-podcasts.lsr) |

### 4.6 音乐、视频、新闻与普通 Siri

| 序号 | 英文名称 | 中文名称 | 用途与选择 | 订阅地址 |
|---:|---|---|---|---|
| 216 | [apple-music-and-radio](../rules/216-apple-music-and-radio.lsr) | Apple Music、广播及共用 API 与应用门户 | 保留 Music 门户、API 和不能据域名进一步切开的音乐视频流量。明确音频传输在 217 | [订阅地址](https://raw.githubusercontent.com/LuckyLight6/loon-rules/main/rules/216-apple-music-and-radio.lsr) |
| 217 | [apple-music-audio-delivery](../rules/217-apple-music-audio-delivery.lsr) | Apple Music 已识别音频交付主机 | 社区资料中的明确音频传输主机，不包含 Music API、账户和整个 itunes.apple.com。缓存是否在大陆不能由域名推定 | [订阅地址](https://raw.githubusercontent.com/LuckyLight6/loon-rules/main/rules/217-apple-music-audio-delivery.lsr) |
| 218 | [apple-video-and-fitness](../rules/218-apple-video-and-fitness.lsr) | Apple TV／Fitness+ 的门户、播放控制与共用主机 | 中国大陆未提供对应订阅；入口默认选服务可用地区的代理。已识别 HLS 交给独立视频组，同一会话用一致出口 | [订阅地址](https://raw.githubusercontent.com/LuckyLight6/loon-rules/main/rules/218-apple-video-and-fitness.lsr) |
| 219 | [apple-tv-video-delivery](../rules/219-apple-tv-video-delivery.lsr) | Apple TV 已识别的 HLS 视频交付 | 匹配已识别 HLS 主机。大陆网络默认与 TV 播放控制同一代理；可单独统计流量，不把其他 Apple CDN 一并代理 | [订阅地址](https://raw.githubusercontent.com/LuckyLight6/loon-rules/main/rules/219-apple-tv-video-delivery.lsr) |
| 220 | [apple-news-and-sports](../rules/220-apple-news-and-sports.lsr) | Apple News／News+、内容入口与 Apple Sports | 中国大陆未提供；默认选对应服务可用地区的代理，不纳入国内直连例外 | [订阅地址](https://raw.githubusercontent.com/LuckyLight6/loon-rules/main/rules/220-apple-news-and-sports.lsr) |
| 221 | [apple-siri-and-search](../rules/221-apple-siri-and-search.lsr) | Siri 与 Spotlight 的专用域名 | Siri、听写和系统搜索可共用主机；未能按主机区分普通 Siri 与 Siri AI 时，保留独立策略供真机对照，不把所有 Siri 当 PCC | [订阅地址](https://raw.githubusercontent.com/LuckyLight6/loon-rules/main/rules/221-apple-siri-and-search.lsr) |

### 4.7 软件更新与下载

| 序号 | 英文名称 | 中文名称 | 用途与选择 | 订阅地址 |
|---:|---|---|---|---|
| 222 | [apple-update-control](../rules/222-apple-update-control.lsr) | 系统更新目录、检查、登记和控制端点 | 含 OTA/Rosetta 检查、系统恢复服务和 Beta 登记；已确认的二进制内容下载另在 223，不按整个 cdn-apple.com 或整段 Apple IP 分类 | [订阅地址](https://raw.githubusercontent.com/LuckyLight6/loon-rules/main/rules/222-apple-update-control.lsr) |
| 223 | [apple-update-downloads](../rules/223-apple-update-downloads.lsr) | 系统更新包与恢复内容下载 | 收系统恢复、更新包和运营商设置包及已核对的精确 DNS 别名。目录、激活和证书另管，不按整个 CDN 或地区推断 | [订阅地址](https://raw.githubusercontent.com/LuckyLight6/loon-rules/main/rules/223-apple-update-downloads.lsr) |
| 224 | [apple-developer-portal](../rules/224-apple-developer-portal.lsr) | Apple Developer 门户 | 只认开发者门户；账户认证、App 公证和独立下载主机沿用各自规则 | [订阅地址](https://raw.githubusercontent.com/LuckyLight6/loon-rules/main/rules/224-apple-developer-portal.lsr) |
| 225 | [apple-developer-downloads](../rules/225-apple-developer-downloads.lsr) | Xcode、Swift Playgrounds 和开发者组件的实际下载 | 开发下载与 App Store、OTA 和共享的 App 公证端点分开 | [订阅地址](https://raw.githubusercontent.com/LuckyLight6/loon-rules/main/rules/225-apple-developer-downloads.lsr) |
| 226 | [apple-mainland-delivery-aliases](../rules/226-apple-mainland-delivery-aliases.lsr) | 已核对的 Apple 大陆就近分发别名 | 只收明确标注 cn-lb 的精确别名。是否从本地边缘节点命中仍以 DNS 和请求日志为准；不能把备案域或公共 CNAME 当大陆独占 CDN | [订阅地址](https://raw.githubusercontent.com/LuckyLight6/loon-rules/main/rules/226-apple-mainland-delivery-aliases.lsr) |
| 227 | [apple-shared-store-assets](../rules/227-apple-shared-store-assets.lsr) | Apple 商店与媒体共用的静态内容 | mzstatic 也承载图标、书籍和音乐内容，不能当成纯安装包。s.mzstatic.com 应先命中 202；静态图片别名不保证专供大陆 | [订阅地址](https://raw.githubusercontent.com/LuckyLight6/loon-rules/main/rules/227-apple-shared-store-assets.lsr) |

### 4.8 证书、设备管理和学校服务

| 序号 | 英文名称 | 中文名称 | 用途与选择 | 订阅地址 |
|---:|---|---|---|---|
| 228 | [apple-certificate-validation](../rules/228-apple-certificate-validation.lsr) | Apple 设备的证书状态和撤销检查 | 只用官方给出的证书端点及已知 Apple 主机别名，不扩到整个 DigiCert | [订阅地址](https://raw.githubusercontent.com/LuckyLight6/loon-rules/main/rules/228-apple-certificate-validation.lsr) |
| 229 | [apple-system-connectivity](../rules/229-apple-system-connectivity.lsr) | Apple 激活、设备管理、诊断与设备素材 | 激活、设备管理、诊断、校时和设备素材走本组。不收整个 Apple 网段或共用 CDN，也不替代账号、推送与钱包组 | [订阅地址](https://raw.githubusercontent.com/LuckyLight6/loon-rules/main/rules/229-apple-system-connectivity.lsr) |
| 230 | [apple-schoolwork-handouts](../rules/230-apple-schoolwork-handouts.lsr) | Apple Schoolwork 讲义与资料交付 | 官方明确归属 Schoolwork Handout 的主机；班级名册和设备验证另走共享服务 | [订阅地址](https://raw.githubusercontent.com/LuckyLight6/loon-rules/main/rules/230-apple-schoolwork-handouts.lsr) |

## 5 开发（海外）

### 5.1 代码托管

| 序号 | 英文名称 | 中文名称 | 用途与选择 | 订阅地址 |
|---:|---|---|---|---|
| 300 | [github-code-and-packages](../rules/300-github-code-and-packages.lsr) | GitHub 代码托管、API、Actions 与容器镜像 | 代码、API、Actions、容器与软件包；官方 Meta 清单补入专用资产主机，不采用其 IP 范围或跨租户托管通配符。Copilot 接口先由 106 匹配，npm 公共仓库仍归 303 | [订阅地址](https://raw.githubusercontent.com/LuckyLight6/loon-rules/main/rules/300-github-code-and-packages.lsr) |
| 301 | [gitlab-hosting](../rules/301-gitlab-hosting.lsr) | GitLab.com | 仅 GitLab 公共托管平台；不接管自建 GitLab 或用户 Pages | [订阅地址](https://raw.githubusercontent.com/LuckyLight6/loon-rules/main/rules/301-gitlab-hosting.lsr) |
| 302 | [bitbucket-hosting](../rules/302-bitbucket-hosting.lsr) | Atlassian Bitbucket | 代码托管与公共 API，不收整个 Atlassian、Jira 或用户站 | [订阅地址](https://raw.githubusercontent.com/LuckyLight6/loon-rules/main/rules/302-bitbucket-hosting.lsr) |

### 5.2 软件包与容器

| 序号 | 英文名称 | 中文名称 | 用途与选择 | 订阅地址 |
|---:|---|---|---|---|
| 303 | [npm-registry](../rules/303-npm-registry.lsr) | npm 软件包 | 官方注册表和产品站；国内镜像单列 | [订阅地址](https://raw.githubusercontent.com/LuckyLight6/loon-rules/main/rules/303-npm-registry.lsr) |
| 304 | [maven-central](../rules/304-maven-central.lsr) | Maven Central | 只认默认依赖仓库，不把 apache.org 整域算作包下载 | [订阅地址](https://raw.githubusercontent.com/LuckyLight6/loon-rules/main/rules/304-maven-central.lsr) |
| 305 | [pypi-packages](../rules/305-pypi-packages.lsr) | PyPI 软件包 | 官方 Python 包索引、文档、上传与文件下载；不包揽 pythonhosted.org 上的项目网站 | [订阅地址](https://raw.githubusercontent.com/LuckyLight6/loon-rules/main/rules/305-pypi-packages.lsr) |
| 306 | [docker-hub](../rules/306-docker-hub.lsr) | Docker Hub | Docker Hub 登录、鉴权和镜像分发按官方用途筛选；不接管共享 Auth0、错误报告、Desktop 更新、Scout 或其他 Docker 产品 | [订阅地址](https://raw.githubusercontent.com/LuckyLight6/loon-rules/main/rules/306-docker-hub.lsr) |
| 307 | [rust-cargo](../rules/307-rust-cargo.lsr) | Rust、Cargo 与 crates.io | 软件包、工具链和文档；不包括私有 Cargo 注册表 | [订阅地址](https://raw.githubusercontent.com/LuckyLight6/loon-rules/main/rules/307-rust-cargo.lsr) |
| 308 | [go-modules](../rules/308-go-modules.lsr) | Go 模块与工具链 | Go 项目、模块代理和校验服务；不扩到通用 Google APIs | [订阅地址](https://raw.githubusercontent.com/LuckyLight6/loon-rules/main/rules/308-go-modules.lsr) |

### 5.3 开发工具

| 序号 | 英文名称 | 中文名称 | 用途与选择 | 订阅地址 |
|---:|---|---|---|---|
| 309 | [jetbrains-ides](../rules/309-jetbrains-ides.lsr) | JetBrains IDE、授权与插件 | IDE、授权、插件市场与设置同步；官方用途表补全当前主机。AI 专用后端、中国区 AI API、Node.js 与 ACP 注册表分别匹配，不把整套依赖都归给 IDE | [订阅地址](https://raw.githubusercontent.com/LuckyLight6/loon-rules/main/rules/309-jetbrains-ides.lsr) |

### 5.4 运行时与代理协议

| 序号 | 英文名称 | 中文名称 | 用途与选择 | 订阅地址 |
|---:|---|---|---|---|
| 310 | [nodejs-runtime](../rules/310-nodejs-runtime.lsr) | Node.js 运行时与官方发行站 | 从官方站点身份确认独立根域，覆盖运行时发布、下载与文档；npm 仓库和国内镜像各自匹配，不含第三方包的网络请求 | [订阅地址](https://raw.githubusercontent.com/LuckyLight6/loon-rules/main/rules/310-nodejs-runtime.lsr) |
| 311 | [agent-client-protocol](../rules/311-agent-client-protocol.lsr) | ACP 协议、文档与代理注册表 | 从 Agent Client Protocol 官方站点身份确认独立根域，覆盖 JetBrains 文档要求的注册表 CDN；具体代理的模型 API、GitHub 和 npm 不归本组 | [订阅地址](https://raw.githubusercontent.com/LuckyLight6/loon-rules/main/rules/311-agent-client-protocol.lsr) |

## 6 通讯与社交（海外）

### 6.1 消息与团队协作

| 序号 | 英文名称 | 中文名称 | 用途与选择 | 订阅地址 |
|---:|---|---|---|---|
| 330 | [telegram-messaging](../rules/330-telegram-messaging.lsr) | Telegram 登录、消息、文件与直连 IP | 核心域名 + 官方 CIDR。网段仅处理裸 IP；未收第三方 ASN、关键词和通用 CDN | [订阅地址](https://raw.githubusercontent.com/LuckyLight6/loon-rules/main/rules/330-telegram-messaging.lsr) |
| 331 | [discord-messaging-and-voice](../rules/331-discord-messaging-and-voice.lsr) | Discord 消息、语音、活动和附件 | 仅 Discord 专用域及精确附件存储主机；不给整个 Google Storage 或含 discord 的域名选路 | [订阅地址](https://raw.githubusercontent.com/LuckyLight6/loon-rules/main/rules/331-discord-messaging-and-voice.lsr) |
| 332 | [signal-messenger](../rules/332-signal-messenger.lsr) | Signal 消息、通话、贴纸、群组与用户名链接 | 按官方网络说明生成当前客户端入口；不将第三方代理、公共中继或未确认的历史域名并入 | [订阅地址](https://raw.githubusercontent.com/LuckyLight6/loon-rules/main/rules/332-signal-messenger.lsr) |
| 333 | [line-messenger](../rules/333-line-messenger.lsr) | LINE | 只收 LINE 产品入口和专用素材；不把 Naver 或其他应用整域纳入 | [订阅地址](https://raw.githubusercontent.com/LuckyLight6/loon-rules/main/rules/333-line-messenger.lsr) |

### 6.2 社交与社区

| 序号 | 英文名称 | 中文名称 | 用途与选择 | 订阅地址 |
|---:|---|---|---|---|
| 334 | [x-social-and-media](../rules/334-x-social-and-media.lsr) | X / Twitter 社交与图像视频 | Grok 专用的 grok.x.com 由 104 在前截取。只接产品和短链，不使用 twitter 关键词或广泛网段 | [订阅地址](https://raw.githubusercontent.com/LuckyLight6/loon-rules/main/rules/334-x-social-and-media.lsr) |
| 335 | [wechat-international-portal](../rules/335-wechat-international-portal.lsr) | WeChat 国际门户与支付 | 只分明确的国际入口；微信和 WeChat 共同使用的 qq.com 下精确子域由 550 负责 | [订阅地址](https://raw.githubusercontent.com/LuckyLight6/loon-rules/main/rules/335-wechat-international-portal.lsr) |
| 336 | [slack-workspaces](../rules/336-slack-workspaces.lsr) | Slack | 工作区、消息、文件和素材；外部登录分别匹配。日志统计留给可选隐私规则，培训、演示和旧版跳转不当作当前客户端必需入口 | [订阅地址](https://raw.githubusercontent.com/LuckyLight6/loon-rules/main/rules/336-slack-workspaces.lsr) |
| 337 | [reddit-community](../rules/337-reddit-community.lsr) | Reddit | 社区及专用内容域；不包括外链网站 | [订阅地址](https://raw.githubusercontent.com/LuckyLight6/loon-rules/main/rules/337-reddit-community.lsr) |

## 7 支付（海外）

| 序号 | 英文名称 | 中文名称 | 用途与选择 | 订阅地址 |
|---:|---|---|---|---|
| 350 | [paypal-payments](../rules/350-paypal-payments.lsr) | PayPal 核心支付、验签和静态资源 | 区分 PayPal 与旗下 Braintree/Venmo/Xoom 等其他产品，不靠 Paypal 关键词判断 | [订阅地址](https://raw.githubusercontent.com/LuckyLight6/loon-rules/main/rules/350-paypal-payments.lsr) |
| 351 | [stripe-payments](../rules/351-stripe-payments.lsr) | Stripe | 托管结账、接口和产品专用素材；不接管商户网站 | [订阅地址](https://raw.githubusercontent.com/LuckyLight6/loon-rules/main/rules/351-stripe-payments.lsr) |
| 352 | [link-payments](../rules/352-link-payments.lsr) | Link 快捷支付 | Stripe 的独立快捷支付产品，从官方站点身份确认根域；Stripe 网关、商户网站和发卡行验证分别匹配 | [订阅地址](https://raw.githubusercontent.com/LuckyLight6/loon-rules/main/rules/352-link-payments.lsr) |
| 353 | [braintree-payments](../rules/353-braintree-payments.lsr) | Braintree 商户支付、网关与 SDK | 生产与沙箱 API 从官方域名代码清单更新，网关和 SDK 使用独立产品范围；不包括 PayPal、Venmo、Xoom 的账户，不采用整段 IP | [订阅地址](https://raw.githubusercontent.com/LuckyLight6/loon-rules/main/rules/353-braintree-payments.lsr) |
| 354 | [venmo-payments](../rules/354-venmo-payments.lsr) | Venmo 支付 | 从官方产品站身份确认专用根域；PayPal、Braintree、其它钱包和商户网站各自匹配 | [订阅地址](https://raw.githubusercontent.com/LuckyLight6/loon-rules/main/rules/354-venmo-payments.lsr) |
| 355 | [xoom-transfers](../rules/355-xoom-transfers.lsr) | Xoom 汇款 | 从官方产品站身份确认专用根域；PayPal、Braintree、其它钱包和商户网站各自匹配 | [订阅地址](https://raw.githubusercontent.com/LuckyLight6/loon-rules/main/rules/355-xoom-transfers.lsr) |

## 8 加密资产（海外）

### 8.1 交易平台

| 序号 | 英文名称 | 中文名称 | 用途与选择 | 订阅地址 |
|---:|---|---|---|---|
| 360 | [binance-platform](../rules/360-binance-platform.lsr) | Binance 币安 | 交易平台、现货 REST API 与实时行情；从官方基础端点说明补入专用主机，不把 binance.vision 整域、BNB 公链或第三方追踪归为交易平台 | [订阅地址](https://raw.githubusercontent.com/LuckyLight6/loon-rules/main/rules/360-binance-platform.lsr) |
| 361 | [okx-platform](../rules/361-okx-platform.lsr) | OKX 欧易 | 交易平台及专用连接，不包括 OKLink 浏览器或整个 Cloudflare | [订阅地址](https://raw.githubusercontent.com/LuckyLight6/loon-rules/main/rules/361-okx-platform.lsr) |
| 362 | [gemini-exchange](../rules/362-gemini-exchange.lsr) | Gemini 交易平台与 API | 从交易平台官方服务器字段确认提供方域；生产、沙箱、网页与 WebSocket 同属 Gemini Exchange，和 Google Gemini AI 分开 | [订阅地址](https://raw.githubusercontent.com/LuckyLight6/loon-rules/main/rules/362-gemini-exchange.lsr) |

### 8.2 钱包服务

| 序号 | 英文名称 | 中文名称 | 用途与选择 | 订阅地址 |
|---:|---|---|---|---|
| 370 | [trust-wallet](../rules/370-trust-wallet.lsr) | Trust Wallet | 钱包自己的服务；第三方 DApp 与各条链的公共 RPC 不属于钱包 | [订阅地址](https://raw.githubusercontent.com/LuckyLight6/loon-rules/main/rules/370-trust-wallet.lsr) |

## 9 媒体（海外）

### 9.1 海外影音合集

| 序号 | 英文名称 | 中文名称 | 用途与选择 | 订阅地址 |
|---:|---|---|---|---|
| 380 | [overseas-media-all](../rules/380-overseas-media-all.lsr) | 海外影音合集 | **合集：替代 381–391。** 汇总所列海外视频、音乐、短视频和直播专项；与成员二选一。国内影音和其他海外影音补充不包含在本组 | [订阅地址](https://raw.githubusercontent.com/LuckyLight6/loon-rules/main/rules/380-overseas-media-all.lsr) |

### 9.2 海外视频平台

| 序号 | 英文名称 | 中文名称 | 用途与选择 | 订阅地址 |
|---:|---|---|---|---|
| 381 | [hbo-streaming](../rules/381-hbo-streaming.lsr) | HBO Max | 只收已核对的产品域；不推断账户订阅或播放地区 | [订阅地址](https://raw.githubusercontent.com/LuckyLight6/loon-rules/main/rules/381-hbo-streaming.lsr) |
| 382 | [youtube-video-and-cdn](../rules/382-youtube-video-and-cdn.lsr) | YouTube 视频、音乐、频道与专用 CDN | 保留 youtubei、googlevideo 和 YouTube 静态域；不收整个 gvt2、Google IP 或 youtube 关键词 | [订阅地址](https://raw.githubusercontent.com/LuckyLight6/loon-rules/main/rules/382-youtube-video-and-cdn.lsr) |
| 383 | [netflix-video-and-delivery](../rules/383-netflix-video-and-delivery.lsr) | Netflix 播放、设备 API 和内容分发 | 保留 Netflix 服务域与 nflx* 中已确认的专用后缀；不接管 AWS 或来源不明的直播 IP | [订阅地址](https://raw.githubusercontent.com/LuckyLight6/loon-rules/main/rules/383-netflix-video-and-delivery.lsr) |
| 384 | [disney-plus-streaming](../rules/384-disney-plus-streaming.lsr) | Disney+ 播放及其专用交付 | 不将迪士尼乐园、体育、Hulu 或整个共享 bamgrid 网关当 Disney+。可归属的主机按精确匹配 | [订阅地址](https://raw.githubusercontent.com/LuckyLight6/loon-rules/main/rules/384-disney-plus-streaming.lsr) |
| 385 | [prime-video-streaming](../rules/385-prime-video-streaming.lsr) | Prime Video 视频 API 和内容 | Amazon 零售、共享 CloudFront 父域和通用图片不纳入。本组只保已识别视频专用域和 CDN 别名 | [订阅地址](https://raw.githubusercontent.com/LuckyLight6/loon-rules/main/rules/385-prime-video-streaming.lsr) |

### 9.3 音乐与直播

| 序号 | 英文名称 | 中文名称 | 用途与选择 | 订阅地址 |
|---:|---|---|---|---|
| 386 | [spotify-audio](../rules/386-spotify-audio.lsr) | Spotify 音乐播放和音频文件 | 去掉任意包含 spotify 的关键词；播放走 spotify.com、scdn.co 等专用后缀 | [订阅地址](https://raw.githubusercontent.com/LuckyLight6/loon-rules/main/rules/386-spotify-audio.lsr) |
| 387 | [twitch-live-video](../rules/387-twitch-live-video.lsr) | Twitch 直播、聊天室和内容 CDN | 不导入整个来源 ASN/IP 或关键词。Twitch 专属后缀独立于其他视频服务 | [订阅地址](https://raw.githubusercontent.com/LuckyLight6/loon-rules/main/rules/387-twitch-live-video.lsr) |
| 388 | [tiktok-international-video](../rules/388-tiktok-international-video.lsr) | TikTok 国际短视频与直播 | 只含 TikTok 专有域；CapCut、抖音、Trae 以及两版共用字节云不划进本组 | [订阅地址](https://raw.githubusercontent.com/LuckyLight6/loon-rules/main/rules/388-tiktok-international-video.lsr) |
| 389 | [bilibili-international-video](../rules/389-bilibili-international-video.lsr) | 哔哩哔哩国际版视频 | 只收明确的国际版根域；共用视频 CDN 和中国站仍按各自规则或通用层 | [订阅地址](https://raw.githubusercontent.com/LuckyLight6/loon-rules/main/rules/389-bilibili-international-video.lsr) |
| 390 | [bahamut-video-and-community](../rules/390-bahamut-video-and-community.lsr) | 巴哈姆特动画疯和电玩社区 | 专表有巴哈姆特域名和精确 CDN 别名，不匹配整个 Akamai/Hinet | [订阅地址](https://raw.githubusercontent.com/LuckyLight6/loon-rules/main/rules/390-bahamut-video-and-community.lsr) |

### 9.4 新闻与节目

| 序号 | 英文名称 | 中文名称 | 用途与选择 | 订阅地址 |
|---:|---|---|---|---|
| 391 | [bbc-news-and-video](../rules/391-bbc-news-and-video.lsr) | BBC 新闻与影音 | BBC 自有产品域；不包揽共享 CDN 或据此保证地区版权可用 | [订阅地址](https://raw.githubusercontent.com/LuckyLight6/loon-rules/main/rules/391-bbc-news-and-video.lsr) |

## 10 游戏（海外）

| 序号 | 英文名称 | 中文名称 | 用途与选择 | 订阅地址 |
|---:|---|---|---|---|
| 410 | [steam-international-platform](../rules/410-steam-international-platform.lsr) | Steam 国际商店、社区、联机和下载 | 国内下载镜像由 610 处理。社区素材和直播只收 Steam 专用主机，不匹配整个第三方 CDN 或共享网段 | [订阅地址](https://raw.githubusercontent.com/LuckyLight6/loon-rules/main/rules/410-steam-international-platform.lsr) |
| 411 | [epic-games-services](../rules/411-epic-games-services.lsr) | Epic Games 商店、登录及 Unreal 服务 | 保留游戏厂商的专用域，不接管客服 SaaS 或共享 Amazon/CloudFront 域 | [订阅地址](https://raw.githubusercontent.com/LuckyLight6/loon-rules/main/rules/411-epic-games-services.lsr) |
| 412 | [playstation-network](../rules/412-playstation-network.lsr) | Sony PlayStation | 商店、账户和产品网络；不把所有 Sony 服务或联机 IP 归入 | [订阅地址](https://raw.githubusercontent.com/LuckyLight6/loon-rules/main/rules/412-playstation-network.lsr) |
| 413 | [nintendo-platform](../rules/413-nintendo-platform.lsr) | Nintendo 任天堂 | 核心平台与官网地区门户；排除大陆专用域、共享基础设施和无法核实归属的游戏域名 | [订阅地址](https://raw.githubusercontent.com/LuckyLight6/loon-rules/main/rules/413-nintendo-platform.lsr) |
| 414 | [hoyoverse-international](../rules/414-hoyoverse-international.lsr) | HoYoverse 国际版 | 国际门户及专用游戏站；米游社和国服另列 | [订阅地址](https://raw.githubusercontent.com/LuckyLight6/loon-rules/main/rules/414-hoyoverse-international.lsr) |
| 415 | [ea-games](../rules/415-ea-games.lsr) | EA 游戏平台 | EA 平台及已识别的专用素材；第三方游戏服务器不整段收录 | [订阅地址](https://raw.githubusercontent.com/LuckyLight6/loon-rules/main/rules/415-ea-games.lsr) |
| 416 | [ubisoft-connect](../rules/416-ubisoft-connect.lsr) | Ubisoft Connect | 育碧账号、启动器与产品服务，独立客户端站点从官方产品说明读取；不把 AWS、Akamai 或调查工具整域归入 | [订阅地址](https://raw.githubusercontent.com/LuckyLight6/loon-rules/main/rules/416-ubisoft-connect.lsr) |
| 417 | [blizzard-battlenet](../rules/417-blizzard-battlenet.lsr) | Blizzard / Battle.net 国际服务 | 国际平台入口；国内运营商入口不因品牌相同而并入 | [订阅地址](https://raw.githubusercontent.com/LuckyLight6/loon-rules/main/rules/417-blizzard-battlenet.lsr) |

## 11 办公与其他海外产品

| 序号 | 英文名称 | 中文名称 | 用途与选择 | 订阅地址 |
|---:|---|---|---|---|
| 430 | [notion-workspace](../rules/430-notion-workspace.lsr) | Notion | 工作区、API、专用素材和官方状态入口；自营主机随官方清单更新。不收出站 IP、整个 Cloudflare，或 notion.site 的公共托管租户与用户自定义域 | [订阅地址](https://raw.githubusercontent.com/LuckyLight6/loon-rules/main/rules/430-notion-workspace.lsr) |
| 431 | [figma-design](../rules/431-figma-design.lsr) | Figma | 在线设计和团队工作区，不收第三方插件访问的任意主机 | [订阅地址](https://raw.githubusercontent.com/LuckyLight6/loon-rules/main/rules/431-figma-design.lsr) |
| 432 | [trello-boards](../rules/432-trello-boards.lsr) | Trello | 看板和专用素材；不收整个 Atlassian 平台 | [订阅地址](https://raw.githubusercontent.com/LuckyLight6/loon-rules/main/rules/432-trello-boards.lsr) |
| 433 | [atlassian-cloud-services](../rules/433-atlassian-cloud-services.lsr) | Atlassian Cloud：共享平台、Jira 与 Confluence | Jira、Confluence、共享认证、素材与政府云的第一方域；Bitbucket、Trello 各有专表。忽略合作方整域、出站 IP 和私有隔离云占位符 | [订阅地址](https://raw.githubusercontent.com/LuckyLight6/loon-rules/main/rules/433-atlassian-cloud-services.lsr) |

## 12 Google 生态

在海外具体产品之后、国内具体产品之前；先认 Discord 等产品专用主机，再处理 Google 的账户、产品和共享平台

### 12.1 Google 生态合集

| 序号 | 英文名称 | 中文名称 | 用途与选择 | 订阅地址 |
|---:|---|---|---|---|
| 450 | [google-all](../rules/450-google-all.lsr) | Google 生态合集 | **合集：替代 451–459。** 替换本章学术、账户、邮箱、办公、Meet、Play、下载和通用服务成员，共用一个出口；更早的 Gemini、YouTube 等专项照常生效。需要节省下载配额时选细分 | [订阅地址](https://raw.githubusercontent.com/LuckyLight6/loon-rules/main/rules/450-google-all.lsr) |

### 12.2 Google 产品细分

| 序号 | 英文名称 | 中文名称 | 用途与选择 | 订阅地址 |
|---:|---|---|---|---|
| 451 | [google-scholar](../rules/451-google-scholar.lsr) | Google 学术搜索 | 按 Google 官方域名清单识别各地区 Scholar 专用主机，不接管账户、通用存储或出版社网站 | [订阅地址](https://raw.githubusercontent.com/LuckyLight6/loon-rules/main/rules/451-google-scholar.lsr) |
| 452 | [google-account-authentication](../rules/452-google-account-authentication.lsr) | Google 共享账号、地区登录、OAuth 授权与换令牌 | 登录和授权供多个业务共用；地区主机按官方模板与地区域名清单生成，不归 Gemini、Gmail、Meet 或 Drive 专项 | [订阅地址](https://raw.githubusercontent.com/LuckyLight6/loon-rules/main/rules/452-google-account-authentication.lsr) |
| 453 | [google-gmail-mail](../rules/453-google-gmail-mail.lsr) | Gmail 网页、邮件协议、专用 API 与投递诊断 | 区分 Gmail 网页、API 和 IMAP、SMTP、POP，含 Workspace 邮件中继。专用 API 和投递诊断随官方目录更新；登录与其他 Google API 分开 | [订阅地址](https://raw.githubusercontent.com/LuckyLight6/loon-rules/main/rules/453-google-gmail-mail.lsr) |
| 454 | [google-meet-meetings](../rules/454-google-meet-meetings.lsr) | Google Meet 会议、API 与 Workspace 共用音视频媒体 | 普通账户、字体和 Chat API 分开；媒体按官方章节的 CIDR 与精确 SNI，只匹配目标 IP，不为匹配解析 DNS。同一 Workspace 媒体入口不能再按发起应用细分 | [订阅地址](https://raw.githubusercontent.com/LuckyLight6/loon-rules/main/rules/454-google-meet-meetings.lsr) |
| 455 | [google-drive-and-documents](../rules/455-google-drive-and-documents.lsr) | Google Drive、文档和上传下载入口 | Drive、Docs 和明确文件主机。账号归 Google 账号组，不把整个 googleusercontent.com 或 www.googleapis.com 当网盘 | [订阅地址](https://raw.githubusercontent.com/LuckyLight6/loon-rules/main/rules/455-google-drive-and-documents.lsr) |
| 456 | [google-play-services](../rules/456-google-play-services.lsr) | Google Play 商店、应用管理与专用 API | 商店门户、企业应用管理、发布、完整性、报告及分组 API 随官方目录更新；游戏服务另列，共用 Android、FCM 和设备配置主机留给 Google 通用层 | [订阅地址](https://raw.githubusercontent.com/LuckyLight6/loon-rules/main/rules/456-google-play-services.lsr) |
| 457 | [google-play-games](../rules/457-google-play-games.lsr) | Google Play 游戏、发布与管理 API | 从官方目录读取 Google Play Games 的游戏服务、发布和管理 API；不把游戏本体、共享下载或所有 Android 主机归入本组 | [订阅地址](https://raw.githubusercontent.com/LuckyLight6/loon-rules/main/rules/457-google-play-games.lsr) |
| 458 | [google-software-downloads](../rules/458-google-software-downloads.lsr) | Google 软件和更新已知下载主机 | Google 软件包，以及使用 Google OTA 的设备下载更新的已知主机。只按下载用途认领精确主机，不按整个 CDN 分流 | [订阅地址](https://raw.githubusercontent.com/LuckyLight6/loon-rules/main/rules/458-google-software-downloads.lsr) |

### 12.3 Google 共用平台

| 序号 | 英文名称 | 中文名称 | 用途与选择 | 订阅地址 |
|---:|---|---|---|---|
| 459 | [google-platform-services](../rules/459-google-platform-services.lsr) | Google 搜索和共享平台兜底 | 置于账号、Gmail、Meet、Drive、Play、下载、Gemini 和 YouTube 之后。保留共享域，去掉通用关键词及共享 IP | [订阅地址](https://raw.githubusercontent.com/LuckyLight6/loon-rules/main/rules/459-google-platform-services.lsr) |

## 13 Microsoft 生态

在海外具体产品之后、国内具体产品之前；Microsoft Copilot、GitHub Copilot 和 GitHub 仍各自独立

### 13.1 Microsoft 生态合集

| 序号 | 英文名称 | 中文名称 | 用途与选择 | 订阅地址 |
|---:|---|---|---|---|
| 470 | [microsoft-all](../rules/470-microsoft-all.lsr) | Microsoft 生态合集 | **合集：替代 471–482。** 汇总所列账户、办公、会议、网盘、工具、商店、Xbox、更新与通用服务；与成员二选一。Microsoft Copilot、GitHub 和 GitHub Copilot 仍独立，不把多租户 Azure 或 Akamai 整段归入 | [订阅地址](https://raw.githubusercontent.com/LuckyLight6/loon-rules/main/rules/470-microsoft-all.lsr) |

### 13.2 Microsoft 产品细分

| 序号 | 英文名称 | 中文名称 | 用途与选择 | 订阅地址 |
|---:|---|---|---|---|
| 471 | [microsoft-vscode](../rules/471-microsoft-vscode.lsr) | Microsoft Visual Studio Code | 编辑器、更新、专用资源和设置同步；共用 Marketplace 与 Visual Studio 依赖下载归 482，GitHub 文件归 300，Copilot 归 106。实验和崩溃统计不按核心入口收录 | [订阅地址](https://raw.githubusercontent.com/LuckyLight6/loon-rules/main/rules/471-microsoft-vscode.lsr) |
| 472 | [microsoft-power-bi](../rules/472-microsoft-power-bi.lsr) | Microsoft Power BI | 报表服务的专用域；Microsoft 登录仍由账户规则处理 | [订阅地址](https://raw.githubusercontent.com/LuckyLight6/loon-rules/main/rules/472-microsoft-power-bi.lsr) |
| 473 | [microsoft-account-authentication](../rules/473-microsoft-account-authentication.lsr) | Microsoft 个人账户与 Entra 登录 | 只收账号管理、共享登录与 Entra 身份主机；不把整个 microsoftonline.com 或 Microsoft Graph 当认证 | [订阅地址](https://raw.githubusercontent.com/LuckyLight6/loon-rules/main/rules/473-microsoft-account-authentication.lsr) |
| 474 | [microsoft-outlook-mail](../rules/474-microsoft-outlook-mail.lsr) | Outlook 与 Exchange Online 邮箱入口 | 个人和工作邮箱、邮件协议与 Outlook 移动客户端分别按官方服务行提取。共享 Entra 登录独立，不展开租户占位字段，不采用同页 IP | [订阅地址](https://raw.githubusercontent.com/LuckyLight6/loon-rules/main/rules/474-microsoft-outlook-mail.lsr) |
| 475 | [microsoft-teams-meetings](../rules/475-microsoft-teams-meetings.lsr) | Teams 会议及 Skype for Business 共用通信入口 | 专用产品域和官方通信媒体网段先匹配；不扩到全部 Microsoft IP。Lync 与部分媒体为共用通信服务，不能凭相同入口区分发起应用 | [订阅地址](https://raw.githubusercontent.com/LuckyLight6/loon-rules/main/rules/475-microsoft-teams-meetings.lsr) |
| 476 | [microsoft-files-and-sharepoint](../rules/476-microsoft-files-and-sharepoint.lsr) | OneDrive 与 SharePoint 文件与同步 | 仅文件产品的专用后缀，去掉 onedrive/skydrive 关键词；共享登录由账号专项处理 | [订阅地址](https://raw.githubusercontent.com/LuckyLight6/loon-rules/main/rules/476-microsoft-files-and-sharepoint.lsr) |
| 477 | [microsoft-windows-update-services](../rules/477-microsoft-windows-update-services.lsr) | Windows Update 检查与传递优化协调 | 更新服务、传递优化控制和内容调度，不把整个 Windows 或 Microsoft 后缀当更新 | [订阅地址](https://raw.githubusercontent.com/LuckyLight6/loon-rules/main/rules/477-microsoft-windows-update-services.lsr) |
| 478 | [microsoft-update-and-store-downloads](../rules/478-microsoft-update-and-store-downloads.lsr) | Windows 更新和 Microsoft Store 已知内容下载 | 仅已知下载和精确 CDN 别名，不扩到整个 delivery.mp.microsoft.com。大文件确认可用后直连 | [订阅地址](https://raw.githubusercontent.com/LuckyLight6/loon-rules/main/rules/478-microsoft-update-and-store-downloads.lsr) |
| 479 | [microsoft-store-services](../rules/479-microsoft-store-services.lsr) | Microsoft Store 商店目录与加载 | 商店前端和目录请求；系统更新控制、账户、许可和文件下载各自匹配 | [订阅地址](https://raw.githubusercontent.com/LuckyLight6/loon-rules/main/rules/479-microsoft-store-services.lsr) |
| 480 | [microsoft-office-downloads](../rules/480-microsoft-office-downloads.lsr) | Microsoft Office 安装与更新下载 | Office 下载主机及其已核对的精确别名；账号、激活与办公 Web 应用不算下载 | [订阅地址](https://raw.githubusercontent.com/LuckyLight6/loon-rules/main/rules/480-microsoft-office-downloads.lsr) |
| 481 | [microsoft-xbox-services](../rules/481-microsoft-xbox-services.lsr) | Xbox Live 已知登录与服务端点 | 明确的 Xbox 令牌与服务、资产主机；不代表全部游戏下载、语音、联机流量均可按域名识别 | [订阅地址](https://raw.githubusercontent.com/LuckyLight6/loon-rules/main/rules/481-microsoft-xbox-services.lsr) |

### 13.3 Microsoft 共用平台

| 序号 | 英文名称 | 中文名称 | 用途与选择 | 订阅地址 |
|---:|---|---|---|---|
| 482 | [microsoft-platform-services](../rules/482-microsoft-platform-services.lsr) | Microsoft 通用客户端和共享服务兜底 | 保留 Microsoft 通用服务和官方列出的 Azure 控制端点；按官方云定义排除租户后缀及会覆盖租户的父域。Graph 留在这里，不把多租户托管平台或共享 Akamai 整段接管 | [订阅地址](https://raw.githubusercontent.com/LuckyLight6/loon-rules/main/rules/482-microsoft-platform-services.lsr) |

## 14 AI 服务（国内版）

国产产品可用国内版合集或成员；海外产品的中国区 API 单列，国际入口仍在前面的 AI 章节，不按厂商或顶级域名混用出口

### 14.1 国产 AI · 国内版合集

| 序号 | 英文名称 | 中文名称 | 用途与选择 | 订阅地址 |
|---:|---|---|---|---|
| 500 | [ai-cn-all](../rules/500-ai-cn-all.lsr) | 国产 AI 国内版合集 | **合集：替代 501–515。** 由各产品专表合并生成；统一选出口时用此表，按厂商选出口则用成员，不同时订阅 | [订阅地址](https://raw.githubusercontent.com/LuckyLight6/loon-rules/main/rules/500-ai-cn-all.lsr) |

### 14.2 国产 AI · 国内版产品细分

| 序号 | 英文名称 | 中文名称 | 用途与选择 | 订阅地址 |
|---:|---|---|---|---|
| 501 | [qwen-mainland](../rules/501-qwen-mainland.lsr) | 阿里千问与百炼 · 国内入口 | 按已核实的国内产品入口生成；同一产品的网页、API 与附件不按功能拆开，共用云平台不收整域 | [订阅地址](https://raw.githubusercontent.com/LuckyLight6/loon-rules/main/rules/501-qwen-mainland.lsr) |
| 502 | [kimi-mainland](../rules/502-kimi-mainland.lsr) | 月之暗面 Kimi · 国内入口 | 按已核实的国内产品入口生成；同一产品的网页、API 与附件不按功能拆开，共用云平台不收整域 | [订阅地址](https://raw.githubusercontent.com/LuckyLight6/loon-rules/main/rules/502-kimi-mainland.lsr) |
| 503 | [zhipu-mainland](../rules/503-zhipu-mainland.lsr) | 智谱 · 国内入口 | 按已核实的国内产品入口生成；同一产品的网页、API 与附件不按功能拆开，共用云平台不收整域 | [订阅地址](https://raw.githubusercontent.com/LuckyLight6/loon-rules/main/rules/503-zhipu-mainland.lsr) |
| 504 | [minimax-mainland](../rules/504-minimax-mainland.lsr) | MiniMax 与海螺 · 国内入口 | 按已核实的国内产品入口生成；同一产品的网页、API 与附件不按功能拆开，共用云平台不收整域 | [订阅地址](https://raw.githubusercontent.com/LuckyLight6/loon-rules/main/rules/504-minimax-mainland.lsr) |
| 505 | [bytedance-mainland](../rules/505-bytedance-mainland.lsr) | 字节豆包、扣子与模型平台 · 国内入口 | 按已核实的国内产品入口生成；同一产品的网页、API 与附件不按功能拆开，共用云平台不收整域 | [订阅地址](https://raw.githubusercontent.com/LuckyLight6/loon-rules/main/rules/505-bytedance-mainland.lsr) |
| 506 | [siliconflow-mainland](../rules/506-siliconflow-mainland.lsr) | 硅基流动 · 国内入口 | 读取官方指南的 SDK API 配置与 API 密钥控制台链接，只生成精确主机；国内版与国际版分别读取，不接管整家云平台 | [订阅地址](https://raw.githubusercontent.com/LuckyLight6/loon-rules/main/rules/506-siliconflow-mainland.lsr) |
| 507 | [tencent-mainland](../rules/507-tencent-mainland.lsr) | 腾讯混元、元宝与 TokenHub · 国内入口 | 按已核实的国内产品入口生成；同一产品的网页、API 与附件不按功能拆开，共用云平台不收整域 | [订阅地址](https://raw.githubusercontent.com/LuckyLight6/loon-rules/main/rules/507-tencent-mainland.lsr) |
| 508 | [deepseek-mainland](../rules/508-deepseek-mainland.lsr) | DeepSeek · 国内入口 | 按已核实的国内产品入口生成；同一产品的网页、API 与附件不按功能拆开，共用云平台不收整域 | [订阅地址](https://raw.githubusercontent.com/LuckyLight6/loon-rules/main/rules/508-deepseek-mainland.lsr) |
| 509 | [baidu-mainland](../rules/509-baidu-mainland.lsr) | 百度文心与千帆 | 文心门户、文心一言入口与千帆 API 按产品来源提取，不收整个百度、百度云或共用账号域 | [订阅地址](https://raw.githubusercontent.com/LuckyLight6/loon-rules/main/rules/509-baidu-mainland.lsr) |
| 510 | [iflytek-mainland](../rules/510-iflytek-mainland.lsr) | 讯飞星火 · 国内入口 | 按已核实的国内产品入口生成；同一产品的网页、API 与附件不按功能拆开，共用云平台不收整域 | [订阅地址](https://raw.githubusercontent.com/LuckyLight6/loon-rules/main/rules/510-iflytek-mainland.lsr) |
| 511 | [liblib-mainland](../rules/511-liblib-mainland.lsr) | 哩布哩布 · 国内入口 | 哩布门户、官方 API 请求示例与页面明确声明的专用资源主机；不收集统计脚本、普通链接或整个共享云 | [订阅地址](https://raw.githubusercontent.com/LuckyLight6/loon-rules/main/rules/511-liblib-mainland.lsr) |
| 512 | [baichuan-mainland](../rules/512-baichuan-mainland.lsr) | 百川智能 · 国内入口 | 按已核实的国内产品入口生成；同一产品的网页、API 与附件不按功能拆开，共用云平台不收整域 | [订阅地址](https://raw.githubusercontent.com/LuckyLight6/loon-rules/main/rules/512-baichuan-mainland.lsr) |
| 513 | [lingyi-mainland](../rules/513-lingyi-mainland.lsr) | 零一万物 · 国内入口 | 按已核实的国内产品入口生成；同一产品的网页、API 与附件不按功能拆开，共用云平台不收整域 | [订阅地址](https://raw.githubusercontent.com/LuckyLight6/loon-rules/main/rules/513-lingyi-mainland.lsr) |
| 514 | [stepfun-mainland](../rules/514-stepfun-mainland.lsr) | 阶跃星辰 · 国内入口 | 按已核实的国内产品入口生成；同一产品的网页、API 与附件不按功能拆开，共用云平台不收整域 | [订阅地址](https://raw.githubusercontent.com/LuckyLight6/loon-rules/main/rules/514-stepfun-mainland.lsr) |
| 515 | [sensetime-mainland](../rules/515-sensetime-mainland.lsr) | 商汤日日新 · 国内入口 | 按已核实的国内产品入口生成；同一产品的网页、API 与附件不按功能拆开，共用云平台不收整域 | [订阅地址](https://raw.githubusercontent.com/LuckyLight6/loon-rules/main/rules/515-sensetime-mainland.lsr) |

### 14.3 海外产品的中国区入口

| 序号 | 英文名称 | 中文名称 | 用途与选择 | 订阅地址 |
|---:|---|---|---|---|
| 516 | [jetbrains-ai-mainland](../rules/516-jetbrains-ai-mainland.lsr) | JetBrains AI · 中国区 API | 只采用官方明确标注 for China 的 API 主机；不并入国产 AI 合集，不按 .cn 后缀推断其它服务或地区 | [订阅地址](https://raw.githubusercontent.com/LuckyLight6/loon-rules/main/rules/516-jetbrains-ai-mainland.lsr) |

## 15 开发（国内）

### 15.1 代码托管与构建

| 序号 | 英文名称 | 中文名称 | 用途与选择 | 订阅地址 |
|---:|---|---|---|---|
| 530 | [gitee-hosting](../rules/530-gitee-hosting.lsr) | Gitee 码云 | 公共代码托管；不收自建服务或用户 Pages | [订阅地址](https://raw.githubusercontent.com/LuckyLight6/loon-rules/main/rules/530-gitee-hosting.lsr) |
| 531 | [coding-platform](../rules/531-coding-platform.lsr) | 腾讯 CODING | 托管和构建平台；不接管构建任务访问的其他包源 | [订阅地址](https://raw.githubusercontent.com/LuckyLight6/loon-rules/main/rules/531-coding-platform.lsr) |
| 532 | [gitcode-hosting](../rules/532-gitcode-hosting.lsr) | GitCode | GitCode 公共站；不把国内其他开发平台并入 | [订阅地址](https://raw.githubusercontent.com/LuckyLight6/loon-rules/main/rules/532-gitcode-hosting.lsr) |

### 15.2 国内软件镜像

| 序号 | 英文名称 | 中文名称 | 用途与选择 | 订阅地址 |
|---:|---|---|---|---|
| 533 | [npmmirror-registry](../rules/533-npmmirror-registry.lsr) | npmmirror 国内镜像 | npm 镜像与二进制镜像；不会替 npm 客户端修改源 | [订阅地址](https://raw.githubusercontent.com/LuckyLight6/loon-rules/main/rules/533-npmmirror-registry.lsr) |
| 534 | [tuna-mirrors](../rules/534-tuna-mirrors.lsr) | 清华 TUNA 开源镜像 | 只收镜像站与 PyPI 镜像，不接管校园网络 | [订阅地址](https://raw.githubusercontent.com/LuckyLight6/loon-rules/main/rules/534-tuna-mirrors.lsr) |

## 16 通讯与社交（国内及两版共用）

| 序号 | 英文名称 | 中文名称 | 用途与选择 | 订阅地址 |
|---:|---|---|---|---|
| 550 | [wechat-shared-and-mainland](../rules/550-wechat-shared-and-mainland.lsr) | 微信国内及两版共用登录、消息与支付 | 限定微信专用域及明确 qq.com、腾讯云主机，不将腾讯 ASN 或整个 QQ 判作微信 | [订阅地址](https://raw.githubusercontent.com/LuckyLight6/loon-rules/main/rules/550-wechat-shared-and-mainland.lsr) |
| 551 | [dingtalk-public](../rules/551-dingtalk-public.lsr) | 钉钉公共服务 | 只匹配公共钉钉域；自建单点登录、专网和第三方企业应用不在内 | [订阅地址](https://raw.githubusercontent.com/LuckyLight6/loon-rules/main/rules/551-dingtalk-public.lsr) |
| 552 | [douban-community](../rules/552-douban-community.lsr) | 豆瓣 | 社区与图片；不按域名推断用户所在地区 | [订阅地址](https://raw.githubusercontent.com/LuckyLight6/loon-rules/main/rules/552-douban-community.lsr) |
| 553 | [weibo-social](../rules/553-weibo-social.lsr) | 微博 | 微博自己的站点与分发域，包括同域地区子站；新浪与微博共用的图片域另列，不按页面语言判断出口 | [订阅地址](https://raw.githubusercontent.com/LuckyLight6/loon-rules/main/rules/553-weibo-social.lsr) |

## 17 支付（国内）

| 序号 | 英文名称 | 中文名称 | 用途与选择 | 订阅地址 |
|---:|---|---|---|---|
| 570 | [alipay-mainland-payments](../rules/570-alipay-mainland-payments.lsr) | 支付宝国内账户支付和静态资源 | 不把 AlipayHK、Alipay+、第三方账户或整个阿里云归为国内支付宝 | [订阅地址](https://raw.githubusercontent.com/LuckyLight6/loon-rules/main/rules/570-alipay-mainland-payments.lsr) |
| 571 | [unionpay-mainland](../rules/571-unionpay-mainland.lsr) | 银联、云闪付国内服务 | 国内服务入口；不把银联国际站按国内支付匹配 | [订阅地址](https://raw.githubusercontent.com/LuckyLight6/loon-rules/main/rules/571-unionpay-mainland.lsr) |

## 18 媒体（国内）

### 18.1 视频平台

| 序号 | 英文名称 | 中文名称 | 用途与选择 | 订阅地址 |
|---:|---|---|---|---|
| 590 | [bilibili-mainland-video](../rules/590-bilibili-mainland-video.lsr) | 哔哩哔哩中国站视频与图片 | 保留国内平台及常用内容交付；国际版专域不混入，API/CDN 共用部分不能按国家强行拆分 | [订阅地址](https://raw.githubusercontent.com/LuckyLight6/loon-rules/main/rules/590-bilibili-mainland-video.lsr) |
| 591 | [douyin-mainland-video](../rules/591-douyin-mainland-video.lsr) | 抖音中国版短视频、直播、图片与素材 | 只取抖音专有域和投放到该产品的 CDN；不纳入 TikTok、今日头条或整个字节基础设施 | [订阅地址](https://raw.githubusercontent.com/LuckyLight6/loon-rules/main/rules/591-douyin-mainland-video.lsr) |
| 592 | [iqiyi-mainland](../rules/592-iqiyi-mainland.lsr) | 爱奇艺国内版 | 国内版与专用素材；国际版 iq.com 不在内 | [订阅地址](https://raw.githubusercontent.com/LuckyLight6/loon-rules/main/rules/592-iqiyi-mainland.lsr) |
| 593 | [youku-video](../rules/593-youku-video.lsr) | 优酷国内站 | 只认国内站及专用素材，不收国际站、整个阿里 CDN | [订阅地址](https://raw.githubusercontent.com/LuckyLight6/loon-rules/main/rules/593-youku-video.lsr) |

### 18.2 音乐平台

| 序号 | 英文名称 | 中文名称 | 用途与选择 | 订阅地址 |
|---:|---|---|---|---|
| 594 | [qq-music](../rules/594-qq-music.lsr) | QQ 音乐 | 只收音乐专用主机；不接管 QQ、微信或整个腾讯平台 | [订阅地址](https://raw.githubusercontent.com/LuckyLight6/loon-rules/main/rules/594-qq-music.lsr) |
| 595 | [kugou-music](../rules/595-kugou-music.lsr) | 酷狗音乐 | 酷狗产品和专用素材，与 QQ 音乐和通用腾讯服务分开 | [订阅地址](https://raw.githubusercontent.com/LuckyLight6/loon-rules/main/rules/595-kugou-music.lsr) |
| 596 | [kuaishou-video](../rules/596-kuaishou-video.lsr) | 快手 | 国内产品和专用素材；Kwai 国际版不按同一品牌并入 | [订阅地址](https://raw.githubusercontent.com/LuckyLight6/loon-rules/main/rules/596-kuaishou-video.lsr) |

## 19 游戏（国内）

| 序号 | 英文名称 | 中文名称 | 用途与选择 | 订阅地址 |
|---:|---|---|---|---|
| 610 | [steam-mainland-downloads](../rules/610-steam-mainland-downloads.lsr) | Steam 中国下载镜像与蒸汽平台内容 | 只收已确认的国内下载镜像；游戏账户、商店和社区归 410。不按第三方 CDN 整域判断 | [订阅地址](https://raw.githubusercontent.com/LuckyLight6/loon-rules/main/rules/610-steam-mainland-downloads.lsr) |
| 611 | [mihoyo-mainland](../rules/611-mihoyo-mainland.lsr) | 米哈游国服与米游社 | 只选可区分的国服产品入口，不根据共享素材判断游戏区服 | [订阅地址](https://raw.githubusercontent.com/LuckyLight6/loon-rules/main/rules/611-mihoyo-mainland.lsr) |
| 612 | [wegame-mainland](../rules/612-wegame-mainland.lsr) | 腾讯 WeGame 国内平台 | 国内平台；不把 Tencent Games 的国际产品和整个 qq.com 直连 | [订阅地址](https://raw.githubusercontent.com/LuckyLight6/loon-rules/main/rules/612-wegame-mainland.lsr) |

## 20 购物与社区（国内）

| 序号 | 英文名称 | 中文名称 | 用途与选择 | 订阅地址 |
|---:|---|---|---|---|
| 630 | [taobao-and-xianyu-shopping](../rules/630-taobao-and-xianyu-shopping.lsr) | 淘宝、天猫、闲鱼购物与图片 | 只收国内消费平台及专用 CDN。不含 AliExpress、整个阿里云或支付宝 | [订阅地址](https://raw.githubusercontent.com/LuckyLight6/loon-rules/main/rules/630-taobao-and-xianyu-shopping.lsr) |
| 631 | [jingdong-shopping](../rules/631-jingdong-shopping.lsr) | 京东购物、账户与商品素材 | 不将整个京东云网络或金融产品一并转为购物匹配 | [订阅地址](https://raw.githubusercontent.com/LuckyLight6/loon-rules/main/rules/631-jingdong-shopping.lsr) |
| 632 | [xiaohongshu-community](../rules/632-xiaohongshu-community.lsr) | 小红书国内内容、社区及专用 CDN | 只收明确产品域；去掉共用风控，不把海外版或未知通用基础设施归入 | [订阅地址](https://raw.githubusercontent.com/LuckyLight6/loon-rules/main/rules/632-xiaohongshu-community.lsr) |
| 633 | [zhihu-community](../rules/633-zhihu-community.lsr) | 知乎 | 社区和图片域；明确的广告仍由前置拦截规则处理 | [订阅地址](https://raw.githubusercontent.com/LuckyLight6/loon-rules/main/rules/633-zhihu-community.lsr) |
| 634 | [railway-tickets](../rules/634-railway-tickets.lsr) | 铁路 12306 | 铁路售票、账户和专用服务。不把第三方支付网站归铁路 | [订阅地址](https://raw.githubusercontent.com/LuckyLight6/loon-rules/main/rules/634-railway-tickets.lsr) |
| 635 | [sina-shared-image-assets](../rules/635-sina-shared-image-assets.lsr) | 新浪与微博共用图片 | 新浪新闻、微博等服务共用的图片域，不代表微博专用；图片域下的广告仍按前置拦截规则处理 | [订阅地址](https://raw.githubusercontent.com/LuckyLight6/loon-rules/main/rules/635-sina-shared-image-assets.lsr) |

## 21 扩展广告与统计拦截

| 序号 | 英文名称 | 中文名称 | 用途与选择 | 订阅地址 |
|---:|---|---|---|---|
| 650 | [extended-ad-and-tracking](../rules/650-extended-ad-and-tracking.lsr) | 可选的扩展广告与统计拦截 | **可选。** 默认关闭。整域拦截需过滤表与 DNS 表共同支持；与已列网站同范围或会覆盖正常入口的规则让位，专用广告子域仍可拦截 | [订阅地址](https://raw.githubusercontent.com/LuckyLight6/loon-rules/main/rules/650-extended-ad-and-tracking.lsr) |

## 22 海外补充

具体产品先匹配，再补其他海外影音和受限站点；这两份分别选择影音策略和通用代理

| 序号 | 英文名称 | 中文名称 | 用途与选择 | 订阅地址 |
|---:|---|---|---|---|
| 670 | [overseas-media-extra](../rules/670-overseas-media-extra.lsr) | 其他海外影音 | 只补专项未覆盖的影音域名，交给海外影音策略；不按共享 IP、关键字或客户端名识别 | [订阅地址](https://raw.githubusercontent.com/LuckyLight6/loon-rules/main/rules/670-overseas-media-extra.lsr) |
| 675 | [overseas-sites-extra](../rules/675-overseas-sites-extra.lsr) | 其他海外网站与受限站点 | 合并已核对的海外与 GFW 域名，扣除已有专项，并排除国内来源冲突和共享基础设施 | [订阅地址](https://raw.githubusercontent.com/LuckyLight6/loon-rules/main/rules/675-overseas-sites-extra.lsr) |

## 23 国内补充

国内补充只保留一套：统一选路用 702，分开选路用 704、707、711；其余请求由 FINAL 处理

### 23.1 国内补充合集

| 序号 | 英文名称 | 中文名称 | 用途与选择 | 订阅地址 |
|---:|---|---|---|---|
| 702 | [mainland-routing-all](../rules/702-mainland-routing-all.lsr) | 国内兜底合集 | **合集：替代 704、707、711。** 将国内域名、网段和 GeoIP 交给同一策略时选本合集；需要分别控制时，用 704、707、711 替代。未命中域名仍可解析后按地址判断 | [订阅地址](https://raw.githubusercontent.com/LuckyLight6/loon-rules/main/rules/702-mainland-routing-all.lsr) |

### 23.2 国内补充细分

| 序号 | 英文名称 | 中文名称 | 用途与选择 | 订阅地址 |
|---:|---|---|---|---|
| 704 | [mainland-domains](../rules/704-mainland-domains.lsr) | 未由专项认领的国内域名补充 | 只补前面专项没有完整覆盖的域名；保留必要父域，不把内网管理名或已识别的国际入口归为国内 | [订阅地址](https://raw.githubusercontent.com/LuckyLight6/loon-rules/main/rules/704-mainland-domains.lsr) |
| 707 | [mainland-networks](../rules/707-mainland-networks.lsr) | 可按 IPv4 / IPv6 网段判断的国内地址 | 域名未命中时按目标地址查网段，排在 GeoIP 之前，不替代国内域名表。每轮整表与 APNIC 中国分配记录和运营商清单取共同支持的范围；证据不足的地址继续由后续规则判断，不据此认定所在地 | [订阅地址](https://raw.githubusercontent.com/LuckyLight6/loon-rules/main/rules/707-mainland-networks.lsr) |
| 711 | [mainland-geoip](../rules/711-mainland-geoip.lsr) | 设备 GeoIP 数据库中的中国大陆地址兜底 | 前面的域名和网段未命中时再用。允许为查地址触发解析；地区归属取决于 Loon 设备上的数据库 | [订阅地址](https://raw.githubusercontent.com/LuckyLight6/loon-rules/main/rules/711-mainland-geoip.lsr) |

产品专表已列在各业务下；统一出口用合集，分别选出口用其成员。[各组怎么选出口](routing.md) · [各类规则怎样更新](maintenance.md) · [参与维护](development.md)

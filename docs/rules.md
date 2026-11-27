# 规则订阅清单

## 选择应用与规则

先进入所用代理应用的目录，再按本页选择产品或合集。各应用共用分组、编号、来源和执行顺序；实际语法、兼容状态和订阅地址在各自目录中列出。

| 代理应用 | 下载目录 |
|---|---|
| Loon | [loon](../rules/loon/README.md) |
| Surge | [surge](../rules/surge/README.md) |
| Mihomo | [mihomo](../rules/mihomo/README.md) |
| Stash | [stash](../rules/stash/README.md) |
| Egern | [egern](../rules/egern/README.md) |
| Surfboard | [surfboard](../rules/surfboard/README.md) |
| Shadowrocket | [shadowrocket](../rules/shadowrocket/README.md) |
| Quantumult X | [quantumult-x](../rules/quantumult-x/README.md) |
| sing-box | [sing-box](../rules/sing-box/README.md) |
| V2Ray | [v2ray](../rules/v2ray/README.md) |

从上往下读，就是订阅的匹配顺序。只选自己要用的行，保持相对位置即可。序号和英文名称对应各应用中的同名规则文件，来源和正文更新时间可在文件或机器清单中查看。

同一出口可以用合集；要分别选出口，就用成员。合集和它列出的成员二选一。客户端刷新订阅通常只更新正文，已有订阅的位置和出口仍需在配置中核对。本地规则、插件或重写也可能先匹配。[客户端格式与限制](clients.md) · [检查实际命中](network-testing.md)

## 1 网络接入与局域网

| 序号 | 英文名称 | 中文名称 | 用途与选择 |
|---:|---|---|---|
| 0110 | <a id="rule-local-links-and-addresses"></a>`local-links-and-addresses` | 局域网名称、路由器、反查与保留地址 | 路由器和局域网名称优先，反查名称随地址范围生成；私网、VPN 和回环保留名称访问。链路本地、组播、保留及文档用地址只匹配已知目标 IP |
| 0120 | <a id="rule-local-no-resolve-alt"></a>`local-no-resolve-alt` | 局域网管理名与已知 IP：不为匹配触发 DNS | **可选。** 替代 0110，不同时订阅。保留全部管理名和网段；未知内网名称不能再靠这份表解析到私网后直连 |
| 0130 | <a id="rule-network-sign-in-and-probes"></a>`network-sign-in-and-probes` | 公共 Wi-Fi 登录、系统网络检查与必需安全连接 | 合并 captive 与 bootstrap；精确放行会被拦截源误判的 Apple 安全浏览令牌。不会直连整个系统服务或广告域 |
| 0140 | <a id="rule-tailscale-control-and-tailnet"></a>`tailscale-control-and-tailnet` | Tailscale 控制面、公开中继与 Tailnet 域名 | 保留专用控制域与 MagicDNS 后缀，并从官方公开 DERP 表读取中继主机。只取主机名，不采用节点 IP；CGNAT 和 ULA 仍由 0110 按用途处理 |
| 0150 | <a id="rule-ip-egress-checks"></a>`ip-egress-checks` | 查询当前公网出口：国内检测页、IPv4、IPv6 和双栈 API | 只收用途明确的查询主机，不接管 IP 资料站、DNS、STUN 或多用途网站。设为代理后，用这些主机查地址的 DDNS 客户端也会看到代理出口 |
| 0160 | <a id="rule-cloudflare-public-dns"></a>`cloudflare-public-dns` | Cloudflare 公共 DNS 与标准解析器地址 | 从官方标准解析器表读取单个公网地址，全部 no-resolve；不使用 Cloudflare 大段 IP，也不导入 Families 产品地址 |

## 2 按需启用的完整服务例外

### 2.1 New Relic 完整域名与必要遥测例外合集

| 序号 | 英文名称 | 中文名称 | 用途与选择 |
|---:|---|---|---|
| 0205 | <a id="rule-newrelic-service-all"></a>`newrelic-service-all` | New Relic 完整域名与必要遥测例外 | **合集：替代 3260。** 主动选用时优先于追踪拦截，完整覆盖官方所列公共域名、遥测与共享依赖。共享主机上的其他请求也随本表选路。目的IP另选3290，或改选0206；与3260及包含它的3000二选一。常规拦截本身不变，不纳入客户私有连接或整家云平台。 |

### 2.2 New Relic 域名、必要遥测与接收网络合集

| 序号 | 英文名称 | 中文名称 | 用途与选择 |
|---:|---|---|---|
| 0206 | <a id="rule-newrelic-service-and-networks-all"></a>`newrelic-service-and-networks-all` | New Relic 域名、必要遥测与接收网络合集 | **合集：替代 3260–3290。** 覆盖0205域名范围及3290公网目的IPv4/IPv6，主动选用时优先于追踪拦截。不能等价表达no-resolve的客户端会标记本组不可用，可使用0205域名方案。与0205、3260、3290或包含这些成员的合集二选一；不加入公共探测器专属出站地址、旧网段或客户VPC。 |

## 3 广告与隐私

### 3.1 广告与隐私

| 序号 | 英文名称 | 中文名称 | 用途与选择 |
|---:|---|---|---|
| 0210 | <a id="rule-apple-and-ai-privacy-exceptions"></a>`apple-and-ai-privacy-exceptions` | Apple 广告与 OpenAI 广告像素的已核实拒绝项 | **可选。** 单独可选，不属于 Apple 或 AI 合集。只拦明确广告入口，不能以大后缀替代 |
| 0220 | <a id="rule-general-ad-and-tracking"></a>`general-ad-and-tracking` | Repcz 广告与追踪拦截 | 新增广告域名须有过滤表与 DNS 表共同支持；保留仍获原来源支持的已审范围，保护业务必需入口；未经交叉确认的新 IP 不自动加入 |
| 0230 | <a id="rule-privacy-public-stun-endpoints"></a>`privacy-public-stun-endpoints` | 已公开的 STUN 主机，供选择性阻断 | **可选。** 仅两个精确主机，不拦 webrtc.org 或所有 stun.*。启用可能影响语音和会议；不能代替 WebRTC 或 DNS 出口检查 |

### 3.2 可选扩展广告与统计拦截

| 序号 | 英文名称 | 中文名称 | 用途与选择 |
|---:|---|---|---|
| 0240 | <a id="rule-extended-ad-and-tracking"></a>`extended-ad-and-tracking` | 可选的扩展广告与统计拦截 | **可选。** 默认关闭。整域拦截需过滤表与 DNS 表共同支持；与已列网站同范围或会覆盖正常入口的规则让位，专用广告子域仍可拦截 |

## 4 AI 服务（海外与国际版）

### 4.1 海外 AI 合集

| 序号 | 英文名称 | 中文名称 | 用途与选择 |
|---:|---|---|---|
| 1000 | <a id="rule-ai-overseas-all"></a>`ai-overseas-all` | 海外 AI 合集 | **合集：替代 1010、1020–1030、1035–1058、1060–1520、1531–1790。** 合并本类细分，以及 OpenAI、Copilot、Amazon Q 与 Kiro 官方网络清单列出的共享依赖。共享主机上的其他应用请求也会按本合集匹配；需分别选路时改用产品细分和共享服务规则，合集与成员二选一。 含官方所列GHE公共命名空间，同一空间内的其他企业请求也随本表选路；企业专用Azure依赖不从公共云父域推断。 |

### 4.2 海外 AI · 产品细分

| 序号 | 英文名称 | 中文名称 | 用途与选择 |
|---:|---|---|---|
| 1010 | <a id="rule-claude-connections"></a>`claude-connections` | Anthropic：Claude、Claude Code 与 API（登录、附件、MCP 和更新） | Claude 自有登录、API、MCP、附件、Artifact、更新及已核实的公开站点使用同一策略；网络地址只取官方入站章节和注册组织当前持有的 Anthropic ASN，使用 no-resolve；内部测试、外部 MCP、共享客服、验证、支付和遥测不整域归入 Claude |

### 4.3 ChatGPT、Codex、API 与官方共享依赖合集

| 序号 | 英文名称 | 中文名称 | 用途与选择 |
|---:|---|---|---|
| 1019 | <a id="rule-chatgpt-service-all"></a>`chatgpt-service-all` | ChatGPT、Codex、API 与官方共享依赖合集 | **合集：替代 1020。** 替代1020，包含官方网络清单中的 WorkOS、验证码、支付、支持和遥测接口；同一共享主机上的其他应用请求也随本表选路。与1000及1020二选一。 |

### 4.4 细分规则

| 序号 | 英文名称 | 中文名称 | 用途与选择 |
|---:|---|---|---|
| 1020 | <a id="rule-chatgpt-connections"></a>`chatgpt-connections` | ChatGPT、Codex、OpenAI API、语音信令与媒体连接 | ChatGPT、Codex、OpenAI API 与语音媒体的专用范围；需单份包含官方列出的共享登录、验证码、支付、支持与遥测接口时选1019，统一 AI 出口可选1000。共享主机不能按发起应用区分。 |
| 1030 | <a id="rule-gemini-connections"></a>`gemini-connections` | Gemini、AI Studio、NotebookLM、Google AI API 和专用 WebChannel | Google AI 自有入口跟随已核实的专用来源、官方 API 与文档身份更新；通用 Google 登录、下载、存储与 API 仍分开 |

### 4.5 Grokipedia 内容与登录合集

| 序号 | 英文名称 | 中文名称 | 用途与选择 |
|---:|---|---|---|
| 1031 | <a id="rule-grokipedia-service-all"></a>`grokipedia-service-all` | Grokipedia 内容与登录合集 | **合集：替代 1035、1050。** 替代所列产品和共用账号成员；与其他包含同一账号成员的服务合集互斥。多个服务统一出口可选1000，分别选路时使用内容细分和1035共用账号。 |

### 4.6 Grok、xAI API 与登录合集

| 序号 | 英文名称 | 中文名称 | 用途与选择 |
|---:|---|---|---|
| 1032 | <a id="rule-xai-service-all"></a>`xai-service-all` | Grok、xAI API 与登录合集 | **合集：替代 1035–1045。** 替代所列产品和共用账号成员，与其他包含同一账号成员的服务合集互斥。各应用目录内原1040-xai-connections是本组的同文兼容入口，保留原有登录覆盖；分别选路时使用1045内容与API、1035共用账号。 |

### 4.7 Cursor 编辑器、API 与登录合集

| 序号 | 英文名称 | 中文名称 | 用途与选择 |
|---:|---|---|---|
| 1033 | <a id="rule-cursor-service-all"></a>`cursor-service-all` | Cursor 编辑器、API 与登录合集 | **合集：替代 1035、1100。** 替代所列产品和共用账号成员；与其他包含同一账号成员的服务合集互斥。多个服务统一出口可选1000，分别选路时使用内容细分和1035共用账号。 |

### 4.8 细分规则

| 序号 | 英文名称 | 中文名称 | 用途与选择 |
|---:|---|---|---|
| 1035 | <a id="rule-grok-cursor-shared-authentication"></a>`grok-cursor-shared-authentication` | Grok、Cursor 与 Grokipedia 共用账号登录 | 从官方最小登录清单和网络用途表读取明确主机；仅合并不能按目的域名区分的共用认证，不接管 Grok 对话、Cursor 编辑器或百科内容。 |
| 1045 | <a id="rule-xai-connections"></a>`xai-connections` | Grok 对话、xAI 模型 API 与专用内容 | Grok 对话、xAI 模型 API 和专用内容；共用登录主机由前置1035优先匹配。单份覆盖服务及登录可选1032；已使用1040的订阅继续保留完整覆盖，分别选路时改用1045内容与1035登录。 |
| 1050 | <a id="rule-grokipedia-encyclopedia"></a>`grokipedia-encyclopedia` | Grokipedia AI 百科站点 | 百科页面与内容；共用登录主机由前置1035优先匹配。单份覆盖内容及登录可选1031。 |
| 1058 | <a id="rule-foundry-local-voice-models"></a>`foundry-local-voice-models` | Foundry Local 语音模型目录、区域 API 与下载 | Copilot CLI 与 App 的本地语音功能需要的模型目录、区域选择和下载；共享模型目录不能再按具体模型区分。Blob 只收官方明确的有限租户前缀，不收整个 Azure 云。 |

### 4.9 GitHub Copilot、认证、实验与语音模型合集

| 序号 | 英文名称 | 中文名称 | 用途与选择 |
|---:|---|---|---|
| 1059 | <a id="rule-github-copilot-service-all"></a>`github-copilot-service-all` | GitHub Copilot、认证、实验与语音模型合集 | **合集：替代 1058、1060。** 替代1058与1060，补入官方 GitHub.com 连接表的共享认证、资源、用户管理和实验接口；同一主机的其他 GitHub 请求也随本表选路。与1000及所列成员二选一，编辑器自身网络仍按所用编辑器处理。 含官方所列GHE公共命名空间，同一空间内的其他企业请求也随本表选路；企业专用Azure依赖不从公共云父域推断。 |

### 4.10 细分规则

| 序号 | 英文名称 | 中文名称 | 用途与选择 |
|---:|---|---|---|
| 1060 | <a id="rule-github-copilot-connections"></a>`github-copilot-connections` | GitHub Copilot：补全、对话、API 与专用附件 | Copilot 专用接口、实时连接、附件、报告与遥测，包含官方有限前缀的下载回落；需单份包含 GitHub 认证和共享实验接口时选1059。编辑器网络及其他共用服务按其实际用途处理。 |
| 1070 | <a id="rule-microsoft-copilot-connections"></a>`microsoft-copilot-connections` | Microsoft Copilot 个人版与工作版独立入口 | 只收自营 Copilot 门户；不吸收 Microsoft 通用登录、Outlook、Graph、Bing 或 GitHub Copilot |
| 1080 | <a id="rule-meta-ai-assistant"></a>`meta-ai-assistant` | Meta AI 助手、Llama 与专用内容入口 | 跟随 Meta AI、Llama 和专用用户内容／运行环境域名；Facebook、Instagram、WhatsApp、Muse 与共用登录另行处理 |
| 1090 | <a id="rule-muse-agent"></a>`muse-agent` | Muse 独立个人助手与其专用入口 | 只匹配 muse.ai；Meta AI 本站单独处理，不把 Meta 社交 App 或 Muse 连接到的第三方网站归进来 |
| 1100 | <a id="rule-cursor-editor-and-api"></a>`cursor-editor-and-api` | Cursor 客户端及专用接口 | 不把通用 GitHub 和云服务纳入 |
| 1110 | <a id="rule-perplexity-search-and-api"></a>`perplexity-search-and-api` | Perplexity 搜索、API 和专用内容入口 | 按租户主机区分，不代理整个第三方文件云 |
| 1120 | <a id="rule-poe-chat-and-api"></a>`poe-chat-and-api` | Poe 聊天与平台域名 | 不纳入底层模型提供商的共享接口 |
| 1130 | <a id="rule-mistral-model-services"></a>`mistral-model-services` | Mistral 平台专用域名 | 第三方推理平台按自己的入口归类 |
| 1140 | <a id="rule-groq-inference"></a>`groq-inference` | Groq 推理服务入口 | 与 Grok/xAI 无关 |
| 1150 | <a id="rule-cohere-model-services"></a>`cohere-model-services` | Cohere 的推理及平台域名 | 不因同一模型由其他云托管就把云整段纳入 |
| 1160 | <a id="rule-hugging-face-model-hub"></a>`hugging-face-model-hub` | Hugging Face 模型库与专用 CDN | 共享存储不整段代理 |
| 1170 | <a id="rule-devin-cloud-coding"></a>`devin-cloud-coding` | Devin 自有云编程入口 | 不覆盖它所访问的外部仓库 |
| 1180 | <a id="rule-elevenlabs-voice-and-api"></a>`elevenlabs-voice-and-api` | ElevenLabs 语音生成、WebSocket、文件与 MCP | 只收厂商专用根域，包含 API 与 ElevenLabs CDN，不扩到第三方语音或存储基础设施 |
| 1185 | <a id="rule-sonantic-voice-services"></a>`sonantic-voice-services` | Sonantic AI 语音平台 | 按产品用途读取语音平台主机，并跟随官方 Sonantic 入口链接；Spotify 音乐、共享云和广告分析不归本组 |
| 1190 | <a id="rule-midjourney-image-tools"></a>`midjourney-image-tools` | Midjourney 图像服务入口 | 不把 Discord 基础设施都交给它 |
| 1200 | <a id="rule-openrouter-gateway"></a>`openrouter-gateway` | OpenRouter 的模型网关入口 | 同一个网关不根据模型名称切流 |
| 1210 | <a id="rule-windsurf-editor-and-api"></a>`windsurf-editor-and-api` | Windsurf 和 Codeium 专用接口 | 不把公共托管平台当开发助手 |
| 1220 | <a id="rule-ai-com-agents"></a>`ai-com-agents` | ai.com 的个人 AI 代理 | ai.com 是独立服务，不归 ChatGPT 或 Claude；海外 AI 统一出口时可选择海外 AI 合集 |
| 1230 | <a id="rule-jetbrains-ai"></a>`jetbrains-ai` | JetBrains AI | AI 专用域和官方明确列出的海外后端；中国区 API 单列，IDE、账号和插件市场由 JetBrains IDE 规则处理，不认领共用配置服务 |
| 1240 | <a id="rule-amp-connections"></a>`amp-connections` | Amp 登录、线程 WebSocket、CLI 与官方运行环境 | 从当前官方网络允许列表读取，不复活已未列出的旧域名；代理须支持 WebSocket，第三方模型和用户访问的网站各自选路 |
| 1250 | <a id="rule-anythingllm-connections"></a>`anythingllm-connections` | AnythingLLM 官网与自营下载、云端入口 | 仅识别 AnythingLLM 自营产品域；本地推理、自建实例及连接的模型服务按各自地址处理，不代理整个共享存储平台 |
| 1260 | <a id="rule-fireworks-model-services"></a>`fireworks-model-services` | Fireworks 模型 API、产品门户与自营资源 | 依据当前官方 API 示例识别 Fireworks 自营域，不把 OpenAI SDK 或第三方存储改归 Fireworks |
| 1270 | <a id="rule-opencode-connections"></a>`opencode-connections` | OpenCode 与 Go 网关 | 只读已登记提供商的服务字段；自营产品域按已核对范围补充，不把文档中的共享云或第三方链接一起归入。自建实例另按目标地址处理 |
| 1280 | <a id="rule-kilo-connections"></a>`kilo-connections` | Kilo 编程助手与模型网关 | 只读已登记提供商的服务字段；自营产品域按已核对范围补充，不把文档中的共享云或第三方链接一起归入。自建实例另按目标地址处理 |
| 1290 | <a id="rule-cline-connections"></a>`cline-connections` | Cline 自营接入与账户 | 只读已登记提供商的服务字段；自营产品域按已核对范围补充，不把文档中的共享云或第三方链接一起归入。自建实例另按目标地址处理 |
| 1300 | <a id="rule-ollama-cloud"></a>`ollama-cloud` | Ollama Cloud 远程接口 | 只识别远程 Cloud 主机，本地 localhost 与内网 Ollama 不归入；同主机下载也可能跟随该出口，独立模型仓库和 CDN 不整段加入 |
| 1310 | <a id="rule-chutes-model-services"></a>`chutes-model-services` | Chutes 模型服务 | 只读已登记提供商的服务字段；自营产品域按已核对范围补充，不把文档中的共享云或第三方链接一起归入。自建实例另按目标地址处理 |
| 1320 | <a id="rule-bothub-model-services"></a>`bothub-model-services` | Bothub 模型网关 | 只读已登记提供商的服务字段；自营产品域按已核对范围补充，不把文档中的共享云或第三方链接一起归入。自建实例另按目标地址处理 |
| 1330 | <a id="rule-commandcode-connections"></a>`commandcode-connections` | CommandCode 编程与模型接口 | 只读已登记提供商的服务字段；自营产品域按已核对范围补充，不把文档中的共享云或第三方链接一起归入。自建实例另按目标地址处理 |
| 1340 | <a id="rule-stackit-model-services"></a>`stackit-model-services` | STACKIT AI Model Serving | 只读 AI Model Serving 的精确 API 主机，不认领整个 STACKIT 云或 onstackit.cloud |
| 1350 | <a id="rule-novita-model-services"></a>`novita-model-services` | Novita 模型服务 | 只读已登记提供商的服务字段；自营产品域按已核对范围补充，不把文档中的共享云或第三方链接一起归入。自建实例另按目标地址处理 |
| 1360 | <a id="rule-nebius-model-services"></a>`nebius-model-services` | Nebius Token Factory | 只读已登记提供商的服务字段；自营产品域按已核对范围补充，不把文档中的共享云或第三方链接一起归入。自建实例另按目标地址处理 |
| 1370 | <a id="rule-baseten-model-services"></a>`baseten-model-services` | Baseten 模型服务 | 只读已登记提供商的服务字段；自营产品域按已核对范围补充，不把文档中的共享云或第三方链接一起归入。自建实例另按目标地址处理 |
| 1380 | <a id="rule-deepinfra-model-services"></a>`deepinfra-model-services` | DeepInfra 模型服务 | 只读已登记提供商的服务字段；自营产品域按已核对范围补充，不把文档中的共享云或第三方链接一起归入。自建实例另按目标地址处理 |
| 1390 | <a id="rule-together-model-services"></a>`together-model-services` | Together AI 模型服务 | API 同时跟随官方当前和前一代 Python SDK 的默认入口，网站读取提供商目录；不从整个 GFW 合集筛选 API |
| 1400 | <a id="rule-cerebras-model-services"></a>`cerebras-model-services` | Cerebras 推理服务 | 只读已登记提供商的服务字段；自营产品域按已核对范围补充，不把文档中的共享云或第三方链接一起归入。自建实例另按目标地址处理 |
| 1410 | <a id="rule-replicate-model-services"></a>`replicate-model-services` | Replicate 模型 API 与结果文件 | 只从产品专表选取已核对的自营范围；共享云、第三方服务、进程名和用户自建地址不随产品整段归类 |
| 1420 | <a id="rule-runway-creative-tools"></a>`runway-creative-tools` | Runway 视频与创作服务 | 只从产品专表选取已核对的自营范围；共享云、第三方服务、进程名和用户自建地址不随产品整段归类 |
| 1430 | <a id="rule-stability-model-services"></a>`stability-model-services` | Stability AI 模型服务 | 只从产品专表选取已核对的自营范围；共享云、第三方服务、进程名和用户自建地址不随产品整段归类 |
| 1440 | <a id="rule-black-forest-model-services"></a>`black-forest-model-services` | Black Forest Labs 与 FLUX | 只从产品专表选取已核对的自营范围；共享云、第三方服务、进程名和用户自建地址不随产品整段归类 |
| 1450 | <a id="rule-replit-cloud-development"></a>`replit-cloud-development` | Replit 云端开发 | 自营账户、编辑与 API；共享托管后缀不整段收入，用户应用按实际目标另行识别 |
| 1460 | <a id="rule-augment-code-assistant"></a>`augment-code-assistant` | Augment Code 编程助手 | 只从产品专表选取已核对的自营范围；共享云、第三方服务、进程名和用户自建地址不随产品整段归类 |
| 1470 | <a id="rule-sourcegraph-code-and-cody"></a>`sourcegraph-code-and-cody` | Sourcegraph 与 Cody | Sourcegraph 官方站点、代码搜索与 Cody；旧 cody.dev 入口保留原来源依据，Amp 由自己的规则识别，不随旧列表混入 |
| 1480 | <a id="rule-continue-code-assistant"></a>`continue-code-assistant` | Continue 编程助手 | 只识别产品自营公网服务；本地推理、自建实例和用户选择的模型提供商按实际目标处理 |
| 1490 | <a id="rule-coderabbit-code-review"></a>`coderabbit-code-review` | CodeRabbit 代码审查 | 只从产品专表选取已核对的自营范围；共享云、第三方服务、进程名和用户自建地址不随产品整段归类 |
| 1500 | <a id="rule-tabnine-code-assistant"></a>`tabnine-code-assistant` | Tabnine 编程助手 | 只从产品专表选取已核对的自营范围；共享云、第三方服务、进程名和用户自建地址不随产品整段归类 |
| 1510 | <a id="rule-factory-coding-agents"></a>`factory-coding-agents` | Factory 编程代理 | 只从产品专表选取已核对的自营范围；共享云、第三方服务、进程名和用户自建地址不随产品整段归类 |
| 1520 | <a id="rule-zed-editor-and-ai"></a>`zed-editor-and-ai` | Zed 编辑器与自营 AI | 只从产品专表选取已核对的自营范围；共享云、第三方服务、进程名和用户自建地址不随产品整段归类 |

### 4.11 Kiro 编程、个人登录与依赖合集

| 序号 | 英文名称 | 中文名称 | 用途与选择 |
|---:|---|---|---|
| 1526 | <a id="rule-kiro-service-all"></a>`kiro-service-all` | Kiro 编程、个人登录与依赖合集 | **合集：替代 1531–1535。** 包含Kiro自有入口、1531共用API、官方个人登录与验证码、Stripe计费及插件/Powers依赖；共享主机上的其他应用请求也随本表选路。本组与细分或其他含1531的合集二选一。各应用目录内原1530入口与本组合文，保留原订阅覆盖；组织SSO和GovCloud旧Q端点仍在核实。 |

### 4.12 Amazon Q 编程、登录与上传合集

| 序号 | 英文名称 | 中文名称 | 用途与选择 |
|---:|---|---|---|
| 1527 | <a id="rule-amazon-q-service-all"></a>`amazon-q-service-all` | Amazon Q 编程、登录与上传合集 | **合集：替代 1531、1537–1539。** 合并Q功能API、1531共用API、代码审查与改写上传，以及官方网络用途表中的认证、工具分发和遥测依赖。profile与SSO地区分别按官方用途展开；共享身份和工具命名空间上的其他应用请求也会随本表选路。与细分或其他含1531的合集二选一。 |

### 4.13 细分规则

| 序号 | 英文名称 | 中文名称 | 用途与选择 |
|---:|---|---|---|
| 1531 | <a id="rule-amazon-q-kiro-shared-api"></a>`amazon-q-kiro-shared-api` | Amazon Q 与 Kiro 共用 API | 两个产品的官方网络清单同时列出的精确API；共用范围按完整用途表求交集。不能按目的域名区分调用产品；分别选路时单独配置本组，不接管其他AWS服务或API子域。 |
| 1535 | <a id="rule-kiro-code-assistant"></a>`kiro-code-assistant` | Kiro 自有入口与编程服务 | 保留社区专表的kiro.dev范围，并从官方完整Core用途表读取自有精确主机；与Amazon Q共用API交给1531。个人登录、计费、插件及共用身份依赖由1526合集带入；组织SSO与GovCloud旧客户端依赖仍需核实，不把AWS整个平台认作Kiro。 |
| 1537 | <a id="rule-amazon-q-developer-api"></a>`amazon-q-developer-api` | Amazon Q 功能与 IDE 集成 API | 官方features用途中的Q功能API及q-developer-标识的IDE集成端点；与Kiro共用的API交给1531。地区随官方profile说明和SDK联动；工具分发、身份、遥测及上传桶不归本组。 |
| 1538 | <a id="rule-amazon-q-code-reviews"></a>`amazon-q-code-reviews` | Amazon Q 代码审查上传 | 官方用途表明确列出的代码审查服务桶；每个URL与ARN核对后保留精确虚拟主机，不接管S3平台、用户桶或代码改写上传。 |
| 1539 | <a id="rule-amazon-q-code-transformations"></a>`amazon-q-code-transformations` | Amazon Q 代码改写上传 | 官方用途表明确列出的代码改写服务桶；每个URL与ARN核对后保留精确虚拟主机，不接管S3平台、用户桶或代码审查上传。 |
| 1540 | <a id="rule-bolt-app-builder"></a>`bolt-app-builder` | Bolt 应用构建 | 只从产品专表选取已核对的自营范围；共享云、第三方服务、进程名和用户自建地址不随产品整段归类 |
| 1550 | <a id="rule-lovable-app-builder"></a>`lovable-app-builder` | Lovable 应用构建 | 只从产品专表选取已核对的自营范围；共享云、第三方服务、进程名和用户自建地址不随产品整段归类 |
| 1560 | <a id="rule-v0-app-builder"></a>`v0-app-builder` | Vercel v0 应用构建 | 只从产品专表选取已核对的自营范围；共享云、第三方服务、进程名和用户自建地址不随产品整段归类 |
| 1570 | <a id="rule-genspark-connections"></a>`genspark-connections` | Genspark 搜索与代理 | 只从产品专表选取已核对的自营范围；共享云、第三方服务、进程名和用户自建地址不随产品整段归类 |
| 1580 | <a id="rule-jasper-marketing-ai"></a>`jasper-marketing-ai` | Jasper 营销 AI | 只从产品专表选取已核对的自营范围；共享云、第三方服务、进程名和用户自建地址不随产品整段归类 |
| 1590 | <a id="rule-gamma-presentations"></a>`gamma-presentations` | Gamma 演示与文档 | 只从产品专表选取已核对的自营范围；共享云、第三方服务、进程名和用户自建地址不随产品整段归类 |
| 1600 | <a id="rule-phind-search"></a>`phind-search` | Phind 搜索与问答 | 只从产品专表选取已核对的自营范围；共享云、第三方服务、进程名和用户自建地址不随产品整段归类 |
| 1610 | <a id="rule-inflection-and-pi"></a>`inflection-and-pi` | Inflection 与 Pi | 只从产品专表选取已核对的自营范围；共享云、第三方服务、进程名和用户自建地址不随产品整段归类 |
| 1620 | <a id="rule-h2o-model-services"></a>`h2o-model-services` | H2O AI 平台 | 只从产品专表选取已核对的自营范围；共享云、第三方服务、进程名和用户自建地址不随产品整段归类 |
| 1630 | <a id="rule-otter-meeting-assistant"></a>`otter-meeting-assistant` | Otter 会议助手 | 只从产品专表选取已核对的自营范围；共享云、第三方服务、进程名和用户自建地址不随产品整段归类 |
| 1640 | <a id="rule-descript-media-tools"></a>`descript-media-tools` | Descript 音视频编辑 | 只从产品专表选取已核对的自营范围；共享云、第三方服务、进程名和用户自建地址不随产品整段归类 |
| 1650 | <a id="rule-synthesia-video-tools"></a>`synthesia-video-tools` | Synthesia 视频生成 | 只从产品专表选取已核对的自营范围；共享云、第三方服务、进程名和用户自建地址不随产品整段归类 |
| 1660 | <a id="rule-luma-creative-tools"></a>`luma-creative-tools` | Luma 创作服务 | 只从产品专表选取已核对的自营范围；共享云、第三方服务、进程名和用户自建地址不随产品整段归类 |
| 1670 | <a id="rule-leonardo-image-tools"></a>`leonardo-image-tools` | Leonardo 图像生成 | 只从产品专表选取已核对的自营范围；共享云、第三方服务、进程名和用户自建地址不随产品整段归类 |
| 1680 | <a id="rule-pika-video-tools"></a>`pika-video-tools` | Pika 视频生成 | 只从产品专表选取已核对的自营范围；共享云、第三方服务、进程名和用户自建地址不随产品整段归类 |
| 1690 | <a id="rule-recraft-design-tools"></a>`recraft-design-tools` | Recraft 设计与图像 | 只从产品专表选取已核对的自营范围；共享云、第三方服务、进程名和用户自建地址不随产品整段归类 |
| 1700 | <a id="rule-udio-music-tools"></a>`udio-music-tools` | Udio 音乐生成 | 只从产品专表选取已核对的自营范围；共享云、第三方服务、进程名和用户自建地址不随产品整段归类 |
| 1705 | <a id="rule-suno-music-generation"></a>`suno-music-generation` | Suno AI 音乐生成、作品播放与下载 | 官网身份核对 Suno 当前域名和旧域别名，完整社区专用表核对范围；图片按实际请求主机补全并尊重既有供应商归属。第三方登录和支付按其依赖另行配置，不认领共用云平台或 ASN。 |
| 1710 | <a id="rule-duck-ai-chat"></a>`duck-ai-chat` | Duck.ai 对话 | 只从产品专表选取已核对的自营范围；共享云、第三方服务、进程名和用户自建地址不随产品整段归类 |
| 1720 | <a id="rule-langchain-agent-platform"></a>`langchain-agent-platform` | LangChain 与代理平台 | 只从产品专表选取已核对的自营范围；共享云、第三方服务、进程名和用户自建地址不随产品整段归类 |
| 1730 | <a id="rule-comfy-cloud-and-registry"></a>`comfy-cloud-and-registry` | Comfy 云端与组件目录 | 只识别产品自营公网服务；本地推理、自建实例和用户选择的模型提供商按实际目标处理 |
| 1740 | <a id="rule-lmstudio-product-services"></a>`lmstudio-product-services` | LM Studio 产品与下载 | 只识别产品自营公网服务；本地推理、自建实例和用户选择的模型提供商按实际目标处理 |
| 1750 | <a id="rule-crewai-agent-platform"></a>`crewai-agent-platform` | CrewAI 代理平台 | 只识别产品自营公网服务；本地推理、自建实例和用户选择的模型提供商按实际目标处理 |
| 1760 | <a id="rule-eigent-agent-services"></a>`eigent-agent-services` | Eigent 代理与协作 | 只识别产品自营公网服务；本地推理、自建实例和用户选择的模型提供商按实际目标处理 |
| 1770 | <a id="rule-manus-agent-services"></a>`manus-agent-services` | Manus 代理与文件 | 只从产品专表选取已核对的自营范围；共享云、第三方服务、进程名和用户自建地址不随产品整段归类 |
| 1780 | <a id="rule-dia-browser-services"></a>`dia-browser-services` | Dia 浏览器自营服务 | 只从产品专表选取已核对的自营范围；共享云、第三方服务、进程名和用户自建地址不随产品整段归类 |
| 1790 | <a id="rule-openclaw-product-services"></a>`openclaw-product-services` | OpenClaw 产品与发布服务 | 只识别产品自营公网服务；本地推理、自建实例和用户选择的模型提供商按实际目标处理 |

### 4.14 国产 AI 国际版合集

| 序号 | 英文名称 | 中文名称 | 用途与选择 |
|---:|---|---|---|
| 1800 | <a id="rule-ai-cn-international-all"></a>`ai-cn-international-all` | 国产 AI 国际版合集 | **合集：替代 1810–1920。** 合并本类已列细分范围，统一出口时使用；与成员二选一，细分仍可分别订阅 |

### 4.15 国产 AI · 国际版产品细分

| 序号 | 英文名称 | 中文名称 | 用途与选择 |
|---:|---|---|---|
| 1810 | <a id="rule-qwen-international"></a>`qwen-international` | 阿里千问与百炼 · 国际入口 | 按已核实的国际产品入口生成；同一产品的网页、API 与附件不按功能拆开，共用云平台不收整域 |
| 1820 | <a id="rule-kimi-international"></a>`kimi-international` | 月之暗面 Kimi · 国际入口 | 按已核实的国际产品入口生成；同一产品的网页、API 与附件不按功能拆开，共用云平台不收整域 |
| 1830 | <a id="rule-zhipu-international"></a>`zhipu-international` | 智谱 · 国际入口 | 按已核实的国际产品入口生成；同一产品的网页、API 与附件不按功能拆开，共用云平台不收整域 |
| 1840 | <a id="rule-minimax-international"></a>`minimax-international` | MiniMax 与海螺 · 国际入口 | 按已核实的国际产品入口生成；同一产品的网页、API 与附件不按功能拆开，共用云平台不收整域 |
| 1850 | <a id="rule-bytedance-international"></a>`bytedance-international` | 字节豆包、扣子与模型平台 · 国际入口 | 按已核实的国际产品入口生成；同一产品的网页、API 与附件不按功能拆开，共用云平台不收整域 |
| 1860 | <a id="rule-siliconflow-international"></a>`siliconflow-international` | 硅基流动 · 国际入口 | 读取官方指南的 SDK API 配置与 API 密钥控制台链接，只生成精确主机；国内版与国际版分别读取，不接管整家云平台 |
| 1870 | <a id="rule-tencent-international"></a>`tencent-international` | 腾讯混元、元宝与 TokenHub · 国际入口 | 按已核实的国际产品入口生成；同一产品的网页、API 与附件不按功能拆开，共用云平台不收整域 |
| 1880 | <a id="rule-stepfun-international"></a>`stepfun-international` | 阶跃星辰 StepFun · 国际入口 | 国际模型 API 与国际 Step Plan；国内 stepfun.com 继续独立，不按厂商合并两版 |
| 1890 | <a id="rule-xiaomi-international"></a>`xiaomi-international` | 小米 MiMo · 新加坡与欧洲计划 | 只读明确标注新加坡、欧洲计划的专用服务字段，不把整个 xiaomimimo.com 从国内或共用 API 接走 |
| 1900 | <a id="rule-youmind-international"></a>`youmind-international` | YouMind · 国际产品入口 | 只从产品专表选取已核对的自营范围；共享云、第三方服务、进程名和用户自建地址不随产品整段归类 |
| 1910 | <a id="rule-qoder-international"></a>`qoder-international` | Qoder 国际产品、自有 API 与插件市场 | 保留产品专表的qoder.com范围，并按官方完整网络元数据跟随自有域名及*.通配范围；qoder.com.cn中的Global端点属于国际产品，不按后缀误分。阿里云、验证码和外部插件市场等共享范围未并入，本表尚不等同完整服务依赖。服务端出站IP不作为客户端目的地址。 |
| 1920 | <a id="rule-lovart-international"></a>`lovart-international` | Lovart · 国际产品入口 | 只从产品专表选取已核对的自营范围；共享云、第三方服务、进程名和用户自建地址不随产品整段归类 |

## 5 Apple 生态

### 5.1 Apple 生态完整合集

| 序号 | 英文名称 | 中文名称 | 用途与选择 |
|---:|---|---|---|
| 2000 | <a id="rule-apple-all"></a>`apple-all` | Apple 生态完整合集 | **合集：替代 2020–2070、2090–2370。** 合并本类已列细分范围，统一出口时使用；与成员二选一，细分仍可分别订阅 |

### 5.2 Apple 海外功能合集

| 序号 | 英文名称 | 中文名称 | 用途与选择 |
|---:|---|---|---|
| 2010 | <a id="rule-apple-overseas-all"></a>`apple-overseas-all` | Apple 海外功能合集 | **合集：替代 2020–2060。** 合并本类已列细分范围，统一出口时使用；与成员二选一，细分仍可分别订阅 |

### 5.3 海外功能细分

| 序号 | 英文名称 | 中文名称 | 用途与选择 |
|---:|---|---|---|
| 2020 | <a id="rule-apple-intelligence-relays"></a>`apple-intelligence-relays` | Apple Intelligence 的 PCC 与系统 AI 扩展中继 | 按 Apple 官方明确用途提取精确主机；iCloud Private Relay、普通 Siri、独立 AI App 和模型下载分别处理。功能资格仍取决于设备、账户和地区 |
| 2030 | <a id="rule-apple-private-relay-connections"></a>`apple-private-relay-connections` | iCloud Private Relay（隐私中继）与 Apple DNS 别名 | 在 iCloud 同步前识别隐私中继；PCC 和系统 AI 扩展由 Apple Intelligence 规则处理，不包含整个 iCloud 或 Apple DNS 后缀 |
| 2040 | <a id="rule-apple-video-and-fitness"></a>`apple-video-and-fitness` | Apple TV／Fitness+ 的门户、播放控制与共用主机 | 中国大陆未提供对应订阅；入口默认选服务可用地区的代理。已识别 HLS 交给独立视频组，同一会话用一致出口 |
| 2050 | <a id="rule-apple-tv-video-delivery"></a>`apple-tv-video-delivery` | Apple TV 已识别的 HLS 视频交付 | 匹配已识别 HLS 主机。大陆网络默认与 TV 播放控制同一代理；可单独统计流量，不把其他 Apple CDN 一并代理 |
| 2060 | <a id="rule-apple-news-and-sports"></a>`apple-news-and-sports` | Apple News／News+、内容入口与 Apple Sports | 中国大陆未提供；默认选对应服务可用地区的代理，不纳入国内直连例外 |

### 5.4 APNs 推送

| 序号 | 英文名称 | 中文名称 | 用途与选择 |
|---:|---|---|---|
| 2070 | <a id="rule-apple-push-connection"></a>`apple-push-connection` | APNs 系统推送的域名与公开客户端网段 | 独立选择长连接出口。默认保留实测可用路径；直连丢通知时可只切此组对照。不能按 App 国别拆系统推送 |

### 5.5 Apple 普通服务合集

| 序号 | 英文名称 | 中文名称 | 用途与选择 |
|---:|---|---|---|
| 2080 | <a id="rule-apple-direct-all"></a>`apple-direct-all` | Apple 普通服务合集 | **合集：替代 2090–2370。** 合并本类已列细分范围，统一出口时使用；与成员二选一，细分仍可分别订阅 |

### 5.6 普通服务细分

| 序号 | 英文名称 | 中文名称 | 用途与选择 |
|---:|---|---|---|
| 2090 | <a id="rule-apple-account-authentication"></a>`apple-account-authentication` | 登录、GrandSlam、OAuth、账户恢复与 iCloud 账户控制 | 包括 GrandSlam 账户关联设备登记及 iCloud 的订阅、发件设置和配额分片；iCloud 文件、邮件内容与共享网关继续由同步和内容规则处理 |
| 2100 | <a id="rule-apple-app-and-device-verification"></a>`apple-app-and-device-verification` | 应用验证、App Attest、macOS 公证与设备身份验证 | 保留系统服务直连；共享 apple-cloudkit.com 不从此组抢走 |
| 2110 | <a id="rule-apple-wallet-payments"></a>`apple-wallet-payments` | Wallet 与 Apple Pay 已知支付入口 | 只收可追溯的精确主机。支付仍依赖账户、设备校验及商户；不吞 ca、Apple 全域或其他支付公司 |
| 2120 | <a id="rule-apple-testflight"></a>`apple-testflight` | TestFlight 测试版安装和分发 | 剔除整个 TestFlight 关键词；商店生产环境和系统 OTA 分开 |
| 2130 | <a id="rule-apple-store-transactions"></a>`apple-store-transactions` | App Store API、搜索与提示、购买与安装指令、Apple Books 商店 | 包括 iTunes 签名初始化、第三方市场安装入口和 Apple Books 门户。账户认证、App 下载和 TestFlight 分开，不包揽整个 itunes.apple.com |
| 2140 | <a id="rule-apple-app-package-downloads"></a>`apple-app-package-downloads` | App Store 安装包下载 | 只匹配已知安装包入口和别名，不把 mzstatic 整段算作安装包。TestFlight、购买、设备验证和系统更新各有专表 |
| 2150 | <a id="rule-apple-association-services"></a>`apple-association-services` | Apple 通用链接的域名验证 | 只匹配 Associated Domains 端点，不放开整个 Apple CDN |
| 2160 | <a id="rule-apple-find-my"></a>`apple-find-my` | Find My 设备与朋友查找的已识别入口 | 查找专用主机与已核对的分片模式先于 iCloud 共用域；定位信号由定位服务规则处理，共用 iCloud 网页、推送与静态素材不并入 |
| 2170 | <a id="rule-apple-location-services"></a>`apple-location-services` | 定位查询、地图配置与信号定位数据 | 定位服务与信号定位共用主机；Find My 由独立专表先匹配，账户、推送与 iCloud 文件各自处理 |
| 2180 | <a id="rule-apple-messaging-identity"></a>`apple-messaging-identity` | Apple IDS 共用身份、注册与查询服务 | 从 Apple 公开配置读取认证、注册、查询与资料入口；保留既有 IDS 父域补充，与定位和推送分开，不代替全部消息媒体或 FaceTime 中继 |
| 2190 | <a id="rule-apple-icloud-mainland"></a>`apple-icloud-mainland` | 中国大陆 iCloud 服务和内容专用域 | 只收官方标注的大陆服务域及 Apple DNS 委派的大陆内容域；不认为 Apple 账户、CloudKit 或共用域都在大陆 |
| 2200 | <a id="rule-apple-icloud-content-domains"></a>`apple-icloud-content-domains` | iCloud 通用内容域 | 仅匹配 icloud-content.com 内容域，能直连再直连。大陆专域另管；部分上传、备份仍使用共用服务 |
| 2210 | <a id="rule-apple-cloud-sync"></a>`apple-cloud-sync` | iCloud 通用服务、CloudKit、同步、邮件及 iWork | 认证、查找、Private Relay、确定的内容域及大陆服务分别匹配；通用域不能用来判断账户或存储国家 |
| 2220 | <a id="rule-apple-podcasts"></a>`apple-podcasts` | Apple 播客 | 识别播客目录，不把创作者自己托管的音频也归给 Apple |
| 2230 | <a id="rule-apple-music-and-radio"></a>`apple-music-and-radio` | Apple Music、广播及共用 API 与应用门户 | 保留 Music 门户、API 和不能据域名进一步切开的音乐视频流量；明确音频传输由 Apple Music 音频分发规则处理 |
| 2240 | <a id="rule-apple-music-audio-delivery"></a>`apple-music-audio-delivery` | Apple Music 已识别音频交付主机 | 社区资料中的明确音频传输主机，不包含 Music API、账户和整个 itunes.apple.com。缓存是否在大陆不能由域名推定 |
| 2250 | <a id="rule-apple-siri-and-search"></a>`apple-siri-and-search` | Siri 与 Spotlight 的专用域名 | Siri、听写和系统搜索可共用主机；未能按主机区分普通 Siri 与 Siri AI 时，保留独立策略供真机对照，不把所有 Siri 当 PCC |
| 2260 | <a id="rule-apple-update-control"></a>`apple-update-control` | 系统更新目录、检查、授权与登记 | 更新检查、签名授权、Beta 登记和运营商更新发现；反馈提交和二进制包体各有专表，不把整组当成匿名静态下载 |
| 2270 | <a id="rule-apple-update-downloads"></a>`apple-update-downloads` | 系统更新包与恢复内容下载 | 收系统恢复、更新包和运营商设置包及已核对的精确 DNS 别名。目录、激活和证书另管，不按整个 CDN 或地区推断 |
| 2280 | <a id="rule-apple-developer-portal"></a>`apple-developer-portal` | Apple Developer 门户 | 只认开发者门户；账户认证、App 公证和独立下载主机沿用各自规则 |
| 2290 | <a id="rule-apple-developer-downloads"></a>`apple-developer-downloads` | Xcode、Swift Playgrounds 和开发者组件的实际下载 | 开发下载与 App Store、OTA 和共享的 App 公证端点分开 |
| 2300 | <a id="rule-apple-mainland-delivery-aliases"></a>`apple-mainland-delivery-aliases` | 已核对的 Apple 大陆就近分发别名 | 只收明确标注 cn-lb 的精确别名。是否从本地边缘节点命中仍以 DNS 和请求日志为准；不能把备案域或公共 CNAME 当大陆独占 CDN |
| 2310 | <a id="rule-apple-shared-store-assets"></a>`apple-shared-store-assets` | Apple 商店与媒体共用的静态内容 | mzstatic 也承载图标、书籍和音乐内容，不能当成纯安装包；s.mzstatic.com 应先命中商店交易规则，静态图片别名不保证专供大陆 |
| 2320 | <a id="rule-apple-certificate-validation"></a>`apple-certificate-validation` | Apple 设备的证书状态和撤销检查 | 只用官方给出的证书端点及已知 Apple 主机别名，不扩到整个 DigiCert |
| 2330 | <a id="rule-apple-system-connectivity"></a>`apple-system-connectivity` | 设备引导、MDM、校时、系统 DNS 与公共素材 | 保留 eSIM、机构管理、校时和公共设备资源的系统路径；激活、设备证书登记与反馈诊断另有专表，不把本组称为匿名 CDN |
| 2340 | <a id="rule-apple-schoolwork-handouts"></a>`apple-schoolwork-handouts` | Apple Schoolwork 讲义与资料交付 | 官方明确归属 Schoolwork Handout 的主机；班级名册和设备验证另走共享服务 |
| 2350 | <a id="rule-apple-device-registration"></a>`apple-device-registration` | 设备激活与 APNs 证书登记门户 | 按 Apple 官方用途读取设备激活与证书请求；eSIM、校时、机构 MDM 和设备素材保留在系统联网组，不按主机名猜测身份用途 |
| 2360 | <a id="rule-apple-feedback-and-diagnostics"></a>`apple-feedback-and-diagnostics` | Feedback Assistant、错误报告与自愿诊断上传 | 只分流已有的反馈和诊断连接，不启用数据分享；诊断素材下载仍归系统联网，更新检查与包体分开 |
| 2370 | <a id="rule-apple-other-services"></a>`apple-other-services` | Apple 官网与尚未细分的通用服务 | 放在 Apple 细分之后，接住来源列出的 Apple 自有服务域；随完整域名来源补入，不另列一份根域白名单。细分先匹配；忽略上游进程和 IP 规则，不使用整个 17.0.0.0/8 |

## 6 开发（海外）

### 6.1 海外开发合集

| 序号 | 英文名称 | 中文名称 | 用途与选择 |
|---:|---|---|---|
| 3000 | <a id="rule-overseas-development-all"></a>`overseas-development-all` | 海外开发合集 | **合集：替代 3010–3260。** 合并本类已列细分范围，统一出口时使用；与成员二选一，细分仍可分别订阅。New Relic 目的网络单列 3290，需要包含遥测和完整依赖时使用 0205 或 0206。 GHE入站网络单列3295，GitHub域名与GHE网络可选3005。 |

### 6.2 GitHub 域名与 GHE 公网入站网络合集

| 序号 | 英文名称 | 中文名称 | 用途与选择 |
|---:|---|---|---|
| 3005 | <a id="rule-github-domains-and-ghe-ingress-all"></a>`github-domains-and-ghe-ingress-all` | GitHub 域名与 GHE 公网入站网络合集 | **合集：替代 3010、3295。** 合并3010已列域名和3295的GHE入站目的网络，与成员二选一；不能等价保留no-resolve的客户端不提供本组，可用3010域名方案。与包含3010的3000二选一。本组没有扩展普通GitHub.com IP或推断企业专用Azure依赖。 |

### 6.3 海外开发 · 产品细分

| 序号 | 英文名称 | 中文名称 | 用途与选择 |
|---:|---|---|---|
| 3010 | <a id="rule-github-code-and-packages"></a>`github-code-and-packages` | GitHub 代码、API、Actions 与 GHE 企业云域名 | 代码、API、Actions、软件包与 GHE 公共命名空间，包括企业内的 Pages。公共 github.io 网站托管另在8130，Copilot 先由AI专项匹配，npm公共仓库另有专表；GHE入站网络单列3295，域名与GHE网络可选3005。企业专用Azure存储和WebSocket主机依企业正式清单处理，不扩大到整家云平台。 |
| 3020 | <a id="rule-gitlab-hosting"></a>`gitlab-hosting` | GitLab.com | 仅 GitLab 公共托管平台；不接管自建 GitLab 或用户 Pages |
| 3030 | <a id="rule-bitbucket-hosting"></a>`bitbucket-hosting` | Atlassian Bitbucket | 代码托管与公共 API，不收整个 Atlassian、Jira 或用户站 |
| 3040 | <a id="rule-npm-registry"></a>`npm-registry` | npm 软件包 | 官方注册表和产品站；国内镜像单列 |
| 3050 | <a id="rule-maven-central"></a>`maven-central` | Maven Central | 只认默认依赖仓库，不把 apache.org 整域算作包下载 |
| 3060 | <a id="rule-pypi-packages"></a>`pypi-packages` | PyPI 软件包 | 官方 Python 包索引、文档、上传与文件下载；不包揽 pythonhosted.org 上的项目网站 |
| 3070 | <a id="rule-docker-hub"></a>`docker-hub` | Docker Hub | Docker Hub 登录、鉴权和镜像分发按官方用途筛选；不接管共享 Auth0、错误报告、Desktop 更新、Scout 或其他 Docker 产品 |
| 3075 | <a id="rule-docker-desktop-and-platform"></a>`docker-desktop-and-platform` | Docker Desktop、Scout、Offload、Hardened Images 与平台服务 | 官方用途表自动补入更新、API、诊断与平台主机；Hub 入口由前表处理，Auth0 和 Bugsnag 按共享供应商处理，不扩大 AWS 或 Cloudflare |
| 3080 | <a id="rule-rust-cargo"></a>`rust-cargo` | Rust、Cargo 与 crates.io | 软件包、工具链和文档；不包括私有 Cargo 注册表 |
| 3090 | <a id="rule-go-modules"></a>`go-modules` | Go 模块与工具链 | Go 项目、模块代理和校验服务；不扩到通用 Google APIs |
| 3100 | <a id="rule-jetbrains-ides"></a>`jetbrains-ides` | JetBrains IDE、授权与插件 | IDE、授权、插件市场与设置同步；官方用途表补全当前主机。AI 专用后端、中国区 AI API、Node.js 与 ACP 注册表分别匹配，不把整套依赖都归给 IDE |
| 3110 | <a id="rule-nodejs-runtime"></a>`nodejs-runtime` | Node.js 运行时与官方发行站 | 从官方站点身份确认独立根域，覆盖运行时发布、下载与文档；npm 仓库和国内镜像各自匹配，不含第三方包的网络请求 |
| 3120 | <a id="rule-agent-client-protocol"></a>`agent-client-protocol` | ACP 协议、文档与代理注册表 | 从 Agent Client Protocol 官方站点身份确认独立根域，覆盖 JetBrains 文档要求的注册表 CDN；具体代理的模型 API、GitHub 和 npm 不归本组 |
| 3130 | <a id="rule-workos-authentication"></a>`workos-authentication` | WorkOS 登录、企业认证与公共组件 | 识别 WorkOS 自有命名空间与已列组件，不把使用 WorkOS 的所有网站认作同一应用；外部身份提供方另行处理 |
| 3140 | <a id="rule-datadog-observability"></a>`datadog-observability` | Datadog 监控、日志与浏览器 SDK | 读取官方地区站点、浏览器接收端和 SDK 分发范围；各区域自动跟随表格更新，不把遥测说成 Claude 专用认证 |
| 3150 | <a id="rule-sentry-error-monitoring"></a>`sentry-error-monitoring` | Sentry 错误监控、API 与 SDK | Sentry 共享平台、地区 API 和 SDK 素材；不把整个平台认作任一接入应用 |
| 3160 | <a id="rule-statsig-feature-management"></a>`statsig-feature-management` | Statsig 功能开关、实验、配置与事件 API | 按官方服务清单跟随主机与专用存储租户；共享 DNS 另归解析器，不扩大到整个 Azure |
| 3170 | <a id="rule-fathom-web-analytics"></a>`fathom-web-analytics` | Fathom 网站访问统计 | Fathom 服务与自有统计脚本；客户自定义代理和网站不归本组，分类不代表免于用户选择的隐私拦截 |
| 3180 | <a id="rule-hcaptcha-verification"></a>`hcaptcha-verification` | hcaptcha 人机验证与服务状态 | 验证服务与已列状态站；不接管使用验证码的客户网站，未核实归属的其它产品不并入 |
| 3190 | <a id="rule-persona-identity-verification"></a>`persona-identity-verification` | Persona 身份、企业与年龄验证 | Persona 自有服务命名空间；官方嵌入文档确认范围，不把第三方商户或客户账号归给 Persona |
| 3200 | <a id="rule-yoti-identity-verification"></a>`yoti-identity-verification` | Yoti 数字身份与年龄验证 | Yoti 已确认的自有站点与子域；客户网站和未证实的相似域名不并入 |
| 3210 | <a id="rule-sift-fraud-prevention"></a>`sift-fraud-prevention` | Sift 反欺诈、设备与风险 API | Sift 自有站点、SDK 与旧品牌 API 命名空间；不接管使用风控服务的商户，不称为 Claude 自有认证 |
| 3220 | <a id="rule-auth0-identity-platform"></a>`auth0-identity-platform` | Auth0 身份认证与共享登录平台 | 供应商自有平台与共享客户端组件；已被前置产品专表识别的专用租户继续归原产品，不因被某个应用使用就整域算作该应用 |
| 3230 | <a id="rule-bugsnag-error-monitoring"></a>`bugsnag-error-monitoring` | Bugsnag 错误监控与会话报告 | 供应商自有平台与共享客户端组件；已被前置产品专表识别的专用租户继续归原产品，不因被某个应用使用就整域算作该应用 |
| 3240 | <a id="rule-backstage-developer-portal"></a>`backstage-developer-portal` | Backstage 开发者门户项目 | Backstage 项目网站与公开产品清单；用户自行部署的门户、GitHub 源码托管和 Spotify 音乐不归本组 |
| 3250 | <a id="rule-spotify-advertising-and-analytics"></a>`spotify-advertising-and-analytics` | Spotify 广告 API 与广告分析 | Ads API 及 Podsights／Spotify Ad Analytics 的控制台、统计和指定租户；分类不代表免于广告与隐私拦截，不接管整个 Spotify 或 Google 云 |
| 3260 | <a id="rule-newrelic-platform"></a>`newrelic-platform` | New Relic 官网、控制台与专用资源 | 识别官网、控制台与按用途确认的专用资源。nr-data.net遥测及共享依赖由0205域名服务例外承接，目的IP网络另在3290；不改常规追踪拦截。 |

### 6.4 海外开发服务的专用目的网络

| 序号 | 英文名称 | 中文名称 | 用途与选择 |
|---:|---|---|---|
| 3290 | <a id="rule-newrelic-ingest-networks"></a>`newrelic-ingest-networks` | New Relic 数据接收网络IPv4与IPv6 | 仅采用官方网页接收网段与JSON清单覆盖一致的公网目的地址，按no-resolve匹配；不加入探测器专属出站地址、已停用网络或客户VPC。可单用或选0206完整合集。 |
| 3295 | <a id="rule-github-enterprise-ingress-networks"></a>`github-enterprise-ingress-networks` | GitHub GHE 数据驻留公网入站网络 | 完整读取官方各地区入站和出站列，仅生成入站目的网段；网页与官方原始文档的全部用途范围须一致，按no-resolve匹配。普通GitHub.com IP、服务器出站和客户VPC不属于本表。 |

## 7 通讯与社交（海外）

### 7.1 海外通讯与社交合集

| 序号 | 英文名称 | 中文名称 | 用途与选择 |
|---:|---|---|---|
| 3300 | <a id="rule-overseas-social-all"></a>`overseas-social-all` | 海外通讯与社交合集 | **合集：替代 3310–3480。** 合并本类已列细分范围，统一出口时使用；与成员二选一，细分仍可分别订阅 |

### 7.2 海外通讯与社交 · 产品细分

| 序号 | 英文名称 | 中文名称 | 用途与选择 |
|---:|---|---|---|
| 3310 | <a id="rule-telegram-messaging"></a>`telegram-messaging` | Telegram 通讯、文件与官方关联工具 | 消息、文件、评论工具与官方内容主机；不把外部客户端、通用链接白名单或 TON、Fragment 等其他产品并入；官方 CIDR 与注册组织持有的 ASN 只匹配已有目标 IP，使用 no-resolve |
| 3320 | <a id="rule-discord-messaging-and-voice"></a>`discord-messaging-and-voice` | Discord 通讯、语音及自营服务 | 通讯、语音、附件、开发入口及相关自营服务；Activities 第三方应用代理另行匹配。未使用的候选别名不自动新增，其他来源仍支持的已有入口保留；共享云与客服平台只匹配专用主机 |
| 3330 | <a id="rule-signal-messenger"></a>`signal-messenger` | Signal 消息、通话、贴纸、群组与用户名链接 | 按官方网络说明生成当前客户端入口；不将第三方代理、公共中继或未确认的历史域名并入 |
| 3340 | <a id="rule-line-messenger"></a>`line-messenger` | LINE | LINE 消息、专用内容与已核实的加好友短链；不把 LINE Mobile、游戏、购物、电视或整个 Naver 当成通信连接 |
| 3350 | <a id="rule-x-social-and-media"></a>`x-social-and-media` | X / Twitter 社交与图像视频 | Grok 专用的 grok.x.com 先由 xAI 规则匹配；只接产品和短链，不使用 twitter 关键词或广泛网段 |
| 3360 | <a id="rule-wechat-international-portal"></a>`wechat-international-portal` | WeChat 国际网站、支付与部分 App 连接 | wechat.com 也承载部分 App 的消息连接；qq.com 下微信与 WeChat 共用的入口由微信国内及共用规则处理 |
| 3370 | <a id="rule-slack-workspaces"></a>`slack-workspaces` | Slack 工作区、消息及相关网站 | 工作区、消息、文件、培训、演示和相关网站；外部登录单独匹配，日志域的产品归属不代表绕过隐私拦截，官方用途资料只保护明确的实时连接主机 |
| 3380 | <a id="rule-reddit-community"></a>`reddit-community` | Reddit 社区、帮助与相关服务 | 社区、内容、帮助、状态、通知及相关网站；外链网站单独匹配，Branch 短链和 Fastly 租户只使用清单中的精确主机 |
| 3390 | <a id="rule-instagram-social"></a>`instagram-social` | Instagram | 跟随产品入口与内容域名来源；排除品牌拼写变体、买粉和周边站点，不使用 instagram 关键词；共用 Facebook CDN 由 Meta 表处理 |
| 3400 | <a id="rule-whatsapp-messaging"></a>`whatsapp-messaging` | WhatsApp 消息、媒体与短链接 | 只采用官方客户端使用的核心命名空间；未核实用途的品牌变体和修改版名称不直接并入，通用 Meta 连接另行识别 |
| 3410 | <a id="rule-threads-social"></a>`threads-social` | Threads | 按所列维护来源识别该产品；只生成 Loon 域名规则，其他产品和厂商共用连接另行处理 |
| 3420 | <a id="rule-pinterest-social"></a>`pinterest-social` | Pinterest | 按所列维护来源识别该产品；只生成 Loon 域名规则，其他产品和厂商共用连接另行处理 |
| 3430 | <a id="rule-bluesky-social"></a>`bluesky-social` | Bluesky 官方应用与网络服务 | 按所列维护来源识别该产品；只生成 Loon 域名规则，其他产品和厂商共用连接另行处理 |
| 3440 | <a id="rule-lark-international"></a>`lark-international` | Lark 国际版协作服务 | 按所列维护来源识别该产品；只生成 Loon 域名规则，其他产品和厂商共用连接另行处理 |
| 3450 | <a id="rule-zoom-meetings"></a>`zoom-meetings` | Zoom 会议与共用服务 | 按所列维护来源识别该产品；只生成 Loon 域名规则，其他产品和厂商共用连接另行处理 |
| 3460 | <a id="rule-xiaomi-international-services"></a>`xiaomi-international-services` | 小米国际社区与应用商店入口 | 按来源标注的国际社区入口识别，和小米国内账户、设备及 MiMo API 分开 |
| 3470 | <a id="rule-linkedin-network"></a>`linkedin-network` | LinkedIn | 按所列维护来源识别该产品；只生成 Loon 域名规则，其他产品和厂商共用连接另行处理 |
| 3480 | <a id="rule-meta-shared-services"></a>`meta-shared-services` | Meta、Facebook 与 Messenger 共用服务 | 跟随所列 Facebook、Messenger、Meta 与 Oculus 业务域范围；品牌拼写变体、买粉、周边站点和未确认用途不作为产品端点；Instagram、WhatsApp、Threads 与 Meta AI 先匹配各自专表 |

## 8 支付（海外）

### 8.1 海外支付合集

| 序号 | 英文名称 | 中文名称 | 用途与选择 |
|---:|---|---|---|
| 3500 | <a id="rule-overseas-payments-all"></a>`overseas-payments-all` | 海外支付合集 | **合集：替代 3510–3595。** 合并本类已列细分范围，统一出口时使用；与成员二选一，细分仍可分别订阅 |

### 8.2 海外支付 · 产品细分

| 序号 | 英文名称 | 中文名称 | 用途与选择 |
|---:|---|---|---|
| 3510 | <a id="rule-paypal-payments"></a>`paypal-payments` | PayPal 核心支付、验签和静态资源 | 区分 PayPal 与旗下 Braintree/Venmo/Xoom 等其他产品，不靠 Paypal 关键词判断 |
| 3520 | <a id="rule-stripe-payments"></a>`stripe-payments` | Stripe | 托管结账、接口和产品专用素材；不接管商户网站 |
| 3530 | <a id="rule-link-payments"></a>`link-payments` | Link 快捷支付 | Stripe 的独立快捷支付产品，从官方站点身份确认根域；Stripe 网关、商户网站和发卡行验证分别匹配 |
| 3540 | <a id="rule-braintree-payments"></a>`braintree-payments` | Braintree 商户支付、网关与 SDK | 生产与沙箱 API 从官方域名代码清单更新，网关和 SDK 使用独立产品范围；不包括 PayPal、Venmo、Xoom 的账户，不采用整段 IP |
| 3550 | <a id="rule-venmo-payments"></a>`venmo-payments` | Venmo 支付 | 从官方产品站身份确认专用根域；PayPal、Braintree、其它钱包和商户网站各自匹配 |
| 3560 | <a id="rule-xoom-transfers"></a>`xoom-transfers` | Xoom 汇款 | 从官方产品站身份确认专用根域；PayPal、Braintree、其它钱包和商户网站各自匹配 |
| 3570 | <a id="rule-wise-transfers"></a>`wise-transfers` | Wise 转账与账户服务 | 按所列维护来源识别该产品；只生成 Loon 域名规则，其他产品和厂商共用连接另行处理 |
| 3580 | <a id="rule-tenpay-global-payments"></a>`tenpay-global-payments` | TenPay Global 跨境支付与商户平台 | 腾讯跨境支付品牌自有域，与财付通国内服务分别管理，不将整个微信或腾讯云归入跨境支付 |
| 3590 | <a id="rule-paddle-subscription-payments"></a>`paddle-subscription-payments` | Paddle 订阅支付、结账、商家 API、账单与 Retain | 从 Paddle.js 生产环境字段跟随当前 Retain 脚本，覆盖结账、商家 API、账单与恢复支付接口；共享 ProfitWell 主机上的其他请求也随本表匹配。开发与预发布环境单独排除，其他支付处理方保留各自规则。 |
| 3595 | <a id="rule-lemonsqueezy-subscription-payments"></a>`lemonsqueezy-subscription-payments` | Lemon Squeezy 订阅支付、结账与商家 API | 官网身份核对支付平台的自有命名空间，覆盖结账和商家入口；商家的自定义域名及银行卡、PayPal、Apple Pay、Google Pay 等处理方仍按其实际服务匹配，不认领整家云平台。 |

## 9 加密资产服务（海外）

### 9.1 海外加密资产服务合集

| 序号 | 英文名称 | 中文名称 | 用途与选择 |
|---:|---|---|---|
| 3600 | <a id="rule-overseas-crypto-all"></a>`overseas-crypto-all` | 海外加密资产服务合集 | **合集：替代 3610–3700。** 合并本类已列细分范围，统一出口时使用；与成员二选一，细分仍可分别订阅 |

### 9.2 海外加密资产服务 · 产品细分

| 序号 | 英文名称 | 中文名称 | 用途与选择 |
|---:|---|---|---|
| 3610 | <a id="rule-binance-platform"></a>`binance-platform` | Binance 币安 | 交易平台、现货 REST API 与实时行情；从官方基础端点说明补入专用主机，不把 binance.vision 整域、BNB 公链或第三方追踪归为交易平台 |
| 3620 | <a id="rule-okx-platform"></a>`okx-platform` | OKX 欧易 | 交易平台及专用连接，不包括 OKLink 浏览器或整个 Cloudflare |
| 3630 | <a id="rule-gemini-exchange"></a>`gemini-exchange` | Gemini 交易平台与 API | 从交易平台官方服务器字段确认提供方域；生产、沙箱、网页与 WebSocket 同属 Gemini Exchange，和 Google Gemini AI 分开 |
| 3640 | <a id="rule-kraken-exchange"></a>`kraken-exchange` | Kraken 交易平台 | 按所列维护来源识别该产品；只生成 Loon 域名规则，其他产品和厂商共用连接另行处理 |
| 3650 | <a id="rule-bybit-exchange"></a>`bybit-exchange` | Bybit 交易平台 | 按所列维护来源识别该产品；只生成 Loon 域名规则，其他产品和厂商共用连接另行处理 |
| 3660 | <a id="rule-kucoin-exchange"></a>`kucoin-exchange` | KuCoin 交易平台 | 按所列维护来源识别该产品；只生成 Loon 域名规则，其他产品和厂商共用连接另行处理 |
| 3670 | <a id="rule-trust-wallet"></a>`trust-wallet` | Trust Wallet | 钱包自己的服务；第三方 DApp 与各条链的公共 RPC 不属于钱包 |
| 3680 | <a id="rule-ton-foundation-sites"></a>`ton-foundation-sites` | TON 官方网站与开发资料 | 识别 TON 自营注册域中的网站和开发资料；第三方 RPC、钱包、节点和 Telegram 消息不并入 |
| 3690 | <a id="rule-toncenter-blockchain-api"></a>`toncenter-blockchain-api` | TON Center 区块链 API | 识别 TON Center 自营 API、主网与测试网入口；其他 RPC 提供商和 Telegram 消息分别匹配 |
| 3700 | <a id="rule-fragment-digital-assets"></a>`fragment-digital-assets` | Fragment 用户名与数字资产服务 | 识别 Fragment 自营网站及服务；Telegram 登录和钱包连接按各自服务匹配，不视为 Telegram 消息流量 |

## 10 影音与内容（海外）

### 10.1 海外影音与内容合集

| 序号 | 英文名称 | 中文名称 | 用途与选择 |
|---:|---|---|---|
| 3800 | <a id="rule-overseas-media-all"></a>`overseas-media-all` | 海外影音与内容合集 | **合集：替代 3810–3960。** 合并本类已列细分范围，统一出口时使用；与成员二选一，细分仍可分别订阅 |

### 10.2 视频平台与配套服务

| 序号 | 英文名称 | 中文名称 | 用途与选择 |
|---:|---|---|---|
| 3810 | <a id="rule-hbo-streaming"></a>`hbo-streaming` | HBO Max | 只收已核对的产品域；不推断账户订阅或播放地区 |
| 3820 | <a id="rule-netflix-video-and-delivery"></a>`netflix-video-and-delivery` | Netflix 播放、设备 API 和内容分发 | 保留 Netflix 服务域与 nflx* 中已确认的专用后缀；不接管 AWS 或来源不明的直播 IP |
| 3825 | <a id="rule-netflix-connection-tests"></a>`netflix-connection-tests` | Netflix FAST 连接检查与测速 | 从 Netflix 官方连接说明读取专用测速网站；测试 Netflix 路径时与播放使用同一出口，其他测速、Google 云和 AWS 共用服务不归本组 |
| 3830 | <a id="rule-disney-plus-streaming"></a>`disney-plus-streaming` | Disney+ 播放及其专用交付 | 播放、网页及专用分发域；官网公开配置按产品身份读取 API、内容与图片入口。迪士尼乐园、Hulu、内部服务器和共用资源另行归属 |
| 3840 | <a id="rule-prime-video-streaming"></a>`prime-video-streaming` | Prime Video 视频 API 和内容 | Amazon 零售、共享 CloudFront 父域和通用图片不纳入。本组只保已识别视频专用域和 CDN 别名 |
| 3850 | <a id="rule-hulu-streaming"></a>`hulu-streaming` | Hulu 视频与交付 | 按所列维护来源识别该产品；只生成 Loon 域名规则，其他产品和厂商共用连接另行处理 |
| 3855 | <a id="rule-discovery-plus-streaming"></a>`discovery-plus-streaming` | Discovery+ 播放、网站与地区 API | Discovery+ 网站、地区 API 与专用播放租户；共用后端归 WBD 平台，不接管整个视频 CDN |
| 3860 | <a id="rule-youtube-video-and-cdn"></a>`youtube-video-and-cdn` | YouTube 视频、音乐、频道与专用 CDN | 保留 youtubei、googlevideo 和 YouTube 静态域；不收整个 gvt2、Google IP 或 youtube 关键词 |
| 3870 | <a id="rule-tiktok-international-video"></a>`tiktok-international-video` | TikTok 国际短视频与直播 | 只含 TikTok 专有域；CapCut、抖音、Trae 以及两版共用字节云不划进本组 |
| 3880 | <a id="rule-bilibili-international-video"></a>`bilibili-international-video` | 哔哩哔哩国际版视频 | 国际版网站、API、素材与专用视频主机，按业务清单全文更新；子域主机用精确匹配，中国站及其海外 CDN 不按地理标签混入 |
| 3890 | <a id="rule-iqiyi-international"></a>`iqiyi-international` | 爱奇艺国际版 iQIYI 与专用国际 API | 国际产品域及已核对的 intl 服务子域先匹配；爱奇艺国内版与整段 iqiyi.com 由国内版规则处理 |
| 3900 | <a id="rule-vimeo-video"></a>`vimeo-video` | Vimeo 视频与交付 | 按所列维护来源识别该产品；只生成 Loon 域名规则，其他产品和厂商共用连接另行处理 |

### 10.3 音乐与音频平台

| 序号 | 英文名称 | 中文名称 | 用途与选择 |
|---:|---|---|---|
| 3910 | <a id="rule-spotify-audio"></a>`spotify-audio` | Spotify 音乐、播客及相关网站 | 音乐、播客、创作者入口、品牌网站和专用 CDN；完整来源中的独立开发、语音 AI、音乐资料库和广告平台分别归类，共享租户保持精确匹配，不采用关键词、User-Agent 或共享云 IP |
| 3915 | <a id="rule-whosampled-music-discovery"></a>`whosampled-music-discovery` | WhoSampled 音乐采样与作品资料库 | 按官方项目说明读取音乐资料网站与同主机 API，和 Spotify 播放入口分开；不因移动 App 未纳入漏洞奖励就认定其网络流量可忽略 |
| 3920 | <a id="rule-soundcloud-audio"></a>`soundcloud-audio` | SoundCloud 音频与创作者服务 | 按所列维护来源识别该产品；只生成 Loon 域名规则，其他产品和厂商共用连接另行处理 |

### 10.4 直播平台

| 序号 | 英文名称 | 中文名称 | 用途与选择 |
|---:|---|---|---|
| 3930 | <a id="rule-twitch-live-video"></a>`twitch-live-video` | Twitch 直播、聊天室和内容 CDN | 不导入整个来源 ASN/IP 或关键词。Twitch 专属后缀独立于其他视频服务 |

### 10.5 新闻与内容社区

| 序号 | 英文名称 | 中文名称 | 用途与选择 |
|---:|---|---|---|
| 3940 | <a id="rule-bbc-news-and-video"></a>`bbc-news-and-video` | BBC 新闻与影音 | BBC 自有产品域；不包揽共享 CDN 或据此保证地区版权可用 |
| 3950 | <a id="rule-bahamut-video-and-community"></a>`bahamut-video-and-community` | 巴哈姆特动画疯和电玩社区 | 专表有巴哈姆特域名和精确 CDN 别名，不匹配整个 Akamai/Hinet |

### 10.6 影音平台共用接口

| 序号 | 英文名称 | 中文名称 | 用途与选择 |
|---:|---|---|---|
| 3960 | <a id="rule-wbd-streaming-platform"></a>`wbd-streaming-platform` | HBO Max 与 Discovery 共用流媒体接口和网页图片 | Max 与 Discovery+ 共用后端、网页图片，以及 Discovery 旧接口平台；原站图片由具体产品处理，共用图片只收实际请求主机，不接管整个 CDN 或图片参数里的后台存储 |

## 11 游戏（海外）

### 11.1 海外游戏合集

| 序号 | 英文名称 | 中文名称 | 用途与选择 |
|---:|---|---|---|
| 4100 | <a id="rule-overseas-games-all"></a>`overseas-games-all` | 海外游戏合集 | **合集：替代 4110–4190。** 合并本类已列细分范围，统一出口时使用；与成员二选一，细分仍可分别订阅 |

### 11.2 海外游戏 · 产品细分

| 序号 | 英文名称 | 中文名称 | 用途与选择 |
|---:|---|---|---|
| 4110 | <a id="rule-steam-international-platform"></a>`steam-international-platform` | Steam 国际商店、社区、联机和下载 | 国内下载镜像单列；社区素材和直播只收 Steam 专用主机，不匹配整个第三方 CDN 或共享网段 |
| 4120 | <a id="rule-epic-games-services"></a>`epic-games-services` | Epic Games 商店、登录及 Unreal 服务 | 保留游戏厂商的专用域，不接管客服 SaaS 或共享 Amazon/CloudFront 域 |
| 4130 | <a id="rule-playstation-network"></a>`playstation-network` | Sony PlayStation | 商店、账户和产品网络；不把所有 Sony 服务或联机 IP 归入 |
| 4140 | <a id="rule-nintendo-platform"></a>`nintendo-platform` | Nintendo 任天堂 | 核心平台与官网地区门户；排除大陆专用域、共享基础设施和无法核实归属的游戏域名 |
| 4150 | <a id="rule-hoyoverse-international"></a>`hoyoverse-international` | HoYoverse 国际版 | 国际门户及专用游戏站；米游社和国服另列 |
| 4160 | <a id="rule-ea-games"></a>`ea-games` | EA 游戏平台 | EA 平台及已识别的专用素材；第三方游戏服务器不整段收录 |
| 4170 | <a id="rule-ubisoft-connect"></a>`ubisoft-connect` | Ubisoft Connect | 育碧账号、启动器与产品服务，独立客户端站点从官方产品说明读取；不把 AWS、Akamai 或调查工具整域归入 |
| 4180 | <a id="rule-blizzard-battlenet"></a>`blizzard-battlenet` | Blizzard / Battle.net 国际服务 | 国际平台入口；国内运营商入口不因品牌相同而并入 |
| 4190 | <a id="rule-netease-international-games"></a>`netease-international-games` | 网易国际游戏与共用 SDK | 按所列维护来源识别该产品；只生成 Loon 域名规则，其他产品和厂商共用连接另行处理 |

## 12 办公、邮件与协作（海外）

### 12.1 海外办公、邮件与协作合集

| 序号 | 英文名称 | 中文名称 | 用途与选择 |
|---:|---|---|---|
| 4300 | <a id="rule-overseas-productivity-all"></a>`overseas-productivity-all` | 海外办公、邮件与协作合集 | **合集：替代 4310–4360。** 合并本类已列细分范围，统一出口时使用；与成员二选一，细分仍可分别订阅 |

### 12.2 海外办公、邮件与协作 · 产品细分

| 序号 | 英文名称 | 中文名称 | 用途与选择 |
|---:|---|---|---|
| 4310 | <a id="rule-notion-workspace"></a>`notion-workspace` | Notion | 工作区、API、专用素材和官方状态页；自营主机随官方用途资料更新，不收出站 IP、整个 Cloudflare、notion.site 公共托管租户或用户自定义域 |
| 4320 | <a id="rule-figma-design"></a>`figma-design` | Figma | 在线设计和团队工作区，不收第三方插件访问的任意主机 |
| 4330 | <a id="rule-trello-boards"></a>`trello-boards` | Trello | 看板和专用素材；不收整个 Atlassian 平台 |
| 4340 | <a id="rule-atlassian-cloud-services"></a>`atlassian-cloud-services` | Atlassian Cloud：共享平台、Jira 与 Confluence | Jira、Confluence、共享认证、素材与政府云的第一方域；Bitbucket、Trello 各有专表。忽略合作方整域、出站 IP 和私有隔离云占位符 |
| 4350 | <a id="rule-proton-suite"></a>`proton-suite` | Proton 邮件、账户及共用服务 | 按所列维护来源识别该产品；只生成 Loon 域名规则，其他产品和厂商共用连接另行处理 |
| 4360 | <a id="rule-intercom-customer-support"></a>`intercom-customer-support` | Intercom 客服、会话、附件与实时通信 | 核心站点与官方 CSP 中 Intercom 品牌来源；地区 CDN 和附件范围跟随文档，不收 YouTube、Vimeo 等外部嵌入产品 |

## 13 Google 生态

### 13.1 Google 日常服务合集

| 序号 | 英文名称 | 中文名称 | 用途与选择 |
|---:|---|---|---|
| 4500 | <a id="rule-google-all"></a>`google-all` | Google 日常服务合集 | **合集：替代 4510–4590。** 合并本类已列细分范围，统一出口时使用；与成员二选一，细分仍可分别订阅 |

### 13.2 Google 日常服务 · 产品细分

| 序号 | 英文名称 | 中文名称 | 用途与选择 |
|---:|---|---|---|
| 4510 | <a id="rule-google-account-authentication"></a>`google-account-authentication` | Google 共享账号、地区登录、OAuth 授权与换令牌 | 登录和授权供多个业务共用；地区主机按官方模板与地区域名清单生成，不归 Gemini、Gmail、Meet 或 Drive 专项 |
| 4520 | <a id="rule-google-gmail-mail"></a>`google-gmail-mail` | Gmail 网页、邮件协议、专用 API 与投递诊断 | 区分 Gmail 网页、API 和 IMAP、SMTP、POP，含 Workspace 邮件中继。专用 API 和投递诊断随官方目录更新；登录与其他 Google API 分开 |
| 4530 | <a id="rule-google-meet-meetings"></a>`google-meet-meetings` | Google Meet 会议、API 与 Workspace 共用音视频媒体 | 普通账户、字体和 Chat API 分开；媒体按官方章节的 CIDR 与精确 SNI，只匹配目标 IP，不为匹配解析 DNS。同一 Workspace 媒体入口不能再按发起应用细分 |
| 4540 | <a id="rule-google-drive-and-documents"></a>`google-drive-and-documents` | Google Drive、文档和上传下载入口 | Drive、Docs 和明确文件主机。账号归 Google 账号组，不把整个 googleusercontent.com 或 www.googleapis.com 当网盘 |
| 4550 | <a id="rule-google-play-services"></a>`google-play-services` | Google Play 商店、应用管理与专用 API | 商店门户、企业应用管理、发布、完整性、报告及分组 API 随官方目录更新；游戏服务另列，共用 Android、FCM 和设备配置主机留给 Google 通用层 |
| 4560 | <a id="rule-google-play-games"></a>`google-play-games` | Google Play 游戏、发布与管理 API | 从官方目录读取 Google Play Games 的游戏服务、发布和管理 API；不把游戏本体、共享下载或所有 Android 主机归入本组 |
| 4570 | <a id="rule-google-software-downloads"></a>`google-software-downloads` | Google 软件和更新已知下载主机 | Google 软件包，以及使用 Google OTA 的设备下载更新的已知主机。只按下载用途认领精确主机，不按整个 CDN 分流 |
| 4580 | <a id="rule-google-scholar"></a>`google-scholar` | Google 学术搜索 | 按 Google 官方域名清单识别各地区 Scholar 专用主机，不接管账户、通用存储或出版社网站 |
| 4585 | <a id="rule-google-firebase-messaging"></a>`google-firebase-messaging` | Google Firebase Cloud Messaging 推送与令牌注册 | Web、iOS SDK 与官方 API 元数据读取推送专用主机；不把设备配置、Firebase 安装标识或 Google 网段都判作推送；iOS 通知的 APNs 接收路径仍在 Apple |
| 4590 | <a id="rule-google-platform-services"></a>`google-platform-services` | Google 搜索、官方资讯、安全浏览 API 与共享平台兜底 | 账号、邮件、会议、云盘、商店、下载、Gemini 和 YouTube 专项先匹配；官方资讯入口按页面用途读取，安全浏览读取服务字段，共用主机保留在平台层，不引入整段共享 IP |

## 14 Microsoft 生态

### 14.1 Microsoft 日常服务合集

| 序号 | 英文名称 | 中文名称 | 用途与选择 |
|---:|---|---|---|
| 4700 | <a id="rule-microsoft-all"></a>`microsoft-all` | Microsoft 日常服务合集 | **合集：替代 4710–4820。** 合并本类已列细分范围，统一出口时使用；与成员二选一，细分仍可分别订阅 |

### 14.2 Microsoft 日常服务 · 产品细分

| 序号 | 英文名称 | 中文名称 | 用途与选择 |
|---:|---|---|---|
| 4710 | <a id="rule-microsoft-account-authentication"></a>`microsoft-account-authentication` | Microsoft 个人账户与 Entra 登录 | 只收个人账户、全球及美国政府云登录与 Entra 身份主机；Azure 中国云控制端点另列，不把整个 microsoftonline.com 或 Microsoft Graph 当认证 |
| 4720 | <a id="rule-microsoft-outlook-mail"></a>`microsoft-outlook-mail` | Outlook 与 Exchange Online 邮箱入口 | 个人和工作邮箱、邮件协议与 Outlook 移动客户端分别按官方服务行提取。共享 Entra 登录独立，不展开租户占位字段，不采用同页 IP |
| 4730 | <a id="rule-microsoft-teams-meetings"></a>`microsoft-teams-meetings` | Teams 会议及 Skype for Business 共用通信入口 | 专用产品域和官方通信媒体网段先匹配；不扩到全部 Microsoft IP。Lync 与部分媒体为共用通信服务，不能凭相同入口区分发起应用 |
| 4740 | <a id="rule-microsoft-files-and-sharepoint"></a>`microsoft-files-and-sharepoint` | OneDrive 与 SharePoint 文件与同步 | 仅文件产品的专用后缀，去掉 onedrive/skydrive 关键词；共享登录由账号专项处理 |
| 4750 | <a id="rule-microsoft-store-services"></a>`microsoft-store-services` | Microsoft Store 商店目录与加载 | 商店前端和目录请求；系统更新控制、账户、许可和文件下载各自匹配 |
| 4760 | <a id="rule-microsoft-windows-update-services"></a>`microsoft-windows-update-services` | Windows Update 检查与传递优化协调 | 更新服务、传递优化控制和内容调度，不把整个 Windows 或 Microsoft 后缀当更新 |
| 4770 | <a id="rule-microsoft-update-and-store-downloads"></a>`microsoft-update-and-store-downloads` | Windows 更新和 Microsoft Store 已知内容下载 | 仅已知下载和精确 CDN 别名，不扩到整个 delivery.mp.microsoft.com。大文件确认可用后直连 |
| 4780 | <a id="rule-microsoft-office-downloads"></a>`microsoft-office-downloads` | Microsoft Office 安装与更新下载 | Office 下载主机及其已核对的精确别名；账号、激活与办公 Web 应用不算下载 |
| 4790 | <a id="rule-microsoft-vscode"></a>`microsoft-vscode` | Microsoft Visual Studio Code | 编辑器、更新、专用资源和设置同步；共用 Marketplace 与 Visual Studio 下载由 Microsoft 共用服务处理，GitHub 文件和 Copilot 各有专项；实验和崩溃统计不按核心入口收录 |
| 4800 | <a id="rule-microsoft-power-bi"></a>`microsoft-power-bi` | Microsoft Power BI | 报表服务的专用域；Microsoft 登录仍由账户规则处理 |
| 4810 | <a id="rule-microsoft-xbox-services"></a>`microsoft-xbox-services` | Xbox Live 已知登录与服务端点 | 明确的 Xbox 令牌与服务、资产主机；不代表全部游戏下载、语音、联机流量均可按域名识别 |
| 4820 | <a id="rule-microsoft-platform-services"></a>`microsoft-platform-services` | Microsoft 通用客户端和共享服务兜底 | 保留 Microsoft 通用服务和官方列出的 Azure 控制端点；按官方云定义排除租户后缀及会覆盖租户的父域。Graph 留在这里，不把多租户托管平台或共享 Akamai 整段接管 |

## 15 跨国厂商国内可用服务

### 15.1 跨国厂商国内可用服务合集

| 序号 | 英文名称 | 中文名称 | 用途与选择 |
|---:|---|---|---|
| 4900 | <a id="rule-multinational-mainland-all"></a>`multinational-mainland-all` | 跨国厂商国内可用服务合集 | **合集：替代 4910–4980。** 合并本类已列细分范围，统一出口时使用；与成员二选一，细分仍可分别订阅 |

### 15.2 厂商国内入口细分

| 序号 | 英文名称 | 中文名称 | 用途与选择 |
|---:|---|---|---|
| 4910 | <a id="rule-qualcomm-mainland"></a>`qualcomm-mainland` | 高通中国与国内可用系统服务 | 采用来源明确标注有中国大陆接入的范围，不按厂商总部或 .cn 后缀猜地区；不等同于所有服务只在中国运行，国际入口与共用主机另列 |
| 4920 | <a id="rule-nvidia-mainland"></a>`nvidia-mainland` | NVIDIA 中国网站与国内下载入口 | 采用来源明确标注有中国大陆接入的范围，不按厂商总部或 .cn 后缀猜地区；不等同于所有服务只在中国运行，国际入口与共用主机另列 |
| 4930 | <a id="rule-intel-mainland"></a>`intel-mainland` | Intel 中国网站 | 采用来源明确标注有中国大陆接入的范围，不按厂商总部或 .cn 后缀猜地区；不等同于所有服务只在中国运行，国际入口与共用主机另列 |
| 4940 | <a id="rule-samsung-mainland"></a>`samsung-mainland` | Samsung 中国网站、云与健康服务 | 采用来源明确标注有中国大陆接入的范围，不按厂商总部或 .cn 后缀猜地区；不等同于所有服务只在中国运行，国际入口与共用主机另列 |
| 4950 | <a id="rule-cloudflare-mainland"></a>`cloudflare-mainland` | Cloudflare 中国网络相关入口 | 采用来源明确标注有中国大陆接入的范围，不按厂商总部或 .cn 后缀猜地区；不等同于所有服务只在中国运行，国际入口与共用主机另列 |
| 4960 | <a id="rule-adobe-mainland"></a>`adobe-mainland` | Adobe 中国区文档云入口 | 采用来源明确标注有中国大陆接入的范围，不按厂商总部或 .cn 后缀猜地区；不等同于所有服务只在中国运行，国际入口与共用主机另列 |
| 4970 | <a id="rule-amazon-mainland"></a>`amazon-mainland` | Amazon 与 AWS 中国区入口 | 采用来源明确标注有中国大陆接入的范围，不按厂商总部或 .cn 后缀猜地区；不等同于所有服务只在中国运行，国际入口与共用主机另列 |
| 4980 | <a id="rule-microsoft-china-cloud-controls"></a>`microsoft-china-cloud-controls` | Microsoft Azure 中国区登录与控制端点 | 从 Azure 官方中国云定义读取登录、管理、门户、目录与 Graph 入口；只收精确控制主机，不接管中国云租户存储或整个 chinacloudapi.cn |

## 16 AI 服务（国内版）

### 16.1 国产 AI 国内版与共用入口合集

| 序号 | 英文名称 | 中文名称 | 用途与选择 |
|---:|---|---|---|
| 6000 | <a id="rule-ai-cn-all"></a>`ai-cn-all` | 国产 AI 国内版与共用入口合集 | **合集：替代 6010–6170。** 合并本类已列细分范围，统一出口时使用；与成员二选一，细分仍可分别订阅 |

### 16.2 国产 AI · 国内版与共用入口 · 产品细分

| 序号 | 英文名称 | 中文名称 | 用途与选择 |
|---:|---|---|---|
| 6010 | <a id="rule-qwen-mainland"></a>`qwen-mainland` | 阿里千问与百炼 · 国内入口 | 按已核实的国内产品入口生成；同一产品的网页、API 与附件不按功能拆开，共用云平台不收整域 |
| 6020 | <a id="rule-kimi-mainland"></a>`kimi-mainland` | 月之暗面 Kimi · 国内入口 | 按已核实的国内产品入口生成；同一产品的网页、API 与附件不按功能拆开，共用云平台不收整域 |
| 6030 | <a id="rule-zhipu-mainland"></a>`zhipu-mainland` | 智谱 · 国内入口 | 按已核实的国内产品入口生成；同一产品的网页、API 与附件不按功能拆开，共用云平台不收整域 |
| 6040 | <a id="rule-minimax-mainland"></a>`minimax-mainland` | MiniMax 与海螺 · 国内入口 | 按已核实的国内产品入口生成；同一产品的网页、API 与附件不按功能拆开，共用云平台不收整域 |
| 6050 | <a id="rule-bytedance-mainland"></a>`bytedance-mainland` | 字节豆包、扣子与模型平台 · 国内入口 | 按已核实的国内产品入口生成；同一产品的网页、API 与附件不按功能拆开，共用云平台不收整域 |
| 6060 | <a id="rule-siliconflow-mainland"></a>`siliconflow-mainland` | 硅基流动 · 国内入口 | 读取官方指南的 SDK API 配置与 API 密钥控制台链接，只生成精确主机；国内版与国际版分别读取，不接管整家云平台 |
| 6070 | <a id="rule-tencent-mainland"></a>`tencent-mainland` | 腾讯混元、元宝与 TokenHub · 国内入口 | 按已核实的国内产品入口生成；同一产品的网页、API 与附件不按功能拆开，共用云平台不收整域 |
| 6080 | <a id="rule-deepseek-mainland"></a>`deepseek-mainland` | DeepSeek · 国内入口 | 按已核实的国内产品入口生成；同一产品的网页、API 与附件不按功能拆开，共用云平台不收整域 |
| 6090 | <a id="rule-baidu-mainland"></a>`baidu-mainland` | 百度文心与千帆 | 文心门户、文心一言入口与千帆 API 按产品来源提取，不收整个百度、百度云或共用账号域 |
| 6100 | <a id="rule-iflytek-mainland"></a>`iflytek-mainland` | 讯飞星火 · 国内入口 | 按已核实的国内产品入口生成；同一产品的网页、API 与附件不按功能拆开，共用云平台不收整域 |
| 6110 | <a id="rule-liblib-mainland"></a>`liblib-mainland` | 哩布哩布 · 国内入口 | 哩布门户、官方 API 请求示例与页面明确声明的专用资源主机；不收集统计脚本、普通链接或整个共享云 |
| 6120 | <a id="rule-baichuan-mainland"></a>`baichuan-mainland` | 百川智能 · 国内入口 | 按已核实的国内产品入口生成；同一产品的网页、API 与附件不按功能拆开，共用云平台不收整域 |
| 6130 | <a id="rule-lingyi-mainland"></a>`lingyi-mainland` | 零一万物 · 国内入口 | 按已核实的国内产品入口生成；同一产品的网页、API 与附件不按功能拆开，共用云平台不收整域 |
| 6140 | <a id="rule-stepfun-mainland"></a>`stepfun-mainland` | 阶跃星辰 · 国内入口 | 按已核实的国内产品入口生成；同一产品的网页、API 与附件不按功能拆开，共用云平台不收整域 |
| 6150 | <a id="rule-sensetime-mainland"></a>`sensetime-mainland` | 商汤日日新 · 国内入口 | 按已核实的国内产品入口生成；同一产品的网页、API 与附件不按功能拆开，共用云平台不收整域 |
| 6160 | <a id="rule-modelscope-mainland"></a>`modelscope-mainland` | 魔搭 ModelScope · 模型 API | ModelScope 模型 API；模型文件与共享下载地址不因这个 API 一并代理 |
| 6170 | <a id="rule-xiaomi-mainland-and-shared"></a>`xiaomi-mainland-and-shared` | 小米 MiMo · 国内计划与共用 API | MiMo 国内计划和没有独立地区域名的共用 API；共用入口不能据域名判断账户地区，海外专用计划在国际版规则中 |

## 17 海外 AI 中国区服务

### 17.1 海外 AI 中国区服务合集

| 序号 | 英文名称 | 中文名称 | 用途与选择 |
|---:|---|---|---|
| 6250 | <a id="rule-ai-overseas-mainland-all"></a>`ai-overseas-mainland-all` | 海外 AI 中国区服务合集 | **合集：替代 6260。** 合并本类已列细分范围，统一出口时使用；与成员二选一，细分仍可分别订阅 |

### 17.2 海外 AI · 中国区服务 · 产品细分

| 序号 | 英文名称 | 中文名称 | 用途与选择 |
|---:|---|---|---|
| 6260 | <a id="rule-jetbrains-ai-mainland"></a>`jetbrains-ai-mainland` | JetBrains AI · 中国区 API | 只采用官方明确标注 for China 的 API 主机；不并入国产 AI 合集，不按 .cn 后缀推断其它服务或地区 |

## 18 开发（国内）

### 18.1 国内开发合集

| 序号 | 英文名称 | 中文名称 | 用途与选择 |
|---:|---|---|---|
| 6300 | <a id="rule-mainland-development-all"></a>`mainland-development-all` | 国内开发合集 | **合集：替代 6310–6350。** 合并本类已列细分范围，统一出口时使用；与成员二选一，细分仍可分别订阅 |

### 18.2 国内开发 · 产品细分

| 序号 | 英文名称 | 中文名称 | 用途与选择 |
|---:|---|---|---|
| 6310 | <a id="rule-gitee-hosting"></a>`gitee-hosting` | Gitee 码云 | 公共代码托管；不收自建服务或用户 Pages |
| 6320 | <a id="rule-coding-platform"></a>`coding-platform` | 腾讯 CODING | 托管和构建平台；不接管构建任务访问的其他包源 |
| 6330 | <a id="rule-gitcode-hosting"></a>`gitcode-hosting` | GitCode | GitCode 公共站；不把国内其他开发平台并入 |
| 6340 | <a id="rule-npmmirror-registry"></a>`npmmirror-registry` | npmmirror 国内镜像 | npm 镜像与二进制镜像；不会替 npm 客户端修改源 |
| 6350 | <a id="rule-tuna-mirrors"></a>`tuna-mirrors` | 清华 TUNA 开源镜像 | 只收镜像站与 PyPI 镜像，不接管校园网络 |

## 19 通讯与社交（国内及两版共用）

### 19.1 国内通讯与社交合集

| 序号 | 英文名称 | 中文名称 | 用途与选择 |
|---:|---|---|---|
| 6500 | <a id="rule-mainland-social-all"></a>`mainland-social-all` | 国内通讯与社交合集 | **合集：替代 6510–6570。** 合并本类已列细分范围，统一出口时使用；与成员二选一，细分仍可分别订阅 |

### 19.2 国内通讯与社交 · 产品细分

| 序号 | 英文名称 | 中文名称 | 用途与选择 |
|---:|---|---|---|
| 6510 | <a id="rule-wechat-shared-and-mainland"></a>`wechat-shared-and-mainland` | 微信国内与两版共用登录、消息和 App 服务 | 微信自有登录、消息、小程序与专用资源；腾讯共用图片、头像、SDK 和独立财付通域另分，不接管腾讯 ASN 或整个 QQ |
| 6520 | <a id="rule-dingtalk-public"></a>`dingtalk-public` | 钉钉公共服务 | 只匹配公共钉钉域；自建单点登录、专网和第三方企业应用不在内 |
| 6530 | <a id="rule-feishu-mainland"></a>`feishu-mainland` | 飞书国内协作服务 | 按所列维护来源识别该产品；只生成 Loon 域名规则，其他产品和厂商共用连接另行处理 |
| 6540 | <a id="rule-weibo-social"></a>`weibo-social` | 微博 | 微博自己的站点与分发域，包括同域地区子站；新浪与微博共用的图片域另列，不按页面语言判断出口 |
| 6550 | <a id="rule-douban-community"></a>`douban-community` | 豆瓣 | 社区与图片；不按域名推断用户所在地区 |
| 6560 | <a id="rule-xiaohongshu-community"></a>`xiaohongshu-community` | 小红书国内内容、社区及专用 CDN | 只收明确产品域；去掉共用风控，不把海外版或未知通用基础设施归入 |
| 6570 | <a id="rule-zhihu-community"></a>`zhihu-community` | 知乎 | 社区和图片域；明确的广告仍由前置拦截规则处理 |

## 20 支付（国内）

### 20.1 国内支付合集

| 序号 | 英文名称 | 中文名称 | 用途与选择 |
|---:|---|---|---|
| 6700 | <a id="rule-mainland-payments-all"></a>`mainland-payments-all` | 国内支付合集 | **合集：替代 6710–6730。** 合并本类已列细分范围，统一出口时使用；与成员二选一，细分仍可分别订阅 |

### 20.2 国内支付 · 产品细分

| 序号 | 英文名称 | 中文名称 | 用途与选择 |
|---:|---|---|---|
| 6710 | <a id="rule-alipay-mainland-payments"></a>`alipay-mainland-payments` | 支付宝国内账户支付和静态资源 | 不把 AlipayHK、Alipay+、第三方账户或整个阿里云归为国内支付宝 |
| 6720 | <a id="rule-unionpay-mainland"></a>`unionpay-mainland` | 银联、云闪付国内服务 | 国内服务入口；不把银联国际站按国内支付匹配 |
| 6730 | <a id="rule-tenpay-mainland-payments"></a>`tenpay-mainland-payments` | 财付通与 QQ 钱包共用支付 | 独立财付通域下的账户、支付、QQ 钱包与共用资源；微信专域下的支付接入仍由微信表处理；TenPay Global 独立分类 |

## 21 影音与直播（国内）

### 21.1 国内影音与直播合集

| 序号 | 英文名称 | 中文名称 | 用途与选择 |
|---:|---|---|---|
| 6900 | <a id="rule-mainland-media-all"></a>`mainland-media-all` | 国内影音与直播合集 | **合集：替代 6910–7000。** 合并本类已列细分范围，统一出口时使用；与成员二选一，细分仍可分别订阅 |

### 21.2 视频平台

| 序号 | 英文名称 | 中文名称 | 用途与选择 |
|---:|---|---|---|
| 6910 | <a id="rule-bilibili-mainland-video"></a>`bilibili-mainland-video` | 哔哩哔哩中国站视频与图片 | 中国站及两版共用的 API、图片和视频父域；国际版已识别的专用主机在前面精确匹配，其余范围保留国内策略，不按服务器国家强行拆分共用服务 |
| 6920 | <a id="rule-iqiyi-mainland"></a>`iqiyi-mainland` | 爱奇艺国内版 | 国内版与专用素材；同时使用国际版规则时，国际专用子域先匹配；单用本表不能从 iqiyi.com 父域排除国际业务 |
| 6930 | <a id="rule-youku-video"></a>`youku-video` | 优酷国内站 | 只认国内站及专用素材，不收国际站、整个阿里 CDN |

### 21.3 音乐、听书与互动平台

| 序号 | 英文名称 | 中文名称 | 用途与选择 |
|---:|---|---|---|
| 6940 | <a id="rule-qq-music"></a>`qq-music` | QQ 音乐 | 只收音乐专用主机；不接管 QQ、微信或整个腾讯平台 |
| 6945 | <a id="rule-wesing-mainland-karaoke"></a>`wesing-mainland-karaoke` | 全民 K 歌国内入口 | 从官方产品链接核对全民 K 歌入口，识别 kg.qq.com 专用范围；不把其他 WeSing 国际服务或全部 QQ 域名归入国内 |
| 6950 | <a id="rule-kugou-music"></a>`kugou-music` | 酷狗音乐、直播与关联客户端 | 按完整酷狗产品清单识别客户端、音乐、直播、专用素材与相关服务；共用域无法按音频和直播内容拆开，不接管整个腾讯平台 |
| 6952 | <a id="rule-kuwo-audio"></a>`kuwo-audio` | 酷我音乐与专用服务 | 跟随完整酷我产品清单，保留品牌别名及官方入口；不接管共享腾讯平台 |
| 6954 | <a id="rule-ximalaya-audio"></a>`ximalaya-audio` | 喜马拉雅音频与内容交付 | 跟随完整产品清单识别喜马拉雅与专用素材；不将 Himalaya 等不同产品按名称相似合并 |
| 6956 | <a id="rule-lazy-audio-books"></a>`lazy-audio-books` | 懒人听书与长音频 | 按上游明确的产品块读取完整范围，并独立核对官方产品入口；不把集团其他产品并入本表 |
| 6958 | <a id="rule-ultimate-music-services"></a>`ultimate-music-services` | 爱听卓乐商用音乐服务 | 按上游明确的产品块读取完整范围，并独立核对官方产品入口；不把集团其他产品并入本表 |
| 6960 | <a id="rule-netease-music"></a>`netease-music` | 网易云音乐 | 识别音乐 API、音频与专用内容主机；网易通用云、其他产品和上游大段 IP 不并入音乐表 |
| 6965 | <a id="rule-tencent-music-shared-services"></a>`tencent-music-shared-services` | 腾讯音乐集团、目录产品与共用服务 | 完整集团清单及官网产品目录扣除前面已识别的具体产品；保留官网、曲谱等目录入口与共用连接，不包含整个腾讯网络 |

### 21.4 短视频与直播平台

| 序号 | 英文名称 | 中文名称 | 用途与选择 |
|---:|---|---|---|
| 6970 | <a id="rule-douyin-mainland-video"></a>`douyin-mainland-video` | 抖音中国版短视频、直播、图片与素材 | 只取抖音专有域和投放到该产品的 CDN；不纳入 TikTok、今日头条或整个字节基础设施 |
| 6980 | <a id="rule-kuaishou-video"></a>`kuaishou-video` | 快手 | 国内产品和专用素材；Kwai 国际版不按同一品牌并入 |
| 6990 | <a id="rule-douyu-live"></a>`douyu-live` | 斗鱼直播 | 按所列维护来源识别该产品；只生成 Loon 域名规则，其他产品和厂商共用连接另行处理 |
| 7000 | <a id="rule-huya-live"></a>`huya-live` | 虎牙直播 | 按所列维护来源识别该产品；只生成 Loon 域名规则，其他产品和厂商共用连接另行处理 |

## 22 游戏（国内）

### 22.1 国内游戏合集

| 序号 | 英文名称 | 中文名称 | 用途与选择 |
|---:|---|---|---|
| 7200 | <a id="rule-mainland-games-all"></a>`mainland-games-all` | 国内游戏合集 | **合集：替代 7210–7230。** 合并本类已列细分范围，统一出口时使用；与成员二选一，细分仍可分别订阅 |

### 22.2 国内游戏 · 产品细分

| 序号 | 英文名称 | 中文名称 | 用途与选择 |
|---:|---|---|---|
| 7210 | <a id="rule-steam-mainland-downloads"></a>`steam-mainland-downloads` | Steam 中国下载镜像与蒸汽平台内容 | 只收已确认的国内下载镜像；游戏账户、商店和社区归 Steam 国际平台规则，不按第三方 CDN 整域判断 |
| 7220 | <a id="rule-mihoyo-mainland"></a>`mihoyo-mainland` | 米哈游国服与米游社 | 只选可区分的国服产品入口，不根据共享素材判断游戏区服 |
| 7230 | <a id="rule-wegame-mainland"></a>`wegame-mainland` | 腾讯 WeGame 国内平台 | 国内平台；不把 Tencent Games 的国际产品和整个 qq.com 直连 |

## 23 购物、生活与办公（国内）

### 23.1 国内购物、生活与办公合集

| 序号 | 英文名称 | 中文名称 | 用途与选择 |
|---:|---|---|---|
| 7400 | <a id="rule-mainland-daily-services-all"></a>`mainland-daily-services-all` | 国内购物、生活与办公合集 | **合集：替代 7410–7480。** 合并本类已列细分范围，统一出口时使用；与成员二选一，细分仍可分别订阅 |

### 23.2 购物平台

| 序号 | 英文名称 | 中文名称 | 用途与选择 |
|---:|---|---|---|
| 7410 | <a id="rule-taobao-and-xianyu-shopping"></a>`taobao-and-xianyu-shopping` | 淘宝、天猫、闲鱼购物与图片 | 只收国内消费平台及专用 CDN。不含 AliExpress、整个阿里云或支付宝 |
| 7420 | <a id="rule-jingdong-shopping"></a>`jingdong-shopping` | 京东购物、账户与商品素材 | 不将整个京东云网络或金融产品一并转为购物匹配 |

### 23.3 出行与生活服务

| 序号 | 英文名称 | 中文名称 | 用途与选择 |
|---:|---|---|---|
| 7430 | <a id="rule-railway-tickets"></a>`railway-tickets` | 铁路 12306 | 铁路售票、账户和专用服务。不把第三方支付网站归铁路 |
| 7440 | <a id="rule-meituan-services"></a>`meituan-services` | 美团与大众点评服务 | 按所列维护来源识别该产品；只生成 Loon 域名规则，其他产品和厂商共用连接另行处理 |
| 7450 | <a id="rule-didi-mobility"></a>`didi-mobility` | 滴滴出行 | 按所列维护来源识别该产品；只生成 Loon 域名规则，其他产品和厂商共用连接另行处理 |

### 23.4 办公、云盘与学习工具

| 序号 | 英文名称 | 中文名称 | 用途与选择 |
|---:|---|---|---|
| 7460 | <a id="rule-youdao-products"></a>`youdao-products` | 有道词典、学习与内容服务 | 按所列维护来源识别该产品；只生成 Loon 域名规则，其他产品和厂商共用连接另行处理 |
| 7470 | <a id="rule-aliyun-drive"></a>`aliyun-drive` | 阿里云盘 | 按所列维护来源识别该产品；只生成 Loon 域名规则，其他产品和厂商共用连接另行处理 |
| 7480 | <a id="rule-wps-office"></a>`wps-office` | WPS Office 与文档服务 | 按所列维护来源识别该产品；只生成 Loon 域名规则，其他产品和厂商共用连接另行处理 |

## 24 全球厂商与云平台共用服务

### 24.1 全球厂商与云平台共用服务合集

| 序号 | 英文名称 | 中文名称 | 用途与选择 |
|---:|---|---|---|
| 8000 | <a id="rule-global-platforms-all"></a>`global-platforms-all` | 全球厂商与云平台共用服务合集 | **合集：替代 8010–8150。** 合并本类已列细分范围，统一出口时使用；与成员二选一，细分仍可分别订阅 |

### 24.2 厂商与云平台细分

| 序号 | 英文名称 | 中文名称 | 用途与选择 |
|---:|---|---|---|
| 8010 | <a id="rule-digitalocean-services"></a>`digitalocean-services` | DigitalOcean 云平台与共用服务 | 仅接住所列产品、地区专表之后的厂商共用范围；按来源更新，忽略进程、IP 和不兼容的正则，不把共用平台当成某个应用 |
| 8020 | <a id="rule-vultr-services"></a>`vultr-services` | Vultr 云平台 | 仅接住所列产品、地区专表之后的厂商共用范围；按来源更新，忽略进程、IP 和不兼容的正则，不把共用平台当成某个应用 |
| 8030 | <a id="rule-hetzner-services"></a>`hetzner-services` | Hetzner 云与存储平台 | 仅接住所列产品、地区专表之后的厂商共用范围；按来源更新，忽略进程、IP 和不兼容的正则，不把共用平台当成某个应用 |
| 8040 | <a id="rule-vercel-shared-services"></a>`vercel-shared-services` | Vercel、Next.js 与共用托管平台 | 仅接住所列产品、地区专表之后的厂商共用范围；按来源更新，忽略进程、IP 和不兼容的正则，不把共用平台当成某个应用 |
| 8050 | <a id="rule-netlify-services"></a>`netlify-services` | Netlify 云平台与资源交付 | 仅接住所列产品、地区专表之后的厂商共用范围；按来源更新，忽略进程、IP 和不兼容的正则，不把共用平台当成某个应用 |
| 8060 | <a id="rule-heroku-services"></a>`heroku-services` | Heroku 云平台与共用托管 | 仅接住所列产品、地区专表之后的厂商共用范围；按来源更新，忽略进程、IP 和不兼容的正则，不把共用平台当成某个应用 |
| 8070 | <a id="rule-oracle-shared-services"></a>`oracle-shared-services` | Oracle、Java 与云平台共用服务 | 仅接住所列产品、地区专表之后的厂商共用范围；按来源更新，忽略进程、IP 和不兼容的正则，不把共用平台当成某个应用 |
| 8080 | <a id="rule-adobe-shared-services"></a>`adobe-shared-services` | Adobe Creative Cloud、Acrobat 与共用平台 | 仅接住所列产品、地区专表之后的厂商共用范围；按来源更新，忽略进程、IP 和不兼容的正则，不把共用平台当成某个应用 |
| 8090 | <a id="rule-cloudflare-shared-services"></a>`cloudflare-shared-services` | Cloudflare 控制台、WARP、Tunnel 与共用平台 | 仅接住所列产品、地区专表之后的厂商共用范围；按来源更新，忽略进程、IP 和不兼容的正则，不把共用平台当成某个应用 |
| 8100 | <a id="rule-amazon-shared-services"></a>`amazon-shared-services` | Amazon、AWS 与共用云平台 | 仅接住所列产品、地区专表之后的厂商共用范围；按来源更新，忽略进程、IP 和不兼容的正则，不把共用平台当成某个应用 |
| 8110 | <a id="rule-discord-activities-proxy"></a>`discord-activities-proxy` | Discord Activities 与第三方应用代理 | 从 Discord 官方代理用途说明读取平台命名空间；其中可以承载第三方应用和游戏，不归为聊天、语音或第三方应用自身的全部服务 |
| 8120 | <a id="rule-disney-shared-services"></a>`disney-shared-services` | Disney 共用账户、登录组件与日志 | MyDisney 账户管理及当前公开 SDK 的生产登录、组件和日志主机，供多个 Disney 产品共用；保持精确匹配，不接管整个 disney.com 或 go.com |
| 8130 | <a id="rule-github-pages-hosting"></a>`github-pages-hosting` | GitHub Pages 默认网站托管 | 默认 github.io 托管命名空间；具体产品的专用租户主机先匹配，本组处理其余平台请求。Pages 管理和产品介绍仍使用 GitHub 网站，自定义域名按其实际产品处理，不从共享 IP 反推归属 |
| 8140 | <a id="rule-mux-data-analytics"></a>`mux-data-analytics` | Mux Data 播放质量监测与 SDK | Mux Data 的专用 litix.io 名称空间；供多个应用使用，独立于接入应用的内容播放规则 |
| 8150 | <a id="rule-mux-video-platform"></a>`mux-video-platform` | Mux 视频播放、缩略图与平台接口 | Mux 自有 mux.com 平台范围，按官方 CSP 跟随播放和图片入口；上传使用的 Google 公共存储仍由其自身规则处理 |

## 25 海外补充

### 25.1 海外补充合集

| 序号 | 英文名称 | 中文名称 | 用途与选择 |
|---:|---|---|---|
| 8200 | <a id="rule-overseas-extra-all"></a>`overseas-extra-all` | 海外补充合集 | **合集：替代 8210–8220。** 合并本类已列细分范围，统一出口时使用；与成员二选一，细分仍可分别订阅 |

### 25.2 影音与网站补充

| 序号 | 英文名称 | 中文名称 | 用途与选择 |
|---:|---|---|---|
| 8210 | <a id="rule-overseas-media-extra"></a>`overseas-media-extra` | 其他海外影音 | 只补专项未覆盖的影音域名，交给海外影音策略；不按共享 IP、关键字或客户端名识别 |
| 8220 | <a id="rule-overseas-sites-extra"></a>`overseas-sites-extra` | 其他海外网站与受限站点 | 专项先识别；已采用的海外与受限站点来源优先于宽泛国内补充，共享云与公共后缀继续排除 |

## 26 国内厂商共用服务

### 26.1 国内厂商共用服务合集

| 序号 | 英文名称 | 中文名称 | 用途与选择 |
|---:|---|---|---|
| 8400 | <a id="rule-mainland-platforms-all"></a>`mainland-platforms-all` | 国内厂商共用服务合集 | **合集：替代 8410–8495。** 合并本类已列细分范围，统一出口时使用；与成员二选一，细分仍可分别订阅 |

### 26.2 厂商共用范围细分

| 序号 | 英文名称 | 中文名称 | 用途与选择 |
|---:|---|---|---|
| 8410 | <a id="rule-netease-shared-services"></a>`netease-shared-services` | 网易邮件、游戏、新闻与其他共用服务 | 仅接住所列产品、地区专表之后的厂商共用范围；按来源更新，忽略进程、IP 和不兼容的正则，不把共用平台当成某个应用 |
| 8420 | <a id="rule-alibaba-shared-services"></a>`alibaba-shared-services` | 阿里巴巴与阿里云共用服务 | 仅接住所列产品、地区专表之后的厂商共用范围；按来源更新，忽略进程、IP 和不兼容的正则，不把共用平台当成某个应用 |
| 8425 | <a id="rule-tencent-shared-content-and-sdk"></a>`tencent-shared-content-and-sdk` | 腾讯共用图片、头像、下载与 SDK | 微信、QQ 等产品共用的资源与 SDK 范围，不作为微信专用；专用 App 主机仍由前面的产品规则处理 |
| 8430 | <a id="rule-tencent-shared-services"></a>`tencent-shared-services` | 腾讯 QQ、邮箱、网站与共用服务 | 仅接住所列产品、地区专表之后的厂商共用范围；按来源更新，忽略进程、IP 和不兼容的正则，不把共用平台当成某个应用 |
| 8440 | <a id="rule-bytedance-shared-services"></a>`bytedance-shared-services` | 字节跳动国内与共用服务 | 仅接住所列产品、地区专表之后的厂商共用范围；按来源更新，忽略进程、IP 和不兼容的正则，不把共用平台当成某个应用 |
| 8450 | <a id="rule-baidu-shared-services"></a>`baidu-shared-services` | 百度搜索、网盘与共用服务 | 仅接住所列产品、地区专表之后的厂商共用范围；按来源更新，忽略进程、IP 和不兼容的正则，不把共用平台当成某个应用 |
| 8460 | <a id="rule-huawei-shared-services"></a>`huawei-shared-services` | 华为账户、设备与共用服务 | 仅接住所列产品、地区专表之后的厂商共用范围；按来源更新，忽略进程、IP 和不兼容的正则，不把共用平台当成某个应用 |
| 8470 | <a id="rule-xiaomi-shared-services"></a>`xiaomi-shared-services` | 小米账户、设备与共用服务 | 仅接住所列产品、地区专表之后的厂商共用范围；按来源更新，忽略进程、IP 和不兼容的正则，不把共用平台当成某个应用 |
| 8480 | <a id="rule-kingsoft-shared-services"></a>`kingsoft-shared-services` | 金山与其他共用服务 | 仅接住所列产品、地区专表之后的厂商共用范围；按来源更新，忽略进程、IP 和不兼容的正则，不把共用平台当成某个应用 |
| 8490 | <a id="rule-sina-shared-image-assets"></a>`sina-shared-image-assets` | 新浪与微博共用图片 | 新浪新闻、微博等服务共用的图片域，不代表微博专用；图片域下的广告仍按前置拦截规则处理 |
| 8495 | <a id="rule-sina-web-and-shared-services"></a>`sina-web-and-shared-services` | 新浪网站、新闻、邮箱与网页服务 | 新浪网站与共用网页范围；微博、AI 和共用图片按前表分别处理，不把整个新浪云租户平台当新闻网站 |

## 27 国内补充

### 27.1 国内补充合集

| 序号 | 英文名称 | 中文名称 | 用途与选择 |
|---:|---|---|---|
| 8600 | <a id="rule-mainland-routing-all"></a>`mainland-routing-all` | 国内补充合集 | **合集：替代 8610–8630。** 合并本类已列细分范围，统一出口时使用；与成员二选一，细分仍可分别订阅 |

### 27.2 域名、网段与 GeoIP

| 序号 | 英文名称 | 中文名称 | 用途与选择 |
|---:|---|---|---|
| 8610 | <a id="rule-mainland-domains"></a>`mainland-domains` | 未由专项认领的国内域名补充 | 只补前面专项没有完整覆盖的域名；保留必要父域，不把内网管理名或已识别的国际入口归为国内 |
| 8620 | <a id="rule-mainland-networks"></a>`mainland-networks` | 可按 IPv4 / IPv6 网段判断的国内地址 | 域名未命中时按目标地址查网段，排在 GeoIP 之前，不替代国内域名表。每轮整表与 APNIC 中国分配记录和运营商清单取共同支持的范围；证据不足的地址继续由后续规则判断，不据此认定所在地 |
| 8630 | <a id="rule-mainland-geoip"></a>`mainland-geoip` | 设备 GeoIP 数据库中的中国大陆地址兜底 | 前面的域名和网段未命中时再用。允许为查地址触发解析；地区归属取决于 Loon 设备上的数据库 |

产品专表已列在各业务下；统一出口用合集，分别选出口用其成员。[各组怎么选出口](routing.md) · [各类规则怎样更新](maintenance.md) · [参与维护](development.md)

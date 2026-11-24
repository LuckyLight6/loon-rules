# Loon 规则

从同一份规则生成，编号和选择顺序与[主清单](../../docs/rules.md)一致。合集与成员二选一

使用前阅读[客户端格式与限制](../../docs/clients.md)。标为无法转换的组不提供删减版订阅

| 序号 | 英文名称 | 中文名称 | 订阅 / 状态 |
|---|---|---|---|
| 0110 | local-links-and-addresses | 局域网名称、路由器、反查与保留地址 | [订阅](https://raw.githubusercontent.com/LuckyLight6/loon-rules/main/rules/0110-local-links-and-addresses.lsr) |
| 0120 | local-no-resolve-alt | 局域网管理名与已知 IP：不为匹配触发 DNS | [订阅](https://raw.githubusercontent.com/LuckyLight6/loon-rules/main/rules/0120-local-no-resolve-alt.lsr) |
| 0130 | network-sign-in-and-probes | 公共 Wi-Fi 登录、系统网络检查与必需安全连接 | [订阅](https://raw.githubusercontent.com/LuckyLight6/loon-rules/main/rules/0130-network-sign-in-and-probes.lsr) |
| 0140 | tailscale-control-and-tailnet | Tailscale 控制面、公开中继与 Tailnet 域名 | [订阅](https://raw.githubusercontent.com/LuckyLight6/loon-rules/main/rules/0140-tailscale-control-and-tailnet.lsr) |
| 0150 | ip-egress-checks | 查询当前公网出口：国内检测页、IPv4、IPv6 和双栈 API | [订阅](https://raw.githubusercontent.com/LuckyLight6/loon-rules/main/rules/0150-ip-egress-checks.lsr) |
| 0160 | cloudflare-public-dns | Cloudflare 公共 DNS 与标准解析器地址 | [订阅](https://raw.githubusercontent.com/LuckyLight6/loon-rules/main/rules/0160-cloudflare-public-dns.lsr) |
| 0210 | apple-and-ai-privacy-exceptions | Apple 广告与 OpenAI 广告像素的已核实拒绝项 | [订阅](https://raw.githubusercontent.com/LuckyLight6/loon-rules/main/rules/0210-apple-and-ai-privacy-exceptions.lsr) |
| 0220 | general-ad-and-tracking | Repcz 广告与追踪拦截 | [订阅](https://raw.githubusercontent.com/LuckyLight6/loon-rules/main/rules/0220-general-ad-and-tracking.lsr) |
| 0230 | privacy-public-stun-endpoints | 已公开的 STUN 主机，供选择性阻断 | [订阅](https://raw.githubusercontent.com/LuckyLight6/loon-rules/main/rules/0230-privacy-public-stun-endpoints.lsr) |
| 0240 | extended-ad-and-tracking | 可选的扩展广告与统计拦截 | [订阅](https://raw.githubusercontent.com/LuckyLight6/loon-rules/main/rules/0240-extended-ad-and-tracking.lsr) |
| 1000 | ai-overseas-all | 海外 AI 合集 | [订阅](https://raw.githubusercontent.com/LuckyLight6/loon-rules/main/rules/1000-ai-overseas-all.lsr) |
| 1010 | claude-connections | Claude 登录、API、MCP、更新、附件和 Artifact | [订阅](https://raw.githubusercontent.com/LuckyLight6/loon-rules/main/rules/1010-claude-connections.lsr) |
| 1020 | chatgpt-connections | ChatGPT、Codex、OpenAI API、语音信令与媒体连接 | [订阅](https://raw.githubusercontent.com/LuckyLight6/loon-rules/main/rules/1020-chatgpt-connections.lsr) |
| 1030 | gemini-connections | Gemini、AI Studio、NotebookLM、Google AI API 和专用 WebChannel | [订阅](https://raw.githubusercontent.com/LuckyLight6/loon-rules/main/rules/1030-gemini-connections.lsr) |
| 1040 | xai-connections | xAI 账号、Grok 对话与模型 API | [订阅](https://raw.githubusercontent.com/LuckyLight6/loon-rules/main/rules/1040-xai-connections.lsr) |
| 1050 | grokipedia-encyclopedia | Grokipedia AI 百科站点 | [订阅](https://raw.githubusercontent.com/LuckyLight6/loon-rules/main/rules/1050-grokipedia-encyclopedia.lsr) |
| 1060 | github-copilot-connections | Copilot API、补全、对话及已证实的附件服务 | [订阅](https://raw.githubusercontent.com/LuckyLight6/loon-rules/main/rules/1060-github-copilot-connections.lsr) |
| 1070 | microsoft-copilot-connections | Microsoft Copilot 个人版与工作版独立入口 | [订阅](https://raw.githubusercontent.com/LuckyLight6/loon-rules/main/rules/1070-microsoft-copilot-connections.lsr) |
| 1080 | meta-ai-assistant | Meta AI 助手、Llama 与专用内容入口 | [订阅](https://raw.githubusercontent.com/LuckyLight6/loon-rules/main/rules/1080-meta-ai-assistant.lsr) |
| 1090 | muse-agent | Muse 独立个人助手与其专用入口 | [订阅](https://raw.githubusercontent.com/LuckyLight6/loon-rules/main/rules/1090-muse-agent.lsr) |
| 1100 | cursor-editor-and-api | Cursor 客户端及专用接口 | [订阅](https://raw.githubusercontent.com/LuckyLight6/loon-rules/main/rules/1100-cursor-editor-and-api.lsr) |
| 1110 | perplexity-search-and-api | Perplexity 搜索、API 和专用内容入口 | [订阅](https://raw.githubusercontent.com/LuckyLight6/loon-rules/main/rules/1110-perplexity-search-and-api.lsr) |
| 1120 | poe-chat-and-api | Poe 聊天与平台域名 | [订阅](https://raw.githubusercontent.com/LuckyLight6/loon-rules/main/rules/1120-poe-chat-and-api.lsr) |
| 1130 | mistral-model-services | Mistral 平台专用域名 | [订阅](https://raw.githubusercontent.com/LuckyLight6/loon-rules/main/rules/1130-mistral-model-services.lsr) |
| 1140 | groq-inference | Groq 推理服务入口 | [订阅](https://raw.githubusercontent.com/LuckyLight6/loon-rules/main/rules/1140-groq-inference.lsr) |
| 1150 | cohere-model-services | Cohere 的推理及平台域名 | [订阅](https://raw.githubusercontent.com/LuckyLight6/loon-rules/main/rules/1150-cohere-model-services.lsr) |
| 1160 | hugging-face-model-hub | Hugging Face 模型库与专用 CDN | [订阅](https://raw.githubusercontent.com/LuckyLight6/loon-rules/main/rules/1160-hugging-face-model-hub.lsr) |
| 1170 | devin-cloud-coding | Devin 自有云编程入口 | [订阅](https://raw.githubusercontent.com/LuckyLight6/loon-rules/main/rules/1170-devin-cloud-coding.lsr) |
| 1180 | elevenlabs-voice-and-api | ElevenLabs 语音生成、WebSocket、文件与 MCP | [订阅](https://raw.githubusercontent.com/LuckyLight6/loon-rules/main/rules/1180-elevenlabs-voice-and-api.lsr) |
| 1190 | midjourney-image-tools | Midjourney 图像服务入口 | [订阅](https://raw.githubusercontent.com/LuckyLight6/loon-rules/main/rules/1190-midjourney-image-tools.lsr) |
| 1200 | openrouter-gateway | OpenRouter 的模型网关入口 | [订阅](https://raw.githubusercontent.com/LuckyLight6/loon-rules/main/rules/1200-openrouter-gateway.lsr) |
| 1210 | windsurf-editor-and-api | Windsurf 和 Codeium 专用接口 | [订阅](https://raw.githubusercontent.com/LuckyLight6/loon-rules/main/rules/1210-windsurf-editor-and-api.lsr) |
| 1220 | ai-com-agents | ai.com 的个人 AI 代理 | [订阅](https://raw.githubusercontent.com/LuckyLight6/loon-rules/main/rules/1220-ai-com-agents.lsr) |
| 1230 | jetbrains-ai | JetBrains AI | [订阅](https://raw.githubusercontent.com/LuckyLight6/loon-rules/main/rules/1230-jetbrains-ai.lsr) |
| 1240 | amp-connections | Amp 登录、线程 WebSocket、CLI 与官方运行环境 | [订阅](https://raw.githubusercontent.com/LuckyLight6/loon-rules/main/rules/1240-amp-connections.lsr) |
| 1250 | anythingllm-connections | AnythingLLM 官网与自营下载、云端入口 | [订阅](https://raw.githubusercontent.com/LuckyLight6/loon-rules/main/rules/1250-anythingllm-connections.lsr) |
| 1260 | fireworks-model-services | Fireworks 模型 API、产品门户与自营资源 | [订阅](https://raw.githubusercontent.com/LuckyLight6/loon-rules/main/rules/1260-fireworks-model-services.lsr) |
| 1270 | opencode-connections | OpenCode 与 Go 网关 | [订阅](https://raw.githubusercontent.com/LuckyLight6/loon-rules/main/rules/1270-opencode-connections.lsr) |
| 1280 | kilo-connections | Kilo 编程助手与模型网关 | [订阅](https://raw.githubusercontent.com/LuckyLight6/loon-rules/main/rules/1280-kilo-connections.lsr) |
| 1290 | cline-connections | Cline 自营接入与账户 | [订阅](https://raw.githubusercontent.com/LuckyLight6/loon-rules/main/rules/1290-cline-connections.lsr) |
| 1300 | ollama-cloud | Ollama Cloud 远程接口 | [订阅](https://raw.githubusercontent.com/LuckyLight6/loon-rules/main/rules/1300-ollama-cloud.lsr) |
| 1310 | chutes-model-services | Chutes 模型服务 | [订阅](https://raw.githubusercontent.com/LuckyLight6/loon-rules/main/rules/1310-chutes-model-services.lsr) |
| 1320 | bothub-model-services | Bothub 模型网关 | [订阅](https://raw.githubusercontent.com/LuckyLight6/loon-rules/main/rules/1320-bothub-model-services.lsr) |
| 1330 | commandcode-connections | CommandCode 编程与模型接口 | [订阅](https://raw.githubusercontent.com/LuckyLight6/loon-rules/main/rules/1330-commandcode-connections.lsr) |
| 1340 | stackit-model-services | STACKIT AI Model Serving | [订阅](https://raw.githubusercontent.com/LuckyLight6/loon-rules/main/rules/1340-stackit-model-services.lsr) |
| 1350 | novita-model-services | Novita 模型服务 | [订阅](https://raw.githubusercontent.com/LuckyLight6/loon-rules/main/rules/1350-novita-model-services.lsr) |
| 1360 | nebius-model-services | Nebius Token Factory | [订阅](https://raw.githubusercontent.com/LuckyLight6/loon-rules/main/rules/1360-nebius-model-services.lsr) |
| 1370 | baseten-model-services | Baseten 模型服务 | [订阅](https://raw.githubusercontent.com/LuckyLight6/loon-rules/main/rules/1370-baseten-model-services.lsr) |
| 1380 | deepinfra-model-services | DeepInfra 模型服务 | [订阅](https://raw.githubusercontent.com/LuckyLight6/loon-rules/main/rules/1380-deepinfra-model-services.lsr) |
| 1390 | together-model-services | Together AI 模型服务 | [订阅](https://raw.githubusercontent.com/LuckyLight6/loon-rules/main/rules/1390-together-model-services.lsr) |
| 1400 | cerebras-model-services | Cerebras 推理服务 | [订阅](https://raw.githubusercontent.com/LuckyLight6/loon-rules/main/rules/1400-cerebras-model-services.lsr) |
| 1410 | replicate-model-services | Replicate 模型 API 与结果文件 | [订阅](https://raw.githubusercontent.com/LuckyLight6/loon-rules/main/rules/1410-replicate-model-services.lsr) |
| 1420 | runway-creative-tools | Runway 视频与创作服务 | [订阅](https://raw.githubusercontent.com/LuckyLight6/loon-rules/main/rules/1420-runway-creative-tools.lsr) |
| 1430 | stability-model-services | Stability AI 模型服务 | [订阅](https://raw.githubusercontent.com/LuckyLight6/loon-rules/main/rules/1430-stability-model-services.lsr) |
| 1440 | black-forest-model-services | Black Forest Labs 与 FLUX | [订阅](https://raw.githubusercontent.com/LuckyLight6/loon-rules/main/rules/1440-black-forest-model-services.lsr) |
| 1450 | replit-cloud-development | Replit 云端开发 | [订阅](https://raw.githubusercontent.com/LuckyLight6/loon-rules/main/rules/1450-replit-cloud-development.lsr) |
| 1460 | augment-code-assistant | Augment Code 编程助手 | [订阅](https://raw.githubusercontent.com/LuckyLight6/loon-rules/main/rules/1460-augment-code-assistant.lsr) |
| 1470 | sourcegraph-code-and-cody | Sourcegraph 与 Cody | [订阅](https://raw.githubusercontent.com/LuckyLight6/loon-rules/main/rules/1470-sourcegraph-code-and-cody.lsr) |
| 1480 | continue-code-assistant | Continue 编程助手 | [订阅](https://raw.githubusercontent.com/LuckyLight6/loon-rules/main/rules/1480-continue-code-assistant.lsr) |
| 1490 | coderabbit-code-review | CodeRabbit 代码审查 | [订阅](https://raw.githubusercontent.com/LuckyLight6/loon-rules/main/rules/1490-coderabbit-code-review.lsr) |
| 1500 | tabnine-code-assistant | Tabnine 编程助手 | [订阅](https://raw.githubusercontent.com/LuckyLight6/loon-rules/main/rules/1500-tabnine-code-assistant.lsr) |
| 1510 | factory-coding-agents | Factory 编程代理 | [订阅](https://raw.githubusercontent.com/LuckyLight6/loon-rules/main/rules/1510-factory-coding-agents.lsr) |
| 1520 | zed-editor-and-ai | Zed 编辑器与自营 AI | [订阅](https://raw.githubusercontent.com/LuckyLight6/loon-rules/main/rules/1520-zed-editor-and-ai.lsr) |
| 1530 | kiro-code-assistant | Kiro 编程助手 | [订阅](https://raw.githubusercontent.com/LuckyLight6/loon-rules/main/rules/1530-kiro-code-assistant.lsr) |
| 1540 | bolt-app-builder | Bolt 应用构建 | [订阅](https://raw.githubusercontent.com/LuckyLight6/loon-rules/main/rules/1540-bolt-app-builder.lsr) |
| 1550 | lovable-app-builder | Lovable 应用构建 | [订阅](https://raw.githubusercontent.com/LuckyLight6/loon-rules/main/rules/1550-lovable-app-builder.lsr) |
| 1560 | v0-app-builder | Vercel v0 应用构建 | [订阅](https://raw.githubusercontent.com/LuckyLight6/loon-rules/main/rules/1560-v0-app-builder.lsr) |
| 1570 | genspark-connections | Genspark 搜索与代理 | [订阅](https://raw.githubusercontent.com/LuckyLight6/loon-rules/main/rules/1570-genspark-connections.lsr) |
| 1580 | jasper-marketing-ai | Jasper 营销 AI | [订阅](https://raw.githubusercontent.com/LuckyLight6/loon-rules/main/rules/1580-jasper-marketing-ai.lsr) |
| 1590 | gamma-presentations | Gamma 演示与文档 | [订阅](https://raw.githubusercontent.com/LuckyLight6/loon-rules/main/rules/1590-gamma-presentations.lsr) |
| 1600 | phind-search | Phind 搜索与问答 | [订阅](https://raw.githubusercontent.com/LuckyLight6/loon-rules/main/rules/1600-phind-search.lsr) |
| 1610 | inflection-and-pi | Inflection 与 Pi | [订阅](https://raw.githubusercontent.com/LuckyLight6/loon-rules/main/rules/1610-inflection-and-pi.lsr) |
| 1620 | h2o-model-services | H2O AI 平台 | [订阅](https://raw.githubusercontent.com/LuckyLight6/loon-rules/main/rules/1620-h2o-model-services.lsr) |
| 1630 | otter-meeting-assistant | Otter 会议助手 | [订阅](https://raw.githubusercontent.com/LuckyLight6/loon-rules/main/rules/1630-otter-meeting-assistant.lsr) |
| 1640 | descript-media-tools | Descript 音视频编辑 | [订阅](https://raw.githubusercontent.com/LuckyLight6/loon-rules/main/rules/1640-descript-media-tools.lsr) |
| 1650 | synthesia-video-tools | Synthesia 视频生成 | [订阅](https://raw.githubusercontent.com/LuckyLight6/loon-rules/main/rules/1650-synthesia-video-tools.lsr) |
| 1660 | luma-creative-tools | Luma 创作服务 | [订阅](https://raw.githubusercontent.com/LuckyLight6/loon-rules/main/rules/1660-luma-creative-tools.lsr) |
| 1670 | leonardo-image-tools | Leonardo 图像生成 | [订阅](https://raw.githubusercontent.com/LuckyLight6/loon-rules/main/rules/1670-leonardo-image-tools.lsr) |
| 1680 | pika-video-tools | Pika 视频生成 | [订阅](https://raw.githubusercontent.com/LuckyLight6/loon-rules/main/rules/1680-pika-video-tools.lsr) |
| 1690 | recraft-design-tools | Recraft 设计与图像 | [订阅](https://raw.githubusercontent.com/LuckyLight6/loon-rules/main/rules/1690-recraft-design-tools.lsr) |
| 1700 | udio-music-tools | Udio 音乐生成 | [订阅](https://raw.githubusercontent.com/LuckyLight6/loon-rules/main/rules/1700-udio-music-tools.lsr) |
| 1710 | duck-ai-chat | Duck.ai 对话 | [订阅](https://raw.githubusercontent.com/LuckyLight6/loon-rules/main/rules/1710-duck-ai-chat.lsr) |
| 1720 | langchain-agent-platform | LangChain 与代理平台 | [订阅](https://raw.githubusercontent.com/LuckyLight6/loon-rules/main/rules/1720-langchain-agent-platform.lsr) |
| 1730 | comfy-cloud-and-registry | Comfy 云端与组件目录 | [订阅](https://raw.githubusercontent.com/LuckyLight6/loon-rules/main/rules/1730-comfy-cloud-and-registry.lsr) |
| 1740 | lmstudio-product-services | LM Studio 产品与下载 | [订阅](https://raw.githubusercontent.com/LuckyLight6/loon-rules/main/rules/1740-lmstudio-product-services.lsr) |
| 1750 | crewai-agent-platform | CrewAI 代理平台 | [订阅](https://raw.githubusercontent.com/LuckyLight6/loon-rules/main/rules/1750-crewai-agent-platform.lsr) |
| 1760 | eigent-agent-services | Eigent 代理与协作 | [订阅](https://raw.githubusercontent.com/LuckyLight6/loon-rules/main/rules/1760-eigent-agent-services.lsr) |
| 1770 | manus-agent-services | Manus 代理与文件 | [订阅](https://raw.githubusercontent.com/LuckyLight6/loon-rules/main/rules/1770-manus-agent-services.lsr) |
| 1780 | dia-browser-services | Dia 浏览器自营服务 | [订阅](https://raw.githubusercontent.com/LuckyLight6/loon-rules/main/rules/1780-dia-browser-services.lsr) |
| 1790 | openclaw-product-services | OpenClaw 产品与发布服务 | [订阅](https://raw.githubusercontent.com/LuckyLight6/loon-rules/main/rules/1790-openclaw-product-services.lsr) |
| 1800 | ai-cn-international-all | 国产 AI 国际版合集 | [订阅](https://raw.githubusercontent.com/LuckyLight6/loon-rules/main/rules/1800-ai-cn-international-all.lsr) |
| 1810 | qwen-international | 阿里千问与百炼 · 国际入口 | [订阅](https://raw.githubusercontent.com/LuckyLight6/loon-rules/main/rules/1810-qwen-international.lsr) |
| 1820 | kimi-international | 月之暗面 Kimi · 国际入口 | [订阅](https://raw.githubusercontent.com/LuckyLight6/loon-rules/main/rules/1820-kimi-international.lsr) |
| 1830 | zhipu-international | 智谱 · 国际入口 | [订阅](https://raw.githubusercontent.com/LuckyLight6/loon-rules/main/rules/1830-zhipu-international.lsr) |
| 1840 | minimax-international | MiniMax 与海螺 · 国际入口 | [订阅](https://raw.githubusercontent.com/LuckyLight6/loon-rules/main/rules/1840-minimax-international.lsr) |
| 1850 | bytedance-international | 字节豆包、扣子与模型平台 · 国际入口 | [订阅](https://raw.githubusercontent.com/LuckyLight6/loon-rules/main/rules/1850-bytedance-international.lsr) |
| 1860 | siliconflow-international | 硅基流动 · 国际入口 | [订阅](https://raw.githubusercontent.com/LuckyLight6/loon-rules/main/rules/1860-siliconflow-international.lsr) |
| 1870 | tencent-international | 腾讯混元、元宝与 TokenHub · 国际入口 | [订阅](https://raw.githubusercontent.com/LuckyLight6/loon-rules/main/rules/1870-tencent-international.lsr) |
| 1880 | stepfun-international | 阶跃星辰 StepFun · 国际入口 | [订阅](https://raw.githubusercontent.com/LuckyLight6/loon-rules/main/rules/1880-stepfun-international.lsr) |
| 1890 | xiaomi-international | 小米 MiMo · 新加坡与欧洲计划 | [订阅](https://raw.githubusercontent.com/LuckyLight6/loon-rules/main/rules/1890-xiaomi-international.lsr) |
| 1900 | youmind-international | YouMind · 国际产品入口 | [订阅](https://raw.githubusercontent.com/LuckyLight6/loon-rules/main/rules/1900-youmind-international.lsr) |
| 1910 | qoder-international | Qoder · 国际产品入口 | [订阅](https://raw.githubusercontent.com/LuckyLight6/loon-rules/main/rules/1910-qoder-international.lsr) |
| 1920 | lovart-international | Lovart · 国际产品入口 | [订阅](https://raw.githubusercontent.com/LuckyLight6/loon-rules/main/rules/1920-lovart-international.lsr) |
| 2000 | apple-all | Apple 生态完整合集 | [订阅](https://raw.githubusercontent.com/LuckyLight6/loon-rules/main/rules/2000-apple-all.lsr) |
| 2010 | apple-overseas-all | Apple 海外功能合集 | [订阅](https://raw.githubusercontent.com/LuckyLight6/loon-rules/main/rules/2010-apple-overseas-all.lsr) |
| 2020 | apple-intelligence-relays | Apple Intelligence 的 PCC 与系统 AI 扩展中继 | [订阅](https://raw.githubusercontent.com/LuckyLight6/loon-rules/main/rules/2020-apple-intelligence-relays.lsr) |
| 2030 | apple-private-relay-connections | iCloud Private Relay（隐私中继）与 Apple DNS 别名 | [订阅](https://raw.githubusercontent.com/LuckyLight6/loon-rules/main/rules/2030-apple-private-relay-connections.lsr) |
| 2040 | apple-video-and-fitness | Apple TV／Fitness+ 的门户、播放控制与共用主机 | [订阅](https://raw.githubusercontent.com/LuckyLight6/loon-rules/main/rules/2040-apple-video-and-fitness.lsr) |
| 2050 | apple-tv-video-delivery | Apple TV 已识别的 HLS 视频交付 | [订阅](https://raw.githubusercontent.com/LuckyLight6/loon-rules/main/rules/2050-apple-tv-video-delivery.lsr) |
| 2060 | apple-news-and-sports | Apple News／News+、内容入口与 Apple Sports | [订阅](https://raw.githubusercontent.com/LuckyLight6/loon-rules/main/rules/2060-apple-news-and-sports.lsr) |
| 2070 | apple-push-connection | APNs 系统推送的域名与公开客户端网段 | [订阅](https://raw.githubusercontent.com/LuckyLight6/loon-rules/main/rules/2070-apple-push-connection.lsr) |
| 2080 | apple-direct-all | Apple 普通服务合集 | [订阅](https://raw.githubusercontent.com/LuckyLight6/loon-rules/main/rules/2080-apple-direct-all.lsr) |
| 2090 | apple-account-authentication | 登录、GrandSlam、OAuth、账户恢复与 iCloud 账户控制 | [订阅](https://raw.githubusercontent.com/LuckyLight6/loon-rules/main/rules/2090-apple-account-authentication.lsr) |
| 2100 | apple-app-and-device-verification | 应用验证、App Attest、macOS 公证与设备身份验证 | [订阅](https://raw.githubusercontent.com/LuckyLight6/loon-rules/main/rules/2100-apple-app-and-device-verification.lsr) |
| 2110 | apple-wallet-payments | Wallet 与 Apple Pay 已知支付入口 | [订阅](https://raw.githubusercontent.com/LuckyLight6/loon-rules/main/rules/2110-apple-wallet-payments.lsr) |
| 2120 | apple-testflight | TestFlight 测试版安装和分发 | [订阅](https://raw.githubusercontent.com/LuckyLight6/loon-rules/main/rules/2120-apple-testflight.lsr) |
| 2130 | apple-store-transactions | App Store API、搜索与提示、购买与安装指令、Apple Books 商店 | [订阅](https://raw.githubusercontent.com/LuckyLight6/loon-rules/main/rules/2130-apple-store-transactions.lsr) |
| 2140 | apple-app-package-downloads | App Store 安装包下载 | [订阅](https://raw.githubusercontent.com/LuckyLight6/loon-rules/main/rules/2140-apple-app-package-downloads.lsr) |
| 2150 | apple-association-services | Apple 通用链接的域名验证 | [订阅](https://raw.githubusercontent.com/LuckyLight6/loon-rules/main/rules/2150-apple-association-services.lsr) |
| 2160 | apple-find-my | Find My 设备与朋友查找的已识别入口 | [订阅](https://raw.githubusercontent.com/LuckyLight6/loon-rules/main/rules/2160-apple-find-my.lsr) |
| 2170 | apple-location-services | 定位查询、地图配置与信号定位数据 | [订阅](https://raw.githubusercontent.com/LuckyLight6/loon-rules/main/rules/2170-apple-location-services.lsr) |
| 2180 | apple-messaging-identity | Apple IDS 共用身份、注册与查询服务 | [订阅](https://raw.githubusercontent.com/LuckyLight6/loon-rules/main/rules/2180-apple-messaging-identity.lsr) |
| 2190 | apple-icloud-mainland | 中国大陆 iCloud 服务和内容专用域 | [订阅](https://raw.githubusercontent.com/LuckyLight6/loon-rules/main/rules/2190-apple-icloud-mainland.lsr) |
| 2200 | apple-icloud-content-domains | iCloud 通用内容域 | [订阅](https://raw.githubusercontent.com/LuckyLight6/loon-rules/main/rules/2200-apple-icloud-content-domains.lsr) |
| 2210 | apple-cloud-sync | iCloud 通用服务、CloudKit、同步、邮件及 iWork | [订阅](https://raw.githubusercontent.com/LuckyLight6/loon-rules/main/rules/2210-apple-cloud-sync.lsr) |
| 2220 | apple-podcasts | Apple 播客 | [订阅](https://raw.githubusercontent.com/LuckyLight6/loon-rules/main/rules/2220-apple-podcasts.lsr) |
| 2230 | apple-music-and-radio | Apple Music、广播及共用 API 与应用门户 | [订阅](https://raw.githubusercontent.com/LuckyLight6/loon-rules/main/rules/2230-apple-music-and-radio.lsr) |
| 2240 | apple-music-audio-delivery | Apple Music 已识别音频交付主机 | [订阅](https://raw.githubusercontent.com/LuckyLight6/loon-rules/main/rules/2240-apple-music-audio-delivery.lsr) |
| 2250 | apple-siri-and-search | Siri 与 Spotlight 的专用域名 | [订阅](https://raw.githubusercontent.com/LuckyLight6/loon-rules/main/rules/2250-apple-siri-and-search.lsr) |
| 2260 | apple-update-control | 系统更新目录、检查、授权与登记 | [订阅](https://raw.githubusercontent.com/LuckyLight6/loon-rules/main/rules/2260-apple-update-control.lsr) |
| 2270 | apple-update-downloads | 系统更新包与恢复内容下载 | [订阅](https://raw.githubusercontent.com/LuckyLight6/loon-rules/main/rules/2270-apple-update-downloads.lsr) |
| 2280 | apple-developer-portal | Apple Developer 门户 | [订阅](https://raw.githubusercontent.com/LuckyLight6/loon-rules/main/rules/2280-apple-developer-portal.lsr) |
| 2290 | apple-developer-downloads | Xcode、Swift Playgrounds 和开发者组件的实际下载 | [订阅](https://raw.githubusercontent.com/LuckyLight6/loon-rules/main/rules/2290-apple-developer-downloads.lsr) |
| 2300 | apple-mainland-delivery-aliases | 已核对的 Apple 大陆就近分发别名 | [订阅](https://raw.githubusercontent.com/LuckyLight6/loon-rules/main/rules/2300-apple-mainland-delivery-aliases.lsr) |
| 2310 | apple-shared-store-assets | Apple 商店与媒体共用的静态内容 | [订阅](https://raw.githubusercontent.com/LuckyLight6/loon-rules/main/rules/2310-apple-shared-store-assets.lsr) |
| 2320 | apple-certificate-validation | Apple 设备的证书状态和撤销检查 | [订阅](https://raw.githubusercontent.com/LuckyLight6/loon-rules/main/rules/2320-apple-certificate-validation.lsr) |
| 2330 | apple-system-connectivity | 设备引导、MDM、校时、系统 DNS 与公共素材 | [订阅](https://raw.githubusercontent.com/LuckyLight6/loon-rules/main/rules/2330-apple-system-connectivity.lsr) |
| 2340 | apple-schoolwork-handouts | Apple Schoolwork 讲义与资料交付 | [订阅](https://raw.githubusercontent.com/LuckyLight6/loon-rules/main/rules/2340-apple-schoolwork-handouts.lsr) |
| 2350 | apple-device-registration | 设备激活与 APNs 证书登记门户 | [订阅](https://raw.githubusercontent.com/LuckyLight6/loon-rules/main/rules/2350-apple-device-registration.lsr) |
| 2360 | apple-feedback-and-diagnostics | Feedback Assistant、错误报告与自愿诊断上传 | [订阅](https://raw.githubusercontent.com/LuckyLight6/loon-rules/main/rules/2360-apple-feedback-and-diagnostics.lsr) |
| 2370 | apple-other-services | Apple 官网与尚未细分的通用服务 | [订阅](https://raw.githubusercontent.com/LuckyLight6/loon-rules/main/rules/2370-apple-other-services.lsr) |
| 3000 | overseas-development-all | 海外开发合集 | [订阅](https://raw.githubusercontent.com/LuckyLight6/loon-rules/main/rules/3000-overseas-development-all.lsr) |
| 3010 | github-code-and-packages | GitHub 代码托管、API、Actions 与容器镜像 | [订阅](https://raw.githubusercontent.com/LuckyLight6/loon-rules/main/rules/3010-github-code-and-packages.lsr) |
| 3020 | gitlab-hosting | GitLab.com | [订阅](https://raw.githubusercontent.com/LuckyLight6/loon-rules/main/rules/3020-gitlab-hosting.lsr) |
| 3030 | bitbucket-hosting | Atlassian Bitbucket | [订阅](https://raw.githubusercontent.com/LuckyLight6/loon-rules/main/rules/3030-bitbucket-hosting.lsr) |
| 3040 | npm-registry | npm 软件包 | [订阅](https://raw.githubusercontent.com/LuckyLight6/loon-rules/main/rules/3040-npm-registry.lsr) |
| 3050 | maven-central | Maven Central | [订阅](https://raw.githubusercontent.com/LuckyLight6/loon-rules/main/rules/3050-maven-central.lsr) |
| 3060 | pypi-packages | PyPI 软件包 | [订阅](https://raw.githubusercontent.com/LuckyLight6/loon-rules/main/rules/3060-pypi-packages.lsr) |
| 3070 | docker-hub | Docker Hub | [订阅](https://raw.githubusercontent.com/LuckyLight6/loon-rules/main/rules/3070-docker-hub.lsr) |
| 3075 | docker-desktop-and-platform | Docker Desktop、Scout、Offload、Hardened Images 与平台服务 | [订阅](https://raw.githubusercontent.com/LuckyLight6/loon-rules/main/rules/3075-docker-desktop-and-platform.lsr) |
| 3080 | rust-cargo | Rust、Cargo 与 crates.io | [订阅](https://raw.githubusercontent.com/LuckyLight6/loon-rules/main/rules/3080-rust-cargo.lsr) |
| 3090 | go-modules | Go 模块与工具链 | [订阅](https://raw.githubusercontent.com/LuckyLight6/loon-rules/main/rules/3090-go-modules.lsr) |
| 3100 | jetbrains-ides | JetBrains IDE、授权与插件 | [订阅](https://raw.githubusercontent.com/LuckyLight6/loon-rules/main/rules/3100-jetbrains-ides.lsr) |
| 3110 | nodejs-runtime | Node.js 运行时与官方发行站 | [订阅](https://raw.githubusercontent.com/LuckyLight6/loon-rules/main/rules/3110-nodejs-runtime.lsr) |
| 3120 | agent-client-protocol | ACP 协议、文档与代理注册表 | [订阅](https://raw.githubusercontent.com/LuckyLight6/loon-rules/main/rules/3120-agent-client-protocol.lsr) |
| 3130 | workos-authentication | WorkOS 登录、企业认证与公共组件 | [订阅](https://raw.githubusercontent.com/LuckyLight6/loon-rules/main/rules/3130-workos-authentication.lsr) |
| 3140 | datadog-observability | Datadog 监控、日志与浏览器 SDK | [订阅](https://raw.githubusercontent.com/LuckyLight6/loon-rules/main/rules/3140-datadog-observability.lsr) |
| 3150 | sentry-error-monitoring | Sentry 错误监控、API 与 SDK | [订阅](https://raw.githubusercontent.com/LuckyLight6/loon-rules/main/rules/3150-sentry-error-monitoring.lsr) |
| 3160 | statsig-feature-management | Statsig 功能开关、实验、配置与事件 API | [订阅](https://raw.githubusercontent.com/LuckyLight6/loon-rules/main/rules/3160-statsig-feature-management.lsr) |
| 3170 | fathom-web-analytics | Fathom 网站访问统计 | [订阅](https://raw.githubusercontent.com/LuckyLight6/loon-rules/main/rules/3170-fathom-web-analytics.lsr) |
| 3180 | hcaptcha-verification | hcaptcha 人机验证与服务状态 | [订阅](https://raw.githubusercontent.com/LuckyLight6/loon-rules/main/rules/3180-hcaptcha-verification.lsr) |
| 3190 | persona-identity-verification | Persona 身份、企业与年龄验证 | [订阅](https://raw.githubusercontent.com/LuckyLight6/loon-rules/main/rules/3190-persona-identity-verification.lsr) |
| 3200 | yoti-identity-verification | Yoti 数字身份与年龄验证 | [订阅](https://raw.githubusercontent.com/LuckyLight6/loon-rules/main/rules/3200-yoti-identity-verification.lsr) |
| 3210 | sift-fraud-prevention | Sift 反欺诈、设备与风险 API | [订阅](https://raw.githubusercontent.com/LuckyLight6/loon-rules/main/rules/3210-sift-fraud-prevention.lsr) |
| 3220 | auth0-identity-platform | Auth0 身份认证与共享登录平台 | [订阅](https://raw.githubusercontent.com/LuckyLight6/loon-rules/main/rules/3220-auth0-identity-platform.lsr) |
| 3230 | bugsnag-error-monitoring | Bugsnag 错误监控与会话报告 | [订阅](https://raw.githubusercontent.com/LuckyLight6/loon-rules/main/rules/3230-bugsnag-error-monitoring.lsr) |
| 3300 | overseas-social-all | 海外通讯与社交合集 | [订阅](https://raw.githubusercontent.com/LuckyLight6/loon-rules/main/rules/3300-overseas-social-all.lsr) |
| 3310 | telegram-messaging | Telegram 登录、消息、文件与服务器地址 | [订阅](https://raw.githubusercontent.com/LuckyLight6/loon-rules/main/rules/3310-telegram-messaging.lsr) |
| 3320 | discord-messaging-and-voice | Discord 通讯、语音及自营服务 | [订阅](https://raw.githubusercontent.com/LuckyLight6/loon-rules/main/rules/3320-discord-messaging-and-voice.lsr) |
| 3330 | signal-messenger | Signal 消息、通话、贴纸、群组与用户名链接 | [订阅](https://raw.githubusercontent.com/LuckyLight6/loon-rules/main/rules/3330-signal-messenger.lsr) |
| 3340 | line-messenger | LINE | [订阅](https://raw.githubusercontent.com/LuckyLight6/loon-rules/main/rules/3340-line-messenger.lsr) |
| 3350 | x-social-and-media | X / Twitter 社交与图像视频 | [订阅](https://raw.githubusercontent.com/LuckyLight6/loon-rules/main/rules/3350-x-social-and-media.lsr) |
| 3360 | wechat-international-portal | WeChat 国际网站、支付与部分 App 连接 | [订阅](https://raw.githubusercontent.com/LuckyLight6/loon-rules/main/rules/3360-wechat-international-portal.lsr) |
| 3370 | slack-workspaces | Slack 工作区、消息及相关网站 | [订阅](https://raw.githubusercontent.com/LuckyLight6/loon-rules/main/rules/3370-slack-workspaces.lsr) |
| 3380 | reddit-community | Reddit 社区、帮助与相关服务 | [订阅](https://raw.githubusercontent.com/LuckyLight6/loon-rules/main/rules/3380-reddit-community.lsr) |
| 3390 | instagram-social | Instagram | [订阅](https://raw.githubusercontent.com/LuckyLight6/loon-rules/main/rules/3390-instagram-social.lsr) |
| 3400 | whatsapp-messaging | WhatsApp 消息、媒体与短链接 | [订阅](https://raw.githubusercontent.com/LuckyLight6/loon-rules/main/rules/3400-whatsapp-messaging.lsr) |
| 3410 | threads-social | Threads | [订阅](https://raw.githubusercontent.com/LuckyLight6/loon-rules/main/rules/3410-threads-social.lsr) |
| 3420 | pinterest-social | Pinterest | [订阅](https://raw.githubusercontent.com/LuckyLight6/loon-rules/main/rules/3420-pinterest-social.lsr) |
| 3430 | bluesky-social | Bluesky 官方应用与网络服务 | [订阅](https://raw.githubusercontent.com/LuckyLight6/loon-rules/main/rules/3430-bluesky-social.lsr) |
| 3440 | lark-international | Lark 国际版协作服务 | [订阅](https://raw.githubusercontent.com/LuckyLight6/loon-rules/main/rules/3440-lark-international.lsr) |
| 3450 | zoom-meetings | Zoom 会议与共用服务 | [订阅](https://raw.githubusercontent.com/LuckyLight6/loon-rules/main/rules/3450-zoom-meetings.lsr) |
| 3460 | xiaomi-international-services | 小米国际社区与应用商店入口 | [订阅](https://raw.githubusercontent.com/LuckyLight6/loon-rules/main/rules/3460-xiaomi-international-services.lsr) |
| 3470 | linkedin-network | LinkedIn | [订阅](https://raw.githubusercontent.com/LuckyLight6/loon-rules/main/rules/3470-linkedin-network.lsr) |
| 3480 | meta-shared-services | Meta、Facebook 与 Messenger 共用服务 | [订阅](https://raw.githubusercontent.com/LuckyLight6/loon-rules/main/rules/3480-meta-shared-services.lsr) |
| 3500 | overseas-payments-all | 海外支付合集 | [订阅](https://raw.githubusercontent.com/LuckyLight6/loon-rules/main/rules/3500-overseas-payments-all.lsr) |
| 3510 | paypal-payments | PayPal 核心支付、验签和静态资源 | [订阅](https://raw.githubusercontent.com/LuckyLight6/loon-rules/main/rules/3510-paypal-payments.lsr) |
| 3520 | stripe-payments | Stripe | [订阅](https://raw.githubusercontent.com/LuckyLight6/loon-rules/main/rules/3520-stripe-payments.lsr) |
| 3530 | link-payments | Link 快捷支付 | [订阅](https://raw.githubusercontent.com/LuckyLight6/loon-rules/main/rules/3530-link-payments.lsr) |
| 3540 | braintree-payments | Braintree 商户支付、网关与 SDK | [订阅](https://raw.githubusercontent.com/LuckyLight6/loon-rules/main/rules/3540-braintree-payments.lsr) |
| 3550 | venmo-payments | Venmo 支付 | [订阅](https://raw.githubusercontent.com/LuckyLight6/loon-rules/main/rules/3550-venmo-payments.lsr) |
| 3560 | xoom-transfers | Xoom 汇款 | [订阅](https://raw.githubusercontent.com/LuckyLight6/loon-rules/main/rules/3560-xoom-transfers.lsr) |
| 3570 | wise-transfers | Wise 转账与账户服务 | [订阅](https://raw.githubusercontent.com/LuckyLight6/loon-rules/main/rules/3570-wise-transfers.lsr) |
| 3580 | tenpay-global-payments | TenPay Global 跨境支付与商户平台 | [订阅](https://raw.githubusercontent.com/LuckyLight6/loon-rules/main/rules/3580-tenpay-global-payments.lsr) |
| 3600 | overseas-crypto-all | 海外加密资产服务合集 | [订阅](https://raw.githubusercontent.com/LuckyLight6/loon-rules/main/rules/3600-overseas-crypto-all.lsr) |
| 3610 | binance-platform | Binance 币安 | [订阅](https://raw.githubusercontent.com/LuckyLight6/loon-rules/main/rules/3610-binance-platform.lsr) |
| 3620 | okx-platform | OKX 欧易 | [订阅](https://raw.githubusercontent.com/LuckyLight6/loon-rules/main/rules/3620-okx-platform.lsr) |
| 3630 | gemini-exchange | Gemini 交易平台与 API | [订阅](https://raw.githubusercontent.com/LuckyLight6/loon-rules/main/rules/3630-gemini-exchange.lsr) |
| 3640 | kraken-exchange | Kraken 交易平台 | [订阅](https://raw.githubusercontent.com/LuckyLight6/loon-rules/main/rules/3640-kraken-exchange.lsr) |
| 3650 | bybit-exchange | Bybit 交易平台 | [订阅](https://raw.githubusercontent.com/LuckyLight6/loon-rules/main/rules/3650-bybit-exchange.lsr) |
| 3660 | kucoin-exchange | KuCoin 交易平台 | [订阅](https://raw.githubusercontent.com/LuckyLight6/loon-rules/main/rules/3660-kucoin-exchange.lsr) |
| 3670 | trust-wallet | Trust Wallet | [订阅](https://raw.githubusercontent.com/LuckyLight6/loon-rules/main/rules/3670-trust-wallet.lsr) |
| 3800 | overseas-media-all | 海外影音与内容合集 | [订阅](https://raw.githubusercontent.com/LuckyLight6/loon-rules/main/rules/3800-overseas-media-all.lsr) |
| 3810 | hbo-streaming | HBO Max | [订阅](https://raw.githubusercontent.com/LuckyLight6/loon-rules/main/rules/3810-hbo-streaming.lsr) |
| 3820 | netflix-video-and-delivery | Netflix 播放、设备 API 和内容分发 | [订阅](https://raw.githubusercontent.com/LuckyLight6/loon-rules/main/rules/3820-netflix-video-and-delivery.lsr) |
| 3830 | disney-plus-streaming | Disney+ 播放及其专用交付 | [订阅](https://raw.githubusercontent.com/LuckyLight6/loon-rules/main/rules/3830-disney-plus-streaming.lsr) |
| 3840 | prime-video-streaming | Prime Video 视频 API 和内容 | [订阅](https://raw.githubusercontent.com/LuckyLight6/loon-rules/main/rules/3840-prime-video-streaming.lsr) |
| 3850 | hulu-streaming | Hulu 视频与交付 | [订阅](https://raw.githubusercontent.com/LuckyLight6/loon-rules/main/rules/3850-hulu-streaming.lsr) |
| 3860 | youtube-video-and-cdn | YouTube 视频、音乐、频道与专用 CDN | [订阅](https://raw.githubusercontent.com/LuckyLight6/loon-rules/main/rules/3860-youtube-video-and-cdn.lsr) |
| 3870 | tiktok-international-video | TikTok 国际短视频与直播 | [订阅](https://raw.githubusercontent.com/LuckyLight6/loon-rules/main/rules/3870-tiktok-international-video.lsr) |
| 3880 | bilibili-international-video | 哔哩哔哩国际版视频 | [订阅](https://raw.githubusercontent.com/LuckyLight6/loon-rules/main/rules/3880-bilibili-international-video.lsr) |
| 3890 | iqiyi-international | 爱奇艺国际版 iQIYI 与专用国际 API | [订阅](https://raw.githubusercontent.com/LuckyLight6/loon-rules/main/rules/3890-iqiyi-international.lsr) |
| 3900 | vimeo-video | Vimeo 视频与交付 | [订阅](https://raw.githubusercontent.com/LuckyLight6/loon-rules/main/rules/3900-vimeo-video.lsr) |
| 3910 | spotify-audio | Spotify 音乐、播客及相关网站 | [订阅](https://raw.githubusercontent.com/LuckyLight6/loon-rules/main/rules/3910-spotify-audio.lsr) |
| 3920 | soundcloud-audio | SoundCloud 音频与创作者服务 | [订阅](https://raw.githubusercontent.com/LuckyLight6/loon-rules/main/rules/3920-soundcloud-audio.lsr) |
| 3930 | twitch-live-video | Twitch 直播、聊天室和内容 CDN | [订阅](https://raw.githubusercontent.com/LuckyLight6/loon-rules/main/rules/3930-twitch-live-video.lsr) |
| 3940 | bbc-news-and-video | BBC 新闻与影音 | [订阅](https://raw.githubusercontent.com/LuckyLight6/loon-rules/main/rules/3940-bbc-news-and-video.lsr) |
| 3950 | bahamut-video-and-community | 巴哈姆特动画疯和电玩社区 | [订阅](https://raw.githubusercontent.com/LuckyLight6/loon-rules/main/rules/3950-bahamut-video-and-community.lsr) |
| 4100 | overseas-games-all | 海外游戏合集 | [订阅](https://raw.githubusercontent.com/LuckyLight6/loon-rules/main/rules/4100-overseas-games-all.lsr) |
| 4110 | steam-international-platform | Steam 国际商店、社区、联机和下载 | [订阅](https://raw.githubusercontent.com/LuckyLight6/loon-rules/main/rules/4110-steam-international-platform.lsr) |
| 4120 | epic-games-services | Epic Games 商店、登录及 Unreal 服务 | [订阅](https://raw.githubusercontent.com/LuckyLight6/loon-rules/main/rules/4120-epic-games-services.lsr) |
| 4130 | playstation-network | Sony PlayStation | [订阅](https://raw.githubusercontent.com/LuckyLight6/loon-rules/main/rules/4130-playstation-network.lsr) |
| 4140 | nintendo-platform | Nintendo 任天堂 | [订阅](https://raw.githubusercontent.com/LuckyLight6/loon-rules/main/rules/4140-nintendo-platform.lsr) |
| 4150 | hoyoverse-international | HoYoverse 国际版 | [订阅](https://raw.githubusercontent.com/LuckyLight6/loon-rules/main/rules/4150-hoyoverse-international.lsr) |
| 4160 | ea-games | EA 游戏平台 | [订阅](https://raw.githubusercontent.com/LuckyLight6/loon-rules/main/rules/4160-ea-games.lsr) |
| 4170 | ubisoft-connect | Ubisoft Connect | [订阅](https://raw.githubusercontent.com/LuckyLight6/loon-rules/main/rules/4170-ubisoft-connect.lsr) |
| 4180 | blizzard-battlenet | Blizzard / Battle.net 国际服务 | [订阅](https://raw.githubusercontent.com/LuckyLight6/loon-rules/main/rules/4180-blizzard-battlenet.lsr) |
| 4190 | netease-international-games | 网易国际游戏与共用 SDK | [订阅](https://raw.githubusercontent.com/LuckyLight6/loon-rules/main/rules/4190-netease-international-games.lsr) |
| 4300 | overseas-productivity-all | 海外办公、邮件与协作合集 | [订阅](https://raw.githubusercontent.com/LuckyLight6/loon-rules/main/rules/4300-overseas-productivity-all.lsr) |
| 4310 | notion-workspace | Notion | [订阅](https://raw.githubusercontent.com/LuckyLight6/loon-rules/main/rules/4310-notion-workspace.lsr) |
| 4320 | figma-design | Figma | [订阅](https://raw.githubusercontent.com/LuckyLight6/loon-rules/main/rules/4320-figma-design.lsr) |
| 4330 | trello-boards | Trello | [订阅](https://raw.githubusercontent.com/LuckyLight6/loon-rules/main/rules/4330-trello-boards.lsr) |
| 4340 | atlassian-cloud-services | Atlassian Cloud：共享平台、Jira 与 Confluence | [订阅](https://raw.githubusercontent.com/LuckyLight6/loon-rules/main/rules/4340-atlassian-cloud-services.lsr) |
| 4350 | proton-suite | Proton 邮件、账户及共用服务 | [订阅](https://raw.githubusercontent.com/LuckyLight6/loon-rules/main/rules/4350-proton-suite.lsr) |
| 4360 | intercom-customer-support | Intercom 客服、会话、附件与实时通信 | [订阅](https://raw.githubusercontent.com/LuckyLight6/loon-rules/main/rules/4360-intercom-customer-support.lsr) |
| 4500 | google-all | Google 日常服务合集 | [订阅](https://raw.githubusercontent.com/LuckyLight6/loon-rules/main/rules/4500-google-all.lsr) |
| 4510 | google-account-authentication | Google 共享账号、地区登录、OAuth 授权与换令牌 | [订阅](https://raw.githubusercontent.com/LuckyLight6/loon-rules/main/rules/4510-google-account-authentication.lsr) |
| 4520 | google-gmail-mail | Gmail 网页、邮件协议、专用 API 与投递诊断 | [订阅](https://raw.githubusercontent.com/LuckyLight6/loon-rules/main/rules/4520-google-gmail-mail.lsr) |
| 4530 | google-meet-meetings | Google Meet 会议、API 与 Workspace 共用音视频媒体 | [订阅](https://raw.githubusercontent.com/LuckyLight6/loon-rules/main/rules/4530-google-meet-meetings.lsr) |
| 4540 | google-drive-and-documents | Google Drive、文档和上传下载入口 | [订阅](https://raw.githubusercontent.com/LuckyLight6/loon-rules/main/rules/4540-google-drive-and-documents.lsr) |
| 4550 | google-play-services | Google Play 商店、应用管理与专用 API | [订阅](https://raw.githubusercontent.com/LuckyLight6/loon-rules/main/rules/4550-google-play-services.lsr) |
| 4560 | google-play-games | Google Play 游戏、发布与管理 API | [订阅](https://raw.githubusercontent.com/LuckyLight6/loon-rules/main/rules/4560-google-play-games.lsr) |
| 4570 | google-software-downloads | Google 软件和更新已知下载主机 | [订阅](https://raw.githubusercontent.com/LuckyLight6/loon-rules/main/rules/4570-google-software-downloads.lsr) |
| 4580 | google-scholar | Google 学术搜索 | [订阅](https://raw.githubusercontent.com/LuckyLight6/loon-rules/main/rules/4580-google-scholar.lsr) |
| 4585 | google-firebase-messaging | Google Firebase Cloud Messaging 推送与令牌注册 | [订阅](https://raw.githubusercontent.com/LuckyLight6/loon-rules/main/rules/4585-google-firebase-messaging.lsr) |
| 4590 | google-platform-services | Google 搜索、官方资讯、安全浏览 API 与共享平台兜底 | [订阅](https://raw.githubusercontent.com/LuckyLight6/loon-rules/main/rules/4590-google-platform-services.lsr) |
| 4700 | microsoft-all | Microsoft 日常服务合集 | [订阅](https://raw.githubusercontent.com/LuckyLight6/loon-rules/main/rules/4700-microsoft-all.lsr) |
| 4710 | microsoft-account-authentication | Microsoft 个人账户与 Entra 登录 | [订阅](https://raw.githubusercontent.com/LuckyLight6/loon-rules/main/rules/4710-microsoft-account-authentication.lsr) |
| 4720 | microsoft-outlook-mail | Outlook 与 Exchange Online 邮箱入口 | [订阅](https://raw.githubusercontent.com/LuckyLight6/loon-rules/main/rules/4720-microsoft-outlook-mail.lsr) |
| 4730 | microsoft-teams-meetings | Teams 会议及 Skype for Business 共用通信入口 | [订阅](https://raw.githubusercontent.com/LuckyLight6/loon-rules/main/rules/4730-microsoft-teams-meetings.lsr) |
| 4740 | microsoft-files-and-sharepoint | OneDrive 与 SharePoint 文件与同步 | [订阅](https://raw.githubusercontent.com/LuckyLight6/loon-rules/main/rules/4740-microsoft-files-and-sharepoint.lsr) |
| 4750 | microsoft-store-services | Microsoft Store 商店目录与加载 | [订阅](https://raw.githubusercontent.com/LuckyLight6/loon-rules/main/rules/4750-microsoft-store-services.lsr) |
| 4760 | microsoft-windows-update-services | Windows Update 检查与传递优化协调 | [订阅](https://raw.githubusercontent.com/LuckyLight6/loon-rules/main/rules/4760-microsoft-windows-update-services.lsr) |
| 4770 | microsoft-update-and-store-downloads | Windows 更新和 Microsoft Store 已知内容下载 | [订阅](https://raw.githubusercontent.com/LuckyLight6/loon-rules/main/rules/4770-microsoft-update-and-store-downloads.lsr) |
| 4780 | microsoft-office-downloads | Microsoft Office 安装与更新下载 | [订阅](https://raw.githubusercontent.com/LuckyLight6/loon-rules/main/rules/4780-microsoft-office-downloads.lsr) |
| 4790 | microsoft-vscode | Microsoft Visual Studio Code | [订阅](https://raw.githubusercontent.com/LuckyLight6/loon-rules/main/rules/4790-microsoft-vscode.lsr) |
| 4800 | microsoft-power-bi | Microsoft Power BI | [订阅](https://raw.githubusercontent.com/LuckyLight6/loon-rules/main/rules/4800-microsoft-power-bi.lsr) |
| 4810 | microsoft-xbox-services | Xbox Live 已知登录与服务端点 | [订阅](https://raw.githubusercontent.com/LuckyLight6/loon-rules/main/rules/4810-microsoft-xbox-services.lsr) |
| 4820 | microsoft-platform-services | Microsoft 通用客户端和共享服务兜底 | [订阅](https://raw.githubusercontent.com/LuckyLight6/loon-rules/main/rules/4820-microsoft-platform-services.lsr) |
| 4900 | multinational-mainland-all | 跨国厂商国内可用服务合集 | [订阅](https://raw.githubusercontent.com/LuckyLight6/loon-rules/main/rules/4900-multinational-mainland-all.lsr) |
| 4910 | qualcomm-mainland | 高通中国与国内可用系统服务 | [订阅](https://raw.githubusercontent.com/LuckyLight6/loon-rules/main/rules/4910-qualcomm-mainland.lsr) |
| 4920 | nvidia-mainland | NVIDIA 中国网站与国内下载入口 | [订阅](https://raw.githubusercontent.com/LuckyLight6/loon-rules/main/rules/4920-nvidia-mainland.lsr) |
| 4930 | intel-mainland | Intel 中国网站 | [订阅](https://raw.githubusercontent.com/LuckyLight6/loon-rules/main/rules/4930-intel-mainland.lsr) |
| 4940 | samsung-mainland | Samsung 中国网站、云与健康服务 | [订阅](https://raw.githubusercontent.com/LuckyLight6/loon-rules/main/rules/4940-samsung-mainland.lsr) |
| 4950 | cloudflare-mainland | Cloudflare 中国网络相关入口 | [订阅](https://raw.githubusercontent.com/LuckyLight6/loon-rules/main/rules/4950-cloudflare-mainland.lsr) |
| 4960 | adobe-mainland | Adobe 中国区文档云入口 | [订阅](https://raw.githubusercontent.com/LuckyLight6/loon-rules/main/rules/4960-adobe-mainland.lsr) |
| 4970 | amazon-mainland | Amazon 与 AWS 中国区入口 | [订阅](https://raw.githubusercontent.com/LuckyLight6/loon-rules/main/rules/4970-amazon-mainland.lsr) |
| 4980 | microsoft-china-cloud-controls | Microsoft Azure 中国区登录与控制端点 | [订阅](https://raw.githubusercontent.com/LuckyLight6/loon-rules/main/rules/4980-microsoft-china-cloud-controls.lsr) |
| 6000 | ai-cn-all | 国产 AI 国内版与共用入口合集 | [订阅](https://raw.githubusercontent.com/LuckyLight6/loon-rules/main/rules/6000-ai-cn-all.lsr) |
| 6010 | qwen-mainland | 阿里千问与百炼 · 国内入口 | [订阅](https://raw.githubusercontent.com/LuckyLight6/loon-rules/main/rules/6010-qwen-mainland.lsr) |
| 6020 | kimi-mainland | 月之暗面 Kimi · 国内入口 | [订阅](https://raw.githubusercontent.com/LuckyLight6/loon-rules/main/rules/6020-kimi-mainland.lsr) |
| 6030 | zhipu-mainland | 智谱 · 国内入口 | [订阅](https://raw.githubusercontent.com/LuckyLight6/loon-rules/main/rules/6030-zhipu-mainland.lsr) |
| 6040 | minimax-mainland | MiniMax 与海螺 · 国内入口 | [订阅](https://raw.githubusercontent.com/LuckyLight6/loon-rules/main/rules/6040-minimax-mainland.lsr) |
| 6050 | bytedance-mainland | 字节豆包、扣子与模型平台 · 国内入口 | [订阅](https://raw.githubusercontent.com/LuckyLight6/loon-rules/main/rules/6050-bytedance-mainland.lsr) |
| 6060 | siliconflow-mainland | 硅基流动 · 国内入口 | [订阅](https://raw.githubusercontent.com/LuckyLight6/loon-rules/main/rules/6060-siliconflow-mainland.lsr) |
| 6070 | tencent-mainland | 腾讯混元、元宝与 TokenHub · 国内入口 | [订阅](https://raw.githubusercontent.com/LuckyLight6/loon-rules/main/rules/6070-tencent-mainland.lsr) |
| 6080 | deepseek-mainland | DeepSeek · 国内入口 | [订阅](https://raw.githubusercontent.com/LuckyLight6/loon-rules/main/rules/6080-deepseek-mainland.lsr) |
| 6090 | baidu-mainland | 百度文心与千帆 | [订阅](https://raw.githubusercontent.com/LuckyLight6/loon-rules/main/rules/6090-baidu-mainland.lsr) |
| 6100 | iflytek-mainland | 讯飞星火 · 国内入口 | [订阅](https://raw.githubusercontent.com/LuckyLight6/loon-rules/main/rules/6100-iflytek-mainland.lsr) |
| 6110 | liblib-mainland | 哩布哩布 · 国内入口 | [订阅](https://raw.githubusercontent.com/LuckyLight6/loon-rules/main/rules/6110-liblib-mainland.lsr) |
| 6120 | baichuan-mainland | 百川智能 · 国内入口 | [订阅](https://raw.githubusercontent.com/LuckyLight6/loon-rules/main/rules/6120-baichuan-mainland.lsr) |
| 6130 | lingyi-mainland | 零一万物 · 国内入口 | [订阅](https://raw.githubusercontent.com/LuckyLight6/loon-rules/main/rules/6130-lingyi-mainland.lsr) |
| 6140 | stepfun-mainland | 阶跃星辰 · 国内入口 | [订阅](https://raw.githubusercontent.com/LuckyLight6/loon-rules/main/rules/6140-stepfun-mainland.lsr) |
| 6150 | sensetime-mainland | 商汤日日新 · 国内入口 | [订阅](https://raw.githubusercontent.com/LuckyLight6/loon-rules/main/rules/6150-sensetime-mainland.lsr) |
| 6160 | modelscope-mainland | 魔搭 ModelScope · 模型 API | [订阅](https://raw.githubusercontent.com/LuckyLight6/loon-rules/main/rules/6160-modelscope-mainland.lsr) |
| 6170 | xiaomi-mainland-and-shared | 小米 MiMo · 国内计划与共用 API | [订阅](https://raw.githubusercontent.com/LuckyLight6/loon-rules/main/rules/6170-xiaomi-mainland-and-shared.lsr) |
| 6250 | ai-overseas-mainland-all | 海外 AI 中国区服务合集 | [订阅](https://raw.githubusercontent.com/LuckyLight6/loon-rules/main/rules/6250-ai-overseas-mainland-all.lsr) |
| 6260 | jetbrains-ai-mainland | JetBrains AI · 中国区 API | [订阅](https://raw.githubusercontent.com/LuckyLight6/loon-rules/main/rules/6260-jetbrains-ai-mainland.lsr) |
| 6300 | mainland-development-all | 国内开发合集 | [订阅](https://raw.githubusercontent.com/LuckyLight6/loon-rules/main/rules/6300-mainland-development-all.lsr) |
| 6310 | gitee-hosting | Gitee 码云 | [订阅](https://raw.githubusercontent.com/LuckyLight6/loon-rules/main/rules/6310-gitee-hosting.lsr) |
| 6320 | coding-platform | 腾讯 CODING | [订阅](https://raw.githubusercontent.com/LuckyLight6/loon-rules/main/rules/6320-coding-platform.lsr) |
| 6330 | gitcode-hosting | GitCode | [订阅](https://raw.githubusercontent.com/LuckyLight6/loon-rules/main/rules/6330-gitcode-hosting.lsr) |
| 6340 | npmmirror-registry | npmmirror 国内镜像 | [订阅](https://raw.githubusercontent.com/LuckyLight6/loon-rules/main/rules/6340-npmmirror-registry.lsr) |
| 6350 | tuna-mirrors | 清华 TUNA 开源镜像 | [订阅](https://raw.githubusercontent.com/LuckyLight6/loon-rules/main/rules/6350-tuna-mirrors.lsr) |
| 6500 | mainland-social-all | 国内通讯与社交合集 | [订阅](https://raw.githubusercontent.com/LuckyLight6/loon-rules/main/rules/6500-mainland-social-all.lsr) |
| 6510 | wechat-shared-and-mainland | 微信国内与两版共用登录、消息和 App 服务 | [订阅](https://raw.githubusercontent.com/LuckyLight6/loon-rules/main/rules/6510-wechat-shared-and-mainland.lsr) |
| 6520 | dingtalk-public | 钉钉公共服务 | [订阅](https://raw.githubusercontent.com/LuckyLight6/loon-rules/main/rules/6520-dingtalk-public.lsr) |
| 6530 | feishu-mainland | 飞书国内协作服务 | [订阅](https://raw.githubusercontent.com/LuckyLight6/loon-rules/main/rules/6530-feishu-mainland.lsr) |
| 6540 | weibo-social | 微博 | [订阅](https://raw.githubusercontent.com/LuckyLight6/loon-rules/main/rules/6540-weibo-social.lsr) |
| 6550 | douban-community | 豆瓣 | [订阅](https://raw.githubusercontent.com/LuckyLight6/loon-rules/main/rules/6550-douban-community.lsr) |
| 6560 | xiaohongshu-community | 小红书国内内容、社区及专用 CDN | [订阅](https://raw.githubusercontent.com/LuckyLight6/loon-rules/main/rules/6560-xiaohongshu-community.lsr) |
| 6570 | zhihu-community | 知乎 | [订阅](https://raw.githubusercontent.com/LuckyLight6/loon-rules/main/rules/6570-zhihu-community.lsr) |
| 6700 | mainland-payments-all | 国内支付合集 | [订阅](https://raw.githubusercontent.com/LuckyLight6/loon-rules/main/rules/6700-mainland-payments-all.lsr) |
| 6710 | alipay-mainland-payments | 支付宝国内账户支付和静态资源 | [订阅](https://raw.githubusercontent.com/LuckyLight6/loon-rules/main/rules/6710-alipay-mainland-payments.lsr) |
| 6720 | unionpay-mainland | 银联、云闪付国内服务 | [订阅](https://raw.githubusercontent.com/LuckyLight6/loon-rules/main/rules/6720-unionpay-mainland.lsr) |
| 6730 | tenpay-mainland-payments | 财付通与 QQ 钱包共用支付 | [订阅](https://raw.githubusercontent.com/LuckyLight6/loon-rules/main/rules/6730-tenpay-mainland-payments.lsr) |
| 6900 | mainland-media-all | 国内影音与直播合集 | [订阅](https://raw.githubusercontent.com/LuckyLight6/loon-rules/main/rules/6900-mainland-media-all.lsr) |
| 6910 | bilibili-mainland-video | 哔哩哔哩中国站视频与图片 | [订阅](https://raw.githubusercontent.com/LuckyLight6/loon-rules/main/rules/6910-bilibili-mainland-video.lsr) |
| 6920 | iqiyi-mainland | 爱奇艺国内版 | [订阅](https://raw.githubusercontent.com/LuckyLight6/loon-rules/main/rules/6920-iqiyi-mainland.lsr) |
| 6930 | youku-video | 优酷国内站 | [订阅](https://raw.githubusercontent.com/LuckyLight6/loon-rules/main/rules/6930-youku-video.lsr) |
| 6940 | qq-music | QQ 音乐 | [订阅](https://raw.githubusercontent.com/LuckyLight6/loon-rules/main/rules/6940-qq-music.lsr) |
| 6950 | kugou-music | 酷狗音乐 | [订阅](https://raw.githubusercontent.com/LuckyLight6/loon-rules/main/rules/6950-kugou-music.lsr) |
| 6960 | netease-music | 网易云音乐 | [订阅](https://raw.githubusercontent.com/LuckyLight6/loon-rules/main/rules/6960-netease-music.lsr) |
| 6970 | douyin-mainland-video | 抖音中国版短视频、直播、图片与素材 | [订阅](https://raw.githubusercontent.com/LuckyLight6/loon-rules/main/rules/6970-douyin-mainland-video.lsr) |
| 6980 | kuaishou-video | 快手 | [订阅](https://raw.githubusercontent.com/LuckyLight6/loon-rules/main/rules/6980-kuaishou-video.lsr) |
| 6990 | douyu-live | 斗鱼直播 | [订阅](https://raw.githubusercontent.com/LuckyLight6/loon-rules/main/rules/6990-douyu-live.lsr) |
| 7000 | huya-live | 虎牙直播 | [订阅](https://raw.githubusercontent.com/LuckyLight6/loon-rules/main/rules/7000-huya-live.lsr) |
| 7200 | mainland-games-all | 国内游戏合集 | [订阅](https://raw.githubusercontent.com/LuckyLight6/loon-rules/main/rules/7200-mainland-games-all.lsr) |
| 7210 | steam-mainland-downloads | Steam 中国下载镜像与蒸汽平台内容 | [订阅](https://raw.githubusercontent.com/LuckyLight6/loon-rules/main/rules/7210-steam-mainland-downloads.lsr) |
| 7220 | mihoyo-mainland | 米哈游国服与米游社 | [订阅](https://raw.githubusercontent.com/LuckyLight6/loon-rules/main/rules/7220-mihoyo-mainland.lsr) |
| 7230 | wegame-mainland | 腾讯 WeGame 国内平台 | [订阅](https://raw.githubusercontent.com/LuckyLight6/loon-rules/main/rules/7230-wegame-mainland.lsr) |
| 7400 | mainland-daily-services-all | 国内购物、生活与办公合集 | [订阅](https://raw.githubusercontent.com/LuckyLight6/loon-rules/main/rules/7400-mainland-daily-services-all.lsr) |
| 7410 | taobao-and-xianyu-shopping | 淘宝、天猫、闲鱼购物与图片 | [订阅](https://raw.githubusercontent.com/LuckyLight6/loon-rules/main/rules/7410-taobao-and-xianyu-shopping.lsr) |
| 7420 | jingdong-shopping | 京东购物、账户与商品素材 | [订阅](https://raw.githubusercontent.com/LuckyLight6/loon-rules/main/rules/7420-jingdong-shopping.lsr) |
| 7430 | railway-tickets | 铁路 12306 | [订阅](https://raw.githubusercontent.com/LuckyLight6/loon-rules/main/rules/7430-railway-tickets.lsr) |
| 7440 | meituan-services | 美团与大众点评服务 | [订阅](https://raw.githubusercontent.com/LuckyLight6/loon-rules/main/rules/7440-meituan-services.lsr) |
| 7450 | didi-mobility | 滴滴出行 | [订阅](https://raw.githubusercontent.com/LuckyLight6/loon-rules/main/rules/7450-didi-mobility.lsr) |
| 7460 | youdao-products | 有道词典、学习与内容服务 | [订阅](https://raw.githubusercontent.com/LuckyLight6/loon-rules/main/rules/7460-youdao-products.lsr) |
| 7470 | aliyun-drive | 阿里云盘 | [订阅](https://raw.githubusercontent.com/LuckyLight6/loon-rules/main/rules/7470-aliyun-drive.lsr) |
| 7480 | wps-office | WPS Office 与文档服务 | [订阅](https://raw.githubusercontent.com/LuckyLight6/loon-rules/main/rules/7480-wps-office.lsr) |
| 8000 | global-platforms-all | 全球厂商与云平台共用服务合集 | [订阅](https://raw.githubusercontent.com/LuckyLight6/loon-rules/main/rules/8000-global-platforms-all.lsr) |
| 8010 | digitalocean-services | DigitalOcean 云平台与共用服务 | [订阅](https://raw.githubusercontent.com/LuckyLight6/loon-rules/main/rules/8010-digitalocean-services.lsr) |
| 8020 | vultr-services | Vultr 云平台 | [订阅](https://raw.githubusercontent.com/LuckyLight6/loon-rules/main/rules/8020-vultr-services.lsr) |
| 8030 | hetzner-services | Hetzner 云与存储平台 | [订阅](https://raw.githubusercontent.com/LuckyLight6/loon-rules/main/rules/8030-hetzner-services.lsr) |
| 8040 | vercel-shared-services | Vercel、Next.js 与共用托管平台 | [订阅](https://raw.githubusercontent.com/LuckyLight6/loon-rules/main/rules/8040-vercel-shared-services.lsr) |
| 8050 | netlify-services | Netlify 云平台与资源交付 | [订阅](https://raw.githubusercontent.com/LuckyLight6/loon-rules/main/rules/8050-netlify-services.lsr) |
| 8060 | heroku-services | Heroku 云平台与共用托管 | [订阅](https://raw.githubusercontent.com/LuckyLight6/loon-rules/main/rules/8060-heroku-services.lsr) |
| 8070 | oracle-shared-services | Oracle、Java 与云平台共用服务 | [订阅](https://raw.githubusercontent.com/LuckyLight6/loon-rules/main/rules/8070-oracle-shared-services.lsr) |
| 8080 | adobe-shared-services | Adobe Creative Cloud、Acrobat 与共用平台 | [订阅](https://raw.githubusercontent.com/LuckyLight6/loon-rules/main/rules/8080-adobe-shared-services.lsr) |
| 8090 | cloudflare-shared-services | Cloudflare 控制台、WARP、Tunnel 与共用平台 | [订阅](https://raw.githubusercontent.com/LuckyLight6/loon-rules/main/rules/8090-cloudflare-shared-services.lsr) |
| 8100 | amazon-shared-services | Amazon、AWS 与共用云平台 | [订阅](https://raw.githubusercontent.com/LuckyLight6/loon-rules/main/rules/8100-amazon-shared-services.lsr) |
| 8110 | discord-activities-proxy | Discord Activities 与第三方应用代理 | [订阅](https://raw.githubusercontent.com/LuckyLight6/loon-rules/main/rules/8110-discord-activities-proxy.lsr) |
| 8200 | overseas-extra-all | 海外补充合集 | [订阅](https://raw.githubusercontent.com/LuckyLight6/loon-rules/main/rules/8200-overseas-extra-all.lsr) |
| 8210 | overseas-media-extra | 其他海外影音 | [订阅](https://raw.githubusercontent.com/LuckyLight6/loon-rules/main/rules/8210-overseas-media-extra.lsr) |
| 8220 | overseas-sites-extra | 其他海外网站与受限站点 | [订阅](https://raw.githubusercontent.com/LuckyLight6/loon-rules/main/rules/8220-overseas-sites-extra.lsr) |
| 8400 | mainland-platforms-all | 国内厂商共用服务合集 | [订阅](https://raw.githubusercontent.com/LuckyLight6/loon-rules/main/rules/8400-mainland-platforms-all.lsr) |
| 8410 | netease-shared-services | 网易邮件、游戏、新闻与其他共用服务 | [订阅](https://raw.githubusercontent.com/LuckyLight6/loon-rules/main/rules/8410-netease-shared-services.lsr) |
| 8420 | alibaba-shared-services | 阿里巴巴与阿里云共用服务 | [订阅](https://raw.githubusercontent.com/LuckyLight6/loon-rules/main/rules/8420-alibaba-shared-services.lsr) |
| 8425 | tencent-shared-content-and-sdk | 腾讯共用图片、头像、下载与 SDK | [订阅](https://raw.githubusercontent.com/LuckyLight6/loon-rules/main/rules/8425-tencent-shared-content-and-sdk.lsr) |
| 8430 | tencent-shared-services | 腾讯 QQ、邮箱、网站与共用服务 | [订阅](https://raw.githubusercontent.com/LuckyLight6/loon-rules/main/rules/8430-tencent-shared-services.lsr) |
| 8440 | bytedance-shared-services | 字节跳动国内与共用服务 | [订阅](https://raw.githubusercontent.com/LuckyLight6/loon-rules/main/rules/8440-bytedance-shared-services.lsr) |
| 8450 | baidu-shared-services | 百度搜索、网盘与共用服务 | [订阅](https://raw.githubusercontent.com/LuckyLight6/loon-rules/main/rules/8450-baidu-shared-services.lsr) |
| 8460 | huawei-shared-services | 华为账户、设备与共用服务 | [订阅](https://raw.githubusercontent.com/LuckyLight6/loon-rules/main/rules/8460-huawei-shared-services.lsr) |
| 8470 | xiaomi-shared-services | 小米账户、设备与共用服务 | [订阅](https://raw.githubusercontent.com/LuckyLight6/loon-rules/main/rules/8470-xiaomi-shared-services.lsr) |
| 8480 | kingsoft-shared-services | 金山与其他共用服务 | [订阅](https://raw.githubusercontent.com/LuckyLight6/loon-rules/main/rules/8480-kingsoft-shared-services.lsr) |
| 8490 | sina-shared-image-assets | 新浪与微博共用图片 | [订阅](https://raw.githubusercontent.com/LuckyLight6/loon-rules/main/rules/8490-sina-shared-image-assets.lsr) |
| 8495 | sina-web-and-shared-services | 新浪网站、新闻、邮箱与网页服务 | [订阅](https://raw.githubusercontent.com/LuckyLight6/loon-rules/main/rules/8495-sina-web-and-shared-services.lsr) |
| 8600 | mainland-routing-all | 国内补充合集 | [订阅](https://raw.githubusercontent.com/LuckyLight6/loon-rules/main/rules/8600-mainland-routing-all.lsr) |
| 8610 | mainland-domains | 未由专项认领的国内域名补充 | [订阅](https://raw.githubusercontent.com/LuckyLight6/loon-rules/main/rules/8610-mainland-domains.lsr) |
| 8620 | mainland-networks | 可按 IPv4 / IPv6 网段判断的国内地址 | [订阅](https://raw.githubusercontent.com/LuckyLight6/loon-rules/main/rules/8620-mainland-networks.lsr) |
| 8630 | mainland-geoip | 设备 GeoIP 数据库中的中国大陆地址兜底 | [订阅](https://raw.githubusercontent.com/LuckyLight6/loon-rules/main/rules/8630-mainland-geoip.lsr) |

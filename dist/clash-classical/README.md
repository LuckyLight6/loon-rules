# Mihomo / Stash 规则

从同一份规则生成，编号和选择顺序与[主清单](../../docs/rules.md)一致。合集与成员二选一

使用前阅读[客户端格式与限制](../../docs/clients.md)。标为无法转换的组不提供删减版订阅

| 序号 | 英文名称 | 中文名称 | 订阅 / 状态 |
|---|---|---|---|
| 0110 | local-links-and-addresses | 局域网名称、路由器、反查与保留地址 | [订阅](https://raw.githubusercontent.com/LuckyLight6/loon-rules/main/dist/clash-classical/0110-local-links-and-addresses.yaml) |
| 0120 | local-no-resolve-alt | 局域网管理名与已知 IP：不为匹配触发 DNS | [订阅](https://raw.githubusercontent.com/LuckyLight6/loon-rules/main/dist/clash-classical/0120-local-no-resolve-alt.yaml) |
| 0130 | network-sign-in-and-probes | 公共 Wi-Fi 登录、系统网络检查与必需安全连接 | [订阅](https://raw.githubusercontent.com/LuckyLight6/loon-rules/main/dist/clash-classical/0130-network-sign-in-and-probes.yaml) |
| 0140 | tailscale-control-and-tailnet | Tailscale 控制面、公开中继与 Tailnet 域名 | [订阅](https://raw.githubusercontent.com/LuckyLight6/loon-rules/main/dist/clash-classical/0140-tailscale-control-and-tailnet.yaml) |
| 0150 | ip-egress-checks | 查询当前公网出口：国内检测页、IPv4、IPv6 和双栈 API | [订阅](https://raw.githubusercontent.com/LuckyLight6/loon-rules/main/dist/clash-classical/0150-ip-egress-checks.yaml) |
| 0160 | cloudflare-public-dns | Cloudflare 公共 DNS 与标准解析器地址 | [订阅](https://raw.githubusercontent.com/LuckyLight6/loon-rules/main/dist/clash-classical/0160-cloudflare-public-dns.yaml) |
| 0210 | apple-and-ai-privacy-exceptions | Apple 广告与 OpenAI 广告像素的已核实拒绝项 | [订阅](https://raw.githubusercontent.com/LuckyLight6/loon-rules/main/dist/clash-classical/0210-apple-and-ai-privacy-exceptions.yaml) |
| 0220 | general-ad-and-tracking | Repcz 广告与追踪拦截 | [订阅](https://raw.githubusercontent.com/LuckyLight6/loon-rules/main/dist/clash-classical/0220-general-ad-and-tracking.yaml) |
| 0230 | privacy-public-stun-endpoints | 已公开的 STUN 主机，供选择性阻断 | [订阅](https://raw.githubusercontent.com/LuckyLight6/loon-rules/main/dist/clash-classical/0230-privacy-public-stun-endpoints.yaml) |
| 0240 | extended-ad-and-tracking | 可选的扩展广告与统计拦截 | [订阅](https://raw.githubusercontent.com/LuckyLight6/loon-rules/main/dist/clash-classical/0240-extended-ad-and-tracking.yaml) |
| 1000 | ai-overseas-all | 海外 AI 合集 | [订阅](https://raw.githubusercontent.com/LuckyLight6/loon-rules/main/dist/clash-classical/1000-ai-overseas-all.yaml) |
| 1010 | claude-connections | Claude 登录、API、MCP、更新、附件和 Artifact | [订阅](https://raw.githubusercontent.com/LuckyLight6/loon-rules/main/dist/clash-classical/1010-claude-connections.yaml) |
| 1020 | chatgpt-connections | ChatGPT、Codex、OpenAI API、语音信令与媒体连接 | [订阅](https://raw.githubusercontent.com/LuckyLight6/loon-rules/main/dist/clash-classical/1020-chatgpt-connections.yaml) |
| 1030 | gemini-connections | Gemini、AI Studio、NotebookLM、Google AI API 和专用 WebChannel | [订阅](https://raw.githubusercontent.com/LuckyLight6/loon-rules/main/dist/clash-classical/1030-gemini-connections.yaml) |
| 1040 | xai-connections | xAI 账号、Grok 对话与模型 API | [订阅](https://raw.githubusercontent.com/LuckyLight6/loon-rules/main/dist/clash-classical/1040-xai-connections.yaml) |
| 1050 | grokipedia-encyclopedia | Grokipedia AI 百科站点 | [订阅](https://raw.githubusercontent.com/LuckyLight6/loon-rules/main/dist/clash-classical/1050-grokipedia-encyclopedia.yaml) |
| 1060 | github-copilot-connections | Copilot API、补全、对话及已证实的附件服务 | [订阅](https://raw.githubusercontent.com/LuckyLight6/loon-rules/main/dist/clash-classical/1060-github-copilot-connections.yaml) |
| 1070 | microsoft-copilot-connections | Microsoft Copilot 个人版与工作版独立入口 | [订阅](https://raw.githubusercontent.com/LuckyLight6/loon-rules/main/dist/clash-classical/1070-microsoft-copilot-connections.yaml) |
| 1080 | meta-ai-assistant | Meta AI 助手、Llama 与专用内容入口 | [订阅](https://raw.githubusercontent.com/LuckyLight6/loon-rules/main/dist/clash-classical/1080-meta-ai-assistant.yaml) |
| 1090 | muse-agent | Muse 独立个人助手与其专用入口 | [订阅](https://raw.githubusercontent.com/LuckyLight6/loon-rules/main/dist/clash-classical/1090-muse-agent.yaml) |
| 1100 | cursor-editor-and-api | Cursor 客户端及专用接口 | [订阅](https://raw.githubusercontent.com/LuckyLight6/loon-rules/main/dist/clash-classical/1100-cursor-editor-and-api.yaml) |
| 1110 | perplexity-search-and-api | Perplexity 搜索、API 和专用内容入口 | [订阅](https://raw.githubusercontent.com/LuckyLight6/loon-rules/main/dist/clash-classical/1110-perplexity-search-and-api.yaml) |
| 1120 | poe-chat-and-api | Poe 聊天与平台域名 | [订阅](https://raw.githubusercontent.com/LuckyLight6/loon-rules/main/dist/clash-classical/1120-poe-chat-and-api.yaml) |
| 1130 | mistral-model-services | Mistral 平台专用域名 | [订阅](https://raw.githubusercontent.com/LuckyLight6/loon-rules/main/dist/clash-classical/1130-mistral-model-services.yaml) |
| 1140 | groq-inference | Groq 推理服务入口 | [订阅](https://raw.githubusercontent.com/LuckyLight6/loon-rules/main/dist/clash-classical/1140-groq-inference.yaml) |
| 1150 | cohere-model-services | Cohere 的推理及平台域名 | [订阅](https://raw.githubusercontent.com/LuckyLight6/loon-rules/main/dist/clash-classical/1150-cohere-model-services.yaml) |
| 1160 | hugging-face-model-hub | Hugging Face 模型库与专用 CDN | [订阅](https://raw.githubusercontent.com/LuckyLight6/loon-rules/main/dist/clash-classical/1160-hugging-face-model-hub.yaml) |
| 1170 | devin-cloud-coding | Devin 自有云编程入口 | [订阅](https://raw.githubusercontent.com/LuckyLight6/loon-rules/main/dist/clash-classical/1170-devin-cloud-coding.yaml) |
| 1180 | elevenlabs-voice-and-api | ElevenLabs 语音生成、WebSocket、文件与 MCP | [订阅](https://raw.githubusercontent.com/LuckyLight6/loon-rules/main/dist/clash-classical/1180-elevenlabs-voice-and-api.yaml) |
| 1190 | midjourney-image-tools | Midjourney 图像服务入口 | [订阅](https://raw.githubusercontent.com/LuckyLight6/loon-rules/main/dist/clash-classical/1190-midjourney-image-tools.yaml) |
| 1200 | openrouter-gateway | OpenRouter 的模型网关入口 | [订阅](https://raw.githubusercontent.com/LuckyLight6/loon-rules/main/dist/clash-classical/1200-openrouter-gateway.yaml) |
| 1210 | windsurf-editor-and-api | Windsurf 和 Codeium 专用接口 | [订阅](https://raw.githubusercontent.com/LuckyLight6/loon-rules/main/dist/clash-classical/1210-windsurf-editor-and-api.yaml) |
| 1220 | ai-com-agents | ai.com 的个人 AI 代理 | [订阅](https://raw.githubusercontent.com/LuckyLight6/loon-rules/main/dist/clash-classical/1220-ai-com-agents.yaml) |
| 1230 | jetbrains-ai | JetBrains AI | [订阅](https://raw.githubusercontent.com/LuckyLight6/loon-rules/main/dist/clash-classical/1230-jetbrains-ai.yaml) |
| 1240 | amp-connections | Amp 登录、线程 WebSocket、CLI 与官方运行环境 | [订阅](https://raw.githubusercontent.com/LuckyLight6/loon-rules/main/dist/clash-classical/1240-amp-connections.yaml) |
| 1250 | anythingllm-connections | AnythingLLM 官网与自营下载、云端入口 | [订阅](https://raw.githubusercontent.com/LuckyLight6/loon-rules/main/dist/clash-classical/1250-anythingllm-connections.yaml) |
| 1260 | fireworks-model-services | Fireworks 模型 API、产品门户与自营资源 | [订阅](https://raw.githubusercontent.com/LuckyLight6/loon-rules/main/dist/clash-classical/1260-fireworks-model-services.yaml) |
| 1270 | opencode-connections | OpenCode 与 Go 网关 | [订阅](https://raw.githubusercontent.com/LuckyLight6/loon-rules/main/dist/clash-classical/1270-opencode-connections.yaml) |
| 1280 | kilo-connections | Kilo 编程助手与模型网关 | [订阅](https://raw.githubusercontent.com/LuckyLight6/loon-rules/main/dist/clash-classical/1280-kilo-connections.yaml) |
| 1290 | cline-connections | Cline 自营接入与账户 | [订阅](https://raw.githubusercontent.com/LuckyLight6/loon-rules/main/dist/clash-classical/1290-cline-connections.yaml) |
| 1300 | ollama-cloud | Ollama Cloud 远程接口 | [订阅](https://raw.githubusercontent.com/LuckyLight6/loon-rules/main/dist/clash-classical/1300-ollama-cloud.yaml) |
| 1310 | chutes-model-services | Chutes 模型服务 | [订阅](https://raw.githubusercontent.com/LuckyLight6/loon-rules/main/dist/clash-classical/1310-chutes-model-services.yaml) |
| 1320 | bothub-model-services | Bothub 模型网关 | [订阅](https://raw.githubusercontent.com/LuckyLight6/loon-rules/main/dist/clash-classical/1320-bothub-model-services.yaml) |
| 1330 | commandcode-connections | CommandCode 编程与模型接口 | [订阅](https://raw.githubusercontent.com/LuckyLight6/loon-rules/main/dist/clash-classical/1330-commandcode-connections.yaml) |
| 1340 | stackit-model-services | STACKIT AI Model Serving | [订阅](https://raw.githubusercontent.com/LuckyLight6/loon-rules/main/dist/clash-classical/1340-stackit-model-services.yaml) |
| 1350 | novita-model-services | Novita 模型服务 | [订阅](https://raw.githubusercontent.com/LuckyLight6/loon-rules/main/dist/clash-classical/1350-novita-model-services.yaml) |
| 1360 | nebius-model-services | Nebius Token Factory | [订阅](https://raw.githubusercontent.com/LuckyLight6/loon-rules/main/dist/clash-classical/1360-nebius-model-services.yaml) |
| 1370 | baseten-model-services | Baseten 模型服务 | [订阅](https://raw.githubusercontent.com/LuckyLight6/loon-rules/main/dist/clash-classical/1370-baseten-model-services.yaml) |
| 1380 | deepinfra-model-services | DeepInfra 模型服务 | [订阅](https://raw.githubusercontent.com/LuckyLight6/loon-rules/main/dist/clash-classical/1380-deepinfra-model-services.yaml) |
| 1390 | together-model-services | Together AI 模型服务 | [订阅](https://raw.githubusercontent.com/LuckyLight6/loon-rules/main/dist/clash-classical/1390-together-model-services.yaml) |
| 1400 | cerebras-model-services | Cerebras 推理服务 | [订阅](https://raw.githubusercontent.com/LuckyLight6/loon-rules/main/dist/clash-classical/1400-cerebras-model-services.yaml) |
| 1410 | replicate-model-services | Replicate 模型 API 与结果文件 | [订阅](https://raw.githubusercontent.com/LuckyLight6/loon-rules/main/dist/clash-classical/1410-replicate-model-services.yaml) |
| 1420 | runway-creative-tools | Runway 视频与创作服务 | [订阅](https://raw.githubusercontent.com/LuckyLight6/loon-rules/main/dist/clash-classical/1420-runway-creative-tools.yaml) |
| 1430 | stability-model-services | Stability AI 模型服务 | [订阅](https://raw.githubusercontent.com/LuckyLight6/loon-rules/main/dist/clash-classical/1430-stability-model-services.yaml) |
| 1440 | black-forest-model-services | Black Forest Labs 与 FLUX | [订阅](https://raw.githubusercontent.com/LuckyLight6/loon-rules/main/dist/clash-classical/1440-black-forest-model-services.yaml) |
| 1450 | replit-cloud-development | Replit 云端开发 | [订阅](https://raw.githubusercontent.com/LuckyLight6/loon-rules/main/dist/clash-classical/1450-replit-cloud-development.yaml) |
| 1460 | augment-code-assistant | Augment Code 编程助手 | [订阅](https://raw.githubusercontent.com/LuckyLight6/loon-rules/main/dist/clash-classical/1460-augment-code-assistant.yaml) |
| 1470 | sourcegraph-code-and-cody | Sourcegraph 与 Cody | [订阅](https://raw.githubusercontent.com/LuckyLight6/loon-rules/main/dist/clash-classical/1470-sourcegraph-code-and-cody.yaml) |
| 1480 | continue-code-assistant | Continue 编程助手 | [订阅](https://raw.githubusercontent.com/LuckyLight6/loon-rules/main/dist/clash-classical/1480-continue-code-assistant.yaml) |
| 1490 | coderabbit-code-review | CodeRabbit 代码审查 | [订阅](https://raw.githubusercontent.com/LuckyLight6/loon-rules/main/dist/clash-classical/1490-coderabbit-code-review.yaml) |
| 1500 | tabnine-code-assistant | Tabnine 编程助手 | [订阅](https://raw.githubusercontent.com/LuckyLight6/loon-rules/main/dist/clash-classical/1500-tabnine-code-assistant.yaml) |
| 1510 | factory-coding-agents | Factory 编程代理 | [订阅](https://raw.githubusercontent.com/LuckyLight6/loon-rules/main/dist/clash-classical/1510-factory-coding-agents.yaml) |
| 1520 | zed-editor-and-ai | Zed 编辑器与自营 AI | [订阅](https://raw.githubusercontent.com/LuckyLight6/loon-rules/main/dist/clash-classical/1520-zed-editor-and-ai.yaml) |
| 1530 | kiro-code-assistant | Kiro 编程助手 | [订阅](https://raw.githubusercontent.com/LuckyLight6/loon-rules/main/dist/clash-classical/1530-kiro-code-assistant.yaml) |
| 1540 | bolt-app-builder | Bolt 应用构建 | [订阅](https://raw.githubusercontent.com/LuckyLight6/loon-rules/main/dist/clash-classical/1540-bolt-app-builder.yaml) |
| 1550 | lovable-app-builder | Lovable 应用构建 | [订阅](https://raw.githubusercontent.com/LuckyLight6/loon-rules/main/dist/clash-classical/1550-lovable-app-builder.yaml) |
| 1560 | v0-app-builder | Vercel v0 应用构建 | [订阅](https://raw.githubusercontent.com/LuckyLight6/loon-rules/main/dist/clash-classical/1560-v0-app-builder.yaml) |
| 1570 | genspark-connections | Genspark 搜索与代理 | [订阅](https://raw.githubusercontent.com/LuckyLight6/loon-rules/main/dist/clash-classical/1570-genspark-connections.yaml) |
| 1580 | jasper-marketing-ai | Jasper 营销 AI | [订阅](https://raw.githubusercontent.com/LuckyLight6/loon-rules/main/dist/clash-classical/1580-jasper-marketing-ai.yaml) |
| 1590 | gamma-presentations | Gamma 演示与文档 | [订阅](https://raw.githubusercontent.com/LuckyLight6/loon-rules/main/dist/clash-classical/1590-gamma-presentations.yaml) |
| 1600 | phind-search | Phind 搜索与问答 | [订阅](https://raw.githubusercontent.com/LuckyLight6/loon-rules/main/dist/clash-classical/1600-phind-search.yaml) |
| 1610 | inflection-and-pi | Inflection 与 Pi | [订阅](https://raw.githubusercontent.com/LuckyLight6/loon-rules/main/dist/clash-classical/1610-inflection-and-pi.yaml) |
| 1620 | h2o-model-services | H2O AI 平台 | [订阅](https://raw.githubusercontent.com/LuckyLight6/loon-rules/main/dist/clash-classical/1620-h2o-model-services.yaml) |
| 1630 | otter-meeting-assistant | Otter 会议助手 | [订阅](https://raw.githubusercontent.com/LuckyLight6/loon-rules/main/dist/clash-classical/1630-otter-meeting-assistant.yaml) |
| 1640 | descript-media-tools | Descript 音视频编辑 | [订阅](https://raw.githubusercontent.com/LuckyLight6/loon-rules/main/dist/clash-classical/1640-descript-media-tools.yaml) |
| 1650 | synthesia-video-tools | Synthesia 视频生成 | [订阅](https://raw.githubusercontent.com/LuckyLight6/loon-rules/main/dist/clash-classical/1650-synthesia-video-tools.yaml) |
| 1660 | luma-creative-tools | Luma 创作服务 | [订阅](https://raw.githubusercontent.com/LuckyLight6/loon-rules/main/dist/clash-classical/1660-luma-creative-tools.yaml) |
| 1670 | leonardo-image-tools | Leonardo 图像生成 | [订阅](https://raw.githubusercontent.com/LuckyLight6/loon-rules/main/dist/clash-classical/1670-leonardo-image-tools.yaml) |
| 1680 | pika-video-tools | Pika 视频生成 | [订阅](https://raw.githubusercontent.com/LuckyLight6/loon-rules/main/dist/clash-classical/1680-pika-video-tools.yaml) |
| 1690 | recraft-design-tools | Recraft 设计与图像 | [订阅](https://raw.githubusercontent.com/LuckyLight6/loon-rules/main/dist/clash-classical/1690-recraft-design-tools.yaml) |
| 1700 | udio-music-tools | Udio 音乐生成 | [订阅](https://raw.githubusercontent.com/LuckyLight6/loon-rules/main/dist/clash-classical/1700-udio-music-tools.yaml) |
| 1710 | duck-ai-chat | Duck.ai 对话 | [订阅](https://raw.githubusercontent.com/LuckyLight6/loon-rules/main/dist/clash-classical/1710-duck-ai-chat.yaml) |
| 1720 | langchain-agent-platform | LangChain 与代理平台 | [订阅](https://raw.githubusercontent.com/LuckyLight6/loon-rules/main/dist/clash-classical/1720-langchain-agent-platform.yaml) |
| 1730 | comfy-cloud-and-registry | Comfy 云端与组件目录 | [订阅](https://raw.githubusercontent.com/LuckyLight6/loon-rules/main/dist/clash-classical/1730-comfy-cloud-and-registry.yaml) |
| 1740 | lmstudio-product-services | LM Studio 产品与下载 | [订阅](https://raw.githubusercontent.com/LuckyLight6/loon-rules/main/dist/clash-classical/1740-lmstudio-product-services.yaml) |
| 1750 | crewai-agent-platform | CrewAI 代理平台 | [订阅](https://raw.githubusercontent.com/LuckyLight6/loon-rules/main/dist/clash-classical/1750-crewai-agent-platform.yaml) |
| 1760 | eigent-agent-services | Eigent 代理与协作 | [订阅](https://raw.githubusercontent.com/LuckyLight6/loon-rules/main/dist/clash-classical/1760-eigent-agent-services.yaml) |
| 1770 | manus-agent-services | Manus 代理与文件 | [订阅](https://raw.githubusercontent.com/LuckyLight6/loon-rules/main/dist/clash-classical/1770-manus-agent-services.yaml) |
| 1780 | dia-browser-services | Dia 浏览器自营服务 | [订阅](https://raw.githubusercontent.com/LuckyLight6/loon-rules/main/dist/clash-classical/1780-dia-browser-services.yaml) |
| 1790 | openclaw-product-services | OpenClaw 产品与发布服务 | [订阅](https://raw.githubusercontent.com/LuckyLight6/loon-rules/main/dist/clash-classical/1790-openclaw-product-services.yaml) |
| 1800 | ai-cn-international-all | 国产 AI 国际版合集 | [订阅](https://raw.githubusercontent.com/LuckyLight6/loon-rules/main/dist/clash-classical/1800-ai-cn-international-all.yaml) |
| 1810 | qwen-international | 阿里千问与百炼 · 国际入口 | [订阅](https://raw.githubusercontent.com/LuckyLight6/loon-rules/main/dist/clash-classical/1810-qwen-international.yaml) |
| 1820 | kimi-international | 月之暗面 Kimi · 国际入口 | [订阅](https://raw.githubusercontent.com/LuckyLight6/loon-rules/main/dist/clash-classical/1820-kimi-international.yaml) |
| 1830 | zhipu-international | 智谱 · 国际入口 | [订阅](https://raw.githubusercontent.com/LuckyLight6/loon-rules/main/dist/clash-classical/1830-zhipu-international.yaml) |
| 1840 | minimax-international | MiniMax 与海螺 · 国际入口 | [订阅](https://raw.githubusercontent.com/LuckyLight6/loon-rules/main/dist/clash-classical/1840-minimax-international.yaml) |
| 1850 | bytedance-international | 字节豆包、扣子与模型平台 · 国际入口 | [订阅](https://raw.githubusercontent.com/LuckyLight6/loon-rules/main/dist/clash-classical/1850-bytedance-international.yaml) |
| 1860 | siliconflow-international | 硅基流动 · 国际入口 | [订阅](https://raw.githubusercontent.com/LuckyLight6/loon-rules/main/dist/clash-classical/1860-siliconflow-international.yaml) |
| 1870 | tencent-international | 腾讯混元、元宝与 TokenHub · 国际入口 | [订阅](https://raw.githubusercontent.com/LuckyLight6/loon-rules/main/dist/clash-classical/1870-tencent-international.yaml) |
| 1880 | stepfun-international | 阶跃星辰 StepFun · 国际入口 | [订阅](https://raw.githubusercontent.com/LuckyLight6/loon-rules/main/dist/clash-classical/1880-stepfun-international.yaml) |
| 1890 | xiaomi-international | 小米 MiMo · 新加坡与欧洲计划 | [订阅](https://raw.githubusercontent.com/LuckyLight6/loon-rules/main/dist/clash-classical/1890-xiaomi-international.yaml) |
| 1900 | youmind-international | YouMind · 国际产品入口 | [订阅](https://raw.githubusercontent.com/LuckyLight6/loon-rules/main/dist/clash-classical/1900-youmind-international.yaml) |
| 1910 | qoder-international | Qoder · 国际产品入口 | [订阅](https://raw.githubusercontent.com/LuckyLight6/loon-rules/main/dist/clash-classical/1910-qoder-international.yaml) |
| 1920 | lovart-international | Lovart · 国际产品入口 | [订阅](https://raw.githubusercontent.com/LuckyLight6/loon-rules/main/dist/clash-classical/1920-lovart-international.yaml) |
| 2000 | apple-all | Apple 生态完整合集 | [订阅](https://raw.githubusercontent.com/LuckyLight6/loon-rules/main/dist/clash-classical/2000-apple-all.yaml) |
| 2010 | apple-overseas-all | Apple 海外功能合集 | [订阅](https://raw.githubusercontent.com/LuckyLight6/loon-rules/main/dist/clash-classical/2010-apple-overseas-all.yaml) |
| 2020 | apple-intelligence-relays | Apple Intelligence 的 PCC 与系统 AI 扩展中继 | [订阅](https://raw.githubusercontent.com/LuckyLight6/loon-rules/main/dist/clash-classical/2020-apple-intelligence-relays.yaml) |
| 2030 | apple-private-relay-connections | iCloud Private Relay（隐私中继）与 Apple DNS 别名 | [订阅](https://raw.githubusercontent.com/LuckyLight6/loon-rules/main/dist/clash-classical/2030-apple-private-relay-connections.yaml) |
| 2040 | apple-video-and-fitness | Apple TV／Fitness+ 的门户、播放控制与共用主机 | [订阅](https://raw.githubusercontent.com/LuckyLight6/loon-rules/main/dist/clash-classical/2040-apple-video-and-fitness.yaml) |
| 2050 | apple-tv-video-delivery | Apple TV 已识别的 HLS 视频交付 | [订阅](https://raw.githubusercontent.com/LuckyLight6/loon-rules/main/dist/clash-classical/2050-apple-tv-video-delivery.yaml) |
| 2060 | apple-news-and-sports | Apple News／News+、内容入口与 Apple Sports | [订阅](https://raw.githubusercontent.com/LuckyLight6/loon-rules/main/dist/clash-classical/2060-apple-news-and-sports.yaml) |
| 2070 | apple-push-connection | APNs 系统推送的域名与公开客户端网段 | [订阅](https://raw.githubusercontent.com/LuckyLight6/loon-rules/main/dist/clash-classical/2070-apple-push-connection.yaml) |
| 2080 | apple-direct-all | Apple 普通服务合集 | [订阅](https://raw.githubusercontent.com/LuckyLight6/loon-rules/main/dist/clash-classical/2080-apple-direct-all.yaml) |
| 2090 | apple-account-authentication | 登录、GrandSlam、OAuth、账户恢复与 iCloud 账户控制 | [订阅](https://raw.githubusercontent.com/LuckyLight6/loon-rules/main/dist/clash-classical/2090-apple-account-authentication.yaml) |
| 2100 | apple-app-and-device-verification | 应用验证、App Attest、macOS 公证与设备身份验证 | [订阅](https://raw.githubusercontent.com/LuckyLight6/loon-rules/main/dist/clash-classical/2100-apple-app-and-device-verification.yaml) |
| 2110 | apple-wallet-payments | Wallet 与 Apple Pay 已知支付入口 | [订阅](https://raw.githubusercontent.com/LuckyLight6/loon-rules/main/dist/clash-classical/2110-apple-wallet-payments.yaml) |
| 2120 | apple-testflight | TestFlight 测试版安装和分发 | [订阅](https://raw.githubusercontent.com/LuckyLight6/loon-rules/main/dist/clash-classical/2120-apple-testflight.yaml) |
| 2130 | apple-store-transactions | App Store API、搜索与提示、购买与安装指令、Apple Books 商店 | [订阅](https://raw.githubusercontent.com/LuckyLight6/loon-rules/main/dist/clash-classical/2130-apple-store-transactions.yaml) |
| 2140 | apple-app-package-downloads | App Store 安装包下载 | [订阅](https://raw.githubusercontent.com/LuckyLight6/loon-rules/main/dist/clash-classical/2140-apple-app-package-downloads.yaml) |
| 2150 | apple-association-services | Apple 通用链接的域名验证 | [订阅](https://raw.githubusercontent.com/LuckyLight6/loon-rules/main/dist/clash-classical/2150-apple-association-services.yaml) |
| 2160 | apple-find-my | Find My 设备与朋友查找的已识别入口 | [订阅](https://raw.githubusercontent.com/LuckyLight6/loon-rules/main/dist/clash-classical/2160-apple-find-my.yaml) |
| 2170 | apple-location-services | 定位查询、地图配置与信号定位数据 | [订阅](https://raw.githubusercontent.com/LuckyLight6/loon-rules/main/dist/clash-classical/2170-apple-location-services.yaml) |
| 2180 | apple-messaging-identity | Apple IDS 共用身份、注册与查询服务 | [订阅](https://raw.githubusercontent.com/LuckyLight6/loon-rules/main/dist/clash-classical/2180-apple-messaging-identity.yaml) |
| 2190 | apple-icloud-mainland | 中国大陆 iCloud 服务和内容专用域 | [订阅](https://raw.githubusercontent.com/LuckyLight6/loon-rules/main/dist/clash-classical/2190-apple-icloud-mainland.yaml) |
| 2200 | apple-icloud-content-domains | iCloud 通用内容域 | [订阅](https://raw.githubusercontent.com/LuckyLight6/loon-rules/main/dist/clash-classical/2200-apple-icloud-content-domains.yaml) |
| 2210 | apple-cloud-sync | iCloud 通用服务、CloudKit、同步、邮件及 iWork | [订阅](https://raw.githubusercontent.com/LuckyLight6/loon-rules/main/dist/clash-classical/2210-apple-cloud-sync.yaml) |
| 2220 | apple-podcasts | Apple 播客 | [订阅](https://raw.githubusercontent.com/LuckyLight6/loon-rules/main/dist/clash-classical/2220-apple-podcasts.yaml) |
| 2230 | apple-music-and-radio | Apple Music、广播及共用 API 与应用门户 | [订阅](https://raw.githubusercontent.com/LuckyLight6/loon-rules/main/dist/clash-classical/2230-apple-music-and-radio.yaml) |
| 2240 | apple-music-audio-delivery | Apple Music 已识别音频交付主机 | [订阅](https://raw.githubusercontent.com/LuckyLight6/loon-rules/main/dist/clash-classical/2240-apple-music-audio-delivery.yaml) |
| 2250 | apple-siri-and-search | Siri 与 Spotlight 的专用域名 | [订阅](https://raw.githubusercontent.com/LuckyLight6/loon-rules/main/dist/clash-classical/2250-apple-siri-and-search.yaml) |
| 2260 | apple-update-control | 系统更新目录、检查、授权与登记 | [订阅](https://raw.githubusercontent.com/LuckyLight6/loon-rules/main/dist/clash-classical/2260-apple-update-control.yaml) |
| 2270 | apple-update-downloads | 系统更新包与恢复内容下载 | [订阅](https://raw.githubusercontent.com/LuckyLight6/loon-rules/main/dist/clash-classical/2270-apple-update-downloads.yaml) |
| 2280 | apple-developer-portal | Apple Developer 门户 | [订阅](https://raw.githubusercontent.com/LuckyLight6/loon-rules/main/dist/clash-classical/2280-apple-developer-portal.yaml) |
| 2290 | apple-developer-downloads | Xcode、Swift Playgrounds 和开发者组件的实际下载 | [订阅](https://raw.githubusercontent.com/LuckyLight6/loon-rules/main/dist/clash-classical/2290-apple-developer-downloads.yaml) |
| 2300 | apple-mainland-delivery-aliases | 已核对的 Apple 大陆就近分发别名 | [订阅](https://raw.githubusercontent.com/LuckyLight6/loon-rules/main/dist/clash-classical/2300-apple-mainland-delivery-aliases.yaml) |
| 2310 | apple-shared-store-assets | Apple 商店与媒体共用的静态内容 | [订阅](https://raw.githubusercontent.com/LuckyLight6/loon-rules/main/dist/clash-classical/2310-apple-shared-store-assets.yaml) |
| 2320 | apple-certificate-validation | Apple 设备的证书状态和撤销检查 | [订阅](https://raw.githubusercontent.com/LuckyLight6/loon-rules/main/dist/clash-classical/2320-apple-certificate-validation.yaml) |
| 2330 | apple-system-connectivity | 设备引导、MDM、校时、系统 DNS 与公共素材 | [订阅](https://raw.githubusercontent.com/LuckyLight6/loon-rules/main/dist/clash-classical/2330-apple-system-connectivity.yaml) |
| 2340 | apple-schoolwork-handouts | Apple Schoolwork 讲义与资料交付 | [订阅](https://raw.githubusercontent.com/LuckyLight6/loon-rules/main/dist/clash-classical/2340-apple-schoolwork-handouts.yaml) |
| 2350 | apple-device-registration | 设备激活与 APNs 证书登记门户 | [订阅](https://raw.githubusercontent.com/LuckyLight6/loon-rules/main/dist/clash-classical/2350-apple-device-registration.yaml) |
| 2360 | apple-feedback-and-diagnostics | Feedback Assistant、错误报告与自愿诊断上传 | [订阅](https://raw.githubusercontent.com/LuckyLight6/loon-rules/main/dist/clash-classical/2360-apple-feedback-and-diagnostics.yaml) |
| 2370 | apple-other-services | Apple 官网与尚未细分的通用服务 | [订阅](https://raw.githubusercontent.com/LuckyLight6/loon-rules/main/dist/clash-classical/2370-apple-other-services.yaml) |
| 3000 | overseas-development-all | 海外开发合集 | [订阅](https://raw.githubusercontent.com/LuckyLight6/loon-rules/main/dist/clash-classical/3000-overseas-development-all.yaml) |
| 3010 | github-code-and-packages | GitHub 代码托管、API、Actions 与容器镜像 | [订阅](https://raw.githubusercontent.com/LuckyLight6/loon-rules/main/dist/clash-classical/3010-github-code-and-packages.yaml) |
| 3020 | gitlab-hosting | GitLab.com | [订阅](https://raw.githubusercontent.com/LuckyLight6/loon-rules/main/dist/clash-classical/3020-gitlab-hosting.yaml) |
| 3030 | bitbucket-hosting | Atlassian Bitbucket | [订阅](https://raw.githubusercontent.com/LuckyLight6/loon-rules/main/dist/clash-classical/3030-bitbucket-hosting.yaml) |
| 3040 | npm-registry | npm 软件包 | [订阅](https://raw.githubusercontent.com/LuckyLight6/loon-rules/main/dist/clash-classical/3040-npm-registry.yaml) |
| 3050 | maven-central | Maven Central | [订阅](https://raw.githubusercontent.com/LuckyLight6/loon-rules/main/dist/clash-classical/3050-maven-central.yaml) |
| 3060 | pypi-packages | PyPI 软件包 | [订阅](https://raw.githubusercontent.com/LuckyLight6/loon-rules/main/dist/clash-classical/3060-pypi-packages.yaml) |
| 3070 | docker-hub | Docker Hub | [订阅](https://raw.githubusercontent.com/LuckyLight6/loon-rules/main/dist/clash-classical/3070-docker-hub.yaml) |
| 3075 | docker-desktop-and-platform | Docker Desktop、Scout、Offload、Hardened Images 与平台服务 | [订阅](https://raw.githubusercontent.com/LuckyLight6/loon-rules/main/dist/clash-classical/3075-docker-desktop-and-platform.yaml) |
| 3080 | rust-cargo | Rust、Cargo 与 crates.io | [订阅](https://raw.githubusercontent.com/LuckyLight6/loon-rules/main/dist/clash-classical/3080-rust-cargo.yaml) |
| 3090 | go-modules | Go 模块与工具链 | [订阅](https://raw.githubusercontent.com/LuckyLight6/loon-rules/main/dist/clash-classical/3090-go-modules.yaml) |
| 3100 | jetbrains-ides | JetBrains IDE、授权与插件 | [订阅](https://raw.githubusercontent.com/LuckyLight6/loon-rules/main/dist/clash-classical/3100-jetbrains-ides.yaml) |
| 3110 | nodejs-runtime | Node.js 运行时与官方发行站 | [订阅](https://raw.githubusercontent.com/LuckyLight6/loon-rules/main/dist/clash-classical/3110-nodejs-runtime.yaml) |
| 3120 | agent-client-protocol | ACP 协议、文档与代理注册表 | [订阅](https://raw.githubusercontent.com/LuckyLight6/loon-rules/main/dist/clash-classical/3120-agent-client-protocol.yaml) |
| 3130 | workos-authentication | WorkOS 登录、企业认证与公共组件 | [订阅](https://raw.githubusercontent.com/LuckyLight6/loon-rules/main/dist/clash-classical/3130-workos-authentication.yaml) |
| 3140 | datadog-observability | Datadog 监控、日志与浏览器 SDK | [订阅](https://raw.githubusercontent.com/LuckyLight6/loon-rules/main/dist/clash-classical/3140-datadog-observability.yaml) |
| 3150 | sentry-error-monitoring | Sentry 错误监控、API 与 SDK | [订阅](https://raw.githubusercontent.com/LuckyLight6/loon-rules/main/dist/clash-classical/3150-sentry-error-monitoring.yaml) |
| 3160 | statsig-feature-management | Statsig 功能开关、实验、配置与事件 API | [订阅](https://raw.githubusercontent.com/LuckyLight6/loon-rules/main/dist/clash-classical/3160-statsig-feature-management.yaml) |
| 3170 | fathom-web-analytics | Fathom 网站访问统计 | [订阅](https://raw.githubusercontent.com/LuckyLight6/loon-rules/main/dist/clash-classical/3170-fathom-web-analytics.yaml) |
| 3180 | hcaptcha-verification | hcaptcha 人机验证与服务状态 | [订阅](https://raw.githubusercontent.com/LuckyLight6/loon-rules/main/dist/clash-classical/3180-hcaptcha-verification.yaml) |
| 3190 | persona-identity-verification | Persona 身份、企业与年龄验证 | [订阅](https://raw.githubusercontent.com/LuckyLight6/loon-rules/main/dist/clash-classical/3190-persona-identity-verification.yaml) |
| 3200 | yoti-identity-verification | Yoti 数字身份与年龄验证 | [订阅](https://raw.githubusercontent.com/LuckyLight6/loon-rules/main/dist/clash-classical/3200-yoti-identity-verification.yaml) |
| 3210 | sift-fraud-prevention | Sift 反欺诈、设备与风险 API | [订阅](https://raw.githubusercontent.com/LuckyLight6/loon-rules/main/dist/clash-classical/3210-sift-fraud-prevention.yaml) |
| 3220 | auth0-identity-platform | Auth0 身份认证与共享登录平台 | [订阅](https://raw.githubusercontent.com/LuckyLight6/loon-rules/main/dist/clash-classical/3220-auth0-identity-platform.yaml) |
| 3230 | bugsnag-error-monitoring | Bugsnag 错误监控与会话报告 | [订阅](https://raw.githubusercontent.com/LuckyLight6/loon-rules/main/dist/clash-classical/3230-bugsnag-error-monitoring.yaml) |
| 3300 | overseas-social-all | 海外通讯与社交合集 | [订阅](https://raw.githubusercontent.com/LuckyLight6/loon-rules/main/dist/clash-classical/3300-overseas-social-all.yaml) |
| 3310 | telegram-messaging | Telegram 登录、消息、文件与服务器地址 | [订阅](https://raw.githubusercontent.com/LuckyLight6/loon-rules/main/dist/clash-classical/3310-telegram-messaging.yaml) |
| 3320 | discord-messaging-and-voice | Discord 通讯、语音及自营服务 | [订阅](https://raw.githubusercontent.com/LuckyLight6/loon-rules/main/dist/clash-classical/3320-discord-messaging-and-voice.yaml) |
| 3330 | signal-messenger | Signal 消息、通话、贴纸、群组与用户名链接 | [订阅](https://raw.githubusercontent.com/LuckyLight6/loon-rules/main/dist/clash-classical/3330-signal-messenger.yaml) |
| 3340 | line-messenger | LINE | [订阅](https://raw.githubusercontent.com/LuckyLight6/loon-rules/main/dist/clash-classical/3340-line-messenger.yaml) |
| 3350 | x-social-and-media | X / Twitter 社交与图像视频 | [订阅](https://raw.githubusercontent.com/LuckyLight6/loon-rules/main/dist/clash-classical/3350-x-social-and-media.yaml) |
| 3360 | wechat-international-portal | WeChat 国际网站、支付与部分 App 连接 | [订阅](https://raw.githubusercontent.com/LuckyLight6/loon-rules/main/dist/clash-classical/3360-wechat-international-portal.yaml) |
| 3370 | slack-workspaces | Slack 工作区、消息及相关网站 | [订阅](https://raw.githubusercontent.com/LuckyLight6/loon-rules/main/dist/clash-classical/3370-slack-workspaces.yaml) |
| 3380 | reddit-community | Reddit 社区、帮助与相关服务 | [订阅](https://raw.githubusercontent.com/LuckyLight6/loon-rules/main/dist/clash-classical/3380-reddit-community.yaml) |
| 3390 | instagram-social | Instagram | [订阅](https://raw.githubusercontent.com/LuckyLight6/loon-rules/main/dist/clash-classical/3390-instagram-social.yaml) |
| 3400 | whatsapp-messaging | WhatsApp 消息、媒体与短链接 | [订阅](https://raw.githubusercontent.com/LuckyLight6/loon-rules/main/dist/clash-classical/3400-whatsapp-messaging.yaml) |
| 3410 | threads-social | Threads | [订阅](https://raw.githubusercontent.com/LuckyLight6/loon-rules/main/dist/clash-classical/3410-threads-social.yaml) |
| 3420 | pinterest-social | Pinterest | [订阅](https://raw.githubusercontent.com/LuckyLight6/loon-rules/main/dist/clash-classical/3420-pinterest-social.yaml) |
| 3430 | bluesky-social | Bluesky 官方应用与网络服务 | [订阅](https://raw.githubusercontent.com/LuckyLight6/loon-rules/main/dist/clash-classical/3430-bluesky-social.yaml) |
| 3440 | lark-international | Lark 国际版协作服务 | [订阅](https://raw.githubusercontent.com/LuckyLight6/loon-rules/main/dist/clash-classical/3440-lark-international.yaml) |
| 3450 | zoom-meetings | Zoom 会议与共用服务 | [订阅](https://raw.githubusercontent.com/LuckyLight6/loon-rules/main/dist/clash-classical/3450-zoom-meetings.yaml) |
| 3460 | xiaomi-international-services | 小米国际社区与应用商店入口 | [订阅](https://raw.githubusercontent.com/LuckyLight6/loon-rules/main/dist/clash-classical/3460-xiaomi-international-services.yaml) |
| 3470 | linkedin-network | LinkedIn | [订阅](https://raw.githubusercontent.com/LuckyLight6/loon-rules/main/dist/clash-classical/3470-linkedin-network.yaml) |
| 3480 | meta-shared-services | Meta、Facebook 与 Messenger 共用服务 | [订阅](https://raw.githubusercontent.com/LuckyLight6/loon-rules/main/dist/clash-classical/3480-meta-shared-services.yaml) |
| 3500 | overseas-payments-all | 海外支付合集 | [订阅](https://raw.githubusercontent.com/LuckyLight6/loon-rules/main/dist/clash-classical/3500-overseas-payments-all.yaml) |
| 3510 | paypal-payments | PayPal 核心支付、验签和静态资源 | [订阅](https://raw.githubusercontent.com/LuckyLight6/loon-rules/main/dist/clash-classical/3510-paypal-payments.yaml) |
| 3520 | stripe-payments | Stripe | [订阅](https://raw.githubusercontent.com/LuckyLight6/loon-rules/main/dist/clash-classical/3520-stripe-payments.yaml) |
| 3530 | link-payments | Link 快捷支付 | [订阅](https://raw.githubusercontent.com/LuckyLight6/loon-rules/main/dist/clash-classical/3530-link-payments.yaml) |
| 3540 | braintree-payments | Braintree 商户支付、网关与 SDK | [订阅](https://raw.githubusercontent.com/LuckyLight6/loon-rules/main/dist/clash-classical/3540-braintree-payments.yaml) |
| 3550 | venmo-payments | Venmo 支付 | [订阅](https://raw.githubusercontent.com/LuckyLight6/loon-rules/main/dist/clash-classical/3550-venmo-payments.yaml) |
| 3560 | xoom-transfers | Xoom 汇款 | [订阅](https://raw.githubusercontent.com/LuckyLight6/loon-rules/main/dist/clash-classical/3560-xoom-transfers.yaml) |
| 3570 | wise-transfers | Wise 转账与账户服务 | [订阅](https://raw.githubusercontent.com/LuckyLight6/loon-rules/main/dist/clash-classical/3570-wise-transfers.yaml) |
| 3580 | tenpay-global-payments | TenPay Global 跨境支付与商户平台 | [订阅](https://raw.githubusercontent.com/LuckyLight6/loon-rules/main/dist/clash-classical/3580-tenpay-global-payments.yaml) |
| 3600 | overseas-crypto-all | 海外加密资产服务合集 | [订阅](https://raw.githubusercontent.com/LuckyLight6/loon-rules/main/dist/clash-classical/3600-overseas-crypto-all.yaml) |
| 3610 | binance-platform | Binance 币安 | [订阅](https://raw.githubusercontent.com/LuckyLight6/loon-rules/main/dist/clash-classical/3610-binance-platform.yaml) |
| 3620 | okx-platform | OKX 欧易 | [订阅](https://raw.githubusercontent.com/LuckyLight6/loon-rules/main/dist/clash-classical/3620-okx-platform.yaml) |
| 3630 | gemini-exchange | Gemini 交易平台与 API | [订阅](https://raw.githubusercontent.com/LuckyLight6/loon-rules/main/dist/clash-classical/3630-gemini-exchange.yaml) |
| 3640 | kraken-exchange | Kraken 交易平台 | [订阅](https://raw.githubusercontent.com/LuckyLight6/loon-rules/main/dist/clash-classical/3640-kraken-exchange.yaml) |
| 3650 | bybit-exchange | Bybit 交易平台 | [订阅](https://raw.githubusercontent.com/LuckyLight6/loon-rules/main/dist/clash-classical/3650-bybit-exchange.yaml) |
| 3660 | kucoin-exchange | KuCoin 交易平台 | [订阅](https://raw.githubusercontent.com/LuckyLight6/loon-rules/main/dist/clash-classical/3660-kucoin-exchange.yaml) |
| 3670 | trust-wallet | Trust Wallet | [订阅](https://raw.githubusercontent.com/LuckyLight6/loon-rules/main/dist/clash-classical/3670-trust-wallet.yaml) |
| 3800 | overseas-media-all | 海外影音与内容合集 | [订阅](https://raw.githubusercontent.com/LuckyLight6/loon-rules/main/dist/clash-classical/3800-overseas-media-all.yaml) |
| 3810 | hbo-streaming | HBO Max | [订阅](https://raw.githubusercontent.com/LuckyLight6/loon-rules/main/dist/clash-classical/3810-hbo-streaming.yaml) |
| 3820 | netflix-video-and-delivery | Netflix 播放、设备 API 和内容分发 | [订阅](https://raw.githubusercontent.com/LuckyLight6/loon-rules/main/dist/clash-classical/3820-netflix-video-and-delivery.yaml) |
| 3830 | disney-plus-streaming | Disney+ 播放及其专用交付 | [订阅](https://raw.githubusercontent.com/LuckyLight6/loon-rules/main/dist/clash-classical/3830-disney-plus-streaming.yaml) |
| 3840 | prime-video-streaming | Prime Video 视频 API 和内容 | [订阅](https://raw.githubusercontent.com/LuckyLight6/loon-rules/main/dist/clash-classical/3840-prime-video-streaming.yaml) |
| 3850 | hulu-streaming | Hulu 视频与交付 | [订阅](https://raw.githubusercontent.com/LuckyLight6/loon-rules/main/dist/clash-classical/3850-hulu-streaming.yaml) |
| 3860 | youtube-video-and-cdn | YouTube 视频、音乐、频道与专用 CDN | [订阅](https://raw.githubusercontent.com/LuckyLight6/loon-rules/main/dist/clash-classical/3860-youtube-video-and-cdn.yaml) |
| 3870 | tiktok-international-video | TikTok 国际短视频与直播 | [订阅](https://raw.githubusercontent.com/LuckyLight6/loon-rules/main/dist/clash-classical/3870-tiktok-international-video.yaml) |
| 3880 | bilibili-international-video | 哔哩哔哩国际版视频 | [订阅](https://raw.githubusercontent.com/LuckyLight6/loon-rules/main/dist/clash-classical/3880-bilibili-international-video.yaml) |
| 3890 | iqiyi-international | 爱奇艺国际版 iQIYI 与专用国际 API | [订阅](https://raw.githubusercontent.com/LuckyLight6/loon-rules/main/dist/clash-classical/3890-iqiyi-international.yaml) |
| 3900 | vimeo-video | Vimeo 视频与交付 | [订阅](https://raw.githubusercontent.com/LuckyLight6/loon-rules/main/dist/clash-classical/3900-vimeo-video.yaml) |
| 3910 | spotify-audio | Spotify 音乐、播客及相关网站 | [订阅](https://raw.githubusercontent.com/LuckyLight6/loon-rules/main/dist/clash-classical/3910-spotify-audio.yaml) |
| 3920 | soundcloud-audio | SoundCloud 音频与创作者服务 | [订阅](https://raw.githubusercontent.com/LuckyLight6/loon-rules/main/dist/clash-classical/3920-soundcloud-audio.yaml) |
| 3930 | twitch-live-video | Twitch 直播、聊天室和内容 CDN | [订阅](https://raw.githubusercontent.com/LuckyLight6/loon-rules/main/dist/clash-classical/3930-twitch-live-video.yaml) |
| 3940 | bbc-news-and-video | BBC 新闻与影音 | [订阅](https://raw.githubusercontent.com/LuckyLight6/loon-rules/main/dist/clash-classical/3940-bbc-news-and-video.yaml) |
| 3950 | bahamut-video-and-community | 巴哈姆特动画疯和电玩社区 | [订阅](https://raw.githubusercontent.com/LuckyLight6/loon-rules/main/dist/clash-classical/3950-bahamut-video-and-community.yaml) |
| 4100 | overseas-games-all | 海外游戏合集 | [订阅](https://raw.githubusercontent.com/LuckyLight6/loon-rules/main/dist/clash-classical/4100-overseas-games-all.yaml) |
| 4110 | steam-international-platform | Steam 国际商店、社区、联机和下载 | [订阅](https://raw.githubusercontent.com/LuckyLight6/loon-rules/main/dist/clash-classical/4110-steam-international-platform.yaml) |
| 4120 | epic-games-services | Epic Games 商店、登录及 Unreal 服务 | [订阅](https://raw.githubusercontent.com/LuckyLight6/loon-rules/main/dist/clash-classical/4120-epic-games-services.yaml) |
| 4130 | playstation-network | Sony PlayStation | [订阅](https://raw.githubusercontent.com/LuckyLight6/loon-rules/main/dist/clash-classical/4130-playstation-network.yaml) |
| 4140 | nintendo-platform | Nintendo 任天堂 | [订阅](https://raw.githubusercontent.com/LuckyLight6/loon-rules/main/dist/clash-classical/4140-nintendo-platform.yaml) |
| 4150 | hoyoverse-international | HoYoverse 国际版 | [订阅](https://raw.githubusercontent.com/LuckyLight6/loon-rules/main/dist/clash-classical/4150-hoyoverse-international.yaml) |
| 4160 | ea-games | EA 游戏平台 | [订阅](https://raw.githubusercontent.com/LuckyLight6/loon-rules/main/dist/clash-classical/4160-ea-games.yaml) |
| 4170 | ubisoft-connect | Ubisoft Connect | [订阅](https://raw.githubusercontent.com/LuckyLight6/loon-rules/main/dist/clash-classical/4170-ubisoft-connect.yaml) |
| 4180 | blizzard-battlenet | Blizzard / Battle.net 国际服务 | [订阅](https://raw.githubusercontent.com/LuckyLight6/loon-rules/main/dist/clash-classical/4180-blizzard-battlenet.yaml) |
| 4190 | netease-international-games | 网易国际游戏与共用 SDK | [订阅](https://raw.githubusercontent.com/LuckyLight6/loon-rules/main/dist/clash-classical/4190-netease-international-games.yaml) |
| 4300 | overseas-productivity-all | 海外办公、邮件与协作合集 | [订阅](https://raw.githubusercontent.com/LuckyLight6/loon-rules/main/dist/clash-classical/4300-overseas-productivity-all.yaml) |
| 4310 | notion-workspace | Notion | [订阅](https://raw.githubusercontent.com/LuckyLight6/loon-rules/main/dist/clash-classical/4310-notion-workspace.yaml) |
| 4320 | figma-design | Figma | [订阅](https://raw.githubusercontent.com/LuckyLight6/loon-rules/main/dist/clash-classical/4320-figma-design.yaml) |
| 4330 | trello-boards | Trello | [订阅](https://raw.githubusercontent.com/LuckyLight6/loon-rules/main/dist/clash-classical/4330-trello-boards.yaml) |
| 4340 | atlassian-cloud-services | Atlassian Cloud：共享平台、Jira 与 Confluence | [订阅](https://raw.githubusercontent.com/LuckyLight6/loon-rules/main/dist/clash-classical/4340-atlassian-cloud-services.yaml) |
| 4350 | proton-suite | Proton 邮件、账户及共用服务 | [订阅](https://raw.githubusercontent.com/LuckyLight6/loon-rules/main/dist/clash-classical/4350-proton-suite.yaml) |
| 4360 | intercom-customer-support | Intercom 客服、会话、附件与实时通信 | [订阅](https://raw.githubusercontent.com/LuckyLight6/loon-rules/main/dist/clash-classical/4360-intercom-customer-support.yaml) |
| 4500 | google-all | Google 日常服务合集 | [订阅](https://raw.githubusercontent.com/LuckyLight6/loon-rules/main/dist/clash-classical/4500-google-all.yaml) |
| 4510 | google-account-authentication | Google 共享账号、地区登录、OAuth 授权与换令牌 | [订阅](https://raw.githubusercontent.com/LuckyLight6/loon-rules/main/dist/clash-classical/4510-google-account-authentication.yaml) |
| 4520 | google-gmail-mail | Gmail 网页、邮件协议、专用 API 与投递诊断 | [订阅](https://raw.githubusercontent.com/LuckyLight6/loon-rules/main/dist/clash-classical/4520-google-gmail-mail.yaml) |
| 4530 | google-meet-meetings | Google Meet 会议、API 与 Workspace 共用音视频媒体 | [订阅](https://raw.githubusercontent.com/LuckyLight6/loon-rules/main/dist/clash-classical/4530-google-meet-meetings.yaml) |
| 4540 | google-drive-and-documents | Google Drive、文档和上传下载入口 | [订阅](https://raw.githubusercontent.com/LuckyLight6/loon-rules/main/dist/clash-classical/4540-google-drive-and-documents.yaml) |
| 4550 | google-play-services | Google Play 商店、应用管理与专用 API | [订阅](https://raw.githubusercontent.com/LuckyLight6/loon-rules/main/dist/clash-classical/4550-google-play-services.yaml) |
| 4560 | google-play-games | Google Play 游戏、发布与管理 API | [订阅](https://raw.githubusercontent.com/LuckyLight6/loon-rules/main/dist/clash-classical/4560-google-play-games.yaml) |
| 4570 | google-software-downloads | Google 软件和更新已知下载主机 | [订阅](https://raw.githubusercontent.com/LuckyLight6/loon-rules/main/dist/clash-classical/4570-google-software-downloads.yaml) |
| 4580 | google-scholar | Google 学术搜索 | [订阅](https://raw.githubusercontent.com/LuckyLight6/loon-rules/main/dist/clash-classical/4580-google-scholar.yaml) |
| 4585 | google-firebase-messaging | Google Firebase Cloud Messaging 推送与令牌注册 | [订阅](https://raw.githubusercontent.com/LuckyLight6/loon-rules/main/dist/clash-classical/4585-google-firebase-messaging.yaml) |
| 4590 | google-platform-services | Google 搜索、官方资讯、安全浏览 API 与共享平台兜底 | [订阅](https://raw.githubusercontent.com/LuckyLight6/loon-rules/main/dist/clash-classical/4590-google-platform-services.yaml) |
| 4700 | microsoft-all | Microsoft 日常服务合集 | [订阅](https://raw.githubusercontent.com/LuckyLight6/loon-rules/main/dist/clash-classical/4700-microsoft-all.yaml) |
| 4710 | microsoft-account-authentication | Microsoft 个人账户与 Entra 登录 | [订阅](https://raw.githubusercontent.com/LuckyLight6/loon-rules/main/dist/clash-classical/4710-microsoft-account-authentication.yaml) |
| 4720 | microsoft-outlook-mail | Outlook 与 Exchange Online 邮箱入口 | [订阅](https://raw.githubusercontent.com/LuckyLight6/loon-rules/main/dist/clash-classical/4720-microsoft-outlook-mail.yaml) |
| 4730 | microsoft-teams-meetings | Teams 会议及 Skype for Business 共用通信入口 | [订阅](https://raw.githubusercontent.com/LuckyLight6/loon-rules/main/dist/clash-classical/4730-microsoft-teams-meetings.yaml) |
| 4740 | microsoft-files-and-sharepoint | OneDrive 与 SharePoint 文件与同步 | [订阅](https://raw.githubusercontent.com/LuckyLight6/loon-rules/main/dist/clash-classical/4740-microsoft-files-and-sharepoint.yaml) |
| 4750 | microsoft-store-services | Microsoft Store 商店目录与加载 | [订阅](https://raw.githubusercontent.com/LuckyLight6/loon-rules/main/dist/clash-classical/4750-microsoft-store-services.yaml) |
| 4760 | microsoft-windows-update-services | Windows Update 检查与传递优化协调 | [订阅](https://raw.githubusercontent.com/LuckyLight6/loon-rules/main/dist/clash-classical/4760-microsoft-windows-update-services.yaml) |
| 4770 | microsoft-update-and-store-downloads | Windows 更新和 Microsoft Store 已知内容下载 | [订阅](https://raw.githubusercontent.com/LuckyLight6/loon-rules/main/dist/clash-classical/4770-microsoft-update-and-store-downloads.yaml) |
| 4780 | microsoft-office-downloads | Microsoft Office 安装与更新下载 | [订阅](https://raw.githubusercontent.com/LuckyLight6/loon-rules/main/dist/clash-classical/4780-microsoft-office-downloads.yaml) |
| 4790 | microsoft-vscode | Microsoft Visual Studio Code | [订阅](https://raw.githubusercontent.com/LuckyLight6/loon-rules/main/dist/clash-classical/4790-microsoft-vscode.yaml) |
| 4800 | microsoft-power-bi | Microsoft Power BI | [订阅](https://raw.githubusercontent.com/LuckyLight6/loon-rules/main/dist/clash-classical/4800-microsoft-power-bi.yaml) |
| 4810 | microsoft-xbox-services | Xbox Live 已知登录与服务端点 | [订阅](https://raw.githubusercontent.com/LuckyLight6/loon-rules/main/dist/clash-classical/4810-microsoft-xbox-services.yaml) |
| 4820 | microsoft-platform-services | Microsoft 通用客户端和共享服务兜底 | [订阅](https://raw.githubusercontent.com/LuckyLight6/loon-rules/main/dist/clash-classical/4820-microsoft-platform-services.yaml) |
| 4900 | multinational-mainland-all | 跨国厂商国内可用服务合集 | [订阅](https://raw.githubusercontent.com/LuckyLight6/loon-rules/main/dist/clash-classical/4900-multinational-mainland-all.yaml) |
| 4910 | qualcomm-mainland | 高通中国与国内可用系统服务 | [订阅](https://raw.githubusercontent.com/LuckyLight6/loon-rules/main/dist/clash-classical/4910-qualcomm-mainland.yaml) |
| 4920 | nvidia-mainland | NVIDIA 中国网站与国内下载入口 | [订阅](https://raw.githubusercontent.com/LuckyLight6/loon-rules/main/dist/clash-classical/4920-nvidia-mainland.yaml) |
| 4930 | intel-mainland | Intel 中国网站 | [订阅](https://raw.githubusercontent.com/LuckyLight6/loon-rules/main/dist/clash-classical/4930-intel-mainland.yaml) |
| 4940 | samsung-mainland | Samsung 中国网站、云与健康服务 | [订阅](https://raw.githubusercontent.com/LuckyLight6/loon-rules/main/dist/clash-classical/4940-samsung-mainland.yaml) |
| 4950 | cloudflare-mainland | Cloudflare 中国网络相关入口 | [订阅](https://raw.githubusercontent.com/LuckyLight6/loon-rules/main/dist/clash-classical/4950-cloudflare-mainland.yaml) |
| 4960 | adobe-mainland | Adobe 中国区文档云入口 | [订阅](https://raw.githubusercontent.com/LuckyLight6/loon-rules/main/dist/clash-classical/4960-adobe-mainland.yaml) |
| 4970 | amazon-mainland | Amazon 与 AWS 中国区入口 | [订阅](https://raw.githubusercontent.com/LuckyLight6/loon-rules/main/dist/clash-classical/4970-amazon-mainland.yaml) |
| 4980 | microsoft-china-cloud-controls | Microsoft Azure 中国区登录与控制端点 | [订阅](https://raw.githubusercontent.com/LuckyLight6/loon-rules/main/dist/clash-classical/4980-microsoft-china-cloud-controls.yaml) |
| 6000 | ai-cn-all | 国产 AI 国内版与共用入口合集 | [订阅](https://raw.githubusercontent.com/LuckyLight6/loon-rules/main/dist/clash-classical/6000-ai-cn-all.yaml) |
| 6010 | qwen-mainland | 阿里千问与百炼 · 国内入口 | [订阅](https://raw.githubusercontent.com/LuckyLight6/loon-rules/main/dist/clash-classical/6010-qwen-mainland.yaml) |
| 6020 | kimi-mainland | 月之暗面 Kimi · 国内入口 | [订阅](https://raw.githubusercontent.com/LuckyLight6/loon-rules/main/dist/clash-classical/6020-kimi-mainland.yaml) |
| 6030 | zhipu-mainland | 智谱 · 国内入口 | [订阅](https://raw.githubusercontent.com/LuckyLight6/loon-rules/main/dist/clash-classical/6030-zhipu-mainland.yaml) |
| 6040 | minimax-mainland | MiniMax 与海螺 · 国内入口 | [订阅](https://raw.githubusercontent.com/LuckyLight6/loon-rules/main/dist/clash-classical/6040-minimax-mainland.yaml) |
| 6050 | bytedance-mainland | 字节豆包、扣子与模型平台 · 国内入口 | [订阅](https://raw.githubusercontent.com/LuckyLight6/loon-rules/main/dist/clash-classical/6050-bytedance-mainland.yaml) |
| 6060 | siliconflow-mainland | 硅基流动 · 国内入口 | [订阅](https://raw.githubusercontent.com/LuckyLight6/loon-rules/main/dist/clash-classical/6060-siliconflow-mainland.yaml) |
| 6070 | tencent-mainland | 腾讯混元、元宝与 TokenHub · 国内入口 | [订阅](https://raw.githubusercontent.com/LuckyLight6/loon-rules/main/dist/clash-classical/6070-tencent-mainland.yaml) |
| 6080 | deepseek-mainland | DeepSeek · 国内入口 | [订阅](https://raw.githubusercontent.com/LuckyLight6/loon-rules/main/dist/clash-classical/6080-deepseek-mainland.yaml) |
| 6090 | baidu-mainland | 百度文心与千帆 | [订阅](https://raw.githubusercontent.com/LuckyLight6/loon-rules/main/dist/clash-classical/6090-baidu-mainland.yaml) |
| 6100 | iflytek-mainland | 讯飞星火 · 国内入口 | [订阅](https://raw.githubusercontent.com/LuckyLight6/loon-rules/main/dist/clash-classical/6100-iflytek-mainland.yaml) |
| 6110 | liblib-mainland | 哩布哩布 · 国内入口 | [订阅](https://raw.githubusercontent.com/LuckyLight6/loon-rules/main/dist/clash-classical/6110-liblib-mainland.yaml) |
| 6120 | baichuan-mainland | 百川智能 · 国内入口 | [订阅](https://raw.githubusercontent.com/LuckyLight6/loon-rules/main/dist/clash-classical/6120-baichuan-mainland.yaml) |
| 6130 | lingyi-mainland | 零一万物 · 国内入口 | [订阅](https://raw.githubusercontent.com/LuckyLight6/loon-rules/main/dist/clash-classical/6130-lingyi-mainland.yaml) |
| 6140 | stepfun-mainland | 阶跃星辰 · 国内入口 | [订阅](https://raw.githubusercontent.com/LuckyLight6/loon-rules/main/dist/clash-classical/6140-stepfun-mainland.yaml) |
| 6150 | sensetime-mainland | 商汤日日新 · 国内入口 | [订阅](https://raw.githubusercontent.com/LuckyLight6/loon-rules/main/dist/clash-classical/6150-sensetime-mainland.yaml) |
| 6160 | modelscope-mainland | 魔搭 ModelScope · 模型 API | [订阅](https://raw.githubusercontent.com/LuckyLight6/loon-rules/main/dist/clash-classical/6160-modelscope-mainland.yaml) |
| 6170 | xiaomi-mainland-and-shared | 小米 MiMo · 国内计划与共用 API | [订阅](https://raw.githubusercontent.com/LuckyLight6/loon-rules/main/dist/clash-classical/6170-xiaomi-mainland-and-shared.yaml) |
| 6250 | ai-overseas-mainland-all | 海外 AI 中国区服务合集 | [订阅](https://raw.githubusercontent.com/LuckyLight6/loon-rules/main/dist/clash-classical/6250-ai-overseas-mainland-all.yaml) |
| 6260 | jetbrains-ai-mainland | JetBrains AI · 中国区 API | [订阅](https://raw.githubusercontent.com/LuckyLight6/loon-rules/main/dist/clash-classical/6260-jetbrains-ai-mainland.yaml) |
| 6300 | mainland-development-all | 国内开发合集 | [订阅](https://raw.githubusercontent.com/LuckyLight6/loon-rules/main/dist/clash-classical/6300-mainland-development-all.yaml) |
| 6310 | gitee-hosting | Gitee 码云 | [订阅](https://raw.githubusercontent.com/LuckyLight6/loon-rules/main/dist/clash-classical/6310-gitee-hosting.yaml) |
| 6320 | coding-platform | 腾讯 CODING | [订阅](https://raw.githubusercontent.com/LuckyLight6/loon-rules/main/dist/clash-classical/6320-coding-platform.yaml) |
| 6330 | gitcode-hosting | GitCode | [订阅](https://raw.githubusercontent.com/LuckyLight6/loon-rules/main/dist/clash-classical/6330-gitcode-hosting.yaml) |
| 6340 | npmmirror-registry | npmmirror 国内镜像 | [订阅](https://raw.githubusercontent.com/LuckyLight6/loon-rules/main/dist/clash-classical/6340-npmmirror-registry.yaml) |
| 6350 | tuna-mirrors | 清华 TUNA 开源镜像 | [订阅](https://raw.githubusercontent.com/LuckyLight6/loon-rules/main/dist/clash-classical/6350-tuna-mirrors.yaml) |
| 6500 | mainland-social-all | 国内通讯与社交合集 | [订阅](https://raw.githubusercontent.com/LuckyLight6/loon-rules/main/dist/clash-classical/6500-mainland-social-all.yaml) |
| 6510 | wechat-shared-and-mainland | 微信国内与两版共用登录、消息和 App 服务 | [订阅](https://raw.githubusercontent.com/LuckyLight6/loon-rules/main/dist/clash-classical/6510-wechat-shared-and-mainland.yaml) |
| 6520 | dingtalk-public | 钉钉公共服务 | [订阅](https://raw.githubusercontent.com/LuckyLight6/loon-rules/main/dist/clash-classical/6520-dingtalk-public.yaml) |
| 6530 | feishu-mainland | 飞书国内协作服务 | [订阅](https://raw.githubusercontent.com/LuckyLight6/loon-rules/main/dist/clash-classical/6530-feishu-mainland.yaml) |
| 6540 | weibo-social | 微博 | [订阅](https://raw.githubusercontent.com/LuckyLight6/loon-rules/main/dist/clash-classical/6540-weibo-social.yaml) |
| 6550 | douban-community | 豆瓣 | [订阅](https://raw.githubusercontent.com/LuckyLight6/loon-rules/main/dist/clash-classical/6550-douban-community.yaml) |
| 6560 | xiaohongshu-community | 小红书国内内容、社区及专用 CDN | [订阅](https://raw.githubusercontent.com/LuckyLight6/loon-rules/main/dist/clash-classical/6560-xiaohongshu-community.yaml) |
| 6570 | zhihu-community | 知乎 | [订阅](https://raw.githubusercontent.com/LuckyLight6/loon-rules/main/dist/clash-classical/6570-zhihu-community.yaml) |
| 6700 | mainland-payments-all | 国内支付合集 | [订阅](https://raw.githubusercontent.com/LuckyLight6/loon-rules/main/dist/clash-classical/6700-mainland-payments-all.yaml) |
| 6710 | alipay-mainland-payments | 支付宝国内账户支付和静态资源 | [订阅](https://raw.githubusercontent.com/LuckyLight6/loon-rules/main/dist/clash-classical/6710-alipay-mainland-payments.yaml) |
| 6720 | unionpay-mainland | 银联、云闪付国内服务 | [订阅](https://raw.githubusercontent.com/LuckyLight6/loon-rules/main/dist/clash-classical/6720-unionpay-mainland.yaml) |
| 6730 | tenpay-mainland-payments | 财付通与 QQ 钱包共用支付 | [订阅](https://raw.githubusercontent.com/LuckyLight6/loon-rules/main/dist/clash-classical/6730-tenpay-mainland-payments.yaml) |
| 6900 | mainland-media-all | 国内影音与直播合集 | [订阅](https://raw.githubusercontent.com/LuckyLight6/loon-rules/main/dist/clash-classical/6900-mainland-media-all.yaml) |
| 6910 | bilibili-mainland-video | 哔哩哔哩中国站视频与图片 | [订阅](https://raw.githubusercontent.com/LuckyLight6/loon-rules/main/dist/clash-classical/6910-bilibili-mainland-video.yaml) |
| 6920 | iqiyi-mainland | 爱奇艺国内版 | [订阅](https://raw.githubusercontent.com/LuckyLight6/loon-rules/main/dist/clash-classical/6920-iqiyi-mainland.yaml) |
| 6930 | youku-video | 优酷国内站 | [订阅](https://raw.githubusercontent.com/LuckyLight6/loon-rules/main/dist/clash-classical/6930-youku-video.yaml) |
| 6940 | qq-music | QQ 音乐 | [订阅](https://raw.githubusercontent.com/LuckyLight6/loon-rules/main/dist/clash-classical/6940-qq-music.yaml) |
| 6950 | kugou-music | 酷狗音乐 | [订阅](https://raw.githubusercontent.com/LuckyLight6/loon-rules/main/dist/clash-classical/6950-kugou-music.yaml) |
| 6960 | netease-music | 网易云音乐 | [订阅](https://raw.githubusercontent.com/LuckyLight6/loon-rules/main/dist/clash-classical/6960-netease-music.yaml) |
| 6970 | douyin-mainland-video | 抖音中国版短视频、直播、图片与素材 | [订阅](https://raw.githubusercontent.com/LuckyLight6/loon-rules/main/dist/clash-classical/6970-douyin-mainland-video.yaml) |
| 6980 | kuaishou-video | 快手 | [订阅](https://raw.githubusercontent.com/LuckyLight6/loon-rules/main/dist/clash-classical/6980-kuaishou-video.yaml) |
| 6990 | douyu-live | 斗鱼直播 | [订阅](https://raw.githubusercontent.com/LuckyLight6/loon-rules/main/dist/clash-classical/6990-douyu-live.yaml) |
| 7000 | huya-live | 虎牙直播 | [订阅](https://raw.githubusercontent.com/LuckyLight6/loon-rules/main/dist/clash-classical/7000-huya-live.yaml) |
| 7200 | mainland-games-all | 国内游戏合集 | [订阅](https://raw.githubusercontent.com/LuckyLight6/loon-rules/main/dist/clash-classical/7200-mainland-games-all.yaml) |
| 7210 | steam-mainland-downloads | Steam 中国下载镜像与蒸汽平台内容 | [订阅](https://raw.githubusercontent.com/LuckyLight6/loon-rules/main/dist/clash-classical/7210-steam-mainland-downloads.yaml) |
| 7220 | mihoyo-mainland | 米哈游国服与米游社 | [订阅](https://raw.githubusercontent.com/LuckyLight6/loon-rules/main/dist/clash-classical/7220-mihoyo-mainland.yaml) |
| 7230 | wegame-mainland | 腾讯 WeGame 国内平台 | [订阅](https://raw.githubusercontent.com/LuckyLight6/loon-rules/main/dist/clash-classical/7230-wegame-mainland.yaml) |
| 7400 | mainland-daily-services-all | 国内购物、生活与办公合集 | [订阅](https://raw.githubusercontent.com/LuckyLight6/loon-rules/main/dist/clash-classical/7400-mainland-daily-services-all.yaml) |
| 7410 | taobao-and-xianyu-shopping | 淘宝、天猫、闲鱼购物与图片 | [订阅](https://raw.githubusercontent.com/LuckyLight6/loon-rules/main/dist/clash-classical/7410-taobao-and-xianyu-shopping.yaml) |
| 7420 | jingdong-shopping | 京东购物、账户与商品素材 | [订阅](https://raw.githubusercontent.com/LuckyLight6/loon-rules/main/dist/clash-classical/7420-jingdong-shopping.yaml) |
| 7430 | railway-tickets | 铁路 12306 | [订阅](https://raw.githubusercontent.com/LuckyLight6/loon-rules/main/dist/clash-classical/7430-railway-tickets.yaml) |
| 7440 | meituan-services | 美团与大众点评服务 | [订阅](https://raw.githubusercontent.com/LuckyLight6/loon-rules/main/dist/clash-classical/7440-meituan-services.yaml) |
| 7450 | didi-mobility | 滴滴出行 | [订阅](https://raw.githubusercontent.com/LuckyLight6/loon-rules/main/dist/clash-classical/7450-didi-mobility.yaml) |
| 7460 | youdao-products | 有道词典、学习与内容服务 | [订阅](https://raw.githubusercontent.com/LuckyLight6/loon-rules/main/dist/clash-classical/7460-youdao-products.yaml) |
| 7470 | aliyun-drive | 阿里云盘 | [订阅](https://raw.githubusercontent.com/LuckyLight6/loon-rules/main/dist/clash-classical/7470-aliyun-drive.yaml) |
| 7480 | wps-office | WPS Office 与文档服务 | [订阅](https://raw.githubusercontent.com/LuckyLight6/loon-rules/main/dist/clash-classical/7480-wps-office.yaml) |
| 8000 | global-platforms-all | 全球厂商与云平台共用服务合集 | [订阅](https://raw.githubusercontent.com/LuckyLight6/loon-rules/main/dist/clash-classical/8000-global-platforms-all.yaml) |
| 8010 | digitalocean-services | DigitalOcean 云平台与共用服务 | [订阅](https://raw.githubusercontent.com/LuckyLight6/loon-rules/main/dist/clash-classical/8010-digitalocean-services.yaml) |
| 8020 | vultr-services | Vultr 云平台 | [订阅](https://raw.githubusercontent.com/LuckyLight6/loon-rules/main/dist/clash-classical/8020-vultr-services.yaml) |
| 8030 | hetzner-services | Hetzner 云与存储平台 | [订阅](https://raw.githubusercontent.com/LuckyLight6/loon-rules/main/dist/clash-classical/8030-hetzner-services.yaml) |
| 8040 | vercel-shared-services | Vercel、Next.js 与共用托管平台 | [订阅](https://raw.githubusercontent.com/LuckyLight6/loon-rules/main/dist/clash-classical/8040-vercel-shared-services.yaml) |
| 8050 | netlify-services | Netlify 云平台与资源交付 | [订阅](https://raw.githubusercontent.com/LuckyLight6/loon-rules/main/dist/clash-classical/8050-netlify-services.yaml) |
| 8060 | heroku-services | Heroku 云平台与共用托管 | [订阅](https://raw.githubusercontent.com/LuckyLight6/loon-rules/main/dist/clash-classical/8060-heroku-services.yaml) |
| 8070 | oracle-shared-services | Oracle、Java 与云平台共用服务 | [订阅](https://raw.githubusercontent.com/LuckyLight6/loon-rules/main/dist/clash-classical/8070-oracle-shared-services.yaml) |
| 8080 | adobe-shared-services | Adobe Creative Cloud、Acrobat 与共用平台 | [订阅](https://raw.githubusercontent.com/LuckyLight6/loon-rules/main/dist/clash-classical/8080-adobe-shared-services.yaml) |
| 8090 | cloudflare-shared-services | Cloudflare 控制台、WARP、Tunnel 与共用平台 | [订阅](https://raw.githubusercontent.com/LuckyLight6/loon-rules/main/dist/clash-classical/8090-cloudflare-shared-services.yaml) |
| 8100 | amazon-shared-services | Amazon、AWS 与共用云平台 | [订阅](https://raw.githubusercontent.com/LuckyLight6/loon-rules/main/dist/clash-classical/8100-amazon-shared-services.yaml) |
| 8110 | discord-activities-proxy | Discord Activities 与第三方应用代理 | [订阅](https://raw.githubusercontent.com/LuckyLight6/loon-rules/main/dist/clash-classical/8110-discord-activities-proxy.yaml) |
| 8200 | overseas-extra-all | 海外补充合集 | [订阅](https://raw.githubusercontent.com/LuckyLight6/loon-rules/main/dist/clash-classical/8200-overseas-extra-all.yaml) |
| 8210 | overseas-media-extra | 其他海外影音 | [订阅](https://raw.githubusercontent.com/LuckyLight6/loon-rules/main/dist/clash-classical/8210-overseas-media-extra.yaml) |
| 8220 | overseas-sites-extra | 其他海外网站与受限站点 | [订阅](https://raw.githubusercontent.com/LuckyLight6/loon-rules/main/dist/clash-classical/8220-overseas-sites-extra.yaml) |
| 8400 | mainland-platforms-all | 国内厂商共用服务合集 | [订阅](https://raw.githubusercontent.com/LuckyLight6/loon-rules/main/dist/clash-classical/8400-mainland-platforms-all.yaml) |
| 8410 | netease-shared-services | 网易邮件、游戏、新闻与其他共用服务 | [订阅](https://raw.githubusercontent.com/LuckyLight6/loon-rules/main/dist/clash-classical/8410-netease-shared-services.yaml) |
| 8420 | alibaba-shared-services | 阿里巴巴与阿里云共用服务 | [订阅](https://raw.githubusercontent.com/LuckyLight6/loon-rules/main/dist/clash-classical/8420-alibaba-shared-services.yaml) |
| 8425 | tencent-shared-content-and-sdk | 腾讯共用图片、头像、下载与 SDK | [订阅](https://raw.githubusercontent.com/LuckyLight6/loon-rules/main/dist/clash-classical/8425-tencent-shared-content-and-sdk.yaml) |
| 8430 | tencent-shared-services | 腾讯 QQ、邮箱、网站与共用服务 | [订阅](https://raw.githubusercontent.com/LuckyLight6/loon-rules/main/dist/clash-classical/8430-tencent-shared-services.yaml) |
| 8440 | bytedance-shared-services | 字节跳动国内与共用服务 | [订阅](https://raw.githubusercontent.com/LuckyLight6/loon-rules/main/dist/clash-classical/8440-bytedance-shared-services.yaml) |
| 8450 | baidu-shared-services | 百度搜索、网盘与共用服务 | [订阅](https://raw.githubusercontent.com/LuckyLight6/loon-rules/main/dist/clash-classical/8450-baidu-shared-services.yaml) |
| 8460 | huawei-shared-services | 华为账户、设备与共用服务 | [订阅](https://raw.githubusercontent.com/LuckyLight6/loon-rules/main/dist/clash-classical/8460-huawei-shared-services.yaml) |
| 8470 | xiaomi-shared-services | 小米账户、设备与共用服务 | [订阅](https://raw.githubusercontent.com/LuckyLight6/loon-rules/main/dist/clash-classical/8470-xiaomi-shared-services.yaml) |
| 8480 | kingsoft-shared-services | 金山与其他共用服务 | [订阅](https://raw.githubusercontent.com/LuckyLight6/loon-rules/main/dist/clash-classical/8480-kingsoft-shared-services.yaml) |
| 8490 | sina-shared-image-assets | 新浪与微博共用图片 | [订阅](https://raw.githubusercontent.com/LuckyLight6/loon-rules/main/dist/clash-classical/8490-sina-shared-image-assets.yaml) |
| 8495 | sina-web-and-shared-services | 新浪网站、新闻、邮箱与网页服务 | [订阅](https://raw.githubusercontent.com/LuckyLight6/loon-rules/main/dist/clash-classical/8495-sina-web-and-shared-services.yaml) |
| 8600 | mainland-routing-all | 国内补充合集 | [订阅](https://raw.githubusercontent.com/LuckyLight6/loon-rules/main/dist/clash-classical/8600-mainland-routing-all.yaml) |
| 8610 | mainland-domains | 未由专项认领的国内域名补充 | [订阅](https://raw.githubusercontent.com/LuckyLight6/loon-rules/main/dist/clash-classical/8610-mainland-domains.yaml) |
| 8620 | mainland-networks | 可按 IPv4 / IPv6 网段判断的国内地址 | [订阅](https://raw.githubusercontent.com/LuckyLight6/loon-rules/main/dist/clash-classical/8620-mainland-networks.yaml) |
| 8630 | mainland-geoip | 设备 GeoIP 数据库中的中国大陆地址兜底 | [订阅](https://raw.githubusercontent.com/LuckyLight6/loon-rules/main/dist/clash-classical/8630-mainland-geoip.yaml) |

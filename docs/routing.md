# 各服务怎么选出口

以下按中国大陆网络、`FINAL` 走代理说明。需要分开的是**业务出口**，不必为每份规则新建策略组：多个产品可以共用一个稳定代理，下载和内网再单独选路。订阅地址与执行位置见[规则清单](rules.md)。

## Apple：认证、业务和内容分别判断

账户与购买可选择信任的美国节点并保持稳定，便于排查认证和交易问题。美区账户本身不要求美国 IP，代理也不能保证防止账户锁定。静态内容仍可能带签名或需要播放许可，不能按“有没有认证”简单决定出口。

| 序号 | 用途 | 出口建议与原因 |
|---:|---|---|
| 123 | Apple Intelligence、PCC 与系统 AI 扩展 | 使用功能支持地区的稳定代理；系统 ChatGPT 扩展与独立 ChatGPT App 的 102 分开。本机完成的推理不产生 PCC 连接 |
| 199 | Find My 设备与朋友查找 | 需要身份相关请求优先海外出口时，交给与账户一致的稳定代理；普通定位和地图由 209 处理，iCloud 文件仍可另走直连 |
| 201 | Apple 账户认证 | 手选稳定节点，与商店交易保持一致，减少登录或令牌刷新时中途换线 |
| 202 | 应用与设备验证 | 优先保留已能完成验证的路径。App Attest、设备身份、公证不能当作普通图片 CDN |
| 203 | Wallet / Apple Pay | 保留已能支付的出口，通常先试直连。支付还依赖设备、账户、发卡方、商户与地区资格 |
| 204 | TestFlight | 与商店交易用同一稳定出口；可识别的安装包另交 206 |
| 205 | App Store、Books 商店与交易 | 同 201。包括目录、购买、安装指令与签名初始化，不等同于包体下载 |
| 206 | App 安装包 | 直连能下载时优先直连，节省配额；商店正常但下载失败时先只比较这一组 |
| 207 | 通用链接与 App 关联 | 优先直连，保证网站与 App 关联检查可用 |
| 208 | APNs 推送 | 使用能稳定收通知的路径；直连漏通知时独立测试代理，不跟随所有 Apple 流量一起切换 |
| 209 | 定位查询与地图配置 | 直连可用时保持；不再把 Find My 专用身份入口混在定位例外里 |
| 210 | IDS 消息身份 | 身份相关连接优先海外时，可与账户用同一稳定代理；它不能代表全部 iMessage 或 FaceTime 媒体流量 |
| 211 | iCloud Private Relay | 已启用且地区支持时选可用代理；这里只识别中继入口，不设置系统功能 |
| 212 | 大陆 iCloud 专域 | 直连，仅覆盖已确认的大陆服务域，不代表所有 iCloud |
| 213 | iCloud 内容域 | 上传、下载均正常时优先直连，大文件可省配额；内容域仍可能有访问条件 |
| 214 | iCloud 同步与共用服务 | 与 213 选择已测通的路径。CloudKit、照片、备份、邮件可能共用主机，**这组也可能承载上传下载**，不能认为只有控制请求 |
| 215 | Podcasts | 根据实际目录与音频连通性选择；节目也可能由第三方站点托管，不能全部由 Apple 规则控制 |
| 216 | Music、广播与业务 API | 先与 217 一起试直连；目录、账户、地区限制或连续播放有问题，再比较代理 |
| 217 | Music 音频分发 | 已识别的音频主机，直连播放正常时保持；不是所有音乐流量都能单独认出 |
| 218 | TV、Fitness+ 门户与播放请求 | 默认使用可用地区的代理，先确认账户和订阅有权使用 |
| 219 | TV 视频分发 | 默认同 218，避免首页能开、内容不能播。想省配额可先降画质，不自动把视频切回直连 |
| 220 | News、Sports | 默认使用可用地区的代理，以正文能加载为准 |
| 221 | Siri、听写与搜索 | 保留已可用路径；普通 Siri 与新功能可能共享主机，不能只靠服务名判断云端用途 |
| 222 | 系统更新检查、授权与登记 | 身份与控制请求优先海外时用稳定代理；包体仍由 223 直连，Feedback Assistant 另在 232 |
| 223 | 系统更新与恢复包 | 优先直连，不为大包自动回退到代理；更新检查和安装授权分别匹配 |
| 224 | 开发者门户 | 需要访问海外文档与开发服务时用稳定代理；跳转认证仍由 201 处理 |
| 225 | 开发者文件下载 | 直连可下载时优先直连，和门户、账户分开 |
| 226 | 已确认的大陆分发别名 | 命中时可直连。只有已核实的服务别名，不根据 CDN 厂商或域名拼写推断地理位置 |
| 227 | 商店与媒体共用素材 | 优先直连，封面、截图等可省流量；前面的验证与业务专用主机先匹配 |
| 228 | 证书状态检查 | 优先直连。部分主机也服务其他厂商，因此独立于 Apple 合集 |
| 229 | 系统基础联网 | 保留 eSIM、机构 MDM、校时、系统 DNS 和公共素材的可用路径，通常直连；不据此认定这些请求匿名 |
| 230 | Schoolwork 作业资料 | 优先直连，或按学校网络要求；不接管全部账户、名册和设备管理 |
| 231 | 设备激活与 APNs 证书登记 | 官方用途明确的身份登记入口可交给账户代理；不把 eSIM 激活和 UDP 校时一起切走 |
| 232 | 反馈与诊断上传 | 按需使用稳定代理，反馈文件也会产生流量；规则只决定已有连接的出口，不打开诊断分享 |

**Apple 合集 200**适合把所列成员交给同一出口，包含 123，排除独立的 228。要同时做到账户代理、更新与 iCloud 大文件直连，就选细分表，不用 200。大流量域名无法完全按认证与静态内容拆开，需用小文件与短视频对照实际请求，不能仅根据组名估算代理流量。

Apple TV、News、Fitness+、Apple Intelligence 等先满足服务支持条件，再选择能用的代理；普通系统联网与已能直连的下载不必追求地区一致。[Apple 服务地区](https://support.apple.com/en-us/118205) · [Apple Intelligence 要求](https://support.apple.com/en-us/121115)

Apple 公布的[企业网络端点](https://support.apple.com/en-us/101555)用于核对部分用途，不是全部消费者流量清单。不同国家也可能共用同一主机和不同 URL 路径，域名规则分不出这些路径；不使用整个 Apple IP 段假装完成地区或业务细分。[推送怎样实测](network-testing.md#apns-推送)

## AI：按产品与实际地区入口选择

| 范围 | 选择与边界 |
|---|---|
| 海外 AI | 统一出口选 100，分别选路则用成员。Claude 101、OpenAI 102、Gemini 103 等保持各自登录、API、文件与对话出口稳定 |
| 其他海外 AI 产品 | Amp、AnythingLLM、Fireworks、OpenCode、Kilo、Cline、Replicate、Runway、Replit 等也在 100 内，成员以清单为准。官网、API 与自建地址按产品边界处理，不把整个云平台划给 AI |
| xAI | 104 包含 Grok、xAI API 及相关产品的共用账号主机。Grokipedia 内容 105、Cursor 编辑器 110、X 社交 334 分别处理；单独选择相关产品时，也需让共用认证出口可用 |
| 国产 AI 国际版 | 125 或其产品成员，包含模型平台及 Qoder、YouMind、Lovart 的国际产品入口；小米 MiMo 的新加坡、欧洲计划只收目录明确列出的 API |
| 国产 AI 国内版与共用入口 | 500 或其产品成员，包括 501–515、518–519；DeepSeek、文心、讯飞、魔搭、小米 MiMo 等各自说明范围，不把全部国产 AI 统称一个产品 |
| JetBrains AI | 海外后端 124、中国区 API 516；IDE 与插件等在 309，516 不并入国产厂商合集 |
| Apple 系统 AI | 123 同时列在 AI 使用顺序中，归属 Apple 生态；不在海外 AI 合集 100 内 |

认证和模型请求尽量用同一稳定出口，长回复或上传过程中避免切节点。产品规则不要求禁用 QUIC、IPv6 或 HTTP/3，异常时根据真实连接比较协议与地址族。

OpenAI 102 的语音地址来自[官方公开 JSON](https://openai.com/chatgpt-voice.json)，使用 `no-resolve`，与专用域名选择同一出口。节点仍须支持实际使用的 UDP 或 TCP 路径。[OpenAI 网络要求](https://help.openai.com/en/articles/9247338-network-recommendations-for-chatgpt-errors-on-web-and-apps)

Claude 网页、App、Desktop、Code 和 Anthropic API 使用 101 的产品范围，工具调用访问的第三方网站仍按目标网站处理。通用 GitHub、包源、Google Storage 与云平台网关不整域归入 AI。[Claude Code 网络要求](https://code.claude.com/docs/en/network-config)

iPhone 的 Loon 不控制另一台 Mac 或 PC；Desktop、Code 和 API 客户端要在实际运行设备上单独验证。

## 海外与国内产品分别管理

下列产品都有独立订阅，多份规则可绑定同一个出口。已知国内镜像和国内版另列，不按厂商注册地把国际入口直连。

| 大类 | 已分出的产品与用途 |
|---|---|
| 海外开发 | GitHub、GitLab、Bitbucket、npm、Maven Central、PyPI、Docker Hub、Rust/Cargo、Go、JetBrains IDE、Node.js、ACP |
| 海外通讯与社交 | Telegram、Discord、Signal、LINE、X、微信国际门户、Slack、Reddit |
| 海外支付 | PayPal、Stripe、Link、Braintree、Venmo、Xoom；商户网站、银行和本地读卡器各自处理 |
| 加密资产 | Binance、OKX、Gemini Exchange、Trust Wallet；Gemini 交易所与 Google AI 分开，第三方 DApp 和公链 RPC 不整包归钱包 |
| 海外媒体 | HBO、YouTube、Netflix、Disney+、Prime Video、Spotify、Twitch、TikTok、哔哩哔哩国际、巴哈姆特、BBC、爱奇艺国际版；统一出口可用 380 替代成员 |
| 海外游戏 | Steam、Epic、PlayStation、Nintendo、HoYoverse、EA、Ubisoft、Battle.net；不代表所有对局 IP 都已覆盖 |
| 海外协作 | Notion、Figma、Trello、Atlassian Cloud；Bitbucket 与 Trello 先匹配，共用 Jira、Confluence 和平台资源随后处理 |
| 国内开发 | Gitee、CODING、GitCode、npmmirror、TUNA 镜像；不会替 npm、pip 或 Maven 修改软件源 |
| 国内通讯与支付 | 微信共用服务、钉钉公共产品、豆瓣、微博、支付宝、银联；无法按同一共享主机区分用户所在国家或全部支付用途 |
| 国内媒体与游戏 | 哔哩哔哩、抖音、爱奇艺、优酷、QQ 音乐、酷狗、快手，Steam 国内下载、米哈游国服、WeGame |
| 国内购物与社区 | 淘宝与闲鱼、京东、小红书、知乎、12306；新浪图片作为跨产品共用资源独立处理 |

产品专用附件、登录和 API 尽量跟随产品。共享云、用户自定义域、第三方插件和自建实例按自身目标匹配，不收进公共产品表。常用规则的来源与边界可在清单直接查看。

## Google、Microsoft 与共享平台

两个生态位于海外具体产品之后、国内产品之前。原因是同一平台会为其他产品托管服务：Discord 专用上传主机先归 Discord，普通 Google 存储才由 Google 处理；不把整个 Azure 租户平台交给 Microsoft。

| 生态 | 细分用途 | 建议 |
|---|---|---|
| Google | 学术、账户、Gmail、Meet、Drive/Docs、Play、Play 游戏、软件下载、共用服务 | 大陆不可用的服务走代理。统一出口用 450；会议和大文件需要不同路径时改选成员。Gemini、YouTube 独立于 450 |
| Microsoft | VS Code、Power BI、账户、Outlook、Teams、OneDrive/SharePoint、更新检查、更新与商店下载、商店、Office 下载、Xbox、共用平台 | 工作与会议用已测通的线路；大包可单独试直连。统一出口用 470；GitHub 和两个 Copilot 各自独立 |

Google 地区登录从官方模板和域名表生成；Gmail、Play 与 Play 游戏读取仍公开的 API 版本。Microsoft 登录与控制入口读取官方定义，Azure 租户后缀及会整体覆盖租户的父域不因此认领。Meet、Teams 的官方媒体网段带 `no-resolve`，共享通信地址不能再按发起 App 细分。[Drive 网络要求](https://knowledge.workspace.google.com/admin/drive/drive-and-sites-firewall-and-proxy-settings) · [Microsoft 365 端点](https://learn.microsoft.com/en-us/microsoft-365/enterprise/urls-and-ip-address-ranges)

## 最后只选一套补充

| 规则 | 做什么 | 怎么用 |
|---|---|---|
| 670 | 其他海外影音 | 专项之后交给影音策略；已经有独立表的服务仍需选择专表或合集 |
| 675 | 其他海外网站与 GFW 域名 | 专项之后交给通用代理，早于国内补充；已采用的海外与 GFW 来源优先于宽泛国内范围，继续排除共享基础设施 |
| 702 | 国内补充合集 | 把域名、网段和 GeoIP 交给同一国内策略 |
| 704、707、711 | 702 的三个成员 | 需要分别控制时替代 702。只按国内域名判断可仅选 704，其余继续到后续规则与 `FINAL` |

海外补充不自动搬到所有国内产品前面：具体产品已有明确用途，先按产品处理；海外补充随后补缺，再交国内宽范围判断。上游来自海外大表也可能有国内或共享域，不能靠移动整份表保证准确。

国内大表与已采用的海外或 GFW 来源相交时，不能因为“国内表也收了”就删掉代理规则。675 保留这些来源的范围，704 让出被完整接住的重合条目；国产 AI 国内版等具体产品仍先匹配。爱奇艺国际专用子域先由 392 处理，592 的国内父域留在后面，不能只根据 iqiyi.com 判断两版出口。

本地、插件和订阅共同决定真实结果。域名阶段与 IP 阶段的匹配、DNS 解析及系统 VPN 路由还须分别检查，见[连接与防泄漏测试](network-testing.md)。

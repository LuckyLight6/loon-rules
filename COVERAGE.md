# 各服务怎么选出口

在[编号清单](INDEX.md)找到要订阅的规则，再到这里看它适合走直连还是代理。共用同一个域名的业务不能靠域名规则拆开。

## Apple：先保证海外服务可用，再给能直连的流量省配额

以下建议针对**中国大陆网络、`FINAL` 走代理**的配置。[Apple 中国大陆媒体服务清单](https://support.apple.com/zh-cn/118205)未列出 Apple TV 订阅、Fitness+ 和 News+；这些服务的入口和播放走可用代理。内网、系统服务和确认能直连的下载单独处理。Apple 账户和商店交易用同一个稳定出口。

CDN 说明内容从哪里交付，不说明谁能获取。公开图片可以匿名访问；受限内容可能要求会话或临时链接，受保护的音视频还可能单独申请播放许可。域名规则不按这些授权条件分流。系统更新包的下载也和设备的安装授权分开处理。参见 [iCloud 分享链接](https://support.apple.com/en-ca/guide/icloud/mm93a9b98683/icloud)、[FairPlay Streaming](https://developer.apple.com/streaming/fps/) 与 [Apple 安全软件更新](https://support.apple.com/en-ie/guide/security/secf683e0b36/web)。

代理有流量上限时，先把能直连的安装包和更新包单独分出去。美区账户可以用已知稳定的美国节点，方便排查；账户并不因此必须使用美国 IP。TV、News 和 Apple Intelligence 还要看订阅、账户地区、设备销售地区和语言。服务端点见 [Apple 企业网络文档](https://support.apple.com/en-us/101555)；媒体、定位和 CDN 别名的来源见规则文件头。

| 编号 · 业务 | 推荐出口 | 用途和理由 |
|---|---|---|
| 012 · 联网探测 | 直连 | `captive.apple.com` 等用于发现酒店、机场的 Wi-Fi 登录页；探测须针对当前网络。 |
| 030 · Apple 合集 | 要统一代理时才选 | 含海外媒体和系统 AI，不能绑直连。要按用途省流量，改选细分；049 仍独立。 |
| 031 · Apple 账户 | 手选固定代理 | 登录、恢复、令牌和部分 iCloud 初始化。与 036 共用一个已测稳定的节点，不用自动测速切换。 |
| 032 · 通用链接与关联域 | 直连 | 系统检查 App 与网站的关联，影响通用链接、App Clips 等。先保留当前网络路径。 |
| 033 · 应用和设备验证 | 直连优先 | App Attest、设备验证、macOS 公证。即使是 `s.mzstatic.com` 也可能是验证，不当成普通图片 CDN。 |
| 034 · Wallet / Apple Pay | 保留现有可用出口，通常先直连 | 包含 Tap to Pay 设置主机 `humb.apple.com`。支付还依赖账户、设备、商户和地区资格，不默认全走美国。 |
| 035 · TestFlight | 手选，与商店交易同出口 | 邀请和测试安装命令与商店流程相关；只有实际匹配到 037 的下载才另走下载策略。 |
| 036 · App Store 交易 / Apple Books 商店 | 与 031 同一固定代理 | 商店目录、购买与安装指令跟登录保持同路；已核对的图书商店门户也在这里，包体不一并代理。 |
| 037 · App 安装包 | 直连优先 | `iosapps.itunes.apple.com` 等下载主机可能流量很大。商店页正常但下载失败时，只给下载组手动换路。 |
| 038 · APNs 推送 | 保留实测能收通知的路径；直连丢推送时单独试代理 | 系统推送连接和 App 自身的注册、同步是两条链路。按 [推送对照测试](NETWORK-VERIFICATION.md#apns直连有些-app-不推送先分开测)定位。 |
| 039 · 定位和查找 | 直连可用就保持，否则单独试代理 | 覆盖已知的 Find My 移动端和数字分片。网页 `icloud.com/find` 用的是 iCloud 共用域；也要确认账户和推送都正常。 |
| 040 · iCloud Private Relay | 启用且地区支持时给可用代理 | 只匹配中继入口。验证 Safari 出口时另行记录是否启用了系统私密转送。 |
| 041 · 大陆分发别名 | 命中则直连 | 只列已经核对的 `cn-lb` 别名。请求若仍显示原始主机名，就由其业务规则决定；别名不保证落到大陆节点。 |
| 042 · iCloud 同步与共享服务 | 和 053 用同一已验证出口；直连确实能同步才直连 | CloudKit、照片、备份和邮件会共用主机。先用小文件验证上传、下载和第二设备同步。 |
| 043 · Music / 广播入口 | 与 056 先一起试直连 | 包括 Music 页面、API 和部分共用内容。登录与播放都成功再保留直连；目录正常不代表能播放。 |
| 044 · TV / Fitness+ 入口 | **默认代理，跟 057 同一路** | 大陆服务清单不含对应订阅。门户能开不等于播放可用，两组一起测。`blobstore.apple.com` 也用于[音乐人图片的签名上传](https://itunespartner.apple.com/music/assets/music-artist-api.pdf)，不按 TV 识别。 |
| 045 · News / Sports | **默认代理** | 新闻门户、正文相关主机和体育服务，先按对应账号支持的地区选出口。 |
| 046 · Apple Intelligence / PCC | **默认独立代理** | 已核对的 PCC 和系统 ChatGPT 扩展。Apple 与 AI 两章是同一个规则入口，不跟独立 ChatGPT App 共用。 |
| 047 · Siri / 听写 / 搜索 | 保留普通 Siri 能用的出口 | Siri AI 已有独立资格条件，共用 Siri 主机暂不按版本硬拆；实际日志显示请求属于这组且失败，再对照切换。 |
| 048 · 系统更新检查 | 直连优先 | 软件目录、恢复检查和 `beta.apple.com` 系统测试版登记不等于下载，也不是 TestFlight。 |
| 049 · 证书状态 | 直连 | OCSP 等可能被其他厂商共用；独立于美区账号及 Apple 合集，避免不必要的系统验证延迟。 |
| 050 · 开发者下载 | 直连优先 | 只分实际文件主机，如 `devimages-cdn.apple.com`。[开发者门户](https://developer.apple.com/download/)同时提供文档和账户入口，不整站当作下载；跳转到认证主机后走 031。 |
| 051 · 激活与系统联网 | 平常直连，受管设备遵从现有网络要求 | 包括设备激活、MDM、诊断、校时与个别 DNS 或 RCS 主机。不是全匿名，也不替换 Loon 的 DNS 设置。 |
| 052 · 商店与媒体共用素材 | 直连优先 | 封面、截图和网页素材常由共用 CDN 提供。保留 033 等更具体规则的优先级，不当成全站下载。 |
| 053 · iCloud 通用内容域 | 上传和下载都测通再走直连 | 大文件直连能省流量；但这一组不覆盖全部备份，也不代表内容匿名或位于大陆。 |
| 054 · iMessage / FaceTime 身份 | 直连优先 | 这组是消息与通话身份入口，不覆盖所有媒体路径；需同时验证 038 和通话。 |
| 055 · OTA 与恢复下载 | 直连优先 | 系统镜像和更新包体积大。不要自动把整份包转到代理；检查失败要先区分 048 和 055。 |
| 056 · Music 已识别音频 | 直连优先 | 有专用音频域才单列。能正常播放就保持直连；其它共用流量由 043 处理。 |
| 057 · TV 已识别视频 | **默认与 044 同一代理** | 视频仍要计入代理流量。先保证能播，再通过画质或用量控制配额，不用未经验证的直连切断会话。 |
| 058 · 中国大陆 iCloud 专域 | 直连 | `icloud.com.cn`、`apzones.com` 和已核验 Apple DNS 委派的 `icloud-content.com.cn` 独立，未把其他 iCloud 流量划成大陆。 |
| 059 · Schoolwork 作业资料 | 直连优先；有机构要求时用其网络 | 只匹配作业资料入口，共享账号、设备验证和管理是另外的链路。 |

`193` 涵盖多种用途，是兼容备选，不能当作大陆直连清单。第一次试用，先确认 TV、News 和 Apple Intelligence 走代理，再用一个小 App 和一张照片检查直连。不用先跑全量备份或播放长视频。

**地区不同不等于域名或 IP 不同。** Apple 明确给大陆 iCloud 标出区域域名，且服务由[云上贵州运营](https://support.apple.com/zh-cn/111754)。相反，Apple TV 的[日本入口](https://tv.apple.com/jp)和[美国入口](https://tv.apple.com/us)共用 `tv.apple.com`，域名规则看不到 `/jp`、`/us`。Apple 公布部分服务的网段，例如 [APNs](https://support.apple.com/en-us/102266) 和 [Private Relay 出口](https://developer.apple.com/icloud/prepare-your-network-for-icloud-private-relay/)；后者标记的是中继 **出去访问网站的 IP**，不用于匹配设备访问 Apple 的目的地址。其他地区未见可给 TV、News、账户逐项分组的官方 IP 清单；[Apple 明示 CDN CNAME 随时变化](https://support.apple.com/en-us/101555)，不按整个 Apple IP 段分流。

## Google 和 Microsoft：专项排在共享平台前

| 生态 | 可独立选出口的业务 | 出口选择 |
|---|---|---|
| Google · 160–169 | 账号、Gmail、Meet、Drive/Docs、Play、软件包、共享服务。统一出口时用 160 替代细分。 | 大陆不可达的服务默认代理；要节省软件下载额度时用细分，确认可用才直连。Gemini 和 YouTube 仍优先按 AI／媒体专项。 |
| Microsoft · 100–115 | 账号、Outlook、Teams、更新、商店、Xbox、OneDrive、Office 包体、共享服务。统一出口时用 100 替代细分。 | 更新包和 Office CDN 能直连就直连。工作业务保留已验证的可用网络；Microsoft Copilot、GitHub 与 GitHub Copilot 仍独立。 |

只单列产品能认出的主机。 `www.googleapis.com`、Google 通用存储与素材、Microsoft Graph、通用 Azure 容器都不归某个产品；同一个域名里的不同路径，以及没有域名的会话媒体，不能靠产品域名分开。来源：[Google Drive 端点](https://knowledge.workspace.google.com/admin/drive/drive-and-sites-firewall-and-proxy-settings)、[Google Meet 网络要求](https://knowledge.workspace.google.com/admin/meet/prepare-your-network-for-meet-meetings-and-live-streams)、[Microsoft 365 端点](https://learn.microsoft.com/en-us/microsoft-365/enterprise/urls-and-ip-address-ranges)、[Windows 更新和商店端点](https://learn.microsoft.com/en-us/windows/privacy/manage-windows-11-endpoints)。

## 更新前查哪些误匹配

首条规则匹配错了，后面就算有正确规则也用不上。自动更新检查**所有默认表和合集顺序**，拦住前面的规则把后面的专项整个盖住。专表在前、父域兜底在后是有意的；两份明确二选一的宽表也可以共有域名。

另有一份[厂商端点清单](endpoint-contracts.json)，以官方资料为准，不从已有规则反推。联网更新会重读选定的 Apple 官方表和 Claude Code 网络端点表。有主机新增或消失，或有入口被前面的规则抢走，就保留上一个版本。Google、Microsoft 及 Claude 网页和桌面只核对清单点名的入口。共享域名注明不归某个产品的原因；文档没列出来的实际请求，还得看设备日志。

- **局域网 vs. 公网。** 011 收 [小米](https://www.mi.com/global/support/faq/details/KA-226613/)、[水星](https://service.mercurycom.com.cn/article-86.html)、[TP-Link](https://www.tp-link.com/us/support/faq/2394/) 等有出处的管理名；小米公网帮助、下载仍走国内公网。默认与国内域名备选都检查局域网管理名的精确重复与后缀覆盖。
- **哪些 IP 规则可以触发 DNS。** 011 的 IPv4／IPv6 链路本地、组播、文档及保留地址只按已知目标 IP 匹配；`.local` 等局域网名字照样按域名分流，私网、内网 VPN 和回环保留按名称访问所需的解析。200、204 是域名未命中后的地址识别，也保留解析。[Loon 的 IP 参数](https://nsloon.app/docs/Rule/ip_rule/#no-resolve) · [IPv6 链路本地地址的 DNS 边界](https://www.rfc-editor.org/rfc/rfc4472.html#section-2.1)
- **办公 vs. 公共云。** `netflix.com.edgesuite.net` 按 Netflix 而非 Microsoft 选路。`edgesuite.net` 等 [Akamai CDN 后缀](https://techdocs.akamai.com/edge-hostnames/docs/edge-hn-terminology)及 `azurewebsites.net` 等 [Azure 多租户域](https://learn.microsoft.com/en-gb/azure/security/fundamentals/azure-domains)不能靠整段后缀判定产品。通用与备选表都不导入这些整段。
- **海外 Apple vs. 直连。** TV／Fitness+、News／Sports、PCC 和 TV 视频四组参与与国内、直连、Apple 兼容候选的交叉检查。识别不了的请求继续按现有顺序走兜底；未发现域名不意味着国内可访问。

DNS 和 WebRTC 各有自己的出口。规则命中没有问题后，再按[网络测试步骤](NETWORK-VERIFICATION.md)检查设备的真实连接。

## AI：按产品和入口，不按集团或共享 CDN

- **Claude 061。** [Anthropic 文档](https://code.claude.com/docs/en/network-config#network-access-requirements)列出的自营入口中，登录与续签（`claude.ai`、`platform.claude.com`、`sso.claude.com`）、API、Claude Code 更新、`bridge.claudeusercontent.com`、Artifact 和 MCP 小组件专域走同一专项。通用 GitHub、npm 和 Google Storage、第三方 MCP、云厂商网关保持原有业务分类。iPhone 的规则不配置 Mac 的 Claude Code 或 Desktop；SSE、长推理与上传还得用实际出口和设备验证。
- **Apple Intelligence 046。** AI 章与 Apple 章引用同一份表。它从 [Apple 官方网络表](https://support.apple.com/en-us/101555)筛选 PCC 及扩展入口，和普通 Siri、系统更新、独立 ChatGPT 分开。 [Apple Intelligence](https://support.apple.com/en-us/121115)和 [Siri AI](https://support.apple.com/en-hk/127893)的资格以设备、语言和账户支持为准；不要把共享 Siri 或模型下载域当作专用推理入口。
- **082 ai.com** 是[独立的 AI 助手服务](https://ai.com/start)，不属于 ChatGPT。单独选择 082，或随 060 共用海外 AI 出口。
- **各产品独立。** Grok 和 xAI API 用 064；X 社交在 093，Grokipedia 在 080。Muse 的 `muse.ai` 用 077，Meta AI 的 `meta.ai` 用 079；两者不匹配 Facebook 等共享平台。国产国内版和国际版按公开入口区分，同一主机不会因为账号或客户端语言不同被强拆。
- **也测不该命中的请求。** `storage.googleapis.com` 不能落到 Gemini、Drive 或 Claude 专用规则；仅包含 google、discord 等字样的无关主机不能被海外兜底接管。单独替换每个合集和同时替换所有合集都检查首条命中。

[status.json](status.json)记录已发布规则的命中检查和上游核对情况。设备的 DNS、WebRTC、CDN 调度和长连接要实测。ChatGPT 的 WebSocket 和文件入口按 [OpenAI 网络文档](https://help.openai.com/en/articles/9247338-network-recommendations-for-chatgpt-errors-on-web-and-apps)核对；语音的 UDP/3478 不靠扩大域名范围或代理整个共享网段解决。

## 备选规则怎么选

### 日常选三份

| 规则 | 管什么 | 怎么判断 |
|---|---|---|
| [180 其他海外影音](rules/180-other-overseas-media.lsr) | Hulu、Max、BBC 等未单列的影音 | 只按域名。Netflix、Apple TV 等已有专项的服务先用专项。 |
| [185 海外站点和 GFW](rules/185-overseas-access-domains.lsr) | 不归其他专项的海外站点 | 只按域名。和 180 一样，生成时扣除已被前面规则完整覆盖的范围。 |
| [192 国内分流合一](rules/192-mainland-routing.lsr) | 同一个国内策略接收域名、网段和 GeoIP 命中 | 先看域名，没命中再按地址判断，网段优先于 GeoIP。 |

想分别控制，就用 `194`、`200`、`204` 替换 `192`：194 只收国内域名，200 查明确网段，204 再查 Loon 的地区数据库。只想按已知域名选路、不启用这两条国内地址兜底时，只选 194。未命中的连接由 `FINAL` 决定。

### 已放进常规规则的入口

- **036 商店交易**：Apple 的 [iTunes 配置](https://init.itunes.apple.com/bag.xml?ix=6) 把 `fpinit.itunes.apple.com` 用于签名初始化，跟商店交易走同一策略，不归下载。
- **055 更新下载**：[Apple 列出的下载主机](https://support.apple.com/en-us/101555) `swcdn.apple.com` 和 `updates-http.cdn-apple.com` 各有 DNS 别名。核对后只加三个确切主机；`mesu` 的更新目录仍归 048。
- **084 国内 AI**：加入[哩布哩布国内站](https://www.liblib.art/document/article_member)和[专用 API](https://www.liblib.art/apis/workflow)。`qwen.ai`、`z.ai` 仍走 085 国际入口，不按厂商所在地改成国内。
- **152 Steam 国际服务**：[Steam 商店](https://store.steampowered.com/) 的页面安全策略列出了社区素材和直播用的两个专用 CDN 主机。只加入这两条，151 的国内下载镜像不变。
- **194 国内域名**：加入[鸿蒙智行](https://hima.auto/privacy/privacy-policy/)官网及跳转到官网的 `www` 入口，不扩到其他域名。

### 哪些整表不该默认打开

影音只补域名用 180，海外站点和 GFW 用 185，国内三种判断用 192。185 和代理兜底选同一出口时，185 的作用是标出已知站点，并抢在国内地址兜底前匹配；没收录的站点仍按后续规则走。以下文件保留原订阅地址，不代表应该全部启用。


| 编号 | 怎么处理 | 原因 |
|---|---|---|
| [181](rules/181-overseas-media-remainder.lsr) | 保留现有的影音订阅；日常选 180 | 保留上游域名的完整覆盖；180 只补各影音专项没有覆盖的域名。 |
| [182](rules/182-overseas-media-with-client-matches.lsr) | 保留客户端兼容用途 | 域名部分已由 180 和各影音专项承接；选择它是为了另用客户端标识。 |
| [183](rules/183-overseas-media-address-compatibility.lsr) | 单独可选，不替代 180 | 不含精确域名或后缀；按地址、关键字、URL 或客户端匹配，容易接管不属于本组的请求。 |
| [184](rules/184-overseas-site-fallback.lsr) | 作为 185 的域名来源，不建议单独用 | 小表仍与国内来源相交，并不是 185 的纯子集。185 先剔除有争议的范围；条数见[来源检查](REVIEW.md)。 |
| [186](rules/186-overseas-site-wide-compatibility.lsr) | 保留宽版兼容；日常用 185 | 除域名外还有 IP 和客户端规则，部分网段写法对不齐掩码。常规只合并域名。 |
| [187](rules/187-overseas-address-and-client-matching.lsr) | 改为单独可选，不替代 185 | 公开文件只有 IP 与客户端规则；关掉 185 使用它会丢掉域名覆盖。 |
| [188](rules/188-restricted-sites-and-addresses.lsr) | 保留地址兼容用途；日常用 185 | 核准的 GFW 域名已合进 185，确认为 Steam 专用的主机用 152；不顺带开启整个地址表。 |
| [190](rules/190-direct-domain-exceptions.lsr) | 不作通用直连 | 和 Google 及广告拦截范围有交叉。目的明确的域名交给原专项。 |
| [191](rules/191-direct-domain-exceptions-extended.lsr) | 不作通用直连 | 混有自建 NAS 的 DDNS、站点素材和 Apple 端点；域名后缀不能说明服务器在用户的本地网络。 |
| [193](rules/193-apple-mainland-service-alternative.lsr) | 不作 Apple 大陆直连 | 混有定位、系统、商店和下载。确认是包体下载的别名才放进 055。 |
| [196](rules/196-mainland-service-domains.lsr) | 只在拆开订阅时替换 194，不与 192 叠加 | 与 194 来源不同，有独有域名。两表都会剔除 085 的国际版 AI 范围，包括会吞掉 `chat.qwenlm.ai` 的父后缀；不能只靠订阅顺序避开错分。 |
| [197](rules/197-mainland-extended-coverage.lsr) | 不纳入默认地址表 | 没有专用域名，混有 ASN、客户端和宽 IP；相比 200 新增的地址包含 APNIC 登记为非 CN 的段。 |
| [201](rules/201-mainland-address-registry.lsr) | 不与 200 合并启用 | 历史范围并非全部登记在 CN。新增范围同时核对分配与路由，仍不能把整表当作实际地理位置。 |
| [202](rules/202-mainland-asn-classification.lsr) | 明确需要按已知 IP 查 ASN 时才选 | 带 `no-resolve`，不为按 ASN 分类触发 DNS 查询。 |
| [203](rules/203-mainland-asn-with-resolution.lsr) | 明确需要域名解析后查 ASN 时才选 | 来源、ASN 名单与 202 都不同。这份允许为归属查询解析域名；不是单纯去掉一个参数。 |

[APNIC 的分配记录](https://www.apnic.net/manage-ip/manage-resources/address-status/by-rir/)标的是资源分配地，不能证明服务器在哪，也不能证明某条线路能直连。国内地址和 ASN 不是给全体业务选出口的第一依据。

`021` 只拦已核实的广告入口；`025` 默认关闭，`026` 需要接受语音和会议可能受影响时才启用。合集给同一出口换一种订阅方式，与成员二选一。

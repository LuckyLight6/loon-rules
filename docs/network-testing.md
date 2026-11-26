# 检查实际命中和连接

在 Loon 请求记录里看 **目标主机、命中规则、最终节点**，再确认业务有没有完成。`TCP` 只是传输类型；规则栏显示 `FINAL` 才表示走兜底。页面能打开，也不能代替上传、播放、推送或持续流式输出的测试。

## 用配置副本逐项试

先导出最初的配置并妥善保留，再复制一份用于测试。同时记下客户端版本、DoH 出口模式、查询回落和系统 DNS 设置；这些全局设置不会随配置副本一起回退。在同一网络、同一手选节点下，先用原配置完成操作，再在副本中加一组订阅对照。每次只调整一项；重新打开 App 或建立新连接后看记录，不先改 IPv6、QUIC 或 DNS 来掩盖原因。

订阅按[清单](rules.md)顺序排列。下表列出细分表；使用合集时，以对应合集作为预期命中。如果先命中本地或插件规则，移动订阅位置不会解决，应找到那条先命中的规则。切回原配置和原节点可作回退；多设备各自测试，不把一台的结果当作另一台的结果。[Loon 匹配优先级](https://nsloon.app/docs/Rule/#匹配优先级)

| 测试对象 | 实际操作 | 通过条件 |
|---|---|---|
| Claude [1010](../rules/loon/1010-claude-connections.lsr) | Safari 和 App 分别上传无敏感内容的 PDF，要求按附件连续回答；Desktop、Code 在实际运行的电脑另测 | 附件内容可读，流式回复持续到完成；专用登录、API 与附件用预期出口 |
| OpenAI [1020](../rules/loon/1020-chatgpt-connections.lsr)、Gemini [1030](../rules/loon/1030-gemini-connections.lsr)、xAI [1040](../rules/loon/1040-xai-connections.lsr) | 分别完成一次流式对话；OpenAI 再试持续语音 | 对话完成，规则与出口正确；语音实际使用的 UDP 或 TCP 路径能持续传输 |
| Apple 账户 [2090](../rules/loon/2090-apple-account-authentication.lsr)、商店 [2130](../rules/loon/2130-apple-store-transactions.lsr)，或日常合集 [2080](../rules/loon/2080-apple-direct-all.lsr) | 正常打开账户页面和商店，观察已有会话的认证或续签；不为测试反复退出登录 | 出现的认证与交易主机按预期选路；没有出现续签只能记未测到 |
| Apple 官网与补充 [2370](../rules/loon/2370-apple-other-services.lsr) | 打开官网、支持与隐私页面，再打开账户注册入口 | 官网由 [2370](../rules/loon/2370-apple-other-services.lsr) 识别，账户与认证仍由 [2090](../rules/loon/2090-apple-account-authentication.lsr) 识别；已有系统和内容直连例外没有被补充表抢走 |
| App 包 [2140](../rules/loon/2140-apple-app-package-downloads.lsr)、iCloud 内容 [2200](../rules/loon/2200-apple-icloud-content-domains.lsr)／同步 [2210](../rules/loon/2210-apple-cloud-sync.lsr)、更新检查 [2260](../rules/loon/2260-apple-update-control.lsr)／更新包 [2270](../rules/loon/2270-apple-update-downloads.lsr)，或日常合集 [2080](../rules/loon/2080-apple-direct-all.lsr) | 下载小 App；上传小文件后在第二设备下载；检查更新 | 各操作按相应用途选择出口，[2080](../rules/loon/2080-apple-direct-all.lsr) 默认直连。下载必须实际完成；只查更新没有测到系统包下载，[2210](../rules/loon/2210-apple-cloud-sync.lsr) 也可能有上传下载 |
| CloudKit 网关 [2210](../rules/loon/2210-apple-cloud-sync.lsr)、证书检查 [2320](../rules/loon/2320-apple-certificate-validation.lsr) | 在正常使用中观察 `gateway.icloud.com`、`ocsp2.apple.com` | 前者属于 CloudKit 内容连接，后者检查证书状态；均保留正常访问，不因请求频繁而拒绝 |
| TV 门户 [2040](../rules/loon/2040-apple-video-and-fitness.lsr)／视频 [2050](../rules/loon/2050-apple-tv-video-delivery.lsr)、News [2060](../rules/loon/2060-apple-news-and-sports.lsr) | 实际播放一段可用内容，打开有权阅读的新闻正文 | 播放与正文完成，门户及内容连接均走预期出口 |
| Apple Intelligence [2020](../rules/loon/2020-apple-intelligence-relays.lsr)，或海外功能 [2010](../rules/loon/2010-apple-overseas-all.lsr) | 触发受支持的云端功能，再试系统 ChatGPT 扩展 | 实际产生的 PCC 或扩展连接命中 [2020](../rules/loon/2020-apple-intelligence-relays.lsr) 或 [2010](../rules/loon/2010-apple-overseas-all.lsr)；纯本地运算不算云端测试 |
| GitHub [3010](../rules/loon/3010-github-code-and-packages.lsr)、Docker [3070](../rules/loon/3070-docker-hub.lsr) | 访问 API，下载公开文件；登录 Docker 并拉取公开镜像 | 业务成功，专用入口归属正确，广告规则没有拒绝必需主机 |
| Telegram [3310](../rules/loon/3310-telegram-messaging.lsr) | 打开 App 等待同步，发送文字并下载一个小文件 | 域名与直接使用的服务器 IP 都命中 Telegram 细分或所选通讯合集；只打开网页或 Bot API 不能代替 App 测试 |
| 微信 [6510](../rules/loon/6510-wechat-shared-and-mainland.lsr)、WeChat 国际入口 [3360](../rules/loon/3360-wechat-international-portal.lsr) | 打开 App 等待同步，再试消息、图片与通话 | 检查实际连接，不能把 `wechat.com` 全当成网页；额外的 HTTPDNS 拦截插件可能先拒绝服务器发现请求 |
| Meet [4530](../rules/loon/4530-google-meet-meetings.lsr)、Teams [4730](../rules/loon/4730-microsoft-teams-meetings.lsr) | 双向音视频并共享屏幕 | 声音、画面和共享持续传输，专用主机与媒体地址按预期选路 |

Google 安全浏览 API 从官方服务字段生成，并受必需端点保护。全球入口与 `googleapis-cn.com` 的已列入口交给 Google，腾讯入口保留国内选路，均不当作广告拦截。[Apple 说明 Safari 会使用 Google 与腾讯的安全浏览服务](https://www.apple.com/legal/privacy/data/en/safari/)。核对命中时不需要提交真实网址、浏览记录或 API 密钥。

另装广告插件时，先核对它的拦截范围。部分合集还拦隐私统计、推送、更新或安全检查，不能把这些都当成广告。AWAvenue 提供[纯广告版](https://raw.githubusercontent.com/TG-Twilight/AWAvenue-Ads-Rule/main/Filters/AWAvenue-Ads-Rule-Loon-Only.Ads.module)，可在保留其广告规则的同时不启用另外两类；本仓的隐私表仍单独选择。插件命中早于订阅时，应调整插件，不能靠后面的订阅放行。

记录显示“已完成”，只说明这条连接已经结束，还要结合上传量、下载量和日志判断。UDP 没有收到数据、随后 TCP 成功，不能把两条都算成业务成功；只有连接数量，也不足以判断反复重试或耗电原因。Apple 官方将 [CloudKit 网关和证书检查](https://support.apple.com/en-us/101555)列为正常网络服务；验证这些连接不需要解密账户请求。

只记公开主机、版本、命中规则和结果；请求 URL、头部、日志里可能有登录信息，不要整份提交。

Telegram 原生客户端可按服务器 IP 使用 TCP，443 端口也不一定承载 HTTPS。3310 保留[官方地址表](https://core.telegram.org/resources/cidr.txt)的全部网段，并以注册持有人仍为 Telegram 的 ASN 补充裸地址匹配，两类规则都使用 `no-resolve`。ASN 是否实际命中还受客户端数据影响；检查登录、同步和文件下载时，记录域名、CIDR 或 ASN 的真实命中，不能只搜 `telegram.org`。[Telegram 传输协议](https://core.telegram.org/mtproto/transports)

## DNS：先看查询走了哪里

HTTPS 走代理不代表 DNS 也由代理解析。在 Wi-Fi、蜂窝分别查询允许公开、未缓存的名称，查看 Loon DNS 记录中的解析器和传输方式；能够管理网关时，再核对本机是否出现意外的 TCP/UDP 53 流量。内网名称只在有权访问的网络里测，不发给公共检测站。

- `dns-server = system` 沿用系统解析器，没有因此启用公网 DoH。内网 VPN 的分域解析器也需要保留
- [可选 DoH 插件](../plugins/public-services-doh.plugin)把所列海外业务交给 Cloudflare，把国产 AI 国内版与所列直连 Apple 服务交给阿里；其他名称不改。若 VPN 需要回答其中某个同名域，先在配置副本中处理
- 按实际访问路径选择解析器，不必按服务所属公司配对。国内直连关注本地 CDN 与可达性；海外代理关注出口附近的结果、完整性和隐私。Google、Cloudflare、阿里、腾讯都能解析其他公司的域名。解析器位置和 ECS 会影响 CDN 调度，见 [Google Public DNS 说明](https://developers.google.com/speed/public-dns/faq)
- 插件只使用 `[Host]` 指定上游，不设置 DoH 连接的代理出口。单独查看 DoH 连接是否走预期路径，再测试故障回落；电脑上访问接口成功，不代表 iPhone 上的 Loon DNS 查询已通过验收
- 要求这些公网查询不能回落到明文 DNS 时，在「配置 → DNS 服务器」关闭「查询回落」。这个设置影响设备上的其他加密 DNS，切换配置不会自动恢复
- 在可控测试网络中暂时令指定加密上游不可达，再用新名称查询。预期是失败，而不是改问接入网 DNS；随后恢复网络。只看正常查询走 HTTPS，没有测到失败回落
- `hijack-dns = *:53` 只能接管进入隧道的相应 DNS 流量；应用自带 DoH/DoT 或没有进入 TUN 的查询要另查。节点的 `server-dns` 只解析节点地址

Loon 可以并发查询多个加密上游，配置多个时应接受同一查询交给这些服务。订阅规则不能替设备关闭回落，也不能替系统建立 VPN 的分域解析。[Loon DNS](https://nsloon.app/docs/DNS/) · [按域设置解析器](https://nsloon.app/docs/DNS/hostmap/)

## IP 规则为什么有的保留解析

`no-resolve` 限制的是 **IP 规则为了匹配而主动查询域名**，不决定 DNS 发给谁，也不代表所有域名都无需解析。

0110 让私网、组网地址和回环地址保留按名称访问的能力：未列出的内部名称解析到这些地址后，仍可按私网选路。链路本地、组播、文档与保留地址只处理已有目标 IP，使用 `no-resolve`。规则先进行域名阶段匹配，未命中才进入相应 IP 阶段；不是每条 IP 规则各查一次 DNS。[IP 匹配说明](https://nsloon.app/docs/Rule/ip_rule/#no-resolve)

明确不需要靠解析结果识别私网名称时，用 **0120 替代 0110**。0120 的 IP 规则全部带 `no-resolve`，管理名和网段由 0110 派生。代价是未知内网名称不能再靠这份私网 IP 表直连，可能继续到后续规则或 `FINAL`；要保留访问，就需在本机明确处理其名称、DNS 与路由。

8620 国内网段和 8630 GeoIP 用于域名未命中后的地址判断，因此允许解析。语音、媒体等只匹配已知目的地址的专项则使用 `no-resolve`。逐组结果由生成器写入维护状态的 `ip-matching`，合集沿用成员参数。

0110 的反查名称由同一份地址声明计算，不另外维护。它只决定这些名称的选路，不设置递归 DNS。[本地反查背景](https://www.rfc-editor.org/rfc/rfc6303.html)

## WebRTC：比较同一地址族的公网地址

在同一浏览器资料、同一网络中，先记录网页出口，再新建 WebRTC 测试会话。对预期走代理的连接，检查 IPv4 和 IPv6 公网候选中是否出现接入网地址。mDNS 隐藏了本地地址，不等于公网路径已经受控；不同地址族也不能直接互相比较。

没有得到公网候选、STUN 超时或被拒绝，记为未测到，不能算通过。随后试一次实际语音或会议，确认处理方式没有破坏正常 UDP。0230 只是已列公共 STUN 端点的可选拒绝表，不能覆盖全部 WebRTC；不以封掉所有 UDP 作为通用修复。

[0150 出口检测](../rules/loon/0150-ip-egress-checks.lsr)可分别测试 [IPv4](https://api.ipify.org)和 [IPv6](https://api6.ipify.org)，同时核对命中和最终节点。IPv6 超时只说明该路径未测通。DDNS 客户端若靠检测站更新家庭公网地址，相关查询不应误走代理。

## 内网和其他 VPN

只连接已有 VPN，先用域名和 IP 访问同一个授权资源，再开启 Loon 重做。**IP 可用、域名不可用先查 DNS；两者都不通先查路由。** `DIRECT` 不会替另一条 VPN 建立路由。

已知网段需要交给系统路由时，检查 `bypass-tun`；使用系统 HTTP 代理时还要检查 `skip-proxy`。私有名称与网段只保存在本机配置。Mac 上的 Tailscale、WireGuard 等先排除网段重叠，再测 MagicDNS 和实际资源；iPhone 的两个普通 VPN App 不能靠订阅规则同时接管隧道。[Tailscale 与其他 VPN](https://tailscale.com/docs/reference/faq/other-vpns)

## APNs 推送

选一个正常和一个常漏通知的 App，检查通知权限、专注模式，在同一 Wi-Fi 下锁屏，由另一设备触发同类通知并记到达时间。换出口后等待长连接重建。

先固定 APNs，只改问题 App 的业务出口；若恢复，检查其登录、推送令牌上报和后台取数。再固定 App，只改 APNs 的出口，对照 `*.push.apple.com`、TCP/5223 与备用 443，最后在蜂窝重复。没有相应系统连接时，先确认 Loon 是否接管了它。

APNs 接收连接不按 App 的国别分开，不能据此把整个 `17.0.0.0/8` 改成代理或直连，也无需为观察选路而解密推送。[Apple APNs 网络要求](https://support.apple.com/en-us/102266)

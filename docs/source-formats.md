# 怎样读取公开来源

先确认资料中的哪一部分能说明业务用途，再选择读取器。不要把“允许访问整个云平台”理解为“这些域名专属于当前产品”。下表中的配置片段放在产品条目的 `extract`、`projection` 或 `expand` 中；完整实例在 [catalog.json](../config/catalog.json)。

## 直接读取业务字段

| 资料 | 读取方式与关键条件 | 现有实例 |
|---|---|---|
| 官方服务 JSON | `service-domain-groups` 选择业务组；`json-service-urls` 用 `paths` 取服务器或下载字段，数组使用 `*`；`identity` 核对产品身份 | GitHub 开发平台 3010、GitHub Pages 托管 8130、Cargo 3080、PyPI 3060、npm 3040 |
| 页面内的公开服务配置 | `next-service-urls` 核对唯一的页面 JSON 与产品身份，再用 `paths` 读取业务 URL；`url-fields` 只在指定正文范围读取所列资源字段 | Disney+ 3830 读取生产 API、默认内容服务和图片；内部与预览配置不参与 |
| SDK 静态配置 | 按模块、类和字段解析默认端点；`c-function-url` 读取指定函数的字面 HTTPS；`qt-host-predicate` 读取 Qt 主机判断；`code-api-endpoints` 读取指定源码字段；`literal-object-urls` 从 JavaScript 语法树读取指定环境的完整 URL 对象 | Claude 1010、xAI 1040、Telegram 3310、Firebase 消息 4585、Disney 共用服务 8120 等 |
| 服务域名列与 CSP | `domain-column-table` 核对列头后读取指定列，`value-format: url` 从 HTTPS／WSS URL 取精确主机；`csp-origins` 按章节、指令和品牌取源 | Datadog 3140、Docker 3075 的完整用途表、Intercom 4360 |
| Go 客户端的主机用途分支 | `go-host-switch` 选择一个函数中直接返回指定用途的字面主机分支，只生成精确域名；忽略注释、字符串示例和其他用途，控制逻辑变化时停止采用 | Apple 账户 2090 跟随 GrandSlam 生产主机更新，补充企业网络表未列出的客户端入口 |
| 业务域名表 | 按章节、列头和用途选择 `host-table`、`purpose-domain-table`、`nested-purpose-domains` 等；IP 列单独处理 | Apple、Microsoft 产品 |
| 标签后面的主机列表 | `purpose-domain-lists`、`host-purpose-list` 按用途标签读取；嵌套子域必须有明确说明并符合域名关系 | Cursor 1100、Signal 3330、Slack 3370 |
| 请求示例和代码字段 | `purpose-url-table`、`labelled-url-pairs` 等只取指定用途的 HTTPS 或 WSS 主机，忽略普通链接和载荷 | API、支付与通讯入口 |
| Microsoft 端点行 | `endpoint-sets` 按服务区与端点 ID 选行。只有确认整行专用时才用 `all-hosts`；否则保留 `roots`、`exact` 筛选 | Outlook 4720、Teams 4730、Office 下载 4780 |
| 官方服务地址表 | `service-address-table` 选择章节与 IPv4／IPv6 列，只接收单个公网地址，生成 `/32`、`/128` 与 `no-resolve`；宽网段、缺列或地址族错误时停止更新 | Cloudflare 公共 DNS 0160，只取标准解析器，和 Families 分开 |
| 指定方向的地址章节 | `section-network-blocks` 只读所选标题下的 CIDR 代码字段，核对地址族与最宽掩码，生成 `no-resolve` | Claude 1010 只读官方入站地址；出站工具调用和已停用地址不混入客户端目的地址 |
| 组织持有的 ASN 集合 | `rdap-entity-autnums` 核对注册组织 ID 与名称，读取当前活动 ASN 列表；成员增减自动跟随，生成 `no-resolve`，不预填 ASN 编号 | Telegram 3310、Anthropic 1010；适用于已确认的产品网络运营者，不能据共享云厂商的登记推断租户用途 |
| 单个 ASN 注册记录 | `rdap-autnum` 核对指定 ASN、注册实体 ID 和组织名称；持有人不符时停止更新 | 只核对一个已知自治系统时使用，维护联系人不等于注册持有人 |
| 独立产品站 | `site-identity` 核对 canonical、品牌及可选的 Open Graph 字段；`scope: source-root` 只适用于已核实的单产品注册域 | 独立支付或产品站 |
| 同一业务的地区端点表 | `purpose-host-table` 可用 `purpose-prefixes` 选择同类用途、`value-format: domain` 读取主机列；`all-exact: true` 只生成精确主机 | Kiro 1530 跟随官方表中的模型服务地区，不收相邻的 AWS 共用登录与验证码 |
| 独立产品域名清单 | `domain-scope-list` 读取整份原生域名规则；`subdomains-as-hosts: true` 保留注册域后缀，将清单中具体服务器收窄为精确主机 | Bilibili 国际版 3880 使用业务专表，不使用混有中国站海外 CDN 的地理标签表 |
| 原生 geosite 产品清单 | `geosite-domain-list` 读取裸域名、`domain:` 与 `full:`，核对属性、子分类引用和共享范围的归属；不使用固定根域白名单代替整份来源 | Spotify 3910、Reddit 3380、Slack 3370、Discord 3320 |
| 官网资源元数据 | `site-resource-hosts` 先用 `identity` 核对站点，再从 `properties` 指定的 Open Graph 图片、音频或视频 URL 取精确主机 | 3880 的独立完整性检查核对官网实际引用的素材；不扫描页面全部链接、广告或脚本 |

例如 GitHub 开发平台读取网站、软件包和 Actions 域名，把 Pages 托管范围交给单独的 8130：

```json
{
  "source": "https://api.github.com/meta",
  "format": "service-domain-groups",
  "path": ["domains"],
  "groups": ["website", "packages", "actions"],
  "platform-domains": ["github.io", "githubusercontent.com"],
  "exclude-platforms": ["github.io"],
  "protect-from-reject": true
}
```

官方公司服务清单可以描述来源自身的注册域。`platform-domains` 另行声明已核实由该供应商提供的平台命名空间，须属于公共后缀表中的私有托管部分。GitHub 官方资料明确区分 Pages 网站托管和开发平台：8130 用 `only-platforms` 选择 Pages，3010 用 `exclude-platforms` 留下代码、原始内容和 Actions 等范围。两个组都要配套筛选前完整服务字段的 `source-inventories`；读取器先检查全部所选字段，再划分产品，新平台范围不能因不符合筛选条件而被忽略。相邻的 IP 字段不是这些域名字段的一部分。

Pages 的默认域名可供不同产品托管网站，因此 8130 放在全球平台共用层，具体产品的专用租户主机先匹配。Pages 的管理与产品介绍仍使用 GitHub 网站；自定义域名不能仅凭解析到 Pages 的 IP 就改归托管平台。

JSON、plist 和用途表格中选定的网络字段都须处理完整。混入无法归属的托管通配范围或共用主机时，停止更新；不能只保留其他有效值就算读取成功。新出现的专用主机仍按来源用途补入，不要求先写进根域白名单。

`protect-from-reject` 用于保护选中用途的明确主机，不放开整家共享平台。用途字段还要通过共享主机与产品归属检查。HTML 忽略脚本、样式、模板与隐藏内容；用途标签可以跨空排版容器，不能跨新说明或新标题。

`next-service-urls` 只解析 `__NEXT_DATA__` 的 JSON，不执行页面脚本。`url-fields` 的每项声明包含 `path` 和 `fields`：在指定对象或列表中查找这些用途字段，字段至少出现一次，出现的值都必须是有效 URL。图片等公开资源可显式设置 `allow-query: true`，结果仍只保留精确主机。选中字段指向共用平台、页面数据缺失或重复、类型及产品身份变化时，停止更新；同一用途范围必须有独立 `source-inventories` 核对。这类局部页面配置不能单独启用 `inventory-refresh`，原入口消失时也不能据此认定整个服务已经停用它。

`product-role-links` 从指定用途的链接取主机，公开跟踪参数不进入规则。相对链接按声明的来源 URL 补全，没有来源地址时不能猜测目标；HTTP、脚本动作和带凭据的链接仍不采用。子域保持精确匹配；链接指向共享平台时，不能因路径属于某个产品就认领整个主机。Google 4590 从官网的 News、Blog 和 Press resources 链接跟随资讯入口。

Netflix 3825 从[官方连接检查说明](https://help.netflix.com/en/node/14424)读取 FAST 测速网站，随用途说明中的名称更新；3820 继续处理播放、设备 API 和分发。独立的 `nested-purpose-domains` 清单核对官方要求可达的全部地址，分别检查它们的首条命中。清单新增未确认归属的主机、共享平台范围或 IP 时停止更新，不能因其他几项仍能识别就忽略新增项。FAST 属于 Netflix 配套测速，比较 Netflix 路径时应选同一出口。

已核实的首方网站发生跳转时，`site-identity.include-source-alias` 可以保留请求最先访问的注册域。它要求品牌与 Open Graph URL 一致，最终身份位于 `canonical-parents` 声明的官方命名空间；canonical 存在时还要与 Open Graph 一致。来源必须是 HTTPS 根入口，不能是业务子域、共享托管租户或带凭据、参数的 URL。EA 4160 用此方式识别 EA Sports 网站入口，不靠手写域名规则补跳转。

`purpose-domain-lists.select` 可用 `roots`、`exact` 从同一官方清单选出产品自有范围。完整清单仍由端点合同独立核对，筛选不能把未处理的新增项藏起来。OpenAI 1020 用这种方式区分自有服务与第三方共享依赖。

官方表已明确用途、且列出的是单个主机时，`host-table.select` 可结合 `role` 与 `all-exact: true` 跟随这些精确端点。2020 只选择 PCC 和 Apple Intelligence 扩展两种用途；官方增加第三方中继主机时可以自动补入，不必先把新名字写进白名单。相邻的 Siri、下载与 iCloud Private Relay 行不参加该选择，域名也不会扩大为整个 CDN 后缀。

## plist 和客户端配置

公开 plist 使用 `plist-service-fields`：

- `identity` 核对文档身份；`host-paths`、`url-paths` 选择业务字段
- 同类地区记录用 `records.paths`，字段用 `url-fields`、`url-patterns`；`required-fields` 指定不可缺少的用途
- 根对象就是记录时，路径写 `[[]]`。同前缀混有开关或计时，使用 `typed-url-patterns`；必需字段变成开关或无效 URL 时仍拒绝更新
- 外层包装有内层二进制数据时，`data-path` 只解开指定的一份，再核对内层身份与字段

商店 2130、音乐 2230 和视频 2040 读取同一公开配置的不同 API 字段。2130 的 `records.allow-query` 允许搜索字段带公开查询参数，提取结果只含主机名。消息身份 2180 使用 `expand.method: public-plist-bag`，只允许数字 `ix` 参数。定位 2170 使用 `ios-client-config`，从公开软件目录计算版本、机型组合，再读取各组合的业务字段，最多读取 `max-documents` 份。

普通下载器只接受无凭据、无查询参数的 HTTPS 来源。上述配置模式单独限制允许的公开参数，不接受令牌、设备标识或额外参数。读取器不发起登录、身份注册或消息操作。任一必需文档损坏或读取不完整，都不能用部分结果替代成品。

这类配置可能只是部分地区或版本的覆盖项，不能作为完整清单启用撤回。历史保留仅限已发布且仍符合当前来源合同的精确主机，见[维护方式](maintenance.md#从来源消失后怎样处理)。

## 跟随目录、地区和产品页面

| 场景 | 声明方法 | 必须检查 |
|---|---|---|
| 官方 API 目录 | `expand` 按产品标题及文档路径模板取文档；`versions: published` 读取仍公开的全部版本，默认 `preferred` 保留既有用法 | 产品身份、版本和服务器字段对应；一份文档不能归两个产品；缺文档时不发布部分结果 |
| 地区主机模板 | `host-templates` 结合用途表、占位字段、端口与同一品牌的地区注册域清单 | 模板、品牌标签和注册域一致；共享租户不能当地区根域。Google 登录 4510 是实例 |
| JSON 中的文章正文 | `json-document` 用 `body-path` 选正文、`identity` 核对文章，再嵌套现成读取器 | 外层来源身份保持一致。JetBrains 1230、3100、6260 按地区注释与用途分开 |
| 前端页面的专用资源 | `next-page` 跟随页面数据明确声明的专用路由文件，再按用途读取字段和请求示例 | 页面身份、资源厂商范围与用途标签都匹配；不执行脚本，不扫描全部资源。Liblib 6110 是实例 |
| 页面当前使用的 SDK | `next-sdk` 核对公开页面中的产品和环境标记，跟随指定字段的 SDK URL，再用 `literal-object-urls` 读取生产配置 | 脚本须属于已确认的资源命名空间；环境对象须唯一、字段齐全且都是静态 URL。语法、用途字段或类型变化时停止更新。8120 跟随 MyDisney 登录组件 |
| 服务 CNAME 的独立租户 | `cname-tenants` 声明服务父域与 Public Suffix List 私有后缀 | 只有原服务链实际指向的完整租户名可生成精确规则；其他租户、子域和共享父域不能顺带采用 |

API 目录中仍公开的旧版本也参加完整清单的并集。页面中的一个请求示例不代表全部服务，不能套用完整清单的撤回语义。

JavaScript SDK 使用 Tree-sitter 解析完整语法树，区分真正的对象、注释、字符串、模板和正则表达式。`literal-object-urls` 只接受指定环境的一个字面对象，`fields` 必须与其 URL 用途字段完全一致；计算属性、函数调用、展开项、重复字段或未知新增字段都会停止更新。SDK 版本与主机由产品页面跟随，不固定生成文件名。8120 的生产配置使用 `prod` 对象；页面选择的脚本主机即使含有 `qa` 字样，也不能据此删掉实际载入入口。

已核实的账户网站缺少 canonical 时，`site-identity.scope: source-host` 可用唯一、精确匹配的品牌元数据识别声明的来源主机；品牌字段可选 `og:site_name` 或 `og:title`。如果页面提供 canonical 或 Open Graph URL，它们必须与该主机一致。结果只是一条精确主机，不扩大为父域；MyDisney 账户管理页使用这种方式。

## 什么时候启用端点轮换

确认来源是完整服务清单后才设 `inventory-refresh`，默认 `inventory-retention: service`。多份来源先取并集，主机从所有来源消失后再隔轮确认。`managed` 产品把完整官方清单放在 `official-inputs`，社区缺项不能启动仍有官方依据主机的撤回计时。

包的发布文件使用 `inventory-retention: published-artifacts`，并用 `revision-path` 选择版本字段；要求单份版本元数据。它保存旧版本文件主机，不把“最新版没再出现”理解为停用。

同一用途表同时列出跨产品主机时，`check-sharing` 从该份提取声明计算共用关系，并核对后续承接。拆分归属时使用本轮完整范围证据，不添加域名迁移豁免。

用途明确的独立产品、地区来源或后置厂商共用表，可以用 `projection.all-domains: true` 跟随已核对来源的全部域名，不能同时填写 `roots`、`exact`，并且必须在 `source-inventories` 声明同一来源的完整归属检查。Apple 2370 使用此方式，细分仍先匹配。整份品牌顶级域、用途未核实的第三方主机等排除须写明原因，不能把“来源里有”当作业务归属的充分依据。

`projection.exact-from-extract: true` 用本轮用途字段生成精确筛选，不再另列同一批主机名。社区表把服务器写成后缀规则、官方用途表只证明这个主机时，结果保持 `DOMAIN`，不会扩大到它的子域。固定 `roots` 仍按声明处理；共享主机保护继续生效。Kiro 的地区 API，以及 OpenAI、Docker 部分已由用途资料证明的主机采用这种方式。

`domain-scope-list` 不把主机扩大为注册域。例如 `api.global.example.com` 在主机模式下保持精确匹配，`example.com` 若原本是后缀规则则保持不变。出现 IP、ASN、参数、公共后缀或共享托管后缀时停止读取；主机模式也不接受来源新增的通配符，避免把格式变化当作普通补全。源中已有的精确规则不会被扩大。

这类完整清单必须配套 `source-inventories`，范围选择要与生成声明一致。生成器既检查整份来源是否由正确产品承接，也检查第一条实际命中；正文里有一条父域，不能代替共享主机和其他产品的归属判断。

确认来源描述的是完整产品范围后，设置 `require-domain-closure: true`。检查读取整份来源，发生在筛选前：未选范围也必须由正确产品完整承接，或有明确的共享、排除依据。落到补充、Reject 或无关产品都不能算通过；其他产品的承接须在独立来源清单中声明并通过首条命中检查。宽泛的地区合集和混有历史品牌的公司表仍按参考资料核对，不能为了消除待查数量开启整表收录。

读取含其他客户端语法的资料时，`projection.domain-lines-only` 和 `source-inventories.domain-lines-only` 选择三种域名规则。`projection-coverage.other-rule-types` 另外列出 IPv4、IPv6、ASN、进程等类型及数量；已认可类型的地址或 ASN 格式错误也会停止更新。采用 IP 还要核对目的地址用途，采用 ASN 要核对运营者，进程规则要核对系统和客户端，类型统计不代替这些判断

`source-inventories.recipe` 可以复用读取器核对结构化的完整来源。Google 地区域名使用 `brand-domain-list`，按官方注册域清单逐项检查首条命中。完整性检查失败会阻止发布，读取失败也不能按零条处理。

Telegram 3310 同时读取官方 CIDR、官方列明的域名范围和注册组织的当前 ASN 集合。域名范围新增项会进入细分表及通讯合集；官方漏洞奖励范围并非全部客户端端点清单，因此不据此撤回其他仍有来源的域名。组织记录出现新 ASN 时自动生成，不再维护一串 ASN 编号；组织身份不符、列表截断或成员损坏时保留已发布版本。ASN 的实际匹配仍依赖客户端的 ASN 数据

评论工具从官方产品链接读取；Telegraph 内容主机从官方客户端的指定 URL 判断函数读取。`qt-host-predicate` 只接受规范化主机后的精确比较并集，生成 `DOMAIN`；判断改成路径、动态值或其他条件时停止更新。它不扫描同一文件的通用链接白名单，因此不会把其中的 Fragment 等外部服务认作消息端点。TON 网站 3680、TON Center API 3690 和 Fragment 3700 按各自官方站点身份维护，归入加密资产分类。

## 原生 geosite 清单怎样分配

`geosite-domain-list` 读取[上游定义的规则语法](https://github.com/v2fly/domain-list-community/blob/master/README.md)，不把评论中的网站名当成规则。裸域名和 `domain:` 保留后缀含义，`full:` 保留精确匹配；可用 `subdomains-as-hosts` 将具体服务器进一步收窄。属性须在 `attributes` 说明用途，不能把 `@ads` 理解为绕过本仓的广告策略。当前读取器不自动执行带属性的 `include:` 筛选，遇到这种输入会停止更新。

`include:child` 表示引用另一个分类，不代表这些域名都属于当前产品。用 `delegated-includes` 指明子分类对应的产品，目标产品须读取同一目录中的实际子文件，并有独立完整性检查。缺少目标来源、出现未处理的引用或循环引用时，不发布部分结果。关键词和正则只有在 `omit-types` 写明原因后才能省略；未识别的类型不能靠这项声明跳过。

上游用注释明确标出产品时，`include-comment-blocks` 可以读取该注释紧邻的域名块，遇到空行或新注释就结束。块内新增域名会跟随产品更新，不必再维护根域白名单；标题缺失、重复或格式变化时停止更新。懒人听书 6956、爱听卓乐 6958 使用这种方式，同时核对腾讯音乐官网的产品链接。选择产品块还必须配套筛选前整份来源的归属检查，不能只证明选出的几行有去处。

腾讯音乐集团表 6965 读取完整集团清单和官网产品目录，扣除前面已经识别的具体产品。酷狗 6950 按完整客户端与关联服务范围维护，包含音乐、直播及专用素材；共用域无法按音频和直播内容拆开，因此不把它描述成纯音乐资源表。酷我、喜马拉雅和全民 K 歌仍保留各自细分，并进入国内影音合集。

同一份清单混入独立平台时，`delegated-scopes` 说明范围、目标产品和用途来源。生成器不会只从当前组删掉这一项：完整性检查还会核对目标组是否承接了整个范围，以及实际第一条命中是否正确。Discord 的 `discordsays.com` 从官方说明确认是 Activities 第三方应用代理，因此由 8110 处理，3320 继续处理通讯、语音与自营入口。

公共后缀表的 PRIVATE 部分描述子域之间的隔离边界，不能单独证明业务属于谁。[PSL 提交规则](https://publicsuffix.org/submit/)说明，这些域名可以由向不同使用者分配子域的域名所有者提交。`product-domain-statements.domain-scope: private-platform` 只在明确的平台用途说明中使用，要求读取结果确实是 PRIVATE 命名空间；不会把普通注册域或公共注册后缀扩大成平台规则。来源写在列表项里时，显式使用 `include-list-items`。

注释也不是停用证明。`excluded-comment-blocks` 只作用于指定注释紧邻的候选块，遇到空行或新注释即结束；不能让一个 `Unused` 注释误伤后面的上传主机。这项选择只控制本来源是否新增候选，其他来源仍支持的已发布入口继续保留，丢失覆盖检查不会因此取消。读取策略、省略类型、候选块和共享范围分配都记录在 `source-inventories` 状态中。

## 公开安全资产怎样按产品分配

`security-program-domains` 读取公开 HackerOne 项目的结构化资产。先用项目 handle、名称和官方项目地址核对身份，再按资产类型、产品标签或明确用途读取主机；不扫描说明中的全部链接。资料镜像来自 [bounty-targets-data](https://github.com/arkadiyt/bounty-targets-data)，原项目入口由 [Spotify 官方页面](https://www.spotify.com/bounty)确认。

每项产品有两道检查：自己的用途清单，以及筛选前的完整项目。完整项目必须处理每条测试内资产。源码、安装程序、App 包名和没有主机的栏目保留类型与处理依据；新增产品或未确认类型不能被筛选条件藏起来。项目身份变化、重复资产、JSON 损坏、用途丢失或共享平台越界时，保留上一版。

维护状态还保存完整项目中每项资产的标识、类型、测试范围和处理方式，每次更新与上一版比较。已有网络目标消失或同一资产改变类型时，先停止更新；其他来源仍覆盖该域名，也不能代替这项核对。记录按项目身份关联，改清单名称或交换两项资产的类型不会绕过检查。安全测试范围变化后，原网络入口仍须有有效来源承接；源码等非网络栏目正常撤下，不会被当成服务端点丢失。

主机来自有明确用途的资产字段或域名代码列表。Markdown 由 CommonMark 解析器读取，合法的文件末尾开放代码围栏可以接受；否定列表、未知代码格式和其他产品的地址不能混进正面清单。通配范围保留原来的通配语义，指定共享租户只生成精确主机。

Spotify 音乐、播客和相关网站继续使用 3910；Sonantic 语音 AI 使用 1185，Backstage 开发者门户使用 3240，Spotify 广告 API 与分析使用 3250，WhoSampled 音乐资料库使用 3915。它们分别进入所属合集。广告分析的分类不等于必须放行统计请求；本次读取不增加整组免拦截设置。

安全测试范围不是完整网络清单，也不单独证明所有权。Backstage 已捐赠 CNCF，不能因它仍列在 Spotify 安全项目中就归入 Spotify 音乐；App 未参加漏洞奖励，也不代表其流量可以忽略。此类来源不启用完整服务清单的自动撤回，已有入口仍需结合其他来源核对。

## 如何证明读取器真的能更新

测试至少包含来源新增一个未预填的主机、遗漏必需字段、共享主机反例，以及连续两轮生成。涉及目录时再增加版本、地区或机型；涉及撤回时验证多来源并集、故障与恢复、重新出现和观察间隔。正文合并成父域后，来源里的明确主机仍应各有首条命中检查。

局域网反查名称属于计算，不是发现。`reverse-dns: true` 从同一份地址声明生成准确的反向区域，要求 `compiled`、`ip-match: per-rule`，不改变 IP 解析用途；测试网段边缘和相邻地址即可。

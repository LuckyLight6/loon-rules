# 怎样读取公开来源

先确认资料中的哪一部分能说明业务用途，再选择读取器。不要把“允许访问整个云平台”理解为“这些域名专属于当前产品”。下表中的配置片段放在产品条目的 `extract`、`projection` 或 `expand` 中；完整实例在 [catalog.json](../config/catalog.json)。

## 直接读取业务字段

| 资料 | 读取方式与关键条件 | 现有实例 |
|---|---|---|
| 官方服务 JSON | `service-domain-groups` 选择业务组；`json-service-urls` 用 `paths` 取服务器或下载字段，数组使用 `*`；`identity` 核对产品身份 | GitHub 3000、Cargo 3070、PyPI 3050、npm 3030 |
| SDK 静态配置 | 按模块、类和字段解析默认端点；不运行下载的源码 | Claude 1010、xAI 1040 等 |
| Go 客户端的主机用途分支 | `go-host-switch` 选择一个函数中直接返回指定用途的字面主机分支，只生成精确域名；忽略注释、字符串示例和其他用途，控制逻辑变化时停止采用 | Apple 账户 2010 跟随 GrandSlam 生产主机更新，补充企业网络表未列出的客户端入口 |
| 业务域名表 | 按章节、列头和用途选择 `host-table`、`purpose-domain-table`、`nested-purpose-domains` 等；IP 列单独处理 | Apple、Microsoft 产品 |
| 标签后面的主机列表 | `purpose-domain-lists`、`host-purpose-list` 按用途标签读取；嵌套子域必须有明确说明并符合域名关系 | Cursor 1100、Signal 3320、Slack 3360 |
| 请求示例和代码字段 | `purpose-url-table`、`labelled-url-pairs` 等只取指定用途的 HTTPS 或 WSS 主机，忽略普通链接和载荷 | API、支付与通讯入口 |
| Microsoft 端点行 | `endpoint-sets` 按服务区与端点 ID 选行。只有确认整行专用时才用 `all-hosts`；否则保留 `roots`、`exact` 筛选 | Outlook 4740、Teams 4750、Office 下载 4800 |
| 独立产品站 | `site-identity` 核对 canonical、品牌及可选的 Open Graph 字段；`scope: source-root` 只适用于已核实的单产品注册域 | 独立支付或产品站 |

例如 GitHub 只读取网站、软件包和 Actions 域名，不读取相邻的 IP 字段：

```json
{
  "source": "https://api.github.com/meta",
  "format": "service-domain-groups",
  "path": ["domains"],
  "groups": ["website", "packages", "actions"],
  "protect-from-reject": true
}
```

`protect-from-reject` 用于保护选中用途的明确主机，不放开整家共享平台。所有读取器使用相同的共享主机边界。HTML 忽略脚本、样式、模板与隐藏内容；用途标签可以跨空排版容器，不能跨新说明或新标题。

官方表已明确用途、且列出的是单个主机时，`host-table.select` 可结合 `role` 与 `all-exact: true` 跟随这些精确端点。1230 只选择 PCC 和 Apple Intelligence 扩展两种用途；官方增加第三方中继主机时可以自动补入，不必先把新名字写进白名单。相邻的 Siri、下载与 iCloud Private Relay 行不参加该选择，域名也不会扩大为整个 CDN 后缀。

## plist 和客户端配置

公开 plist 使用 `plist-service-fields`：

- `identity` 核对文档身份；`host-paths`、`url-paths` 选择业务字段
- 同类地区记录用 `records.paths`，字段用 `url-fields`、`url-patterns`；`required-fields` 指定不可缺少的用途
- 根对象就是记录时，路径写 `[[]]`。同前缀混有开关或计时，使用 `typed-url-patterns`；必需字段变成开关或无效 URL 时仍拒绝更新
- 外层包装有内层二进制数据时，`data-path` 只解开指定的一份，再核对内层身份与字段

商店 2050、音乐 2170 和视频 2190 读取同一公开配置的不同 API 字段。消息身份 2110 使用 `expand.method: public-plist-bag`，只允许数字 `ix` 参数。定位 2100 使用 `ios-client-config`，从公开软件目录计算版本、机型组合，再读取各组合的业务字段；`max-documents` 限制数量。

普通下载器只接受无凭据、无查询参数的 HTTPS 来源。上述配置模式单独限制允许的公开参数，不接受令牌、设备标识或额外参数。读取器不发起登录、身份注册或消息操作。任一必需文档损坏或读取不完整，都不能用部分结果替代成品。

这类配置可能只是部分地区或版本的覆盖项，不能作为完整清单启用撤回。历史保留仅限已发布且仍符合当前来源合同的精确主机，见[维护方式](maintenance.md#从来源消失后怎样处理)。

## 跟随目录、地区和产品页面

| 场景 | 声明方法 | 必须检查 |
|---|---|---|
| 官方 API 目录 | `expand` 按产品标题及文档路径模板取文档；`versions: published` 读取仍公开的全部版本，默认 `preferred` 保留既有用法 | 产品身份、版本和服务器字段对应；一份文档不能归两个产品；缺文档时不发布部分结果 |
| 地区主机模板 | `host-templates` 结合用途表、占位字段、端口与同一品牌的地区注册域清单 | 模板、品牌标签和注册域一致；共享租户不能当地区根域。Google 登录 4520 是实例 |
| JSON 中的文章正文 | `json-document` 用 `body-path` 选正文、`identity` 核对文章，再嵌套现成读取器 | 外层来源身份保持一致。JetBrains 1240、3090、5160 按地区注释与用途分开 |
| 前端页面的专用资源 | `next-page` 跟随页面数据明确声明的专用路由文件，再按用途读取字段和请求示例 | 页面身份、资源厂商范围与用途标签都匹配；不执行脚本，不扫描全部资源。Liblib 5110 是实例 |
| 服务 CNAME 的独立租户 | `cname-tenants` 声明服务父域与 Public Suffix List 私有后缀 | 只有原服务链实际指向的完整租户名可生成精确规则；其他租户、子域和共享父域不能顺带采用 |

API 目录中仍公开的旧版本也参加完整清单的并集。页面中的一个请求示例不代表全部服务，不能套用完整清单的撤回语义。

## 什么时候启用端点轮换

确认来源是完整服务清单后才设 `inventory-refresh`，默认 `inventory-retention: service`。多份来源先取并集，主机从所有来源消失后再隔轮确认。`managed` 产品把完整官方清单放在 `official-inputs`，社区缺项不能启动仍有官方依据主机的撤回计时。

包的发布文件使用 `inventory-retention: published-artifacts`，并用 `revision-path` 选择版本字段；要求单份版本元数据。它保存旧版本文件主机，不把“最新版没再出现”理解为停用。

同一用途表同时列出跨产品主机时，`check-sharing` 从该份提取声明计算共用关系，并核对后续承接。拆分归属时使用本轮完整范围证据，不添加域名迁移豁免。

## 如何证明读取器真的能更新

测试至少包含来源新增一个未预填的主机、遗漏必需字段、共享主机反例，以及连续两轮生成。涉及目录时再增加版本、地区或机型；涉及撤回时验证多来源并集、故障与恢复、重新出现和观察间隔。正文合并成父域后，来源里的明确主机仍应各有首条命中检查。

局域网反查名称属于计算，不是发现。`reverse-dns: true` 从同一份地址声明生成准确的反向区域，要求 `compiled`、`ip-match: per-rule`，不改变 IP 解析用途；测试网段边缘和相邻地址即可。

# 参与开发

修错分时，先确认错误来自哪里：来源缺少入口、分类条件不对，还是更早的规则抢先命中。修改声明或生成逻辑，再生成订阅；直接改 `rules/` 中的成品，下次更新会被覆盖。

代码和规则在 `main` 分支维护。`readme` 是 GitHub 首页的默认展示分支，只保留空 README 和定时更新入口。

## 在本地检查和生成

需要 Python 3.10 或更新版本，联网更新还需要 `curl`。生成器没有第三方运行依赖；开发时在虚拟环境安装本仓包，源码布局使用 [`src/`](https://packaging.python.org/en/latest/discussions/src-layout-vs-flat-layout/)：

```sh
python3 -m venv .venv
. .venv/bin/activate
python3 -m pip install --editable .
```

随后在仓库根目录运行：

```sh
python3 -B -m unittest discover -s checks
python3 -B -m loon_rules --verify-files
python3 -B scoped_dns.py --check
python3 -B -m loon_rules --check-exports
```

改过分类、来源或目录说明后，依次生成并检查：

```sh
python3 -B -m loon_rules --render-index
python3 -B -m loon_rules --refresh
python3 -B scoped_dns.py
python3 -B scoped_dns.py --check
python3 -B -m loon_rules --verify-files
python3 -B -m loon_rules --export
python3 -B -m loon_rules --check-exports
```

`--refresh` 联网读取来源并写入通过检查的结果；`--check` 执行来源和生成检查，不写文件；`--verify-files` 只检查本地文件。安装后也可运行 `loon-rules --verify-files`；普通安装从当前目录向上查找规则仓库，在仓库内或其子目录运行即可。源码方式始终处理命令所在的仓库，原有 `python3 -B maintain.py ...` 和 `python3 -B scoped_dns.py ...` 无需安装包也可直接运行。`--adopt-ad-scope` 用于维护者审阅常规或扩展广告的大幅变更后，一次性采用交叉核对范围，不在定时任务中使用。

## 工程结构

| 位置 | 内容 |
|---|---|
| `config/catalog.json` | 厂商、产品、地区、用途、来源、编号、合集及执行顺序 |
| `config/scope-policy.json` | 共享基础设施和不能整段归给单个产品的范围 |
| `config/endpoint-contracts.json` | 独立核对的官方端点、业务用途和预期归属 |
| `src/loon_rules/sources/` | 下载公开资料、按用途提取、展开版本与地区文档、核对来源依据 |
| `src/loon_rules/exports/` | 从同一份已验证规则生成客户端格式，检查不能等价转换的类型、参数与通配符 |
| `src/loon_rules/generation/` | 编译规则、处理归属、补充与合集、验证候选、生成文件和报告 |
| `src/loon_rules/rules.py`、`domains.py`、`matching.py` | 规则语法、域名范围和首条匹配；IPv4、IPv6 与 IP 参数检查 |
| `src/loon_rules/catalog.py`、`policy.py` | 分类声明、生成字段和共同边界 |
| `src/loon_rules/cli.py`、`src/loon_rules/plugins/` | 命令入口与分域 DNS 插件生成 |
| `checks/` | 来源解析、连续更新、错误输入、范围归属与优先级测试 |
| `rules/`、`dist/`、`plugins/` | Loon 原规则、多客户端成品与索引、可选插件 |
| `data/` | 公共后缀表及下一轮更新必需的维护状态 |
| `docs/` | 使用、选路、测试和开发说明 |
| `build/` | 本轮检查输出，已忽略，不提交 |

根目录的 `maintain.py`、`scoped_dns.py` 保留命令兼容，具体实现均在 `src/loon_rules/`。`source-components` 是生成器内部的来源比对输入，不带订阅编号，不生成额外 `.lsr`；它们的已核对正文和时间保存在维护状态中。

`scoped-dns.routes` 为每个服务范围声明 `resolver`、`provider` 和 `groups`，可分别更换加密解析器；旧的单上游声明仍可使用。不同上游的域名范围相交时生成失败，避免同一名称被两套设置接管。它只生成 Host 映射，设备上的 DoH 出口和回落另行验证。

## 新增或调整产品

在 `config/catalog.json` 找到同类条目，明确五件事：

1. **产品与用途。** 区分国内版、国际版和共用服务；公司注册地、网页语言与 IP 所有者都不能直接决定出口
2. **来源与许可。** 在 `sources` 列出公开资料，读取明确的字段、业务表格或 SDK 默认端点。镜像和共同上游使用同一个来源家族
3. **生成方式。** `compiled` 从用途资料和范围声明生成；`managed` 以上一版已核对的内容为基线，按声明接纳或撤回变化；`view` 合并成员
4. **位置与选择。** 填写唯一 `priority`、业务 `section`、子类 `routing-group` 和小写连字符名称。`selection` 区分细分、可选或替代表；合集按 `member-selection` 或明确成员生成
5. **验证样本。** 正例包括登录、API、文件和主要业务；反例包括共享云、相似名称与另一地区版本。IP 规则须说明是否为了匹配而解析，并检查完整网段

已确认服务使用自有网络时，ASN 集合可以用 `rdap-entity-autnums` 跟随注册组织，不逐个列 ASN；组织 ID 与名称保留为身份依据。官方表按用途取主机后，再用完整 URL 列做独立归属检查，避免新用途落在已有筛选之外。进程条件另核对客户端能力，不因上游有一行进程名就加入手机通用规则

`priority-width: 4` 统一生成四位编号，当前各组初始按 10 递增，例如 2090、2100。新增组先用相邻空号，例如 2095；不要求以后新增的编号也必须是 10 的倍数。编号同时用于文件地址，确定后不要只为整理外观反复改名。旧格式调用未声明位数时仍按三位处理。

`routing-bands` 按业务与地区安排大类，内部 `groups` 声明子类起始编号、标题、分区和允许的策略含义。每份规则填写唯一 `routing-group`，编号必须落在该子类区间；例如短视频与直播不能填进音乐区间。目录标题由这些声明生成，新产品加入所属子类，不再追加“更多产品”等临时分段。运行 `--render-index` 同步目录与生成字段

`service-directory` 记录厂商、产品和对应的细分规则，生成 `docs/services.md`。每份非合集订阅只能归一家厂商，或明确列为网络、隐私、补充等公共用途。同一厂商的几个产品可以引用同一份共用表，不重复生成正文；没有可靠用途来源时不要为目录凑出独立规则。`docs/rules.md` 仍是唯一的订阅执行顺序。

## 新域名如何自动进入

优先用 `extract` 按官方用途取值，或用 `expand` 跟随官方目录、公开客户端配置与地区模板。超出已有范围的新根域，需要明确用途依据：官方输入的 `authority` 必须配套提取 `recipe`；普通候选至少需要两个不同 `family` 支持。官方只证明一个主机时，不能扩成整个父域。

来源失败时，已采用范围及其必需入口保护继续保留，不累计撤回时间。完整服务清单、发布文件和局部配置的撤回条件不同，见[维护方式](maintenance.md)。输入格式与现成实例见[来源读取说明](source-formats.md)。

同一来源用于拆分产品时，原范围须被唯一的新产品完整承接，不能只覆盖根域或交给兜底。生成器根据本轮筛选结果记录迁移，不为个别域名加永久豁免。公司共享登录可以由前面的账号规则处理，后面的产品父域识别其他请求；仍须检查完整范围和实际首条命中。

合集可以用 `member-selection.groups` 跟随所属子类的全部细分成员；新增产品同时进入细分清单和对应合集。

`source-inventories` 是发布条件，不只是统计。新增范围未归属、被错误产品抢先匹配或完整清单读取失败时，生成器保留上一版。选择整份公司域名来源时，必须配套这项检查；不能靠扩大父域让用例通过。

完整产品投影另设 `require-domain-closure: true`，把筛选前的全部范围纳入验收。其他产品承接时，须符合 `source-inventories` 的用途声明；补充和 Reject 不代替产品归属。参考表与完整产品清单的区别取决于原资料的用途，不取决于条数。地区标签可能描述服务器位置，不能直接解释为产品的国内版或国际版。

只有确实不共用域名范围的产品才放进 `exclusive-domains`。已确认的专用主机位于另一个服务的共用父域下时，保留窄规则在前、共用父域在后，并检查两边正例与反例；不要删掉有效父域来消除包含关系。所有细分和合法合集组合仍要通过首条命中、完全重复与整条遮盖检查。

用途提取已经列出精确主机时，使用 `projection.exact-from-extract` 代替重复的 `exact` 名单。它只从本轮提取结果取精确主机，保留上游后缀规则的收窄记录；不从已发布文件、固定 `include` 或其他产品借主机。所需用途字段消失或只剩共享入口时，不生成假完整的筛选结果。

从共用表拆出用途时，可在新产品声明 `separates`，列出原表。两者必须在同一业务分区，或在厂商目录中属于同一厂商，并有共同公开来源；只有新表完整接住旧范围，生成器才接受归属变化。合并不同来源时，`merge-domains.prefer` 只能引用已经列在 `include` 的输入，用于明确的来源优先权；不能把域名逐个写进代码来绕过冲突。

## 怎样写有效的测试

让测试改变来源中的主机、版本或用途，再核对规则、合集和首条命中都跟着变化。把新名字预先写进固定声明，只证明重新生成，不能证明发现新端点。

对更新逻辑还要覆盖连续两轮生成、来源故障与恢复、明确主机被父域合并、共享平台反例以及撤回条件。解析器测试检查取值，生成测试检查变化能否落到成品，组合检查按实际顺序找第一条命中。匹配索引只复用本轮不再变动的候选，不跨轮缓存规则。

提交来源声明、代码、测试和相关成品；`data/maintenance-state.json` 中被下一轮使用的依据也要同步。不要提交 `build/`、抓取原文、工作日志或设备记录。DNS、WebRTC、推送、播放和长连接需要设备测试，不能以规则测试通过代替。[设备测试](network-testing.md)

合法合集选择按共同成员互斥。组合检查只枚举能影响当前域名、IP 或重复规则的选择，其余选择不改变结果；所有局部合法选择都能扩展成完整合法选择，因此覆盖全部配置，不做随机抽样。完整组合数按互斥关系精确计算；同时检查每条域名范围与相交 IP 在任意合法选择中是否会被提前覆盖

## 检查其他客户端格式

`--export` 先验证本地规则，再生成 `dist/`；`--check-exports` 重新计算成品，发现缺失、过时或多余的生成文件就失败。来源更新仍先经过原有分类、完整性和顺序检查，导出器不重新决定业务归属。不能等价转换的整组记录在 `dist/manifest.json`，不按客户端另维护删减版名单

有官方命令行程序时，可以逐份检查原生格式。程序路径由维护者提供，测试放在临时目录，不启用 TUN 或改动系统代理：

```sh
python3 -B checks/native_formats.py --mihomo /path/to/mihomo --sing-box /path/to/sing-box --v2ray /path/to/v2ray
```

CI 从官方发布下载固定版本到临时目录，检查 Mihomo Classical provider、sing-box source 编译和 V2Ray 配置片段；不把二进制程序或本机检查记录提交到仓库。使用方式和不能等价转换的范围见[客户端说明](clients.md)

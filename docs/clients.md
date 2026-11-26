# 在不同客户端使用同一套规则

先按[规则清单](rules.md)选产品或合集，再到下表进入对应代理应用的目录。全部订阅统一在 `rules/<代理应用>/`，共用来源、分类、编号和更新任务。订阅只提供匹配条件，出口、节点、DNS 和规则顺序仍由客户端配置决定

| 客户端 | 格式与下载目录 | 本版范围 |
|---|---|---|
| Loon | [`.lsr`](../rules/loon/README.md) | 完整保留现有语法与逐条 IP 参数 |
| Surge | [`.list`](../rules/surge/README.md) | 直接使用无策略规则集，无需再维护一份文本 |
| Mihomo | [Classical YAML](../rules/mihomo/README.md) | 保留域名、IPv4、IPv6、ASN、GeoIP 和 `no-resolve`；通配符转为等价正则 |
| Stash | [Classical YAML](../rules/stash/README.md) | 使用与 Mihomo 相同的转换结果，实际文件位于 Stash 目录 |
| Egern | [原生 YAML](../rules/egern/README.md) | 使用原生集合字段；混合 IP 解析用途分 OR 分支表达 |
| Shadowrocket | [兼容文本](../rules/shadowrocket/README.md) | 输出兼容规则集；尚未在 Shadowrocket App 实测 |
| Surfboard | [兼容文本](../rules/surfboard/README.md) | 不输出含 `IP-ASN` 的组；普通通配符需要支持该类型的版本 |
| Quantumult X | [原生 filter](../rules/quantumult-x/README.md) | 通过 `force-policy` 绑定出口；含逐条 `no-resolve` 的组不转换 |
| sing-box | [原生 source JSON](../rules/sing-box/README.md) | 只输出能够完整表达的域名组，不从混合组删去 IP、ASN 或 GeoIP |
| V2Ray | [JSON 路由片段](../rules/v2ray/README.md) | 只输出能够完整表达的域名组；核心不直接订阅 HTTP 规则集，需合并路由配置 |

旧的平铺规则和 `dist/` 下载地址已经停用，已有配置需要换成下列应用目录的地址。

每个下载目录逐项列出“订阅”或无法转换的原因。[机器可读清单](../rules/manifest.json)同时记录原文件、更新时间、原规则数、转换后规则数和兼容状态。JSON 文件不能带规则头注释，元数据放在这份清单中

Loon 使用 `.lsr`，Surge 使用正文相同的 `.list`；两者自动同步。Mihomo / Stash 使用同一份转换结果，分别在自己的目录提供文件；Shadowrocket / Surfboard 也按各自兼容范围分别输出。各应用都从同一批已校验规则生成。`-all` 仍由同一批细分成员生成，合集与成员二选一

## Loon、Surge、Shadowrocket 和 Surfboard

Loon 在 `[Remote Rule]` 引用原地址，并绑定现有策略：

```ini
[Remote Rule]
https://raw.githubusercontent.com/LuckyLight6/loon-rules/main/rules/loon/1030-gemini-connections.lsr, policy=PROXY, tag=1030-gemini-connections, enabled=true
```

Surge 在 `[Rule]` 使用同一份无策略规则集：

```ini
[Rule]
RULE-SET,https://raw.githubusercontent.com/LuckyLight6/loon-rules/main/rules/surge/1030-gemini-connections.list,PROXY
```

Shadowrocket 使用本应用目录中的兼容文本：

```ini
[Rule]
RULE-SET,https://raw.githubusercontent.com/LuckyLight6/loon-rules/main/rules/shadowrocket/1030-gemini-connections.list,PROXY
```

Surfboard 使用自己的目录：

```ini
[Rule]
RULE-SET,https://raw.githubusercontent.com/LuckyLight6/loon-rules/main/rules/surfboard/1030-gemini-connections.list,PROXY
```

把 `PROXY` 换成自己的策略名，放在更宽泛的规则和兜底之前。Surfboard 的目录会排除含 ASN 的组，不要从 Shadowrocket 目录绕过这个限制

依据：[Loon 订阅](https://nsloon.app/docs/Rule/sub_rule/)、[Surge 规则集](https://manual.nssurge.com/rules/ruleset.html)、[Surge 域名](https://manual.nssurge.com/rules/domain.html)、[Surge IP](https://manual.nssurge.com/rules/ip.html)、[Surfboard 规则集](https://getsurfboard.com/docs/profile-format/rule/ruleset/)、[Surfboard 语法参考](https://getsurfboard.com/docs/ai-profile-guide/reference/)。Shadowrocket 的[官网](https://shadowlaunch.com/)没有提供足以核对全部高级语义的公开手册，因此兼容文本仍需在 App 内验收

## Mihomo 和 Stash

使用 `classical`。下面是 Mihomo 地址；Stash 使用相同文件名，将目录改为 `rules/stash/`：

```yaml
rule-providers:
  gemini:
    type: http
    behavior: classical
    format: yaml
    url: https://raw.githubusercontent.com/LuckyLight6/loon-rules/main/rules/mihomo/1030-gemini-connections.yaml
    path: ./rules/gemini.yaml
    interval: 86400

rules:
  - RULE-SET,gemini,PROXY
```

`DOMAIN-WILDCARD` 会转成限定完整主机名的 `DOMAIN-REGEX`，保留 `*`、`?` 和数字范围的含义。IP 行的 `no-resolve` 保留在行内；不要在引用整份 provider 时统一追加这个参数，否则原本允许解析的规则也会受影响

依据：[Mihomo Classical 格式](https://wiki.metacubex.one/en/config/rule-providers/content/)、[Mihomo 规则](https://wiki.metacubex.one/en/config/rules/)、[Stash 规则集](https://stash.wiki/en/rules/rule-set)、[Stash 规则类型](https://stash.wiki/en/rules/rule-types)

## Egern

在已有 `rules` 中引用原生 YAML：

```yaml
rules:
  - rule_set:
      match: https://raw.githubusercontent.com/LuckyLight6/loon-rules/main/rules/egern/1030-gemini-connections.yaml
      policy: PROXY
      update_interval: 86400
```

域名使用 `domain_set`、`domain_suffix_set` 等字段，ASN 使用 `asn_set`。Egern 的 `no_resolve` 作用于所在集合的 IP 条件；遇到 0110 这种混合表，允许解析的条件放在主集合，仅处理已有 IP 的条件放在带 `no_resolve: true` 的 `or_set` 分支。没有把两种用途合成一个全局开关

依据：[Egern 规则和规则集合](https://egernapp.com/docs/configuration/rules/)。格式依据官方字段生成，OR 分支及实际解析行为仍需 Egern App 验收

## Quantumult X

在 `[filter_remote]` 指定实际策略：

```ini
[filter_remote]
https://raw.githubusercontent.com/LuckyLight6/loon-rules/main/rules/quantumult-x/1030-gemini-connections.list, tag=Gemini, force-policy=PROXY, enabled=true
```

成品采用 `host`、`host-suffix`、`host-wildcard` 等原生写法，行内 `proxy` 由 `force-policy` 覆盖。文件不带 `final`，不会抢走其他订阅的兜底。字符范围会有限展开为等价条件，不把 `[0-9]` 粗略改成 `?`

官方样例没有等价的逐条 `no-resolve` 参数。因此，含此参数的整组不输出，不能删掉参数后假称行为相同。依据：[官方配置](https://github.com/crossutility/Quantumult-X/blob/master/sample.conf)、[官方 filter 示例](https://github.com/crossutility/Quantumult-X/blob/master/filter.snippet)

## sing-box

引用 source JSON，示例使用 1.14.4 检查：

```json
{
  "route": {
    "rule_set": [
      {
        "type": "remote",
        "tag": "gemini",
        "format": "source",
        "url": "https://raw.githubusercontent.com/LuckyLight6/loon-rules/main/rules/sing-box/1030-gemini-connections.json",
        "update_interval": "1d"
      }
    ],
    "rules": [
      {"rule_set": "gemini", "action": "route", "outbound": "PROXY"}
    ]
  }
}
```

将片段合并到已有配置，保留自己的出站、DNS 和后续路由。source 规则集只保存匹配条件，客户端负责读取及编译；仓库不为每次更新时间另存一份二进制

Headless Rule 没有原生 ASN、GeoIP 条件，解析动作也不在规则集里。本版保守地不输出含 IP 条件的混合组，不用域名删减版冒充原组。依据：[Source 格式](https://sing-box.sagernet.org/configuration/rule-set/source-format/)、[Headless Rule](https://sing-box.sagernet.org/configuration/rule-set/headless-rule/)

## V2Ray

成品是可合并的 `routing.rules` JSON 片段，不是节点订阅。下载所需文件，将 `outboundTag` 中的 `PROXY` 换成自己的出口，再把 `routing.rules` 按清单顺序加入已有配置

```sh
curl -fL https://raw.githubusercontent.com/LuckyLight6/loon-rules/main/rules/v2ray/1030-gemini-connections.json -o gemini-routing.json
v2ray test -c base.json -c gemini-routing.json
```

测试前，`base.json` 必须已有名为 `PROXY` 的出站，或先替换片段中的标签。核心支持合并配置文件；更新周期由使用它的前端或运维任务安排，仓库不会改写本机的私人配置

V2Ray 的 `domainStrategy` 是路由层设置，不能在单份远程片段里逐条复现 Loon 的 DNS 触发条件。本版不导出含 IP 的混合组，也不擅自修改全局 `domainStrategy`。依据：[路由](https://www.v2fly.org/config/routing.html)、[核心配置文档](https://www.v2fly.org/config/overview.html)

## 不可转换时如何处理

例如 Claude、OpenAI 和 Telegram 的现有规则含 IP 或 ASN 条件。Loon、Surge、Mihomo、Stash 可以保留它们；其他格式可能标为无法转换。不要自行删去报错行，也不要把 `.lsr` 改后缀当作解决办法

首次生成就不支持的组，会在清单中明确标出。以后已经发布的客户端订阅如果因新增规则变得无法转换，更新任务会停止并保留上一版，等待补齐适配；不会自动发布删减表或让订阅突然消失

原生程序检查目前覆盖 Mihomo、sing-box、V2Ray。其余客户端依据公开语法及兼容格式生成，尚未逐个完成 App 实测。格式能读入，也不能代替真实设备上的 DNS、WebRTC、登录、支付、上传、推送与长连接测试，见[网络测试](network-testing.md)

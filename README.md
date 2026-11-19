# Loon 分流规则

在 Loon 里给 Claude 单独选节点，让 Apple 下载、账户登录和海外媒体各走合适的出口。订阅同一个 `.lsr` 地址，几台设备就能更新同一份规则。**规则只管哪些请求归到哪一组，节点和策略由你在 Loon 里选。**

## 订阅一份规则

1. 从[编号清单](INDEX.md)打开所需的规则文件。在 GitHub 点 **Raw**，复制地址。
2. 在 Loon 添加规则订阅，粘贴地址，选一个已经存在的策略。例如，把 `061-claude-connections` 交给手动选节点的 Claude 策略。
3. 切到分流模式，打开目标服务。在请求记录里看**匹配规则**和**实际节点**。有多个订阅时，把专项放在通用规则前。

也可以在配置的 `[Remote Rule]` 段添加同样的订阅。下面的 `PROXY` 可以换成你的策略组：

```ini
[Remote Rule]
https://raw.githubusercontent.com/LuckyLight6/loon-rules/main/rules/061-claude-connections.lsr, policy=PROXY, tag=061-claude-connections, enabled=true
```

建议使用 Loon **build 1008 或更新版本**。App Store 和 Find My 的数字分片要用这个版本起支持的 `DOMAIN-WILDCARD`。[订阅语法](https://nsloon.app/docs/Rule/sub_rule/) · [规则优先级](https://nsloon.app/docs/Rule/#匹配优先级)

## 想分开选节点，还是统一出口？

| 要分流的服务 | 怎么选 |
|---|---|
| Apple | 细分选 `031–059`：账户和购买可共用一个手选节点，下载、推送和 iCloud 独立；在中国大陆，TV、News 和 Apple Intelligence 走可用代理。想统一代理再选 `030-apple-all`，不要把这份合集整体设为直连。 |
| AI | Claude、ChatGPT、Gemini、Grok 分别用 `061–064`。若海外 AI 全用同一个出口，选 `060-ai-overseas-all` 替代它的成员。国产 AI 国内入口用 `084`，国际入口用 `085`；Apple Intelligence 始终用 `046`。 |
| Google 和 Microsoft | Google 的登录、邮件、会议、网盘和下载在 `160–169`；Microsoft 的对应服务在 `100–115`。统一出口分别用 `160` 或 `100` 替代成员。Google Gemini、YouTube、Microsoft Copilot 和 GitHub Copilot 仍各自分流。 |
| 其他日常服务 | 网络接入、隐私、社交、代码托管、影视游戏、国内购物和地区兜底，按[编号清单](INDEX.md)选。相同用途的备选表只用一份。 |

**同一用途不要同时开细分表和它的合集。** Loon 的本地与插件规则可以先于订阅命中；已有宽泛规则时，光调整订阅顺序不够。域名未命中才进入 IP 阶段。仓库只在确实按已知 IP 匹配时加 `no-resolve`；私网识别和地区兜底仍保留必要的解析。

## 规则怎么更新

[自动更新](https://github.com/LuckyLight6/loon-rules/actions/workflows/refresh.yml)计划每天北京时间 **11:37** 检查，也可以手动运行。每次更新先核对来源、首条命中、共享域名和合集顺序；不通过就保留上一版。边界明确的来源按规则筛选，范围较宽的上游只记录待复核变化，不把新增域名直接推给订阅者。

文件头写明用途、范围、来源、创建时间和正文更新时间；日期使用 UTC。只改说明或重新检查不会刷新正文日期。[检查结果](status.json) · [来源与许可](NOTICE.md)

## 遇到错分或连不上

先看[各服务推荐出口](COVERAGE.md)，再用[实际测试步骤](NETWORK-VERIFICATION.md)确认。域名命中不代表 DNS 和 WebRTC 出口正确；内网、公司 VPN、节点、订阅凭据和证书都应在自己设备上配置，不放进公共规则。

如果反馈问题，提供**公开主机名、Loon 版本、命中规则、预期和实际出口**就够了。不要贴完整配置、登录链接、内网域名或带凭据的日志。

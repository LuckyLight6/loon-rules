# Loon 分流规则与多客户端格式

按服务和用途选择出口的 Loon 订阅规则，覆盖 AI、Apple、Google、Microsoft，以及开发、通讯、支付、影音、游戏等产品。规则不包含节点；同一份订阅可以在不同设备上绑定不同策略，也可以把多份订阅交给同一个策略组。同时从同一套数据生成 Surge、Mihomo、Stash、Egern、Surfboard、Shadowrocket、Quantumult X、sing-box 和 V2Ray 格式，具体范围见[客户端格式与限制](docs/clients.md)。

[规则清单与订阅地址](docs/rules.md) · [其他客户端](docs/clients.md) · [按厂商查产品](docs/services.md) · [出口怎么选](docs/routing.md) · [怎样测试](docs/network-testing.md) · [自动更新方式](docs/maintenance.md) · [参与开发](docs/development.md)

## 开始使用

以海外 AI 为例，在 Loon 新增规则订阅，复制 [1000 海外 AI 合集](https://raw.githubusercontent.com/LuckyLight6/loon-rules/main/rules/1000-ai-overseas-all.lsr)的地址，绑定已有的代理策略。直接编辑配置时，写在 `[Remote Rule]` 段，把 `PROXY` 换成实际策略名：

```ini
[Remote Rule]
https://raw.githubusercontent.com/LuckyLight6/loon-rules/main/rules/1000-ai-overseas-all.lsr, policy=PROXY, tag=1000-ai-overseas-all, enabled=true
```

在原配置的副本里试用，保留最初的备份。按[清单顺序](docs/rules.md)排列所选订阅，再切到分流模式。订阅刷新只更新规则正文，不会替设备调整顺序或选择节点。部分规则使用 `DOMAIN-WILDCARD`，需要 Loon **build 1008 或更新版本**。[Loon 规则订阅文档](https://nsloon.app/docs/Rule/sub_rule/)

规则采用四位序号，初始每 10 递增，为新增规则预留空号。文件、清单和配置顺序使用同一套编号。

## 先选择合集，或按产品分别选路

| 使用方式 | 选择 |
|---|---|
| 海外 AI | 1000，或按 Claude、OpenAI、Gemini、xAI 等产品分别选择 |
| 国产 AI 国际版与国内版 | 1800 国际版；6000 国内版与共用入口 |
| 海外 AI 中国区服务 | 6250，目前只含已核实的 JetBrains AI 中国区 API |
| Apple 日常分流 | 2010 海外功能、2070 推送、2080 普通服务；全部统一出口则选 2000 |
| 海外开发、通讯、支付、加密资产 | 3000、3300、3500、3600；各自保留产品成员 |
| 海外影音、游戏、办公协作 | 3800、4100、4300；各自保留产品成员 |
| Google、Microsoft | 4500、4700 日常服务；AI、YouTube、GitHub 等专项分别处理 |
| 跨国厂商国内入口 | 4900，或分别选高通、NVIDIA、Intel 等成员，放在海外具体服务之后 |
| 国内开发、通讯、支付 | 6300、6500、6700；各自保留产品成员 |
| 国内影音、游戏、生活办公 | 6900、7200、7400；各自保留产品成员 |
| 厂商共用范围 | 8000 全球厂商与云平台；8400 国内厂商，均在具体产品之后 |
| 海外与国内补充 | 8200 海外补充；8600 国内补充，均可改用成员分别选路 |

`-all` 从所列成员生成，**与成员二选一**。需要不同出口时改用细分规则；多份规则可以共用一个策略组，不必每份都建组。合集也不能重叠选择，例如 Apple 完整合集与日常拆分方案

## 顺序与拦截

网络接入与局域网、常规广告与隐私之后，依次处理海外与国际版 AI、Apple、海外具体产品、Google 和 Microsoft。跨国厂商的国内入口随后处理；国内具体产品再按业务排列。厂商通用父域、海外补充和国内补充放在后面，避免抢走具体业务

常规广告用 0220，0210 是已核实的 Apple 广告与 OpenAI 广告像素。7800 是默认关闭的扩展拦截，位于具体产品之后、厂商共用表之前。0230 只拦已列公共 STUN 端点，可能影响通话和会议，不能凭它宣称 WebRTC 已防泄漏。[实际命中与防泄漏测试](docs/network-testing.md)

## DNS 插件单独选择

[公网服务分域 DoH 插件](plugins/public-services-doh.plugin)为所列海外业务使用 Cloudflare，为国产 AI 国内版和所列直连 Apple 服务使用阿里公共 DoH；其他名称沿用系统或 VPN 的解析器。插件只有域名映射，不解密 HTTPS，不运行脚本。DoH 连接的最终出口与失败回落要在设备上检查；选择加密上游不等于防泄漏已经通过。内网名称和私有网段只放在自己的配置里。[选择与测试 DNS](docs/network-testing.md#dns先看查询走了哪里)

## 更新与反馈

仓库计划每天北京时间 **11:37 和 23:37** 更新，定时触发状态以 Actions 中的 `schedule` 记录为准。生成器读取官方用途资料和社区来源，检查新增、撤回、归属与首条命中，通过后才提交成品。源码、分类条件与维护依据都保留在仓库中；每轮检查摘要在 GitHub Actions，详细维护状态在 `data/maintenance-state.json`。[自动更新能做什么](docs/maintenance.md)

反馈错分时，提供公开主机名、Loon 版本、命中规则、预期出口和操作结果即可。请勿提交完整配置、节点凭据、证书、内部名称或带登录信息的 URL。

生成器代码使用 [MIT License](LICENSE)。规则与参考数据遵循各自来源的许可，见 [NOTICE](NOTICE.md) 和 `licenses/`。

# Loon 分流规则

按服务和用途选择出口的 Loon 订阅规则，覆盖 AI、Apple、Google、Microsoft，以及开发、通讯、支付、影音、游戏等产品。规则不包含节点；同一份订阅可以在不同设备上绑定不同策略，也可以把多份订阅交给同一个策略组。

[规则清单与订阅地址](docs/rules.md) · [出口怎么选](docs/routing.md) · [怎样测试](docs/network-testing.md) · [自动更新方式](docs/maintenance.md) · [参与开发](docs/development.md)

## 开始使用

以海外 AI 为例，在 Loon 新增规则订阅，复制 [100 海外 AI 合集](https://raw.githubusercontent.com/LuckyLight6/loon-rules/main/rules/100-ai-overseas-all.lsr)的地址，绑定已有的代理策略。直接编辑配置时，写在 `[Remote Rule]` 段，把 `PROXY` 换成实际策略名：

```ini
[Remote Rule]
https://raw.githubusercontent.com/LuckyLight6/loon-rules/main/rules/100-ai-overseas-all.lsr, policy=PROXY, tag=100-ai-overseas-all, enabled=true
```

在原配置的副本里试用，保留最初的备份。按[清单顺序](docs/rules.md)排列所选订阅，再切到分流模式。订阅刷新只更新规则正文，不会替设备调整顺序或选择节点。部分规则使用 `DOMAIN-WILDCARD`，需要 Loon **build 1008 或更新版本**。[Loon 规则订阅文档](https://nsloon.app/docs/Rule/sub_rule/)

## 先决定哪些服务需要分开选路

| 使用方式 | 选择 |
|---|---|
| 海外 AI 用同一稳定出口 | 100；需要分别选路时，改选 Claude、OpenAI、Gemini、xAI 等成员 |
| 国产 AI 区分国内与国际入口 | 国内版 500，国际版 125；两者也各有产品细分。Apple Intelligence 独立使用 123 |
| Apple 登录和下载用不同出口 | 用 Apple 细分表。账户 201、交易 205 可选同一稳定节点；安装包 206、系统下载 223、iCloud 内容 213 分别选路。TV、News、PCC 使用可用地区的代理 |
| Google 或 Microsoft 统一选路 | 分别选 450、470；需要区分账户、会议、文件或更新下载时，改选成员 |
| 补充专项没有识别的网站 | 670 交给海外影音策略，675 交给通用代理。国内补充选 702；需要分别控制时，用 704、707、711 替代 |

`-all` 是合集，**与它的成员二选一**。`-extra` 只补专项以外的范围，不能代替专项。规则按用途细分，不要求每份都新建一个策略组。

## 顺序与拦截

清单和生成检查使用同一套顺序：网络接入与局域网、常规广告与隐私、海外及国际版 AI、Apple、海外具体产品、Google、Microsoft、国内 AI 与国内产品、可选扩展广告、海外补充、国内补充。具体产品先认领专用主机，共享平台和地区补充随后处理。

常规广告用 022。021 是明确的 Apple 广告与 OpenAI 广告像素；650 是默认关闭的扩展拦截。023 只拦已列出的公共 STUN 端点，可能影响会议和语音，不能凭它宣称 WebRTC 已防泄漏。[实际命中与防泄漏测试](docs/network-testing.md)

## DNS 插件单独选择

[公网服务分域 DoH 插件](plugins/public-services-doh.plugin)为所列海外业务使用 Cloudflare，为国产 AI 国内版与大陆 iCloud 使用阿里公共 DoH；其他名称沿用系统或 VPN 的解析器。插件只有域名映射，不解密 HTTPS，不运行脚本。DoH 连接的最终出口与失败回落要在设备上检查；选择加密上游不等于防泄漏已经通过。内网名称和私有网段只放在自己的配置里。[选择与测试 DNS](docs/network-testing.md#dns先看查询走了哪里)

## 更新与反馈

仓库配置了每天北京时间 **11:37** 的更新任务。生成器读取官方用途资料和社区来源，检查新增、撤回、归属与首条命中，通过后才提交成品。源码、分类条件与维护依据都保留在仓库中；每轮检查摘要在 GitHub Actions，详细维护状态在 `data/maintenance-state.json`。[自动更新能做什么](docs/maintenance.md)

反馈错分时，提供公开主机名、Loon 版本、命中规则、预期出口和操作结果即可。请勿提交完整配置、节点凭据、证书、内部名称或带登录信息的 URL。

生成器代码使用 [MIT License](LICENSE)。规则与参考数据遵循各自来源的许可，见 [NOTICE](NOTICE.md) 和 `licenses/`。

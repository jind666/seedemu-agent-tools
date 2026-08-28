# DNS 工具设计大纲

## 一、基础工具

基础工具负责单次、只读的 DNS 信息查询，不修改 zone，也不判断完整委派是否正确。

### `dns.lookup`

- 查询 A、AAAA、NS、MX、TXT、SOA、CNAME 等记录；
- 支持使用 `source` 的默认 resolver，或查询指定 DNS 服务器；
- 区分命令执行失败、DNS 响应状态和无记录三种情况；
- 作为其他诊断工具的基础查询能力。

### `dns.reverse_lookup`

- 对 IPv4 或 IPv6 地址执行 PTR 反向查询；
- 自动生成对应的反向 DNS 名称；
- 返回 PTR 记录及 DNS 响应状态。

### `dns.batch_lookup`

- 在一次调用中查询多个名称和记录类型，减少 Agent 重复调用工具；
- 每个查询独立返回状态，单个失败不丢失其他查询结果；
- 适用于一次收集某个 zone 的 SOA、NS、A 和 AAAA 等基础信息；

## 二、域名注册及更新工具

这类工具会改变域名所有权、委派或 zone 内容，需要验证当前 `source` 的身份与权限，并对
写操作提供幂等和状态查询能力。

#### `registrar_find`

- 定位当前仿真环境中允许 `source` 使用的 Registrar 前端；
- 只返回注册服务位置，不直接列出可调用接口或返回 secret；
- Agent 后续读取 Registrar 的公开网页和同源 JavaScript，自行理解注册流程。

#### `registrar_request`

- 读取 Registrar 前端资源并发送受限的同源请求；
- 支持 availability check、registration quote、registration、operation 查询、domain
  查询和 nameserver update 等现实中存在对应能力的业务操作；
- 不作为任意 HTTP 代理，必须限制 Registrar origin、重定向和危险请求；
- 支持“注册与委派一并处理”和“注册后更新 Nameserver”两种流程。

#### `dns_configure`

- 统一处理自带权威 DNS 的动态建区和记录维护；
- zone 不存在时，验证 `source` 权限并执行 Primary/Secondary provisioning；
- zone 加载后，通过 RFC 2136 和 update TSIG 新增、替换或删除记录；
- 使用独立的 transfer TSIG 完成主从同步；
- 验证 SOA、NS、serial、权威响应及主从收敛情况。

## 三、诊断工具

诊断工具保持只读，重点不是返回一次查询结果，而是比较多个观察点、解释解析路径并定位配置
错误。

### `dns.compare`

- 从同一个 `source` 向多个 DNS 服务器查询同一记录；
- 比较响应状态、答案、TTL、延迟和超时；
- 用于发现缓存差异、主从不一致或不同 resolver 的结果差异。

### `dns.trace`

- 从根区开始跟踪完整 DNS 委派链；
- 展示每一层 referral、权威服务器和最终答案；
- 用于定位解析在哪一级父区或子区中断。

### `dns.check_delegation`

- 比较父区返回的 referral/glue 与子区权威服务器返回的 NS；
- 检查委派目标、glue 地址和子区权威配置是否一致；
- 用于验证 Registrar 完成父区更新后的委派结果。

### `dns.zone_transfer`

- 在明确授权的情况下执行 AXFR/IXFR，检查权威服务器实际提供的完整 zone；
- 用于诊断 Secondary 数据缺失、serial 不一致或传送权限配置错误；
- 默认拒绝未授权目标，并限制返回数据量，避免成为任意 zone 枚举工具；

### `dns.validate_dnssec`

- 验证 DS、DNSKEY、RRSIG 组成的 DNSSEC 信任链；
- 区分未启用 DNSSEC、签名过期、DS 不匹配和验证失败；

### `dns.observe_cache`

- 从同一 `source` 重复查询并观察 TTL 变化、缓存命中和过期后的刷新；
- 用于分析权威记录已经更新但递归 resolver 仍返回旧值的问题；
- 只负责观察，不主动清理或修改 resolver cache。

### `dns.diagnose_resolver`

- 检查指定递归 resolver 的可达性、递归能力和基础响应行为；
- 用于区分权威 DNS 配置错误与 `source` 所使用 resolver 的故障；
- 与 `dns.lookup`、`dns.compare` 共享底层查询能力，但输出面向 resolver 健康状态。

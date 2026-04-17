# AIBank Hermes Agent

基于 [hermes-agent](https://github.com/NousResearch/hermes-agent) 的银行业务智能代理扩展包。

## 目录结构

```
├── hermes/            # hermes-agent 子模块
├── tools/             # 自定义工具（安装时复制到 hermes/tools/）
├── plugins/           # 自定义插件（安装时复制到 hermes/plugins/）
├── guards/            # 防护插件（安装时复制到 ~/.hermes/plugins/）
├── skills/            # 自定义技能（安装时复制到 ~/.hermes/skills/）
└── install.sh         # 一键安装脚本
```

## 快速安装

```bash
# 克隆仓库（包含子模块）
git clone --recursive https://github.com/your-org/aibank-hermes-agent.git

# 或者先克隆再初始化子模块
git clone https://github.com/your-org/aibank-hermes-agent.git
cd aibank-hermes-agent
git submodule update --init --recursive

# 执行一键安装
./install.sh
```

安装脚本会：
1. 初始化子模块（包括嵌套子模块）
2. 复制自定义工具、插件、技能到相应目录（增量模式，已存在的跳过）
3. 运行 hermes 的 setup-hermes.sh 完成环境配置

## 使用

安装完成后：

```bash
# 如果 PATH 未自动配置，先重新加载 shell
source ~/.zshrc  # 或 source ~/.bashrc

# 运行 hermes
hermes

# 查看状态
hermes status

# 配置 API keys
hermes setup
```

## 自定义内容

### Skills（技能）

`skills/mobile_bank/` 包含银行业务相关技能：
- 信用卡管家
- 贷款顾问
- 理财顾问
- 风险管理
- 股票分析
- 等

### Guards（防护）

`guards/mobile_bank_guard/` 包含银行业务安全防护插件。

### Plugins（插件）

`plugins/memory/` 包含记忆增强插件。

## 更新子模块

```bash
git submodule update --remote hermes
```
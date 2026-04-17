---
name: medical-imaging-review
description: 撰写医学影像AI研究的全面文献综述。在撰写综述论文、系统综述或关于CT、MRI、X射线影像中的分割、检测、分类等主题的文献分析时使用。触发词包括"综述论文"、"综述"、"文献综述"、"综述"，或提及撰写医学影像深度学习的学术综述。
allowed-tools:
  - Read
  - Write
  - Edit
  - Glob
  - Grep
  - Bash
  - WebSearch
  - WebFetch
  - TodoWrite
---

# 医学影像AI文献综述写作技能

撰写医学影像AI全面文献综述的系统化工作流程。

## 快速开始

当用户请求文献综述时：

1. **初始化项目**，包含三个核心文件：
   - `CLAUDE.md` - 写作指南和术语
   - `IMPLEMENTATION_PLAN.md` - 分阶段执行计划
   - `manuscript_draft.md` - 主要手稿

2. **遵循7阶段工作流程**（参见 [WORKFLOW.md](WORKFLOW.md)）

3. **使用标准模板**（参见 [TEMPLATES.md](TEMPLATES.md)）

## 核心原则

### 写作风格
- 使用**模糊语言**："可能"、"表明"、"似乎"、"已显示出有希望的结果"
- 避免绝对声明：永远不要说"X是最好的方法"
- 每个声明都需要引用支持
- 每个方法部分都需要一个**局限性**段落

### 必需元素
- **要点框**（3-5个项目符号）在标题后
- 每个主要部分的**比较表**
- **性能指标**，格式一致（Dice: 0.XXX, HD95: X.XX mm）
- **图形占位符**，带详细说明
- **按主题组织的参考文献**（通常80-120篇）

### 段落结构
1. 主题句（主要声明）
2. 支持证据（引用+数据）
3. 分析（批判性评估）
4. 过渡到下一段

## 文献来源

### ArXiv MCP（预印本和最新研究）

GitHub: https://github.com/blazickjp/arxiv-mcp-server

**可用工具：**
- `search_papers` - 通过关键词搜索，带日期范围和类别过滤器
- `download_paper` - 通过arXiv ID下载论文
- `list_papers` - 列出所有已下载的论文
- `read_paper` - 读取已下载的论文内容

**配置：**
```json
{
  "mcpServers": {
    "arxiv": {
      "command": "uvx",
      "args": ["arxiv-mcp-server"],
      "env": {
        "ARXIV_STORAGE_PATH": "~/.arxiv-mcp-server/papers"
      }
    }
  }
}
```

**使用示例：**
```
搜索："医学影像分割transformer"
类别：cs.CV, eess.IV
日期范围：2023-01-01至今
最大结果：50
```

### PubMed MCP（生物医学文献）

GitHub: https://github.com/grll/pubmedmcp

访问3500多万篇生物医学文献引用。

**配置：**
```json
{
  "mcpServers": {
    "pubmedmcp": {
      "command": "uvx",
      "args": ["pubmedmcp@latest"],
      "env": {
        "UV_PRERELEASE": "allow",
        "UV_PYTHON": "3.12"
      }
    }
  }
}
```

**搜索技巧：**
- 使用MeSH术语进行精确的医学搜索
- 结合出版物类型过滤器（综述、临床试验）
- 按日期过滤以获取最新文献

### Zotero集成（参考文献管理）

访问本地Zotero数据库（需要用户提供用户ID）：
```bash
# 列出集合
curl -s "http://localhost:23119/api/users/[USER_ID]/collections"

# 从集合获取项目
curl -s "http://localhost:23119/api/users/[USER_ID]/collections/[KEY]/items"
```

或者，可以使用Zotero-MCP，但需要用户提前进行手动配置。

提取：标题、摘要、日期、创建者、出版物标题、DOI

### 来源选择指南

| 来源 | 最适合 | 优势 |
|--------|----------|-----------|
| **ArXiv** | 最新方法、深度学习进展 | 预印本、快速访问、CS/AI焦点 |
| **PubMed** | 临床验证、医学背景 | 同行评议、MeSH索引、临床 |
| **Zotero** | 组织的集合、现有库 | 本地管理、注释、PDF |

## 标准综述结构

```markdown
# [标题]：最新进展和未来方向

## 要点
- [3-5个项目符号总结主要发现]

## 摘要

## 1. 引言
### 1.1 临床背景
### 1.2 技术挑战
### 1.3 范围和贡献

## 2. 数据集和评估指标
### 2.1 公共数据集
**表1. 公共数据集**
| 数据集 | 年份 | 病例数 | 注释 | 访问 |

### 2.2 评估指标

## 3. 深度学习方法
### 3.1 [类别1]
### 3.2 [类别2]
...
**表2. 方法比较**
| 参考文献 | 类别 | 架构 | 数据集 | 性能 | 创新 |

## 4. 下游应用

## 5. 商业产品和临床转化
**表3. 商业产品**

## 6. 讨论
### 6.1 当前局限性
### 6.2 未来方向

## 7. 结论

## 参考文献
```

## 方法描述模板

```markdown
### 3.X [方法类别]

[1-2段引言，说明动机]

**[方法名称]：** [作者]等人[ref]提出了[方法]，该方法[创新]：
- [关键组件1]
- [关键组件2]
在[数据集]上达到Dice X.XX。

**数学公式：**（如适用）
$$\mathcal{L} = \mathcal{L}_{seg} + \lambda \mathcal{L}_{aux}$$

**局限性：** 尽管有优势，[类别]方法面临：（1）[限制1]；（2）[限制2]。
```

## 引用模式

```markdown
# 数据引用
"...达到Dice 0.89 [23]"

# 方法引用
"Gu等人[45]提出了..."

# 多重引用
"多项研究证明了... [12, 15, 23]"

# 比较性
"虽然[12]专注于...，[15]解决了..."
```

## 质量检查清单

完成前，验证：
- [ ] 存在要点（3-5个项目符号）
- [ ] 每个主要部分有表格
- [ ] 每个方法类别有局限性
- [ ] 术语一致
- [ ] 适当使用模糊语言
- [ ] 80-120篇参考文献，按主题组织
- [ ] 带说明的图形占位符

## 文件参考

- [WORKFLOW.md](WORKFLOW.md) - 详细的7阶段工作流程
- [TEMPLATES.md](TEMPLATES.md) - CLAUDE.md和IMPLEMENTATION_PLAN.md模板
- [DOMAINS.md](DOMAINS.md) - 特定领域的方法类别

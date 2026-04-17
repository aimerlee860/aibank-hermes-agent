#!/usr/bin/env python3
"""
技能初始化器 - 从模板创建新技能

用法：
    init_skill.py <skill-name> --path <path>

示例：
    init_skill.py my-new-skill --path skills/public
    init_skill.py my-api-helper --path skills/private
    init_skill.py custom-skill --path /custom/location
"""

import sys
from pathlib import Path

SKILL_TEMPLATE = """---
name: {skill_name}
description: [TODO: 完成并详细说明技能做什么以及何时使用它。包括何时使用此技能 - 触发它的特定场景、文件类型或任务。]
---

# {skill_title}

## 概述

[TODO: 1-2句话解释此技能实现的功能]

## 构建此技能

[TODO: 选择最适合此技能目的的结构。常见模式：

**1. 基于工作流程**（最适合顺序过程）
- 当有清晰的逐步程序时效果很好
- 示例：DOCX技能，带有"工作流程决策树" → "读取" → "创建" → "编辑"
- 结构：## 概述 → ## 工作流程决策树 → ## 步骤1 → ## 步骤2...

**2. 基于任务**（最适合工具集合）
- 当技能提供不同操作/功能时效果很好
- 示例：PDF技能，带有"快速开始" → "合并PDF" → "拆分PDF" → "提取文本"
- 结构：## 概述 → ## 快速开始 → ## 任务类别1 → ## 任务类别2...

**3. 参考/指南**（最适合标准或规范）
- 对于品牌指南、编码标准或要求效果很好
- 示例：品牌样式，带有"品牌指南" → "颜色" → "字体" → "功能"
- 结构：## 概述 → ## 指南 → ## 规范 → ## 用法...

**4. 基于能力**（最适合集成系统）
- 当技能提供多个相互关联的功能时效果很好
- 示例：产品管理，带有"核心能力" → 编号的能力列表
- 结构：## 概述 → ## 核心能力 → ### 1. 功能 → ### 2. 功能...

模式可以根据需要混合和匹配。大多数技能组合模式（例如，从基于任务开始，为复杂操作添加工作流程）。

完成后删除整个"构建此技能"部分 - 这只是指导。]

## [TODO: 根据选择的结构替换为第一个主要部分]

[TODO: 在此处添加内容。参见现有技能中的示例：
- 技术技能的代码示例
- 复杂工作流程的决策树
- 具有真实用户请求的具体示例
- 根据需要引用脚本/模板/参考资料]

## 资源

此技能包括示例资源目录，演示如何组织不同类型的捆绑资源：

### scripts/
可以直接运行以执行特定操作的可执行代码（Python/Bash等）。

**其他技能的示例：**
- PDF技能：`fill_fillable_fields.py`、`extract_form_field_info.py` - PDF操作的实用工具
- DOCX技能：`document.py`、`utilities.py` - 文档处理的Python模块

**适用于：** Python脚本、shell脚本或任何执行自动化、数据处理或特定操作的可执行代码。

**注意：** 脚本可以在不加载到上下文的情况下执行，但仍可以由Claude读取以进行修补或环境调整。

### references/
旨在加载到上下文中的文档和参考资料，以告知Claude的过程和思考。

**其他技能的示例：**
- 产品管理：`communication.md`、`context_building.md` - 详细的工作流程指南
- BigQuery：API参考文档和查询示例
- 财务：模式文档、公司政策

**适用于：** 深入文档、API参考、数据库模式、综合指南或Claude在工作时应参考的任何详细信息。

### assets/
不打算加载到上下文中的文件，而是在Claude产生的输出中使用。

**其他技能的示例：**
- 品牌样式：PowerPoint模板文件（.pptx）、徽标文件
- 前端构建器：HTML/React样板项目目录
- 字体：字体文件（.ttf、.woff2）

**适用于：** 模板、样板代码、文档模板、图像、图标、字体或任何要在最终输出中复制或使用的文件。

---

**可以删除任何不需要的目录。** 并非每个技能都需要所有三种类型的资源。
"""

EXAMPLE_SCRIPT = '''#!/usr/bin/env python3
"""
{skill_name}的示例辅助脚本

这是一个可以直接执行的占位符脚本。
替换为实际实现，如果不需要则删除。

其他技能的真实脚本示例：
- pdf/scripts/fill_fillable_fields.py - 填写PDF表单字段
- pdf/scripts/convert_pdf_to_images.py - 将PDF页面转换为图像
"""

def main():
    print("这是{skill_name}的示例脚本")
    # TODO: 在此处添加实际脚本逻辑
    # 这可能是数据处理、文件转换、API调用等

if __name__ == "__main__":
    main()
'''

EXAMPLE_REFERENCE = """# {skill_title}的参考文档

这是详细参考文档的占位符。
替换为实际参考内容，如果不需要则删除。

其他技能的真实参考文档示例：
- product-management/references/communication.md - 状态更新的综合指南
- product-management/references/context_building.md - 收集上下文的深入探讨
- bigquery/references/ - API参考和查询示例

## 参考文档何时有用

参考文档非常适合：
- 综合API文档
- 详细的工作流程指南
- 复杂的多步骤过程
- 对主SKILL.md来说太长的信息
- 仅特定用例需要的内容

## 结构建议

### API参考示例
- 概述
- 身份验证
- 带示例的端点
- 错误代码
- 速率限制

### 工作流程指南示例
- 先决条件
- 逐步说明
- 常见模式
- 故障排除
- 最佳实践
"""

EXAMPLE_ASSET = """# 示例资产文件

此占位符表示资产文件的存储位置。
替换为实际资产文件（模板、图像、字体等），如果不需要则删除。

资产文件不打算加载到上下文中，而是在Claude产生的输出中使用。

其他技能的资产文件示例：
- 品牌指南：logo.png、slides_template.pptx
- 前端构建器：hello-world/目录，包含HTML/React样板
- 字体：custom-font.ttf、font-family.woff2
- 数据：sample_data.csv、test_dataset.json

## 常见资产类型

- 模板：.pptx、.docx、样板目录
- 图像：.png、.jpg、.svg、.gif
- 字体：.ttf、.otf、.woff、.woff2
- 样板代码：项目目录、起始文件
- 图标：.ico、.svg
- 数据文件：.csv、.json、.xml、.yaml

注意：这是文本占位符。实际资产可以是任何文件类型。
"""


def title_case_skill_name(skill_name):
    """将连字符技能名称转换为标题大小写以显示。"""
    return ' '.join(word.capitalize() for word in skill_name.split('-'))


def init_skill(skill_name, path):
    """
    使用模板SKILL.md初始化新技能目录。

    参数：
        skill_name: 技能名称
        path: 应创建技能目录的路径

    返回：
        创建的技能目录路径，如果错误则返回None
    """
    # 确定技能目录路径
    skill_dir = Path(path).resolve() / skill_name

    # 检查目录是否已存在
    if skill_dir.exists():
        print(f"❌ 错误：技能目录已存在：{skill_dir}")
        return None

    # 创建技能目录
    try:
        skill_dir.mkdir(parents=True, exist_ok=False)
        print(f"✅ 创建技能目录：{skill_dir}")
    except Exception as e:
        print(f"❌ 创建目录错误：{e}")
        return None

    # 从模板创建SKILL.md
    skill_title = title_case_skill_name(skill_name)
    skill_content = SKILL_TEMPLATE.format(
        skill_name=skill_name,
        skill_title=skill_title
    )

    skill_md_path = skill_dir / 'SKILL.md'
    try:
        skill_md_path.write_text(skill_content)
        print("✅ 创建SKILL.md")
    except Exception as e:
        print(f"❌ 创建SKILL.md错误：{e}")
        return None

    # 创建带示例文件的资源目录
    try:
        # 创建scripts/目录和示例脚本
        scripts_dir = skill_dir / 'scripts'
        scripts_dir.mkdir(exist_ok=True)
        example_script = scripts_dir / 'example.py'
        example_script.write_text(EXAMPLE_SCRIPT.format(skill_name=skill_name))
        example_script.chmod(0o755)
        print("✅ 创建scripts/example.py")

        # 创建references/目录和示例参考文档
        references_dir = skill_dir / 'references'
        references_dir.mkdir(exist_ok=True)
        example_reference = references_dir / 'api_reference.md'
        example_reference.write_text(EXAMPLE_REFERENCE.format(skill_title=skill_title))
        print("✅ 创建references/api_reference.md")

        # 创建assets/目录和示例资产占位符
        assets_dir = skill_dir / 'assets'
        assets_dir.mkdir(exist_ok=True)
        example_asset = assets_dir / 'example_asset.txt'
        example_asset.write_text(EXAMPLE_ASSET)
        print("✅ 创建assets/example_asset.txt")
    except Exception as e:
        print(f"❌ 创建资源目录错误：{e}")
        return None

    # 打印后续步骤
    print(f"\n✅ 技能'{skill_name}'在{skill_dir}成功初始化")
    print("\n后续步骤：")
    print("1. 编辑SKILL.md以完成TODO项目并更新描述")
    print("2. 自定义或删除scripts/、references/和assets/中的示例文件")
    print("3. 准备就绪时运行验证器以检查技能结构")

    return skill_dir


def main():
    if len(sys.argv) < 4 or sys.argv[2] != '--path':
        print("用法：init_skill.py <skill-name> --path <path>")
        print("\n技能名称要求：")
        print("  - 连字符大小写标识符（例如，'data-analyzer'）")
        print("  - 仅小写字母、数字和连字符")
        print("  - 最多40个字符")
        print("  - 必须与目录名称完全匹配")
        print("\n示例：")
        print("  init_skill.py my-new-skill --path skills/public")
        print("  init_skill.py my-api-helper --path skills/private")
        print("  init_skill.py custom-skill --path /custom/location")
        sys.exit(1)

    skill_name = sys.argv[1]
    path = sys.argv[3]

    print(f"🚀 初始化技能：{skill_name}")
    print(f"   位置：{path}")
    print()

    result = init_skill(skill_name, path)

    if result:
        sys.exit(0)
    else:
        sys.exit(1)


if __name__ == "__main__":
    main()

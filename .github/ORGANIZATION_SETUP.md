# 组织级别配置分发指南

本文档解答如何在 GitHub 组织内将 Dependabot 和 Workflow 配置分发到多个项目。

## 📋 目录

- [问题 1: 如何分发配置到多个项目](#问题-1-如何分发配置到多个项目)
- [问题 2: Dependabot 分支要求](#问题-2-dependabot-分支要求)
- [问题 3: Dependabot 与检查流程](#问题-3-dependabot-与检查流程)

---

## 问题 1: 如何批量添加配置文件到多个项目

### 需求说明

需要批量给多个项目添加：
- `.github/workflows/dependency-review.yml` - 依赖检查工作流
- `.github/dependabot.yml` - Dependabot 配置

不同项目可能是：
- Maven 项目（`pom.xml`）
- Gradle 项目（`build.gradle` 或 `build.gradle.kts`）
- Scala 项目（`build.sbt`）
- 其他构建工具

### 方案 A: GitHub CLI 批量脚本 ⭐ 推荐

#### 步骤 1: 准备配置文件模板

创建不同构建工具的配置文件模板：

**Maven 项目的 `dependabot.yml`**:
```yaml
version: 2
updates:
  - package-ecosystem: "maven"
    directory: "/"
    schedule:
      interval: "weekly"
    open-pull-requests-limit: 5
    groups:
      spring-boot-dependencies:
        patterns:
          - "org.springframework.boot:*"
          - "org.springframework:*"
        update-types:
          - "minor"
          - "patch"
```

**Gradle 项目的 `dependabot.yml`**:
```yaml
version: 2
updates:
  - package-ecosystem: "gradle"
    directory: "/"
    schedule:
      interval: "weekly"
    open-pull-requests-limit: 5
```

**Scala 项目的 `dependabot.yml`**:
```yaml
version: 2
updates:
  - package-ecosystem: "sbt"
    directory: "/"
    schedule:
      interval: "weekly"
    open-pull-requests-limit: 5
```

#### 步骤 2: 创建批量添加脚本

```bash
#!/bin/bash

# 配置
ORG_NAME="your-org"
BRANCH="main"  # 目标分支（必须是默认分支）
WORKFLOW_FILE=".github/workflows/dependency-review.yml"
DEPENDABOT_FILE=".github/dependabot.yml"

# 检测项目类型的函数
detect_project_type() {
  local repo=$1
  local repo_path="/tmp/$repo"
  
  if [ -f "$repo_path/pom.xml" ]; then
    echo "maven"
  elif [ -f "$repo_path/build.gradle" ] || [ -f "$repo_path/build.gradle.kts" ]; then
    echo "gradle"
  elif [ -f "$repo_path/build.sbt" ]; then
    echo "sbt"
  else
    echo "unknown"
  fi
}

# 生成对应类型的 dependabot.yml
generate_dependabot_config() {
  local project_type=$1
  local output_file=$2
  
  case $project_type in
    maven)
      cat > "$output_file" << 'EOF'
version: 2
updates:
  - package-ecosystem: "maven"
    directory: "/"
    schedule:
      interval: "weekly"
    open-pull-requests-limit: 5
    groups:
      spring-boot-dependencies:
        patterns:
          - "org.springframework.boot:*"
          - "org.springframework:*"
        update-types:
          - "minor"
          - "patch"
EOF
      ;;
    gradle)
      cat > "$output_file" << 'EOF'
version: 2
updates:
  - package-ecosystem: "gradle"
    directory: "/"
    schedule:
      interval: "weekly"
    open-pull-requests-limit: 5
EOF
      ;;
    sbt)
      cat > "$output_file" << 'EOF'
version: 2
updates:
  - package-ecosystem: "sbt"
    directory: "/"
    schedule:
      interval: "weekly"
    open-pull-requests-limit: 5
EOF
      ;;
    *)
      echo "未知项目类型，跳过"
      return 1
      ;;
  esac
}

# 主流程
main() {
  # 获取组织下所有仓库
  echo "获取组织 $ORG_NAME 下的所有仓库..."
  repos=$(gh repo list $ORG_NAME --limit 1000 --json name -q '.[].name')
  
  for repo in $repos; do
    echo ""
    echo "========================================="
    echo "处理仓库: $repo"
    echo "========================================="
    
    # 克隆仓库
    echo "克隆仓库..."
    gh repo clone $ORG_NAME/$repo /tmp/$repo 2>/dev/null || {
      echo "⚠️  克隆失败，跳过"
      continue
    }
    
    cd /tmp/$repo || continue
    
    # 切换到目标分支
    git checkout $BRANCH 2>/dev/null || {
      echo "⚠️  分支 $BRANCH 不存在，跳过"
      cd ..
      rm -rf /tmp/$repo
      continue
    }
    
    # 检测项目类型
    project_type=$(detect_project_type $repo)
    echo "检测到项目类型: $project_type"
    
    if [ "$project_type" == "unknown" ]; then
      echo "⚠️  无法识别项目类型，跳过"
      cd ..
      rm -rf /tmp/$repo
      continue
    fi
    
    # 检查是否已存在配置文件
    if [ -f "$WORKFLOW_FILE" ] && [ -f "$DEPENDABOT_FILE" ]; then
      echo "✅ 配置文件已存在，跳过"
      cd ..
      rm -rf /tmp/$repo
      continue
    fi
    
    # 创建 .github 目录
    mkdir -p .github/workflows
    
    # 添加 workflow 文件（通用，适用于所有项目）
    if [ ! -f "$WORKFLOW_FILE" ]; then
      echo "添加 workflow 文件..."
      cp /path/to/template/dependency-review.yml "$WORKFLOW_FILE"
    fi
    
    # 生成并添加 dependabot.yml（根据项目类型）
    if [ ! -f "$DEPENDABOT_FILE" ]; then
      echo "生成 $project_type 类型的 dependabot.yml..."
      generate_dependabot_config $project_type "$DEPENDABOT_FILE"
    fi
    
    # 检查是否有变更
    if git diff --quiet && git diff --cached --quiet; then
      echo "✅ 无变更，跳过提交"
      cd ..
      rm -rf /tmp/$repo
      continue
    fi
    
    # 创建新分支
    branch_name="chore/add-dependency-config-$(date +%s)"
    git checkout -b $branch_name
    
    # 提交变更
    git add .github/
    git commit -m "chore: add dependency review workflow and dependabot config
    
    - Add dependency-review.yml workflow
    - Add dependabot.yml for $project_type project
    - Auto-generated by batch script"
    
    # 推送并创建 PR
    git push origin $branch_name
    gh pr create \
      --title "Add dependency review workflow and dependabot config" \
      --body "自动添加依赖检查配置
    
    - 项目类型: $project_type
    - 添加了 dependency-review.yml 工作流
    - 添加了 dependabot.yml 配置
    
    请审查后合并到 $BRANCH 分支。" \
      --base $BRANCH
    
    echo "✅ 已创建 PR"
    
    # 清理
    cd ..
    rm -rf /tmp/$repo
  done
  
  echo ""
  echo "========================================="
  echo "批量处理完成！"
  echo "========================================="
}

# 运行主函数
main
```

#### 步骤 3: 使用脚本

```bash
# 安装 GitHub CLI（如果未安装）
# macOS: brew install gh
# Linux: 参考 https://cli.github.com/

# 登录 GitHub
gh auth login

# 设置执行权限
chmod +x batch-add-config.sh

# 修改脚本中的配置
# ORG_NAME="your-org"
# 准备 workflow 模板文件路径

# 运行脚本
./batch-add-config.sh
```

---

### 方案 B: 使用 GitHub API + Python 脚本

#### 步骤 1: 创建模板仓库

1. 创建一个仓库，包含标准配置
2. 在仓库设置中标记为 **Template repository**

#### 步骤 2: 基于模板创建新仓库

创建新仓库时选择 "Use this template"

**优点**:
- ✅ 新项目自动包含配置

**缺点**:
- ❌ 已有项目需要手动添加
- ❌ 配置更新需要手动同步到各个项目

---

### 方案 C: 自动化脚本批量分发

使用 GitHub API 批量推送配置到所有仓库。

#### 示例脚本

```bash
#!/bin/bash

ORG_NAME="your-org"
CONFIG_REPO=".github"  # 配置仓库名
BRANCH="main"

# 获取组织下所有仓库
repos=$(gh repo list $ORG_NAME --limit 1000 --json name -q '.[].name')

for repo in $repos; do
  echo "处理仓库: $repo"
  
  # 克隆仓库
  gh repo clone $ORG_NAME/$repo /tmp/$repo
  
  cd /tmp/$repo
  
  # 创建 .github 目录
  mkdir -p .github/workflows
  
  # 复制配置文件
  cp /path/to/config-repo/.github/workflows/dependency-review.yml .github/workflows/
  cp /path/to/config-repo/.github/dependabot.yml .github/
  
  # 提交并推送
  git checkout -b add-dependency-config
  git add .github/
  git commit -m "chore: add dependency review workflow and dependabot config"
  git push origin add-dependency-config
  
  # 创建 PR（可选）
  gh pr create --title "Add dependency review workflow" --body "自动添加依赖检查配置"
  
  cd ..
  rm -rf /tmp/$repo
done
```

**优点**:
- ✅ 可以批量处理已有项目
- ✅ 可以自定义每个项目的配置

**缺点**:
- ❌ 需要维护脚本
- ❌ 配置更新需要重新运行脚本

---

### 方案 D: GitHub App + 自动化

创建一个 GitHub App，自动为新仓库添加配置。

**优点**:
- ✅ 完全自动化
- ✅ 新仓库自动配置

**缺点**:
- ❌ 开发成本高
- ❌ 需要维护 App

---

## 问题 2: Dependabot 分支要求

### Dependabot.yml 文件位置

**重要**: `dependabot.yml` 文件必须位于仓库的**默认分支**（通常是 `main` 或 `master`）。

### 默认分支配置

Dependabot 会：
1. 读取默认分支的 `dependabot.yml` 配置
2. 基于默认分支创建更新 PR
3. 检查默认分支的依赖

### 如何查看和修改默认分支

1. 进入仓库 **Settings** → **General**
2. 在 **Default branch** 部分查看当前默认分支
3. 可以点击 **Switch to another branch** 修改默认分支

### 在测试分支测试 Dependabot

**重要限制**: Dependabot 只在默认分支生效，无法在测试分支直接测试。

但是你可以：

#### 方法 1: 临时修改默认分支（不推荐）

1. 将测试分支设为默认分支
2. 等待 Dependabot 运行（或手动触发）
3. 测试完成后改回原默认分支

**缺点**: 会影响其他开发者，不推荐。

#### 方法 2: 合并到默认分支后测试（推荐）

1. 将 `dependabot.yml` 和测试代码合并到默认分支
2. Dependabot 会自动检测并创建修复 PR
3. 查看修复 PR 的效果

#### 方法 3: 手动触发 Dependabot 检查

虽然无法在非默认分支运行 Dependabot，但可以：

1. **手动触发依赖图更新**:
   - 推送到默认分支
   - GitHub 会自动扫描依赖
   - 等待几分钟让依赖图生成

2. **查看 Dependabot Alerts**:
   - 进入仓库 **Security** → **Dependabot alerts**
   - 查看检测到的漏洞
   - 点击漏洞可以查看修复建议

3. **手动创建修复 PR**（模拟 Dependabot）:
   - 查看漏洞详情中的修复版本
   - 手动更新依赖版本
   - 创建 PR 查看效果

### 多分支支持

虽然 `dependabot.yml` 必须在默认分支，但你可以：

1. **为不同目录配置不同的更新策略**:
```yaml
updates:
  - package-ecosystem: "maven"
    directory: "/"
    target-branch: "main"  # 指定目标分支
    schedule:
      interval: "weekly"
```

2. **Dependabot Security Updates** 会自动检测所有分支的漏洞，但修复 PR 会基于默认分支创建。

---

## 问题 3: Dependabot 与检查流程

### Dependabot 创建的 PR 会触发检查吗？

**答案**: 是的，但需要特殊配置。

### 默认行为

当 Dependabot 创建 PR 时：
- ✅ 会触发 `pull_request` 事件
- ✅ 会运行配置的 workflow
- ⚠️ **但是**: `GITHUB_TOKEN` 默认只有**只读权限**
- ⚠️ **但是**: 无法访问 GitHub Actions Secrets

### 如何让 Dependabot PR 参与完整检查流程

#### 步骤 1: 在工作流中增加权限

```yaml
name: Dependency Review

on:
  pull_request:
    types: [opened, synchronize, reopened]

permissions:
  contents: read
  pull-requests: write      # 需要写入权限来创建评论
  security-events: write
  checks: write              # 需要写入权限来创建 Check Run

jobs:
  dependency-review:
    runs-on: ubuntu-latest
    # 如果是 Dependabot 触发的，需要特殊处理
    if: github.actor != 'dependabot[bot]' || github.event_name == 'pull_request'
    steps:
      - uses: actions/checkout@v4
      # ... 其他步骤
```

#### 步骤 2: 处理 Dependabot 的特殊权限

```yaml
jobs:
  dependency-review:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
        with:
          # Dependabot PR 需要特殊配置
          token: ${{ secrets.GITHUB_TOKEN }}
      
      - name: Dependency Review
        uses: actions/dependency-review-action@v4
        # 这个 action 会自动处理 Dependabot PR
```

#### 步骤 3: 使用 Dependabot Secrets（如果需要）

如果 workflow 需要访问 Secrets：

1. 在仓库 **Settings** → **Secrets and variables** → **Actions**
2. 创建 **Dependabot secrets**（不是普通的 Secrets）
3. 在工作流中使用：

```yaml
- name: Use secret
  env:
    API_KEY: ${{ secrets.DEPENDABOT_API_KEY }}  # Dependabot secrets 前缀
  run: echo "Using API key"
```

### 当前配置的检查流程

查看 `dependency-review.yml`，它已经配置为：

1. ✅ 监听 `pull_request` 事件（包括 Dependabot 创建的 PR）
2. ✅ 有 `pull-requests: write` 权限（可以创建评论）
3. ✅ 有 `checks: write` 权限（可以创建 Check Run）
4. ✅ 使用 `dependency-review-action`（自动处理 Dependabot PR）

**结论**: 当前配置已经可以让 Dependabot 创建的 PR 参与检查流程。

### 验证 Dependabot PR 是否触发检查

1. Dependabot 创建 PR 后
2. 查看 PR 页面的 **Checks** 标签
3. 应该能看到 "Dependency Review" 检查运行
4. 如果有漏洞，会看到失败的检查和相关评论

---

## 手动触发 Dependabot 和查看修复 PR

### 如何手动触发 Dependabot

#### 方法 1: 通过 GitHub UI 触发（最简单）

1. **确保配置在默认分支**:
   - `dependabot.yml` 必须在 `main` 或 `master` 分支
   - 如果当前在测试分支，需要先合并到默认分支

2. **触发依赖图扫描**:
   - 进入仓库 **Settings** → **Code security and analysis**
   - 找到 **Dependabot alerts** 部分
   - 点击 **Check for updates** 按钮
   - 等待几分钟让 GitHub 扫描依赖

3. **查看 Dependabot Alerts**:
   - 进入 **Security** → **Dependabot alerts**
   - 查看检测到的漏洞列表
   - 每个漏洞会显示：
     - 漏洞名称和 CVE/GHSA ID
     - 严重程度（Critical/High/Moderate/Low）
     - 受影响的依赖和版本
     - **建议的修复版本**

4. **手动触发 Security Update**:
   - 在 Dependabot alerts 页面
   - 点击漏洞右侧的 **Create Dependabot security update** 按钮
   - Dependabot 会自动创建修复 PR

#### 方法 2: 通过 GitHub API 触发

```bash
# 查看仓库的依赖图状态
gh api repos/:owner/:repo/dependency-graph/sbom

# 注意：GitHub 会自动扫描，无法直接 API 触发
# 但可以通过推送代码到默认分支来触发扫描
```

#### 方法 3: 模拟 Dependabot PR（查看格式）

如果你想看看 Dependabot 创建的 PR 长什么样，可以手动创建一个：

```bash
# 1. 查看漏洞详情和修复版本
# 在 Security → Dependabot alerts 中查看

# 2. 切换到默认分支
git checkout main  # 或 master

# 3. 创建修复分支（使用 Dependabot 的命名格式）
git checkout -b dependabot/maven/com.google.guava-guava-32.1.3-jre

# 4. 更新依赖版本（例如：guava 18.0 -> 32.1.3-jre）
# 修改 pom.xml 或 build.gradle

# 5. 提交（使用 Dependabot 的提交格式）
git commit -m "Bump guava from 18.0 to 32.1.3-jre

Bumps [guava](https://github.com/google/guava) from 18.0 to 32.1.3-jre.
- [Release notes](https://github.com/google/guava/releases)
- [Commits](https://github.com/google/guava/compare/v18.0...v32.1.3-jre)

---
updated-dependencies:
- dependency-name: com.google.guava:guava
  dependency-type: direct:production
  update-type: version-update:semver-major
..."

# 6. 推送并创建 PR
git push origin dependabot/maven/com.google.guava-guava-32.1.3-jre
gh pr create \
  --title "Bump guava from 18.0 to 32.1.3-jre" \
  --body "## Changes

- Updated \`com.google.guava:guava\` from \`18.0\` to \`32.1.3-jre\`

## Security

This PR addresses security vulnerabilities:
- CVE-XXXX-XXXXX: Description

## Release Notes

See [release notes](https://github.com/google/guava/releases/tag/v32.1.3-jre)

## Checklist

- [ ] Tests pass
- [ ] No breaking changes"
```

### Dependabot PR 的典型格式

Dependabot 创建的 PR 通常包含：

#### 1. 标题格式
```
Bump [package-name] from [old-version] to [new-version]
```

示例：
- `Bump guava from 18.0 to 32.1.3-jre`
- `Bump log4j-core from 2.11.0 to 2.17.1`
- `Bump jackson-databind from 2.9.8 to 2.15.2`

#### 2. PR 描述包含

- **Changes**: 依赖更新说明
- **Security**: 安全漏洞信息（如果是安全更新）
  - CVE/GHSA ID
  - 漏洞描述
  - 严重程度
- **Release Notes**: 链接到新版本的发布说明
- **Changelog**: 变更日志链接
- **Compatibility**: 兼容性说明
- **Dependencies**: 依赖关系图

#### 3. 自动标签

- `dependencies` - 依赖更新
- `security` - 安全更新（如果是 Security Update）
- `java` / `maven` / `gradle` - 根据项目类型

#### 4. 自动检查

- CI/CD 检查会自动运行
- Dependency Review 检查会运行（如果配置了）
- 代码质量检查（如果配置了）

#### 5. PR 内容示例

```markdown
## Changes

- Updated `com.google.guava:guava` from `18.0` to `32.1.3-jre`

## Security

This PR addresses security vulnerabilities:
- **CVE-2023-2976**: Deserialization vulnerability in Guava
  - Severity: High
  - Fixed in: 32.0.0

## Release Notes

See [release notes](https://github.com/google/guava/releases/tag/v32.1.3-jre)

## Dependencies

- Direct dependency: `com.google.guava:guava@32.1.3-jre`
- Transitive dependencies updated: 0

## Checklist

- [x] Tests pass
- [x] No breaking changes
```

### 在测试分支查看 Dependabot 效果

虽然 Dependabot 只在默认分支运行，但你可以：

#### 方法 1: 查看其他仓库的 Dependabot PR

1. 访问组织内其他已配置 Dependabot 的仓库
2. 在 Pull requests 页面筛选：
   - 作者: `dependabot[bot]`
   - 标签: `dependencies` 或 `security`
3. 查看 PR 的结构和格式

#### 方法 2: 合并到默认分支后观察

1. 将测试代码合并到默认分支
2. 等待 Dependabot 自动检测（可能需要几小时到一天）
3. 或手动触发 "Check for updates"
4. 查看创建的修复 PR

#### 方法 3: 使用 GitHub Actions 模拟

创建一个 workflow 来模拟 Dependabot 的行为：

```yaml
name: Simulate Dependabot

on:
  workflow_dispatch:
    inputs:
      package:
        description: 'Package name'
        required: true
      old_version:
        description: 'Old version'
        required: true
      new_version:
        description: 'New version'
        required: true

jobs:
  create-pr:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Update dependency
        run: |
          # 更新依赖版本
          # ...
      - name: Create PR
        uses: peter-evans/create-pull-request@v5
        with:
          title: "Bump ${{ inputs.package }} from ${{ inputs.old_version }} to ${{ inputs.new_version }}"
          body: |
            ## Changes
            - Updated `${{ inputs.package }}` from `${{ inputs.old_version }}` to `${{ inputs.new_version }}`
          branch: dependabot/maven/${{ inputs.package }}-${{ inputs.new_version }}
```

---

## Dependabot PR 管理行为

### 如果 PR 一直不合并会怎样？

#### 核心行为

**Dependabot 不会为同一依赖创建多个 PR**：

1. **更新现有 PR**:
   - 如果依赖有新的更新版本可用
   - Dependabot 会**更新现有的 PR**，而不是创建新的 PR
   - 会在现有 PR 中添加新的 commit，更新到最新版本

2. **不会创建新 PR**:
   - 只要现有 PR 保持打开状态
   - Dependabot 不会为同一依赖创建第二个 PR
   - 除非手动关闭现有 PR

3. **PR 数量限制**:
   - `open-pull-requests-limit` 配置限制了同时打开的 PR 总数
   - 如果达到限制，Dependabot 会等待现有 PR 合并后再创建新的

#### 示例场景

**场景 1: 版本更新**

```
初始状态: guava 18.0
Dependabot 创建 PR: guava 18.0 → 20.0 (PR #1)
你未合并 PR #1

一周后，guava 发布 21.0:
Dependabot 行为: 更新 PR #1，添加 commit: guava 20.0 → 21.0
结果: PR #1 现在更新 guava 18.0 → 21.0
```

**场景 2: 安全更新**

```
初始状态: log4j-core 2.11.0 (有漏洞)
Dependabot Security Update 创建 PR: log4j-core 2.11.0 → 2.17.1 (PR #2)
你未合并 PR #2

如果发现新的安全漏洞或修复版本:
Dependabot 行为: 更新 PR #2 到最新安全版本
结果: PR #2 更新到最新修复版本
```

**场景 3: 达到 PR 限制**

```
配置: open-pull-requests-limit: 5
当前状态: 已有 5 个打开的 Dependabot PR

Dependabot 行为:
- 不会创建新的 PR
- 会更新现有的 PR（如果有新版本）
- 等待现有 PR 合并后，再创建新的 PR
```

**场景 4: 手动修复依赖后合并到 master**

```
初始状态: log4j-core 2.11.0 (有漏洞)
Dependabot 创建 PR: log4j-core 2.11.0 → 2.17.1 (PR #3)
你未合并 PR #3

你在开发分支手动修复:
- 更新 log4j-core 2.11.0 → 2.17.1
- 合并到 master 分支

Dependabot 下次执行时:
✅ 检测到 master 分支的 log4j-core 已经是 2.17.1
✅ 自动关闭 PR #3（因为依赖已经更新）
✅ 添加评论说明："This pull request has been automatically closed because the dependency has been updated."
```

**重要**: Dependabot 会：
- 检查默认分支（master/main）的当前依赖版本
- 如果依赖已经更新到修复版本或更高版本
- **自动关闭相关的 PR**
- 在 PR 中添加关闭说明

### 如何控制 Dependabot 行为

#### 1. 配置 PR 数量限制

```yaml
updates:
  - package-ecosystem: "maven"
    open-pull-requests-limit: 5  # 最多同时打开 5 个 PR
```

**建议**:
- 小项目: 3-5 个
- 中等项目: 5-10 个
- 大项目: 10-20 个

#### 2. 使用依赖分组

```yaml
groups:
  spring-boot-dependencies:
    patterns:
      - "org.springframework.boot:*"
    update-types:
      - "minor"
      - "patch"
```

**效果**:
- 多个相关依赖合并到一个 PR
- 减少 PR 数量
- 更容易管理和审查

#### 3. 自动合并策略

可以使用 GitHub Actions 自动合并符合条件的 PR：

```yaml
name: Auto-merge Dependabot

on:
  pull_request:
    types: [opened, synchronize]

jobs:
  auto-merge:
    if: github.actor == 'dependabot[bot]'
    runs-on: ubuntu-latest
    steps:
      - name: Auto-merge
        uses: fastify/github-action-merge-dependabot@v3
        with:
          github-token: ${{ secrets.GITHUB_TOKEN }}
          # 只自动合并 patch 版本更新
          target: minor
          # 需要所有检查通过
          merge-method: squash
```

#### 4. 手动管理 PR

**关闭不需要的 PR**:
- 如果某个依赖更新不需要，可以关闭 PR
- Dependabot 不会重新创建（除非有新的安全更新）

**合并 PR**:
- 合并后，Dependabot 会继续监控该依赖
- 如果有新版本，会创建新的 PR

**手动修复依赖**:
- 如果在开发分支手动更新了依赖版本
- 合并到 master 后，Dependabot 会自动检测
- **会自动关闭相关的 PR**（如果依赖已经更新到修复版本或更高）
- PR 会显示："This pull request has been automatically closed because the dependency has been updated."

### 安全更新（Security Updates）的特殊行为

**重要**: 安全更新不受 `open-pull-requests-limit` 限制！

- 每个安全漏洞会**单独创建 PR**
- 即使达到 PR 限制，安全更新仍会创建
- 安全更新的优先级更高

**示例**:
```
配置: open-pull-requests-limit: 5
当前状态: 已有 5 个版本更新 PR

发现新的安全漏洞:
Dependabot 行为: 仍然创建安全更新 PR（不受限制）
结果: 现在有 6 个打开的 PR（5 个版本更新 + 1 个安全更新）
```

### 最佳实践

1. **定期审查和合并 PR**:
   - 每周审查一次 Dependabot PR
   - 优先合并安全更新 PR
   - 合并版本更新 PR（如果测试通过）

2. **合理设置 PR 限制**:
   - 根据团队规模和处理能力设置
   - 避免 PR 积压过多

3. **使用依赖分组**:
   - 减少 PR 数量
   - 提高管理效率

4. **配置自动合并**（可选）:
   - 对于低风险的 patch 版本更新
   - 可以配置自动合并
   - 但需要确保有足够的测试覆盖

---

## 📝 最佳实践总结

### 组织级别配置分发

1. **推荐方案**: 使用**可重用工作流**
   - 创建一个 `.github` 配置仓库
   - 定义可重用工作流
   - 各项目引用该工作流

2. **批量更新**: 使用脚本批量推送配置到已有项目

3. **新项目**: 使用模板仓库自动包含配置

### Dependabot 配置

1. **文件位置**: 必须在默认分支（`main` 或 `master`）
2. **目标分支**: 可以在 `dependabot.yml` 中指定 `target-branch`
3. **检查流程**: Dependabot PR 会自动触发 workflow，但需要正确配置权限

### 检查流程集成

1. **权限配置**: 确保 workflow 有 `pull-requests: write` 和 `checks: write` 权限
2. **Dependabot Secrets**: 如果需要访问 Secrets，使用 Dependabot Secrets
3. **自动处理**: `dependency-review-action` 会自动处理 Dependabot PR

---

## 🔗 参考资源

- [可重用工作流文档](https://docs.github.com/en/actions/using-workflows/reusing-workflows)
- [Dependabot 配置文档](https://docs.github.com/en/code-security/dependabot/dependabot-version-updates/configuration-options-for-the-dependabot.yml-file)
- [Dependabot 与 GitHub Actions](https://docs.github.com/en/code-security/dependabot/working-with-dependabot/automating-dependabot-with-github-actions)
- [GitHub API 文档](https://docs.github.com/en/rest)


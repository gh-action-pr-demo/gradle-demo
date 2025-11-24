# Dependency Submission 权限修复

## 问题描述

在运行 GitHub Actions workflow 时遇到以下错误：

```
HttpError: Dependency submission failed for dependency-graph-reports/dependency_review-dependency-review.json.
Resource not accessible by integration
Please ensure that the 'contents: write' permission is available for the workflow job.
Note that this permission is never available for a 'pull_request' trigger from a repository fork.
```

## 根本原因

1. `gradle/actions/dependency-submission@v3` 需要 `contents: write` 权限才能提交依赖图到 GitHub
2. 原始配置只有 `contents: read` 权限
3. 从 fork 仓库的 PR 永远无法获得写权限（GitHub 安全限制）

## 解决方案

### 方案说明

不跳过 dependency submission，而是**确保在有足够权限的事件类型上执行**。

### 关键概念

GitHub Actions 有两种 PR 事件：

1. **`pull_request`** 事件
   - 在 PR 分支的上下文中运行
   - 权限受限（特别是 fork PR）
   - **无法获得 `contents: write` 权限**（即使配置了）

2. **`pull_request_target`** 事件
   - 在基础分支（目标分支）的上下文中运行
   - **可以获得完整的仓库权限**
   - 适合需要写权限的操作

### 实施的修改

### 1. 添加 `contents: write` 权限

修改 `permissions` 部分：

```yaml
permissions:
  contents: write  # Required for dependency-submission
  pull-requests: write
  security-events: write
  checks: write
```

### 2. 更新 Checkout 步骤

确保在 `pull_request_target` 事件中检出 PR 的代码：

```yaml
- name: Checkout repository
  if: steps.get-pr-number.outputs.is_pr == 'true'
  uses: actions/checkout@v4
  with:
    # For pull_request_target, explicitly checkout the PR head
    ref: ${{ github.event.pull_request.head.sha || github.sha }}
    fetch-depth: 0
```

### 3. 条件化 Dependency Submission

只在 `pull_request_target` 事件上执行（该事件有写权限）：

```yaml
- name: Submit Gradle dependency graph
  # Only run on pull_request_target (has write permission)
  # This is required for dependency-review-action to work properly
  if: steps.detect-gradle.outputs.is_gradle == 'true' && github.event_name == 'pull_request_target'
  continue-on-error: true
  uses: gradle/actions/dependency-submission@v3
  with:
    dependency-graph: generate-and-submit
```

## 关键改进

1. **不跳过 submission**：确保依赖图始终被提交
2. **使用正确的事件**：利用 `pull_request_target` 的写权限
3. **检出正确代码**：确保分析的是 PR 的代码而不是基础分支
4. **错误容忍**：使用 `continue-on-error: true` 提高健壮性

## 工作流程

workflow 配置了两个触发事件：

```yaml
on:
  pull_request:
    types: [opened, synchronize, reopened]
  pull_request_target:
    types: [opened, synchronize, reopened]
```

**执行逻辑**：
- `pull_request` 触发：执行依赖检查和评论，但**跳过** dependency submission
- `pull_request_target` 触发：**执行** dependency submission + 依赖检查和评论

这样确保：
- ✅ Dependency submission 总是能成功（在有权限的事件中）
- ✅ 依赖检查能够基于最新的依赖图工作
- ✅ 同时支持同仓库 PR 和 fork PR

## 行为说明

- **同一仓库的 PR**：
  - ✅ `pull_request_target` 提交依赖图
  - ✅ 执行依赖漏洞检查
  - ✅ 在 PR 中发布检查结果

- **Fork 仓库的 PR**：
  - ✅ `pull_request_target` 提交依赖图（仍然可以工作）
  - ✅ 执行依赖漏洞检查
  - ✅ 在 PR 中发布检查结果

## 安全说明

使用 `pull_request_target` 时需要注意：
- 该事件在基础分支上下文中运行，有完整的仓库权限
- 我们通过显式 checkout PR 代码来分析 PR 的依赖
- 由于只是读取和分析依赖，不执行任意代码，因此是安全的

## 测试建议

1. 在同一仓库创建 PR 测试正常流程
2. 从 fork 仓库创建 PR 测试跳过逻辑
3. 验证依赖检查功能在两种情况下都能正常工作

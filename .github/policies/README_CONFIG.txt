# 策略配置说明

## 配置文件位置

`.github/policies/config.txt`

## 配置项

### 1. fail_on_severity

控制 `dependency-review-action` 在什么严重程度下使构建失败。

**可选值**：
- `critical` - 仅 critical 级别漏洞会导致失败
- `high` - high 及以上级别会导致失败
- `moderate` - moderate 及以上级别会导致失败
- `low` - 所有级别都会导致失败

**默认值**：`high`

**示例**：
```
fail_on_severity: high
```

### 2. min_severity

控制策略过滤器报告的最低严重程度。只有达到或超过此级别的漏洞才会在 PR 评论中显示。

**可选值**：
- `critical` - 仅报告 critical 级别
- `high` - 报告 high 和 critical 级别
- `moderate` - 报告 moderate、high 和 critical 级别
- `low` - 报告所有级别

**默认值**：`critical`

**示例**：
```
min_severity: critical
```

## 完整配置示例

```
# Dependency Review Configuration

# 构建失败阈值
fail_on_severity: high

# 策略过滤最低严重程度
min_severity: critical
```

## 使用场景

### 场景 1：严格模式
只关注最严重的漏洞：
```
fail_on_severity: critical
min_severity: critical
```

### 场景 2：平衡模式（推荐）
构建在 high 级别失败，但只报告 critical 级别的策略违规：
```
fail_on_severity: high
min_severity: critical
```

### 场景 3：宽松模式
捕获更多漏洞：
```
fail_on_severity: moderate
min_severity: high
```

## 上游策略管理

如果使用 GitHub 仓库作为上游策略源：

1. 在策略仓库中创建 `config.txt`
2. 设置 workflow 环境变量：
   ```yaml
   env:
     POLICY_SOURCE: github
     POLICY_REPO: your-org/dependency-policies
   ```
3. 配置会自动从上游仓库读取

## 注意事项

- 配置文件使用简单的 `key: value` 格式
- 以 `#` 开头的行是注释
- 如果配置文件不存在或解析失败，会使用默认值
- 配置更改会在下次 PR 触发时生效

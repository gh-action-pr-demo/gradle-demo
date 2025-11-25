# Grype 集成与使用说明

本文档描述如何在该 Gradle 项目中使用 [Grype](https://github.com/anchore/grype) 进行漏洞扫描，以及 GitHub Actions 工作流的实现细节和本地调试方法。

## Grype 是什么

Grype 是 Anchore 维护的开源漏洞扫描器，支持扫描容器镜像、文件系统目录以及 CycloneDX、SPDX 等格式的 SBOM。其漏洞数据库整合了 NVD、GitHub Advisory、OSV、Red Hat 等多个来源，默认每日自动更新。Grype 的特点包括：

- **多生态支持**：涵盖 Java/Gradle、npm、PyPI、操作系统包等多种生态。
- **SBOM 优先**：可直接扫描由 Syft 等工具生成的 CycloneDX SBOM，降低误报。
- **可配置阈值**：支持 `--fail-on` 或 `fail-on-severity` 控制失败级别。
- **离线/缓存能力**：数据库可缓存在 Runner 或本地，便于重复扫描。

## GitHub Actions 工作流 (`.github/workflows/grype-scan.yml`)

该工作流在 PR 打开/同步/重新开启以及手动触发时运行，流程如下：

1. **构建上下文**：使用 Temurin JDK 17 与 `gradle/actions/setup-gradle@v3`，执行 `./gradlew clean build`，保证依赖被解析并写入 `build/`.
2. **SBOM 生成**：通过 `anchore/sbom-action@v0`（底层是 Syft）生成 `sbom.cdx.json`。
3. **数据库缓存**：`actions/cache@v4` 缓存 `~/.cache/grype/db`，减少重复下载。
4. **Grype 扫描**：`anchore/grype-action@v1` 对 SBOM 执行扫描，`fail-on-severity: high`，若出现 High/Critical 漏洞即让工作流失败。
5. **结果产出**：SBOM 与 `grype-report.json` 通过 `actions/upload-artifact@v4` 上传，并在步骤摘要中提示下载路径。

如需调整严重级别或扫描方式，可编辑工作流中的以下字段：

```yaml
with:
  scan-type: sbom          # 可改为 dir
  sbom: sbom.cdx.json      # 改为需要扫描的路径
  fail-on-severity: high   # 可改为 critical / medium / low / negligible
```

若需要离线数据库，可在 Runner 预先挂载更新好的 DB，或把 `GRYPE_DB_CACHE_DIR` 指向共享卷。

## 本地运行 Grype

1. **安装**
   - macOS（Homebrew）：`brew install anchore/grype/grype`
   - 脚本：`curl -sSfL https://raw.githubusercontent.com/anchore/grype/main/install.sh | sh -s -- -b /usr/local/bin`

2. **生成 SBOM（推荐）**
   ```bash
   brew install anchore/syft/syft   # 若尚未安装
   syft dir:. -o cyclonedx-json > sbom.cdx.json
   ```

3. **执行扫描**
   ```bash
   grype sbom:sbom.cdx.json --fail-on high --add-cpes-if-none
   ```
   或直接扫描目录 / 构建产物：
   ```bash
   grype dir:build/libs --fail-on high
   ```

4. **数据库管理**
   - 更新数据库：`grype db update`
   - 使用缓存：`GRYPE_DB_CACHE_DIR=~/.cache/grype grype ...`

## 与现有 dependency-review 的关系

- `dependency-review-action` 继续提交 Gradle 依赖图，适合检测**新增依赖差异**。
- Grype 则基于 SBOM 做完整扫描，可发现 baseline 中已有的高危漏洞，弥补前者的盲区。
- 两者可并行使用：如果依赖图提交异常，Grype 仍能给出完整漏洞结果。

## 常见问题

| 场景 | 处理方式 |
| ---- | -------- |
| 需要不同阈值 | 修改工作流中的 `fail-on-severity` |
| 网络受限 | 预热 `~/.cache/grype/db`，并在 `actions/cache` 中共享 |
| 只想扫描特定模块 | 调整 SBOM 生成命令或直接扫描目标目录 |

如需进一步定制（例如把报告转成 SARIF、推送到 Security tab），可在 Grype 步骤后增加 `github/codeql-action/upload-sarif`。


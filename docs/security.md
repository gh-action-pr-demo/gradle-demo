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
4. **Grype 扫描**：在 Runner 内安装 Grype CLI 并执行 `grype sbom:sbom.cdx.json --fail-on $GRYPE_FAIL_ON_SEVERITY --add-cpes-if-none -o json`，默认阈值 `high`（可通过环境变量 `GRYPE_FAIL_ON_SEVERITY` 配置）。命中阈值时返回码为 2，但工作流会继续生成报告与评论。
5. **结果产出**：一方面仍可上传 SBOM 与 JSON 报告供离线分析；另一方面，Python 汇总脚本会把严重等级分布与 Top 依赖写入 Step Summary，并在 PR 中自动发表评论，做到“无需下载 artifact 也能查看结果”。

如需调整严重级别或扫描方式，可修改以下位置：

- `GRYPE_FAIL_ON_SEVERITY` 环境变量：控制 `--fail-on` 的级别（critical / high / medium / low / negligible / none）。
- `anchore/sbom-action@v0` 的 `path`/`format`/`output-file`，或直接改为其它 SBOM 生成方式。
- 如果希望 Grype 直接扫描目录，可把命令替换为 `grype dir:build/libs ...` 并同步更新评论脚本使用的输入路径。

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
| 需要不同阈值 | 修改 `GRYPE_FAIL_ON_SEVERITY` （示例：`critical`） |
| 网络受限 | 预热 `~/.cache/grype/db`，并在 `actions/cache` 中共享 |
| 只想扫描特定模块 | 调整 SBOM 生成命令或直接扫描目标目录 |
| 不想重复评论 | 在 GitHub Script 中查找历史评论并更新（可后续扩展） |

如需进一步定制（例如把报告转成 SARIF、推送到 Security tab），可在 Grype 步骤后增加 `github/codeql-action/upload-sarif`。


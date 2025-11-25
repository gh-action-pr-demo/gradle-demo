# Gradle Demo - GitHub Action 漏洞检测演示

这是一个简单的 Gradle 项目，用于演示 GitHub Actions 识别依赖库漏洞。

## 项目结构

```
gradle-demo/
├── build.gradle          # Gradle 构建配置
├── settings.gradle       # Gradle 设置
├── gradlew              # Gradle Wrapper 脚本 (Unix)
├── gradlew.bat          # Gradle Wrapper 脚本 (Windows)
├── gradle/              # Gradle Wrapper 配置
└── src/
    ├── main/
    │   ├── java/com/example/demo/
    │   │   └── App.java
    │   └── resources/
    │       └── log4j2.xml
    └── test/
        └── java/com/example/demo/
            └── AppTest.java
```

## 依赖说明

核心依赖及其用途：

- `org.apache.logging.log4j:log4j-core:2.10.0` —— Log4Shell 漏洞复现
- `org.apache.commons:commons-text:1.9` —— Text4Shell 漏洞复现
- `com.fasterxml.jackson.core:jackson-databind:2.10.0`
- `com.alibaba:fastjson:1.2.80`
- `commons-collections:commons-collections:3.2.1`
- `com.google.guava:guava:30.1-jre`
- 测试：`org.junit.jupiter:junit-jupiter-*:5.8.1`

## 构建和运行

### 构建项目
```bash
./gradlew build
```

### 运行应用
```bash
./gradlew run
```

### 运行测试
```bash
./gradlew test
```

## 漏洞扫描方案

### Dependency Review（已存在）

- 工作流：`.github/workflows/dependency-review.yml`
- 功能：提交 Gradle 依赖图、对比 PR 与基线差异，支持远程/本地策略过滤。
- 适用场景：关注“新增或升级”依赖带来的漏洞。

### Grype Vulnerability Scan（新增）

- 工作流：`.github/workflows/grype-scan.yml`
- 流程：构建 → Syft 生成 CycloneDX SBOM → Grype 扫描 → 上传 SBOM/报告。
- 默认阈值：遇到 High 及以上漏洞即失败。
- 默认缓存：`~/.cache/grype/db`，减少数据库下载时间。
- 适用场景：需要对整个工作区做全量漏洞扫描，即便 baseline 未提交依赖图也可工作。

> 详尽说明（含本地运行示例）见 `docs/security.md`。

## 使用的技术

- Gradle 7.6
- Java 11
- JUnit Jupiter 5.8.1

## 本地运行 Grype（快速参考）

```bash
brew install anchore/grype/grype anchore/syft/syft
syft dir:. -o cyclonedx-json > sbom.cdx.json
grype sbom:sbom.cdx.json --fail-on high --add-cpes-if-none
```

更详细的配置、缓存与阈值说明参见 `docs/security.md`。
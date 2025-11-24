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

项目包含以下依赖：

- **log4j-core 2.14.1** - ⚠️ 此版本存在已知的安全漏洞（CVE-2021-44228 等），用于演示 GitHub Actions 的漏洞检测功能
- **guava 30.1-jre** - Google 核心库
- **JUnit Jupiter 5.8.1** - 单元测试框架

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

## GitHub Actions 说明

此项目专门用于演示 GitHub Actions 的依赖检查功能，可以检测项目中使用的有漏洞的依赖库。

## 使用的技术

- Gradle 7.6
- Java 11
- JUnit Jupiter 5.8.1


123
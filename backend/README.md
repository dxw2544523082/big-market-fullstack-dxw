# 后端模块

本目录是整合仓库的完整 Maven 多模块后端。**运行说明以[根 README](../README.md)为准**，默认启动 profile 为 `local`，端口 `18091`，使用仓库根的独立中间件环境。

```bash
# 从仓库根运行，自动构建和启动前后端及独立中间件
python scripts/dev.py up
python scripts/smoke.py
```

后端单独构建（请使用 JDK 8）：

```bash
cd backend
mvn clean package -DskipTests
java -jar big-market-dxw-app/target/big-market-dxw-app.jar --spring.profiles.active=local
```

独立编解码回归测试：

```bash
mvn -pl big-market-dxw-app -am -Dtest=RedisCodecTest -Dsurefire.failIfNoSpecifiedTests=false -DskipTests=false test
```

历史 JUnit4 集成测试需要中间件和指定测试数据，不将其标为已全量通过。原 `docs/dev-ops/` 下脚本/compose 留作历史参考，不作为整合版入口。

架构及功能边界见 [架构说明](../docs/ARCHITECTURE.md)。发奖消费者目前只打印消息，没有实际发券、加积分或发实物。

# Docker secrets 约定

本项目运行时使用 `secrets/` 目录中的文件作为 Docker/Compose secrets 源文件（挂载到容器的 `/run/secrets/...`），并在容器内通过 `*_FILE` 读取注入到同名环境变量。

## `.key` 双文件约定

- `secrets/<name>`：实际给 Docker secrets 使用的文件（生产环境只需要这个）。
- `secrets/<name>.key`：明文对照文件（仅用于本地查看/编辑；生产环境不应包含）。

打包/部署前，执行同步脚本把 `.key` 生成到无后缀文件：

```bash
bash tools/secrets/sync.sh
```

也可以使用仓库根目录脚本：
```bash
bash ./build.sh dev
```

如果需要在生成后移除 `.key` 文件（用于生产打包产物不携带 `.key`）：

```bash
bash tools/secrets/sync.sh --clean-key
```

或：
```bash
bash ./build.sh prod
```

## 当前 Compose 使用到的 secrets

- `secrets/mysql_root_password`
- `secrets/db_password`
- `secrets/secret_key`

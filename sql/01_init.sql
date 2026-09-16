-- AskUSST 初始化 SQL
-- 在 psql / pgAdmin 中执行。

-- 1) 先连到默认的 postgres 维护库，建业务库（Docker 方案已自动建库，跳过这步）：
CREATE DATABASE askusst;

-- 2) 连接到 askusst 库后，开启 pgvector 扩展：
CREATE EXTENSION IF NOT EXISTS vector;

-- 3) 验证扩展已安装（应输出一行 vector）：
SELECT extname, extversion FROM pg_extension WHERE extname = 'vector';

-- 4) 表结构不要手写！由 Python 端 SQLModel.metadata.create_all 自动创建
--    （执行 python -m app.db.init_db）

"""资料文件下载/预览接口。

- GET /files/list              列出文件库（调试/前端展示用）
- GET /files/download?file_id= 安全下载（解析后强制限定在 data/files 目录内，防路径穿越）

学习/演示版暂不鉴权（与登录演示一致）；生产环境应校验 X-User-Id 与权限，
并对敏感资料做访问控制。
"""
import mimetypes
from urllib.parse import quote

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import FileResponse

from app.agent.file_store import build_catalog, resolve_path

router = APIRouter(prefix="/files", tags=["files"])

# 浏览器可直接内联预览的类型：图片 + PDF
_INLINE_EXT = {".pdf", ".png", ".jpg", ".jpeg", ".gif", ".webp", ".bmp"}


@router.get("/list")
def list_files():
    """返回文件库目录（不含本地路径）。"""
    return {"files": [
        {"file_id": c["file_id"], "name": c["name"], "type": c["type"],
         "ext": c["ext"], "size": c["size"], "desc": c["desc"]}
        for c in build_catalog()
    ]}


@router.get("/download")
def download(file_id: str = Query(..., description="文件相对路径标识"),
             mode: str = Query("download", pattern="^(download|inline)$")):
    target = resolve_path(file_id)
    if target is None:
        raise HTTPException(404, "文件不存在或已下架")

    # RFC 5987 中文文件名编码，避免下载时文件名乱码
    disposition = "inline" if (mode == "inline"
                               and target.suffix.lower() in _INLINE_EXT) else "attachment"
    filename_star = quote(target.name)
    media_type = mimetypes.guess_type(target.name)[0] or "application/octet-stream"

    return FileResponse(
        path=str(target),
        media_type=media_type,
        filename=target.name,
        headers={"Content-Disposition":
                 f"{disposition}; filename*=UTF-8''{filename_star}"},
    )

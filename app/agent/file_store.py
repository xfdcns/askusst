"""资料文件库：供 get_file 工具检索，供 /files/download 安全下载。

设计：
- 可下发文件统一放在 data/files/（settings.files_path），支持 pdf/txt/csv/xlsx/docx/图片等；
- 命中方式两层：
  1) data/files/manifest.json 手工登记（推荐，可写中文别名）；
  2) 未登记的文件自动扫描，用文件名（去扩展名）作为关键词；
- 检索只做"关键词重叠 + 子串"的确定性匹配，不调模型，保证可复现、可解释；
  "判断学生到底要哪份文件"由大模型完成，本模块只负责把候选找出来；
- 出于安全考虑，下载接口用 file_id（相对路径）定位，并强制解析结果仍在 files 目录内，
  防止 ../ 路径穿越。
"""
import json
import unicodedata
from pathlib import Path

from app.core.config import settings

# 允许下发的扩展名（其余文件即使放进目录也不会被检索/下载）
ALLOWED_EXT = {
    ".pdf", ".txt", ".md", ".csv", ".xls", ".xlsx",
    ".doc", ".docx", ".ppt", ".pptx",
    ".png", ".jpg", ".jpeg", ".gif", ".webp", ".bmp",
}

# 扩展名 -> 类型/图标，供前端展示
FILE_TYPE_MAP = {
    ".pdf": "pdf",
    ".txt": "text", ".md": "text", ".csv": "excel",
    ".xls": "excel", ".xlsx": "excel",
    ".doc": "word", ".docx": "word",
    ".ppt": "ppt", ".pptx": "ppt",
    ".png": "image", ".jpg": "image", ".jpeg": "image",
    ".gif": "image", ".webp": "image", ".bmp": "image",
}


def _norm(text: str) -> str:
    """归一化：全角->半角、小写、去掉空白与常见标点，便于中文/编号匹配。"""
    text = unicodedata.normalize("NFKC", str(text)).lower()
    for ch in " \t\n\r　()（）[]【】_-—·.,，。、:：;；":
        text = text.replace(ch, "")
    return text


def _scan_files() -> list[dict]:
    """扫描 files 目录下所有允许类型的文件（相对路径作为 file_id）。"""
    root = settings.files_path
    root.mkdir(parents=True, exist_ok=True)
    out = []
    for p in sorted(root.rglob("*")):
        if not p.is_file():
            continue
        if p.name == "manifest.json" or p.suffix.lower() not in ALLOWED_EXT:
            continue
        out.append({
            "file_id": p.relative_to(root).as_posix(),
            "name": p.name,
            "ext": p.suffix.lower(),
        })
    return out


def _load_manifest() -> dict[str, dict]:
    """读取可选的 manifest.json，返回 {file_id: 额外元信息}。"""
    mp = settings.files_path / "manifest.json"
    if not mp.exists():
        return {}
    try:
        data = json.loads(mp.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {}
    if isinstance(data, list):
        return {str(item.get("file_id", "")): item for item in data if item.get("file_id")}
    return {}


def build_catalog() -> list[dict]:
    """合并 manifest 与自动扫描，生成统一文件目录。"""
    manifest = _load_manifest()
    catalog = []
    for f in _scan_files():
        meta = manifest.get(f["file_id"], {})
        stem = Path(f["name"]).stem
        kws = list(meta.get("keywords", [])) + [stem]
        catalog.append({
            "file_id": f["file_id"],
            "name": meta.get("name", f["name"]),
            "type": FILE_TYPE_MAP.get(f["ext"], "file"),
            "ext": f["ext"],
            "size": (settings.files_path / f["file_id"]).stat().st_size,
            "keywords": sorted({_norm(k) for k in kws if str(k).strip()}),
            "desc": str(meta.get("desc", "")),
        })
    return catalog


def _score(query_norm: str, item: dict) -> int:
    """确定性打分：查询是关键词子串 / 关键词是查询子串 / 关键词与查询有字符重叠。"""
    score = 0
    for kw in item["keywords"]:
        if not kw:
            continue
        if kw in query_norm or query_norm in kw:
            score += 10
        overlap = len(set(kw) & set(query_norm))
        if overlap >= 2:
            score += overlap
    return score


def search_files(query: str, top_k: int = 3) -> list[dict]:
    """根据自然语言/关键词找文件，返回命中的文件元信息（不含本地绝对路径）。"""
    qn = _norm(query)
    if not qn:
        return []
    scored = []
    for item in build_catalog():
        s = _score(qn, item)
        if s > 0:
            scored.append((s, item))
    scored.sort(key=lambda x: x[0], reverse=True)
    hits = []
    for _, item in scored[:top_k]:
        hits.append({
            "file_id": item["file_id"],
            "name": item["name"],
            "type": item["type"],
            "ext": item["ext"],
            "size": item["size"],
            "desc": item["desc"],
        })
    return hits


def resolve_path(file_id: str) -> Path | None:
    """把 file_id 安全解析为本地路径；越界或不存在返回 None（防路径穿越）。"""
    root = settings.files_path.resolve()
    try:
        target = (root / file_id).resolve()
    except (OSError, ValueError):
        return None
    if root != target and root not in target.parents:
        return None
    if not target.is_file() or target.suffix.lower() not in ALLOWED_EXT:
        return None
    return target

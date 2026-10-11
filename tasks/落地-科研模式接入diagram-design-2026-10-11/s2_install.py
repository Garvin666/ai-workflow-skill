"""s2：从上游归档取 skills/diagram-design 交付面，复制安装 + 生成 lock 台账。"""
import hashlib, json, shutil, tarfile, tempfile
from pathlib import Path

REV = "7a2e22170ee838e859d8142ba825d83f8b6375e6"
REV_SHORT = REV[:8]
TAR = Path(tempfile.gettempdir()) / "dd-recon" / "src" / "dd.tar.gz"
EXTRACT = Path(tempfile.gettempdir()) / "dd-recon" / "src" / "extracted"
TARGET = Path(__file__).resolve().parents[3] / "diagram-design"
VENDOR_DIR = Path(__file__).resolve().parents[3] / ".vendor"
LOCK = VENDOR_DIR / "diagram-design.lock.json"

assert TAR.exists(), f"归档不存在: {TAR}"
if TARGET.exists():
    raise SystemExit(f"目标已存在，拒绝覆盖: {TARGET}")

# 1) 解压（只取技能子树与仓根 LICENSE）
EXTRACT.mkdir(parents=True, exist_ok=True)
want = f"diagram-design-{REV}/skills/diagram-design/"
want_lic = f"diagram-design-{REV}/LICENSE"
n = 0
with tarfile.open(TAR, "r:gz") as tf:
    for m in tf.getmembers():
        if m.name.startswith(want) and m.isfile():
            tf.extract(m, EXTRACT, filter="data")
            n += 1
        elif m.name == want_lic and m.isfile():
            tf.extract(m, EXTRACT, filter="data")
print(f"解压文件数（技能面）: {n}")

src_root = EXTRACT / f"diagram-design-{REV}"
src_skill = src_root / "skills" / "diagram-design"
src_lic = src_root / "LICENSE"
assert src_skill.is_dir(), "技能子树缺失"
assert src_lic.is_file(), "上游 LICENSE 缺失"

# 2) 复制安装（逐字节）
TARGET.mkdir(parents=True)
files = []
for p in sorted(src_skill.rglob("*")):
    if p.is_file():
        rel = p.relative_to(src_skill)
        dst = TARGET / rel
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(p, dst)
        data = dst.read_bytes()
        files.append({
            "path": "diagram-design/" + rel.as_posix(),
            "upstream_path": f"skills/diagram-design/{rel.as_posix()}",
            "sha256": hashlib.sha256(data).hexdigest(),
            "bytes": len(data),
            "patched": False,
            "carried_along": False,
        })
# 随库携带 LICENSE（MIT 署名义务）
dst_lic = TARGET / "LICENSE"
shutil.copy2(src_lic, dst_lic)
lic_bytes = dst_lic.read_bytes()
files.append({
    "path": "diagram-design/LICENSE",
    "upstream_path": "LICENSE",
    "sha256": hashlib.sha256(lic_bytes).hexdigest(),
    "bytes": len(lic_bytes),
    "patched": False,
    "carried_along": True,
})

# 3) content_digest
h = hashlib.sha256()
for f in sorted(files, key=lambda x: x["path"]):
    h.update(f["path"].encode())
    h.update(b"\x00")
    h.update(str(f["bytes"]).encode())
    h.update(b"\x00")
    h.update(f["sha256"].encode())
    h.update(b"\n")
digest = h.hexdigest()

# 4) lock
lock = {
    "vendor": "cathrynlavery/diagram-design",
    "upstream": "https://github.com/cathrynlavery/diagram-design",
    "upstream_rev": REV,
    "upstream_rev_short": REV_SHORT,
    "upstream_date": "2026-10-10（该 rev 的提交日 2026-10-10T21:10:13Z；上游无 release tag）",
    "license": "MIT",
    "upstream_license_file": "LICENSE（仓根）",
    "license_copyright": src_lic.read_text(encoding="utf-8").strip().splitlines()[2].strip(),
    "declared_version": "2.6（SKILL.md frontmatter metadata.version）；⚠️ 插件 manifest 为 2.6.74 ⇒ 版本号不可作判据，以 upstream_rev 为唯一坐标（与 archify 同纪律）",
    "install_form": "扁平外挂（复制安装，非联接）",
    "target_path": str(TARGET),
    "source_path": f"https://github.com/cathrynlavery/diagram-design/tree/{REV}/skills/diagram-design",
    "content_digest": digest,
    "content_digest_scope": "排序后的 <相对路径>\\0<字节数>\\0<sha256>\\n 串联后取 sha256",
    "installed_at": "2026-10-11",
    "installed_by": "ai-workflow 任务 tasks/落地-科研模式接入diagram-design-2026-10-11（s2）",
    "patch_policy_note": "不改其任何文件（patched 恒为 false）：上游是 MIT 资产，逐字节一致才能做漂移检测（--verify-lock）。同步上游按 references/external-skills.md §7.5 整体重取，不逐文件补丁。",
    "carried_along_note": "LICENSE 为**随库携带**而非上游 skills/diagram-design/ 内文件：其原件在仓库根，为满足 MIT 署名义务与技能内引用完整性而放入技能目录（与 mattpocock/hairline 同法）。",
    "scope_note": "交付面 = 上游 skills/diagram-design/ 子树（SKILL.md + references/ + assets/ + scripts/）。⚠️ 上游仓根的 scripts/verify-*.py 与 scripts/vendor/icons 为 **repo-checkout 专用**（其 SKILL.md 自检条写 'From a repository checkout…'），装态退化为手动自检 ⇒ **不纳入交付面**，如实登记为未覆盖项。",
    "skills": ["diagram-design"],
    "skill_count": 1,
    "files": files,
    "file_count": len(files),
    "reference_mentions": [],
    "reference_mention_count": 0,
    "install_form_reason": "2026-10-11 判形：① 源为普通 GitHub 仓库（不受插件管理、不会删建目录）⇒ 与本簇主流先例（humanizer / hairline-create / archify = 复制安装）一致；② 交付面 4.9 MB / 279 文件，未达 ppt-master（107 MB）那种必须联接的量级；③ 无 fail-closed 完整性门禁（其 scripts/self_check.py 是**产物自检**，非自身完整性守卫）⇒ 不适用 ppt-master 的零改动联接法；④ 逐字节一致便于 --verify-lock 漂移检测。故取「复制安装」。",
}
LOCK.write_text(json.dumps(lock, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")

print(f"安装完成: {TARGET}")
print(f"文件数: {len(files)}（技能面 {len(files)-1} + 随库 LICENSE 1）")
print(f"content_digest: {digest}")
print(f"lock -> {LOCK}")

# 回读断言
back = json.loads(LOCK.read_text(encoding="utf-8"))
assert back["file_count"] == len(files)
on_disk = [p for p in TARGET.rglob("*") if p.is_file()]
assert len(on_disk) == len(files), f"磁盘 {len(on_disk)} != lock {len(files)}"
print("回读断言 OK：磁盘文件数 =", len(on_disk))

"""s1: 冻结基线 + 安装 hairline-create（复制安装、零补丁）+ 立台账。

只做三件事：
  1) 基线快照：把本次将改动的 8 个原件复制到 tmp/.../baseline/ 并出 sha256 清单
  2) 安装：按锁定 rev 取上游 11 文件 + LICENSE，逐文件校验 git blob sha1（证明确实取自该 rev），
     再逐字节写入 ~/.workbuddy/skills/hairline-create/
  3) 台账：写 .vendor/hairline.lock.json（逐文件 sha256 + content_digest）
"""
import base64
import hashlib
import json
import subprocess
import sys
from pathlib import Path

REPO = "lucasmarkes/hairline"
REV = "a2217852fed6d1a4f20bc7d43d4fad1a3de117b8"
SKILL_DIR = "skills/hairline-create"
# 原为硬编码本机主目录（出站清单第 4 项）⇒ 由 __file__ 推导技能根再反推
SKILL_REPO = Path(__file__).resolve().parents[2]
SKILL_ROOT = SKILL_REPO.parent
HOME = SKILL_REPO.parents[2]
TARGET = SKILL_ROOT / "hairline-create"
TMP = SKILL_REPO / "tmp" / "hairline-20261009"

UPSTREAM_FILES = [
    f"{SKILL_DIR}/SKILL.md",
    f"{SKILL_DIR}/bench.html",
    f"{SKILL_DIR}/build.mjs",
    f"{SKILL_DIR}/concepts.md",
    f"{SKILL_DIR}/kernel.js",
    f"{SKILL_DIR}/look.md",
    f"{SKILL_DIR}/look.mjs",
    f"{SKILL_DIR}/rules.md",
    f"{SKILL_DIR}/validate.mjs",
    f"{SKILL_DIR}/examples/riffle.js",
    f"{SKILL_DIR}/examples/terrain.js",
]
LICENSE_REL = "LICENSE"

BASELINE_FILES = [
    "SKILL.md",
    "README.md",
    "references/external-skills.md",
    "references/aesthetic-rubric.yaml",
    "references/diagram-mode.md",
    "references/ppt-mode.md",
    "scripts/check_aesthetics.py",
    "scripts/checks_core.py",
    "_archive/changelog.md",
]


def sha256_bytes(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def git_blob_sha1(b: bytes) -> str:
    h = hashlib.sha1()
    h.update(b"blob %d\0" % len(b))
    h.update(b)
    return h.hexdigest()


def fetch(rel: str):
    """经 gh api 取该 rev 下单个文件；返回 (content_bytes, blob_sha1, size)。"""
    url = f"repos/{REPO}/contents/{rel}?ref={REV}"
    r = subprocess.run(["gh", "api", url], capture_output=True, text=True)
    if r.returncode != 0:
        raise SystemExit(f"[FAIL] gh api 取数失败 {rel}: {r.stderr.strip()[:300]}")
    j = json.loads(r.stdout)
    content = base64.b64decode(j["content"])
    return content, j["sha"], j["size"]


def main():
    TMP.mkdir(parents=True, exist_ok=True)
    baseline = TMP / "baseline"

    # ---- 1) 基线快照 ----
    lines, copied = [], 0
    for rel in BASELINE_FILES:
        src = SKILL_REPO / rel
        if not src.is_file():
            raise SystemExit(f"[FAIL] 基线源不存在：{src}")
        dst = baseline / rel
        dst.parent.mkdir(parents=True, exist_ok=True)
        if not dst.exists():
            dst.write_bytes(src.read_bytes())
        a = sha256_bytes(src.read_bytes())
        b = sha256_bytes(dst.read_bytes())
        if a != b:
            raise SystemExit(f"[FAIL] 基线副本与源不一致：{rel}")
        lines.append(f"{a}  {rel}")
        copied += 1
    (TMP / "baseline-manifest.sha256").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"[OK] 基线快照 {copied}/{len(BASELINE_FILES)} 个文件，sha256 与源逐一对上")

    # ---- 2) 安装 ----
    if TARGET.exists():
        raise SystemExit(f"[FAIL] 目标已存在，拒绝覆盖：{TARGET}")
    records, digest_input = [], []
    total = 0
    plan = list(UPSTREAM_FILES) + [LICENSE_REL]
    for rel in plan:
        content, blob_sha, size = fetch(rel)
        calc = git_blob_sha1(content)
        if calc != blob_sha:
            raise SystemExit(f"[FAIL] {rel} git blob sha1 不符：本地 {calc} / 上游 {blob_sha}")
        if len(content) != size:
            raise SystemExit(f"[FAIL] {rel} 字节数不符：本地 {len(content)} / 上游 {size}")
        # 目标相对路径：剥掉 skills/hairline-create/ 前缀；LICENSE 落为 hairline-create/LICENSE
        if rel == LICENSE_REL:
            target_rel = "LICENSE"
            carried = True
        else:
            target_rel = rel[len(SKILL_DIR) + 1:]
            carried = False
        out = TARGET / target_rel
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_bytes(content)
        if sha256_bytes(out.read_bytes()) != sha256_bytes(content):
            raise SystemExit(f"[FAIL] 落盘后回读不一致：{target_rel}")
        records.append({
            "skill": "hairline-create",
            "path": f"hairline-create/{target_rel}",
            "upstream_path": rel,
            "sha256": sha256_bytes(content),
            "bytes": len(content),
            "patched": False,
            "carried_along": carried,
        })
        digest_input.append(f"{target_rel}\0{len(content)}\0{sha256_bytes(content)}")
        total += len(content)
    digest_input.sort()
    content_digest = sha256_bytes(("\n".join(digest_input) + "\n").encode())

    print(f"[OK] 安装 {len(records)} 个文件到 {TARGET}（共 {total} B）；逐文件 git blob sha1 与锁定 rev 相符")

    # ---- 3) 台账 ----
    lic = (TARGET / "LICENSE").read_text(encoding="utf-8")
    copy_line = next((l.strip() for l in lic.splitlines() if l.strip().startswith("Copyright")), "")
    lock = {
        "vendor": REPO,
        "upstream": f"https://github.com/{REPO}",
        "upstream_rev": REV,
        "upstream_rev_short": REV[:8],
        "upstream_date": "2026-10-08（该 rev 的提交日）",
        "license": "MIT",
        "upstream_license_file": "hairline-create/LICENSE",
        "license_copyright": copy_line,
        "declared_version": "n/a（上游 skills/hairline-create/SKILL.md 的 frontmatter 无 version 字段；以 upstream_rev 为唯一坐标）",
        "install_form": "扁平外挂（复制安装，非联接）",
        "target_path": str(TARGET),
        "source_path": f"https://github.com/{REPO}/tree/{REV}/{SKILL_DIR}",
        "content_digest": content_digest,
        "content_digest_scope": "排序后的 <相对路径>\\0<字节数>\\0<sha256>\\n 串联后取 sha256",
        "installed_at": "2026-10-09",
        "installed_by": "ai-workflow 任务 tasks/复用-hairline视觉工艺-2026-10-09（s1）",
        "patch_policy_note": "不改其任何文件（patched 恒为 false）：上游是 MIT 资产，逐字节一致才能做漂移检测（--verify-lock）。同步上游按 references/external-skills.md §7.3 整体重取，不逐文件补丁。",
        "carried_along_note": "hairline-create/LICENSE 为**随库携带**而非上游 skills/hairline-create/ 内文件：其原件在仓库根 LICENSE，为满足 MIT 署名义务与技能内引用完整性而放入技能目录（与 mattpocock 批次的「上游 LICENSE 随库保留」同法）。upstream_path 字段记录了它的真实出处。",
        "skills": ["hairline-create"],
        "skill_count": 1,
        "files": records,
        "file_count": len(records),
        "reference_mentions": [],
        "reference_mention_count": 0,
        "install_form_reason": "2026-10-09 判形：① 源为普通 GitHub 仓库（不受插件管理、不会删建目录）⇒ 联接不会天然断，但 11 文件 / 约 140 KB 量级小，零拷贝无收益；② 与本簇主流先例（mattpocock 24 个 = 扁平外挂）一致，真实目录不依赖宿主是否跟随联接；③ 逐字节一致便于 --verify-lock 漂移检测。故取「复制安装」。",
    }
    lock_path = SKILL_ROOT / ".vendor" / "hairline.lock.json"
    lock_path.write_text(json.dumps(lock, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"[OK] 台账落盘：{lock_path}（{len(records)} 条 files 记录，content_digest={content_digest[:16]}…）")

    # ---- 自证：真实目录而非联接 + frontmatter 可解析 ----
    tj = subprocess.run(
        ["cmd", "/c", "dir", "/AL", str(SKILL_ROOT), "|", "findstr", "/I", "hairline"],
        capture_output=True, text=True)
    print("[INFO] 联接探测（dir /AL 输出，空=非联接）:", (tj.stdout.strip() or "<空>"))
    print(f"[SELFTEST] target_exists={TARGET.is_dir()} file_count_on_disk={sum(1 for p in TARGET.rglob('*') if p.is_file())}")


if __name__ == "__main__":
    main()

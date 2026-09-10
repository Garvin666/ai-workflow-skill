"""http_fetch.py - 联网抓取（超时 30s + 退避重试）。

能力:
    1) 普通抓取（保持 v1 行为兼容）
    2) GitHub 仓库指标结构化取值（解决匿名 API 403 限流的坑）
    3) HTML → 纯文本（省 token，避免把整页 HTML 塞进上下文）

用法:
    python http_fetch.py <URL>                      # 内容打印到 stdout
    python http_fetch.py <URL> --out page.html      # 写入文件
    python http_fetch.py <URL> --text               # HTML 提取为纯文本
    python http_fetch.py <URL> --grep "关键词" --max-chars 3000   # 定向提取（省 token）
    python http_fetch.py --github-repo owner/repo   # 输出指标（TSV）
    python http_fetch.py --github-repo a/b,c/d --json
    python http_fetch.py --github-repo owner/repo --out repo.json

GitHub 鉴权（可选，提高限额）:
    设置环境变量 GITHUB_TOKEN=<PAT>；未设置则用匿名限额（60 次/小时/IP）。

403 处理规则（重要）:
    - GitHub 匿名限流返回 403（不是权限错误）→ 识别 X-RateLimit-* / Retry-After 后等待重试
    - 其他 403 → 视为权限问题，不重试
"""
import argparse
import html
import json
import os
import re
import sys
import time
import urllib.error
import urllib.request

sys.stdout.reconfigure(encoding="utf-8")
sys.stderr.reconfigure(encoding="utf-8")

TIMEOUT = 30
RETRY_DELAYS = (2, 4, 8)
RATE_LIMIT_MAX_WAIT = int(os.environ.get("AIWF_GITHUB_MAX_WAIT", "60"))  # 单次限流最长等待秒数
RATE_LIMIT_MAX_RETRY = int(os.environ.get("AIWF_GITHUB_MAX_RETRY", "2"))  # 限流重试次数上限
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) ai-workflow/2.0",
    "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
}

GITHUB_FIELDS = (
    "full_name",
    "stargazers_count",
    "forks_count",
    "open_issues_count",
    "archived",
    "pushed_at",
    "updated_at",
    "created_at",
    "description",
    "html_url",
)


def _rate_limit_wait(headers) -> int:
    """从响应头推算需要等待的秒数；无法判定时给保守默认值。"""
    retry_after = headers.get("Retry-After")
    if retry_after and retry_after.isdigit():
        return min(int(retry_after) + 1, RATE_LIMIT_MAX_WAIT)
    reset = headers.get("X-RateLimit-Reset")
    if reset and reset.isdigit():
        wait = int(reset) - int(time.time()) + 1
        if wait > 0:
            return min(wait, RATE_LIMIT_MAX_WAIT)
    return 15


def fetch(url: str, token: str | None = None) -> bytes:
    headers = dict(HEADERS)
    if token:
        headers["Authorization"] = f"Bearer {token}"
    elif "api.github.com" in url and os.environ.get("GITHUB_TOKEN"):
        headers["Authorization"] = f"Bearer {os.environ['GITHUB_TOKEN']}"

    last_err = None
    rl_waits = 0
    attempts = (0,) + RETRY_DELAYS
    for i, delay in enumerate(attempts):
        if delay:
            time.sleep(delay)
        req = urllib.request.Request(url, headers=headers)
        try:
            with urllib.request.urlopen(req, timeout=TIMEOUT) as resp:
                return resp.read()
        except urllib.error.HTTPError as e:
            body = ""
            try:
                body = e.read().decode("utf-8", errors="replace")[:200]
            except Exception:  # noqa: BLE001 - 读取响应体失败不应掩盖原始错误
                pass
            if e.code == 403 and ("rate limit" in body.lower() or e.headers.get("X-RateLimit-Remaining") == "0"):
                if rl_waits >= RATE_LIMIT_MAX_RETRY:
                    print(
                        f"[ERROR] GitHub API 持续限流（已等待重试 {rl_waits} 次）。"
                        "解决办法：设置环境变量 GITHUB_TOKEN=<PAT> 提高限额，或改用已有实测数据并标注『未实时校验』。",
                        file=sys.stderr,
                    )
                    raise SystemExit(5)
                rl_waits += 1
                wait = _rate_limit_wait(e.headers)
                last_err = f"HTTP 403 限流（等待 {wait}s 后重试）"
                print(f"[WARN] GitHub API 限流，等待 {wait}s 重试（第 {rl_waits}/{RATE_LIMIT_MAX_RETRY} 次）", file=sys.stderr)
                time.sleep(wait)
                continue
            if e.code in (401, 403, 404):
                print(f"[ERROR] HTTP {e.code}（不重试）: {url} :: {body}", file=sys.stderr)
                raise SystemExit(3)
            last_err = f"HTTP {e.code}"
        except (urllib.error.URLError, TimeoutError, OSError) as e:
            last_err = str(e)
        print(f"[WARN] 第 {i + 1} 次失败: {last_err}", file=sys.stderr)
    print(f"[ERROR] 重试耗尽: {last_err}", file=sys.stderr)
    raise SystemExit(4)


def html_to_text(raw: bytes) -> str:
    """极简 HTML → 文本：去脚本/样式/标签，解实体，压缩空行。不引第三方依赖。"""
    for enc in ("utf-8", "gbk", "latin-1"):
        try:
            s = raw.decode(enc)
            break
        except UnicodeDecodeError:
            continue
    else:
        s = raw.decode("utf-8", errors="replace")
    s = re.sub(r"(?is)<(script|style|noscript|svg)[^>]*>.*?</\1>", " ", s)
    s = re.sub(r"(?is)<!--.*?-->", " ", s)
    s = re.sub(r"(?i)<br\s*/?>|</(p|div|li|tr|h[1-6])>", "\n", s)
    s = re.sub(r"(?s)<[^>]+>", " ", s)
    s = html.unescape(s)
    lines = [re.sub(r"[ \t\u00a0]+", " ", ln).strip() for ln in s.splitlines()]
    return "\n".join(ln for ln in lines if ln)


def github_repo_metrics(slug: str, token: str | None = None) -> dict:
    slug = slug.strip().strip("/")
    if slug.count("/") != 1:
        print(f"[ERROR] 仓库格式应为 owner/repo，收到: {slug}", file=sys.stderr)
        raise SystemExit(2)
    raw = fetch(f"https://api.github.com/repos/{slug}", token=token)
    data = json.loads(raw.decode("utf-8"))
    out = {k: data.get(k) for k in GITHUB_FIELDS}
    lic = data.get("license") or {}
    out["license_spdx"] = lic.get("spdx_id")
    out["license_name"] = lic.get("name")
    out["_note"] = "NOASSERTION 表示 GitHub 无法自动归类，非『无许可证』；仍久未更新的 pushed_at 是活跃度风险信号"
    return out


def main() -> None:
    ap = argparse.ArgumentParser(description="联网抓取 / GitHub 指标取值 / HTML 转文本")
    ap.add_argument("url", nargs="?", help="目标 URL（与 --github-repo 二选一）")
    ap.add_argument("--out", help="写入文件（缺省打印 stdout）")
    ap.add_argument("--text", action="store_true", help="HTML 提取为纯文本后再输出/保存")
    ap.add_argument("--github-repo", help="GitHub 仓库 owner/repo，多个用逗号分隔")
    ap.add_argument("--json", action="store_true", help="GitHub 指标以 JSON 输出（缺省 TSV）")
    ap.add_argument("--token", help="GitHub PAT（缺省读环境变量 GITHUB_TOKEN）")
    ap.add_argument("--grep", help="只输出匹配该正则的行（自动启用 --text，用于精检索省 token）")
    ap.add_argument("--max-chars", type=int, help="输出截断到 N 个字符（配合 --grep 做定向读取）")
    ap.add_argument("--ignore-case", action="store_true", help="--grep 忽略大小写")
    args = ap.parse_args()

    if args.github_repo:
        token = args.token or os.environ.get("GITHUB_TOKEN")
        rows = []
        for slug in [s for s in args.github_repo.split(",") if s.strip()]:
            try:
                rows.append(github_repo_metrics(slug, token=token))
            except SystemExit as e:
                msg = f"fetch_failed(code={e.code})"
                print(f"[WARN] {slug.strip()} 取值失败：{msg}（数据缺失请勿编造，改用其他来源或标注『未实时校验』）", file=sys.stderr)
                rows.append({"full_name": slug.strip(), "error": msg})
        failed = [r for r in rows if r.get("error")]
        if failed:
            print(f"[WARN] {len(failed)}/{len(rows)} 个仓库未取到实测数据，禁止用二手数字替代", file=sys.stderr)
        if args.json:
            text = json.dumps(rows, ensure_ascii=False, indent=2)
        else:
            cols = ["full_name", "stargazers_count", "forks_count", "license_spdx", "pushed_at", "archived", "error"]
            text = "\t".join(cols) + "\n"
            for r in rows:
                text += "\t".join(
                    "—" if r.get(c) is None else ("否" if r.get(c) is False else str(r.get(c))) for c in cols
                ) + "\n"
        if args.out:
            with open(args.out, "w", encoding="utf-8-sig") as f:
                f.write(text)
            print(f"[ OK ] 已写入 {args.out}（{len(rows)} 个仓库）")
        else:
            print(text)
        return

    if not args.url:
        ap.error("必须提供 URL 或 --github-repo")

    content = fetch(args.url)
    if args.grep and not args.text:
        args.text = True
        print("[INFO] 指定 --grep，自动启用 HTML→文本", file=sys.stderr)
    if args.text:
        text = html_to_text(content)
        if args.grep:
            flags = re.IGNORECASE if args.ignore_case else 0
            try:
                pat = re.compile(args.grep, flags)
            except re.error as e:
                print(f"[ERROR] 正则非法: {e}", file=sys.stderr)
                raise SystemExit(2)
            hits = [f"{i}: {ln}" for i, ln in enumerate(text.splitlines(), 1) if pat.search(ln)]
            print(f"[INFO] grep 命中 {len(hits)} 行（原文 {len(text)} 字符）", file=sys.stderr)
            text = "\n".join(hits)
        if args.max_chars and len(text) > args.max_chars:
            text = text[: args.max_chars] + f"\n...[已截断，原始 {len(text)} 字符]"
        if args.out:
            with open(args.out, "w", encoding="utf-8-sig") as f:
                f.write(text)
            print(f"[ OK ] 已写入 {args.out}（{len(text)} 字符）")
        else:
            print(text)
        return

    if args.out:
        with open(args.out, "wb") as f:
            f.write(content)
        print(f"[ OK ] 已写入 {args.out}（{len(content)} 字节）")
    else:
        sys.stdout.buffer.write(content)


if __name__ == "__main__":
    main()

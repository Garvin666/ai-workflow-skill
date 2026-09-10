"""http_fetch.py - 联网抓取（超时 30s + 退避重试 3 次）。

用法:
    python http_fetch.py <URL>                 # 内容打印到 stdout
    python http_fetch.py <URL> --out page.html # 内容写入文件（utf-8-sig）
"""
import argparse
import sys
import time
import urllib.error
import urllib.request

sys.stdout.reconfigure(encoding="utf-8")
sys.stderr.reconfigure(encoding="utf-8")

TIMEOUT = 30
RETRY_DELAYS = (2, 4, 8)
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) ai-workflow/1.0",
    "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
}


def fetch(url: str) -> bytes:
    last_err = None
    for attempt, delay in enumerate((0,) + RETRY_DELAYS):
        if delay:
            time.sleep(delay)
        req = urllib.request.Request(url, headers=HEADERS)
        try:
            with urllib.request.urlopen(req, timeout=TIMEOUT) as resp:
                if resp.status != 200:
                    last_err = f"HTTP {resp.status}"
                else:
                    return resp.read()
        except urllib.error.HTTPError as e:
            if e.code in (401, 403, 404):
                print(f"[ERROR] HTTP {e.code}（不重试）: {url}", file=sys.stderr)
                raise SystemExit(3)
            last_err = f"HTTP {e.code}"
        except (urllib.error.URLError, TimeoutError, OSError) as e:
            last_err = str(e)
        print(f"[WARN] 第 {attempt + 1} 次失败: {last_err}", file=sys.stderr)
    print(f"[ERROR] 重试耗尽: {last_err}", file=sys.stderr)
    raise SystemExit(4)


def main() -> None:
    ap = argparse.ArgumentParser(description="联网抓取工具")
    ap.add_argument("url")
    ap.add_argument("--out", help="写入文件（缺省打印 stdout）")
    args = ap.parse_args()

    content = fetch(args.url)

    if args.out:
        with open(args.out, "wb") as f:
            f.write(content)
        print(f"[ OK ] 已写入 {args.out}（{len(content)} 字节）")
    else:
        sys.stdout.buffer.write(content)


if __name__ == "__main__":
    main()

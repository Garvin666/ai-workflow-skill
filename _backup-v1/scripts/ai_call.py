"""ai_call.py - AI 模型调用封装（OpenAI 兼容接口）。

环境变量:
    AI_API_KEY   必填（不落日志、不回显）
    AI_API_BASE  选填，默认 https://api.deepseek.com/v1
    AI_MODEL     选填，默认 deepseek-chat

用法:
    echo 问题 | python ai_call.py
    python ai_call.py --prompt-file prompt.txt --system "你是助手" --out result.txt
"""
import argparse
import json
import os
import sys
import time

import urllib.error
import urllib.request

sys.stdout.reconfigure(encoding="utf-8")
sys.stderr.reconfigure(encoding="utf-8")

DEFAULT_BASE = "https://api.deepseek.com/v1"
DEFAULT_MODEL = "deepseek-chat"
RETRY_DELAYS = (2, 4, 8)  # 秒，指数退避


def call_api(prompt: str, system: str | None, timeout: int = 60) -> str:
    base = os.environ.get("AI_API_BASE", DEFAULT_BASE).rstrip("/")
    model = os.environ.get("AI_MODEL", DEFAULT_MODEL)
    key = os.environ.get("AI_API_KEY", "")
    if not key:
        print("[ERROR] 未设置环境变量 AI_API_KEY", file=sys.stderr)
        raise SystemExit(2)

    url = f"{base}/chat/completions"
    messages = ([{"role": "system", "content": system}] if system else []) + [
        {"role": "user", "content": prompt}
    ]
    payload = json.dumps({"model": model, "messages": messages}).encode("utf-8")

    last_err = None
    for attempt, delay in enumerate((0,) + RETRY_DELAYS):
        if delay:
            time.sleep(delay)
        req = urllib.request.Request(
            url,
            data=payload,
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {key}",
            },
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                data = json.loads(resp.read().decode("utf-8"))
            return data["choices"][0]["message"]["content"]
        except urllib.error.HTTPError as e:
            body = e.read().decode("utf-8", errors="replace")[:300]
            # 凭据/参数错误不重试
            if e.code in (401, 403, 400):
                print(f"[ERROR] HTTP {e.code}（不重试）: {body}", file=sys.stderr)
                raise SystemExit(3)
            last_err = f"HTTP {e.code}: {body}"
        except (urllib.error.URLError, TimeoutError, OSError) as e:
            last_err = str(e)
        print(f"[WARN] 第 {attempt + 1} 次失败: {last_err}", file=sys.stderr)

    print(f"[ERROR] 重试耗尽: {last_err}", file=sys.stderr)
    raise SystemExit(4)


def main() -> None:
    ap = argparse.ArgumentParser(description="AI 模型调用封装")
    ap.add_argument("--prompt-file", help="prompt 文件路径（缺省读 stdin）")
    ap.add_argument("--system", help="system 提示词（选填）")
    ap.add_argument("--out", help="结果写入文件（utf-8-sig，缺省打印 stdout）")
    args = ap.parse_args()

    if args.prompt_file:
        with open(args.prompt_file, "r", encoding="utf-8-sig") as f:
            prompt = f.read()
    else:
        prompt = sys.stdin.read()
    if not prompt.strip():
        print("[ERROR] prompt 为空", file=sys.stderr)
        raise SystemExit(1)

    answer = call_api(prompt, args.system)

    if args.out:
        with open(args.out, "w", encoding="utf-8-sig") as f:
            f.write(answer)
        print(f"[ OK ] 结果已写入 {args.out}")
    else:
        print(answer)


if __name__ == "__main__":
    main()

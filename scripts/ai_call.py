"""ai_call.py - AI 模型调用封装（OpenAI 兼容接口）。

环境变量:
    AI_API_KEY     必填（不落日志、不回显）
    AI_API_BASE    选填，默认 https://api.deepseek.com/v1
    AI_MODEL       选填，默认 deepseek-chat
    AI_PRICE_IN    选填，输入价格（元/百万 token），用于 --stats 成本估算
    AI_PRICE_OUT   选填，输出价格（元/百万 token）

用法:
    echo 问题 | python ai_call.py
    python ai_call.py --prompt-file prompt.txt --system "你是助手" --out result.txt
    python ai_call.py --prompt-file p.txt --model deepseek-reasoner --stats
    python ai_call.py --batch-file prompts.txt --out results.jsonl --concurrency 3

批量模式（--batch-file）:
    每行一个 prompt，共用同一 system（保持缓存前缀稳定），线程池并发调用；
    结果按行写入 JSONL（含 prompt / answer / usage / error），失败不中断整体。

Token / 缓存纪律（调用侧请遵守）:
    - system 段保持**稳定前缀**（同一任务多轮复用同一 system），DeepSeek 磁盘 KV 缓存
      可命中约 98% 折扣；禁止每次改写前缀，否则缓存全失效
    - 动态内容（本轮数据、时间戳）一律放在 user 段
    - 长文批量任务：先做索引/摘要再按需取片段，不要整库塞入
"""
import argparse
import concurrent.futures
import json
import os
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")
sys.stderr.reconfigure(encoding="utf-8")

DEFAULT_BASE = "https://api.deepseek.com/v1"
DEFAULT_MODEL = "deepseek-chat"
RETRY_DELAYS = (2, 4, 8)  # 秒，指数退避


def _build_payload(model: str, prompt: str, system: str | None, args) -> bytes:
    messages = ([{"role": "system", "content": system}] if system else []) + [
        {"role": "user", "content": prompt}
    ]
    body = {"model": model, "messages": messages}
    if args.max_tokens:
        body["max_tokens"] = args.max_tokens
    if args.temperature is not None:
        body["temperature"] = args.temperature
    return json.dumps(body).encode("utf-8")


def call_api(prompt: str, system: str | None, args, timeout: int = 60) -> tuple[str, dict]:
    base = os.environ.get("AI_API_BASE", DEFAULT_BASE).rstrip("/")
    model = args.model or os.environ.get("AI_MODEL", DEFAULT_MODEL)
    key = os.environ.get("AI_API_KEY", "")
    if not key:
        print("[ERROR] 未设置环境变量 AI_API_KEY", file=sys.stderr)
        raise SystemExit(2)

    url = f"{base}/chat/completions"
    payload = _build_payload(model, prompt, system, args)

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
            return data["choices"][0]["message"]["content"], (data.get("usage") or {})
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


def report_usage(model: str, usage: dict) -> None:
    if not usage:
        print("[STATS] 接口未返回 usage，无法统计 token", file=sys.stderr)
        return
    pin, pout = usage.get("prompt_tokens"), usage.get("completion_tokens")
    total = usage.get("total_tokens")
    cached = usage.get("prompt_cache_hit_tokens")
    line = f"[STATS] model={model} 输入={pin} 输出={pout} 合计={total}"
    if cached is not None:
        line += f" 缓存命中={cached}"
    p_in, p_out = os.environ.get("AI_PRICE_IN"), os.environ.get("AI_PRICE_OUT")
    if p_in and p_out and pin is not None and pout is not None:
        cost = float(pin) / 1e6 * float(p_in) + float(pout) / 1e6 * float(p_out)
        line += f" 估算成本=¥{cost:.4f}（按 AI_PRICE_IN/OUT）"
    else:
        line += "（设置 AI_PRICE_IN / AI_PRICE_OUT 可估算成本）"
    print(line, file=sys.stderr)


def run_batch(args, system: str | None) -> None:
    src = Path(args.batch_file)
    if not src.exists():
        print(f"[ERROR] 批量文件不存在: {src}", file=sys.stderr)
        raise SystemExit(1)
    prompts = [ln.strip() for ln in src.read_text(encoding="utf-8-sig").splitlines() if ln.strip()]
    if not prompts:
        print("[ERROR] 批量文件无有效 prompt", file=sys.stderr)
        raise SystemExit(1)

    out_path = Path(args.out) if args.out else src.with_name(src.stem + "-results.jsonl")
    model = args.model or os.environ.get("AI_MODEL", DEFAULT_MODEL)
    total = len(prompts)
    done = 0
    t0 = time.time()
    print(f"[INFO] 批量调用 {total} 条，并发 {args.concurrency}，模型 {model} → {out_path}", file=sys.stderr)

    def one(item: tuple[int, str]) -> dict:
        idx, prompt = item
        record = {"index": idx, "prompt": prompt, "model": model}
        try:
            answer, usage = call_api(prompt, system, args)
            record.update({"answer": answer, "usage": usage})
        except SystemExit as e:
            record["error"] = f"call_failed(code={e.code})"
        return record

    failures = 0
    with open(out_path, "w", encoding="utf-8") as f, concurrent.futures.ThreadPoolExecutor(
        max_workers=max(1, args.concurrency)
    ) as pool:
        for record in pool.map(one, list(enumerate(prompts, 1))):
            f.write(json.dumps(record, ensure_ascii=False) + "\n")
            f.flush()
            done += 1
            if record.get("error"):
                failures += 1
            print(f"[进度] {done}/{total} 完成（失败 {failures}）", file=sys.stderr)

    cost = time.time() - t0
    print(f"[ OK ] 批量完成：{done}/{total}，失败 {failures}，耗时 {cost:.1f}s → {out_path}", file=sys.stderr)
    if failures:
        print("[WARN] 存在失败条目，请检查 JSONL 中 error 字段（无效 key 会整体失败）", file=sys.stderr)
    print(f"[ OK ] 结果已写入 {out_path}")


def main() -> None:
    ap = argparse.ArgumentParser(description="AI 模型调用封装")
    ap.add_argument("--prompt-file", help="prompt 文件路径（缺省读 stdin）")
    ap.add_argument("--system", help="system 提示词（选填，保持稳定以吃缓存）")
    ap.add_argument("--system-file", help="从文件读取 system 提示词（长 system 推荐用文件）")
    ap.add_argument("--out", help="结果写入文件（utf-8-sig，缺省打印 stdout）")
    ap.add_argument("--model", help="覆盖本次调用的模型（缺省读 AI_MODEL）")
    ap.add_argument("--max-tokens", type=int, help="输出上限")
    ap.add_argument("--temperature", type=float, help="采样温度")
    ap.add_argument("--stats", action="store_true", help="回显 token 用量与成本估算（stderr）")
    ap.add_argument("--batch-file", help="批量模式：每行一个 prompt 的文本文件")
    ap.add_argument("--concurrency", type=int, default=3, help="批量模式并发数（默认 3）")
    args = ap.parse_args()

    system = args.system
    if args.system_file:
        with open(args.system_file, "r", encoding="utf-8-sig") as f:
            system = f.read()

    if args.batch_file:
        run_batch(args, system)
        return

    if args.prompt_file:
        with open(args.prompt_file, "r", encoding="utf-8-sig") as f:
            prompt = f.read()
    else:
        prompt = sys.stdin.read()
    if not prompt.strip():
        print("[ERROR] prompt 为空", file=sys.stderr)
        raise SystemExit(1)

    answer, usage = call_api(prompt, system, args)

    if args.stats:
        report_usage(args.model or os.environ.get("AI_MODEL", DEFAULT_MODEL), usage)

    if args.out:
        with open(args.out, "w", encoding="utf-8-sig") as f:
            f.write(answer)
        print(f"[ OK ] 结果已写入 {args.out}")
    else:
        print(answer)


if __name__ == "__main__":
    main()

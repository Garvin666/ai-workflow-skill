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

TIERS_PATH = Path(__file__).with_name("model_tiers.json")
LEDGER_DEFAULT = Path.home() / ".workbuddy" / "cache" / "ai-workflow" / "usage_ledger.jsonl"


def resolve_tier(tier: str) -> dict:
    """按档位名从 model_tiers.json 解析调用配置；缺失/未知则退回全局变量。"""
    if not TIERS_PATH.exists():
        print(f"[WARN] 档位配置缺失 {TIERS_PATH}，退回全局 AI_MODEL", file=sys.stderr)
        return {}
    try:
        tiers = json.loads(TIERS_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as e:
        print(f"[WARN] 档位配置解析失败：{e}", file=sys.stderr)
        return {}
    cfg = tiers.get(tier)
    if not cfg:
        print(f"[WARN] 未知档位 '{tier}'，可选：{', '.join(tiers.keys())}", file=sys.stderr)
        return {}
    return cfg


def _append_ledger(path: str, tier: str, model: str, usage: dict) -> None:
    """把一次调用的档位/模型/token/成本追加到用量账本（JSONL），供阶段路由降本实测。"""
    try:
        pin = int(usage.get("prompt_tokens") or 0)
        pout = int(usage.get("completion_tokens") or 0)
        p_in = float(os.environ.get("AI_PRICE_IN", 0) or 0)
        p_out = float(os.environ.get("AI_PRICE_OUT", 0) or 0)
        cost = pin / 1e6 * p_in + pout / 1e6 * p_out
        rec = {
            "ts": time.strftime("%Y-%m-%dT%H:%M:%S"),
            "tier": tier,
            "model": model,
            "prompt_tokens": pin,
            "completion_tokens": pout,
            "total_tokens": int(usage.get("total_tokens") or (pin + pout)),
            "cost_yuan": round(cost, 6),
        }
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        with open(path, "a", encoding="utf-8") as f:
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")
        print(f"[LEDGER] 已记录 -> {path}（tier={tier} cost=Y{cost:.4f}）", file=sys.stderr)
    except Exception as e:  # noqa: BLE001
        print(f"[WARN] 账本写入失败：{e}", file=sys.stderr)



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
            if args.ledger or args.tier:
                _append_ledger(args.ledger or str(LEDGER_DEFAULT), args.tier or "default", model, usage)
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


def _selftest() -> int:
    """--selftest：只回归「不联网、不读凭据」的纯逻辑。

    覆盖：model_tiers.json 档位解析、请求体构造、成本估算（账本落盘）、批量文件解析。
    任何用例都不触发 call_api（无 AI_API_KEY 时由子进程验证其失败路径）。
    """
    import io
    import subprocess
    import tempfile
    from contextlib import redirect_stderr
    from types import SimpleNamespace

    results: list[bool] = []

    def fmt(v):
        if isinstance(v, (dict, list, tuple)):
            return json.dumps(v, ensure_ascii=False, sort_keys=True, default=str)
        return str(v)

    def check(name: str, actual, expected) -> None:
        ok = actual == expected
        print(f"[{'PASS' if ok else 'MISS'}] {name}：实际={fmt(actual)} 期望={fmt(expected)}")
        results.append(ok)

    # 1) 档位解析：strong 必须给出 reasoner 与官方价目
    cfg = resolve_tier("strong")
    check("档位 strong 解析(model/price_in/price_out)",
          (cfg.get("model"), cfg.get("price_in"), cfg.get("price_out")),
          ("deepseek-reasoner", 4.0, 16.0))

    # 2) 阴性对照：未知档位必须拒绝（返回空且不抛异常），并留下 WARN
    err_buf = io.StringIO()
    with redirect_stderr(err_buf):
        unknown = resolve_tier("no-such-tier")
    check("阴性：未知档位退化为 {}（且 stderr 报未知档位）",
          (unknown, "未知档位" in err_buf.getvalue()), ({}, True))

    # 3) 请求体构造：system 段必须落在 messages[0]，可选字段按传参注入
    body = json.loads(_build_payload("m-1", "hi", "sys", SimpleNamespace(max_tokens=256, temperature=0.0)))
    check("请求体：system 在首位 + max_tokens/temperature 生效",
          (body["messages"][0], body["messages"][1]["content"], body["max_tokens"], body["temperature"]),
          ({"role": "system", "content": "sys"}, "hi", 256, 0.0))

    # 4) 阴性对照：未传 system / 未设上限时不得凭空多出字段
    body2 = json.loads(_build_payload("m-1", "hi", None, SimpleNamespace(max_tokens=None, temperature=None)))
    check("阴性：无 system/无上限时不多发字段",
          (list(body2.keys()), len(body2["messages"]), body2["messages"][0]["role"]),
          (["model", "messages"], 1, "user"))

    # 5) 成本估算：1M 输入×4 元 + 0.5M 输出×16 元 = 12 元
    old_in, old_out = os.environ.get("AI_PRICE_IN"), os.environ.get("AI_PRICE_OUT")
    try:
        os.environ["AI_PRICE_IN"], os.environ["AI_PRICE_OUT"] = "4.0", "16.0"
        with tempfile.TemporaryDirectory() as td:
            ledger = Path(td) / "ledger.jsonl"
            with redirect_stderr(io.StringIO()):
                _append_ledger(str(ledger), "strong", "deepseek-reasoner",
                               {"prompt_tokens": 1_000_000, "completion_tokens": 500_000})
            rec = json.loads(ledger.read_text(encoding="utf-8").strip())
        check("成本估算 1M×4 + 0.5M×16（元）", (rec["cost_yuan"], rec["total_tokens"]), (12.0, 1_500_000))
    finally:
        for k, v in (("AI_PRICE_IN", old_in), ("AI_PRICE_OUT", old_out)):
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v

    # 6) 批量解析：BOM/空行/纯空格行都要过滤；缺 key 时按条记 error 且不联网
    with tempfile.TemporaryDirectory() as td:
        bf = Path(td) / "prompts.txt"
        bf.write_text("\ufeff第一条\n\n   \n第二条\n", encoding="utf-8")
        out_path = Path(td) / "results.jsonl"
        env = {k: v for k, v in os.environ.items() if k != "AI_API_KEY"}
        proc = subprocess.run(
            [sys.executable, os.path.abspath(__file__), "--batch-file", str(bf),
             "--out", str(out_path), "--concurrency", "2"],
            capture_output=True, text=True, encoding="utf-8", errors="replace", env=env, timeout=120,
        )
        recs = [json.loads(ln) for ln in out_path.read_text(encoding="utf-8").splitlines() if ln.strip()]
        check("批量解析：BOM/空行过滤为 2 条，缺 key 记 call_failed(2)",
              (len(recs), sorted(r["prompt"] for r in recs), {r.get("error") for r in recs}),
              (2, ["第一条", "第二条"], {"call_failed(code=2)"}))

    total = len(results)
    ok_n = sum(1 for r in results if r)
    print(f"=== selftest：{ok_n}/{total} ===")
    return 0 if ok_n == total else 1


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
    ap.add_argument("--tier", help="阶段路由档位：strong/mid/cheap（按 model_tiers.json 解析 base/key/model/price）")
    ap.add_argument("--ledger", help="用量账本 JSONL 路径（缺省 ~/.workbuddy/cache/ai-workflow/usage_ledger.jsonl）；--tier 时自动写入")
    ap.add_argument("--batch-file", help="批量模式：每行一个 prompt 的文本文件")
    ap.add_argument("--concurrency", type=int, default=3, help="批量模式并发数（默认 3）")
    ap.add_argument("--selftest", action="store_true",
                    help="自检：回归档位解析/请求体构造/成本估算/批量解析（不联网、不读凭据，全过 exit 0）")
    args = ap.parse_args()

    if args.selftest:
        raise SystemExit(_selftest())

    # 阶段感知模型路由：--tier 覆盖 base/key/model/price（见 model_tiers.json）
    if args.tier:
        cfg = resolve_tier(args.tier)
        if cfg:
            base = cfg.get("base")
            if cfg.get("base_env"):
                base = os.environ.get(cfg["base_env"], base)
            if base:
                os.environ["AI_API_BASE"] = base
            key = os.environ.get(cfg["key_env"], "") if cfg.get("key_env") else ""
            os.environ["AI_API_KEY"] = key or "none"  # 本地档（Ollama）无需真实 key
            if cfg.get("model"):
                os.environ["AI_MODEL"] = cfg["model"]
                args.model = cfg["model"]
            if cfg.get("price_in") is not None:
                os.environ["AI_PRICE_IN"] = str(cfg["price_in"])
            if cfg.get("price_out") is not None:
                os.environ["AI_PRICE_OUT"] = str(cfg["price_out"])
            print(f"[ROUTE] 档位={args.tier} -> model={cfg.get('model')} base={os.environ['AI_API_BASE']}",
                  file=sys.stderr)

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

    if args.ledger or args.tier:
        _append_ledger(args.ledger or str(LEDGER_DEFAULT), args.tier or "default",
                       args.model or os.environ.get("AI_MODEL", DEFAULT_MODEL), usage)

    if args.out:
        with open(args.out, "w", encoding="utf-8-sig") as f:
            f.write(answer)
        print(f"[ OK ] 结果已写入 {args.out}")
    else:
        print(answer)


if __name__ == "__main__":
    main()

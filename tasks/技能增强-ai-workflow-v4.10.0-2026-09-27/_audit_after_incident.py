# -*- coding: utf-8 -*-
"""误删核实：技能仓 tasks/ 现状 + git 完整性 + 他线文件检查。"""
import os, subprocess

S = r'C:\Users\<用户名>\.workbuddy\skills\ai-workflow'

def g(*a):
    r = subprocess.run(['git'] + list(a), capture_output=True, text=True,
                       encoding='utf-8', errors='replace', cwd=S)
    return r.returncode, r.stdout, r.stderr

print('=== 1. git 完整性（HEAD 与分支）===')
print(g('log', '--oneline', '-1')[1].strip())
print('branch:', g('branch', '--show-current')[1].strip())
rc, o, _ = g('status', '--porcelain=v1')
print('status 条数:', len([l for l in o.splitlines() if l.strip()]))

print()
print('=== 2. tasks/ 根下我本会话与疑似他线的留痕文件 ===')
T = os.path.join(S, 'tasks')
for f in sorted(os.listdir(T)):
    if os.path.isfile(os.path.join(T, f)):
        sz = os.path.getsize(os.path.join(T, f))
        print(f'  {sz:>8}B  {f}')

print()
print('=== 3. 本次推送关键留痕是否完好 ===')
for f in ['_push-result-20260928.txt', '_verify-push-20260928.txt',
          '_tmp-dryrun-20260928.txt', '_tmp-apply-20260928.txt']:
    p = os.path.join(T, f)
    print(('OK  ' if os.path.isfile(p) else '缺失'), f, os.path.getsize(p) if os.path.isfile(p) else '')

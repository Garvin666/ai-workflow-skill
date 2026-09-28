/*
 * geom-probe.js —— 渲染色取数器（页面侧），供 CDP 驱动（如 ui库 scripts/shoot-page.mjs）注入执行。
 *
 * 产出契约（与 check_aesthetics.py 的 extract_geom 一致）：
 *   { version, source, space, scale, scope, viewport:{w,h},
 *     nodes:[ {i, parent, tag, cls, text,
 *              rect:{x,y,w,h},            ← 坐标空间见下
 *              fontSize, fontWeight, color, bg, visible} ] }
 *
 * v2 两处修正（2026-09-26 第二轮，均由「真实 deck 页」实测暴露）：
 *
 *   ① **取数范围可限定**（可选参数 rootSelector）
 *      真页面上不止一个「画面」。ui库 的组件库演示页同时挂着 21 个主题缩略图 ——
 *      全文档取数会把缩略图里的色条也当成兄弟元素参与聚类，测出来的不是这张幻灯片。
 *      故支持 `__geomProbe('.ui-deck__slide--active')` 只取当前页。
 *      默认（不传参）仍是整文档，行为向后兼容。
 *
 *   ② **坐标归一化到「设计像素」**
 *      deck 舞台是「固定 1920x1080 画布 + transform:scale」。此时
 *      getBoundingClientRect() 给的是**缩放后**的渲染 px：同一张幻灯片按 0.53 缩放时，
 *      设计上的 8px 韵律网格在渲染 px 里只有 4.25px —— 直接拿渲染 px 去比 8px 网格会
 *      **整片假红**。故：rect 一律换算回设计 px，且**以作用域根为原点**
 *      （原点不归零的话，`y mod 8` 的相位由元素在整页里的滚动位置决定，同样无意义）。
 *      换算依据：根元素的 `--deck-canvas-width`（主题契约里的设计基准宽）。
 *      取不到该变量时 scale=1、space='rendered' —— **不猜测**，如实登记坐标空间。
 *
 * 用法（以 ui库 的 shoot-page.mjs 为例，它先跑 --prep 再跑 --eval）：
 *   node scripts/shoot-page.mjs --file=page.html \
 *        --prep="$(cat <skill>/scripts/geom-probe.js)" \
 *        --eval="return window.__geomProbe();" > geom.json                      # 整文档
 *   node scripts/shoot-page.mjs --file=page.html \
 *        --prep="$(cat .../geom-probe.js)" \
 *        --eval="return window.__geomProbe('.ui-deck__slide--active');" > geom.json
 *   python <skill>/scripts/check_aesthetics.py --rubric <判据集> --css a.css --geom geom.json
 *
 * 设计要点：
 *  · **只读 DOM，绝不改页面**（--prep 与 --eval 之间不做任何写操作）——
 *    "测量不得改变被测对象"，与 shoot-page.mjs 的 --prep 语义（摆状态）刻意区分。
 *  · `i` 按「文档序」编号，`parent` 存父节点的 **i**（作用域外/根为 null）—— 判据按 parent 分组，
 *    故父子关系必须来自同一次快照，不得二次查询。
 *  · 跳过 display:none / visibility:hidden / 零尺寸 的节点（不可见 ⇒ 无从谈版式）；
 *    但 `visible` 字段照实记录，判据侧再做取舍（不替判据决定）。
 *  · 颜色一律输出 **rgb() 整数三元组**，不输出 hex/命名色 —— 色彩数学在校验器侧统一。
 *  · 缺值不编造：拿不到就写 null，由判据侧判 SKIP。
 */
window.__geomProbe = function (rootSelector) {
  'use strict';

  var rd = function (v) { return Math.round(v * 100) / 100; };

  var toRgb = function (s) {
    if (!s) return null;
    var m = String(s).match(/rgba?\(\s*([\d.]+)[,\s]+([\d.]+)[,\s]+([\d.]+)/i);
    if (m) return [Math.round(+m[1]), Math.round(+m[2]), Math.round(+m[3])];
    // 仅兜底极少数以 hex 暴露的场景；不解析命名色（编造颜色比缺值更坏）
    var h = String(s).trim().match(/^#([0-9a-f]{6})$/i);
    if (h) return [parseInt(h[1].slice(0, 2), 16), parseInt(h[1].slice(2, 4), 16), parseInt(h[1].slice(4, 6), 16)];
    return null;
  };

  var visible = function (el) {
    var cs = getComputedStyle(el);
    if (cs.display === 'none' || cs.visibility === 'hidden' || parseFloat(cs.opacity) === 0) return false;
    var r = el.getBoundingClientRect();
    return r.width > 0 && r.height > 0;
  };

  var SEL = (typeof rootSelector === 'string' && rootSelector) ? rootSelector : null;
  var root = SEL ? document.querySelector(SEL) : document.body;

  if (!root) {
    // 作用域选择器没命中 —— 明确报「找不到」，返回空集。
    // （校验器侧对空节点集判 SKIP，不得当成「没有坏版式」而假绿。）
    return {
      version: '2', source: location.href, space: 'unknown', scale: null,
      scope: { selector: SEL, found: false },
      viewport: { w: window.innerWidth, h: window.innerHeight },
      nodes: []
    };
  }

  // ---- 坐标归一：缩放画布下，渲染 px ≠ 设计 px（且原点必须落在作用域根）----
  var rr = root.getBoundingClientRect();
  var canvasW = parseFloat(getComputedStyle(root).getPropertyValue('--deck-canvas-width')) || 0;
  var scale = 1;
  var space = 'rendered';
  if (canvasW > 0 && rr.width > 0) {
    var s = rr.width / canvasW;
    if (s > 0) { scale = s; space = 'design'; }
  }
  var toDesign = function (v) { return v / scale; };

  // 一次性、文档序遍历作用域内全部元素并建索引 —— 父子关系统一来自本次快照
  var all = [root].concat(Array.prototype.slice.call(root.querySelectorAll('*')));
  var idx = new Map();
  all.forEach(function (el, n) { idx.set(el, n); });

  var nodes = all.map(function (el, n) {
    var cs = getComputedStyle(el);
    var r = el.getBoundingClientRect();
    var p = el.parentElement;
    var own = Array.prototype.slice.call(el.childNodes)
      .filter(function (c) { return c.nodeType === 3; })
      .map(function (c) { return c.nodeValue; }).join('').replace(/\s+/g, ' ').trim();
    return {
      i: n,
      // 父节点在作用域内才记 i；作用域外（含根）为 null ⇒ 判据不会跨作用域聚类
      parent: (p && p !== el && idx.has(p)) ? idx.get(p) : null,
      tag: el.tagName.toLowerCase(),
      cls: (el.getAttribute('class') || null),
      text: own || null,
      rect: {
        x: rd(toDesign(r.left - rr.left)),
        y: rd(toDesign(r.top - rr.top)),
        w: rd(toDesign(r.width)),
        h: rd(toDesign(r.height))
      },
      fontSize: parseFloat(cs.fontSize) || null,
      fontWeight: cs.fontWeight || null,
      color: toRgb(cs.color),
      bg: toRgb(cs.backgroundColor),
      visible: visible(el)
    };
  });

  return {
    version: '2',
    source: location.href,
    space: space,
    scale: rd(scale),
    scope: { selector: SEL, found: true, rect_rendered: { w: rd(rr.width), h: rd(rr.height) } },
    viewport: { w: window.innerWidth, h: window.innerHeight },
    nodes: nodes
  };
};

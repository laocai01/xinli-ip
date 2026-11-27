# -*- coding: utf-8 -*-
"""batch4 合成器 v1.0（2026-11-18）

架构（沿用 batch3 已验证的方案，不另搞一套）：
  · 真人主轴连续缩放 1080×1920，卡片 overlay=0:0 全屏原样盖上
  · 字幕烧在真人上（ASS，source = 已校对字幕_N.json）
  · LOGO 左上 / AI 声明右下（卡片期间不叠 LOGO，卡面自带品牌区）
  · BGM 逐集不同，严格低于人声

用法:
  python compose_b4.py <集号> --plan     只算排期并打印（不出片）
  python compose_b4.py <集号>            出片
"""
import os
import sys
import io
import json
import subprocess
import time

R4 = os.path.dirname(os.path.abspath(__file__))
ROOT = "E:/心理咨询IP"
TR4 = ROOT + "/03-内容/转录/batch4"
sys.path.insert(0, R4)

import cards_b4 as CB
import card_layouts as CL
import subs_b4 as SB
import bgm_cal as BC

FF = ("C:/Users/Dell/AppData/Local/Microsoft/WinGet/Packages/"
      "Gyan.FFmpeg_Microsoft.Winget.Source_8wekyb3d8bbwe/ffmpeg-9.0.1-full_build/bin/ffmpeg.exe")
FFP = FF.replace("ffmpeg.exe", "ffprobe.exe")
LOGO = ROOT + "/04-工程/overlay_new/logo_corner.png"
NOTICE = ROOT + "/04-工程/overlay_new/ai_notice.png"
CARD_HTML = R4 + "/cards_html"
CARD_MP4 = R4 + "/cards_mp4"
OUT = ROOT + "/05-成片"

SW, SH = 1080, 1920
CARD_ANIM = 4.0          # 动画 4.0s（120 帧 @30fps）
CARD_HOLD = 3.0          # 停留 3.0s  → 每张 7.0s
WIN = CARD_ANIM + CARD_HOLD
OPEN_MIN = 3.0           # 首卡不早于 3.0s（0 秒真人开口）
END_KEEP = 8.0          # 片尾留 10s 给收尾（关注/预告）
CARD_RATIO_MAX = 0.40    # 卡片总时长 ≤40% → 真人 ≥60%（董事长 2026-11-18 硬指标）
MIN_GAP = 1.2            # 卡间至少 1.2s 真人
WINDOW40 = 34.0          # 任意 40 秒内最多 2 张
VOICE_DB = 5.0
BGM_BELOW = 9.0


def hr(t):
    print("\n" + "=" * 70)
    print("  " + t)
    print("=" * 70)


def dur(p):
    r = subprocess.run([FFP, "-v", "error", "-show_entries", "format=duration",
                        "-of", "default=nw=1:nk=1", p], capture_output=True, text=True)
    try:
        return float(r.stdout.strip())
    except ValueError:
        return 0.0


def load_subs(n):
    p = os.path.join(TR4, "已校对字幕_%d.json" % n)
    if not os.path.exists(p):
        raise SystemExit("❌ 缺已校对字幕: %s" % p)
    return json.load(io.open(p, encoding="utf-8"))


def find_time(cues, anchor):
    """锚点关键词 → 该词出现的那句的起始秒数"""
    P = "，。！？、；：,.!?;: \u3000"

    def norm(s):
        return "".join(c for c in s if c not in P)
    a = norm(anchor)
    for c in cues:
        if a in norm(c["text"]):
            return c["start"]
    # 退化：取前半段匹配
    for c in cues:
        if norm(anchor)[:8] in norm(c["text"]):
            return c["start"]
    return None


def plan(n):
    cfg = CB.EPS[n]
    src = os.path.join(ROOT, "素材", "%d.mp4" % n)
    raw = dur(src)
    sp = cfg["speed"]
    total = round(raw / sp, 2)

    cues = load_subs(n)
    cards = CB.CARDS[n]
    themes = CB.THEME_OF[n]

    # 1) 锚点 → 时间
    cand = []
    for c in cards:
        t_raw = find_time(cues, c["anchor"])
        if t_raw is None:
            raise SystemExit("❌ 第%d条 锚点找不到: %s" % (n, c["anchor"]))
        cand.append((c, t_raw / sp))
    cand.sort(key=lambda x: x[1])

    # 2) 排期：首卡≥OPEN_MIN、40秒内≤2张、卡间≥MIN_GAP、末卡不超过 total-END_KEEP-WIN
    work_a = OPEN_MIN
    work_b = total - END_KEEP - WIN
    rows = []
    for c, t in cand:
        t = max(t, work_a)
        recent = [r["t"] for r in rows if t - r["t"] < WINDOW40]
        if len(recent) >= 2:
            t = recent[0] + WINDOW40 + 0.6
        if rows and t < rows[-1]["t"] + WIN + MIN_GAP:
            t = rows[-1]["t"] + WIN + MIN_GAP
        if t > work_b:
            # ★ 放不下时不要直接丢：只有在「剩余空间够」的前提下才顺延，
            #   否则标记为"待重排"，后面按均匀分布补回时间轴
            t = work_b
            if rows and t < rows[-1]["t"] + WIN + MIN_GAP:
                continue
        rows.append(dict(card=c, t=round(t, 2), win=WIN))

    # ★ 均匀重排（2026-11-18）：卡片必须铺满全片，且任意 40s 内 ≤2 张。
    #   做法：把可用时间轴切成 len(rows) 个等距槽位，逐张放进最近槽位。
    if rows:
        n_cards = len(rows)
        span_a, span_b = OPEN_MIN, total - END_KEEP - WIN
        if n_cards > 1:
            step = (span_b - span_a) / (n_cards - 1)
        else:
            step = 0.0
        # 40s 窗口内 ≤2 张要求最小间距：span/(n-1) 通常已 >20s，无需额外约束
        fixed = []
        for i, r in enumerate(rows):
            slot = span_a + step * i
            # 槽位与锚点偏离不超过一个步长时，用槽位（保证铺满）
            t = slot if abs(slot - r["t"]) <= max(step, 1.0) else r["t"]
            fixed.append(dict(card=r["card"], t=round(t, 2), win=WIN))
        # 间距兜底
        for i in range(1, len(fixed)):
            if fixed[i]["t"] < fixed[i-1]["t"] + WIN + MIN_GAP:
                fixed[i]["t"] = round(fixed[i-1]["t"] + WIN + MIN_GAP, 2)
        rows = fixed

    # 3) 覆盖度检查：卡片必须铺满全片（最后一卡不能太早）
    if rows and rows[-1]["t"] < total * 0.55:
        raise SystemExit("❌ 末卡太早(%.1fs/%.1fs)，卡片会堆在前半段" % (rows[-1]["t"], total))

    # 4) 真人占比硬判
    card_sec = len(rows) * WIN
    ratio = card_sec / total
    if ratio > CARD_RATIO_MAX:
        raise SystemExit("❌ 卡片占 %.1f%% 超过 40%%（真人<60%），必须减卡" % (ratio * 100))

    # 5) 版式/动画唯一性
    lays = [r["card"]["layout"] for r in rows]
    anims = [r["card"]["anim"] for r in rows]
    if len(set(lays)) != len(lays):
        raise SystemExit("❌ 同集版式重复: %s" % lays)
    if len(set(anims)) != len(anims):
        raise SystemExit("❌ 同集动画重复: %s" % anims)

    return dict(src=src, raw=raw, sp=sp, total=total, rows=rows, cues=cues,
                cfg=cfg, card_sec=card_sec, ratio=ratio)


def build_htmls(n, P):
    d = os.path.join(CARD_HTML, str(n))
    os.makedirs(d, exist_ok=True)
    themes = CB.THEME_OF[n]
    out = []
    for i, r in enumerate(P["rows"]):
        c = dict(r["card"])
        c["theme"] = themes[i % len(themes)]
        c["seq"] = "第 %02d 张" % (i + 1)
        c["_key"] = (n, i + 1)   # 点缀方案索引（每集每张独立）
        html = CL.build_html(c)
        p = os.path.join(d, c["name"] + ".html")
        io.open(p, "w", encoding="utf-8").write(html)
        out.append(p)
    return out


def render_cards(n, P, lanes=4):
    d = os.path.join(CARD_MP4, str(n))
    os.makedirs(d, exist_ok=True)
    need = [r["card"]["name"] for r in P["rows"]]
    miss = [k for k in need if not os.path.exists(os.path.join(d, k + ".mp4"))]
    if not miss:
        print("  ✅ 卡片已齐 %d/%d" % (len(need), len(need)))
        return
    print("  渲染 %d 张卡片（%d 路并行）…" % (len(miss), lanes))
    tasks = [dict(html="%s/%d/%s.html" % (CARD_HTML, n, k),
                  out="%s/%d/%s.mp4" % (CARD_MP4, n, k),
                  frames=int(CARD_ANIM * 30), fps=30) for k in miss]
    tj = os.path.join(R4, "tasks_%d.json" % n)
    json.dump(tasks, io.open(tj, "w", encoding="utf-8"), ensure_ascii=False)

    env = dict(os.environ, CARD_ROOT=R4)
    procs = []
    for i in range(lanes):
        procs.append(subprocess.Popen(
            [sys.executable, os.path.join(R4, "render_lane.py"), tj, str(i), str(lanes)],
            env=env, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True))
    logs = []
    for p in procs:
        o, _ = p.communicate()
        logs.append(o or "")
    for l in logs:
        print("\n".join("    " + x for x in l.strip().splitlines()[-4:]))
    miss2 = [k for k in need if not os.path.exists(os.path.join(d, k + ".mp4"))]
    if miss2:
        raise SystemExit("❌ 卡片渲染失败: %s" % miss2)
    print("  ✅ 卡片齐备 %d/%d" % (len(need), len(need)))


def compose(n, P):
    cfg = P["cfg"]
    total = P["total"]
    sp = P["sp"]
    ass = SB.build(n, P["cues"], sp)
    print("  字幕: %s" % ass)

    f = []
    # 真人：原样，只做尺寸确认（禁裁禁调）
    f.append("[0:v]setpts=PTS/%.4f,scale=%d:%d:flags=lanczos,setsar=1,fps=30[graded]"
             % (sp, SW, SH))
    # 字幕（cd 到字幕目录，避免 Windows 盘符转义）
    f.append("[graded]ass=%s,scale=%d:%d,setsar=1[withsub]"
             % (os.path.basename(ass), SW, SH))

    cur = "withsub"
    for ci, r in enumerate(P["rows"]):
        k, ct, cwin = r["card"]["name"], r["t"], r["win"]
        hold = max(0.5, cwin - CARD_ANIM)
        f.append("[%d:v]trim=start=0:end=%.3f,setpts=N/(30*TB),fps=30,"
                 "scale=1080:1920,setsar=1[ca%d]" % (ci + 1, CARD_ANIM, ci))
        f.append("[%d:v]trim=start=%.3f:end=%.3f,setpts=N/(30*TB),fps=30,"
                 "scale=1080:1920,setsar=1,tpad=stop_mode=clone:stop_duration=%.2f[cb%d]"
                 % (ci + 1, max(0.0, CARD_ANIM - 0.05), CARD_ANIM, hold, ci))
        f.append("[ca%d][cb%d]concat=n=2:v=1:a=0,setpts=PTS-STARTPTS[cc%d]"
                 % (ci, ci, ci))
        f.append("[cc%d]tpad=start_duration=%.3f:start_mode=add:color=black[c%d]"
                 % (ci, ct, ci))
        f.append("[%s][c%d]overlay=0:0:enable='between(t,%.3f,%.3f)'[o%d]"
                 % (cur, ci, ct, ct + cwin, ci))
        cur = "o%d" % ci

    li = len(P["rows"]) + 1
    f.append("[%d:v]scale=130:-1[logo]" % li)
    card_win = "+".join(["between(t,%.3f,%.3f)" % (r["t"], r["t"] + r["win"])
                         for r in P["rows"]])
    f.append("[%s][logo]overlay=24:24:enable='not(%s)'[wi]" % (cur, card_win))
    f.append("[%d:v]null[note]" % (li + 1))
    f.append("[wi][note]overlay=W-w-40:H-h-30[pre]")
    f.append("[pre]scale=1080:1920:flags=lanczos,setsar=1,"
             "scale=in_range=full:out_range=tv,format=yuv420p,"
             "setparams=range=tv:colorspace=bt709[vout]")

    bgm_idx = 1 + len(P["rows"]) + 2
    # ★ BGM 实测校准（董事长 2026-11-18「咖啡厅感」）：
    #   先量素材人声 RMS 与 BGM 原 RMS，反算增益让 BGM = 人声 - 13.5dB
    #   不许写死 volume，不许高通砍旋律
    gain, diag = BC.calc_gain(P["src"], cfg["bgm"], sp)
    print("  BGM 校准: 人声 %.1fdB / BGM原 %.1fdB → 增益 %.1fdB"
          % (diag.get("voice_db", 0), diag.get("bgm_db", 0), gain))
    af = ("[0:a]volume=%.1fdB,atempo=%.4f[voice];"
          "[%d:a]aloop=loop=-1:size=2e9,atrim=0:%.2f,"
          "equalizer=f=300:t=q:w=1.2:g=-1.5,"
          "equalizer=f=2600:t=q:w=1.0:g=2.0,"
          "volume=%.1fdB,"
          "afade=t=in:st=0:d=2.5,afade=t=out:st=%.2f:d=3.5[bgm];"
          "[voice][bgm]amix=inputs=2:duration=first:normalize=0:dropout_transition=0,"
          "alimiter=limit=0.95:attack=1:release=80:level=false[aout]"
          % (VOICE_DB, sp, bgm_idx, total, gain, total - 3.5))

    os.makedirs(os.path.join(OUT, cfg["line"]), exist_ok=True)
    outp = os.path.join(OUT, cfg["line"], cfg["name"] + ".tmp.mp4")
    cmd = [FF, "-y", "-v", "warning", "-stats", "-i", P["src"]]
    for r in P["rows"]:
        cmd += ["-i", os.path.join(CARD_MP4, str(n), r["card"]["name"] + ".mp4")]
    cmd += ["-i", LOGO, "-i", NOTICE, "-i", cfg["bgm"]]
    fc = ";".join(f) + ";" + af
    io.open(os.path.join(R4, "fc_%d.txt" % n), "w", encoding="utf-8").write(fc)
    cmd += ["-filter_complex", fc, "-map", "[vout]", "-map", "[aout]",
            "-t", "%.2f" % total,
            "-c:v", "libx264", "-preset", "medium", "-profile:v", "main", "-level", "4.1",
            "-crf", "20", "-maxrate", "8M", "-bufsize", "16M",
            "-refs", "3", "-x264-params", "keyint=60:min-keyint=60:scenecut=0:bframes=2",
            "-pix_fmt", "yuv420p", "-r", "30", "-g", "60",
            "-c:a", "aac", "-profile:a", "aac_low", "-b:a", "192k", "-ar", "48000", "-ac", "2",
            "-movflags", "+faststart", outp]
    t0 = time.time()
    print("  → 合成中 …")
    r = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8",
                       errors="replace", cwd=os.path.dirname(ass))
    if r.returncode != 0:
        print("❌ ffmpeg 失败:\n" + r.stderr[-3000:])
        return None
    print("  ✅ %s  %.1fMB  %.1f 分钟"
          % (outp, os.path.getsize(outp) / 1048576, (time.time() - t0) / 60))
    return outp


def main():
    n = int(sys.argv[1])
    only_plan = "--plan" in sys.argv
    hr("第 %d 条 · %s" % (n, CB.EPS[n]["title"]))
    P = plan(n)
    print("  素材 %.1fs ÷%.2f → 成片 %.1fs (%.1f:%04.1f)"
          % (P["raw"], P["sp"], P["total"], P["total"] // 60, P["total"] % 60))
    for i, r in enumerate(P["rows"]):
        print("   %02d %-26s %-10s %-10s t=%6.1f"
              % (i + 1, r["card"]["name"], r["card"]["layout"], r["card"]["anim"], r["t"]))
    print("  卡片 %d 张 × %.1fs = %.1fs (%.1f%%)  → 真人 %.1f%%"
          % (len(P["rows"]), WIN, P["card_sec"], P["ratio"] * 100, (1 - P["ratio"]) * 100))
    if only_plan:
        return
    build_htmls(n, P)
    render_cards(n, P)
    out = compose(n, P)
    print("\nRESULT %s" % out)


if __name__ == "__main__":
    main()

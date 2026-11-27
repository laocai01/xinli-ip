# -*- coding: utf-8 -*-
"""进度落盘：董事长关机会问"到哪了"，这个文件必须能直接读出结论
   用法: python status.py            → 只看
        python status.py note "xx"   → 追加一条备注
"""
import io, json, os, subprocess, sys, time

ROOT = "E:/心理咨询IP"
R = ROOT + "/04-工程/batch2"
OUT = ROOT + "/05-成片"
DOC = ROOT + "/09-方案文档/第二批11-16_制作进度_20261024.md"
FFP = r"C:/Users/Dell/AppData/Local/Microsoft/WinGet/Packages/Gyan.FFmpeg_Microsoft.Winget.Source_8wekyb3d8bbwe/ffmpeg-9.0.1-full_build/bin/ffprobe.exe"

NAMES = {
    1: "第11条 怎么跟一个不说话的人把话说上",
    2: "第12条 你一歇下来就发慌",
    3: "第13条 两口子没话说了是从哪一天开始的",
    4: "第14条 怎么把话说到孩子心里去",
    5: "第15条 你越来越不敢麻烦孩子了",
    6: "第16条 如果遇见二十岁的自己你会说什么",
}


def dur(p):
    try:
        return float(subprocess.run([FFP, "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", p],
                                    capture_output=True, text=True, timeout=20).stdout.strip())
    except Exception:
        return 0.0


def stat(n):
    clean = "%s/素材_clean/%d.mp4" % (ROOT, n)
    eye = "%s/素材_clean/eye_%d.mp4" % (ROOT, n)
    mid = "%s/素材_clean/%d.mp4.mid.mp4" % (ROOT, n)
    d = json.load(io.open("%s/final_%d.json" % (R, n), encoding="utf-8")) if os.path.exists("%s/final_%d.json" % (R, n)) else None
    line = {"A线": "没人可说", "B线": "我是不是没用了"}[ "A线" if n <= 3 else "B线" ]
    fin = None
    for f in os.listdir(OUT) if os.path.isdir(OUT) else []:
        p = os.path.join(OUT, f)
        if os.path.isdir(p):
            for g in os.listdir(p):
                if g.startswith("第%d条" % (n + 22)):
                    fin = os.path.join(p, g)
    return dict(sub=os.path.exists(clean), eye=os.path.exists(eye), proc=os.path.exists(mid),
                final=fin, sub_dur=dur(clean) if os.path.exists(clean) else 0,
                final_dur=dur(fin) if fin else 0,
                cues=len(d["cues"]) if d else 0)


def main():
    rows = []
    for n in range(1, 7):
        s = stat(n)
        if s["final"]:
            stage = "✅ 成片已出"
        elif s["sub"]:
            stage = "去反光完成，待合成"
        elif s["proc"]:
            stage = "去反光中"
        else:
            stage = "排队"
        rows.append((n, NAMES[n], stage, s))

    md = ["# 第二批 11–16 制作进度", "",
          "**更新时间**：%s" % time.strftime("%Y-%m-%d %H:%M"), "",
          "| 集 | 标题 | 进度 | 字幕条数 | 去反光 | 眼部特写 | 成片 |", "|---|---|---|---|---|---|---|"]
    for n, name, stage, s in rows:
        md.append("| %d | %s | %s | %d | %s | %s | %s |" % (
            n, name, stage, s["cues"], "✅" if s["sub"] else ("⏳" if s["proc"] else "—"),
            "✅" if s["eye"] else "—",
            ("✅ %.1fs" % s["final_dur"]) if s["final"] else "—"))
    md += ["", "## 本批定的硬规矩（验收口径）", "",
           "- **成片 176 秒**（3 分钟内，手机直传抖音/视频号）",
           "- **语速 232–254 字/分**（正常讲解区间，不许为了压时长硬加速）",
           "- 字幕与口播逐条对齐到最后一秒：无空档、无重叠",
           "- 卡片每张都动，但 2 秒内动完，其余时间完全静止可读",
           "- 验收 18 项机器全过后才允许交付（见 verify_batch2.py）",
           "- 合规禁词扫描 0 命中（compliance_check.py）",
           "- 反光修复 pip 主线：pipeline2_one.py（去反光 + 眼部特写小窗，同一帧不二次编码）",
           ""]
    if len(sys.argv) > 2 and sys.argv[1] == "note":
        md += ["## 备注", "", sys.argv[2], ""]
    io.open(DOC, "w", encoding="utf-8").write("\n".join(md))
    print("\n".join(md[:14]))
    print("\n→ 写入:", DOC)


if __name__ == "__main__":
    main()

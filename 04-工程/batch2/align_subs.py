# -*- coding: utf-8 -*-
"""字幕草稿 v4（最终形态）
   · 全篇字符级对齐（ASR ↔ 提词稿）：同音字用稿子，临场发挥保留 ASR 原话
   · 稿子的标点回填到时间轴 → 按标点断句，单条 ≤13 字
   · 产出 draft_<n>.json（cues: start/end/text）
"""
import json, io, os, re, sys, difflib

ROOT = "E:/心理咨询IP"
TR = ROOT + "/03-内容/转录/batch2"
PROMPT = ROOT + "/03-内容/提词器_定稿"
OUT = ROOT + "/04-工程/batch2"
MAXLEN = 13
PUNCT = "，。、；：！？“”‘’（）《》…—·"

MAP = {
 1: "11_A线第4讲_怎么跟一个不说话的人把话说上.md",
 2: "12_A线第5讲_你一歇下来就发慌.md",
 3: "13_A线第6讲_两口子没话说了是从哪一天开始的.md",
 4: "14_B线第4讲_怎么把话说到孩子心里去.md",
 5: "15_B线第5讲_你越来越不敢麻烦孩子了.md",
 6: "16_B线第6讲_如果遇见二十岁的自己你会说什么.md",
}


def norm_ch(c):
    return not (c.isspace() or c in PUNCT or c in ",.;:!?\"'()《》-")


def script_full(path):
    parts = []
    for raw in io.open(path, encoding="utf-8").read().split("\n"):
        s = raw.strip()
        if s.startswith("【"):
            break
        if not s or s.startswith("#") or s.startswith(">") or s.startswith("---"):
            continue
        s = s.replace("★", "")
        s = re.sub(r"（[^）]*）", "", s)
        s = re.sub(r"\*\*", "", s).strip()
        if s:
            parts.append(s)
    return "".join(parts)


def build(n, verbose=False):
    d = json.load(io.open(os.path.join(TR, "raw_%d.json" % n), encoding="utf-8"))
    sc = script_full(os.path.join(PROMPT, MAP[n]))

    # 稿子：规范化字符序列 + 反查索引
    norm_idx = [i for i, ch in enumerate(sc) if norm_ch(ch)]
    scn = "".join(sc[i] for i in norm_idx)

    # ASR：规范化字符 + 时间
    ac, at = [], []
    for seg in d["segs"]:
        t = seg["text"].replace(" ", "")
        if not t:
            continue
        a, b = seg["start"], seg["end"]
        chars = [c for c in t if norm_ch(c)]
        for i, c in enumerate(chars):
            ac.append(c)
            at.append((a + (b - a) * i / len(chars), a + (b - a) * (i + 1) / len(chars)))
    asr = "".join(ac)

    sm = difflib.SequenceMatcher(None, asr, scn, autojunk=False)
    seq = []          # (char, t0, t1)
    flags = []
    for tag, i1, i2, j1, j2 in sm.get_opcodes():
        if tag in ("equal", "replace"):
            if tag == "replace":
                sim = difflib.SequenceMatcher(None, asr[i1:i2], scn[j1:j2]).ratio()
                flags.append(dict(t=at[i1][0], asr=asr[i1:i2], script=scn[j1:j2], r=round(sim, 2)))
                if len(asr[i1:i2]) >= 6 and sim < 0.3:   # 长段且完全不同 = 临场改词 → 保留原话
                    seq += [(asr[k], at[k][0], at[k][1]) for k in range(i1, i2)]
                    continue
            if i2 <= i1 or j2 <= j1:
                continue
            t0, t1 = at[i1][0], at[i2 - 1][1]
            # 稿子这段原文（含内部标点）
            seg_txt = sc[norm_idx[j1]:norm_idx[j2 - 1] + 1]
            # 允许补上后面紧跟的标点
            k = norm_idx[j2 - 1] + 1
            while k < len(sc) and sc[k] in PUNCT:
                seg_txt += sc[k]; k += 1
            cnt = j2 - j1
            step = (t1 - t0) / max(1, cnt)
            ci = 0
            for ch in seg_txt:
                if norm_ch(ch):
                    a = t0 + step * ci
                    b = t0 + step * (ci + 1)
                    ci += 1
                else:
                    a = t0 + step * ci
                    b = a + step * 0.5
                seq.append((ch, a, b))
        elif tag == "delete":
            seq += [(asr[k], at[k][0], at[k][1]) for k in range(i1, i2)]
            flags.append(dict(t=at[i1][0], asr=asr[i1:i2], script="<临场发挥>", r=0.0))
        # insert → 漏念，丢弃

    # 断句：标点处断（≥4 字时），否则满 MAXLEN 断
    cues, cur = [], []
    for ch, a, b in seq:
        cur.append((ch, a, b))
        nl = sum(1 for c, _, _ in cur if norm_ch(c))
        if (ch in "，。！？；：" and nl >= 4) or nl >= MAXLEN:
            cues.append(cur); cur = []
    if cur:
        cues.append(cur)

    out = []
    for c in cues:
        txt = "".join(x[0] for x in c)
        txt = txt.translate({ord(q): None for q in '"“”‘’'})
        txt = txt.strip(PUNCT + " ")
        if not txt:
            continue
        out.append(dict(start=round(c[0][1], 2), end=round(c[-1][2], 2), text=txt))
    # 合并过短条（<5 字）到前一条
    merged = []
    for c in out:
        if merged and len(re.sub(r"[^\w]", "", c["text"])) < 5:
            merged[-1]["text"] += c["text"]
            merged[-1]["end"] = c["end"]
        else:
            merged.append(c)
    out = merged
    # 去重叠
    for i in range(len(out) - 1):
        if out[i]["end"] > out[i + 1]["start"]:
            out[i]["end"] = round(out[i + 1]["start"] - 0.01, 2)

    res = dict(n=n, src=os.path.basename(d["src"]), duration=d["duration"], cues=out, flags=flags)
    json.dump(res, io.open(os.path.join(OUT, "draft_%d.json" % n), "w", encoding="utf-8"),
              ensure_ascii=False, indent=1)
    with io.open(os.path.join(OUT, "draft_%d.md" % n), "w", encoding="utf-8") as f:
        f.write("# 素材 %d  %s  %.1fs  %d 条\n\n## 差异/临场区间\n\n" % (n, res["src"], res["duration"], len(out)))
        for x in flags:
            f.write("- [%7.1fs] r=%.2f ASR:`%s` / 稿:`%s`\n" % (x["t"], x["r"], x["asr"][:40], x["script"][:40]))
        f.write("\n## 字幕\n\n")
        for i, c in enumerate(out):
            f.write("%3d [%7.2f -> %7.2f] %s\n" % (i, c["start"], c["end"], c["text"]))
    if verbose:
        print(io.open(os.path.join(OUT, "draft_%d.md" % n), encoding="utf-8").read())
    return res


if __name__ == "__main__":
    for n in [int(x) for x in (sys.argv[1:] or ["1", "2", "3", "4", "5", "6"])]:
        r = build(n)
        print("draft %d: %.1fs cues=%d flags=%d  末句 %.1fs" %
              (n, r["duration"], len(r["cues"]), len(r["flags"]), r["cues"][-1]["end"]))

# -*- coding: utf-8 -*-
"""字幕定稿：成片字幕 = 真实口播（ASR 分段）+ 提词稿校正同音错字

核心原则（董事长定的口径）：
  1. 字幕必须和真人讲的每一句一致，讲到最后一秒
  2. 以提词稿为"正确写法"，临场发挥保留原话
  3. 断句以 ASR 的自然停顿为一句（不会切在词中间），超长再按安全切点拆
  4. 下集预告不收进成片

用法：
    python final_text2.py 2 3 4 5 6
输出：
    final_N.json  （时间轴 = 素材原始时间，成片端统一除以倍速）
"""
import io
import os
import re
import sys
import json
import difflib

ROOT = "E:/心理咨询IP/04-工程/batch2"
MAXLEN = 13
PUNCT = "，。！？、；：“”‘’（）「」…—·,.!?;:\"'() "

# 虚词/标点前后 = 自然断点，不切在词中间
SAFE_AFTER = set("的了吗呢吧啊着过就都也还才再又要会能可以是在对把被让给从向")


def nc(c):
    return not (c.isspace() or c in PUNCT)


def load_draft(n):
    return json.load(io.open(os.path.join(ROOT, "draft_%d.json" % n), encoding="utf-8"))


def load_prompt(n):
    """提词稿（正确写法）。没有就返回 None"""
    p = os.path.join(ROOT, "prompt_%d.txt" % n)
    if os.path.exists(p):
        return io.open(p, encoding="utf-8").read()
    return None


def fix_homophones(asr_text, prompt):
    """用提词稿校正 ASR 的同音错字：只在同长度片段上做替换，不改长度、不删内容"""
    if not prompt:
        return asr_text
    pb = "".join(c for c in prompt if nc(c))
    ab = asr_text
    sm = difflib.SequenceMatcher(None, pb, ab, autojunk=False)
    out = []
    for tag, i1, i2, j1, j2 in sm.get_opcodes():
        if tag == "equal":
            out.append(ab[j1:j2])
        elif tag == "replace" and (i2 - i1) == (j2 - j1):
            out.append(pb[i1:i2])          # 同长度：用提词稿的正确写法
        else:
            out.append(ab[j1:j2])          # 其他：保留 ASR 原话（临场发挥）
    return "".join(out)


def split_long(text):
    """超长句按安全切点拆，不切在词中间"""
    if len(text) <= MAXLEN:
        return [text]
    parts, cur = [], ""
    for ch in text:
        cur += ch
        if len(cur) >= MAXLEN - 2 and (ch in SAFE_AFTER or ch in "，。！？、；"):
            parts.append(cur)
            cur = ""
    if cur:
        parts.append(cur)
    # 仍超长的再均分
    out = []
    for p in parts:
        while len(p) > MAXLEN:
            out.append(p[:MAXLEN])
            p = p[MAXLEN:]
        if p:
            out.append(p)
    return out


def build(n):
    d = load_draft(n)
    segs = d["cues"]
    prompt = load_prompt(n)

    # 找预告起点（"下一讲/下一期/下集"），之后全部丢弃
    stop = len(segs)
    for i, s in enumerate(segs):
        if any(k in s["text"] for k in ("下一讲", "下一期", "下集", "下一条")):
            stop = i
            break

    asr_full = "".join(s["text"].replace(" ", "") for s in segs[:stop])
    fixed = fix_homophones(asr_full, prompt)

    # 逐字时间轴：把 ASR 所有段的字拼成一条连续流，每个字带上它在语音里的起止时间。
    # 这样断句可以跨段进行（ASR 的分段是按停顿切的，不是句子边界），
    # 断句只按"标点 + 长度 + 安全切点"，不会再被 ASR 的碎段绑死。
    char_t = []
    ai = 0
    for s_ in segs[:stop]:
        raw = s_["text"].replace(" ", "")
        chars = [c for c in raw if nc(c)]
        if not chars:
            continue
        a, b = s_["start"], s_["end"]
        step = (b - a) / len(chars)
        for k in range(len(chars)):
            ch_fixed = fixed[ai + k] if ai + k < len(fixed) else chars[k]
            char_t.append((ch_fixed, a + step * k, a + step * (k + 1)))
        ai += len(chars)

    # 现在把连续字流按"标点 + 长度 + 安全断点"切成字幕条
    def _flush(buf):
        if not buf:
            return
        txt = "".join(c for c, _, _ in buf).strip(PUNCT)
        if not txt:
            return
        t0 = round(buf[0][1], 2)
        t1 = round(buf[-1][2], 2)
        if t1 - t0 < 0.35:
            t1 = round(t0 + 0.35, 2)
        out.append(dict(start=t0, end=t1, text=txt))

    out = []
    buf = []
    for ch, t0, t1 in char_t:
        buf.append((ch, t0, t1))
        nlen = len(buf)
        # 断句条件：句末标点（够 4 字）/ 逗号顿号（够 8 字）/ 到上限且落在安全切点 / 硬上限
        brk = False
        if ch in "。！？" and nlen >= 4:
            brk = True
        elif ch in "，、；：》」" and nlen >= 8:
            brk = True
        elif nlen >= MAXLEN:
            # 到上限：只有落在安全切点才断，否则再多收几个字到自然断点（最多 +3）
            if ch in SAFE_AFTER or ch in PUNCT:
                brk = True
            elif nlen >= MAXLEN + 3:
                brk = True
        if brk:
            _flush(buf)
            buf = []
    _flush(buf)

    # 收尾碎片合并：末尾读不完的短条并回上一句
    while len(out) >= 2:
        last = out[-1]
        if (last["end"] - last["start"]) < 0.9 or len(last["text"]) <= 2:
            prev = out[-2]
            prev["text"] = prev["text"] + last["text"]
            prev["end"] = max(prev["end"], last["end"])
            out.pop()
        else:
            break

    # 时间单调化
    for i in range(1, len(out)):
        if out[i]["start"] < out[i - 1]["end"]:
            out[i]["start"] = round(out[i - 1]["end"], 2)
        if out[i]["end"] <= out[i]["start"]:
            out[i]["end"] = round(out[i]["start"] + 0.4, 2)

    res = dict(n=n, src=d.get("src", ""), duration=d["duration"], cues=out)
    json.dump(res, io.open(os.path.join(ROOT, "final_%d.json" % n), "w", encoding="utf-8"),
              ensure_ascii=False, indent=1)
    return res


if __name__ == "__main__":
    for n in [int(x) for x in (sys.argv[1:] or ["2"])]:
        r = build(n)
        c = r["cues"]
        print("EP%d 字幕 %d 条 | 首 %.2fs 末 %.2fs | 字数 %d" %
              (n, len(c), c[0]["start"], c[-1]["end"], sum(len(x["text"]) for x in c)))
        for x in c[:3]:
            print("   %.1f-%.1f %s" % (x["start"], x["end"], x["text"]))
        print("   ...")
        for x in c[-2:]:
            print("   %.1f-%.1f %s" % (x["start"], x["end"], x["text"]))

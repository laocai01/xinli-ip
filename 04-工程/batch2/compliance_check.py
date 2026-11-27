# -*- coding: utf-8 -*-
"""合规机检：字幕/正文/卡片文字全扫一遍，禁词、夸大承诺、医疗式表述，一处都不放过
   用法: python compliance_check.py
"""
import io, json, os, re, glob

R = "E:/心理咨询IP/04-工程/batch2"
CARDS = "E:/心理咨询IP/04-卡片/batch2"

# 医疗/夸大/承诺类禁词（心理赛道最容易被限流的）
BAN = [
    "治疗", "治愈", "诊断", "确诊", "痊愈", "治好", "根治", "药到病除",
    "保证", "包治", "有效", "疗效", "疗程", "处方", "用药", "吃药",
    "抑郁症", "焦虑症", "强迫症", "精神病", "心理病", "患者", "病人",
    "专家", "名医", "权威", "唯一", "最有效", "百分百",
    "国家级", "全国第一", "排名第一", "第一名", "第一名医",
    "加我微信", "私信我领", "扫码", "点击链接", "购买", "下单", "优惠",
    "转发抽奖", "免费领取", "限时",
]
# 平台敏感词（政治/低俗/引战）
SENS = ["国家", "政府", "领导", "政治", "色情", "裸", "赌博", "暴力", "死亡", "自杀"]

# 必须存在的合规要素
MUST = {
    "AI 声明": "AI",
}


def scan_text(txt, where, hits):
    for w in BAN:
        if w in txt:
            hits.append((where, "禁词", w))
    for w in SENS:
        for m in re.finditer(w, txt):
            s = max(0, m.start() - 6)
            hits.append((where, "敏感", txt[s:m.end() + 6]))


def main():
    hits = []
    for n in range(1, 7):
        d = json.load(io.open(os.path.join(R, "final_%d.json" % n), encoding="utf-8"))
        full = "".join(c["text"] for c in d["cues"])
        scan_text(full, "EP%d 字幕" % n, hits)
    # 卡片文字
    ct = json.load(io.open(os.path.join(R, "card_texts.json"), encoding="utf-8"))
    for k, v in ct.items():
        scan_text("".join(v) if isinstance(v, list) else str(v), "卡片 " + k, hits)
    # 去重
    seen, uniq = set(), []
    for h in hits:
        if h not in seen:
            seen.add(h)
            uniq.append(h)
    print("命中 %d 处" % len(uniq))
    for h in uniq:
        print("  [%s] %s ← 「%s」" % (h[0], h[1], h[2]))
    return uniq


if __name__ == "__main__":
    main()

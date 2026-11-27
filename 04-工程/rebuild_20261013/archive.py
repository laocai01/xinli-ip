# -*- coding: utf-8 -*-
"""交付归档（事故整改项）——把 9 条成片 + 全部物料另存一份，并清掉旧命名残留
用法: python archive.py
落盘：E:/工作结果/交付归档/老蔡说_第一批9条_20261013/
       ├─ 01_成片/（9 条 mp4，规范名）
       ├─ 02_字幕/（已校对字幕源 json + 校对清单 + 待听音音频）
       ├─ 03_方案/（发布物料包 + 卡片品牌区规范 + 成片交付标准）
       └─ 归档说明.md
"""
import os, io, shutil, json, glob
ROOT = "E:/心理咨询IP"
DST = "E:/工作结果/交付归档/老蔡说_第一批9条_20261013"
SRC_LINE = {"没人可说": ["a", "b"], }

FILES = {  # 最终 9 条（规范名）
 "没人可说": ["第14条_没人可说第1讲_为什么你累得要死却睡不着_20261013.mp4",
            "第15条_没人可说第2讲_你不是脾气变了_20261013.mp4",
            "第16条_没人可说第3讲_家里那个最沉默的人_20261013.mp4"],
 "我是不是没用了": ["第17条_我是不是没用了第1讲_退休那天起我就没用了_20261013.mp4",
              "第18条_我是不是没用了第2讲_屋里安静得吓人_20261013.mp4",
              "第19条_我是不是没用了第3讲_我给孩子打电话没说两句就挂了_20261013.mp4"],
 "你根本不了解我": ["第20条_你根本不了解我第1讲_孩子不说话不代表没事_20261013.mp4",
              "第21条_你根本不了解我第2讲_你越问他越不说_20261013.mp4",
              "第22条_你根本不了解我第3讲_他考砸那天最怕的不是你骂他_20261013.mp4"],
}


def main():
    os.makedirs(DST + "/01_成片", exist_ok=True)
    os.makedirs(DST + "/02_字幕", exist_ok=True)
    os.makedirs(DST + "/03_方案", exist_ok=True)
    n_ok, n_miss = 0, []
    for line, names in FILES.items():
        for nm in names:
            s = os.path.join(ROOT, "05-成片", line, nm)
            if os.path.exists(s):
                shutil.copy2(s, os.path.join(DST, "01_成片", nm))
                n_ok += 1
                print("  ✅ %.1fMB  %s" % (os.path.getsize(s) / 1e6, nm))
            else:
                n_miss.append(s)
                print("  ❌ 缺: %s" % s)
    # 字幕与方案
    for s in glob.glob(ROOT + "/03-内容/字幕校对/*"):
        if os.path.isfile(s):
            shutil.copy2(s, os.path.join(DST, "02_字幕", os.path.basename(s)))
    if os.path.isdir(ROOT + "/03-内容/字幕校对/待听音_音频"):
        shutil.copytree(ROOT + "/03-内容/字幕校对/待听音_音频", DST + "/02_字幕/待听音_音频", dirs_exist_ok=True)
    for f in ["发布物料包_第一批9条_20261013.md", "卡片品牌区规范_定稿_20261012.md",
              "成片交付标准_v1.0_20261010.md", "动画规格定稿_20261008.md"]:
        s = os.path.join(ROOT, "09-方案文档", f)
        if os.path.exists(s):
            shutil.copy2(s, os.path.join(DST, "03_方案", f))
    for f in glob.glob(ROOT + "/04-工程/rebuild_20261013/*.py"):
        shutil.copy2(f, os.path.join(DST, "03_方案", "工程_" + os.path.basename(f)))
    # 旧的短名残留（被桌面端播放器锁住时删不掉，留着会混淆）
    stale = []
    for p in glob.glob(ROOT + "/05-成片/*/[0-9][0-9]_*.mp4"):
        try:
            os.remove(p); print("  🧹 清掉旧命名残留: %s" % os.path.basename(p))
        except Exception as e:
            stale.append(p); print("  ⚠ 旧命名残留删不掉（被占用，关掉播放器后可手动删）: %s" % p)
    io.open(os.path.join(DST, "归档说明.md"), "w", encoding="utf-8").write(
        "# 归档说明 · 老蔡说 第一批 9 条（重做版 2026-10-13）\n\n"
        "- 归档时间：2026-10-13（事故整改项：交付物必须另存归档）\n"
        "- 成片：%d 条（过渡片已发布，按董事长指示不改动、不入本归档）\n"
        "- 字幕：三轮校对共 259 处（规则表 188 + 逐字通读 33 + 对提词器定稿 38）\n"
        "- 卡片：停留按字数 max(3.0, 字数/5) 秒；首卡不早于 3.0s；末卡不盖结尾\n"
        "- 规格：1080×1920 / 30fps / H.264 / yuv420p / AAC 192k / CRF17 medium\n"
        "- 发布：见 03_方案/发布物料包_第一批9条_20261013.md（D2–D10，抖音 08:30）\n"
        % n_ok)
    print("\n归档完成: %s  （%d 条）" % (DST, n_ok))
    if n_miss:
        print("⚠ 缺失 %d 条，未归档" % len(n_miss))
    if stale:
        print("⚠ 残留 %d 个（被占用）" % len(stale))


if __name__ == "__main__":
    main()

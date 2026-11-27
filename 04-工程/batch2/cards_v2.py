# -*- coding: utf-8 -*-
"""卡片扩展方案 v2 —— 每集 12 张，覆盖全片

董事长要求原话：
  "你就4张卡片，怎么穿插整个视频，增加卡片，以后每集的卡片数量也是要增加，
   不能就4张，完全覆盖不了整个视频"

设计原则：
1. 卡片覆盖全片，间隔不超过 20 秒（原来 40 秒才一张，中间大段纯真人）
2. 每集卡片版式按内容轮换，不全是同一种版式
3. 卡片占用时长缩短到 4.5-7 秒（原来的 8-12 秒太长，像整屏切换）
4. 卡片期间真人仍在，卡片是叠加上去的信息层，不是覆盖切换
5. 关键词锚点取自 final_*.json 里的原句，保证和口播对得上
"""

# 结构: (卡片名, 版式, 关键词锚点, 参数)
# 版式: main=主卡 / three=三行机制卡 / quote=金句卡 / steps=方法卡
CARDS_V2 = {
 2: [  # 第24条 你一歇下来就发慌
   ("01_主_一歇就发慌",    "main",  "你一歇下来就发慌",
    dict(l1="你一歇下来", l2="就发慌", sub="不是你不想歇")),
   ("02_three_不敢闲",     "three", "还有一堆琐碎的事",
    dict(lead="不敢闲的人的日常", items=["事没做完，不敢停","脑子接着算账","身体歇了，心没歇"])),
   ("03_quote_三种反应",   "quote", "你有没有过这样的时候",
    dict(lead="歇下来的第一反应", big="不是轻松，是慌")),
   ("04_three_三段账",     "three", "账：那事还没弄完",
    dict(lead="你一躺下就开始算账", items=["那事还没弄完","那个电话还没打","那个人还在等你回"])),
   ("05_quote_不是懒",     "quote", "所以你不是懒",
    dict(lead="说清楚一件事", big="你不是懒，你是不敢闲")),
   ("06_three_随时待命",   "three", "一个随时待命的人",
    dict(lead="你把自己活成了", items=["手机不敢静音","有人找立刻放下碗","全年无休，从不请假"])),
   ("07_quote_一把尺子",   "quote", "是因为你心里有一把尺子",
    dict(lead="根子在这里", big="你心里有一把尺子")),
   ("08_three_从小听的",   "three", "而这把尺子，是从小拿起来的",
    dict(lead="这些话你听了半辈子", items=["你要懂事","你要争气","家里就靠你了"], tail="你做到了，可你也累坏了")),
   ("09_quote_放下来",     "quote", "那怎么把这把尺子放下来",
    dict(lead="第一件事", big="把「应该」换成「可以」")),
   ("10_steps_两件小事",   "steps", "就做两件事情",
    dict(lead="从今天起，做两件小事", items=["把「我应该」换成「我可以」","每天留五分钟，什么都不干"])),
   ("10a_three_五分钟",    "three", "第二件：每天给自己留五分钟",
    dict(lead="五分钟，具体怎么用", items=["不刷手机，刷手机也是填","坐着，站着，看窗外","什么都不干，就待着"])),
   ("10b_three_做不到",    "three", "我懂。可是你不用等",
    dict(lead="你会说：我做不到", items=["一歇下来就慌","一闲下来就愧疚","这不是你不行，是习惯了"], tail="习惯，是可以换掉的")),
   ("11_quote_架太久",     "quote", "懒，你是把自己架得太久了",
    dict(lead="记住这一句", big="那是你把自己，架得太久了")),
   ("12_steps_带人回来",   "steps", "把这条转给你家那个闲不下来",
    dict(lead="如果你身边有这样的人", items=["把这条转给他","跟他说一句：你可以歇","不是客套，是真的"])),
   ("13_quote_评论区",     "quote", "评论区打个数字",
    dict(lead="你是哪一种", big="打1 一歇就发慌 / 打2 一躺就不想动")),
 ],

 3: [  # 第25条 两口子没话说了是从哪一天开始的（锚点按 ep3 真实口播重写）
   ("01_主_没话说了",      "main",  "两口子没话说",
    dict(l1="两口子没话说", l2="是从哪一天开始的", sub="不是不爱了，是不再应声了")),
   ("02_quote_从嗯开始",   "quote", "是从嗯开始的",
    dict(lead="两个人变淡，从来不是从吵架开始", big="是从「嗯」开始的")),
   ("03_three_都是通知",   "three", "都是一句通知加一句收到",
    dict(lead="你们今天说过的几句话", items=["吃饭了。嗯。","水烧好了。","几点回来。再说吧"], tail="话都在，可没有一句是给对方的")),
   ("04_three_二十三年",   "three", "结婚二十三年",
    dict(lead="我认识一对夫妻，女的说我们没有矛盾也没话说", items=["上个月她看见一棵开花的树","拍了张照，看了看他的头像","又放下了"])),
   ("05_quote_不想让他看", "quote", "不是那棵树不好看",
    dict(lead="你听出来没有", big="是她已经不想让他看了")),
   ("06_quote_没被接住",   "quote", "感情不是被时间磨掉的",
    dict(lead="你以为感情是被时间磨淡的", big="是被一次次没被接住磨掉的")),
   ("07_quote_就不说了",   "quote", "次数多了",
    dict(lead="她跟你说个事，你在看手机", big="不是不想说，是把话收起来了")),
   ("08_steps_两件事",     "steps", "两件事今天就能做" if False else "特别简单",
    dict(lead="那咋办呢，特别简单", items=["她说话时，你放下手机看她一眼","应一声「嗯」——这叫我听见你了","每天有六秒，你是属于她的"])),
   ("09_quote_我在呢",     "quote", "靠的不是我爱你三个字",
    dict(lead="两口子过到后面", big="靠的是那句——哎，我在呢")),
   ("10_quote_我听见你了", "quote", "一次次我听见你了",
    dict(lead="说到底就是一句话", big="感情是靠一次次「我听见你了」撑住的")),
 ],
 4: [  # 第26条 怎么把话说到孩子心里去（锚点按 ep4 真实口播重写）
   ("01_主_说到心里",      "main",  "怎么把话说到孩子的心里去",
    dict(l1="怎么把话", l2="说到孩子的心里去", sub="不是靠讲道理")),
   ("02_quote_说成考核",   "quote", "说成了考核",
    dict(lead="你说了半天，他一句话没听进去", big="因为你把关心说成了考核")),
   ("03_three_问三句",     "three", "吃饭了没有",
    dict(lead="你给孩子打电话，是不是就问这三句", items=["吃饭了没有","忙不忙","钱够不够花"], tail="句句是真心，可句句都是问进度")),
   ("04_three_就冷了",     "three", "还行够用就没话了",
    dict(lead="他回你一句", items=["吃了","还行","够用"], tail="不是他不想聊，是你给的话头只能接一句")),
   ("05_three_两分半",     "three", "最长的一次是两分半",
    dict(lead="一位六十岁的大姐说", items=["跟儿子打电话最长两分半","因为那天儿子在开车","没手挂电话"])),
   ("06_quote_又来了",     "quote", "又来了",
    dict(lead="你一句问他忙不忙", big="他心里先冒出这两个字")),
   ("07_quote_只有两个字", "quote", "答案只有两个字",
    dict(lead="不是他烦你", big="是你问的问题，答案只有两个字")),
   ("08_steps_换话头",     "steps", "把问进度换成递话头",
    dict(lead="那咋办呢，记住这两句", items=["别说你要注意身体，说我看见你瘦了","先说你自己的感受","他才敢说他自己的事"])),
   ("09_quote_怎么撑过来", "quote", "你是怎么撑到现在的",
    dict(lead="他哪天说「我最近挺累的」", big="你就问这一句，别急着接「那你早点睡」")),
   ("10_quote_关心不是问", "quote", "关心不是问进度",
    dict(lead="说到底一句话", big="是让他有话可接")),
 ],
 5: [  # 第27条 年纪大了 有话不敢跟孩子说
   ("01_主_不敢麻烦孩子",  "main",  "你是不是越来越不敢麻烦孩子",
    dict(l1="越来越不敢", l2="麻烦孩子了", sub="不是不想他，是怕成负担")),
   ("02_three_干过的事",   "three", "你有没有干过这些事",
    dict(lead="这些话，你是不是常说", items=["你忙吧，没啥事","没事没事老毛病了","不用不用，我够花"], tail="你以为这叫懂事")),
   ("03_quote_一把门",     "quote", "一把门",
    dict(lead="其实你是在", big="把一扇门，一点点关上")),
   ("04_three_那位老师",   "three", "我认识一位退休的老师",
    dict(lead="他自己去复查，护士问家属呢", items=["他说：我没家属","语气特别平常","我听着心里一紧"])),
   ("05_quote_不是不需要", "quote", "他不是不需要人",
    dict(lead="他说不需要，其实", big="是怕一开口就成了麻烦")),
   ("06_three_他累在哪",   "three", "他累的",
    dict(lead="孩子真正难受的是", items=["你什么都不告诉他","他连帮你的机会都没有","他觉得你已经不需要他了"])),
   ("07_quote_小时候",     "quote", "他小时候发高烧",
    dict(lead="那时候", big="是谁背着他往医院跑")),
   ("08_quote_不是没用",   "quote", "你是怕自己没有用了",
    dict(lead="说穿了", big="你不是怕麻烦他，是怕自己没用了")),
   ("09_three_小口子",     "three", "找一个人",
    dict(lead="留一个小口子，让人能进来", items=["找一个人，或一件事","每天都等着你","早上给老伙计打个电话"])),
   ("10_quote_最难开口",   "quote", "你最难开口的",
    dict(lead="试着说这一句", big="儿子，我有件事想请你帮个忙")),
   ("11_quote_他会踏实",   "quote", "他反而心里踏实",
    dict(lead="你让他帮你一次", big="因为他感受到被你需要")),
   ("12_three_我们这代",   "three", "我们这一代人",
    dict(lead="一辈子都在扛", items=["扛家里，扛单位，扛孩子","最不习惯的是被人照顾","可被人惦记，不是你亏欠谁"])),
   ("13_quote_没有人等你", "quote", "人老了怕的不是累",
    dict(lead="说到底一句话", big="是没有人等你")),
   ("14_steps_转给孩子",   "steps", "把这条转给你的孩子",
    dict(lead="什么话都别说，转过去就行", items=["他会懂","你手上有没有一件","有人等着你的小事"])),
 ],
 6: [  # 第28条 如果遇见二十岁的自己
   ("01_主_二十岁的自己",  "main",  "遇见二十岁的自己",
    dict(l1="如果遇见", l2="二十岁的自己", sub="你会对他说什么")),
   ("02_quote_留给了别人", "quote", "你把最好的",
    dict(lead="回头看一看", big="一句都没留给你自己")),
   ("03_three_对自己狠",   "three", "你对谁都宽",
    dict(lead="别人一句难听的话", items=["你能记三年","孩子考上大学，你说应该的","老伙计夸你能干，你摆摆手说算啥"])),
   ("04_three_那位大爷",   "three", "我认识一位大爷",
    dict(lead="七十二岁，天天在小区下象棋", items=["孙子问他年轻时候的自己","他讲了半天，讲的全是别人的事","他说：我这一辈子没啥好说的"])),
   ("05_quote_没人问过",   "quote", "我心里咯噔一下",
    dict(lead="不是他没啥好说的", big="是从来没有人问过他")),
   ("06_quote_锁起来了",   "quote", "你以为不提就是放下",
    dict(lead="其实", big="你是把它锁起来了")),
   ("07_steps_三句话",     "steps", "睡觉之前",
    dict(lead="跟二十岁的自己说三句话", items=["这些年，你辛苦了","有一件事，你当年做得没有错","后面的路，我替你走完"])),
   ("08_quote_最缺的那句", "quote", "最缺的那一句",
    dict(lead="往往是", big="得由你自己说给自己听")),
   ("09_steps_写三件小事", "steps", "睡前写三件小事",
    dict(lead="今天让你心里舒服的小事，写三件", items=["每件后面加一句为什么","写一个星期","你看日子的眼神就变了"])),
   ("10_quote_眼睛挪开",   "quote", "不是日子变了",
    dict(lead="是你终于", big="把眼睛从「我没做好」挪开了")),
   ("11_quote_第一次来",   "quote", "你也是第一次来这世上",
    dict(lead="没有人教过你", big="你也不用一直当那个最懂事的人")),
   ("12_quote_辛苦了",     "quote", "最该被你说一句辛苦了",
    dict(lead="说到底就是一句话", big="那个人，其实是你自己")),
   ("13_steps_转给他",     "steps", "转给你身边那个人",
    dict(lead="那个一辈子不夸自己的人", items=["他家里可能就有一个","把这条转给他","评论区说说你会对二十岁的自己说什么"])),
   ("14_quote_不提了",     "quote", "你只是不提了",
    dict(lead="过去的事其实没有过去", big="你只是不提了")),
   ("15_quote_锁起来了2",  "quote", "把它锁起来了",
    dict(lead="你以为不提就是放下", big="其实你是把它锁起来了")),
   ("16_steps_打开",       "steps", "今天咱们不锁了",
    dict(lead="今天不锁了，咱们打开", items=["跟二十岁的自己说说话","就想一个人——二十来岁的你","他在干啥，穿什么，愁什么"])),
 ],
}

# ★ 2026-10-26 董事长定：每集最多 10 张卡片（卡片太多会挤掉真人讲解时间）
MAX_CARDS = 10
# ★ 选取规则：按「锚点关键词在本集口播里的位置」均匀分布地挑 10 张，
#   而不是按列表等距抽——等距抽会把中段的卡抽掉、把片尾的卡留下，导致超片长被丢弃。
import json as _json, os as _os, io as _io
_R = _os.path.dirname(_os.path.abspath(__file__))
_EPS_SPEED = {1: 1.196, 2: 1.264, 3: 1.027, 4: 1.138, 5: 1.163, 6: 1.061}


def _anchor_time(n, kw):
    dp = _os.path.join(_R, "draft_%d.json" % n)
    if not _os.path.exists(dp):
        return None
    d = _json.load(_io.open(dp, encoding="utf-8"))
    sp = _EPS_SPEED.get(n, 1.0)
    for c in d["cues"]:
        if kw in c["text"]:
            return c["start"] / sp
    return None


def _pick_even(n, cards, keep=MAX_CARDS):
    """选出 keep 张卡，保证「每张都有对应口播内容 + 全片均匀分布」。
    做法：
      1. 每张卡算锚点时间；锚点落在片尾最后 10 秒的丢掉（放不下）
      2. 若可用卡 >= keep：在 0..(片长-14) 上等距取点，各取锚点最近的卡（不重复）
      3. 若不足 keep：先用可用的全部，剩下的补位（anchor 返回 None，由 compose 兜底时间填）
    """
    dp = _os.path.join(_R, "draft_%d.json" % n)
    if not _os.path.exists(dp):
        return cards[:keep]
    dj = _json.load(_io.open(dp, encoding="utf-8"))
    sp = _EPS_SPEED.get(n, 1.0)
    full = dj["duration"] / sp

    def t_of(kw):
        for c in dj["cues"]:
            if kw in c["text"]:
                return c["start"] / sp
        return None

    scored = []
    for cd in cards:
        t = t_of(cd[2])
        scored.append((t, cd))
    usable = [(t, cd) for t, cd in scored if t is not None and t <= full - 10]
    drop = [(t, cd) for t, cd in scored if not (t is not None and t <= full - 10)]

    if len(usable) >= keep:
        span = max(1.0, full - 16)
        chosen, used = [], set()
        for i in range(keep):
            target = span * i / float(keep - 1)
            best, bi = 1e9, -1
            for j, (t, cd) in enumerate(usable):
                if j in used:
                    continue
                dd = abs(t - target)
                if dd < best:
                    best, bi = dd, j
            if bi >= 0:
                used.add(bi)
                chosen.append(usable[bi])
        chosen.sort(key=lambda x: x[0])
        return [cd for _, cd in chosen]

    # 不足：全用可用的，再从丢弃的里补
    got = sorted(usable, key=lambda x: x[0])
    need = keep - len(got)
    if need > 0 and drop:
        got += drop[:need]
    return [cd for _, cd in got]


for _k in list(CARDS_V2.keys()):
    CARDS_V2[_k] = _pick_even(_k, CARDS_V2[_k])

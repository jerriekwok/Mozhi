export const copybooks = [
    {
        id: "yzq-duobaota",
        name: "多宝塔碑",
        dynasty: "唐",
        calligrapher: "颜真卿",
        style: "楷书",
        description: "颜真卿楷书代表作之一，结构端严，笔力雄健，适合楷书入门与结构训练。",
        characters: ["大", "唐", "故", "千", "福", "寺", "多", "宝", "塔", "碑"]
    },
    {
        id: "lgq-xuanmita",
        name: "玄秘塔碑",
        dynasty: "唐",
        calligrapher: "柳公权",
        style: "楷书",
        description: "柳公权晚年楷书名作，骨力劲健，结构精严，可用于观察中宫收束。",
        characters: ["大", "达", "法", "师", "玄", "秘", "塔", "碑", "铭", "序"]
    },
    {
        id: "oyx-jiuchenggong",
        name: "九成宫醴泉铭",
        dynasty: "唐",
        calligrapher: "欧阳询",
        style: "楷书",
        description: "欧阳询楷书极则，法度森严，险中求稳，适合练习点画位置与重心。",
        characters: ["九", "成", "宫", "醴", "泉", "铭", "秘", "书", "监", "臣"]
    },
    {
        id: "wxz-lanting",
        name: "兰亭集序",
        dynasty: "东晋",
        calligrapher: "王羲之",
        style: "行书",
        description: "天下第一行书，行气自然，变化丰富，适合赏析行书节奏与章法。",
        characters: ["永", "和", "九", "年", "兰", "亭", "修", "禊", "事", "也"]
    },
    {
        id: "ss-hanshi",
        name: "寒食帖",
        dynasty: "宋",
        calligrapher: "苏轼",
        style: "行书",
        description: "天下第三行书，情绪沉郁而气象开阔，适合观察墨色与行气变化。",
        characters: ["自", "我", "来", "黄", "州", "寒", "食", "雨", "年", "欲"]
    },
    {
        id: "hs-zixu",
        name: "自叙帖",
        dynasty: "唐",
        calligrapher: "怀素",
        style: "草书",
        description: "狂草代表作，线条连绵飞动，适合草书赏析与节奏感观察。",
        characters: ["怀", "素", "家", "长", "沙", "出", "家", "而", "酷", "嗜"]
    }
];

export const calligraphyStyles = [
    { id: "yan", name: "颜体", calligrapher: "颜真卿", dynasty: "唐", style: "楷书" },
    { id: "liu", name: "柳体", calligrapher: "柳公权", dynasty: "唐", style: "楷书" },
    { id: "ou", name: "欧体", calligrapher: "欧阳询", dynasty: "唐", style: "楷书" },
    { id: "wang", name: "王羲之行书", calligrapher: "王羲之", dynasty: "东晋", style: "行书" },
    { id: "su", name: "苏体", calligrapher: "苏轼", dynasty: "宋", style: "行书" },
    { id: "huai", name: "怀素草书", calligrapher: "怀素", dynasty: "唐", style: "草书" }
];

export const quickQuestions = [
    "什么是永字八法？",
    "颜真卿的书法特点？",
    "如何选择毛笔？",
    "楷书四大家是谁？"
];

export const topics = [
    "楷书技法",
    "行书章法",
    "草书鉴赏",
    "王羲之",
    "颜真卿",
    "苏轼",
    "永字八法",
    "中锋用笔",
    "结构规律",
    "临摹方法",
    "文房四宝",
    "题款钤印"
];

export const classicWorks = copybooks.map((copybook) => ({
    id: copybook.id,
    title: `${copybook.calligrapher}《${copybook.name}》`,
    style: copybook.style,
    author: copybook.calligrapher
}));

export const quickActions = ["作品赏析", "字体风格学习", "临帖指导", "创作建议"];

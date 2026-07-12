const featuredPhrases = {
    "ybs-lishu": ["高山流水", "明月清风"],
    "hsj-lishu": ["书贵瘦硬", "骨力洞达"],
    "fs-xingshu": ["宁拙毋巧", "宁丑毋媚"],
    "zjz-kaishu": ["云霞出海曙", "梅柳渡江春"],
    "zy-kaishu": ["天地玄黄", "宇宙洪荒"],
    "lgq-kaishu": ["心正则笔正", "笔谏"],
    "sym-kaishu": ["执笔五字法", "书法论丛"],
    "zwy-xingshu": ["笔墨传神", "翰墨清赏"],
    "wxz-shengjiao": ["大唐三藏圣教序", "太宗文皇帝制"],
    "wd-xingshu": ["拟山园帖", "赠张抱一草书诗卷"],
    "mf-xingshu": ["蜀素帖", "苕溪诗帖"],
    "ysn-kaishu": ["孔子庙堂碑", "汝南公主墓志"],
    "zzq-kaishu": ["二金蝶堂印谱", "悲盦居士"],
    "zmf-sanmenji": ["湖州路德清县", "重修三教堂记"],
    "zbq-xingshu": ["咬定青山不放松", "千磨万击还坚劲"],
    "zsr-lishu": ["完白山人", "江流有声断岸千尺"],
    "jn-lishu": ["冬心先生", "漆书集联"],
    "yzq-duobaota": ["大唐西京千福寺", "多宝佛塔感应碑"],
    "weibei-kaishu": ["始平公造像记", "郑文公碑"]
};

const localGlyphSources = [
    { id: "ybs-lishu", name: "隶书", calligrapher: "伊秉绶", dynasty: "清", style: "隶书", glyphSource: "伊秉綬 隸書" },
    { id: "hsj-lishu", name: "隶书", calligrapher: "何绍基", dynasty: "清", style: "隶书", glyphSource: "何紹基 隸書" },
    { id: "fs-xingshu", name: "行书", calligrapher: "傅山", dynasty: "明清", style: "行书", glyphSource: "傅山 行書" },
    { id: "zjz-kaishu", name: "楷书", calligrapher: "张即之", dynasty: "南宋", style: "楷书", glyphSource: "張即之 楷書" },
    { id: "zy-kaishu", name: "楷书", calligrapher: "智永", dynasty: "隋", style: "楷书", glyphSource: "智永 楷書" },
    { id: "lgq-kaishu", name: "楷书", calligrapher: "柳公权", dynasty: "唐", style: "楷书", glyphSource: "柳公權 楷書" },
    { id: "sym-kaishu", name: "楷书", calligrapher: "沈尹默", dynasty: "近现代", style: "楷书", glyphSource: "沈尹默 楷書" },
    { id: "zwy-xingshu", name: "行书", calligrapher: "王壮为", dynasty: "近现代", style: "行书", glyphSource: "王壯為 行書" },
    { id: "wxz-shengjiao", name: "集字圣教序", calligrapher: "王羲之", dynasty: "东晋", style: "行书", glyphSource: "王羲之 集字聖教序 行書" },
    { id: "wd-xingshu", name: "行书", calligrapher: "王铎", dynasty: "明", style: "行书", glyphSource: "王鐸 行書" },
    { id: "mf-xingshu", name: "行书", calligrapher: "米芾", dynasty: "北宋", style: "行书", glyphSource: "米芾 行書" },
    { id: "ysn-kaishu", name: "楷书", calligrapher: "虞世南", dynasty: "唐", style: "楷书", glyphSource: "虞世南 楷書" },
    { id: "zzq-kaishu", name: "楷书", calligrapher: "赵之谦", dynasty: "清", style: "楷书", glyphSource: "趙之謙 楷書" },
    { id: "zmf-sanmenji", name: "三门记", calligrapher: "赵孟頫", dynasty: "元", style: "楷书", glyphSource: "趙孟頫 三門記 楷書" },
    { id: "zbq-xingshu", name: "行书", calligrapher: "郑板桥", dynasty: "清", style: "行书", glyphSource: "鄭板橋 行書" },
    { id: "zsr-lishu", name: "隶书", calligrapher: "郑石如", dynasty: "清", style: "隶书", glyphSource: "鄭石如 隸書" },
    { id: "jn-lishu", name: "隶书", calligrapher: "金农", dynasty: "清", style: "隶书", glyphSource: "金農 隸書" },
    { id: "yzq-duobaota", name: "多宝塔碑", calligrapher: "颜真卿", dynasty: "唐", style: "楷书", glyphSource: "顏真卿 多寶塔碑 楷書" },
    { id: "weibei-kaishu", name: "魏碑", calligrapher: "魏碑", dynasty: "北魏", style: "楷书", glyphSource: "魏碑 楷書" }
];

export const copybooks = localGlyphSources.map((source) => ({
    ...source,
    description: `本地字库收录的${source.calligrapher}${source.style}单字，可直接用于集字创作。`,
    phrases: featuredPhrases[source.id] || []
}));

export const calligraphyStyles = copybooks.map((copybook) => ({
    id: copybook.id,
    name: copybook.name === copybook.style ? `${copybook.calligrapher}${copybook.style}` : copybook.name,
    calligrapher: copybook.calligrapher,
    dynasty: copybook.dynasty,
    style: copybook.style
}));

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

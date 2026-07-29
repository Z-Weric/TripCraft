"""种子景点数据 — 10 城市，每城市 5-8 个景点"""

SEED_POIS = [
    # ===== 杭州 =====
    {"city": "杭州", "name": "西湖", "category": "自然风光", "lat": 30.2592, "lng": 120.1300, "address": "杭州市西湖区", "cost": 0, "duration": "3h", "note": "免费，建议从断桥开始沿白堤步行", "rating": 4.9},
    {"city": "杭州", "name": "楼外楼", "category": "美食", "lat": 30.2550, "lng": 120.1350, "address": "杭州市西湖区孤山路30号", "cost": 200, "duration": "1.5h", "note": "西湖醋鱼必点，人均100元", "rating": 4.5},
    {"city": "杭州", "name": "灵隐寺", "category": "历史文化", "lat": 30.2400, "lng": 120.1000, "address": "杭州市西湖区灵隐路法云弄1号", "cost": 75, "duration": "2h", "note": "飞来峰石窟值得看", "rating": 4.7},
    {"city": "杭州", "name": "千岛湖", "category": "自然风光", "lat": 29.6087, "lng": 119.0314, "address": "杭州市淳安县", "cost": 130, "duration": "2.5h", "note": "建议提前购票，船票含在门票内", "rating": 4.6},
    {"city": "杭州", "name": "芹川古村", "category": "历史文化", "lat": 29.6200, "lng": 119.0400, "address": "杭州市淳安县浪川乡", "cost": 0, "duration": "3h", "note": "免费，徽派建筑群保存完好", "rating": 4.4},
    {"city": "杭州", "name": "西溪湿地", "category": "自然风光", "lat": 30.2700, "lng": 120.0600, "address": "杭州市西湖区天目山路518号", "cost": 80, "duration": "2h", "note": "摇橹船体验推荐，船票另付60元", "rating": 4.5},
    {"city": "杭州", "name": "知味观", "category": "美食", "lat": 30.2650, "lng": 120.1650, "address": "杭州市上城区仁和路83号", "cost": 100, "duration": "1.5h", "note": "杭帮菜老字号，猫耳朵必点", "rating": 4.3},
    {"city": "杭州", "name": "河坊街", "category": "购物", "lat": 30.2500, "lng": 120.1700, "address": "杭州市上城区河坊街", "cost": 200, "duration": "2h", "note": "特产伴手礼采购，定胜糕推荐", "rating": 4.2},

    # ===== 成都 =====
    {"city": "成都", "name": "宽窄巷子", "category": "历史文化", "lat": 30.6950, "lng": 104.0580, "address": "成都市青羊区宽窄巷子", "cost": 0, "duration": "2h", "note": "免费，体验老成都生活", "rating": 4.5},
    {"city": "成都", "name": "锦里", "category": "购物", "lat": 30.6430, "lng": 104.0480, "address": "成都市武侯区武侯祠大街231号", "cost": 0, "duration": "1.5h", "note": "免费，三国文化商业街", "rating": 4.3},
    {"city": "成都", "name": "大熊猫繁育研究基地", "category": "自然风光", "lat": 30.7320, "lng": 104.1440, "address": "成都市成华区熊猫大道1375号", "cost": 55, "duration": "3h", "note": "早上8点去能看到活跃的熊猫", "rating": 4.8},
    {"city": "成都", "name": "陈麻婆豆腐", "category": "美食", "lat": 30.6580, "lng": 104.0630, "address": "成都市青羊区青华路10号", "cost": 80, "duration": "1h", "note": "麻婆豆腐发源地，人均40元", "rating": 4.4},
    {"city": "成都", "name": "杜甫草堂", "category": "历史文化", "lat": 30.6580, "lng": 104.0200, "address": "成都市青羊区青华路37号", "cost": 50, "duration": "1.5h", "note": "杜甫故居，园林幽静", "rating": 4.4},
    {"city": "成都", "name": "人民公园鹤鸣茶社", "category": "美食", "lat": 30.6590, "lng": 104.0560, "address": "成都市青羊区少城路12号", "cost": 30, "duration": "2h", "note": "成都最老茶馆，体验盖碗茶", "rating": 4.5},

    # ===== 西安 =====
    {"city": "西安", "name": "秦始皇兵马俑博物馆", "category": "历史文化", "lat": 34.3840, "lng": 109.2730, "address": "西安市临潼区秦陵北路", "cost": 120, "duration": "3h", "note": "世界遗产，建议请讲解", "rating": 4.9},
    {"city": "西安", "name": "回民街", "category": "美食", "lat": 34.2640, "lng": 108.9400, "address": "西安市莲湖区回民街", "cost": 80, "duration": "2h", "note": "羊肉泡馍、肉夹馍必吃", "rating": 4.3},
    {"city": "西安", "name": "大雁塔", "category": "历史文化", "lat": 34.2180, "lng": 108.9610, "address": "西安市雁塔区雁塔南路", "cost": 65, "duration": "1.5h", "note": "唐代佛塔，音乐喷泉晚上看", "rating": 4.6},
    {"city": "西安", "name": "西安城墙", "category": "历史文化", "lat": 34.2570, "lng": 108.9400, "address": "西安市碑林区南大街", "cost": 54, "duration": "2h", "note": "骑行城墙推荐，租自行车45元", "rating": 4.7},
    {"city": "西安", "name": "华清宫", "category": "历史文化", "lat": 34.3660, "lng": 109.2140, "address": "西安市临潼区华清路38号", "cost": 120, "duration": "2h", "note": "唐代温泉行宫，《长恨歌》演出推荐", "rating": 4.4},

    # ===== 厦门 =====
    {"city": "厦门", "name": "鼓浪屿", "category": "自然风光", "lat": 24.4480, "lng": 118.0670, "address": "厦门市思明区鼓浪屿", "cost": 90, "duration": "4h", "note": "轮渡35元含往返，万国建筑群", "rating": 4.7},
    {"city": "厦门", "name": "南普陀寺", "category": "历史文化", "lat": 24.4400, "lng": 118.0900, "address": "厦门市思明区思明南路515号", "cost": 0, "duration": "1.5h", "note": "免费，千年古刹", "rating": 4.5},
    {"city": "厦门", "name": "曾厝垵", "category": "美食", "lat": 24.4360, "lng": 118.1080, "address": "厦门市思明区曾厝垵", "cost": 60, "duration": "2h", "note": "小吃一条街，沙茶面推荐", "rating": 4.1},
    {"city": "厦门", "name": "环岛路", "category": "自然风光", "lat": 24.4350, "lng": 118.1200, "address": "厦门市思明区环岛路", "cost": 0, "duration": "2h", "note": "免费，骑行海岸线推荐", "rating": 4.6},
    {"city": "厦门", "name": "中山路步行街", "category": "购物", "lat": 24.4660, "lng": 118.0890, "address": "厦门市思明区中山路", "cost": 100, "duration": "2h", "note": "南洋骑楼建筑，特产采购", "rating": 4.3},

    # ===== 苏州 =====
    {"city": "苏州", "name": "拙政园", "category": "历史文化", "lat": 31.3240, "lng": 120.6300, "address": "苏州市姑苏区东北街178号", "cost": 70, "duration": "2h", "note": "中国四大名园之首", "rating": 4.7},
    {"city": "苏州", "name": "平江路", "category": "历史文化", "lat": 31.3140, "lng": 120.6240, "address": "苏州市姑苏区平江路", "cost": 0, "duration": "2h", "note": "免费，古运河边的老街", "rating": 4.5},
    {"city": "苏州", "name": "松鹤楼", "category": "美食", "lat": 31.3180, "lng": 120.6200, "address": "苏州市姑苏区太监弄72号", "cost": 150, "duration": "1.5h", "note": "苏帮菜老字号，松鼠桂鱼必点", "rating": 4.4},
    {"city": "苏州", "name": "虎丘", "category": "历史文化", "lat": 31.3220, "lng": 120.5720, "address": "苏州市姑苏区虎丘山门", "cost": 60, "duration": "1.5h", "note": "吴中第一名胜，斜塔值得看", "rating": 4.5},
    {"city": "苏州", "name": "金鸡湖", "category": "自然风光", "lat": 31.3120, "lng": 120.6680, "address": "苏州市工业园区金鸡湖", "cost": 0, "duration": "2h", "note": "免费，夜景灯光秀推荐", "rating": 4.4},

    # ===== 南京 =====
    {"city": "南京", "name": "中山陵", "category": "历史文化", "lat": 32.0570, "lng": 118.8460, "address": "南京市玄武区紫金山", "cost": 0, "duration": "2h", "note": "免费，需提前预约", "rating": 4.8},
    {"city": "南京", "name": "夫子庙", "category": "购物", "lat": 32.0230, "lng": 118.7870, "address": "南京市秦淮区夫子庙", "cost": 50, "duration": "2h", "note": "秦淮河夜景，小吃丰富", "rating": 4.4},
    {"city": "南京", "name": "鸭血粉丝汤（回味鸭血粉丝）", "category": "美食", "lat": 32.0250, "lng": 118.7900, "address": "南京市秦淮区夫子庙附近", "cost": 40, "duration": "1h", "note": "南京招牌小吃，人均20元", "rating": 4.3},
    {"city": "南京", "name": "玄武湖", "category": "自然风光", "lat": 32.0730, "lng": 118.8050, "address": "南京市玄武区玄武巷1号", "cost": 0, "duration": "2h", "note": "免费，城中最大的湖泊公园", "rating": 4.5},
    {"city": "南京", "name": "总统府", "category": "历史文化", "lat": 32.0480, "lng": 118.7970, "address": "南京市玄武区长江路292号", "cost": 35, "duration": "1.5h", "note": "近代史博物馆，建筑精美", "rating": 4.5},

    # ===== 重庆 =====
    {"city": "重庆", "name": "洪崖洞", "category": "历史文化", "lat": 29.5650, "lng": 106.5810, "address": "重庆市渝中区沧白路88号", "cost": 0, "duration": "2h", "note": "免费，夜景酷似千与千寻", "rating": 4.6},
    {"city": "重庆", "name": "磁器口古镇", "category": "购物", "lat": 29.5790, "lng": 106.4470, "address": "重庆市沙坪坝区磁器口", "cost": 0, "duration": "2h", "note": "免费，陈麻花推荐", "rating": 4.3},
    {"city": "重庆", "name": "长江索道", "category": "自然风光", "lat": 29.5580, "lng": 106.5830, "address": "重庆市渝中区新华路", "cost": 30, "duration": "0.5h", "note": "跨江索道，山城特色体验", "rating": 4.4},
    {"city": "重庆", "name": "火锅（珮姐老火锅）", "category": "美食", "lat": 29.5630, "lng": 106.5780, "address": "重庆市渝中区民权路", "cost": 120, "duration": "2h", "note": "重庆火锅必体验，人均60元", "rating": 4.5},
    {"city": "重庆", "name": "武隆天生三桥", "category": "自然风光", "lat": 29.3200, "lng": 107.7600, "address": "重庆市武隆区", "cost": 125, "duration": "3h", "note": "世界自然遗产，天坑景观", "rating": 4.7},

    # ===== 长沙 =====
    {"city": "长沙", "name": "橘子洲", "category": "自然风光", "lat": 28.1880, "lng": 112.9770, "address": "长沙市岳麓区橘子洲", "cost": 0, "duration": "2h", "note": "免费，需预约，毛主席像打卡", "rating": 4.6},
    {"city": "长沙", "name": "文和友（超级文和友）", "category": "美食", "lat": 28.1950, "lng": 112.9790, "address": "长沙市天心区贺龙体育馆", "cost": 80, "duration": "2h", "note": "怀旧美食城，小龙虾必点", "rating": 4.4},
    {"city": "长沙", "name": "岳麓山", "category": "自然风光", "lat": 28.1870, "lng": 112.9420, "address": "长沙市岳麓区岳麓山", "cost": 0, "duration": "3h", "note": "免费，爱晚亭看红叶", "rating": 4.6},
    {"city": "长沙", "name": "茶颜悦色（太平街店）", "category": "美食", "lat": 28.1930, "lng": 112.9750, "address": "长沙市天心区太平街", "cost": 20, "duration": "0.5h", "note": "长沙招牌奶茶，幽兰拿铁推荐", "rating": 4.5},
    {"city": "长沙", "name": "太平老街", "category": "购物", "lat": 28.1940, "lng": 112.9740, "address": "长沙市天心区太平街", "cost": 50, "duration": "1.5h", "note": "贾谊故居在此，小吃丰富", "rating": 4.3},

    # ===== 青岛 =====
    {"city": "青岛", "name": "栈桥", "category": "自然风光", "lat": 36.0590, "lng": 120.3180, "address": "青岛市市南区太平路", "cost": 0, "duration": "1h", "note": "免费，青岛地标", "rating": 4.4},
    {"city": "青岛", "name": "八大关", "category": "历史文化", "lat": 36.0540, "lng": 120.3580, "address": "青岛市市南区八大关", "cost": 0, "duration": "2h", "note": "免费，万国建筑群", "rating": 4.6},
    {"city": "青岛", "name": "崂山", "category": "自然风光", "lat": 36.1600, "lng": 120.6200, "address": "青岛市崂山区", "cost": 90, "duration": "4h", "note": "海上名山，太清宫推荐", "rating": 4.5},
    {"city": "青岛", "name": "船歌鱼水饺", "category": "美食", "lat": 36.0650, "lng": 120.3820, "address": "青岛市市南区闽江路", "cost": 100, "duration": "1h", "note": "墨鱼水饺招牌，人均50元", "rating": 4.4},
    {"city": "青岛", "name": "金沙滩", "category": "自然风光", "lat": 35.9650, "lng": 120.1670, "address": "青岛市黄岛区金沙滩", "cost": 0, "duration": "3h", "note": "免费，亚洲第一滩", "rating": 4.5},

    # ===== 大理 =====
    {"city": "大理", "name": "洱海", "category": "自然风光", "lat": 25.7980, "lng": 100.1840, "address": "大理市洱海", "cost": 0, "duration": "4h", "note": "免费，环湖骑行推荐", "rating": 4.8},
    {"city": "大理", "name": "大理古城", "category": "历史文化", "lat": 25.6940, "lng": 100.1580, "address": "大理市古城区", "cost": 0, "duration": "2h", "note": "免费，南城楼和五华楼打卡", "rating": 4.5},
    {"city": "大理", "name": "苍山", "category": "自然风光", "lat": 25.6750, "lng": 100.1150, "address": "大理市苍山", "cost": 40, "duration": "3h", "note": "索道上行，洗马潭值得看", "rating": 4.6},
    {"city": "大理", "name": "喜洲古镇", "category": "美食", "lat": 25.7700, "lng": 100.1300, "address": "大理市喜洲镇", "cost": 30, "duration": "2h", "note": "喜洲粑粑必吃，白族建筑群", "rating": 4.4},
    {"city": "大理", "name": "双廊古镇", "category": "购物", "lat": 25.9600, "lng": 100.1800, "address": "大理市双廊镇", "cost": 50, "duration": "2h", "note": "洱海最佳观景点，日落推荐", "rating": 4.5},
]
import requests
import random
import json
from dotenv import load_dotenv
import os
from flask import Flask, request, jsonify, render_template
import logging as builtin_logging
from urllib.parse import quote

app = Flask(__name__, static_folder='static', template_folder='templates')
load_dotenv()

# 設置日誌
builtin_logging.basicConfig(
    filename='game.log',
    level=builtin_logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    encoding='utf-8'
)
logger = builtin_logging.getLogger(__name__)

# API 配置
API_CONFIGS = [
    {"base_url": os.getenv("AI_API_URL1"), "api_key": os.getenv("AI_API_KEY1"), "model": os.getenv("AI_API_MODEL1")},
    {"base_url": os.getenv("AI_API_URL2"), "api_key": os.getenv("AI_API_KEY2"), "model": os.getenv("AI_API_MODEL2")}
]

# 隨機映射配置
CONFIG_MAPPING = {
    "LOCATION": ["遊艇", "酒店房間", "富翁大屋", "無人島", "太空站", "長城", "華山之顛", "商場洗手間", "月球上", "潛艇中", "後台", "舞台"],
    "CASE": ["兇殺案", "盜竊", "性侵", "整蠱", "偷吃東西", "資訊外洩", "縱火案", "謀殺未遂"],
    "TIME": ["早上", "中午", "晚上", "深夜"],
    "PERSONALITY": ["聰明", "冷酷", "風趣", "淫蕩", "緊張", "膽小", "狡猾", "智慧型", "大直男", "綠茶婊", "謹慎", "衝動", "懷疑", "迷信"],
    "ROLE": ["美女", "學生", "醫生", "商人", "管家", "小朋友", "專家", "殺手", "清潔工", "蝙蝠俠", "革命家", "神職人員", "和尚", "大明星", "警察", "政治家", "律師"],
    "SURNAME": ["陳", "李", "張", "王", "林", "小", "大", "美國"]
}

def call_siliconflow_api(prompt, config, max_chars=None):
    url = config["base_url"]
    headers = {"Authorization": f"Bearer {config['api_key']}", "Content-Type": "application/json"}
    data = {"model": config["model"], "messages": [{"role": "user", "content": prompt}], "max_tokens": 1000, "temperature": 0.8}
    
    logger.info(f"API Request to {url} with model {config['model']}:\n{prompt}")
    
    try:
        response = requests.post(url, json=data, headers=headers, timeout=15)
        response.raise_for_status()
        result = response.json()["choices"][0]["message"]["content"]
        logger.info(f"API Response (raw):\n{result}")
        if max_chars and len(result) > max_chars:
            result = result[:max_chars] + "..."
            logger.warning(f"回應超過{max_chars}字，已截斷")
        return result
    except Exception as e:
        logger.error(f"API調用失敗: {e}")
        return None

def get_random_api_config():
    return random.choice(API_CONFIGS)

@app.route('/init', methods=['GET'])
def init_game():
    location = random.choice(CONFIG_MAPPING["LOCATION"])
    case_type = random.choice(CONFIG_MAPPING["CASE"])
    time = random.choice(CONFIG_MAPPING["TIME"])
    roles = random.sample(CONFIG_MAPPING["ROLE"], min(5, len(CONFIG_MAPPING["ROLE"])))
    personalities = random.choices(CONFIG_MAPPING["PERSONALITY"], k=5)
    surnames = random.sample(CONFIG_MAPPING["SURNAME"], min(5, len(CONFIG_MAPPING["SURNAME"])))
    
    logger.info(f"隨機生成的案件: {case_type} 在 {location}，時間 {time}")
    
    role_data = {}
    for surname, role, personality in zip(surnames, roles, personalities):
        role_name = f"{surname}{role}"
        role_data[role_name] = {"personality": personality, "clue": "", "is_killer": False}
    
    killer = random.choice(list(role_data.keys()))
    role_data[killer]["is_killer"] = True
    logger.info(f"隨機選定的兇手: {killer}")
    
    host_prompt = f"""
    生成一個{case_type}故事，發生在{location}，時間是{time}。
    有5個角色：{', '.join(role_data.keys())}。
    兇手是{killer}。請為每個角色生成一個相關線索（約20字），並描述案件有趣的經過（包含背景事件，例如案發前的情況，角色之間身份的互動）。
    輸出格式為JSON，包含案件背景（鍵名為"case"，包含location, case_type, time, victim, events）和角色資料（鍵名為"roles"，為字典格式，鍵為角色名，值包含personality和clue）。
    請用繁體中文回應。
    """
    config = get_random_api_config()
    story_raw = call_siliconflow_api(host_prompt, config)
    
    if story_raw is None or not story_raw.strip():
        logger.error("故事生成失敗，返回備用數據")
        game_data = {
            "case": {"location": location, "case_type": case_type, "time": time, "victim": "神秘人物", "events": "未知事件"},
            "roles": {role: {**data, "clue": "案發時行蹤不明"} for role, data in role_data.items()}
        }
    else:
        story_cleaned = story_raw.replace("```json", "").replace("```", "").strip()
        logger.info(f"清理後的JSON:\n{story_cleaned}")
        try:
            story = json.loads(story_cleaned)
            case_data = story.get("case") or story.get("case_background")
            if not case_data:
                raise ValueError("缺少案件背景")
            
            if "roles" in story:
                roles_dict = story["roles"]
            elif "characters" in story:
                roles_dict = {char["name"]: {"personality": char.get("personality", role_data[char["name"]]["personality"]), "clue": char["clue"]} for char in story["characters"]}
                for char in story["characters"]:
                    if char.get("relation_to_case") == "兇手":
                        role_data[char["name"]]["is_killer"] = True
            else:
                raise ValueError("缺少角色資料")
            
            if len(roles_dict) < 5:
                logger.warning("角色數不足，補充中")
                for role in role_data:
                    if role not in roles_dict:
                        roles_dict[role] = {"personality": role_data[role]["personality"], "clue": "案發時行蹤不明"}
            
            game_data = {
                "case": case_data,
                "roles": {role: {**role_data[role], **data} for role, data in roles_dict.items()}
            }
        except json.JSONDecodeError as e:
            logger.error(f"JSON解析失敗，清理後內容:\n{story_cleaned}\n錯誤: {str(e)}")
            game_data = {
                "case": {"location": location, "case_type": case_type, "time": time, "victim": "神秘人物", "events": "未知事件"},
                "roles": {role: {**data, "clue": "案發時行蹤不明"} for role, data in role_data.items()}
            }
        except ValueError as e:
            logger.error(f"數據結構錯誤:\n{story_cleaned}\n錯誤: {str(e)}")
            game_data = {
                "case": {"location": location, "case_type": case_type, "time": time, "victim": "神秘人物", "events": "未知事件"},
                "roles": {role: {**data, "clue": "案發時行蹤不明"} for role, data in role_data.items()}
            }
    
    # 從 case 生成圖像 Prompt
    case = game_data["case"]
    image_prompt = f"在{case['location']}，{case['time']}的時間，發生了神秘事件卡通風格。"
    image_url = f"https://image.pollinations.ai/prompt/{quote(image_prompt)}?width=1024&height=768&model=flux-realism"
    
    # 將 image_url 加入 game_data
    game_data["image_url"] = image_url
    
    return jsonify(game_data)

@app.route('/talk', methods=['POST'])
def talk_to_role():
    data = request.json
    role = data["role"]
    question = data["question"]
    game_data = data.get("game_data")  # 從前端傳來的 game_data
    
    if not game_data or "roles" not in game_data or role not in game_data["roles"]:
        logger.error("game_data 無效或缺少角色資料")
        return jsonify({"error": "遊戲數據無效，請先初始化遊戲"}), 400
    
    role_data = game_data["roles"][role]
    case_data = game_data["case"]
    config = get_random_api_config()
    is_victim = role == case_data["victim"]
    
    if role_data["is_killer"]:
        prompt = f"""
        我們來玩一個猜猜兇手的角色扮演遊戲。你是{role}，性格{role_data['personality']}，你是兇手。
        案件背景：{case_data['case_type']}發生在{case_data['location']}，時間是{case_data['time']}，受害者是{case_data['victim']}。
        背景事件：{case_data['events']}。
        你的線索：{role_data['clue']}。
        玩家問：'{question}'，請用你的性格回應，試圖誤導玩家，但保持合理性。回應不超過250字。但是如果玩家猜到是你了。你就囂張地承認和說明原因吧。
        請用繁體中文回應。
        """
    elif is_victim:
        prompt = f"""
        我們來玩一個猜猜兇手的角色扮演遊戲。你是{role}，性格{role_data['personality']}，你是受害者。
        案件背景：{case_data['case_type']}發生在{case_data['location']}，時間是{case_data['time']}，受害者是你。
        背景事件：{case_data['events']}。
        你的線索：{role_data['clue']}。
        玩家問：'{question}'，請用你的性格回應，提供真實但不完整的資訊，表現出受害者的情緒。回應不超過250字。
        請用繁體中文回應。
        """
    else:
        prompt = f"""
        我們來玩一個猜猜兇手的角色扮演遊戲。你是{role}，性格{role_data['personality']}，你不是兇手。
        案件背景：{case_data['case_type']}發生在{case_data['location']}，時間是{case_data['time']}，受害者是{case_data['victim']}。
        背景事件：{case_data['events']}。
        你的線索：{role_data['clue']}。
        玩家問：'{question}'，請用你的性格回應，提供真實但不完整的資訊，並明確否認涉案。回應不超過250字。
        請用繁體中文回應。
        """
    response = call_siliconflow_api(prompt, config, max_chars=250)
    if response is None:
        response = "我不知道該說什麼..."
    return jsonify({"response": response})

@app.route('/guess', methods=['POST'])
def guess_killer():
    data = request.json
    guess = data["guess"]
    game_data = data.get("game_data")  # 從前端傳來的 game_data
    
    if not game_data or "roles" not in game_data:
        logger.error("game_data 無效或缺少角色資料")
        return jsonify({"error": "遊戲數據無效，請先初始化遊戲"}), 400
    
    killer = next(role for role, data in game_data["roles"].items() if data["is_killer"])
    correct = guess == killer
    prompt = f"""
    根據以下案件背景生成總結：
    {game_data['case']['case_type']}發生在{game_data['case']['location']}，時間是{game_data['case']['time']}，受害者是{game_data['case']['victim']}。
    背景事件：{game_data['case']['events']}。
    兇手是{killer}。請描述事件有趣的經過和動機，約250字，用繁體中文。
    """
    config = get_random_api_config()
    summary = call_siliconflow_api(prompt, config)
    if summary is None:
        summary = f"兇手是{killer}，但總結生成失敗。"
    return jsonify({"correct": correct, "summary": summary})

@app.route('/')
def index():
    return render_template('index.html')

if __name__ == "__main__":
    print("啟動Flask應用...")
    app.run(debug=True, host='0.0.0.0', port=5000)
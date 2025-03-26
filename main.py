import requests
import random
import json
from dotenv import load_dotenv
import os
from requests.adapters import HTTPAdapter
from requests.packages.urllib3.util.retry import Retry

# 載入 .env 檔案
load_dotenv()

# 從 .env 讀取多個 API 配置
API_CONFIGS = [
    {
        "base_url": os.getenv("AI_API_URL1"),
        "api_key": os.getenv("AI_API_KEY1"),
        "model": os.getenv("AI_API_MODEL1")
    },
    {
        "base_url": os.getenv("AI_API_URL2"),
        "api_key": os.getenv("AI_API_KEY2"),
        "model": os.getenv("AI_API_MODEL2")
    }
]

# SiliconFlow API 調用（帶重試）
def call_siliconflow_api(prompt, config):
    url = config["base_url"]
    headers = {
        "Authorization": f"Bearer {config['api_key']}",
        "Content-Type": "application/json"
    }
    data = {
        "model": config["model"],
        "messages": [{"role": "user", "content": prompt}],
        "max_tokens": 100,  # 縮短回應長度
        "temperature": 0.7
    }
    session = requests.Session()
    retry = Retry(total=3, backoff_factor=1, status_forcelist=[500, 502, 503, 504])
    adapter = HTTPAdapter(max_retries=retry)
    session.mount("https://", adapter)
    try:
        response = session.post(url, json=data, headers=headers, timeout=15)  # 延長超時
        response.raise_for_status()
        print(f"使用模型：{config['model']}")
        return response.json()["choices"][0]["message"]["content"]
    except Exception as e:
        print(f"API調用失敗: {e}")
        return f"模擬回應: {prompt}"

# 隨機選擇API配置
def get_random_api_config():
    return random.choice(API_CONFIGS)

# 初始化遊戲（隨機角色名稱）
def initialize_game():
    host_prompt = """
    生成一個偵探故事，隨機創建5個角色名稱（例如：陳先生、李小姐等），並為每個角色指定性格和線索。
    隨機指定一個兇手。故事發生在一座豪宅，受害者是屋主，使用具體兇器。
    輸出格式為JSON，包含案件背景和角色資料。
    請用繁體中文回應。
    """
    config = get_random_api_config()
    story_raw = call_siliconflow_api(host_prompt, config)
    
    try:
        story = json.loads(story_raw)
    except json.JSONDecodeError:
        story = {
            "case": {"location": "豪宅", "victim": "屋主", "weapon": "匕首"},
            "roles": {
                "陳醫生": {"personality": "冷靜", "clue": "聽到爭吵聲", "is_killer": False},
                "林管家": {"personality": "緊張", "clue": "發現屍體", "is_killer": True},
                "張商人": {"personality": "狡猾", "clue": "有財務糾紛", "is_killer": False},
                "王學生": {"personality": "天真", "clue": "看到園丁離開", "is_killer": False},
                "李園丁": {"personality": "沉默", "clue": "手上沾血", "is_killer": False}
            }
        }
    return story

# 角色回應生成
def get_role_response(role, question, game_data):
    role_data = game_data["roles"][role]
    case_data = game_data["case"]
    config = get_random_api_config()
    
    if role_data["is_killer"]:
        prompt = f"""
        我們來做一個偵探的遊戲。你是{role}，性格{role_data['personality']}，你是兇手。
        案件背景：受害者是{case_data['victim']}，在{case_data['location']}被{case_data['weapon']}殺害。
        你的線索：{role_data['clue']}。
        玩家問：'{question}'，請用你的性格回應，試圖誤導玩家，但保持合理性。回應不超過250字。
        請用繁體中文回應。
        """
    else:
        prompt = f"""
        你是{role}，性格{role_data['personality']}，不是兇手。
        案件背景：受害者是{case_data['victim']}，在{case_data['location']}被{case_data['weapon']}殺害。
        你的線索：{role_data['clue']}。
        玩家問：'{question}'，請用你的性格回應，提供真實但不完整的資訊，並明確否認涉案。回應不超過250字。
        請用繁體中文回應。
        """
    return call_siliconflow_api(prompt, config)

# 生成案件總結
def generate_summary(game_data):
    killer = next(role for role, data in game_data["roles"].items() if data["is_killer"])
    prompt = f"""
    根據以下案件背景生成總結：
    地點：{game_data['case']['location']}，受害者：{game_data['case']['victim']}，兇器：{game_data['case']['weapon']}。
    兇手是{killer}。請描述事件經過和動機，約500字，用繁體中文。
    """
    config = get_random_api_config()
    return call_siliconflow_api(prompt, config)

# 檢查玩家猜測
def check_answer(guess, game_data):
    for role, data in game_data["roles"].items():
        if data["is_killer"] and role == guess:
            return True
    return False

# 遊戲介面（新增對話歷史和總結）
def game_interface(game_data):
    roles = list(game_data["roles"].keys())
    chat_history = []
    print(f"歡迎來到《誰是兇手》！案件發生在{game_data['case']['location']}，受害者是{game_data['case']['victim']}，兇器是{game_data['case']['weapon']}。")
    print(f"可對話角色：{', '.join(roles)}")
    print("提示：輸入 '歷史' 查看對話記錄。")
    
    while True:
        action = input("\n你想做什麼？（輸入角色名稱與其對話，'猜兇手' 或 '歷史'）：").strip()
        
        if action == "猜兇手":
            guess = input("你認為兇手是誰？").strip()
            if guess not in roles:
                print("請輸入有效角色名稱！")
                continue
            summary = generate_summary(game_data)
            if check_answer(guess, game_data):
                print(f"恭喜你！{guess} 是兇手！\n案件總結：{summary}")
            else:
                print(f"錯了！{guess} 不是兇手。\n案件總結：{summary}")
            break
        
        elif action == "歷史":
            if chat_history:
                print("\n對話歷史：")
                for entry in chat_history:
                    print(entry)
            else:
                print("還沒有對話記錄。")
        
        elif action in roles:
            question = input(f"對 {action} 問什麼？").strip()
            response = get_role_response(action, question, game_data)
            chat_history.append(f"{action} 說：{response}")
            print(f"{action} 說：{response}")
        else:
            print("請輸入有效指令！")

# 主程式
if __name__ == "__main__":
    print("正在初始化遊戲...")
    game_data = initialize_game()
    game_interface(game_data)
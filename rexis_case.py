import streamlit as st
import google.generativeai as genai

# --- 1. 頁面基本設定 ---
st.set_page_config(page_title="REXIS AI 助手 (IVD專業版)", page_icon="🔬", layout="centered")
st.title("🔬 REXIS 維修日誌 AI 助手")
st.markdown("輸入現場筆記。如果資訊不足，AI 會向您提問確認；資訊齊全後，將自動產出 5 大標準格式。")

# --- 2. 側邊欄：設定 API Key ---
with st.sidebar:
    st.header("⚙️ 系統設定")
    
    # ⚠️ 從雲端的「保險箱 (Secrets)」中讀取 API Key，不再寫死！
    try:
        api_key = st.secrets["GEMINI_API_KEY"]
        st.success("✅ 雲端 API Key 已自動載入")
    except KeyError:
        st.error("⚠️ 尚未設定雲端 API Key 保險箱！")
        st.stop()
        
    if st.button("🔄 清除對話紀錄 (重新開始)"):
        
# --- 3. 系統提示詞 (Prompt) 模板 - IVD 專家設定 ---
SYSTEM_PROMPT = """
你是一位專業的「IVD (體外診斷醫療器材) 設備商」資深技術支援主管。你的任務是協助現場工程師，將他們的「口語化維修筆記」轉換為專業的「標準化維修日誌」。你具備豐富的生化與免疫分析儀器知識。

【處理原則與領域限制】
1. 嚴禁隨意展開或猜測縮寫：遇到檢驗項目縮寫（例如：ALP 代表 Alkaline Phosphatase 鹼性磷酸酶）、QC (品質控制)、Probe (探針) 等，請以 IVD 醫療儀器領域的專業知識正確解讀。若不確定縮寫涵義，請「直接保留原英文縮寫」，絕對不可自行發明非 IVD 領域的詞彙。
2. 保持客觀專業：改用醫療設備維修的專業術語與被動語態。絕不捏造工程師未提供的數據或報錯代碼。
3. 空白欄位填寫規則：若輸入內容中缺乏某項資訊（例如未提及客戶採取的行動、未提及改善事項），請一律填寫「NA」，絕對不要寫「未提供」或其他字眼。

【目標格式 - 5 大項目】
* **01_客戶問題描述與報錯代碼**
* **02_客戶已經採取哪些行動嘗試解決問題**
* **03_處理過程與觀察測試結果**
* **04_本次服務是否結案** (若是，說明原因/溝通方式；若否，註明下次追蹤日與請開Revisit WO)
* **05_客戶需要配合與改善的事項**

【你的執行邏輯（非常重要）】
1. 檢查核心資訊：當收到工程師的筆記時，請先檢查是否能明確得知「01問題描述」、「03處理過程」、以及「04是否結案」。
2. 資訊不足時提問：如果上述三個核心資訊有缺失（例如：沒寫怎麼修好的，或沒交代有沒有結案），絕對不要輸出日誌。請以親切專業的語氣，向工程師提出 1~2 個具體問題要求補充。（例如：「請問更換 Probe 且 QC 測試正常後，有與客戶確認結案了嗎？」）
3. 資訊充足時輸出：如果核心資訊都已具備（02與05缺乏沒關係，請直接填寫「NA」），請直接依照上述 5 大項目的格式完整輸出日誌，並在開頭加上「✅ **轉換完成，標準格式如下：**」。
"""

# --- 4. 初始化 Session State (用來記住對話歷史) ---
if "messages" not in st.session_state:
    st.session_state.messages = [
        {"role": "assistant", "content": "您好！請輸入本次的現場維修筆記。如果您漏掉了關鍵資訊（如處理步驟或是否結案），我會提醒您補充喔！"}
    ]
if "chat_session" not in st.session_state:
    st.session_state.chat_session = None

# --- 5. 顯示對話歷史 ---
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

# --- 6. 使用者輸入與 AI 處理 ---
if user_input := st.chat_input("在此輸入現場狀況，或回覆 AI 的提問..."):
    # 顯示並紀錄使用者輸入
    with st.chat_message("user"):
        st.markdown(user_input)
    st.session_state.messages.append({"role": "user", "content": user_input})

    # 初始化 Gemini 的 Chat 物件
    if st.session_state.chat_session is None:
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel('gemini-2.5-flash')
        st.session_state.chat_session = model.start_chat(history=[
            {"role": "user", "parts": [SYSTEM_PROMPT + "\n\n請了解上述規則，了解請回覆『OK』。"]},
            {"role": "model", "parts": ["OK，我已完全了解 IVD 領域的審核規則與輸出格式。請工程師輸入維修筆記。"]}
        ])

    # 傳送訊息給 AI 並取得回覆
    with st.chat_message("assistant"):
        with st.spinner('AI 正在精煉語句與格式化中... ⏳'):
            try:
                response = st.session_state.chat_session.send_message(user_input)
                st.markdown(response.text)
                st.session_state.messages.append({"role": "assistant", "content": response.text})
            except Exception as e:
                st.error(f"❌ 發生錯誤，請檢查網路狀態。\n錯誤訊息：{e}")

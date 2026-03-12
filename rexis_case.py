import streamlit as st
import google.generativeai as genai
import os

# --- 1. 頁面基本設定與 Roche 企業風格 (CSS) ---
st.set_page_config(page_title="REXIS Service Assistant", page_icon="🟦", layout="centered")

st.markdown("""
<style>
    .stApp { background-color: #F4F5F8; font-family: 'Segoe UI', Arial, sans-serif; }
    .roche-title { color: #0066CC; font-weight: 800; font-size: 2.2rem; border-bottom: 3px solid #0066CC; padding-bottom: 10px; margin-bottom: 5px; }
    .roche-subtitle { color: #555555; font-size: 1rem; margin-bottom: 25px; }
    .pri-alert-box { background-color: #FFF0F0; color: #D32F2F; padding: 20px; border-left: 8px solid #D32F2F; border-radius: 6px; font-size: 1.15rem; font-weight: bold; margin-top: 20px; margin-bottom: 25px; box-shadow: 0 4px 6px rgba(0,0,0,0.1); line-height: 1.6; }
    .pri-alert-title { font-size: 1.4rem; font-weight: 900; margin-bottom: 8px; display: flex; align-items: center; }
    .pri-reasoning { background-color: #E8F0FE; color: #004494; padding: 15px; border-radius: 6px; font-size: 1rem; margin-bottom: 20px; border: 1px solid #B6D4FE; }
</style>
""", unsafe_allow_html=True)

st.markdown('<div class="roche-title">REXIS Service AI Assistant</div>', unsafe_allow_html=True)
st.markdown('<div class="roche-subtitle">自動化服務日誌轉換與 PRI/PSI 智能法規篩選系統 (PDF 增強版)</div>', unsafe_allow_html=True)

# --- 2. 側邊欄：設定 API Key ---
with st.sidebar:
    st.markdown("<h3 style='color: #0066CC;'>⚙️ System Settings</h3>", unsafe_allow_html=True)
    try:
        api_key = st.secrets["GEMINI_API_KEY"]
        st.success("✅ Secure API Key Loaded")
    except KeyError:
        st.error("⚠️ 尚未設定雲端 API Key 保險箱！")
        st.stop()
        
    if st.button("🔄 Restart Session (清除紀錄)"):
        st.session_state.messages = []
        st.session_state.chat_session = None
        st.rerun()
        
    st.markdown("---")
    st.caption("💡 提示：若為檢驗數值異常 (ER) 案件，請盡量提供原數值與重測數值。AI 將自動比對 PRI_Criteria.pdf 進行判定。")

# --- 3. 核心功能：快取並上傳 PDF 文件 ---
@st.cache_resource
def load_document_to_gemini(key, file_path):
    """將 PDF 上傳給 Gemini 並回傳文件物件，避免每次對話重複上傳"""
    genai.configure(api_key=key)
    if os.path.exists(file_path):
        try:
            return genai.upload_file(path=file_path, display_name="PRI_Criteria")
        except Exception as e:
            st.sidebar.error(f"上傳 PDF 失敗: {e}")
            return None
    else:
        st.sidebar.warning(f"找不到 {file_path}，AI 將僅能依賴基本邏輯判斷。")
        return None

# 初始化文件
pdf_document = load_document_to_gemini(api_key, "PRI_Criteria.pdf")

# --- 4. 系統提示詞 (Prompt) 模板 - 強制說明觸發理由 ---
SYSTEM_PROMPT = """
你是一位專業的「IVD 設備商」資深技術與應用支援主管，精通 Roche 的 QARA 規範。
我會提供一份名為 PRI_Criteria.pdf 的法規文件。請你**嚴格依據這份文件中的標準（特別是 Criteria to classify as PRI ER）**來評估工程師的日誌。

【PRI / PSI 智能判斷與提問邏輯】
1. 若為單純硬體故障（無數值異常或錯誤報告發出），請勿詢問 PRI，直接輸出日誌。
2. 若涉及檢驗異常 (ER)：
   - 請自動在 PDF 中搜尋對應的 Parameter/Test（如 HbA1c, Troponin T hs 等）。
   - 確認工程師提供的數值偏差是否達到 PDF 中規定的標準。
   - 若資訊不足以計算偏差或確認是否影響臨床決策，請提問要求補充（如：「請問原測量值與重測值各是多少？」）。

【目標格式與觸發說明機制】
當資訊齊全準備輸出最終日誌時，請依據以下結構輸出：

1. **法規判斷觸發器與說明**：
   - 如果案件達到 PDF 中的 PRI 升級標準，請在最開頭獨立一行輸出 `[PRI_ALERT]`。
   - 緊接著 `[PRI_ALERT]` 之後，**你必須**輸出一段名為「💡 **PRI 評估說明：**」的文字，明確寫出：
     (1) 參考的文件 Unique Identifier (如 CT-174) 與測試項目。
     (2) 文件中規定的確切升級標準 (Criteria)。
     (3) 根據工程師輸入的數值，你計算出的偏差值為何，以及為何判定達標/未達標。
     範例：「根據文件 CT-174 (Troponin T hs)，標準為數值 >=14 pg/mL 時誤差大於 20%。本次原值 20，重測值 14，偏差達 30%，因此觸發 PRI 升級。」

2. 接著輸出「✅ **轉換完成，標準格式如下：**」
3. 嚴格輸出 5 大標準項目：
* **01_客戶問題描述與報錯代碼**
* **02_客戶已經採取哪些行動嘗試解決問題**
* **03_處理過程與觀察測試結果**
* **04_本次服務是否結案**
* **05_客戶需要配合與改善的事項**
"""

# --- 5. 初始化 Session State ---
if "messages" not in st.session_state:
    st.session_state.messages = [
        {"role": "assistant", "content": "您好！請輸入本次的現場服務筆記。系統將自動為您格式化，並比對 PRI_Criteria 文件進行精準的法規風險評估。"}
    ]
if "chat_session" not in st.session_state:
    st.session_state.chat_session = None

# --- 6. 顯示對話歷史 ---
for msg in st.session_state.messages:
    if msg["role"] == "assistant" and "💡 **PRI 評估說明：**" in msg["content"]:
        parts = msg["content"].split("✅ **轉換完成")
        st.markdown(f'<div class="pri-reasoning">{parts[0]}</div>', unsafe_allow_html=True)
        if len(parts) > 1:
            st.markdown("✅ **轉換完成" + parts[1])
    else:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

# --- 7. 使用者輸入與 AI 處理 ---
if user_input := st.chat_input("在此輸入現場狀況，或回覆提問..."):
    with st.chat_message("user"):
        st.markdown(user_input)
    st.session_state.messages.append({"role": "user", "content": user_input})

    if st.session_state.chat_session is None:
        genai.configure(api_key=api_key)
        # ⚠️ 已改回您測試成功的版本：gemini-2.5-flash
        model = genai.GenerativeModel('gemini-2.5-flash') 
        
        history_parts = [SYSTEM_PROMPT + "\n\n請了解上述規則，了解請回覆『OK』。"]
        if pdf_document:
            history_parts.insert(0, pdf_document)
            
        st.session_state.chat_session = model.start_chat(history=[
            {"role": "user", "parts": history_parts},
            {"role": "model", "parts": ["OK，我已完全了解，將會讀取文件標準，並在判定觸發 PRI 時明確說明引用條款與計算理由。請輸入服務筆記。"]}
        ])

    with st.chat_message("assistant"):
        with st.spinner('AI 正在翻閱 PRI 文件進行比對與處理中... ⏳'):
            try:
                response = st.session_state.chat_session.send_message(user_input)
                raw_text = response.text
                
                # --- 攔截 PRI_ALERT 標籤並觸發大字報 ---
                if "[PRI_ALERT]" in raw_text:
                    st.markdown("""
                    <div class="pri-alert-box">
                        <div class="pri-alert-title">🚨 【法規升級警告】</div>
                        系統偵測到此案件涉及顯著的檢驗數值異常 (ER) 或錯誤報告發出。<br>
                        依據羅氏 QARA 規範與清單比對，此案件符合 PRI / PSI 通報標準。<br><br>
                        <b>🛑 請勿將此 Log 存入一般案件，請立即「重新開立專屬的 PRI/PSI 案件」進行處理與通報！</b>
                    </div>
                    """, unsafe_allow_html=True)
                    clean_text = raw_text.replace("[PRI_ALERT]", "").strip()
                else:
                    clean_text = raw_text

                # 顯示 AI 的評估說明與 5 大點內文
                if "💡 **PRI 評估說明：**" in clean_text:
                    parts = clean_text.split("✅ **轉換完成")
                    st.markdown(f'<div class="pri-reasoning">{parts[0]}</div>', unsafe_allow_html=True)
                    if len(parts) > 1:
                        st.markdown("✅ **轉換完成" + parts[1])
                else:
                    st.markdown(clean_text)
                
                st.session_state.messages.append({"role": "assistant", "content": clean_text})
                
            except Exception as e:
                st.error(f"❌ 發生錯誤，請檢查網路狀態或 API 額度

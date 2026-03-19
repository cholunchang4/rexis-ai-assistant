import streamlit as st
import google.generativeai as genai
import os
import urllib.parse
from streamlit_mic_recorder import speech_to_text
import streamlit.components.v1 as components

# --- 1. 頁面基本設定與 Roche 企業風格 (CSS) ---
st.set_page_config(page_title="REXIS Service Assistant", page_icon="🟦", layout="centered")

st.markdown("""
<style>
    :root {
        --roche-blue: #0066CC; --subtitle-color: #555555;
        --alert-bg: #FFF0F0; --alert-border: #D32F2F; --alert-text: #B71C1C;
        --info-bg: #E8F0FE; --info-border: #B6D4FE; --info-text: #004494;
    }
    @media (prefers-color-scheme: dark) {
        :root {
            --roche-blue: #5B9AFF; --subtitle-color: #AAAAAA;
            --alert-bg: #3A1616; --alert-border: #FF6666; --alert-text: #FF9999;
            --info-bg: #142840; --info-border: #2D5A88; --info-text: #8AB4F8;
        }
    }
    .stApp { font-family: 'Segoe UI', Arial, sans-serif; }
    .roche-title { color: var(--roche-blue); font-weight: 800; font-size: 2.2rem; border-bottom: 3px solid var(--roche-blue); padding-bottom: 10px; margin-bottom: 5px; }
    .roche-subtitle { color: var(--subtitle-color); font-size: 1rem; margin-bottom: 15px; }
    
    .pri-container { margin-top: 15px; margin-bottom: 25px; box-shadow: 0 4px 10px rgba(0,0,0,0.08); border-radius: 8px; overflow: hidden; }
    .pri-alert-header { background-color: var(--alert-bg); color: var(--alert-text); padding: 15px 20px; font-size: 1.25rem; font-weight: 900; border-left: 8px solid var(--alert-border); display: flex; align-items: center; }
    .pri-reasoning-body { background-color: var(--info-bg); color: var(--info-text); padding: 15px 20px; font-size: 0.95rem; line-height: 1.6; border-left: 8px solid var(--info-border); border-top: 1px solid #ffffff33; }
    
    .developer-signature { text-align: center; margin-top: 50px; padding-top: 20px; border-top: 1px solid #E0E0E0; color: #888888; font-size: 0.85rem; font-weight: 500; letter-spacing: 0.5px;}
    .email-btn { background-color: var(--roche-blue); color: white !important; padding: 0.4rem 1rem; border-radius: 4px; text-decoration: none; font-weight: bold; font-size: 0.9rem; display: inline-block; margin-top: 10px; text-align: center;}
    .email-btn:hover { opacity: 0.8; }
</style>
""", unsafe_allow_html=True)

# --- 2. 注入 JavaScript 快捷鍵監聽器 (隱藏於背景) ---
components.html("""
<script>
const doc = window.parent.document;
doc.addEventListener('keydown', function(e) {
    if ((e.ctrlKey || e.metaKey) && e.shiftKey) {
        if (e.key.toLowerCase() === 'e') {
            e.preventDefault();
            let emailBtns = Array.from(doc.querySelectorAll('.email-btn'));
            if(emailBtns.length > 0) emailBtns[emailBtns.length - 1].click();
        }
        if (e.key.toLowerCase() === 's') {
            e.preventDefault();
            let buttons = Array.from(doc.querySelectorAll('button'));
            let dlBtns = buttons.filter(b => b.innerText.includes('下載 TXT'));
            if(dlBtns.length > 0) dlBtns[dlBtns.length - 1].click();
        }
        if (e.key.toLowerCase() === 'c') {
            e.preventDefault();
            let codeBlocks = doc.querySelectorAll('code');
            if(codeBlocks.length > 0) {
                navigator.clipboard.writeText(codeBlocks[codeBlocks.length - 1].innerText);
                let toast = doc.createElement('div');
                toast.innerText = '✅ 5大點日誌已成功複製！';
                toast.style.cssText = 'position:fixed; bottom:30px; right:30px; background:#0066CC; color:white; padding:12px 24px; border-radius:8px; z-index:9999; font-weight:bold; box-shadow:0 4px 12px rgba(0,0,0,0.3); transition: opacity 0.5s;';
                doc.body.appendChild(toast);
                setTimeout(() => { toast.style.opacity = '0'; setTimeout(() => toast.remove(), 500); }, 2000);
            }
        }
    }
});
</script>
""", height=0, width=0)

# --- 3. 標題區塊與使用說明 ---
st.markdown('<div class="roche-title">REXIS Service AI Assistant</div>', unsafe_allow_html=True)
st.markdown('<div class="roche-subtitle">自動化服務日誌轉換與 PRI/PSI 智能法規篩選系統</div>', unsafe_allow_html=True)

with st.expander("📖 如何使用此系統？ (點擊展開)"):
    st.markdown("""
    **👋 歡迎使用 REXIS AI 助手！本系統將協助您快速產出標準日誌，並自動把關法規風險。**
    
    1. **輸入狀況：** 在下方輸入框打字，或點擊「🎙️」按鈕使用語音輸入。
       * *💡 提示：若案件涉及檢驗數值異常 (ER)，請盡量提供「測試項目」、「原數值」與「重測數值」，以利系統比對。*
    2. **AI 智慧處理：** 系統會自動將口語內容轉為 REXIS 標準 5 大點格式。
    3. **🛡️ 法規自動判斷：** 系統會背景讀取羅氏原廠文件。若案件符合 PRI 升級標準，會彈出 **紅色大字報** 與 **法規評估說明**，提醒您須另開專屬案件。
    4. **一鍵匯出與快捷鍵：** * 使用快捷鍵 **`Ctrl + Shift + C`** 即可一鍵複製 5大點日誌。
       * 可設定預設主管信箱，使用 **`Ctrl + Shift + E`** 快速發送 Email。
       * 使用 **`Ctrl + Shift + S`** 可快速下載日誌 TXT 檔。
    """)

# --- 4. 側邊欄：設定 API、Email 與開發者簽名 ---
with st.sidebar:
    st.markdown("<h3 style='color: var(--roche-blue);'>⚙️ System Settings</h3>", unsafe_allow_html=True)
    try:
        api_key = st.secrets["GEMINI_API_KEY"]
        st.success("✅ Secure API Key Loaded")
    except KeyError:
        st.error("⚠️ 尚未設定雲端 API Key 保險箱！")
        st.stop()
    
    st.markdown("---")
    st.markdown("📩 **匯出設定**")
    default_email = st.text_input("預設收件信箱 (例如主管信箱)", value="", placeholder="name@roche.com")
    
    st.markdown("---")
    if st.button("🔄 Restart Session (清除紀錄)"):
        st.session_state.messages = []
        st.session_state.chat_session = None
        st.rerun()
        
    st.markdown('<div class="developer-signature">Designed & Developed by<br><b>Cholun Chang</b></div>', unsafe_allow_html=True)

# --- 5. 核心功能：快取並上傳 PDF 文件 ---
@st.cache_resource
def load_document_to_gemini(key, file_path):
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

pdf_document = load_document_to_gemini(api_key, "PRI_Criteria.pdf")

# --- 6. 系統提示詞 (Prompt) 模板 (修復版：強制輸出5大點) ---
SYSTEM_PROMPT = """
你是一位專業的「IVD 設備商」資深技術與應用支援主管，精通 Roche 的 QARA 規範。
我會提供一份名為 PRI_Criteria.pdf 的法規文件。請你嚴格依據這份文件中的標準來評估工程師的日誌，並將日誌轉換為標準 5 大點格式。

【PRI / PSI 智能判斷邏輯】
1. 若為單純硬體故障：不需評估法規，請直接輸出 5 大點日誌。
2. 若涉及檢驗異常 (ER)：搜尋 PDF 標準，確認偏差是否達標。
   - 若達標：在最開頭獨立一行輸出 `[PRI_ALERT]`，接著輸出「💡 **PRI 評估說明：**」解釋計算過程。
   - 若未達標：不需輸出 `[PRI_ALERT]`，但可以輸出「💡 **PRI 評估說明：**」解釋為何未達標。

【目標輸出格式 (非常重要)】
請你「務必」嚴格依照以下順序與格式輸出：

(如果有 ER 評估才輸出這段)
💡 **PRI 評估說明：** [你的評估理由與偏差計算...]

✅ **轉換完成，可利用快捷鍵或下方按鈕操作：**
```text
* 01_客戶問題描述與報錯代碼：[內容]
* 02_客戶已經採取哪些行動嘗試解決問題：[內容或 NA]
* 03_處理過程與觀察測試結果：[內容]
* 04_本次服務是否結案：[內容]
* 05_客戶需要配合與改善的事項：[內容或 NA]
```
(請確保這 5 點被包覆在 ```text 和 ``` 之間)
"""

# --- 7. 初始化 Session State ---
if "messages" not in st.session_state:
    st.session_state.messages = [{"role": "assistant", "content": "您好！請輸入本次的現場服務筆記，**您也可以點擊下方麥克風使用語音輸入** 🎙️。系統將為您自動格式化並評估法規風險。"}]
if "chat_session" not in st.session_state:
    st.session_state.chat_session = None

# --- 8. 顯示對話歷史與動態按鈕 ---
for i, msg in enumerate(st.session_state.messages):
    if msg["role"] == "assistant" and "💡 **PRI 評估說明：**" in msg["content"]:
        parts = msg["content"].split("✅ **轉換完成")
        reasoning = parts[0].replace("💡 **PRI 評估說明：**", "").strip()
        
        st.markdown(f"""
        <div class="pri-container">
            <div class="pri-alert-header" style="background-color: var(--info-border); color: var(--info-text); border-left-color: var(--roche-blue);">💡 【法規狀態說明】</div>
            <div class="pri-reasoning-body"><b>系統評估依據：</b><br>{reasoning}</div>
        </div>
        """, unsafe_allow_html=True)
        
        if len(parts) > 1:
            st.markdown("✅ **轉換完成" + parts[1])
            
            # 加入下載與 Email 按鈕
            log_content = parts[1].split("```text")[-1].replace("```", "").strip()
            col1, col2 = st.columns([1, 4])
            with col1:
                st.download_button("💾 下載 TXT", data=log_content, file_name="REXIS_Service_Log.txt", mime="text/plain", key=f"dl_{i}")
            with col2:
                subject = urllib.parse.quote("REXIS Service Log 提報")
                body = urllib.parse.quote("主管您好，\n\n以下為本次服務日誌：\n\n" + log_content + "\n\nDesigned & Developed by Cholun Chang")
                mailto_url = f"mailto:{default_email}?subject={subject}&body={body}"
                st.markdown(f'<a href="{mailto_url}" target="_blank" class="email-btn">📧 以 Email 發送</a>', unsafe_allow_html=True)
    else:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

# --- 9. 輸入區 (文字 + 語音) ---
st.markdown("---")
# 語音輸入
spoken_text = speech_to_text(language='zh-TW', start_prompt="🎙️ 點此開始錄音 (允許麥克風權限)", stop_prompt="⏹️ 點此停止錄音", just_once=True, key='STT')
# 文字輸入
text_input = st.chat_input("或在此輸入文字狀況...")

user_input = spoken_text if spoken_text else text_input

if user_input:
    with st.chat_message("user"):
        st.markdown(user_input)
    st.session_state.messages.append({"role": "user", "content": user_input})

    if st.session_state.chat_session is None:
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel('gemini-2.5-flash') 
        history_parts = [SYSTEM_PROMPT + "\n\n請了解上述規則，了解請回覆『OK』。"]
        if pdf_document:
            history_parts.insert(0, pdf_document)
        st.session_state.chat_session = model.start_chat(history=[
            {"role": "user", "parts": history_parts},
            {"role": "model", "parts": ["OK，我已完全了解。我會嚴格依照要求的格式，在評估完法規後，務必輸出 5 大點日誌。請輸入服務筆記。"]}
        ])

    with st.chat_message("assistant"):
        with st.spinner('AI 正在處理日誌並翻閱 PRI 文件進行比對... ⏳'):
            try:
                response = st.session_state.chat_session.send_message(user_input)
                raw_text = response.text
                
                if "[PRI_ALERT]" in raw_text:
                    clean_text = raw_text.replace("[PRI_ALERT]", "").strip()
                    # 如果有觸發 ALERT，顯示紅色的強烈警告大字報
                    st.markdown("""
                    <div class="pri-container" style="border: 2px solid var(--alert-border);">
                        <div class="pri-alert-header">🚨 【法規升級警告】</div>
                        <div class="pri-reasoning-body" style="color: var(--alert-text); background-color: var(--alert-bg);">
                        <b>🛑 請勿將此 Log 存入一般案件，請立即「重新開立專屬的 PRI/PSI 案件」進行處理與通報！</b>
                        </div>
                    </div>
                    """, unsafe_allow_html=True)
                else:
                    clean_text = raw_text

                if "💡 **PRI 評估說明：**" in clean_text:
                    parts = clean_text.split("✅ **轉換完成")
                    reasoning = parts[0].replace("💡 **PRI 評估說明：**", "").strip()
                    
                    # 顯示評估依據的藍色框
                    st.markdown(f"""
                    <div class="pri-container">
                        <div class="pri-alert-header" style="background-color: var(--info-border); color: var(--info-text); border-left-color: var(--roche-blue);">💡 【法規狀態說明】</div>
                        <div class="pri-reasoning-body"><b>系統評估依據：</b><br>{reasoning}</div>
                    </div>
                    """, unsafe_allow_html=True)
                    
                    if len(parts) > 1:
                        st.markdown("✅ **轉換完成" + parts[1])
                        log_content = parts[1].split("```text")[-1].replace("```", "").strip()
                        col1, col2 = st.columns([1, 4])
                        with col1:
                            st.download_button("💾 下載 TXT", data=log_content, file_name="REXIS_Service_Log.txt", mime="text/plain", key="dl_current")
                        with col2:
                            subject = urllib.parse.quote("REXIS Service Log 提報")
                            body = urllib.parse.quote("主管您好，\n\n以下為本次服務日誌：\n\n" + log_content + "\n\nDesigned & Developed by Cholun Chang")
                            mailto_url = f"mailto:{default_email}?subject={subject}&body={body}"
                            st.markdown(f'<a href="{mailto_url}" target="_blank" class="email-btn">📧 以 Email 發送</a>', unsafe_allow_html=True)
                else:
                    st.markdown(clean_text)
                
                st.session_state.messages.append({"role": "assistant", "content": clean_text})
                
            except Exception as e:
                st.error(f"❌ 發生錯誤，請檢查網路狀態或 API 額度。\n錯誤訊息：{e}")

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

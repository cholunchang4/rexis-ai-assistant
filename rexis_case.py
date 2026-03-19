import streamlit as st
import google.generativeai as genai
import os
import urllib.parse
import re
from streamlit_mic_recorder import speech_to_text
import streamlit.components.v1 as components

# 💡 終極防護：避免網頁顯示器把程式碼切斷
tick3 = "``" + "`"

# --- 1. 頁面基本設定與 頂級 SaaS 企業風格 (CSS) ---
st.set_page_config(page_title="REXIS Service Assistant", page_icon="🧬", layout="centered")

st.markdown("""
<style>
    :root {
        --roche-blue: #0066CC; 
        --roche-cyan: #00BFFF;
        --subtitle-color: #64748B;
        --bg-color: #F8FAFC;
        --primary-gradient: linear-gradient(135deg, #0066CC 0%, #00BFFF 100%);
        --alert-gradient: linear-gradient(135deg, #FEF2F2 0%, #FEE2E2 100%);
        --alert-border: #EF4444;
        --alert-text: #991B1B;
        --info-gradient: linear-gradient(135deg, #F0FdfA 0%, #E0F2FE 100%);
        --info-border: #0ea5e9;
        --info-text: #0369A1;
        --card-shadow: 0 10px 25px -5px rgba(0, 0, 0, 0.05), 0 8px 10px -6px rgba(0, 0, 0, 0.01);
        --card-radius: 12px;
    }
    
    @media (prefers-color-scheme: dark) {
        :root {
            --roche-blue: #3B82F6; 
            --roche-cyan: #38BDF8;
            --subtitle-color: #94A3B8;
            --bg-color: #0F172A;
            --primary-gradient: linear-gradient(135deg, #3B82F6 0%, #0EA5E9 100%);
            --alert-gradient: linear-gradient(135deg, #450A0A 0%, #220505 100%);
            --alert-border: #EF4444;
            --alert-text: #FCA5A5;
            --info-gradient: linear-gradient(135deg, #082F49 0%, #0C4A6E 100%);
            --info-border: #38BDF8;
            --info-text: #BAE6FD;
            --card-shadow: 0 10px 25px -5px rgba(0, 0, 0, 0.3);
        }
    }
    
    .stApp { font-family: 'Inter', 'Segoe UI', sans-serif; background-color: transparent; }
    
    .roche-title { 
        background: var(--primary-gradient);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        font-weight: 900; 
        font-size: 2.5rem; 
        letter-spacing: -0.5px;
        padding-bottom: 5px; 
        margin-bottom: 0px; 
    }
    
    .title-divider { height: 4px; width: 60px; background: var(--primary-gradient); border-radius: 2px; margin-top: 8px; margin-bottom: 15px; }
    .roche-subtitle { color: var(--subtitle-color); font-size: 1.05rem; font-weight: 500; margin-bottom: 20px; }
    
    .pri-container { margin-top: 20px; margin-bottom: 30px; box-shadow: var(--card-shadow); border-radius: var(--card-radius); overflow: hidden; transition: transform 0.2s ease; }
    .pri-container:hover { transform: translateY(-2px); }
    .pri-alert-header { background: var(--alert-gradient); color: var(--alert-text); padding: 16px 24px; font-size: 1.2rem; font-weight: 800; border-left: 6px solid var(--alert-border); display: flex; align-items: center; letter-spacing: 0.5px;}
    .pri-reasoning-body { background: var(--info-gradient); color: var(--info-text); padding: 20px 24px; font-size: 0.95rem; line-height: 1.7; border-left: 6px solid var(--info-border); }
    
    .developer-signature { text-align: center; margin-top: 60px; padding-top: 20px; border-top: 1px dashed #CBD5E1; color: var(--subtitle-color); font-size: 0.8rem; font-weight: 400; letter-spacing: 1px;}
    .email-btn { background: var(--primary-gradient); color: white !important; padding: 0.5rem 1.2rem; border-radius: 50px; text-decoration: none; font-weight: 600; font-size: 0.9rem; display: inline-block; margin-top: 10px; text-align: center; box-shadow: 0 4px 6px rgba(0,102,204,0.2); transition: all 0.3s ease; }
    .email-btn:hover { box-shadow: 0 6px 12px rgba(0,102,204,0.3); transform: translateY(-2px); }
</style>
""", unsafe_allow_html=True)

# --- 2. 注入 JavaScript 快捷鍵監聽器 ---
components.html("""
<script>
const doc = window.parent.document;
function fallbackCopyTextToClipboard(text) {
  var textArea = doc.createElement("textarea");
  textArea.value = text;
  textArea.style.top = "0"; textArea.style.left = "0"; textArea.style.position = "fixed";
  doc.body.appendChild(textArea); textArea.focus(); textArea.select();
  try { doc.execCommand('copy'); } catch (err) {}
  doc.body.removeChild(textArea);
}

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
                let textToCopy = codeBlocks[codeBlocks.length - 1].innerText;
                if (window.parent.navigator.clipboard) {
                    window.parent.navigator.clipboard.writeText(textToCopy).catch(() => fallbackCopyTextToClipboard(textToCopy));
                } else { fallbackCopyTextToClipboard(textToCopy); }
                
                let toast = doc.createElement('div');
                toast.innerHTML = '✨ <b>5大點日誌已成功複製！</b>';
                toast.style.cssText = 'position:fixed; bottom:40px; right:40px; background: linear-gradient(135deg, #0066CC, #00BFFF); color:white; padding:16px 28px; border-radius:50px; z-index:9999; font-family:sans-serif; box-shadow: 0 10px 25px rgba(0,102,204,0.4); transition: all 0.5s cubic-bezier(0.68, -0.55, 0.265, 1.55);';
                doc.body.appendChild(toast);
                setTimeout(() => { toast.style.opacity = '0'; toast.style.transform = 'translateY(20px)'; setTimeout(() => toast.remove(), 500); }, 2500);
            }
        }
    }
});
</script>
""", height=0, width=0)

# --- 3. 標題區塊與使用說明 ---
st.markdown('<div class="roche-title">REXIS Service Assistant</div>', unsafe_allow_html=True)
st.markdown('<div class="title-divider"></div>', unsafe_allow_html=True)
st.markdown('<div class="roche-subtitle">自動化服務日誌轉換與 PRI/PSI 智能法規篩選系統</div>', unsafe_allow_html=True)

with st.expander("📖 系統操作指南 (點擊展開)"):
    st.markdown("""
    **👋 歡迎！本系統將協助您以最高效率產出標準日誌，並自動把關法規風險。**
    
    * 🎙️ **語音/文字輸入：** 若案件涉及檢驗數值異常 (ER)，請務必提及「測試項目」、「原數值」與「重測數值」。提及「醫院名稱」將自動為檔案命名。
    * 🛡️ **法規智能判斷：** 系統背景比對羅氏原廠文件。若觸發 PRI 升級標準，將以卡片提示您另開專案。
    * ⚡ **鍵盤極速操作 (快捷鍵)：**
        * `Ctrl + Shift + C`：一鍵複製產出的 5大點日誌。
        * `Ctrl + Shift + E`：將日誌快速發送至側邊欄設定的個人備份信箱。
        * `Ctrl + Shift + S`：快速下載 TXT 檔。
    """)

# --- 4. 側邊欄 ---
with st.sidebar:
    st.markdown("<h3 style='color: var(--roche-blue); font-weight:800;'>⚙️ Settings</h3>", unsafe_allow_html=True)
    try:
        api_key = st.secrets["GEMINI_API_KEY"]
        st.success("✅ Secure API Key Loaded")
    except KeyError:
        st.error("⚠️ 尚未設定雲端 API Key 保險箱！")
        st.stop()
    
    st.markdown("---")
    st.markdown("📩 **個人備份設定**")
    default_email = st.text_input("個人備份信箱", value="", placeholder="your.name@roche.com")
    
    st.markdown("---")
    if st.button("🔄 Restart Session (清除對話)"):
        st.session_state.messages = []
        st.session_state.chat_session = None
        st.rerun()
        
    st.markdown('<div class="developer-signature">Designed & Developed by<br><span style="font-weight:700; color:var(--roche-blue); font-size:1rem;">Cholun Chang</span></div>', unsafe_allow_html=True)

# --- 5. 載入 PDF ---
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

# --- 6. 系統提示詞 (Prompt) 模板 ---
SYSTEM_PROMPT = f"""
你是一位專業的「IVD 設備商」資深技術與應用支援主管，精通 Roche 的 QARA 規範。
我會提供一份名為 PRI_Criteria.pdf 的法規文件。請你嚴格依據這份文件中的標準來評估工程師的日誌，並將日誌轉換為標準 5 大點格式。

【PRI / PSI 智能判斷邏輯 (非常重要)】
1. 排除條件 (不屬於 ER，絕對不觸發 PRI)：
   - 單純硬體/軟體故障（無病患數值異常發出）。
   - 「校正 (Calibration) 失敗」或「品管 (QC) 失敗/Out」：實務上這些情況發生時，機台會阻擋測試，不會有錯誤的病患報告發出給醫師。因此，這「絕對不屬於」檢驗異常 (ER)。若遇到這類情況，請判斷為未達標，不需啟動 PRI_ALERT，只需產出日誌即可。
2. 若涉及真實的病患檢驗異常 (ER) (例如：病患檢體測量數值偏差、發出偽陽性/偽陰性報告)：
   - 搜尋 PDF 標準，確認偏差是否達標。
   - 若達標：最開頭輸出 `[PRI_ALERT]`，並提供「💡 **PRI 評估說明：**」。
   - 若未達標：可提供「💡 **PRI 評估說明：**」解釋為何未達標。

【目標輸出格式 (非常重要)】
請你務必依照以下順序與格式輸出：

1. **擷取醫院/客戶名稱**：請從使用者的輸入中判斷是否有提到醫院、診所或客戶名稱(如:台大、榮總等)。
   - 如果有，請獨立一行輸出：`[HOSP_NAME: 該醫院名稱]`
   - 如果沒有提到，請獨立一行輸出：`[HOSP_NAME: NA]`

2. **法規評估說明** (若有 ER 評估才輸出)：
💡 **PRI 評估說明：** [理由...]

3. **日誌主體**：
✅ **轉換完成，請使用快捷鍵或點擊框框右上角 📋 複製：**
{tick3}text
* 01_客戶問題描述與報錯代碼：[內容]
* 02_客戶已經採取哪些行動嘗試解決問題：[內容或 NA]
* 03_處理過程與觀察測試結果：[內容]
* 04_本次服務是否結案：[內容]
* 05_客戶需要配合與改善的事項：[內容或 NA]
{tick3}
"""

# --- 7. 初始化 Session State ---
if "messages" not in st.session_state:
    st.session_state.messages = [{"role": "assistant", "content": "您好！請輸入本次的現場服務筆記，**推薦使用下方麥克風進行語音輸入** 🎙️。系統將為您自動格式化並評估法規風險。"}]
if "chat_session" not in st.session_state:
    st.session_state.chat_session = None

# --- 8. 顯示對話歷史與動態按鈕 ---
def render_assistant_message(msg_content, index):
    hosp_match = re.search(r"\x5bHOSP_NAME:\s*(.+?)\x5d", msg_content)
    hospital_name = ""
    if hosp_match and hosp_match.group(1).strip() != "NA":
        hospital_name = hosp_match.group(1).strip()
    
    clean_text = re.sub(r"\x5bHOSP_NAME:\s*.+?\x5d\n*", "", msg_content)
    clean_text = clean_text.replace("[PRI_ALERT]", "").strip()

    file_suffix = f"_{hospital_name}" if hospital_name else ""
    file_name = f"REXIS_Log{file_suffix}.txt"
    subject_title = f"REXIS 服務日誌備份{file_suffix}"

    if "[PRI_ALERT]" in msg_content:
        st.markdown("""
        <div class="pri-container">
            <div class="pri-alert-header">🚨 【法規升級警告】</div>
            <div class="pri-reasoning-body" style="color: var(--alert-text); background: var(--alert-gradient); border-left-color: var(--alert-border);">
            <b>🛑 依據法規標準，請勿將此 Log 存入一般案件，請立即「重新開立專屬的 PRI/PSI 案件」！</b>
            </div>
        </div>
        """, unsafe_allow_html=True)

    if "💡 **PRI 評估說明：**" in clean_text:
        parts = clean_text.split("✅ **轉換完成")
        reasoning = parts[0].replace("💡 **PRI 評估說明：**", "").strip()
        
        st.markdown(f"""
        <div class="pri-container">
            <div class="pri-alert-header" style="background: var(--info-gradient); color: var(--info-text); border-left-color: var(--roche-blue);">💡 【法規狀態說明】</div>
            <div class="pri-reasoning-body"><b>系統評估依據：</b><br>{reasoning}</div>
        </div>
        """, unsafe_allow_html=True)
        
        if len(parts) > 1:
            st.markdown("✅ **轉換完成" + parts[1])
            log_content = parts[1].split(f"{tick3}text")[-1].replace(tick3, "").strip()
            
            col1, col2 = st.columns([1, 4])
            with col1:
                st.download_button("💾 下載 TXT", data=log_content, file_name=file_name, mime="text/plain", key=f"dl_{index}")
            with col2:
                subject = urllib.parse.quote(subject_title)
                body = urllib.parse.quote("這是本次的 REXIS 服務日誌備份：\n\n" + log_content + "\n\nDesigned & Developed by Cholun Chang")
                mailto_url = f"mailto:{default_email}?subject={subject}&body={body}"
                st.markdown(f'<a href="{mailto_url}" target="_blank" class="email-btn">✨ 寄給自己備份</a>', unsafe_allow_html=True)
    else:
        st.markdown(clean_text)
        if f"{tick3}text" in clean_text:
            log_content = clean_text.split(f"{tick3}text")[-1].replace(tick3, "").strip()
            col1, col2 = st.columns([1, 4])
            with col1:
                st.download_button("💾 下載 TXT", data=log_content, file_name=file_name, mime="text/plain", key=f"dl_{index}")
            with col2:
                subject = urllib.parse.quote(subject_title)
                body = urllib.parse.quote("這是本次的 REXIS 服務日誌備份：\n\n" + log_content + "\n\nDesigned & Developed by Cholun Chang")
                mailto_url = f"mailto:{default_email}?subject={subject}&body={body}"
                st.markdown(f'<a href="{mailto_url}" target="_blank" class="email-btn">✨ 寄給自己備份</a>', unsafe_allow_html=True)

for i, msg in enumerate(st.session_state.messages):
    if msg["role"] == "assistant":
        render_assistant_message(msg["content"], i)
    else:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

# --- 9. 輸入區 (文字 + 語音) ---
st.markdown("---")
spoken_text = speech_to_text(language='zh-TW', start_prompt="🎙️ 點此開始錄音 (允許麥克風權限)", stop_prompt="⏹️ 點此停止錄音", just_once=True, key='STT')
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
            {"role": "model", "parts": ["OK，我已完全了解。我會擷取醫院名稱，並嚴格輸出 5 大點日誌。請輸入服務筆記。"]}
        ])

    with st.chat_message("assistant"):
        status = st.status("🧠 AI 正在處理中...", expanded=True)
        status.write("🔍 分析語意並擷取關鍵數據...")
        status.write("📚 翻閱 PRI/PSI 法規文件進行比對...")
        
        try:
            response = st.session_state.chat_session.send_message(user_input)
            status.update(label="✅ 處理完成！", state="complete", expanded=False)
            st.session_state.messages.append({"role": "assistant", "content": response.text})
            st.rerun() 
            
        except Exception as e:
            status.update(label="❌ 發生錯誤", state="error", expanded=False)
            st.error(f"請檢查網路狀態或 API 額度。\n錯誤訊息：{e}")

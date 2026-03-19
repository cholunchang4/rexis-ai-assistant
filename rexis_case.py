import streamlit as st
import google.generativeai as genai
import os
import urllib.parse
import re
from streamlit_mic_recorder import speech_to_text
import streamlit.components.v1 as components

# --- 1. 頁面基本設定與 SaaS 風格 CSS ---
st.set_page_config(page_title="REXIS Service Assistant", page_icon="🟦", layout="centered")

st.markdown("""
<style>
    :root {
        --primary-color: #0066CC;
        --bg-color: #FFFFFF;
        --text-main: #1F2937;
        --text-muted: #6B7280;
        --border-color: #E5E7EB;
        --alert-bg: #FEF2F2;
        --alert-border: #EF4444;
        --alert-text: #B91C1C;
        --info-bg: #F8FAFC;
        --info-border: #3B82F6;
        --info-text: #1D4ED8;
    }
    @media (prefers-color-scheme: dark) {
        :root {
            --primary-color: #3B82F6;
            --bg-color: #111827;
            --text-main: #F3F4F6;
            --text-muted: #9CA3AF;
            --border-color: #374151;
            --alert-bg: #450a0a;
            --alert-text: #FCA5A5;
            --info-bg: #0F172A;
            --info-text: #93C5FD;
        }
    }
    
    .stApp { font-family: 'Inter', -apple-system, BlinkMacSystemFont, "Segoe UI", Helvetica, Arial, sans-serif; }
    .roche-title { color: var(--primary-color); font-weight: 800; font-size: 2.2rem; margin-bottom: 0px; letter-spacing: -0.5px;}
    .title-divider { height: 3px; width: 40px; background-color: var(--primary-color); border-radius: 2px; margin-top: 8px; margin-bottom: 12px; }
    .roche-subtitle { color: var(--text-muted); font-size: 1rem; font-weight: 500; margin-bottom: 20px; }
    
    .base-card { background-color: var(--bg-color); border: 1px solid var(--border-color); border-radius: 8px; padding: 20px; margin-bottom: 20px; box-shadow: 0 1px 3px rgba(0,0,0,0.05); }
    .alert-card { border-left: 4px solid var(--alert-border); background-color: var(--alert-bg); }
    .alert-title { color: var(--alert-text); font-weight: 700; font-size: 1.1rem; margin-bottom: 8px; display: flex; align-items: center;}
    .info-card { border-left: 4px solid var(--info-border); background-color: var(--info-bg); }
    .info-title { color: var(--info-text); font-weight: 700; font-size: 1rem; margin-bottom: 8px; }
    .info-body { color: var(--text-main); font-size: 0.95rem; line-height: 1.6; }
    
    .action-bar { display: flex; gap: 12px; margin-top: 15px; padding-top: 15px; border-top: 1px solid var(--border-color); flex-wrap: wrap; }
    .action-btn { background-color: transparent; color: var(--text-main) !important; border: 1px solid var(--border-color); padding: 8px 16px; border-radius: 6px; font-size: 0.9rem; font-weight: 600; cursor: pointer; text-decoration: none; display: inline-flex; align-items: center; justify-content: center; transition: all 0.2s ease; }
    .action-btn:hover { background-color: var(--info-bg); border-color: var(--primary-color); color: var(--primary-color) !important; }
    .developer-signature { text-align: center; margin-top: 50px; color: var(--text-muted); font-size: 0.8rem; font-weight: 500; }
</style>
""", unsafe_allow_html=True)

# --- 2. 注入 JavaScript (剪貼簿與快捷鍵) ---
components.html("""
<script>
const doc = window.parent.document;
function fallbackCopyTextToClipboard(text) {
  var textArea = doc.createElement("textarea");
  textArea.value = text; textArea.style.top = "0"; textArea.style.left = "0"; textArea.style.position = "fixed";
  doc.body.appendChild(textArea); textArea.focus(); textArea.select();
  try { doc.execCommand('copy'); } catch (err) {} doc.body.removeChild(textArea);
}
function showToast(message) {
    let toast = doc.createElement('div'); toast.innerHTML = message;
    toast.style.cssText = 'position:fixed; bottom:30px; left:50%; transform:translateX(-50%); background:#1F2937; color:white; padding:12px 24px; border-radius:8px; z-index:9999; font-family:sans-serif; font-size:14px; box-shadow: 0 4px 6px rgba(0,0,0,0.1); transition: opacity 0.3s;';
    doc.body.appendChild(toast); setTimeout(() => { toast.style.opacity = '0'; setTimeout(() => toast.remove(), 300); }, 2000);
}
doc.addEventListener('click', function(e) {
    if (e.target && e.target.closest('.btn-copy')) {
        let btn = e.target.closest('.btn-copy'); let textToCopy = decodeURIComponent(btn.getAttribute('data-clipboard'));
        if (window.parent.navigator.clipboard) {
            window.parent.navigator.clipboard.writeText(textToCopy).then(() => showToast('✅ 日誌已複製到剪貼簿')).catch(() => { fallbackCopyTextToClipboard(textToCopy); showToast('✅ 日誌已複製'); });
        } else { fallbackCopyTextToClipboard(textToCopy); showToast('✅ 日誌已複製'); }
    }
});
doc.addEventListener('keydown', function(e) {
    if ((e.ctrlKey || e.metaKey) && e.shiftKey) {
        if (e.key.toLowerCase() === 'e') { e.preventDefault(); let btns = Array.from(doc.querySelectorAll('.btn-email')); if(btns.length > 0) btns[btns.length - 1].click(); }
        if (e.key.toLowerCase() === 's') { e.preventDefault(); let btns = Array.from(doc.querySelectorAll('.btn-download')); if(btns.length > 0) btns[btns.length - 1].click(); }
        if (e.key.toLowerCase() === 'c') { e.preventDefault(); let btns = Array.from(doc.querySelectorAll('.btn-copy')); if(btns.length > 0) btns[btns.length - 1].click(); }
    }
});
</script>
""", height=0, width=0)

# --- 3. 初始化 Session State ---
if "messages" not in st.session_state:
    st.session_state.messages = [{"role": "assistant", "content": "您好！請輸入現場狀況，推薦使用下方麥克風 🎙️ 語音輸入。系統將自動整理 5 大點並把關法規風險。"}]
if "chat_session" not in st.session_state: st.session_state.chat_session = None
if "mic_key" not in st.session_state: st.session_state.mic_key = 0 

# --- 4. 標題與操作說明 ---
st.markdown('<div class="roche-title">REXIS Assistant</div>', unsafe_allow_html=True)
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

# --- 5. 側邊欄 ---
with st.sidebar:
    st.markdown("<h3 style='color: var(--primary-color); font-weight:700;'>⚙️ Settings</h3>", unsafe_allow_html=True)
    try: api_key = st.secrets["GEMINI_API_KEY"]
    except KeyError: st.error("⚠️ 尚未設定雲端 API Key！"); st.stop()
    
    st.markdown("📩 **個人備份設定**")
    default_email = st.text_input("接收信箱", value="", placeholder="your.name@roche.com")
    st.markdown("---")
    if st.button("🔄 清除對話紀錄", use_container_width=True):
        st.session_state.messages = [{"role": "assistant", "content": "對話已清除！請輸入現場狀況。"}]
        st.session_state.chat_session = None
        st.session_state.mic_key += 1 
        st.rerun()
    st.markdown('<div class="developer-signature">Designed by <b>Cholun Chang</b></div>', unsafe_allow_html=True)

@st.cache_resource
def load_document_to_gemini(key, file_path):
    genai.configure(api_key=key)
    if os.path.exists(file_path):
        try: return genai.upload_file(path=file_path, display_name="PRI_Criteria")
        except Exception: return None
    return None
pdf_document = load_document_to_gemini(api_key, "PRI_Criteria.pdf")

# --- 6. 系統提示詞 (導入軍規級標籤系統) ---
SYSTEM_PROMPT = """
你是一位專業的 IVD 設備支援主管，精通 Roche QARA 規範。
【法規判斷邏輯】
1. 排除條件：單純硬體故障、「校正(Calibration)/QC 失敗」(機台會阻擋測試，不會發出病患報告，故絕不屬於 ER，無需 PRI)。
2. 真實 ER：確認偏差是否達標。

【強制輸出格式】
請嚴格使用以下標籤輸出，不要加上多餘的問候語。

[HOSP_NAME] 醫院名稱 (若無請填 NA)
[REASONING] 你的法規評估理由 (若是單純硬體故障不需評估，請填 NA)
[PRI_ALERT] YES 或 NO
[LOG]
* 01_客戶問題描述與報錯代碼：[內容]
* 02_客戶已經採取哪些行動嘗試解決問題：[內容或 NA]
* 03_處理過程與觀察測試結果：[內容]
* 04_本次服務是否結案：[內容]
* 05_客戶需要配合與改善的事項：[內容或 NA]
"""

# --- 7. 訊息渲染引擎 (精準解析器) ---
def render_assistant_message(msg_content):
    # 解析標籤
    hosp_match = re.search(r"\[HOSP_NAME\]\s*(.+)", msg_content)
    hospital_name = hosp_match.group(1).strip() if hosp_match and hosp_match.group(1).strip() != "NA" else ""
    
    reasoning_match = re.search(r"\[REASONING\]\s*(.+)", msg_content)
    reasoning = reasoning_match.group(1).strip() if reasoning_match and reasoning_match.group(1).strip() != "NA" else ""
    
    is_alert = "[PRI_ALERT] YES" in msg_content
    
    log_match = re.search(r"\[LOG\]\s*(.+)", msg_content, re.DOTALL)
    log_content = log_match.group(1).strip() if log_match else msg_content # 若解析失敗則顯示原文字

    file_name = f"REXIS_Log_{hospital_name}.txt" if hospital_name else "REXIS_Log.txt"
    subject_title = f"REXIS 服務日誌備份_{hospital_name}" if hospital_name else "REXIS 服務日誌備份"

    # 渲染 UI
    if is_alert:
        st.markdown("""
        <div class="base-card alert-card">
            <div class="alert-title">🚨 法規升級警告</div>
            <div class="info-body">依據法規標準，請勿將此 Log 存入一般案件，請立即<b>重新開立專屬的 PRI/PSI 案件</b>！</div>
        </div>
        """, unsafe_allow_html=True)

    if reasoning:
        st.markdown(f"""
        <div class="base-card info-card">
            <div class="info-title">💡 系統評估依據</div>
            <div class="info-body">{reasoning}</div>
        </div>
        """, unsafe_allow_html=True)

    if log_content:
        encoded_log = urllib.parse.quote(log_content)
        dl_href = f"data:text/plain;charset=utf-8,{encoded_log}"
        mail_href = f"mailto:{default_email}?subject={urllib.parse.quote(subject_title)}&body={urllib.parse.quote('這是本次的日誌備份：\\n\\n' + log_content)}"
        
        st.markdown(f"""
        <div class="base-card">
            <div style="white-space: pre-wrap; font-family: inherit; font-size: 0.95rem; color: var(--text-main); margin-bottom: 0;">{log_content}</div>
            <div class="action-bar">
                <button class="action-btn btn-copy" data-clipboard="{encoded_log}">📋 複製日誌</button>
                <a href="{dl_href}" download="{file_name}" class="action-btn btn-download">💾 下載 TXT</a>
                <a href="{mail_href}" target="_blank" class="action-btn btn-email">📧 寄給自己</a>
            </div>
        </div>
        """, unsafe_allow_html=True)

for msg in st.session_state.messages:
    if msg["role"] == "assistant":
        if msg["content"].startswith("您好！") or msg["content"].startswith("對話已清除"):
            with st.chat_message("assistant"): st.markdown(msg["content"])
        else:
            render_assistant_message(msg["content"])
    else:
        with st.chat_message("user"): st.markdown(msg["content"])

# --- 8. 輸入區 ---
st.markdown("---")
dynamic_mic_key = f"STT_{st.session_state.mic_key}"
spoken_text = speech_to_text(language='zh-TW', start_prompt="🎙️ 點此開始錄音", stop_prompt="⏹️ 停止錄音並送出", just_once=True, key=dynamic_mic_key)
text_input = st.chat_input("或在此輸入文字狀況...")

user_input = spoken_text if spoken_text else text_input

if user_input:
    with st.chat_message("user"): st.markdown(user_input)
    st.session_state.messages.append({"role": "user", "content": user_input})

    if st.session_state.chat_session is None:
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel('gemini-2.5-flash') 
        history_parts = [SYSTEM_PROMPT]
        if pdf_document: history_parts.insert(0, pdf_document)
        st.session_state.chat_session = model.start_chat(history=[
            {"role": "user", "parts": history_parts},
            {"role": "model", "parts": ["OK，我已完全了解。我會嚴格使用標籤格式輸出。"]}
        ])

    with st.chat_message("assistant"):
        status = st.status("🧠 系統分析中...", expanded=True)
        try:
            response = st.session_state.chat_session.send_message(user_input)
            status.update(label="✅ 處理完成！", state="complete", expanded=False)
            st.session_state.messages.append({"role": "assistant", "content": response.text})
            st.rerun() 
        except Exception as e:
            status.update(label="❌ 發生錯誤", state="error", expanded=False)
            st.error(f"請檢查網路狀態或 API。\n{e}")

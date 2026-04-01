import streamlit as st
import google.generativeai as genai
import os
import urllib.parse
import re
from streamlit_mic_recorder import speech_to_text
import streamlit.components.v1 as components

# 💡 終極防護：避免網頁顯示器把程式碼切斷
tick3 = "``" + "`"

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
        --warning-bg: #FFFBEB;
        --warning-border: #F59E0B;
        --warning-text: #B45309;
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
            --warning-bg: #451A03;
            --warning-border: #F59E0B;
            --warning-text: #FCD34D;
        }
    }
    
    .stApp { font-family: 'Inter', -apple-system, BlinkMacSystemFont, "Segoe UI", Helvetica, Arial, sans-serif; }
    .roche-title { color: var(--primary-color); font-weight: 800; font-size: 2.2rem; margin-bottom: 0px; letter-spacing: -0.5px;}
    .title-divider { height: 3px; width: 40px; background-color: var(--primary-color); border-radius: 2px; margin-top: 8px; margin-bottom: 12px; }
    .roche-subtitle { color: var(--text-muted); font-size: 1rem; font-weight: 500; margin-bottom: 25px; }
    
    .base-card { background-color: var(--bg-color); border: 1px solid var(--border-color); border-radius: 8px; padding: 20px; margin-bottom: 20px; box-shadow: 0 1px 3px rgba(0,0,0,0.05); }
    .alert-card { border-left: 4px solid var(--alert-border); background-color: var(--alert-bg); }
    .alert-title { color: var(--alert-text); font-weight: 700; font-size: 1.1rem; margin-bottom: 8px; display: flex; align-items: center;}
    .info-card { border-left: 4px solid var(--info-border); background-color: var(--info-bg); }
    .info-title { color: var(--info-text); font-weight: 700; font-size: 1rem; margin-bottom: 8px; }
    .info-body { color: var(--text-main); font-size: 0.95rem; line-height: 1.6; }
    .warning-card { border-left: 4px solid var(--warning-border); background-color: var(--warning-bg); }
    .warning-title { color: var(--warning-text); font-weight: 700; font-size: 1rem; margin-bottom: 8px; }
    
    /* 案件分類標籤 (Badge) CSS */
    .badge-complaint { background-color: #FEE2E2; color: #B91C1C; padding: 4px 12px; border-radius: 20px; font-size: 0.85rem; font-weight: 700; display: inline-block; margin-bottom: 12px; border: 1px solid #FCA5A5;}
    .badge-inquiry { background-color: #DCFCE7; color: #047857; padding: 4px 12px; border-radius: 20px; font-size: 0.85rem; font-weight: 700; display: inline-block; margin-bottom: 12px; border: 1px solid #86EFAC;}
    .badge-logistics { background-color: #FFEDD5; color: #B45309; padding: 4px 12px; border-radius: 20px; font-size: 0.85rem; font-weight: 700; display: inline-block; margin-bottom: 12px; border: 1px solid #FDBA74;}
    
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
    st.session_state.messages = [{"role": "assistant", "content": "您好！請輸入現場狀況，推薦使用下方麥克風 🎙️ 語音輸入。\n\n💡 系統將會協助您檢查**合規必填資訊**，並自動評估法規風險。"}]
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
    * 🛡️ **合規檢查：** 系統會自動檢查您是否遺漏了**產品批號 (Lot)、儀器序號 (SN) 或軟體版本**，並在需要時主動提醒您補齊。補齊後會自動寫入日誌中。
    * 🚨 **高風險攔截：** 若提及資安威脅、仿冒品或資料隱私請求，系統會立即警告並建議通報窗口。
    * ⚡ **鍵盤極速操作 (快捷鍵)：**
        * `Ctrl + Shift + C`：一鍵複製產出的日誌。
        * `Ctrl + Shift + E`：一鍵開啟 Gmail 準備寄送備份 (需在側邊欄設定信箱)。
        * `Ctrl + Shift + S`：快速下載 TXT 檔。
    """)

# --- 5. 側邊欄 ---
with st.sidebar:
    st.markdown("<h3 style='color: var(--primary-color); font-weight:700;'>⚙️ Settings</h3>", unsafe_allow_html=True)
    try: api_key = st.secrets["GEMINI_API_KEY"]
    except KeyError: st.error("⚠️ 尚未設定雲端 API Key！"); st.stop()
    
    st.markdown("📩 **個人備份設定 (Gmail 專屬)**")
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

# --- 6. 系統提示詞 (🔥 核心修復：強制寫入追蹤資訊) ---
# [cite: 166]
SYSTEM_PROMPT = """
你是一位專業的 IVD 設備支援主管，精通 Roche QARA 規範 (MQMS-PM-GSP-04 V11)。
請嚴格評估使用者的輸入內容，確保合規，並輸出標準格式。

【案件分類邏輯】
1. Inquiry (一般詢問)：單純要資訊、設定問題，無產品故障指控。
   - 特別注意：若客戶索取紙本 eIFU，需在 7 天內免費提供。
2. Logistics Claim (物流客訴)：運輸造成的損壞 (外箱破損、寄錯地址)。
3. Complaint (客訴)：硬體故障、軟體Bug、包裝缺件、試劑問題等所有產品缺陷。

【強制合規與高風險攔截】
- 若涉及資安/駭客/中毒，觸發 [CYBERSECURITY]
- 若涉及仿冒/標籤異常/非授權供應商，觸發 [COUNTERFEIT]
- 若客戶要求刪除個資/資料，觸發 [DSR_PRIVACY] (需通報 DPO)
- 若涉及重大傳染病(如伊波拉)且設備故障，觸發 [pPHT_ALERT] (需2天內通報)
- 自動隱藏/打碼所有出現的病患真實姓名與身分證字號。

【PRI / PSI 判斷邏輯】
- 單純硬體故障、校正(Calibration)/QC 失敗：不屬於 ER，無需 PRI。
- 真實 ER (病患數值異常)：確認偏差是否達標。

【處理流程 - 重要！】
步驟 1：檢查資訊是否齊全。一份合格的日誌「必須」包含以下至少一項追蹤資訊：
  - 儀器序號 (SN)
  - 產品批號 (Lot)
  - 軟體版本 (Software version)
  如果「目前所有的對話紀錄中」完全沒有提及上述任何一項，請「不要」產出 [LOG]！
  你必須先使用 [ASK_USER] 標籤來詢問使用者：「請問本次案件的儀器序號(SN)或產品批號(Lot)為何？請補齊後為您產出完整日誌。」

步驟 2：當資訊齊全（包含使用者後續補充的資訊）時，才產出完整的標籤格式。

【強制輸出格式】
請嚴格使用以下標籤輸出，不要加上多餘的問候語。

[CLASSIFICATION] (填入 Inquiry, Logistics Claim, 或 Complaint)
[HOSP_NAME] 醫院名稱 (若無請填 NA)
[COMPLIANCE_WARNINGS] (若觸發高風險攔截，請列具體警告；若無填 NA)
[REASONING] 你的 PRI/PSI 評估理由 (若不需評估填 NA)
[PRI_ALERT] YES 或 NO
[ASK_USER] (若遺漏 SN/Lot/SW，請填入你要詢問使用者的話；若資訊齊全，請填 NA)

(只有當 [ASK_USER] 為 NA 時，才輸出以下 [LOG] 區塊)
[LOG]
如果 [CLASSIFICATION] 是 Complaint 或 Logistics Claim，請務必使用以下 5 大點格式：
* 01_客戶問題描述與報錯代碼：[內容。必須在開頭第一句，明確寫出所有收集到的追蹤資訊 (例如：機台序號: XXX, 試劑批號: YYY)。絕對不能遺漏使用者補充的批號或序號]
* 02_客戶已經採取哪些行動嘗試解決問題：[內容或 NA]
* 03_處理過程與觀察測試結果：[內容]
* 04_本次服務是否結案：[不可僅回答是/否。必須依據處理過程，明確寫出「可結案的客觀原因」(例如：QC Pass、校正成功、功能恢復正常等)，並說明客戶同意結案]
* 05_客戶需要配合與改善的事項：[內容或 NA]

如果 [CLASSIFICATION] 是 Inquiry，請不要使用 5 大點格式。請直接用流暢的段落文字總結使用者的處理過程。段落的開頭必須明確列出收集到的追蹤資訊(SN/Lot)。段落的結尾「務必」加上結案說明，格式如下：「因 [填入客觀結案原因，例如：說明完畢、測試正常等]，本次的詢問確認無產品表現/儀器設計或其他品質問題疑慮，客戶同意結案。」
"""

# --- 7. 訊息渲染引擎 ---
def render_assistant_message(msg_content):
    hosp_match = re.search(r"\[HOSP_NAME\]\s*(.+)", msg_content)
    hospital_name = hosp_match.group(1).strip() if hosp_match and hosp_match.group(1).strip() != "NA" else ""
    
    class_match = re.search(r"\[CLASSIFICATION\]\s*(.+)", msg_content)
    classification = class_match.group(1).strip() if class_match and class_match.group(1).strip() != "NA" else ""
    
    warnings_match = re.search(r"\[COMPLIANCE_WARNINGS\]\s*(.+)", msg_content)
    compliance_warnings = warnings_match.group(1).strip() if warnings_match and warnings_match.group(1).strip() != "NA" else ""
    
    reasoning_match = re.search(r"\[REASONING\]\s*(.+)", msg_content)
    reasoning = reasoning_match.group(1).strip() if reasoning_match and reasoning_match.group(1).strip() != "NA" else ""
    
    ask_match = re.search(r"\[ASK_USER\]\s*(.+)", msg_content)
    ask_user = ask_match.group(1).strip() if ask_match and ask_match.group(1).strip() != "NA" else ""
    
    is_alert = "[PRI_ALERT] YES" in msg_content
    
    log_match = re.search(r"\[LOG\]\s*(.+)", msg_content, re.DOTALL)
    log_content = log_match.group(1).strip() if log_match else ""

    file_name = f"REXIS_Log_{hospital_name}.txt" if hospital_name else "REXIS_Log.txt"
    subject_title = f"REXIS 服務日誌備份_{hospital_name}" if hospital_name else "REXIS 服務日誌備份"

    if ask_user:
        st.markdown(f"""
        <div class="base-card warning-card">
            <div class="warning-title">⚠️ 系統合規提醒</div>
            <div class="info-body">{ask_user}</div>
        </div>
        """, unsafe_allow_html=True)
        return 

    if compliance_warnings:
        st.markdown(f"""
        <div class="base-card alert-card">
            <div class="alert-title">🚨 高風險事件通報提醒</div>
            <div class="info-body"><b>系統偵測到特殊事件：</b><br>{compliance_warnings}</div>
        </div>
        """, unsafe_allow_html=True)

    if is_alert:
        st.markdown("""
        <div class="base-card alert-card">
            <div class="alert-title">🚨 法規升級警告 (PRI/PSI)</div>
            <div class="info-body">依據法規標準，此案涉及檢驗異常 (ER) 且達標，請立即<b>重新開立專屬的 PRI/PSI 案件</b>！</div>
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
        badge_html = ""
        if "Complaint" in classification:
            badge_html = '<div class="badge-complaint">🔴 客訴 (Complaint)</div>'
        elif "Inquiry" in classification:
            badge_html = '<div class="badge-inquiry">🟢 一般詢問 (Inquiry)</div>'
        elif "Logistics" in classification:
            badge_html = '<div class="badge-logistics">🟠 物流客訴 (Logistics Claim)</div>'

        encoded_log = urllib.parse.quote(log_content)
        dl_href = f"data:text/plain;charset=utf-8,{encoded_log}"
        
        email_body_text = "這是本次的日誌備份：\r\n\r\n" + log_content.replace('\r\n', '\n').replace('\n', '\r\n')
        encoded_subject = urllib.parse.quote(subject_title)
        encoded_body = urllib.parse.quote(email_body_text)
        gmail_href = f"https://mail.google.com/mail/?view=cm&fs=1&to={default_email}&su={encoded_subject}&body={encoded_body}"
        
        st.markdown(f"""
        <div class="base-card">
            {badge_html}
            <div style="white-space: pre-wrap; font-family: inherit; font-size: 0.95rem; color: var(--text-main); margin-bottom: 0;">{log_content}</div>
            <div class="action-bar">
                <button class="action-btn btn-copy" data-clipboard="{encoded_log}">📋 複製日誌</button>
                <a href="{dl_href}" download="{file_name}" class="action-btn btn-download">💾 下載 TXT</a>
                <a href="{gmail_href}" target="_blank" class="action-btn btn-email">📧 用 Gmail 寄送</a>
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
            {"role": "model", "parts": ["OK，我已完全了解。我會嚴格使用標籤格式輸出，並在必要時主動詢問缺少資訊。"]}
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

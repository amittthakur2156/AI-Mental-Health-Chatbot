const USER_ID_KEY = "calmmind_user_id";
let currentSessionId = null;
let currentSessionTitle = "New Support Session";
let sessionsCache = [];
let voiceReplyEnabled = true;
let recognition = null;
let isRecording = false;
let moodChart = null;
let emotionChart = null;
let activityChart = null;
let riskChart = null;
let lastAssistantReply = "";
let localVideoStream = null;

const LANGUAGE_CONFIG = {
  auto: { label: "Auto Detect", speech: "hi-IN", direction: "ltr" },
  hinglish: { label: "Hinglish", speech: "hi-IN", direction: "ltr" },
  hindi: { label: "Hindi", speech: "hi-IN", direction: "ltr" },
  english: { label: "English", speech: "en-IN", direction: "ltr" },
  punjabi: { label: "Punjabi", speech: "pa-IN", direction: "ltr" },
  marathi: { label: "Marathi", speech: "mr-IN", direction: "ltr" },
  telugu: { label: "Telugu", speech: "te-IN", direction: "ltr" },
  urdu: { label: "Urdu", speech: "ur-PK", direction: "rtl" },
  french: { label: "French", speech: "fr-FR", direction: "ltr" },
  chinese: { label: "Chinese", speech: "zh-CN", direction: "ltr" },
};

function getPreferredLanguage() {
  return localStorage.getItem("calmmind_language") || "hinglish";
}

function setPreferredLanguage(value) {
  const lang = LANGUAGE_CONFIG[value] ? value : "hinglish";
  localStorage.setItem("calmmind_language", lang);
  document.documentElement.setAttribute("dir", LANGUAGE_CONFIG[lang].direction || "ltr");
  return lang;
}

function getSpeechLang() {
  const lang = getPreferredLanguage();
  return (LANGUAGE_CONFIG[lang] || LANGUAGE_CONFIG.hinglish).speech;
}

function getUserId() {
  let id = localStorage.getItem(USER_ID_KEY);
  if (!id) {
    id = "demo_" + Math.random().toString(36).slice(2, 10);
    localStorage.setItem(USER_ID_KEY, id);
  }
  return id;
}

async function api(path, options = {}) {
  const headers = Object.assign({ "Content-Type": "application/json", "X-User-Id": getUserId() }, options.headers || {});
  const res = await fetch(path, { ...options, headers });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) throw new Error(data.error || "Request failed");
  return data;
}

function toast(message) {
  const el = document.getElementById("toast");
  if (!el) return;
  el.textContent = message;
  el.classList.remove("hidden");
  setTimeout(() => el.classList.add("hidden"), 3000);
}

function initTheme() {
  const saved = localStorage.getItem("calmmind_theme") || "light";
  document.documentElement.setAttribute("data-theme", saved);
  document.getElementById("themeToggle")?.addEventListener("click", () => {
    const next = document.documentElement.getAttribute("data-theme") === "dark" ? "light" : "dark";
    document.documentElement.setAttribute("data-theme", next);
    localStorage.setItem("calmmind_theme", next);
  });
}

function formatTime(value) {
  if (!value) return "";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return "";
  return date.toLocaleString([], { month: "short", day: "numeric", hour: "2-digit", minute: "2-digit" });
}

function shortText(text, max = 80) {
  const clean = String(text || "").replace(/\s+/g, " ").trim();
  return clean.length > max ? clean.slice(0, max - 1) + "…" : clean;
}

function clearChatWelcome() {
  const box = document.getElementById("chatMessages");
  if (!box) return;
  if (box.querySelector(".welcome-message") && box.children.length === 1) box.innerHTML = "";
}

function addMessage(role, content, meta = {}) {
  const box = document.getElementById("chatMessages");
  if (!box) return null;
  const div = document.createElement("div");
  div.className = `message ${role}`;
  if (meta.messageId) div.dataset.messageId = meta.messageId;

  const p = document.createElement("p");
  p.textContent = content;
  div.appendChild(p);

  const bits = [];
  if (meta.input_type) bits.push(meta.input_type);
  if (meta.emotion) bits.push(`emotion: ${meta.emotion}`);
  if (meta.intent) bits.push(`intent: ${meta.intent}`);
  if (meta.mood_score !== undefined && meta.mood_score !== null) bits.push(`mood: ${meta.mood_score}/10`);
  if (meta.created_at) bits.push(formatTime(meta.created_at));
  if (bits.length) {
    const small = document.createElement("div");
    small.className = "message-meta";
    small.textContent = bits.join(" · ");
    div.appendChild(small);
  }

  box.appendChild(div);
  box.scrollTop = box.scrollHeight;
  return div;
}

function showTyping() {
  const box = document.getElementById("chatMessages");
  if (!box) return null;
  const div = document.createElement("div");
  div.className = "message bot typing-message";
  div.innerHTML = `<div class="typing-dots"><span></span><span></span><span></span></div><div class="message-meta">CalmMind is thinking...</div>`;
  box.appendChild(div);
  box.scrollTop = box.scrollHeight;
  return div;
}

function updateBadges(result = {}) {
  const analysis = result.analysis || {};
  const emotion = result.emotion || analysis.emotion || "neutral";
  const intent = result.intent || analysis.intent || "support";
  const riskLevel = result.risk_level || analysis.risk_level || "low";
  const riskScore = result.risk_score ?? analysis.risk_score ?? 5;
  const mood = result.mood_score ?? analysis.mood_score ?? 5;
  const inputType = result.input_type || "text";
  const language = result.language || analysis.language || "hinglish";
  const triggers = result.triggers || analysis.triggers || [];
  const tool = result.recommended_tool || analysis.recommended_tool || "supportive_chat";
  const knowledge = result.knowledge_used || analysis.knowledge_used || [];
  const memory = result.memory_summary || analysis.memory_summary || "Memory will update after a few messages.";

  const emotionEl = document.getElementById("emotionBadge");
  const intentEl = document.getElementById("intentBadge");
  const moodEl = document.getElementById("moodBadge");
  const riskEl = document.getElementById("riskBadge");
  if (emotionEl) emotionEl.textContent = `emotion: ${emotion}`;
  if (intentEl) intentEl.textContent = `intent: ${intent}`;
  if (moodEl) moodEl.textContent = `mood: ${mood}/10`;
  if (riskEl) {
    riskEl.textContent = `risk: ${riskLevel} (${riskScore}/100)`;
    riskEl.className = `badge ${["medium", "high", "emergency"].includes(riskLevel) ? "risk" : "safe"}`;
  }

  const sideEmotion = document.getElementById("sideEmotion");
  const sideIntent = document.getElementById("sideIntent");
  const sideMood = document.getElementById("sideMood");
  const sideRiskScore = document.getElementById("sideRiskScore");
  const sideLanguage = document.getElementById("sideLanguage");
  const sideTriggers = document.getElementById("sideTriggers");
  const sideTool = document.getElementById("sideTool");
  const sideInputType = document.getElementById("sideInputType");
  const memorySummary = document.getElementById("memorySummary");
  const knowledgeUsed = document.getElementById("knowledgeUsed");
  if (sideEmotion) sideEmotion.textContent = emotion;
  if (sideIntent) sideIntent.textContent = intent;
  if (sideMood) sideMood.textContent = `${mood}/10`;
  if (sideRiskScore) sideRiskScore.textContent = `${riskScore}/100`;
  if (sideLanguage) sideLanguage.textContent = language;
  if (sideTriggers) sideTriggers.textContent = Array.isArray(triggers) && triggers.length ? triggers.join(", ") : "none";
  if (sideTool) sideTool.textContent = tool;
  if (sideInputType) sideInputType.textContent = inputType;
  if (memorySummary) memorySummary.textContent = memory || "Memory will update after a few messages.";
  if (knowledgeUsed) knowledgeUsed.textContent = Array.isArray(knowledge) && knowledge.length ? knowledge.join(" • ") : "No knowledge source used.";

  if (["high", "emergency"].includes(riskLevel)) {
    const steps = result.safety_card?.immediate_steps || analysis.safety_immediate_steps || [];
    if (steps.length) console.warn("Safety steps:", steps);
  }
}

function updateCurrentSessionHeader(session = {}) {
  currentSessionTitle = session.title || currentSessionTitle || "New Support Session";
  const titleEl = document.getElementById("currentSessionTitle");
  const metaEl = document.getElementById("currentSessionMeta");
  if (titleEl) titleEl.textContent = currentSessionTitle;
  if (metaEl) {
    const created = session.started_at ? `Started ${formatTime(session.started_at)}` : "Professional support session";
    const updated = session.updated_at ? `Updated ${formatTime(session.updated_at)}` : "";
    metaEl.textContent = [created, updated].filter(Boolean).join(" · ");
  }
}

function renderSessions(sessions = sessionsCache) {
  const list = document.getElementById("sessionList");
  const count = document.getElementById("sessionCount");
  if (!list) return;
  const query = (document.getElementById("sessionSearch")?.value || "").toLowerCase().trim();
  const filtered = sessions.filter((s) => {
    const text = `${s.title || ""} ${s.last_preview || ""}`.toLowerCase();
    return !query || text.includes(query);
  });
  if (count) count.textContent = `${sessions.length} session${sessions.length === 1 ? "" : "s"}`;
  list.innerHTML = "";
  if (!filtered.length) {
    const empty = document.createElement("div");
    empty.className = "empty-state";
    empty.textContent = sessions.length ? "No matching sessions." : "No sessions yet. Start a new chat.";
    list.appendChild(empty);
    return;
  }
  filtered.forEach((s) => {
    const item = document.createElement("button");
    item.type = "button";
    item.className = `session-item pro-session-item ${Number(currentSessionId) === Number(s.id) ? "active" : ""}`;
    const riskClass = ["medium", "high", "emergency"].includes(s.last_risk_level) ? "risk" : "safe";
    item.innerHTML = `
      <span class="session-title">${escapeHtml(s.title || "Support Session")}</span>
      <span class="session-preview">${escapeHtml(s.last_preview || "No messages yet")}</span>
      <span class="session-footer"><span>${Number(s.message_count || 0)} msg</span><span>${formatTime(s.updated_at)}</span></span>
      <span class="session-tags"><span class="mini-badge">${escapeHtml(s.last_emotion || "neutral")}</span><span class="mini-badge ${riskClass}">${escapeHtml(s.last_risk_level || "low")}</span></span>
    `;
    item.onclick = () => loadSessionMessages(s.id);
    list.appendChild(item);
  });
}

function escapeHtml(str) {
  return String(str || "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}

async function loadSessions() {
  const list = document.getElementById("sessionList");
  if (!list) return;
  try {
    const data = await api("/api/history");
    sessionsCache = data.sessions || [];
    renderSessions(sessionsCache);
  } catch (err) {
    list.innerHTML = `<div class="empty-state">Could not load sessions.</div>`;
  }
}

async function loadMemoryProfile() {
  const memorySummary = document.getElementById("memorySummary");
  if (!memorySummary) return;
  try {
    const data = await api("/api/memory/profile");
    memorySummary.textContent = data.summary || "Memory will update after a few messages.";
  } catch (err) {
    memorySummary.textContent = "Memory unavailable in this session.";
  }
}

async function resetMemoryProfile() {
  if (!confirm("Reset AI memory for this demo user? Chat history will remain.")) return;
  try {
    await api("/api/memory/profile", { method: "DELETE" });
    await loadMemoryProfile();
    toast("AI memory reset.");
  } catch (err) {
    toast("Memory reset failed: " + err.message);
  }
}

async function createNewSession() {
  try {
    const data = await api("/api/session/new", { method: "POST", body: JSON.stringify({ title: "New Support Session" }) });
    currentSessionId = data.session_id;
    updateCurrentSessionHeader(data.session || { title: "New Support Session" });
    const box = document.getElementById("chatMessages");
    if (box) {
      box.innerHTML = "";
      addMessage("bot", "New session started. Tum text ya mic se baat kar sakte ho — aaj tum kaisa feel kar rahe ho?", { input_type: "system" });
    }
    sessionsCache = data.sessions || [];
    renderSessions(sessionsCache);
    toast("New session started.");
  } catch (err) {
    toast("Could not create session: " + err.message);
  }
}

async function loadSessionMessages(id) {
  const box = document.getElementById("chatMessages");
  if (!box) return;
  try {
    const data = await api(`/api/session/${id}`);
    currentSessionId = id;
    updateCurrentSessionHeader(data.session || {});
    box.innerHTML = "";
    (data.messages || []).forEach((m) => {
      addMessage(m.role === "assistant" ? "bot" : "user", m.content, m);
    });
    if (!(data.messages || []).length) {
      addMessage("bot", "Ye session empty hai. Apni feeling ya question share karo.", { input_type: "system" });
    }
    renderSessions(sessionsCache);
  } catch (err) {
    toast("Could not open session: " + err.message);
  }
}

async function renameCurrentSession() {
  if (!currentSessionId) return toast("Pehle ek session select/start karo.");
  const title = prompt("New session title:", currentSessionTitle || "Support Session");
  if (!title || !title.trim()) return;
  try {
    const data = await api(`/api/session/${currentSessionId}`, { method: "PATCH", body: JSON.stringify({ title: title.trim() }) });
    sessionsCache = data.sessions || [];
    const current = sessionsCache.find((s) => Number(s.id) === Number(currentSessionId));
    updateCurrentSessionHeader(current || { title: title.trim() });
    renderSessions(sessionsCache);
    toast("Session renamed.");
  } catch (err) {
    toast("Rename failed: " + err.message);
  }
}

async function deleteCurrentSession() {
  if (!currentSessionId) return toast("No current session selected.");
  if (!confirm("Delete this chat session?")) return;
  try {
    const data = await api(`/api/session/${currentSessionId}`, { method: "DELETE" });
    currentSessionId = null;
    currentSessionTitle = "New Support Session";
    updateCurrentSessionHeader({ title: currentSessionTitle });
    const box = document.getElementById("chatMessages");
    if (box) {
      box.innerHTML = "";
      addMessage("bot", "Session deleted. Start a new conversation whenever you are ready.", { input_type: "system" });
    }
    sessionsCache = data.sessions || [];
    renderSessions(sessionsCache);
    toast("Session deleted.");
  } catch (err) {
    toast("Delete failed: " + err.message);
  }
}

async function clearAllHistory() {
  if (!confirm("Clear all chat sessions for this demo user?")) return;
  try {
    const data = await api("/api/history", { method: "DELETE" });
    currentSessionId = null;
    sessionsCache = data.sessions || [];
    renderSessions(sessionsCache);
    const box = document.getElementById("chatMessages");
    if (box) {
      box.innerHTML = "";
      addMessage("bot", "All local chat history cleared. You can start fresh now.", { input_type: "system" });
    }
    toast("All history cleared.");
  } catch (err) {
    toast("Could not clear history: " + err.message);
  }
}

async function sendChatMessage(text, inputType = "text") {
  const input = document.getElementById("messageInput");
  const message = (text || input?.value || "").trim();
  if (!message) return;
  if (input) input.value = "";
  clearChatWelcome();
  addMessage("user", message, { input_type: inputType, created_at: new Date().toISOString() });
  const typing = showTyping();
  try {
    const data = await api("/api/chat", {
      method: "POST",
      body: JSON.stringify({
        message,
        session_id: currentSessionId,
        input_type: inputType,
        preferred_language: getPreferredLanguage(),
      }),
    });
    currentSessionId = data.session_id;
    typing?.remove();
    lastAssistantReply = data.reply || "";
    addMessage("bot", data.reply, data);
    updateBadges(data);
    if (data.sessions) {
      sessionsCache = data.sessions;
      const current = sessionsCache.find((s) => Number(s.id) === Number(currentSessionId));
      updateCurrentSessionHeader(current || { title: currentSessionTitle });
      renderSessions(sessionsCache);
    } else {
      loadSessions();
    }
    if (voiceReplyEnabled && inputType === "voice") speakText(data.reply);
  } catch (err) {
    typing?.remove();
    addMessage("bot", "Sorry, kuch technical issue aa gaya: " + err.message, { input_type: "system" });
  }
}

function speakText(text) {
  if (!("speechSynthesis" in window)) return toast("Speech synthesis not supported in this browser.");
  const exactReply = String(text || "");
  if (!exactReply.trim()) return;
  window.speechSynthesis.cancel();
  const utter = new SpeechSynthesisUtterance(exactReply);
  utter.lang = getSpeechLang();
  utter.rate = 0.95;
  utter.pitch = 1;
  utter.onstart = () => setVoiceStatus("Speaking exact AI reply...", "speaking");
  utter.onend = () => setVoiceStatus("Mic idle", "idle");
  utter.onerror = () => setVoiceStatus("Speech error", "error");
  window.speechSynthesis.speak(utter);
}


function setVoiceStatus(text, state = "idle") {
  const status = document.getElementById("voiceStatus");
  const micBtn = document.getElementById("micBtn");
  if (status) {
    status.innerHTML = `<span class="status-dot ${state}"></span> ${escapeHtml(text)}`;
  }
  if (micBtn) micBtn.classList.toggle("recording", state === "listening");
}

function initLanguageControls() {
  const selected = setPreferredLanguage(getPreferredLanguage());
  [document.getElementById("languageSelect"), document.getElementById("connectLanguageSelect")].forEach((select) => {
    if (!select) return;
    select.value = selected;
    select.addEventListener("change", (e) => {
      const lang = setPreferredLanguage(e.target.value);
      document.querySelectorAll("#languageSelect,#connectLanguageSelect").forEach(el => { if (el) el.value = lang; });
      const hint = document.getElementById("languageHint") || document.getElementById("connectLangHint");
      if (hint) hint.textContent = `Selected: ${LANGUAGE_CONFIG[lang].label}. Mic and voice reply language updated.`;
      if (recognition) recognition.lang = getSpeechLang();
      toast(`Language set to ${LANGUAGE_CONFIG[lang].label}`);
    });
  });
}

function initVoice() {
  const micBtn = document.getElementById("micBtn");
  if (!micBtn) return;
  const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
  if (!SpeechRecognition) {
    setVoiceStatus("Mic STT not supported. Use Chrome/Edge or type message.", "error");
    micBtn.disabled = true;
    return;
  }
  recognition = new SpeechRecognition();
  recognition.lang = getSpeechLang();
  recognition.interimResults = false;
  recognition.continuous = false;

  recognition.onstart = () => {
    isRecording = true;
    setVoiceStatus("Listening...", "listening");
  };
  recognition.onend = () => {
    isRecording = false;
    if (!window.speechSynthesis?.speaking) setVoiceStatus("Mic idle", "idle");
  };
  recognition.onerror = (e) => {
    toast("Mic error: " + e.error);
    setVoiceStatus("Mic error", "error");
  };
  recognition.onresult = (event) => {
    const transcript = event.results?.[0]?.[0]?.transcript || "";
    const input = document.getElementById("messageInput");
    if (input) input.value = transcript;
    setVoiceStatus("Thinking...", "thinking");
    sendChatMessage(transcript, "voice");
  };
  micBtn.addEventListener("click", () => {
    if (isRecording) {
      recognition.stop();
    } else {
      recognition.lang = getSpeechLang();
      recognition.start();
    }
  });
  document.getElementById("speakToggle")?.addEventListener("click", (e) => {
    voiceReplyEnabled = !voiceReplyEnabled;
    e.currentTarget.textContent = `Voice Reply: ${voiceReplyEnabled ? "On" : "Off"}`;
    if (!voiceReplyEnabled) window.speechSynthesis?.cancel();
  });
  document.getElementById("stopSpeakBtn")?.addEventListener("click", () => {
    window.speechSynthesis?.cancel();
    setVoiceStatus("Speech stopped", "idle");
  });
  document.getElementById("repeatLastReplyBtn")?.addEventListener("click", () => {
    if (lastAssistantReply) speakText(lastAssistantReply); else toast("No AI reply yet.");
  });
}


function initChat() {
  if (!document.getElementById("chatMessages")) return;
  document.getElementById("sendBtn")?.addEventListener("click", () => sendChatMessage());
  document.getElementById("messageInput")?.addEventListener("keydown", (e) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      sendChatMessage();
    }
  });
  document.getElementById("newSessionBtn")?.addEventListener("click", createNewSession);
  document.getElementById("renameSessionBtn")?.addEventListener("click", renameCurrentSession);
  document.getElementById("deleteSessionBtn")?.addEventListener("click", deleteCurrentSession);
  document.getElementById("clearHistoryBtn")?.addEventListener("click", clearAllHistory);
  document.getElementById("sessionSearch")?.addEventListener("input", () => renderSessions(sessionsCache));
  document.getElementById("resetMemoryBtn")?.addEventListener("click", resetMemoryProfile);
  initLanguageControls();
  document.querySelectorAll(".tool-btn,.quick-chip").forEach(btn => btn.addEventListener("click", () => sendChatMessage(btn.dataset.prompt)));
  initVoice();
  loadSessions();
  loadMemoryProfile();
}

function destroyChart(chart) {
  if (chart && typeof chart.destroy === "function") chart.destroy();
}

function chartLabels(rows, dateKey = "date") {
  return (rows || []).map((row) => row[dateKey] || row.day || "-");
}

function chartNumbers(rows, key) {
  return (rows || []).map((row) => Number(row[key] || 0));
}

function renderEmotionList(emotions = []) {
  const list = document.getElementById("emotionList");
  if (!list) return;
  list.innerHTML = "";
  if (!emotions.length) {
    list.innerHTML = '<div class="empty-state">No emotion data yet. Start chatting or journaling.</div>';
    return;
  }
  emotions.forEach((e) => {
    const div = document.createElement("div");
    div.className = "list-item compact-item";
    div.innerHTML = '<strong>' + escapeHtml(e.emotion || "neutral") + '</strong><span>' + Number(e.count || 0) + ' entries</span>';
    list.appendChild(div);
  });
}

function renderHeatmap(rows = []) {
  const box = document.getElementById("moodHeatmap");
  if (!box) return;
  box.innerHTML = "";
  if (!rows.length) {
    box.innerHTML = '<div class="empty-state">No mood calendar data yet. Try a few chat or journal entries.</div>';
    return;
  }
  rows.slice(0, 90).reverse().forEach((row) => {
    const cell = document.createElement("div");
    const level = row.level || "empty";
    cell.className = 'heat-cell ' + level;
    cell.title = (row.date || '-') + ': mood ' + (row.avg_score || '-') + '/10 · ' + (row.count || 0) + ' log(s)';
    cell.innerHTML = '<span>' + String(row.date || '').slice(5) + '</span><strong>' + (row.avg_score || '-') + '</strong>';
    box.appendChild(cell);
  });
}

function renderWeeklyReport(report = {}) {
  const box = document.getElementById("weeklyReport");
  if (!box) return;
  const insights = report.insights || [];
  const recommendations = report.recommendations || [];
  box.innerHTML =
    '<div class="report-summary-grid">' +
      '<div><strong>' + (report.avg_mood ?? '-') + '</strong><span>Avg mood</span></div>' +
      '<div><strong>' + escapeHtml(report.top_emotion || '-') + '</strong><span>Top emotion</span></div>' +
      '<div><strong>' + escapeHtml(report.trend_direction || '-') + '</strong><span>Trend</span></div>' +
      '<div><strong>' + (report.activity_total ?? 0) + '</strong><span>Activities</span></div>' +
    '</div>' +
    '<h4>Insights</h4>' +
    '<ul>' + (insights.map(i => '<li>' + escapeHtml(i) + '</li>').join('') || '<li>Not enough data yet.</li>') + '</ul>' +
    '<h4>Recommended next steps</h4>' +
    '<ul>' + (recommendations.map(r => '<li>' + escapeHtml(r) + '</li>').join('') || '<li>Start with one mood check-in today.</li>') + '</ul>';
}

function copyWeeklyReport() {
  const box = document.getElementById("weeklyReport");
  if (!box) return;
  const text = box.innerText.trim();
  if (navigator.clipboard) {
    navigator.clipboard.writeText(text).then(() => toast("Weekly report copied."));
  } else {
    toast("Copy is not supported in this browser.");
  }
}

async function loadAdvancedDashboard() {
  if (!document.getElementById("moodChart")) return;
  const days = Number(document.getElementById("dashboardRange")?.value || 30);
  const exportCsv = document.getElementById("exportCsvLink");
  const exportJson = document.getElementById("exportJsonLink");
  if (exportCsv) exportCsv.href = "/api/mood/export/csv?user_id=" + encodeURIComponent(getUserId());
  if (exportJson) exportJson.href = "/api/mood/export/json?user_id=" + encodeURIComponent(getUserId());
  const [summary, trends, emotions, activity, risks, heatmap, weekly] = await Promise.all([
    api('/api/mood/summary?days=' + days),
    api('/api/mood/trends?days=' + days),
    api('/api/mood/emotions?days=' + days),
    api('/api/mood/activity?days=' + days),
    api('/api/mood/risk-trends?days=' + days),
    api('/api/mood/heatmap?days=' + Math.max(days, 90)),
    api('/api/mood/weekly-report?days=' + Math.min(days, 30)),
  ]);

  const cards = summary.cards || {};
  document.getElementById("avgMood").textContent = cards.avg_mood ?? "-";
  document.getElementById("periodMood").textContent = cards.period_avg_mood ?? "-";
  document.getElementById("moodLabel").textContent = cards.mood_label || "not enough data";
  document.getElementById("periodLogs").textContent = (summary.period_stats?.total_logs ?? 0) + ' logs';
  document.getElementById("activeStreak").textContent = cards.active_streak ?? 0;
  document.getElementById("topEmotion").textContent = cards.top_emotion || "-";
  document.getElementById("topIntent").textContent = 'intent: ' + (cards.top_intent || "-");
  document.getElementById("chatCount").textContent = cards.chat_messages ?? 0;
  document.getElementById("sessionCountCard").textContent = (cards.sessions ?? 0) + ' sessions';
  document.getElementById("voiceCount").textContent = cards.voice_sessions ?? 0;
  document.getElementById("riskEvents").textContent = cards.risk_events ?? 0;
  document.getElementById("highRiskEvents").textContent = (cards.high_risk_events ?? 0) + ' high risk';
  document.getElementById("journalCount").textContent = cards.journals ?? 0;
  document.getElementById("trendDirection").textContent = weekly.report?.trend_direction || "not enough data";

  const trendRows = trends.trends || [];
  const emotionRows = emotions.emotions || [];
  const activityRows = activity.activity || [];
  const riskRows = risks.risk_trends || [];

  destroyChart(moodChart);
  destroyChart(emotionChart);
  destroyChart(activityChart);
  destroyChart(riskChart);

  moodChart = new Chart(document.getElementById("moodChart"), {
    type: "line",
    data: {
      labels: chartLabels(trendRows),
      datasets: [
        { label: "Avg mood", data: chartNumbers(trendRows, "avg_score"), tension: .35 },
        { label: "Lowest", data: chartNumbers(trendRows, "min_score"), tension: .25 },
        { label: "Highest", data: chartNumbers(trendRows, "max_score"), tension: .25 },
      ]
    },
    options: { responsive: true, maintainAspectRatio: false, scales: { y: { min: 0, max: 10 } } }
  });

  emotionChart = new Chart(document.getElementById("emotionChart"), {
    type: "doughnut",
    data: {
      labels: emotionRows.map(e => e.emotion || "neutral"),
      datasets: [{ label: "Emotions", data: emotionRows.map(e => Number(e.count || 0)) }]
    },
    options: { responsive: true, maintainAspectRatio: false }
  });
  renderEmotionList(emotionRows);

  activityChart = new Chart(document.getElementById("activityChart"), {
    type: "bar",
    data: {
      labels: activityRows.map(r => r.day || "-"),
      datasets: [
        { label: "Chat", data: activityRows.map(r => Number(r.chat_count || 0)) },
        { label: "Voice", data: activityRows.map(r => Number(r.voice_count || 0)) },
        { label: "Journal", data: activityRows.map(r => Number(r.journal_count || 0)) },
      ]
    },
    options: { responsive: true, maintainAspectRatio: false, scales: { y: { beginAtZero: true } } }
  });

  const riskByDate = {};
  (riskRows || []).forEach((row) => {
    if (!riskByDate[row.date]) riskByDate[row.date] = { low: 0, medium: 0, high: 0, emergency: 0 };
    riskByDate[row.date][row.risk_level || "low"] = Number(row.count || 0);
  });
  const riskDates = Object.keys(riskByDate).sort();
  riskChart = new Chart(document.getElementById("riskChart"), {
    type: "bar",
    data: {
      labels: riskDates,
      datasets: [
        { label: "Low", data: riskDates.map(d => riskByDate[d].low || 0) },
        { label: "Medium", data: riskDates.map(d => riskByDate[d].medium || 0) },
        { label: "High", data: riskDates.map(d => riskByDate[d].high || 0) },
        { label: "Emergency", data: riskDates.map(d => riskByDate[d].emergency || 0) },
      ]
    },
    options: { responsive: true, maintainAspectRatio: false, scales: { y: { beginAtZero: true } } }
  });

  renderHeatmap(heatmap.heatmap || []);
  renderWeeklyReport(weekly.report || {});
}

async function initDashboard() {
  if (!document.getElementById("moodChart")) return;
  document.getElementById("dashboardRange")?.addEventListener("change", () => loadAdvancedDashboard().catch(err => toast("Dashboard load failed: " + err.message)));
  document.getElementById("refreshDashboardBtn")?.addEventListener("click", () => loadAdvancedDashboard().then(() => toast("Dashboard refreshed.")));
  document.getElementById("copyReportBtn")?.addEventListener("click", copyWeeklyReport);
  await loadAdvancedDashboard();
}

async function initJournal() {
  if (!document.getElementById("saveJournalBtn")) return;
  async function load() {
    const data = await api("/api/journal");
    const list = document.getElementById("journalList");
    list.innerHTML = "";
    (data.journals || []).forEach(j => {
      const item = document.createElement("div");
      item.className = "list-item";
      item.innerHTML = `<strong>${escapeHtml(j.title)}</strong><br><small>Mood: ${j.mood_score} · ${formatTime(j.created_at)}</small><p>${escapeHtml(j.ai_summary || "")}</p>`;
      list.appendChild(item);
    });
  }
  document.getElementById("saveJournalBtn").addEventListener("click", async () => {
    const payload = {
      title: document.getElementById("journalTitle").value,
      content: document.getElementById("journalContent").value,
      gratitude: document.getElementById("journalGratitude").value,
    };
    const data = await api("/api/journal", { method: "POST", body: JSON.stringify(payload) });
    const box = document.getElementById("journalSummary");
    box.textContent = `AI Summary: ${data.summary}`;
    box.classList.remove("hidden");
    document.getElementById("journalContent").value = "";
    document.getElementById("journalGratitude").value = "";
    load();
  });
  load();
}

async function initSafety() {
  if (!document.getElementById("saveSafetyBtn")) return;
  const fields = [
    "warningSigns", "copingActions", "trustedContacts", "safePlaces", "environmentSafety",
    "reasonsToLive", "professionalSupport", "crisisSteps", "emergencyNotes"
  ];
  const map = {
    warningSigns: "warning_signs",
    copingActions: "coping_actions",
    trustedContacts: "trusted_contacts",
    safePlaces: "safe_places",
    environmentSafety: "environment_safety",
    reasonsToLive: "reasons_to_live",
    professionalSupport: "professional_support",
    crisisSteps: "crisis_steps",
    emergencyNotes: "emergency_notes"
  };
  let template = {};

  function updateCompletion(score, validation = {}) {
    const completion = document.getElementById("planCompletion");
    const progress = document.getElementById("planProgress");
    const validationBox = document.getElementById("safetyValidation");
    const safeScore = Math.max(0, Math.min(100, Number(score || 0)));
    if (completion) completion.textContent = `${safeScore}%`;
    if (progress) progress.style.width = `${safeScore}%`;
    if (validationBox) {
      const missing = validation.missing_important_fields || [];
      validationBox.textContent = missing.length
        ? `Missing important fields: ${missing.join(", ")}`
        : "Plan looks actionable. Review it regularly and keep contacts updated.";
    }
  }

  function renderResources(resources = []) {
    const list = document.getElementById("resourceList");
    if (!list) return;
    list.innerHTML = "";
    resources.forEach((r) => {
      const item = document.createElement("div");
      item.className = "resource-item";
      item.innerHTML = `<strong>${escapeHtml(r.name)}</strong><span>${escapeHtml(r.contact)}</span><p>${escapeHtml(r.description)}</p>`;
      list.appendChild(item);
    });
  }

  try {
    const data = await api("/api/safety-plan");
    template = data.template || {};
    fields.forEach(id => {
      const el = document.getElementById(id);
      if (el) el.value = data.plan?.[map[id]] || "";
    });
    updateCompletion(data.completion_score, data.validation || {});
    renderResources(data.resources || []);
  } catch (err) {
    toast("Safety plan load failed: " + err.message);
  }

  document.getElementById("fillTemplateBtn")?.addEventListener("click", () => {
    fields.forEach(id => {
      const el = document.getElementById(id);
      const key = map[id];
      if (el && !el.value.trim()) el.value = template[key] || "";
    });
    toast("Example template filled. Edit it for the user.");
  });

  document.getElementById("runCrisisCheckBtn")?.addEventListener("click", async () => {
    const payload = {
      text: document.getElementById("crisisText")?.value || "",
      safe_status: document.getElementById("safeStatus")?.value || "not_sure",
      contact_person: document.getElementById("checkinContact")?.value || "",
      current_location: document.getElementById("checkinLocation")?.value || "",
      notes: document.getElementById("crisisText")?.value || "",
    };
    const data = await api("/api/crisis-checkin", { method: "POST", body: JSON.stringify(payload) });
    const box = document.getElementById("crisisResult");
    if (box) {
      box.classList.remove("hidden");
      box.innerHTML = `
        <strong>Risk: ${escapeHtml(data.risk_level)} (${escapeHtml(data.risk_score)}/100)</strong>
        <p>${escapeHtml(data.response || "Safety check saved.")}</p>
        <small>Urgency: ${escapeHtml(data.urgency)} · Action: ${escapeHtml(data.recommended_action)}</small>
      `;
    }
    toast("Safety check completed.");
  });

  document.getElementById("saveSafetyBtn").addEventListener("click", async () => {
    const payload = {};
    fields.forEach(id => {
      const el = document.getElementById(id);
      payload[map[id]] = el ? el.value : "";
    });
    const data = await api("/api/safety-plan", { method: "POST", body: JSON.stringify(payload) });
    updateCompletion(data.completion_score, data.validation || {});
    toast("Safety plan saved.");
  });
}

async function loadAdminData() {
  const data = await api("/api/admin/analytics");
  document.getElementById("adminUsers").textContent = data.totals.users;
  document.getElementById("adminMessages").textContent = data.totals.messages;
  document.getElementById("adminRisk").textContent = data.totals.risk_events;
  document.getElementById("adminHighRisk").textContent = data.totals.high_risk_events;
  document.getElementById("adminUnack").textContent = data.totals.unacknowledged_risk_events;
  document.getElementById("adminCheckins").textContent = data.totals.crisis_checkins;
  document.getElementById("adminVoice").textContent = data.totals.voice_sessions;
  document.getElementById("adminCalls").textContent = data.totals.call_sessions;
  document.getElementById("adminAvgMood").textContent = data.avg_mood ?? "-";
  document.getElementById("adminAvgRisk").textContent = data.avg_risk ?? "-";
  document.getElementById("adminSafetyPlans").textContent = data.totals.safety_plans ?? 0;
  document.getElementById("adminLatestRisk").textContent = data.latest_risk_event ? `${data.latest_risk_event.risk_level} · ${formatTime(data.latest_risk_event.created_at)}` : "-";

  const risks = await api("/api/admin/risk-events");
  const list = document.getElementById("riskList");
  list.innerHTML = "";
  (risks.risk_events || []).forEach(r => {
    const item = document.createElement("div");
    item.className = `list-item risk-event-card ${["high", "emergency"].includes(r.risk_level) ? "urgent" : ""}`;
    const cats = (r.categories_list || []).join(", ");
    item.innerHTML = `
      <strong>${escapeHtml(r.risk_level)} · ${escapeHtml(r.risk_score)}/100</strong>
      <small>${escapeHtml(r.user_id)} · ${formatTime(r.created_at)} · ${escapeHtml(r.urgency || "normal")}</small>
      <p>${escapeHtml(r.content_preview)}</p>
      <p class="muted-small">Action: ${escapeHtml(r.recommended_action || "-")} ${cats ? " · " + escapeHtml(cats) : ""}</p>
      ${r.acknowledged ? "<span class='mini-badge safe'>acknowledged</span>" : "<span class='mini-badge risk'>needs review</span>"}
    `;
    list.appendChild(item);
  });

  const checkins = await api("/api/admin/crisis-checkins");
  const checkinList = document.getElementById("checkinList");
  checkinList.innerHTML = "";
  (checkins.checkins || []).forEach(c => {
    const item = document.createElement("div");
    item.className = "list-item";
    item.innerHTML = `<strong>${escapeHtml(c.safe_status)}</strong><br><small>${escapeHtml(c.user_id)} · ${formatTime(c.created_at)}</small><p>Risk: ${escapeHtml(c.risk_level)} (${escapeHtml(c.risk_score)}/100)</p>`;
    checkinList.appendChild(item);
  });
}

async function initAdmin() {
  if (!document.getElementById("adminUsers")) return;
  await loadAdminData();
  document.getElementById("refreshAdminBtn")?.addEventListener("click", () => loadAdminData().then(() => toast("Admin data refreshed.")));
}


function telLink(phone) {
  const clean = String(phone || "").replace(/[^0-9+]/g, "");
  return clean ? `tel:${clean}` : "#";
}

async function loadContacts() {
  const list = document.getElementById("trustedContactList");
  if (!list) return;
  try {
    const data = await api("/api/connect/contacts");
    const contacts = [...(data.defaults || []), ...(data.contacts || [])];
    list.innerHTML = "";
    if (!contacts.length) {
      list.innerHTML = `<div class="empty-state">No contacts saved yet.</div>`;
      return;
    }
    contacts.forEach((c) => {
      const item = document.createElement("div");
      item.className = "contact-card";
      const isSaved = c.id !== undefined;
      const phone = c.phone || c.contact;
      item.innerHTML = `
        <div><strong>${escapeHtml(c.name)}</strong><small>${escapeHtml(c.relation || c.type || "support")}</small></div>
        <p>${escapeHtml(c.notes || c.description || "")}</p>
        <div class="button-row wrap">
          <a class="primary-btn" href="${telLink(phone)}">Call ${escapeHtml(phone)}</a>
          <a class="ghost-btn" href="sms:${escapeHtml(phone)}">Message</a>
          ${isSaved ? `<button class="ghost-btn danger-text" data-delete-contact="${c.id}" type="button">Delete</button>` : ""}
        </div>
      `;
      list.appendChild(item);
    });
    list.querySelectorAll("[data-delete-contact]").forEach((btn) => {
      btn.addEventListener("click", async () => {
        await api(`/api/connect/contacts/${btn.dataset.deleteContact}`, { method: "DELETE" });
        toast("Contact deleted.");
        loadContacts();
      });
    });
  } catch (err) {
    list.innerHTML = `<div class="empty-state">Could not load contacts.</div>`;
  }
}

async function saveTrustedContact() {
  const payload = {
    name: document.getElementById("contactName")?.value || "",
    phone: document.getElementById("contactPhone")?.value || "",
    relation: document.getElementById("contactRelation")?.value || "trusted_person",
    notes: document.getElementById("contactNotes")?.value || "",
    is_primary: document.getElementById("contactPrimary")?.checked || false,
  };
  try {
    await api("/api/connect/contacts", { method: "POST", body: JSON.stringify(payload) });
    ["contactName", "contactPhone", "contactRelation", "contactNotes"].forEach(id => { const el = document.getElementById(id); if (el) el.value = ""; });
    const primary = document.getElementById("contactPrimary");
    if (primary) primary.checked = false;
    toast("Trusted contact saved.");
    loadContacts();
  } catch (err) {
    toast("Contact save failed: " + err.message);
  }
}

async function startCameraPreview() {
  const video = document.getElementById("localVideoPreview");
  const empty = document.getElementById("videoPreviewEmpty");
  if (!video || !navigator.mediaDevices?.getUserMedia) return toast("Camera not supported in this browser.");
  try {
    localVideoStream = await navigator.mediaDevices.getUserMedia({ video: true, audio: true });
    video.srcObject = localVideoStream;
    await video.play();
    if (empty) empty.classList.add("hidden");
    toast("Camera preview started.");
  } catch (err) {
    toast("Camera permission/error: " + err.message);
  }
}

function stopCameraPreview() {
  if (localVideoStream) {
    localVideoStream.getTracks().forEach(track => track.stop());
    localVideoStream = null;
  }
  const video = document.getElementById("localVideoPreview");
  const empty = document.getElementById("videoPreviewEmpty");
  if (video) video.srcObject = null;
  if (empty) empty.classList.remove("hidden");
}

async function createVideoRoom() {
  try {
    const data = await api("/api/connect/video-room", { method: "POST", body: JSON.stringify({ language: getPreferredLanguage() }) });
    const room = data.room || {};
    const box = document.getElementById("videoRoomBox");
    const urlEl = document.getElementById("videoRoomUrl");
    const link = document.getElementById("openVideoRoomLink");
    if (box) box.classList.remove("hidden");
    if (urlEl) urlEl.textContent = room.room_url || "";
    if (link) link.href = room.room_url || "#";
    renderVideoSessions(data.sessions || []);
    toast("V-Call room created. Share the link with a trusted person.");
  } catch (err) {
    toast("Video room failed: " + err.message);
  }
}

function renderVideoSessions(sessions = []) {
  const list = document.getElementById("videoSessionList");
  if (!list) return;
  list.innerHTML = "";
  if (!sessions.length) {
    list.innerHTML = `<div class="empty-state">No v-call rooms yet.</div>`;
    return;
  }
  sessions.forEach((s) => {
    const item = document.createElement("div");
    item.className = "list-item";
    item.innerHTML = `<strong>${escapeHtml(s.room_id)}</strong><br><small>${formatTime(s.started_at)} · ${escapeHtml(s.language || "hinglish")}</small><div class="button-row wrap"><a class="ghost-btn" target="_blank" rel="noopener" href="${escapeHtml(s.room_url)}">Open</a><button class="ghost-btn" data-copy="${escapeHtml(s.room_url)}">Copy</button></div>`;
    list.appendChild(item);
  });
  list.querySelectorAll("[data-copy]").forEach(btn => btn.addEventListener("click", () => navigator.clipboard?.writeText(btn.dataset.copy).then(() => toast("Link copied."))));
}

async function initConnect() {
  if (!document.getElementById("trustedContactList")) return;
  initLanguageControls();
  document.getElementById("saveContactBtn")?.addEventListener("click", saveTrustedContact);
  document.getElementById("startCameraBtn")?.addEventListener("click", startCameraPreview);
  document.getElementById("stopCameraBtn")?.addEventListener("click", stopCameraPreview);
  document.getElementById("createVideoRoomBtn")?.addEventListener("click", createVideoRoom);
  document.getElementById("copyVideoRoomBtn")?.addEventListener("click", () => {
    const url = document.getElementById("videoRoomUrl")?.textContent || "";
    if (url) navigator.clipboard?.writeText(url).then(() => toast("Video link copied."));
  });
  await loadContacts();
  try {
    const data = await api("/api/connect/video-sessions");
    renderVideoSessions(data.sessions || []);
  } catch (err) {}
}

document.addEventListener("DOMContentLoaded", () => {
  initTheme();
  initChat();
  initDashboard().catch(err => console.warn(err));
  initJournal().catch(err => console.warn(err));
  initSafety().catch(err => console.warn(err));
  initAdmin().catch(err => console.warn(err));
  initConnect().catch(err => console.warn(err));
});

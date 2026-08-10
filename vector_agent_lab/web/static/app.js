const messageList = document.getElementById("messageList");
const chatForm = document.getElementById("chatForm");
const messageInput = document.getElementById("messageInput");
const sendButton = document.getElementById("sendButton");
const toolList = document.getElementById("toolList");
const conversationList = document.getElementById("conversationList");
const traceList = document.getElementById("traceList");
const statusText = document.getElementById("statusText");
const sessionLabel = document.getElementById("sessionLabel");
const newSessionButton = document.getElementById("newSessionButton");
const newTopicButton = document.getElementById("newTopicButton");

const storageKey = "vector_agent_lab_session_id";
let sessionId = window.localStorage.getItem(storageKey) || "";
let conversations = [];

function setStatus(text) {
  statusText.textContent = text;
}

function updateSessionLabel(conversation) {
  if (conversation) {
    sessionLabel.textContent = `Topic: ${conversation.title}`;
    return;
  }
  sessionLabel.textContent = sessionId ? `Session ${sessionId.slice(0, 10)}` : "New topic";
}

function messageClass(role) {
  if (role === "assistant" || role === "agent") {
    return "agent";
  }
  if (role === "system" || role === "tool") {
    return "agent";
  }
  return role;
}

function shouldRenderMarkdown(role) {
  return role === "assistant" || role === "agent";
}

function escapeHtml(value) {
  return String(value)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#39;");
}

function renderInlineMarkdown(value) {
  const codeParts = [];
  let html = escapeHtml(value);

  html = html.replace(/`([^`]+)`/g, (_, code) => {
    const token = `@@CODE_${codeParts.length}@@`;
    codeParts.push(`<code>${code}</code>`);
    return token;
  });

  html = html.replace(/\*\*([^*]+)\*\*/g, "<strong>$1</strong>");
  html = html.replace(/\*([^*\n]+)\*/g, "<em>$1</em>");
  html = html.replace(
    /\[([^\]]+)\]\((https?:\/\/[^)\s]+)\)/g,
    '<a href="$2" target="_blank" rel="noopener noreferrer">$1</a>',
  );

  return html.replace(/@@CODE_(\d+)@@/g, (_, index) => codeParts[Number(index)] || "");
}

function appendMarkdownBlock(container, tagName, text, className) {
  const element = document.createElement(tagName);
  if (className) {
    element.className = className;
  }
  element.innerHTML = renderInlineMarkdown(text);
  container.appendChild(element);
  return element;
}

function renderMarkdown(text) {
  const container = document.createElement("div");
  container.className = "markdown-body";
  const lines = String(text || "").replace(/\r\n/g, "\n").split("\n");

  let paragraph = [];
  let list = null;
  let listType = "";
  let blockquote = [];
  let codeFence = false;
  let codeLines = [];

  function flushParagraph() {
    if (paragraph.length === 0) {
      return;
    }
    appendMarkdownBlock(container, "p", paragraph.join(" "));
    paragraph = [];
  }

  function flushList() {
    if (!list) {
      return;
    }
    container.appendChild(list);
    list = null;
    listType = "";
  }

  function flushBlockquote() {
    if (blockquote.length === 0) {
      return;
    }
    appendMarkdownBlock(container, "blockquote", blockquote.join("\n"));
    blockquote = [];
  }

  function flushCodeBlock() {
    const pre = document.createElement("pre");
    const code = document.createElement("code");
    code.textContent = codeLines.join("\n");
    pre.appendChild(code);
    container.appendChild(pre);
    codeLines = [];
  }

  function flushBlocks() {
    flushParagraph();
    flushList();
    flushBlockquote();
  }

  for (const line of lines) {
    const trimmed = line.trim();

    if (trimmed.startsWith("```")) {
      if (codeFence) {
        flushCodeBlock();
        codeFence = false;
      } else {
        flushBlocks();
        codeFence = true;
      }
      continue;
    }

    if (codeFence) {
      codeLines.push(line);
      continue;
    }

    if (!trimmed) {
      flushBlocks();
      continue;
    }

    if (/^(-{3,}|\*{3,}|_{3,})$/.test(trimmed)) {
      flushBlocks();
      container.appendChild(document.createElement("hr"));
      continue;
    }

    const heading = /^(#{1,4})\s+(.+)$/.exec(trimmed);
    if (heading) {
      flushBlocks();
      appendMarkdownBlock(container, `h${heading[1].length}`, heading[2]);
      continue;
    }

    const quote = /^>\s?(.*)$/.exec(line);
    if (quote) {
      flushParagraph();
      flushList();
      blockquote.push(quote[1]);
      continue;
    }

    const unordered = /^[-*]\s+(.+)$/.exec(trimmed);
    const ordered = /^\d+\.\s+(.+)$/.exec(trimmed);
    if (unordered || ordered) {
      flushParagraph();
      flushBlockquote();

      const nextType = ordered ? "ol" : "ul";
      if (!list || listType !== nextType) {
        flushList();
        list = document.createElement(nextType);
        listType = nextType;
      }

      const item = document.createElement("li");
      item.innerHTML = renderInlineMarkdown((ordered || unordered)[1]);
      list.appendChild(item);
      continue;
    }

    flushList();
    flushBlockquote();
    paragraph.push(trimmed);
  }

  if (codeFence) {
    flushCodeBlock();
  }
  flushBlocks();

  return container;
}

function appendMessage(role, text) {
  const item = document.createElement("div");
  item.className = `message ${messageClass(role)}`;

  if (shouldRenderMarkdown(role)) {
    item.appendChild(renderMarkdown(text));
  } else {
    item.textContent = text;
  }

  messageList.appendChild(item);
  messageList.scrollTop = messageList.scrollHeight;
}

function renderMessages(messages) {
  messageList.innerHTML = "";
  for (const message of messages || []) {
    appendMessage(message.role, message.content);
  }
}

function renderTrace(traceEvents) {
  traceList.innerHTML = "";

  if (!traceEvents || traceEvents.length === 0) {
    const empty = document.createElement("div");
    empty.className = "empty-state";
    empty.textContent = "No trace yet";
    traceList.appendChild(empty);
    return;
  }

  for (const event of traceEvents) {
    const item = document.createElement("div");
    item.className = `trace-item trace-${event.type || "event"}`;

    const header = document.createElement("div");
    header.className = "trace-header";

    const title = document.createElement("div");
    title.className = "trace-title";
    title.textContent = `${event.step}. ${event.title}`;

    const type = document.createElement("div");
    type.className = "trace-type";
    type.textContent = event.type || "event";

    header.append(title, type);
    item.appendChild(header);

    if (event.detail) {
      const detail = document.createElement("pre");
      detail.className = "trace-detail";
      detail.textContent = event.detail;
      item.appendChild(detail);
    }

    traceList.appendChild(item);
  }
}

function formatDate(value) {
  if (!value) {
    return "";
  }

  const date = new Date(value);
  if (Number.isNaN(date.getTime())) {
    return "";
  }

  return date.toLocaleString([], {
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
  });
}

function renderConversations(items) {
  conversationList.innerHTML = "";

  if (!items || items.length === 0) {
    const empty = document.createElement("div");
    empty.className = "empty-state";
    empty.textContent = "No topics yet";
    conversationList.appendChild(empty);
    return;
  }

  for (const conversation of items) {
    const item = document.createElement("button");
    item.className = `conversation-item${conversation.id === sessionId ? " active" : ""}`;
    item.type = "button";

    const title = document.createElement("div");
    title.className = "conversation-title";
    title.textContent = conversation.title || "Untitled";

    const meta = document.createElement("div");
    meta.className = "conversation-meta";
    meta.textContent = `${conversation.message_count || 0} messages · ${formatDate(conversation.updated_at)}`;

    item.append(title, meta);

    if (conversation.last_message) {
      const preview = document.createElement("div");
      preview.className = "conversation-preview";
      preview.textContent = conversation.last_message;
      item.appendChild(preview);
    }

    item.addEventListener("click", () => loadConversation(conversation.id));
    conversationList.appendChild(item);
  }
}

async function loadConversations() {
  const response = await fetch("/api/conversations");
  if (!response.ok) {
    throw new Error(`HTTP ${response.status}`);
  }

  const payload = await response.json();
  conversations = payload.conversations || [];
  renderConversations(conversations);
  return conversations;
}

async function loadConversation(nextSessionId) {
  if (!nextSessionId) {
    return;
  }

  const response = await fetch(`/api/conversations/${nextSessionId}`);
  if (response.status === 404) {
    sessionId = "";
    window.localStorage.removeItem(storageKey);
    messageList.innerHTML = "";
    renderTrace([]);
    updateSessionLabel();
    conversations = conversations.filter((conversation) => conversation.id !== nextSessionId);
    renderConversations(conversations);
    messageInput.focus();
    return;
  }

  if (!response.ok) {
    throw new Error(`HTTP ${response.status}`);
  }

  const payload = await response.json();
  sessionId = payload.conversation.id;
  window.localStorage.setItem(storageKey, sessionId);
  renderMessages(payload.messages || []);
  renderTrace(payload.trace || []);
  updateSessionLabel(payload.conversation);
  renderConversations(conversations);
  messageInput.focus();
}

function parseToolDescription(description) {
  return description
    .split("\n")
    .map((line) => line.trim())
    .filter(Boolean)
    .map((line) => {
      const clean = line.startsWith("- ") ? line.slice(2) : line;
      const splitAt = clean.indexOf(":");
      if (splitAt === -1) {
        return { name: clean, description: "" };
      }
      return {
        name: clean.slice(0, splitAt).trim(),
        description: clean.slice(splitAt + 1).trim(),
      };
    });
}

async function loadTools() {
  try {
    const response = await fetch("/api/tools");
    if (!response.ok) {
      throw new Error(`HTTP ${response.status}`);
    }

    const payload = await response.json();
    const tools = parseToolDescription(payload.description || "");
    toolList.innerHTML = "";

    for (const tool of tools) {
      const item = document.createElement("div");
      item.className = "tool-item";

      const name = document.createElement("div");
      name.className = "tool-name";
      name.textContent = tool.name;

      const desc = document.createElement("div");
      desc.className = "tool-desc";
      desc.textContent = tool.description;

      item.append(name, desc);
      toolList.appendChild(item);
    }

    setStatus("Ready");
  } catch (error) {
    setStatus("Offline");
    toolList.textContent = String(error.message || error);
  }
}

function autosizeInput() {
  messageInput.style.height = "auto";
  messageInput.style.height = `${messageInput.scrollHeight}px`;
}

async function sendMessage(text) {
  appendMessage("user", text);
  renderTrace([{ step: 1, type: "running", title: "Agent running", detail: text }]);
  sendButton.disabled = true;
  sendButton.textContent = "Wait";

  try {
    const response = await fetch("/api/chat", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        message: text,
        session_id: sessionId || null,
        max_tool_iterations: 5,
      }),
    });

    const payload = await response.json();
    if (!response.ok) {
      throw new Error(payload.detail || `HTTP ${response.status}`);
    }

    sessionId = payload.session_id;
    window.localStorage.setItem(storageKey, sessionId);
    updateSessionLabel(payload.conversation);
    appendMessage("agent", payload.reply || "");
    renderTrace(payload.trace || []);
    await loadConversations();
  } catch (error) {
    appendMessage("error", String(error.message || error));
    renderTrace([{ step: 1, type: "error", title: "Request failed", detail: String(error.message || error) }]);
  } finally {
    sendButton.disabled = false;
    sendButton.textContent = "Send";
    messageInput.focus();
  }
}

chatForm.addEventListener("submit", (event) => {
  event.preventDefault();
  const text = messageInput.value.trim();
  if (!text) {
    return;
  }
  messageInput.value = "";
  autosizeInput();
  sendMessage(text);
});

messageInput.addEventListener("input", autosizeInput);
messageInput.addEventListener("keydown", (event) => {
  if (event.key === "Enter" && !event.shiftKey) {
    event.preventDefault();
    chatForm.requestSubmit();
  }
});

async function startNewTopic() {
  const oldSessionId = sessionId;
  sessionId = "";
  window.localStorage.removeItem(storageKey);
  messageList.innerHTML = "";
  renderTrace([]);
  updateSessionLabel();
  renderConversations(conversations);

  if (oldSessionId) {
    await fetch(`/api/sessions/${oldSessionId}/reset`, { method: "POST" }).catch(() => {});
  }

  messageInput.focus();
}

newSessionButton.addEventListener("click", startNewTopic);
newTopicButton.addEventListener("click", startNewTopic);

updateSessionLabel();
renderTrace([]);
loadTools();
loadConversations()
  .then(() => {
    if (sessionId) {
      return loadConversation(sessionId);
    }
    return null;
  })
  .catch((error) => {
    setStatus("Offline");
    conversationList.innerHTML = "";
    const empty = document.createElement("div");
    empty.className = "empty-state";
    empty.textContent = String(error.message || error);
    conversationList.appendChild(empty);
    sessionId = "";
    window.localStorage.removeItem(storageKey);
    updateSessionLabel();
  });

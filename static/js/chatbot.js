const chatThread = document.getElementById("chat-thread");
const chatEmpty = document.getElementById("chat-empty");
const chatInput = document.getElementById("chat-input");
const sendButton = document.getElementById("send-message");
const promptChips = document.getElementById("prompt-chips");
const floatingButton = document.getElementById("floating-assistant");
const assistantPopover = document.getElementById("assistant-popover");
const assistantInput = document.getElementById("assistant-input");
const assistantSend = document.getElementById("assistant-send");
const assistantClose = document.getElementById("assistant-close");

const STORAGE_KEY = "smartcampus_chat_history";
const MAX_HISTORY = 20;

const getToken = () => null;

const escapeHtml = (value) =>
  value
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/\"/g, "&quot;")
    .replace(/'/g, "&#039;");

const formatMarkdown = (text) => {
  const safe = escapeHtml(text || "");
  const parts = safe.split("```");
  const formatted = parts
    .map((part, index) => {
      if (index % 2 === 1) {
        return `<pre><code>${part}</code></pre>`;
      }
      let output = part.replace(/`([^`]+)`/g, "<code>$1</code>");
      output = output.replace(/\*\*([^*]+)\*\*/g, "<strong>$1</strong>");
      output = output.replace(/\n/g, "<br>");
      return output;
    })
    .join("");
  return formatted;
};

const saveHistory = (messages) => {
  const trimmed = messages.slice(-MAX_HISTORY);
  localStorage.setItem(STORAGE_KEY, JSON.stringify(trimmed));
};

const loadHistory = () => {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    return raw ? JSON.parse(raw) : [];
  } catch (error) {
    return [];
  }
};

const scrollToBottom = () => {
  if (!chatThread) return;
  chatThread.scrollTop = chatThread.scrollHeight;
};

const setEmptyState = (visible) => {
  if (!chatEmpty) return;
  chatEmpty.style.display = visible ? "grid" : "none";
};

const renderMessage = (role, content, options = {}) => {
  if (!chatThread) return;
  const wrapper = document.createElement("div");
  wrapper.className = `chat-message ${role}`;

  const bubble = document.createElement("div");
  bubble.className = role === "user" ? "user-bubble" : "assistant-bubble";
  bubble.innerHTML = `<div class="message-text">${formatMarkdown(content)}</div>`;

  if (role === "assistant" && options.actions) {
    const actions = document.createElement("div");
    actions.className = "message-actions";
    options.actions.forEach((action) => {
      const button = document.createElement("button");
      button.type = "button";
      button.className = "ghost-btn";
      button.textContent = action;
      button.addEventListener("click", () => {
        if (window.showToast) {
          window.showToast(`${action} queued`, "success");
        }
      });
      actions.appendChild(button);
    });
    bubble.appendChild(actions);
  }

  wrapper.appendChild(bubble);
  chatThread.appendChild(wrapper);
  scrollToBottom();
};

const renderTyping = () => {
  if (!chatThread) return null;
  const wrapper = document.createElement("div");
  wrapper.className = "chat-message assistant";
  wrapper.innerHTML = `
    <div class="assistant-bubble typing">
      <div class="typing-indicator">
        <span></span><span></span><span></span>
      </div>
      <div class="typing-status">Thinking...</div>
    </div>
  `;
  chatThread.appendChild(wrapper);
  scrollToBottom();
  return wrapper;
};

const updateTypingState = (node, state) => {
  if (!node) return;
  const status = node.querySelector(".typing-status");
  if (status) {
    status.textContent = state;
  }
};

const streamText = (node, text) => {
  if (!node) return;
  const message = node.querySelector(".message-text");
  if (!message) return;
  let index = 0;
  const step = () => {
    index += Math.max(2, Math.round(text.length / 120));
    const slice = text.slice(0, index);
    message.innerHTML = formatMarkdown(slice);
    scrollToBottom();
    if (index < text.length) {
      requestAnimationFrame(step);
    }
  };
  requestAnimationFrame(step);
};

const handleSend = async (inputValue) => {
  const message = (inputValue || "").trim();
  if (!message) return;
  if (message.length > 1000) {
    if (window.showToast) {
      window.showToast("Message too long", "error");
    }
    return;
  }
  const history = loadHistory();
  renderMessage("user", message);
  setEmptyState(false);
  history.push({ role: "user", content: message });
  saveHistory(history);

  const typingNode = renderTyping();
  updateTypingState(typingNode, "Searching context...");

  try {
    const response = await window.apiFetch("/api/chatbot/message", {
      method: "POST",
      body: JSON.stringify({
        message,
        history: history.map((item) => `${item.role}: ${item.content}`),
      }),
    });

    if (!response || !response.ok) {
      throw new Error("AI request failed");
    }

    const data = await response.json();
    if (!data.success) {
      throw new Error(data.message || "AI response unavailable");
    }

    if (typingNode) {
      typingNode.remove();
    }

    const actions = [
      "Generate Quiz",
      "Create Study Plan",
      "Explain Further",
      "Save Notes",
      "Start Focus Session",
    ];
    const wrapper = document.createElement("div");
    wrapper.className = "chat-message assistant";
    wrapper.innerHTML = `<div class="assistant-bubble"><div class="message-text"></div></div>`;
    chatThread.appendChild(wrapper);
    streamText(wrapper, data.response || "");

    const actionsRow = document.createElement("div");
    actionsRow.className = "message-actions";
    actions.forEach((action) => {
      const button = document.createElement("button");
      button.type = "button";
      button.className = "ghost-btn";
      button.textContent = action;
      button.addEventListener("click", () => {
        if (window.showToast) {
          window.showToast(`${action} queued`, "success");
        }
      });
      actionsRow.appendChild(button);
    });
    const bubble = wrapper.querySelector(".assistant-bubble");
    bubble.appendChild(actionsRow);

    history.push({ role: "assistant", content: data.response || "" });
    saveHistory(history);
  } catch (error) {
    if (typingNode) {
      typingNode.remove();
    }
    renderMessage("assistant", "I ran into a hiccup. Please try again in a moment.");
    if (window.showToast) {
      window.showToast("AI request failed", "error");
    }
  }
};

const loadSuggestions = async () => {
  if (!promptChips) return;
  try {
    const response = await window.apiFetch("/api/chatbot/suggestions");
    if (!response || !response.ok) return;
    const data = await response.json();
    promptChips.innerHTML = "";
    (data.suggestions || []).forEach((suggestion) => {
      const chip = document.createElement("button");
      chip.type = "button";
      chip.className = "chip";
      chip.textContent = suggestion;
      chip.addEventListener("click", () => {
        if (chatInput) {
          chatInput.value = suggestion;
          chatInput.focus();
        }
      });
      promptChips.appendChild(chip);
    });
  } catch (error) {
    promptChips.innerHTML = "";
  }
};

const hydrateHistory = () => {
  const history = loadHistory();
  if (!history.length) {
    setEmptyState(true);
    return;
  }
  setEmptyState(false);
  history.forEach((item) => {
    renderMessage(item.role, item.content);
  });
};

const bindShortcuts = () => {
  document.addEventListener("keydown", (event) => {
    if (event.key === "/" && document.activeElement !== chatInput) {
      event.preventDefault();
      if (chatInput) {
        chatInput.focus();
      }
    }
    if ((event.ctrlKey || event.metaKey) && event.key.toLowerCase() === "k") {
      event.preventDefault();
      if (chatInput) {
        chatInput.focus();
      }
    }
  });
};

const setupFloatingAssistant = () => {
  if (!floatingButton || !assistantPopover) return;
  floatingButton.addEventListener("click", () => {
    assistantPopover.classList.toggle("open");
  });
  if (assistantClose) {
    assistantClose.addEventListener("click", () => {
      assistantPopover.classList.remove("open");
    });
  }
  if (assistantSend) {
    assistantSend.addEventListener("click", () => {
      const value = assistantInput.value.trim();
      if (!value) return;
      assistantInput.value = "";
      assistantPopover.classList.remove("open");
      handleSend(value);
    });
  }
};

if (sendButton) {
  sendButton.addEventListener("click", () => handleSend(chatInput.value));
}

if (chatInput) {
  chatInput.addEventListener("keydown", (event) => {
    if (event.key === "Enter" && !event.shiftKey) {
      event.preventDefault();
      handleSend(chatInput.value);
      chatInput.value = "";
    }
  });
}

hydrateHistory();
loadSuggestions();
bindShortcuts();
setupFloatingAssistant();

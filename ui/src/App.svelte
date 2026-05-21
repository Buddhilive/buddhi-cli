<script lang="ts">
  import { onMount, tick } from "svelte";
  import { Streamdown } from "svelte-streamdown";

  // Chat message interface
  interface Message {
    id: string;
    role: "user" | "assistant";
    text: string;
  }

  // Svelte 5 Runes for State Management
  let messages = $state<Message[]>([]);
  let inputText = $state("");
  let isStreaming = $state(false);
  let isThinking = $state(false);
  let error = $state<string | null>(null);
  let isDarkMode = $state(false);

  // Auto-scroll references
  let chatContainer = $state<HTMLElement | null>(null);
  let autoScroll = $state(true);
  let showScrollButton = $state(false);
  let textareaRef = $state<HTMLTextAreaElement | null>(null);

  // Initialize Theme on Mount
  onMount(() => {
    const savedTheme = localStorage.getItem("theme");
    if (
      savedTheme === "dark" ||
      (!savedTheme && window.matchMedia("(prefers-color-scheme: dark)").matches)
    ) {
      isDarkMode = true;
      document.documentElement.classList.add("dark");
    } else {
      isDarkMode = false;
      document.documentElement.classList.remove("dark");
    }
  });

  // Toggle Theme Switcher
  function toggleTheme() {
    isDarkMode = !isDarkMode;
    if (isDarkMode) {
      document.documentElement.classList.add("dark");
      localStorage.setItem("theme", "dark");
    } else {
      document.documentElement.classList.remove("dark");
      localStorage.setItem("theme", "light");
    }
  }

  // Clear Session & Reset Chat
  function startNewChat() {
    messages = [];
    error = null;
    inputText = "";
    isStreaming = false;
    isThinking = false;
    autoScroll = true;
    showScrollButton = false;
    if (textareaRef) {
      textareaRef.style.height = "auto";
    }
  }

  // Automatically grow textarea vertically
  function handleInput(e: Event) {
    const target = e.target as HTMLTextAreaElement;
    target.style.height = "auto";
    target.style.height = `${Math.min(target.scrollHeight, 180)}px`;
  }

  // Capture scrolling actions
  function handleScroll() {
    if (!chatContainer) return;
    const { scrollTop, scrollHeight, clientHeight } = chatContainer;

    // Check if user is near the bottom
    const isAtBottom = scrollHeight - scrollTop - clientHeight < 40;

    if (isAtBottom) {
      autoScroll = true;
      showScrollButton = false;
    } else {
      if (isStreaming) {
        autoScroll = false;
        showScrollButton = true;
      }
    }
  }

  // Scroll viewport down helper
  async function scrollToBottom() {
    await tick();
    if (chatContainer) {
      chatContainer.scrollTop = chatContainer.scrollHeight;
    }
  }

  // Handle enter key submit
  function handleKeyDown(e: KeyboardEvent) {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      sendMessage();
    }
  }

  // Stream-decode standard and SSE Responses API events
  async function sendMessage() {
    if (!inputText.trim() || isStreaming) return;

    const userMessageText = inputText;
    inputText = "";
    error = null;

    if (textareaRef) {
      textareaRef.style.height = "auto";
    }

    const userMsgId = `usr-${Math.random().toString(36).slice(2, 11)}`;
    messages.push({
      id: userMsgId,
      role: "user",
      text: userMessageText,
    });

    autoScroll = true;
    showScrollButton = false;
    await scrollToBottom();

    const agentMsgId = `agt-${Math.random().toString(36).slice(2, 11)}`;
    isThinking = true;
    isStreaming = true;

    const isViteDev =
      typeof window !== "undefined" && window.location.port === "58422";
    const apiEndpoint = isViteDev
      ? "http://localhost:58421/v1/responses"
      : "/v1/responses";

    try {
      const requestPayload = {
        input: messages.map((msg) => ({
          role: msg.role,
          content: [{ type: "text", text: msg.text }],
        })),
        stream: true,
      };

      const response = await fetch(apiEndpoint, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify(requestPayload),
      });

      if (!response.ok) {
        throw new Error(`Inference returned status ${response.status}`);
      }

      if (!response.body) {
        throw new Error("Empty body received from the inference stream.");
      }

      const reader = response.body.getReader();
      const decoder = new TextDecoder();
      let buffer = "";

      messages.push({
        id: agentMsgId,
        role: "assistant",
        text: "",
      });

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split("\n");
        buffer = lines.pop() || "";

        for (const line of lines) {
          const cleanLine = line.trim();
          if (!cleanLine) continue;

          if (cleanLine === "data: [DONE]") {
            continue;
          }

          if (cleanLine.startsWith("data: ")) {
            try {
              const dataJson = JSON.parse(cleanLine.substring(6));
              const textChunk = dataJson.delta?.content?.[0]?.text || "";

              if (textChunk) {
                if (isThinking) {
                  isThinking = false;
                }

                const agentMsgIndex = messages.findIndex(
                  (m) => m.id === agentMsgId,
                );
                if (agentMsgIndex !== -1) {
                  messages[agentMsgIndex].text += textChunk;
                }

                if (autoScroll) {
                  await scrollToBottom();
                }
              }
            } catch (err) {
              console.error("Failed to parse SSE payload line:", err);
            }
          }
        }
      }
    } catch (err: any) {
      console.error("Streaming connection failed:", err);
      error =
        err.message || "A network error occurred while reaching the server.";
      isThinking = false;

      // Clean up empty placeholder messages
      const lastMsg = messages[messages.length - 1];
      if (lastMsg && lastMsg.role === "assistant" && !lastMsg.text) {
        messages.pop();
      }
    } finally {
      isStreaming = false;
      isThinking = false;
    }
  }

  // Retry logic: removes trailing error state and re-submits
  function retryLastMessage() {
    if (messages.length === 0 || isStreaming) return;

    const userMsgs = messages.filter((m) => m.role === "user");
    if (userMsgs.length === 0) return;

    const lastUserMsg = userMsgs[userMsgs.length - 1];
    const index = messages.findIndex((m) => m.id === lastUserMsg.id);

    if (index !== -1) {
      inputText = lastUserMsg.text;
      messages = messages.slice(0, index);
      sendMessage();
    }
  }

  // Preset prompts loader
  function selectPreset(promptText: string) {
    inputText = promptText;
    if (textareaRef) {
      textareaRef.focus();
      textareaRef.style.height = "auto";
      textareaRef.style.height = `${Math.min(textareaRef.scrollHeight, 180)}px`;
    }
  }
</script>

<div class="app-container">
  <!-- Topbar -->
  <header class="top-nav">
    <div class="logo-area">
      <span class="logo-prefix">BUDDHI</span>
      <span class="logo-suffix">AI</span>
      <span class="logo-badge">playground</span>
    </div>

    <div class="actions-area">
      <button
        onclick={startNewChat}
        class="btn-secondary"
        title="Start New Chat"
      >
        <svg
          xmlns="http://www.w3.org/2000/svg"
          width="16"
          height="16"
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          stroke-width="2"
          stroke-linecap="round"
          stroke-linejoin="round"
        >
          <path
            d="M3 6h18M19 6v14c0 1-1 2-2 2H7c-1 0-2-1-2-2V6M8 6V4c0-1 1-2 2-2h4c1 0 2 1 2 2v2M10 11v6M14 11v6"
          />
        </svg>
        <span>New Chat</span>
      </button>

      <button
        onclick={toggleTheme}
        class="btn-icon"
        title="Toggle Light/Dark Theme"
        aria-label="Toggle Theme"
      >
        {#if isDarkMode}
          <!-- Sun Icon -->
          <svg
            xmlns="http://www.w3.org/2000/svg"
            width="18"
            height="18"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            stroke-width="2"
            stroke-linecap="round"
            stroke-linejoin="round"
          >
            <circle cx="12" cy="12" r="4" /><path
              d="M12 2v2M12 20v2M4.93 4.93l1.41 1.41M17.66 17.66l1.41 1.41M2 12h2M20 12h2M6.34 17.66l-1.41 1.41M19.07 4.93l-1.41 1.41"
            />
          </svg>
        {:else}
          <!-- Moon Icon -->
          <svg
            xmlns="http://www.w3.org/2000/svg"
            width="18"
            height="18"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            stroke-width="2"
            stroke-linecap="round"
            stroke-linejoin="round"
          >
            <path d="M12 3a6 6 0 0 0 9 9 9 9 0 1 1-9-9Z" />
          </svg>
        {/if}
      </button>
    </div>
  </header>

  <!-- Main Viewport -->
  <main bind:this={chatContainer} onscroll={handleScroll} class="chat-viewport">
    <div class="chat-inner">
      {#if messages.length === 0}
        <!-- Welcome empty state -->
        <section class="empty-state">
          <div class="empty-branding animate-spring-slide-in">
            <h1>Inference Terminal</h1>
            <p class="subtitle">Buddhi AI Playground</p>
          </div>

          <div class="presets-grid">
            <h2 class="presets-title">Quick Starter Prompts</h2>
            <div class="presets-list">
              <button
                onclick={() =>
                  selectPreset(
                    "Explain quantum computing in simple technical terms.",
                  )}
                class="preset-card"
              >
                <h3>Explain Quantum Tech</h3>
                <p>Learn complex physics in clear analogies.</p>
              </button>
              <button
                onclick={() =>
                  selectPreset(
                    "Write a highly optimized TypeScript binary search function with comments.",
                  )}
                class="preset-card"
              >
                <h3>Algorithm Optimization</h3>
                <p>Request clear, structured, type-safe code snippets.</p>
              </button>
              <button
                onclick={() =>
                  selectPreset(
                    "What are the key best practices when structuring Svelte 5 runes?",
                  )}
                class="preset-card"
              >
                <h3>Svelte 5 Runes Advice</h3>
                <p>Discuss reactive state design patterns.</p>
              </button>
            </div>
          </div>
        </section>
      {:else}
        <!-- Conversation Thread -->
        <div class="message-list">
          {#each messages as msg (msg.id)}
            {#if msg.role === "user"}
              <div class="message-row user-row">
                <div class="message-bubble user-bubble animate-spring-slide-in">
                  <span class="user-meta">User</span>
                  <div class="user-content">{msg.text}</div>
                </div>
              </div>
            {:else}
              <div class="message-row agent-row">
                <div class="agent-avatar">
                  <svg
                    xmlns="http://www.w3.org/2000/svg"
                    width="16"
                    height="16"
                    viewBox="0 0 24 24"
                    fill="none"
                    stroke="currentColor"
                    stroke-width="2"
                    stroke-linecap="round"
                    stroke-linejoin="round"
                  >
                    <path
                      d="M12 2a10 10 0 0 1 7.54 16.59A6 6 0 0 0 12 13a6 6 0 0 0-7.54 3.59A10 10 0 0 1 12 2Z"
                    /><circle cx="12" cy="8" r="3.5" />
                  </svg>
                </div>
                <div class="message-bubble agent-bubble markdown-body">
                  {#if msg.text}
                    <Streamdown content={msg.text} />
                  {:else}
                    <div class="typing-loading">
                      <span class="typing-dot"></span>
                      <span class="typing-dot"></span>
                      <span class="typing-dot"></span>
                    </div>
                  {/if}
                </div>
              </div>
            {/if}
          {/each}

          <!-- Agent Shimmer Thinking Box -->
          {#if isThinking}
            <div class="message-row agent-row thinking-row">
              <div class="agent-avatar">
                <svg
                  class="spin-slow"
                  xmlns="http://www.w3.org/2000/svg"
                  width="16"
                  height="16"
                  viewBox="0 0 24 24"
                  fill="none"
                  stroke="currentColor"
                  stroke-width="2"
                  stroke-linecap="round"
                  stroke-linejoin="round"
                >
                  <path
                    d="M12 2v4M12 18v4M4.93 4.93l2.83 2.83M16.24 16.24l2.83 2.83M2 12h4M18 12h4M6.34 17.66l2.83-2.83M14.93 9.07l2.83-2.83"
                  />
                </svg>
              </div>
              <div
                class="message-bubble agent-bubble thinking-bubble animate-shimmer"
              >
                <div class="thinking-text">
                  Agent is formulating a response...
                </div>
                <div class="shimmer-block"></div>
                <div class="shimmer-block w-4-5"></div>
                <div class="shimmer-block w-3-5"></div>
              </div>
            </div>
          {/if}

          <!-- Graceful Error Dialog -->
          {#if error}
            <div class="message-row system-row">
              <div class="error-card animate-spring-slide-in">
                <div class="error-header">
                  <svg
                    xmlns="http://www.w3.org/2000/svg"
                    width="18"
                    height="18"
                    viewBox="0 0 24 24"
                    fill="none"
                    stroke="currentColor"
                    stroke-width="2"
                    stroke-linecap="round"
                    stroke-linejoin="round"
                  >
                    <circle cx="12" cy="12" r="10" /><line
                      x1="12"
                      y1="8"
                      x2="12"
                      y2="12"
                    /><line x1="12" y1="16" x2="12.01" y2="16" />
                  </svg>
                  <h4>Stream Connection Error</h4>
                </div>
                <p class="error-body">{error}</p>
                <div class="error-actions">
                  <button onclick={retryLastMessage} class="btn-primary">
                    <svg
                      xmlns="http://www.w3.org/2000/svg"
                      width="14"
                      height="14"
                      viewBox="0 0 24 24"
                      fill="none"
                      stroke="currentColor"
                      stroke-width="2"
                      stroke-linecap="round"
                      stroke-linejoin="round"
                    >
                      <path
                        d="M21.5 2v6h-6M21.34 15.57a10 10 0 1 1-.57-8.38l5.67-5.67"
                      />
                    </svg>
                    <span>Retry Request</span>
                  </button>
                  <button onclick={startNewChat} class="btn-text">Cancel</button
                  >
                </div>
              </div>
            </div>
          {/if}
        </div>
      {/if}
    </div>
  </main>

  <!-- Sticky Bottom Bar -->
  <footer class="input-dock">
    <!-- Float Scroll Button -->
    {#if showScrollButton}
      <button
        onclick={() => {
          autoScroll = true;
          scrollToBottom();
        }}
        class="btn-scroll-bottom animate-spring-slide-in"
      >
        <svg
          xmlns="http://www.w3.org/2000/svg"
          width="14"
          height="14"
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          stroke-width="2"
          stroke-linecap="round"
          stroke-linejoin="round"
        >
          <path d="M12 5v14M5 12l7 7 7-7" />
        </svg>
        <span>Scroll to bottom</span>
      </button>
    {/if}

    <div class="dock-inner">
      <div class="input-wrapper">
        <textarea
          bind:this={textareaRef}
          bind:value={inputText}
          oninput={handleInput}
          onkeydown={handleKeyDown}
          placeholder={isStreaming
            ? "Streaming response, please wait..."
            : "Ask Buddhi AI anything... (Shift + Enter for new line)"}
          disabled={isStreaming}
          rows="1"
          class="chat-textarea"
        ></textarea>

        <button
          onclick={sendMessage}
          disabled={isStreaming || !inputText.trim()}
          class="btn-send"
          aria-label="Send message"
        >
          <svg
            xmlns="http://www.w3.org/2000/svg"
            width="18"
            height="18"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            stroke-width="2.5"
            stroke-linecap="round"
            stroke-linejoin="round"
          >
            <line x1="22" y1="2" x2="11" y2="13" /><polygon
              points="22 2 15 22 11 13 2 9 22 2"
            />
          </svg>
        </button>
      </div>
    </div>
  </footer>
</div>

<style>
  /* App Container Grid Layout */
  .app-container {
    width: 100%;
    height: 100svh;
    display: grid;
    grid-template-rows: 56px 1fr auto;
    background-color: var(--bg);
    overflow: hidden;
  }

  /* Top Navigation */
  .top-nav {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 0 24px;
    border-bottom: 1px solid var(--border);
    background-color: var(--bg);
    z-index: 10;
  }

  .logo-area {
    display: flex;
    align-items: center;
    gap: 6px;
    font-size: 18px;
    letter-spacing: -0.5px;
  }

  .logo-prefix {
    font-weight: 800;
    color: var(--text-h);
  }

  .logo-suffix {
    font-weight: 800;
    color: var(--accent);
  }

  .logo-badge {
    font-size: 10px;
    font-family: var(--mono);
    color: var(--accent);
    border: 1px solid var(--accent);
    padding: 1px 4px;
    border-radius: 2px;
    text-transform: uppercase;
    letter-spacing: 1px;
    font-weight: 600;
  }

  .actions-area {
    display: flex;
    align-items: center;
    gap: 12px;
  }

  /* Chat Viewport and Scrollable Inner Box */
  .chat-viewport {
    width: 100%;
    overflow-y: auto;
    padding: 24px;
    display: flex;
    justify-content: center;
  }

  .chat-inner {
    width: 100%;
    max-width: 800px;
    display: flex;
    flex-direction: column;
  }

  /* Empty State / Welcome Screen */
  .empty-state {
    flex: 1;
    display: flex;
    flex-direction: column;
    justify-content: center;
    padding: 48px 0;
  }

  .empty-branding {
    text-align: center;
    margin-bottom: 48px;
  }

  .empty-branding h1 {
    font-size: 38px;
    font-weight: 700;
    letter-spacing: -1px;
    color: var(--text-h);
    margin: 0 0 12px;
  }

  .empty-branding .subtitle {
    font-size: 15px;
    color: var(--text);
    opacity: 0.85;
    margin: 0;
  }

  .presets-grid {
    margin-top: 16px;
  }

  .presets-title {
    font-size: 12px;
    font-family: var(--mono);
    text-transform: uppercase;
    letter-spacing: 1px;
    color: var(--accent);
    margin-bottom: 16px;
    text-align: center;
    font-weight: 600;
  }

  .presets-list {
    display: grid;
    grid-template-columns: 1fr;
    gap: 12px;
  }

  @media (min-width: 640px) {
    .presets-list {
      grid-template-columns: repeat(3, 1fr);
    }
  }

  .preset-card {
    text-align: left;
    background-color: var(--bubble-user);
    border: 1px solid var(--border);
    border-radius: 2px;
    padding: 16px;
    cursor: pointer;
    transition: all 0.25s cubic-bezier(0.165, 0.84, 0.44, 1);
  }

  .preset-card:hover {
    border-color: var(--accent);
    transform: translateY(-2px);
    box-shadow: rgba(var(--accent-rgb), 0.08) 0 4px 12px;
  }

  .preset-card h3 {
    font-size: 14px;
    font-weight: 600;
    color: var(--text-h);
    margin: 0 0 6px;
  }

  .preset-card p {
    font-size: 12px;
    color: var(--text);
    opacity: 0.8;
    margin: 0;
    line-height: 1.4;
  }

  /* Conversation Rows */
  .message-list {
    display: flex;
    flex-direction: column;
    gap: 24px;
    padding-bottom: 24px;
  }

  .message-row {
    display: flex;
    width: 100%;
  }

  .user-row {
    justify-content: flex-end;
  }

  .agent-row {
    justify-content: flex-start;
    gap: 16px;
    border-bottom: 1px solid var(--border);
    padding-bottom: 24px;
  }

  .agent-avatar {
    width: 32px;
    height: 32px;
    border-radius: 2px;
    background-color: rgba(var(--accent-rgb), 0.1);
    border: 1px solid var(--accent);
    color: var(--accent);
    display: flex;
    align-items: center;
    justify-content: center;
    flex-shrink: 0;
  }

  .message-bubble {
    max-width: 100%;
    position: relative;
  }

  .user-bubble {
    max-width: 80%;
    background-color: var(--bubble-user);
    border: 1px solid var(--border);
    color: var(--bubble-user-text);
    padding: 12px 18px;
    border-radius: 2px;
  }

  .user-meta {
    display: block;
    font-size: 10px;
    font-family: var(--mono);
    text-transform: uppercase;
    color: var(--accent);
    margin-bottom: 4px;
    font-weight: 600;
  }

  .user-content {
    font-size: 15px;
    line-height: 1.5;
    word-break: break-word;
  }

  .agent-bubble {
    flex-grow: 1;
    padding-top: 4px;
  }

  .typing-loading {
    display: flex;
    align-items: center;
    height: 24px;
  }

  /* Thinking Shimmer */
  .thinking-bubble {
    border-radius: 2px;
    padding: 12px 16px;
    min-height: 80px;
  }

  .thinking-text {
    font-size: 12px;
    font-family: var(--mono);
    color: var(--accent);
    margin-bottom: 12px;
  }

  .shimmer-block {
    height: 10px;
    background-color: var(--shimmer-bg);
    margin-bottom: 8px;
    border-radius: 1px;
  }

  .shimmer-block.w-4-5 {
    width: 80%;
  }
  .shimmer-block.w-3-5 {
    width: 60%;
  }

  /* Error Box styling */
  .system-row {
    justify-content: center;
  }

  .error-card {
    width: 100%;
    max-width: 500px;
    background-color: rgba(var(--accent-rgb), 0.04);
    border: 1px dashed var(--accent);
    padding: 20px;
    border-radius: 2px;
    text-align: left;
  }

  .error-header {
    display: flex;
    align-items: center;
    gap: 8px;
    color: var(--accent);
    margin-bottom: 8px;
  }

  .error-header h4 {
    margin: 0;
    font-size: 15px;
    font-weight: 600;
  }

  .error-body {
    font-size: 13px;
    color: var(--text);
    margin: 0 0 16px;
    line-height: 1.5;
  }

  .error-actions {
    display: flex;
    gap: 12px;
    align-items: center;
  }

  /* Bottom Dock & Textarea Form */
  .input-dock {
    border-top: 1px solid var(--border);
    background-color: var(--bg);
    padding: 16px 24px 24px;
    display: flex;
    justify-content: center;
    position: relative;
  }

  .btn-scroll-bottom {
    position: absolute;
    top: -40px;
    left: 50%;
    transform: translateX(-50%);
    background-color: var(--bg);
    border: 1px solid var(--accent);
    color: var(--accent);
    padding: 6px 14px;
    border-radius: 2px;
    font-size: 12px;
    font-family: var(--mono);
    display: flex;
    align-items: center;
    gap: 6px;
    cursor: pointer;
    box-shadow: rgba(0, 0, 0, 0.08) 0 4px 12px;
    transition: all 0.2s ease;
  }

  .btn-scroll-bottom:hover {
    background-color: var(--accent);
    color: var(--bg);
  }

  .dock-inner {
    width: 100%;
    max-width: 800px;
  }

  .input-wrapper {
    display: flex;
    align-items: flex-end;
    background-color: var(--bubble-user);
    border: 1px solid var(--border);
    border-radius: 2px;
    padding: 10px 14px;
    transition: border-color 0.25s ease;
  }

  .input-wrapper:focus-within {
    border-color: var(--accent);
    box-shadow: rgba(var(--accent-rgb), 0.06) 0 0 0 3px;
  }

  .chat-textarea {
    flex-grow: 1;
    background: transparent;
    border: none;
    outline: none;
    color: var(--text);
    font-family: var(--sans);
    font-size: 15px;
    line-height: 1.5;
    resize: none;
    max-height: 180px;
    padding: 2px 8px 2px 0;
  }

  .chat-textarea::placeholder {
    color: var(--text);
    opacity: 0.55;
  }

  /* General Action Buttons */
  .btn-send {
    background: none;
    border: none;
    color: var(--accent);
    cursor: pointer;
    padding: 4px;
    display: flex;
    align-items: center;
    justify-content: center;
    opacity: 0.85;
    transition: all 0.2s ease;
  }

  .btn-send:hover:not(:disabled) {
    opacity: 1;
    transform: scale(1.1);
  }

  .btn-send:disabled {
    color: var(--text);
    opacity: 0.3;
    cursor: not-allowed;
  }

  .btn-secondary {
    background: transparent;
    border: 1px solid var(--border);
    color: var(--text);
    border-radius: 2px;
    padding: 6px 12px;
    font-size: 13px;
    font-family: var(--sans);
    display: flex;
    align-items: center;
    gap: 8px;
    cursor: pointer;
    transition: all 0.25s cubic-bezier(0.165, 0.84, 0.44, 1);
  }

  .btn-secondary:hover {
    border-color: var(--accent);
    color: var(--accent);
    box-shadow: rgba(var(--accent-rgb), 0.04) 0 2px 8px;
  }

  .btn-primary {
    background-color: var(--accent);
    border: 1px solid var(--accent);
    color: var(--bg);
    border-radius: 2px;
    padding: 8px 16px;
    font-size: 13px;
    font-weight: 600;
    display: flex;
    align-items: center;
    gap: 8px;
    cursor: pointer;
    transition: all 0.2s ease;
  }

  .btn-primary:hover {
    background-color: transparent;
    color: var(--accent);
  }

  .btn-text {
    background: transparent;
    border: none;
    color: var(--text);
    opacity: 0.7;
    cursor: pointer;
    font-size: 13px;
    padding: 8px 12px;
  }

  .btn-text:hover {
    opacity: 1;
    color: var(--accent);
  }

  .btn-icon {
    background: transparent;
    border: 1px solid var(--border);
    color: var(--text);
    border-radius: 2px;
    width: 32px;
    height: 32px;
    display: flex;
    align-items: center;
    justify-content: center;
    cursor: pointer;
    transition: all 0.2s ease;
  }

  .btn-icon:hover {
    border-color: var(--accent);
    color: var(--accent);
  }

  /* Micro Utilities */
  .spin-slow {
    animation: spin 8s infinite linear;
  }

  @keyframes spin {
    from {
      transform: rotate(0deg);
    }
    to {
      transform: rotate(360deg);
    }
  }
</style>

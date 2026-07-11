import {
    analyzeCalligraphyStream,
    chatWithAIStream,
    deleteChatSession,
    generateCalligraphy,
    generateLearningPlan,
    getChatSession,
    getChatSessions,
    getCalligraphyStyles,
    getCopybooks,
    saveArtwork,
    uploadCalligraphyImage
} from "./api.js";
import { initGallery } from "./gallery.js";
import { quickQuestions, topics } from "../data/calligraphy.js";

const state = {
    currentRoute: "home",
    conversations: [],
    currentConversationId: null,
    pendingImage: null,
    selectedCopybookId: null,
    selectedStyleId: null,
    styleFilter: "全部"
};

const ALLOWED_IMAGE_TYPES = ["image/png", "image/jpeg", "image/webp"];
const DEFAULT_IMAGE_QUESTION = "请分析这张书法图片";
let galleryController = null;

function $(selector) {
    return document.querySelector(selector);
}

function $all(selector) {
    return Array.from(document.querySelectorAll(selector));
}

function createId() {
    return Date.now().toString(36) + Math.random().toString(36).slice(2);
}

function normalizeSavedMessage(message) {
    return {
        id: String(message.id),
        role: message.role === "human" ? "user" : "assistant",
        content: message.content || "",
        image: null,
        sources: Array.isArray(message.sources) ? message.sources : [],
        timestamp: message.created_at || Date.now()
    };
}

function applySavedConversation(savedConversation) {
    const conversation = {
        id: savedConversation.id,
        title: savedConversation.title || "新对话",
        messages: (savedConversation.messages || []).map(normalizeSavedMessage),
        updatedAt: savedConversation.updated_at || Date.now(),
        persisted: true
    };
    const index = state.conversations.findIndex((item) => item.id === conversation.id);
    if (index === -1) {
        state.conversations.unshift(conversation);
    } else {
        state.conversations[index] = conversation;
    }
    state.currentConversationId = conversation.id;
}

async function openSavedConversation(conversationId) {
    const savedConversation = await getChatSession(conversationId);
    applySavedConversation(savedConversation);
    renderConversationList();
    renderMessages();
}

async function loadSavedConversations() {
    try {
        const savedConversations = await getChatSessions();
        state.conversations = savedConversations.map((conversation) => ({
            id: conversation.id,
            title: conversation.title || "新对话",
            messages: [],
            updatedAt: conversation.updated_at || Date.now(),
            persisted: true
        }));

        if (state.conversations.length > 0) {
            await openSavedConversation(state.conversations[0].id);
            return;
        }
    } catch (error) {
        // The chat remains usable in the frontend's temporary mode if the
        // backend has not started yet.
        console.warn("Saved conversations could not be loaded:", error);
    }

    ensureConversation();
    renderConversationList();
    renderMessages();
}

function showToast(text) {
    const toast = $("#toast");
    toast.textContent = text;
    toast.hidden = false;
    window.clearTimeout(showToast.timer);
    showToast.timer = window.setTimeout(() => {
        toast.hidden = true;
    }, 2600);
}

function routeTo(route) {
    state.currentRoute = ["home", "chat", "learn", "gallery", "create"].includes(route) ? route : "home";

    $all("[data-page]").forEach((page) => {
        page.classList.toggle("is-active", page.dataset.page === state.currentRoute);
    });

    $all("[data-route-link]").forEach((link) => {
        link.classList.toggle("is-active", link.dataset.routeLink === state.currentRoute);
    });

    galleryController?.setActive(state.currentRoute === "gallery");

    $("#siteNav").classList.remove("is-open");
    $("#navToggle").setAttribute("aria-expanded", "false");
    window.scrollTo({ top: 0, behavior: "auto" });
}

function initRouter() {
    $all("[data-route-link]").forEach((link) => {
        link.addEventListener("click", (event) => {
            event.preventDefault();
            const route = link.dataset.routeLink;
            window.location.hash = route;
            routeTo(route);
        });
    });

    $("#navToggle").addEventListener("click", () => {
        const nav = $("#siteNav");
        const isOpen = nav.classList.toggle("is-open");
        $("#navToggle").setAttribute("aria-expanded", String(isOpen));
    });

    window.addEventListener("hashchange", () => {
        routeTo(window.location.hash.replace("#", "") || "home");
    });

    routeTo(window.location.hash.replace("#", "") || "home");
}

function renderHomeCopybooks() {
    const container = $("#homeCopybooks");
    container.innerHTML = getCopybooks()
        .map((copybook) => `
            <button class="copybook-card" type="button" data-copybook-id="${copybook.id}">
                <span class="copybook-card__dynasty">${copybook.dynasty}代</span>
                <span class="copybook-card__author">${copybook.calligrapher}</span>
                <strong>${copybook.name}</strong>
                <span class="copybook-card__style">${copybook.style}</span>
                <p>${copybook.description}</p>
                <span class="copybook-card__action">前往集字创作</span>
            </button>
        `)
        .join("");

    container.addEventListener("click", (event) => {
        const card = event.target.closest("[data-copybook-id]");
        if (!card) return;
        state.selectedCopybookId = card.dataset.copybookId;
        window.location.hash = "create";
        routeTo("create");
        renderCreate();
    });
}

function ensureConversation() {
    if (state.currentConversationId) {
        return state.currentConversationId;
    }

    const id = createId();
    state.conversations.unshift({
        id,
        title: "新对话",
        messages: [],
        updatedAt: Date.now(),
        persisted: false
    });
    state.currentConversationId = id;
    renderConversationList();
    return id;
}

function getCurrentConversation() {
    return state.conversations.find((conversation) => conversation.id === state.currentConversationId);
}

function formatTime(timestamp) {
    const date = new Date(timestamp);
    const hours = String(date.getHours()).padStart(2, "0");
    const minutes = String(date.getMinutes()).padStart(2, "0");
    return `${date.getMonth() + 1}/${date.getDate()} ${hours}:${minutes}`;
}

function renderConversationList() {
    const list = $("#conversationList");
    list.innerHTML = state.conversations
        .map((conversation) => `
            <div class="conversation-row">
                <button class="conversation-item ${conversation.id === state.currentConversationId ? "is-active" : ""}" type="button" data-conversation-id="${conversation.id}">
                    <span>${conversation.title}</span>
                    <small>${formatTime(conversation.updatedAt)}</small>
                </button>
                <button class="conversation-delete" type="button" data-delete-conversation-id="${conversation.id}" aria-label="删除对话：${conversation.title}" title="删除对话">×</button>
            </div>
        `)
        .join("");
}

function createImageButton(image) {
    const button = document.createElement("button");
    button.className = "message__image-button";
    button.type = "button";
    button.dataset.previewSrc = image.src;
    button.dataset.previewAlt = image.filename || "书法图片";
    button.setAttribute("aria-label", "查看图片");

    const img = document.createElement("img");
    img.src = image.src;
    img.alt = image.filename || "书法图片";
    img.loading = "lazy";

    button.appendChild(img);
    return button;
}

function createMessage(role, messageData) {
    const message = document.createElement("article");
    message.className = `message message--${role}`;

    const bubble = document.createElement("div");
    bubble.className = "message__bubble";

    const content = typeof messageData === "string" ? messageData : messageData?.content || "";
    const image = typeof messageData === "object" ? messageData?.image : null;
    const sources = typeof messageData === "object" ? messageData?.sources : null;

    if (content) {
        const text = document.createElement("div");
        text.className = "message__text";
        text.textContent = content;
        bubble.appendChild(text);
    }

    if (image?.src) {
        bubble.appendChild(createImageButton(image));
    }

    if (role === "assistant" && Array.isArray(sources) && sources.length > 0) {
        bubble.appendChild(createSourceList(sources));
    }

    message.appendChild(bubble);
    return message;
}

function createSourceList(sources) {
    const details = document.createElement("details");
    details.className = "message__sources";

    const summary = document.createElement("summary");
    summary.textContent = `参考资料（${sources.length}）`;
    details.appendChild(summary);

    const list = document.createElement("ul");
    sources.forEach((source) => {
        const item = document.createElement("li");
        const title = document.createElement("span");
        title.className = "message__source-title";
        title.textContent = source.title || source.file || "知识库资料";
        item.appendChild(title);

        if (source.file && source.file !== source.title) {
            const file = document.createElement("small");
            file.textContent = source.file;
            item.appendChild(file);
        }

        if (source.content) {
            const excerpt = document.createElement("p");
            excerpt.textContent = source.content;
            item.appendChild(excerpt);
        }

        list.appendChild(item);
    });

    details.appendChild(list);
    return details;
}

function renderMessages(scrollBehavior = "smooth") {
    const conversation = getCurrentConversation();
    const list = $("#messageList");
    const welcome = $("#chatWelcome");
    list.innerHTML = "";

    if (!conversation || conversation.messages.length === 0) {
        welcome.hidden = false;
        return;
    }

    welcome.hidden = true;
    conversation.messages.forEach((message) => {
        list.appendChild(createMessage(message.role, message));
    });
    $("#chatScroll").scrollTo({ top: $("#chatScroll").scrollHeight, behavior: scrollBehavior });
}

function addMessage(role, content, image = null, sources = []) {
    const conversationId = ensureConversation();
    const conversation = getCurrentConversation();
    conversation.messages.push({ id: createId(), role, content, image, sources, timestamp: Date.now() });
    conversation.updatedAt = Date.now();
    if (role === "user" && conversation.title === "新对话") {
        const title = content || image?.filename || "书法图片";
        conversation.title = title.slice(0, 16) + (title.length > 16 ? "..." : "");
    }
    state.currentConversationId = conversationId;
    renderConversationList();
    renderMessages();
    return conversationId;
}

function addStreamingAssistantMessage(placeholder = "正在检索资料…") {
    ensureConversation();
    const conversation = getCurrentConversation();
    const message = {
        id: createId(),
        role: "assistant",
        content: placeholder,
        image: null,
        sources: [],
        pending: true,
        timestamp: Date.now()
    };

    conversation.messages.push(message);
    conversation.updatedAt = Date.now();
    renderConversationList();
    renderMessages("auto");
    return message;
}

function createOfflineImageAnswer(question) {
    return (
        "【前端离线测试模式】当前没有连接到图片上传/分析后端，图片已经按聊天样式显示，方便先测试前端交互。\n\n" +
        `关于“${question || DEFAULT_IMAGE_QUESTION}”，正式接入后这里会返回书法图片的章法、结构、用笔和练习建议。`
    );
}

function setChatLoading(isLoading) {
    const sendButton = $("#sendButton");
    const imageButton = $("#imageUploadButton");
    sendButton.disabled = isLoading;
    sendButton.textContent = isLoading ? "思考中" : "发送";
    imageButton.disabled = isLoading;
}

function resizeComposer() {
    const input = $("#messageInput");
    input.style.height = "auto";
    input.style.height = `${Math.min(input.scrollHeight, 150)}px`;
}

function renderPendingImage() {
    const preview = $("#composerPreview");
    preview.innerHTML = "";

    if (!state.pendingImage) {
        preview.hidden = true;
        return;
    }

    const img = document.createElement("img");
    img.src = state.pendingImage.src;
    img.alt = state.pendingImage.filename;

    const name = document.createElement("span");
    name.textContent = state.pendingImage.filename;

    const removeButton = document.createElement("button");
    removeButton.type = "button";
    removeButton.textContent = "移除";
    removeButton.setAttribute("aria-label", "移除待发送图片");
    removeButton.addEventListener("click", () => {
        clearPendingImage();
        $("#messageInput").focus();
    });

    preview.append(img, name, removeButton);
    preview.hidden = false;
}

function clearPendingImage(options = {}) {
    const { keepObjectUrl = false } = options;
    if (state.pendingImage && !keepObjectUrl) {
        URL.revokeObjectURL(state.pendingImage.src);
    }
    state.pendingImage = null;
    renderPendingImage();
}

function setPendingImage(file) {
    if (!ALLOWED_IMAGE_TYPES.includes(file.type)) {
        showToast("请上传 PNG、JPG 或 WebP 图片。");
        return;
    }

    clearPendingImage();
    state.pendingImage = {
        file,
        filename: file.name || "书法图片",
        src: URL.createObjectURL(file)
    };
    renderPendingImage();
    showToast("图片已加入本次提问。");
}

function openImageViewer(src, alt) {
    const viewer = $("#imageViewer");
    const img = $("#imageViewerImg");
    img.src = src;
    img.alt = alt || "书法图片";
    viewer.hidden = false;
    $("#imageViewerClose").focus();
}

function closeImageViewer() {
    const viewer = $("#imageViewer");
    const img = $("#imageViewerImg");
    viewer.hidden = true;
    img.removeAttribute("src");
    img.alt = "";
}

async function initChat() {
    renderConversationList();
    renderMessages();
    await loadSavedConversations();

    $("#quickChips").innerHTML = quickQuestions
        .map((question) => `<button type="button" data-question="${question}">${question}</button>`)
        .join("");

    $("#topicTags").innerHTML = topics
        .map((topic) => `<button type="button" data-question="${topic}">${topic}</button>`)
        .join("");

    $("#newChatButton").addEventListener("click", () => {
        state.currentConversationId = null;
        ensureConversation();
        renderConversationList();
        renderMessages();
    });

    $("#conversationList").addEventListener("click", async (event) => {
        const deleteButton = event.target.closest("[data-delete-conversation-id]");
        if (deleteButton) {
            const conversationId = deleteButton.dataset.deleteConversationId;
            const conversation = state.conversations.find((item) => item.id === conversationId);
            if (!conversation) return;

            const confirmed = window.confirm(`确定删除“${conversation.title}”吗？删除后无法恢复。`);
            if (!confirmed) return;

            try {
                if (conversation.persisted) {
                    await deleteChatSession(conversationId);
                }

                const wasCurrent = state.currentConversationId === conversationId;
                state.conversations = state.conversations.filter((item) => item.id !== conversationId);
                if (wasCurrent) {
                    state.currentConversationId = null;
                    if (state.conversations.length > 0) {
                        const nextConversation = state.conversations[0];
                        if (nextConversation.persisted) {
                            await openSavedConversation(nextConversation.id);
                        } else {
                            state.currentConversationId = nextConversation.id;
                        }
                    } else {
                        ensureConversation();
                    }
                }
                renderConversationList();
                renderMessages();
                showToast("对话已删除。");
            } catch (error) {
                showToast("删除失败，请检查后端服务后重试。");
            }
            return;
        }

        const item = event.target.closest("[data-conversation-id]");
        if (!item) return;
        if (item.dataset.conversationId === state.currentConversationId) return;
        try {
            await openSavedConversation(item.dataset.conversationId);
        } catch (error) {
            showToast("历史对话加载失败，请检查后端服务。");
        }
    });

    document.body.addEventListener("click", (event) => {
        const questionButton = event.target.closest("[data-question]");
        if (!questionButton) return;
        $("#messageInput").value = questionButton.dataset.question;
        resizeComposer();
        $("#messageInput").focus();
    });

    $("#messageInput").addEventListener("input", resizeComposer);
    $("#messageInput").addEventListener("keydown", (event) => {
        if (event.key === "Enter" && !event.shiftKey) {
            event.preventDefault();
            $("#composer").requestSubmit();
        }
    });

    $("#imageUploadButton").addEventListener("click", () => {
        $("#imageUploadInput").click();
    });

    $("#imageUploadInput").addEventListener("change", (event) => {
        const [file] = event.target.files;
        event.target.value = "";
        if (!file) return;

        setPendingImage(file);
    });

    $("#messageList").addEventListener("click", (event) => {
        const imageButton = event.target.closest("[data-preview-src]");
        if (!imageButton) return;
        openImageViewer(imageButton.dataset.previewSrc, imageButton.dataset.previewAlt);
    });

    $("#imageViewer").addEventListener("click", (event) => {
        if (event.target.id === "imageViewer" || event.target.id === "imageViewerClose") {
            closeImageViewer();
        }
    });

    document.addEventListener("keydown", (event) => {
        if (event.key === "Escape" && !$("#imageViewer").hidden) {
            closeImageViewer();
        }
    });

    $("#composer").addEventListener("submit", async (event) => {
        event.preventDefault();
        const input = $("#messageInput");
        const message = input.value.trim();
        const pendingImage = state.pendingImage;

        if (!message && !pendingImage) {
            showToast("请先输入书法问题或上传作品。");
            return;
        }

        setChatLoading(true);

        try {
            if (pendingImage) {
                const image = {
                    src: pendingImage.src,
                    filename: pendingImage.filename
                };
                const question = message || DEFAULT_IMAGE_QUESTION;
                input.value = "";
                resizeComposer();
                addMessage("user", message, image);
                clearPendingImage({ keepObjectUrl: true });
                const assistantMessage = addStreamingAssistantMessage("正在分析图片…");

                try {
                    const uploadData = await uploadCalligraphyImage(pendingImage.file);
                    const data = await analyzeCalligraphyStream({
                        uploadId: uploadData.uploadId,
                        imageUrl: uploadData.imageUrl,
                        question
                    }, {
                        onChunk(chunk) {
                            if (assistantMessage.pending) {
                                assistantMessage.content = "";
                                assistantMessage.pending = false;
                            }
                            assistantMessage.content += chunk;
                            renderMessages("auto");
                        }
                    });

                    if (assistantMessage.pending) {
                        assistantMessage.content = data.answer || "图片分析完成，但没有返回具体内容。";
                        assistantMessage.pending = false;
                    }
                    renderMessages("auto");
                } catch (error) {
                    assistantMessage.pending = false;
                    if (error instanceof TypeError) {
                        assistantMessage.content = createOfflineImageAnswer(question);
                        showToast("后端未连接，已使用前端离线测试回复。");
                    } else {
                        assistantMessage.content = `图片分析失败：${error.message || "请稍后重试。"}`;
                        showToast(error.message || "图片分析失败，请稍后重试。");
                    }
                    renderMessages("auto");
                }
            } else {
                input.value = "";
                resizeComposer();
                const conversationId = addMessage("user", message);
                const assistantMessage = addStreamingAssistantMessage();

                try {
                    const data = await chatWithAIStream(message, conversationId, {
                        onSources(sources) {
                            assistantMessage.sources = sources;
                            renderMessages("auto");
                        },
                        onChunk(chunk) {
                            if (assistantMessage.pending) {
                                assistantMessage.content = "";
                                assistantMessage.pending = false;
                            }
                            assistantMessage.content += chunk;
                            renderMessages("auto");
                        }
                    });

                    if (assistantMessage.pending) {
                        assistantMessage.content = data.answer || "根据现有资料无法回答。";
                        assistantMessage.pending = false;
                    }
                    assistantMessage.sources = data.sources || assistantMessage.sources;
                    if (!data.offline) {
                        getCurrentConversation().persisted = true;
                    }
                    renderMessages("auto");
                } catch (streamError) {
                    if (assistantMessage.pending) {
                        assistantMessage.content = "抱歉，当前无法完成回答，请稍后重试。";
                        assistantMessage.pending = false;
                        renderMessages("auto");
                    }
                    throw streamError;
                }
            }
        } catch (error) {
            showToast(error.message || "连接失败，请检查后端服务。");
        } finally {
            setChatLoading(false);
        }
    });
}

function renderCopybookTabs() {
    const styles = ["全部", ...new Set(getCopybooks().map((copybook) => copybook.style))];
    $("#copybookTabs").innerHTML = styles
        .map((style) => `
            <button class="${state.styleFilter === style ? "is-active" : ""}" type="button" data-style-filter="${style}">
                ${style}
            </button>
        `)
        .join("");
}

function renderCopybookList() {
    const copybooks = getCopybooks().filter((copybook) => {
        return state.styleFilter === "全部" || copybook.style === state.styleFilter;
    });

    if (!state.selectedCopybookId && copybooks.length > 0) {
        state.selectedCopybookId = copybooks[0].id;
    }

    $("#copybookList").innerHTML = copybooks
        .map((copybook) => `
            <button class="choice-card ${state.selectedCopybookId === copybook.id ? "is-active" : ""}" type="button" data-select-copybook="${copybook.id}">
                <strong>${copybook.calligrapher} · ${copybook.name}</strong>
                <span>${copybook.dynasty} · ${copybook.style}</span>
            </button>
        `)
        .join("");
}

function renderCharacters() {
    const copybook = getCopybooks().find((item) => item.id === state.selectedCopybookId);
    $("#characterGrid").innerHTML = copybook
        ? copybook.characters.map((char) => `<button type="button" data-character="${char}">${char}</button>`).join("")
        : `<p class="muted">请选择字帖</p>`;
}

function renderStyles() {
    if (!state.selectedStyleId) {
        state.selectedStyleId = getCalligraphyStyles()[0]?.id || null;
    }

    $("#styleList").innerHTML = getCalligraphyStyles()
        .map((style) => `
            <button class="choice-card ${state.selectedStyleId === style.id ? "is-active" : ""}" type="button" data-select-style="${style.id}">
                <strong>${style.name}</strong>
                <span>${style.dynasty} · ${style.calligrapher} · ${style.style}</span>
            </button>
        `)
        .join("");
}

function renderCreateStatus() {
    const copybook = getCopybooks().find((item) => item.id === state.selectedCopybookId);
    const style = getCalligraphyStyles().find((item) => item.id === state.selectedStyleId);
    $("#createStatus").textContent = `当前风格：${style ? `${style.name} · ${style.calligrapher}` : "未选择"} · 当前字帖：${copybook ? `${copybook.calligrapher}《${copybook.name}》` : "未选择"}`;
}

function renderCreate() {
    renderCopybookTabs();
    renderCopybookList();
    renderCharacters();
    renderStyles();
    renderCreateStatus();
}

function renderLearningPlan(data) {
    $("#learningPlanText").textContent = data.plan || "暂时无法生成学习路径。";

    const sourcesContainer = $("#learningPlanSources");
    sourcesContainer.replaceChildren();
    if (Array.isArray(data.sources) && data.sources.length > 0) {
        sourcesContainer.appendChild(createSourceList(data.sources));
    }

    $("#learningPlanResult").hidden = false;
}

function initLearning() {
    const form = $("#learningPlanForm");
    const submitButton = $("#learningPlanSubmit");

    form.addEventListener("submit", async (event) => {
        event.preventDefault();
        const dailyMinutes = Number($("#learningMinutes").value);
        if (!Number.isInteger(dailyMinutes) || dailyMinutes < 10 || dailyMinutes > 180) {
            showToast("每日练习时间请填写 10 到 180 分钟。");
            return;
        }

        submitButton.disabled = true;
        submitButton.textContent = "正在生成…";
        try {
            const data = await generateLearningPlan({
                level: $("#learningLevel").value,
                style: $("#learningStyle").value,
                daily_minutes: dailyMinutes,
                goal: $("#learningGoal").value.trim()
            });
            renderLearningPlan(data);
        } catch (error) {
            showToast(error.message || "学习路径生成失败，请检查后端服务。");
        } finally {
            submitButton.disabled = false;
            submitButton.textContent = "生成学习路径";
        }
    });
}

function initCreate() {
    renderCreate();

    $("#copybookTabs").addEventListener("click", (event) => {
        const tab = event.target.closest("[data-style-filter]");
        if (!tab) return;
        state.styleFilter = tab.dataset.styleFilter;
        state.selectedCopybookId = null;
        renderCreate();
    });

    $("#copybookList").addEventListener("click", (event) => {
        const item = event.target.closest("[data-select-copybook]");
        if (!item) return;
        state.selectedCopybookId = item.dataset.selectCopybook;
        renderCreate();
    });

    $("#styleList").addEventListener("click", (event) => {
        const item = event.target.closest("[data-select-style]");
        if (!item) return;
        state.selectedStyleId = item.dataset.selectStyle;
        renderCreate();
    });

    $("#characterGrid").addEventListener("click", (event) => {
        const item = event.target.closest("[data-character]");
        if (!item) return;
        const input = $("#createTextInput");
        input.value += item.dataset.character;
        input.focus();
    });

    $("#generateButton").addEventListener("click", async () => {
        const text = $("#createTextInput").value.trim();
        if (!text) {
            showToast("请先输入创作文字。");
            return;
        }

        const result = await generateCalligraphy({
            text,
            styleId: state.selectedStyleId,
            copybookId: state.selectedCopybookId
        });
        showToast(result.message);
    });

    $("#saveArtworkButton").addEventListener("click", async () => {
        const result = await saveArtwork({
            title: $("#createTextInput").value.trim(),
            imageUrl: "",
            styleId: state.selectedStyleId,
            copybookId: state.selectedCopybookId
        });
        showToast(result.message);
    });
}

document.addEventListener("DOMContentLoaded", async () => {
    renderHomeCopybooks();
    await initChat();
    initLearning();
    initCreate();
    galleryController = initGallery();
    initRouter();
});

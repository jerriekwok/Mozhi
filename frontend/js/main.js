import {
    analyzeCalligraphyStream,
    chatWithAIStream,
    deleteChatSession,
    generateLearningPlan,
    getChatSession,
    getChatSessions,
    getCalligraphyStyles,
    getCopybooks,
    searchGlyphs,
    uploadCalligraphyImage
} from "./api.js";
import { drawArtworkPreview, exportArtworkPng } from "./features/create/artwork_renderer.js";
import { createSourceList, renderChatMessages, updateStreamingMessage } from "./features/chat/message_view.js";
import { initGallery } from "./gallery.js";
import { $, $all, showToast } from "./shared/dom.js";
import { quickQuestions, topics } from "../data/calligraphy.js";

const state = {
    currentRoute: "home",
    conversations: [],
    currentConversationId: null,
    pendingImage: null,
    selectedCopybookId: null,
    selectedStyleId: null,
    styleFilter: "全部",
    glyphCharacters: [],
    glyphSelections: [],
    glyphTransforms: [],
    selectedGlyphIndex: null
};

const ALLOWED_IMAGE_TYPES = ["image/png", "image/jpeg", "image/webp"];
const DEFAULT_IMAGE_QUESTION = "请分析这张书法图片";
const BACKEND_ORIGIN = "http://127.0.0.1:8000";
let galleryController = null;
let glyphArtworkVersion = 0;
let activeGlyphDrag = null;
const GLYPH_GRID_SIZE = 12;
const GLYPH_CENTER_SNAP_DISTANCE = 9;

function createId() {
    return Date.now().toString(36) + Math.random().toString(36).slice(2);
}

function normalizeSavedMessage(message) {
    return {
        id: String(message.id),
        role: message.role === "human" ? "user" : "assistant",
        content: message.content || "",
        image: message.image_url
            ? { src: `${BACKEND_ORIGIN}${message.image_url}`, filename: "已上传书法图片" }
            : null,
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

function renderMessages(scrollBehavior = "smooth") {
    renderChatMessages(getCurrentConversation(), scrollBehavior);
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

function updateStreamingAssistantMessage(message) {
    // A reply may still be streaming after the user switches to another
    // conversation. Keep updating its data, but never redraw the conversation
    // currently being viewed with a message from the previous one.
    const owner = state.conversations.find((conversation) =>
        conversation.messages.some((item) => item.id === message.id)
    );
    if (!owner || state.currentConversationId !== owner.id) return;
    if (!updateStreamingMessage(message)) renderMessages("auto");
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
                const conversationId = addMessage("user", message || question, image);
                clearPendingImage({ keepObjectUrl: true });
                const assistantMessage = addStreamingAssistantMessage("正在分析图片…");

                try {
                    const uploadData = await uploadCalligraphyImage(pendingImage.file);
                    const data = await analyzeCalligraphyStream({
                        uploadId: uploadData.uploadId,
                        imageUrl: uploadData.imageUrl,
                        question,
                        sessionId: conversationId
                    }, {
                        onChunk(chunk) {
                            if (assistantMessage.pending) {
                                assistantMessage.content = "";
                                assistantMessage.pending = false;
                            }
                            assistantMessage.content += chunk;
                            updateStreamingAssistantMessage(assistantMessage);
                        },
                        onDone(sessionId) {
                            if (!sessionId) return;
                            const conversation = state.conversations.find((item) => item.id === conversationId);
                            if (conversation) {
                                conversation.id = sessionId;
                                conversation.persisted = true;
                                if (state.currentConversationId === conversationId) {
                                    state.currentConversationId = sessionId;
                                }
                                renderConversationList();
                            }
                        }
                    });

                    if (assistantMessage.pending) {
                        assistantMessage.content = data.answer || "图片分析完成，但没有返回具体内容。";
                        assistantMessage.pending = false;
                    }
                    updateStreamingAssistantMessage(assistantMessage);
                } catch (error) {
                    assistantMessage.pending = false;
                    if (error instanceof TypeError) {
                        assistantMessage.content = createOfflineImageAnswer(question);
                        showToast("后端未连接，已使用前端离线测试回复。");
                    } else {
                        assistantMessage.content = `图片分析失败：${error.message || "请稍后重试。"}`;
                        showToast(error.message || "图片分析失败，请稍后重试。");
                    }
                    updateStreamingAssistantMessage(assistantMessage);
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
                            if (state.currentConversationId === conversationId) renderMessages("auto");
                        },
                        onChunk(chunk) {
                            if (assistantMessage.pending) {
                                assistantMessage.content = "";
                                assistantMessage.pending = false;
                            }
                            assistantMessage.content += chunk;
                            updateStreamingAssistantMessage(assistantMessage);
                        }
                    });

                    if (assistantMessage.pending) {
                        assistantMessage.content = data.answer || "根据现有资料无法回答。";
                        assistantMessage.pending = false;
                    }
                    assistantMessage.sources = data.sources || assistantMessage.sources;
                    if (!data.offline) {
                        const conversation = state.conversations.find((item) => item.id === conversationId);
                        if (conversation) conversation.persisted = true;
                    }
                    updateStreamingAssistantMessage(assistantMessage);
                } catch (streamError) {
                    if (assistantMessage.pending) {
                        assistantMessage.content = "抱歉，当前无法完成回答，请稍后重试。";
                        assistantMessage.pending = false;
                        updateStreamingAssistantMessage(assistantMessage);
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

function renderSamplePhrases() {
    const copybook = getCopybooks().find((item) => item.id === state.selectedCopybookId);
    const phrases = copybook?.phrases || [];
    $("#samplePhraseList").innerHTML = phrases
        .map((phrase) => `<button class="sample-phrase" type="button" data-sample-phrase="${phrase}">${phrase}</button>`)
        .join("");
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
    const found = state.glyphCharacters.filter((item) => item.candidates.length > 0).length;
    const missing = state.glyphCharacters.filter((item) => item.candidates.length === 0).map((item) => item.character);
    const glyphStatus = state.glyphCharacters.length > 0
        ? ` · 已找到 ${found}/${state.glyphCharacters.length} 字${missing.length ? ` · 缺字：${missing.join("、")}` : ""} · 已自动裁白边并统一视觉大小`
        : "";
    $("#createStatus").textContent = `当前风格：${style ? `${style.name} · ${style.calligrapher}` : "未选择"} · 当前字帖：${copybook ? `${copybook.calligrapher}《${copybook.name}》` : "未选择"}${glyphStatus}`;
}

function renderArtboard() {
    const artboard = $("#artboard");
    const version = ++glyphArtworkVersion;
    if (state.glyphCharacters.length === 0) {
        artboard.innerHTML = `
            <div class="empty-art">
                <span class="seal">集</span>
                <h2>集字创作预览区</h2>
                <p>选择字帖后输入文字，系统会从本地字库查找真实单字并自动竖排。</p>
            </div>
        `;
        syncGlyphEditor();
        return;
    }

    artboard.innerHTML = `
        <div class="glyph-artwork" aria-label="集字作品预览">
            ${state.glyphCharacters.map((item, index) => {
                const candidate = item.candidates[state.glyphSelections[index] || 0];
                return candidate
                    ? `
                        <div class="glyph-artwork__item ${state.selectedGlyphIndex === index ? "is-selected" : ""}" data-artwork-glyph-index="${index}" title="${item.character} · ${candidate.artist}">
                            <canvas class="glyph-artwork__canvas" width="480" height="480" data-glyph-artwork-index="${index}" aria-label="${item.character}"></canvas>
                        </div>
                    `
                    : `<span class="glyph-artwork__missing">缺${item.character}</span>`;
            }).join("")}
        </div>
    `;

    requestAnimationFrame(() => layoutGlyphArtwork(artboard));
    void drawArtworkPreview({
        artboard,
        version,
        getCurrentVersion: () => glyphArtworkVersion,
        glyphCharacters: state.glyphCharacters,
        glyphSelections: state.glyphSelections
    });
    syncGlyphEditor();
}

function defaultGlyphTransform() {
    return { x: 0, y: 0, scale: 1, rotation: 0 };
}

function ensureGlyphTransforms() {
    state.glyphTransforms = state.glyphCharacters.map(
        (_, index) => state.glyphTransforms[index] || defaultGlyphTransform()
    );
}

function getGlyphTransform(index) {
    ensureGlyphTransforms();
    return state.glyphTransforms[index];
}

function applyGlyphTransform(index) {
    const item = document.querySelector(`[data-artwork-glyph-index="${index}"]`);
    if (!item) return;
    const transform = getGlyphTransform(index);
    item.style.transform = `translate(-50%, -50%) translate(${transform.x}px, ${transform.y}px) scale(${transform.scale}) rotate(${transform.rotation}deg)`;
    item.classList.toggle("is-selected", state.selectedGlyphIndex === index);
}

function clearArtworkSelection() {
    state.selectedGlyphIndex = null;
    document.querySelectorAll("[data-artwork-glyph-index]").forEach((item) => {
        item.classList.remove("is-selected");
    });
    document.querySelector(".glyph-artwork")?.classList.remove("is-editing");
    syncGlyphEditor();
}

function snapGlyphOffset(value) {
    if (Math.abs(value) <= GLYPH_CENTER_SNAP_DISTANCE) return 0;
    return Math.round(value / GLYPH_GRID_SIZE) * GLYPH_GRID_SIZE;
}

function layoutGlyphArtwork(artboard) {
    const artwork = artboard.querySelector(".glyph-artwork");
    if (!artwork || state.glyphCharacters.length === 0) return;
    const height = artwork.clientHeight;
    const width = artwork.clientWidth;
    if (!height || !width) return;

    const size = Math.min(width * 0.72, Math.max(72, (height - 16) / state.glyphCharacters.length * 0.92));
    state.glyphCharacters.forEach((_, index) => {
        const item = artwork.querySelector(`[data-artwork-glyph-index="${index}"]`);
        if (!item) return;
        item.style.setProperty("--glyph-size", `${size}px`);
        item.style.left = "50%";
        item.style.top = `${((index + 0.5) / state.glyphCharacters.length) * 100}%`;
        applyGlyphTransform(index);
    });
}

function syncGlyphEditor() {
    const editor = $("#glyphEditor");
    const index = state.selectedGlyphIndex;
    const character = index === null ? null : state.glyphCharacters[index]?.character;
    editor.hidden = !character;
    if (!character) return;
    const transform = getGlyphTransform(index);
    $("#glyphEditHint").textContent = `正在调整“${character}”：拖动移动，滚轮缩放`;
    $("#glyphRotation").value = String(transform.rotation);
}

function selectArtworkGlyph(index) {
    state.selectedGlyphIndex = index;
    applyGlyphTransform(index);
    document.querySelectorAll("[data-artwork-glyph-index]").forEach((item) => {
        const itemIndex = Number(item.dataset.artworkGlyphIndex);
        item.classList.toggle("is-selected", itemIndex === index);
    });
    document.querySelector(".glyph-artwork")?.classList.add("is-editing");
    syncGlyphEditor();
}

function resetGlyphLayout() {
    state.glyphTransforms = state.glyphCharacters.map(() => defaultGlyphTransform());
    state.selectedGlyphIndex = null;
    renderArtboard();
}

function renderCreate() {
    renderCopybookTabs();
    renderCopybookList();
    renderSamplePhrases();
    renderStyles();
    renderArtboard();
    renderCreateStatus();
    $("#exportArtworkButton").disabled = state.glyphCharacters.length === 0;
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
        state.glyphCharacters = [];
        state.glyphSelections = [];
        state.glyphTransforms = [];
        state.selectedGlyphIndex = null;
        renderCreate();
    });

    $("#copybookList").addEventListener("click", (event) => {
        const item = event.target.closest("[data-select-copybook]");
        if (!item) return;
        state.selectedCopybookId = item.dataset.selectCopybook;
        state.glyphCharacters = [];
        state.glyphSelections = [];
        state.glyphTransforms = [];
        state.selectedGlyphIndex = null;
        renderCreate();
    });

    $("#styleList").addEventListener("click", (event) => {
        const item = event.target.closest("[data-select-style]");
        if (!item) return;
        state.selectedStyleId = item.dataset.selectStyle;
        const style = getCalligraphyStyles().find((entry) => entry.id === state.selectedStyleId);
        if (style) {
            state.styleFilter = style.style;
            const matchingCopybook = getCopybooks().find(
                (copybook) => copybook.calligrapher === style.calligrapher
            );
            state.selectedCopybookId = matchingCopybook?.id || null;
        }
        state.glyphCharacters = [];
        state.glyphSelections = [];
        state.glyphTransforms = [];
        state.selectedGlyphIndex = null;
        renderCreate();
    });

    $("#samplePhraseList").addEventListener("click", (event) => {
        const phrase = event.target.closest("[data-sample-phrase]");
        if (!phrase) return;
        const input = $("#createTextInput");
        input.value = phrase.dataset.samplePhrase;
        input.focus();
        showToast("已填入字帖推荐字句。");
    });

    const artboard = $("#artboard");
    artboard.addEventListener("pointerdown", (event) => {
        const item = event.target.closest("[data-artwork-glyph-index]");
        if (!item) {
            clearArtworkSelection();
            return;
        }
        const index = Number(item.dataset.artworkGlyphIndex);
        const transform = getGlyphTransform(index);
        selectArtworkGlyph(index);
        activeGlyphDrag = {
            index,
            pointerId: event.pointerId,
            startX: event.clientX,
            startY: event.clientY,
            originX: transform.x,
            originY: transform.y
        };
        item.setPointerCapture(event.pointerId);
        event.preventDefault();
    });

    artboard.addEventListener("pointermove", (event) => {
        if (!activeGlyphDrag || activeGlyphDrag.pointerId !== event.pointerId) return;
        const transform = getGlyphTransform(activeGlyphDrag.index);
        transform.x = snapGlyphOffset(activeGlyphDrag.originX + event.clientX - activeGlyphDrag.startX);
        transform.y = snapGlyphOffset(activeGlyphDrag.originY + event.clientY - activeGlyphDrag.startY);
        applyGlyphTransform(activeGlyphDrag.index);
    });

    const finishGlyphDrag = (event) => {
        if (!activeGlyphDrag || activeGlyphDrag.pointerId !== event.pointerId) return;
        const item = event.target.closest("[data-artwork-glyph-index]");
        if (item?.hasPointerCapture(event.pointerId)) item.releasePointerCapture(event.pointerId);
        activeGlyphDrag = null;
    };
    artboard.addEventListener("pointerup", finishGlyphDrag);
    artboard.addEventListener("pointercancel", finishGlyphDrag);

    artboard.addEventListener("wheel", (event) => {
        const item = event.target.closest("[data-artwork-glyph-index]");
        if (!item) return;
        const index = Number(item.dataset.artworkGlyphIndex);
        const transform = getGlyphTransform(index);
        transform.scale = Math.max(0.65, Math.min(1.55, transform.scale + (event.deltaY < 0 ? 0.05 : -0.05)));
        selectArtworkGlyph(index);
        applyGlyphTransform(index);
        event.preventDefault();
    }, { passive: false });

    $("#glyphScaleDown").addEventListener("click", () => {
        if (state.selectedGlyphIndex === null) return;
        const transform = getGlyphTransform(state.selectedGlyphIndex);
        transform.scale = Math.max(0.65, transform.scale - 0.05);
        applyGlyphTransform(state.selectedGlyphIndex);
    });
    $("#glyphScaleUp").addEventListener("click", () => {
        if (state.selectedGlyphIndex === null) return;
        const transform = getGlyphTransform(state.selectedGlyphIndex);
        transform.scale = Math.min(1.55, transform.scale + 0.05);
        applyGlyphTransform(state.selectedGlyphIndex);
    });
    $("#glyphRotation").addEventListener("input", (event) => {
        if (state.selectedGlyphIndex === null) return;
        getGlyphTransform(state.selectedGlyphIndex).rotation = Number(event.target.value);
        applyGlyphTransform(state.selectedGlyphIndex);
    });
    $("#glyphResetCurrent").addEventListener("click", () => {
        if (state.selectedGlyphIndex === null) return;
        state.glyphTransforms[state.selectedGlyphIndex] = defaultGlyphTransform();
        applyGlyphTransform(state.selectedGlyphIndex);
        syncGlyphEditor();
    });
    $("#glyphResetLayout").addEventListener("click", resetGlyphLayout);

    $("#generateButton").addEventListener("click", async () => {
        const text = $("#createTextInput").value.trim();
        if (!text) {
            showToast("请先输入创作文字。");
            return;
        }

        const copybook = getCopybooks().find((item) => item.id === state.selectedCopybookId);
        const button = $("#generateButton");
        if (!copybook?.glyphSource) {
            showToast("请先选择已接入本地字库的字帖。");
            return;
        }

        button.disabled = true;
        button.textContent = "正在查字…";
        try {
            const result = await searchGlyphs(text, copybook.glyphSource);
            state.glyphCharacters = result.characters || [];
            state.glyphSelections = state.glyphCharacters.map(() => 0);
            state.glyphTransforms = state.glyphCharacters.map(() => defaultGlyphTransform());
            state.selectedGlyphIndex = null;
            renderCreate();
            if (result.missing_characters?.length) {
                showToast(`已生成可用字形，缺字：${result.missing_characters.join("、")}`);
            }
        } catch (error) {
            showToast(error.message || "字库查询失败，请检查后端服务。");
        } finally {
            button.disabled = false;
            button.textContent = "开始集字";
        }
    });

    $("#exportArtworkButton").addEventListener("click", async () => {
        const button = $("#exportArtworkButton");
        button.disabled = true;
        button.textContent = "正在导出…";
        try {
            await exportArtworkPng({
                artboard: $("#artboard"),
                glyphCharacters: state.glyphCharacters,
                glyphSelections: state.glyphSelections,
                getGlyphTransform,
                title: $("#createTextInput").value
            });
            showToast("已导出 1800 × 2400 PNG。");
        } catch (error) {
            showToast(error.message || "导出失败，请稍后重试。");
        } finally {
            button.disabled = state.glyphCharacters.length === 0;
            button.textContent = "导出 PNG";
        }
    });
}

document.addEventListener("DOMContentLoaded", () => {
    renderHomeCopybooks();
    initRouter();
    initLearning();
    initCreate();

    try {
        galleryController = initGallery();
        galleryController?.setActive(state.currentRoute === "gallery");
    } catch (error) {
        console.error("Gallery initialization failed:", error);
        showToast("文化展馆暂时无法加载，其他功能仍可正常使用。");
    }

    void initChat().catch((error) => {
        console.error("Chat initialization failed:", error);
        showToast("聊天记录暂时无法加载，请检查后端服务。");
    });
});

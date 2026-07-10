import {
    analyzeCalligraphy,
    chatWithAI,
    generateCalligraphy,
    getCalligraphyStyles,
    getCopybooks,
    saveArtwork,
    uploadCalligraphyImage
} from "./api.js";
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

function $(selector) {
    return document.querySelector(selector);
}

function $all(selector) {
    return Array.from(document.querySelectorAll(selector));
}

function createId() {
    return Date.now().toString(36) + Math.random().toString(36).slice(2);
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
    state.currentRoute = ["home", "chat", "create"].includes(route) ? route : "home";

    $all("[data-page]").forEach((page) => {
        page.classList.toggle("is-active", page.dataset.page === state.currentRoute);
    });

    $all("[data-route-link]").forEach((link) => {
        link.classList.toggle("is-active", link.dataset.routeLink === state.currentRoute);
    });

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
        updatedAt: Date.now()
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
            <button class="conversation-item ${conversation.id === state.currentConversationId ? "is-active" : ""}" type="button" data-conversation-id="${conversation.id}">
                <span>${conversation.title}</span>
                <small>${formatTime(conversation.updatedAt)}</small>
            </button>
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

    if (content) {
        const text = document.createElement("div");
        text.className = "message__text";
        text.textContent = content;
        bubble.appendChild(text);
    }

    if (image?.src) {
        bubble.appendChild(createImageButton(image));
    }

    message.appendChild(bubble);
    return message;
}

function renderMessages() {
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
    $("#chatScroll").scrollTo({ top: $("#chatScroll").scrollHeight, behavior: "smooth" });
}

function addMessage(role, content, image = null) {
    const conversationId = ensureConversation();
    const conversation = getCurrentConversation();
    conversation.messages.push({ id: createId(), role, content, image, timestamp: Date.now() });
    conversation.updatedAt = Date.now();
    if (role === "user" && conversation.title === "新对话") {
        const title = content || image?.filename || "书法图片";
        conversation.title = title.slice(0, 16) + (title.length > 16 ? "..." : "");
    }
    state.currentConversationId = conversationId;
    renderConversationList();
    renderMessages();
}

function formatAnalysisAnswer(data) {
    const suggestions = Array.isArray(data.suggestions) && data.suggestions.length > 0
        ? `\n\n练习建议：\n${data.suggestions.map((item, index) => `${index + 1}. ${item}`).join("\n")}`
        : "";
    const analysis = data.analysis
        ? `\n\n具体分析：\n章法：${data.analysis.composition}\n结构：${data.analysis.structure}\n用笔：${data.analysis.strokes}`
        : "";
    return `图片分析结果（${data.style || "书法"} · ${data.score ?? "-"}分）\n\n${data.summary || "已完成图片分析。"}${analysis}${suggestions}`;
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

function initChat() {
    ensureConversation();
    renderConversationList();
    renderMessages();

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

    $("#conversationList").addEventListener("click", (event) => {
        const item = event.target.closest("[data-conversation-id]");
        if (!item) return;
        state.currentConversationId = item.dataset.conversationId;
        renderConversationList();
        renderMessages();
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

                try {
                    const uploadData = await uploadCalligraphyImage(pendingImage.file);
                    const data = await analyzeCalligraphy({
                        uploadId: uploadData.uploadId,
                        imageUrl: uploadData.imageUrl,
                        question
                    });
                    addMessage("assistant", formatAnalysisAnswer(data));
                } catch (error) {
                    addMessage("assistant", createOfflineImageAnswer(question));
                    showToast("后端未连接，已使用前端离线测试回复。");
                }
            } else {
                input.value = "";
                resizeComposer();
                addMessage("user", message);
                const data = await chatWithAI(message);
                addMessage("assistant", data.answer);
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

document.addEventListener("DOMContentLoaded", () => {
    initRouter();
    renderHomeCopybooks();
    initChat();
    initCreate();
});

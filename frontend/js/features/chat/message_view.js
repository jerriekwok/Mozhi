import { $ } from "../../shared/dom.js";


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
    if (typeof messageData === "object" && messageData?.id) {
        message.dataset.messageId = String(messageData.id);
    }

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
    if (image?.src) bubble.appendChild(createImageButton(image));
    if (role === "assistant" && Array.isArray(sources) && sources.length > 0) {
        bubble.appendChild(createSourceList(sources));
    }

    message.appendChild(bubble);
    return message;
}


export function createSourceList(sources) {
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


export function renderChatMessages(conversation, scrollBehavior = "smooth") {
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


export function updateStreamingMessage(message) {
    const messageElement = document.querySelector(`[data-message-id="${message.id}"]`);
    const textElement = messageElement?.querySelector(".message__text");
    if (!textElement) return false;

    textElement.textContent = message.content;
    $("#chatScroll").scrollTo({ top: $("#chatScroll").scrollHeight, behavior: "auto" });
    return true;
}

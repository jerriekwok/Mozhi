import { chatWithAI } from "./api.js";

function createMessage(role, text) {
    const message = document.createElement("article");
    message.className = `message message--${role}`;

    const bubble = document.createElement("div");
    bubble.className = "message__bubble";
    bubble.textContent = text;

    message.appendChild(bubble);
    return message;
}

function showToast(text) {
    const toast = document.querySelector("#toast");
    toast.textContent = text;
    toast.hidden = false;

    window.clearTimeout(showToast.timer);
    showToast.timer = window.setTimeout(() => {
        toast.hidden = true;
    }, 2600);
}

function buildLocalReply(message) {
    return `已收到你的问题：“${message}”\n\n墨智建议先观察整体章法，再看单字结构，最后拆解起笔、行笔与收笔。后续接入 AI Agent 后，这里会返回更完整的作品分析。`;
}

export function initChat(composerController) {
    const form = document.querySelector("#composer");
    const messageList = document.querySelector("#messageList");
    const chatScroll = document.querySelector("#chatScroll");
    const uploadButton = document.querySelector("#uploadButton");
    const imageAnalyzeButton = document.querySelector("#imageAnalyzeButton");
    const voiceButton = document.querySelector("#voiceButton");

    const appendMessage = (role, text) => {
        messageList.appendChild(createMessage(role, text));
        chatScroll.scrollTo({ top: chatScroll.scrollHeight, behavior: "smooth" });
    };

    form.addEventListener("submit", async (event) => {
        event.preventDefault();
        const message = composerController.input.value.trim();

        if (!message) {
            showToast("请先输入书法问题或上传作品。");
            return;
        }

        appendMessage("user", message);
        composerController.reset();
        showToast("墨智正在分析你的书法作品……");

        try {
            const data = await chatWithAI(message);
            appendMessage("assistant", data.answer || buildLocalReply(message));
        } catch (error) {
            appendMessage("assistant", buildLocalReply(message));
        }
    });

    uploadButton.addEventListener("click", () => {
        showToast("已模拟上传作品，后续将接入真实图片上传与预览。");
    });

    imageAnalyzeButton.addEventListener("click", () => {
        composerController.input.value = "请分析这张书法图片的结构、用笔、章法和改进方向。";
        composerController.input.focus();
        showToast("图片分析入口已就绪，等待接入视觉模型。");
    });

    voiceButton.addEventListener("click", () => {
        showToast("语音输入能力预留中。");
    });
}

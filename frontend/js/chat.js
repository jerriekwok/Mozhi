import { chatWithAI } from "./api.js";

function createMessage(role, text, id = null) {
    const message = document.createElement("article");
    message.className = `message message--${role}`;
    if (id) {
        message.id = id;
    }

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

export function initChat(composerController) {
    const form = document.querySelector("#composer");
    const messageList = document.querySelector("#messageList");
    const chatScroll = document.querySelector("#chatScroll");
    const uploadButton = document.querySelector("#uploadButton");
    const imageAnalyzeButton = document.querySelector("#imageAnalyzeButton");
    const voiceButton = document.querySelector("#voiceButton");
    const sendButton = document.querySelector(".send-button");

    const appendMessage = (role, text, id = null) => {
        messageList.appendChild(createMessage(role, text, id));
        chatScroll.scrollTo({ top: chatScroll.scrollHeight, behavior: "smooth" });
    };

    const removeMessage = (id) => {
        const el = document.getElementById(id);
        if (el) el.remove();
    };

    const setLoading = (loading) => {
        sendButton.disabled = loading;
        sendButton.style.opacity = loading ? "0.5" : "1";
        sendButton.style.cursor = loading ? "not-allowed" : "pointer";
    };

    form.addEventListener("submit", async (event) => {
        event.preventDefault();
        const message = composerController.input.value.trim();

        if (!message) {
            showToast("请先输入书法问题或上传作品。");
            return;
        }

        // 显示用户消息
        appendMessage("user", message);
        composerController.reset();
        setLoading(true);

        // 显示 loading 指示器
        const loadingId = "loading-" + Date.now();
        appendMessage("assistant-loading", "墨智正在思考中……", loadingId);

        try {
            const data = await chatWithAI(message);
            removeMessage(loadingId);
            appendMessage("assistant", data.answer);
        } catch (error) {
            removeMessage(loadingId);
            showToast(error.message || "连接失败，请检查网络或后端服务");
        } finally {
            setLoading(false);
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

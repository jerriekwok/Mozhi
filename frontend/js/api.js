const API_BASE_URL = "http://127.0.0.1:8000";

import { calligraphyStyles, copybooks } from "../data/calligraphy.js";

function createOfflineChatAnswer(message) {
    return {
        answer:
            "【前端离线测试模式】当前没有连接到后端或本地大模型，我先用内置回复帮你测试聊天流程。\n\n" +
            `关于“${message}”，可以先从章法、结构、用笔三方面观察：整体布局是否疏密得当，单字重心是否稳定，起收笔和转折是否清楚。` +
            "如果是临帖练习，建议先慢写三遍，再对照原帖修正横画角度、竖画力度和字内留白。"
    };
}

async function request(path, options = {}) {
    const { headers: optionHeaders, ...fetchOptions } = options;
    const headers = optionHeaders === null
        ? undefined
        : {
            "Content-Type": "application/json",
            ...optionHeaders
        };

    const response = await fetch(`${API_BASE_URL}${path}`, {
        headers,
        ...fetchOptions
    });

    if (!response.ok) {
        throw new Error(`API request failed with status ${response.status}`);
    }

    return response.json();
}

export async function chatWithAI(message) {
    if (!message) {
        throw new Error("Message is required");
    }

    try {
        return await request("/chat", {
            method: "POST",
            body: JSON.stringify({ message })
        });
    } catch (error) {
        if (error instanceof TypeError) {
            return createOfflineChatAnswer(message);
        }
        throw error;
    }
}

export async function uploadCalligraphyImage(file, options = {}) {
    if (!file) {
        throw new Error("Image file is required");
    }

    const formData = new FormData();
    formData.append("file", file);
    formData.append("purpose", options.purpose || "analysis");

    return request("/uploads/calligraphy", {
        method: "POST",
        headers: null,
        body: formData
    });
}

export async function analyzeCalligraphy(payload) {
    if (!payload || (!payload.uploadId && !payload.imageUrl)) {
        throw new Error("uploadId or imageUrl is required");
    }

    return request("/calligraphy/analyze", {
        method: "POST",
        body: JSON.stringify(payload)
    });
}

export function getCopybooks() {
    return copybooks;
}

export function getCalligraphyStyles() {
    return calligraphyStyles;
}

export async function generateCalligraphy(payload) {
    console.info("generateCalligraphy reserved payload:", payload);
    return {
        status: "reserved",
        imageUrl: "",
        message: "集字创作接口尚未接入，当前仅展示界面预留。"
    };
}

export async function saveArtwork(payload) {
    console.info("saveArtwork reserved payload:", payload);
    return {
        status: "reserved",
        message: "作品保存接口尚未接入。"
    };
}

const API_BASE_URL = "http://127.0.0.1:8000";

import { calligraphyStyles, copybooks } from "../data/calligraphy.js";

function createOfflineChatAnswer(message, sessionId) {
    return {
        answer: `【离线模式】当前无法连接本地 RAG 服务。你提出的问题是：“${message}”。请检查后端和 Ollama 是否已启动。`,
        sources: [],
        session_id: sessionId,
        offline: true
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
        const errorBody = await response.json().catch(() => null);
        throw new Error(errorBody?.detail || `API request failed with status ${response.status}`);
    }

    if (response.status === 204) {
        return null;
    }

    return response.json();
}

export async function getChatSessions() {
    return request("/api/chat/sessions");
}

export async function getChatSession(sessionId) {
    if (!sessionId) {
        throw new Error("Conversation id is required");
    }
    return request(`/api/chat/sessions/${encodeURIComponent(sessionId)}`);
}

export async function deleteChatSession(sessionId) {
    if (!sessionId) {
        throw new Error("Conversation id is required");
    }
    return request(`/api/chat/sessions/${encodeURIComponent(sessionId)}`, {
        method: "DELETE"
    });
}

function parseSseEvent(rawEvent) {
    const lines = rawEvent.split(/\r?\n/);
    const event = lines.find((line) => line.startsWith("event:"))?.slice(6).trim() || "message";
    const data = lines
        .filter((line) => line.startsWith("data:"))
        .map((line) => line.slice(5).trimStart())
        .join("\n");

    return { event, data: data ? JSON.parse(data) : {} };
}

export async function chatWithAIStream(message, sessionId, handlers = {}) {
    if (!message) {
        throw new Error("Message is required");
    }

    let response;
    try {
        response = await fetch(`${API_BASE_URL}/api/chat/stream`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ question: message, session_id: sessionId || null })
        });
    } catch (error) {
        if (error instanceof TypeError) {
            const fallback = createOfflineChatAnswer(message, sessionId);
            handlers.onSources?.(fallback.sources);
            handlers.onChunk?.(fallback.answer);
            handlers.onDone?.(fallback.session_id);
            return fallback;
        }
        throw error;
    }

    if (!response.ok) {
        const errorBody = await response.json().catch(() => null);
        throw new Error(errorBody?.detail || `API request failed with status ${response.status}`);
    }
    if (!response.body) {
        throw new Error("Streaming response body is unavailable");
    }

    const reader = response.body.getReader();
    const decoder = new TextDecoder("utf-8");
    let buffer = "";
    let answer = "";
    let sources = [];
    let completedSessionId = sessionId;

    while (true) {
        const { done, value } = await reader.read();
        buffer += decoder.decode(value || new Uint8Array(), { stream: !done });

        const events = buffer.split(/\r?\n\r?\n/);
        buffer = events.pop() || "";

        for (const rawEvent of events) {
            if (!rawEvent.trim()) continue;
            const { event, data } = parseSseEvent(rawEvent);

            if (event === "sources") {
                sources = Array.isArray(data.sources) ? data.sources : [];
                handlers.onSources?.(sources);
            } else if (event === "chunk") {
                const content = data.content || "";
                answer += content;
                handlers.onChunk?.(content, answer);
            } else if (event === "done") {
                completedSessionId = data.session_id || completedSessionId;
                handlers.onDone?.(completedSessionId);
            } else if (event === "error") {
                throw new Error(data.error || "RAG stream failed");
            }
        }

        if (done) break;
    }

    return { answer, sources, session_id: completedSessionId, offline: false };
}

export async function generateLearningPlan(payload) {
    if (!payload) {
        throw new Error("Learning plan preferences are required");
    }

    return request("/api/learning/plan", {
        method: "POST",
        body: JSON.stringify(payload)
    });
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

export async function analyzeCalligraphyStream(payload, handlers = {}) {
    if (!payload || (!payload.uploadId && !payload.imageUrl)) {
        throw new Error("uploadId or imageUrl is required");
    }

    const response = await fetch(`${API_BASE_URL}/calligraphy/analyze/stream`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload)
    });

    if (!response.ok) {
        const errorBody = await response.json().catch(() => null);
        throw new Error(errorBody?.detail || `Image analysis failed with status ${response.status}`);
    }
    if (!response.body) {
        throw new Error("Streaming response body is unavailable");
    }

    const reader = response.body.getReader();
    const decoder = new TextDecoder("utf-8");
    let buffer = "";
    let answer = "";

    while (true) {
        const { done, value } = await reader.read();
        buffer += decoder.decode(value || new Uint8Array(), { stream: !done });

        const events = buffer.split(/\r?\n\r?\n/);
        buffer = events.pop() || "";

        for (const rawEvent of events) {
            if (!rawEvent.trim()) continue;
            const { event, data } = parseSseEvent(rawEvent);

            if (event === "chunk") {
                const content = data.content || "";
                answer += content;
                handlers.onChunk?.(content, answer);
            } else if (event === "done") {
                handlers.onDone?.(answer);
            } else if (event === "error") {
                throw new Error(data.error || "Image analysis failed");
            }
        }

        if (done) break;
    }

    return { answer };
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

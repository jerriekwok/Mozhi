const API_BASE_URL = "http://127.0.0.1:8000";

async function request(path, options = {}) {
    const response = await fetch(`${API_BASE_URL}${path}`, {
        headers: {
            "Content-Type": "application/json",
            ...options.headers
        },
        ...options
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

    // Future FastAPI endpoint: POST /chat
    return request("/chat", {
        method: "POST",
        body: JSON.stringify({ message })
    });
}

export async function analyzeCalligraphy(payload) {
    // Future FastAPI endpoint: POST /calligraphy/analyze
    return request("/calligraphy/analyze", {
        method: "POST",
        body: JSON.stringify(payload)
    });
}

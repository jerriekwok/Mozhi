export function initCalligraphyEditor() {
    const reservePanel = document.querySelector(".feature-reserve");

    reservePanel.addEventListener("click", () => {
        const event = new CustomEvent("mozhi:editor-ready", {
            detail: {
                modules: ["upload", "preview", "score", "stroke-analysis", "ocr"]
            }
        });

        window.dispatchEvent(event);
    });
}

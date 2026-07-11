export function initComposerInput() {
    const input = document.querySelector("#messageInput");
    const chips = document.querySelector("#quickChips");

    const resize = () => {
        input.style.height = "auto";
        input.style.height = `${Math.min(input.scrollHeight, 150)}px`;
    };

    input.addEventListener("input", resize);

    chips.addEventListener("click", (event) => {
        const chip = event.target.closest("button[data-prompt]");
        if (!chip) return;

        input.value = chip.dataset.prompt;
        resize();
        input.focus();
    });

    return {
        input,
        reset() {
            input.value = "";
            resize();
        }
    };
}

import { initSidebar } from "./sidebar.js";
import { initComposerInput } from "./input.js";
import { initChat } from "./chat.js";
import { initCalligraphyEditor } from "./editor.js";

document.addEventListener("DOMContentLoaded", () => {
    initSidebar();
    const composerController = initComposerInput();
    initChat(composerController);
    initCalligraphyEditor();
});

import { drawNormalizedGlyph, loadGlyphImage, measureGlyph } from "../../glyph_layout.js";

function getMedian(values) {
    const sorted = [...values].sort((left, right) => left - right);
    const middle = Math.floor(sorted.length / 2);
    return sorted.length % 2 === 0 ? (sorted[middle - 1] + sorted[middle]) / 2 : sorted[middle];
}

function getGlyphVisualScale(frame, medianMass) {
    const { width, height } = frame.bounds;
    const baseScale = Math.min((480 * 0.8) / width, (480 * 0.8) / height);
    const renderedMass = frame.inkPixels ? frame.inkPixels * baseScale * baseScale : medianMass;
    const massRatio = medianMass && renderedMass ? medianMass / renderedMass : 1;
    return Math.max(0.92, Math.min(1.08, Math.sqrt(massRatio)));
}

async function loadArtworkEntries(glyphCharacters, glyphSelections, tolerateLoadFailure = false) {
    return Promise.all(glyphCharacters.map(async (item, index) => {
        const candidate = item.candidates[glyphSelections[index] || 0];
        if (!candidate) return { item, index, candidate: null, image: null, frame: null };
        try {
            const image = await loadGlyphImage(candidate.imageUrl);
            return { item, index, candidate, image, frame: measureGlyph(image) };
        } catch (error) {
            if (!tolerateLoadFailure) throw error;
            return { item, index, candidate, image: null, frame: null };
        }
    }));
}

function getMedianVisualMass(entries) {
    const visualMasses = entries
        .filter((entry) => entry?.frame?.inkPixels)
        .map((entry) => {
            const { width, height } = entry.frame.bounds;
            const baseScale = Math.min((480 * 0.8) / width, (480 * 0.8) / height);
            return entry.frame.inkPixels * baseScale * baseScale;
        });
    return visualMasses.length ? getMedian(visualMasses) : 0;
}

function showGlyphFallback(canvas, candidate, character) {
    if (!canvas) return;
    const fallback = document.createElement("img");
    fallback.className = "glyph-artwork__fallback";
    fallback.src = candidate.imageUrl;
    fallback.alt = `${character} · ${candidate.artist}`;
    fallback.title = `${character} · ${candidate.artist}`;
    canvas.replaceWith(fallback);
}

export async function drawArtworkPreview({ artboard, version, getCurrentVersion, glyphCharacters, glyphSelections }) {
    const entries = await loadArtworkEntries(glyphCharacters, glyphSelections, true);
    if (version !== getCurrentVersion()) return;
    const medianMass = getMedianVisualMass(entries);

    entries.forEach((entry) => {
        if (!entry?.candidate) return;
        const canvas = artboard.querySelector(`[data-glyph-artwork-index="${entry.index}"]`);
        if (!entry.image || !entry.frame || !canvas) {
            showGlyphFallback(canvas, entry.candidate, entry.item.character);
            return;
        }
        try {
            drawNormalizedGlyph(canvas, entry.image, {
                frame: entry.frame,
                visualScale: getGlyphVisualScale(entry.frame, medianMass)
            });
        } catch {
            showGlyphFallback(canvas, entry.candidate, entry.item.character);
        }
    });
}

function getArtworkLayout(artboard, glyphCharacters) {
    const artwork = artboard.querySelector(".glyph-artwork");
    const count = glyphCharacters.length;
    if (!artwork || !count || !artwork.clientWidth || !artwork.clientHeight) return null;
    return {
        width: artwork.clientWidth,
        height: artwork.clientHeight,
        glyphSize: Math.min(artwork.clientWidth * 0.72, Math.max(72, (artwork.clientHeight - 16) / count * 0.92))
    };
}

export async function exportArtworkPng({ artboard, glyphCharacters, glyphSelections, getGlyphTransform, title }) {
    const layout = getArtworkLayout(artboard, glyphCharacters);
    if (!layout) throw new Error("请先生成集字作品。");

    const exportWidth = 1800;
    const exportHeight = 2400;
    const output = document.createElement("canvas");
    output.width = exportWidth;
    output.height = exportHeight;
    const context = output.getContext("2d");
    if (!context) throw new Error("浏览器不支持图片导出。");

    context.fillStyle = "#fffcf6";
    context.fillRect(0, 0, exportWidth, exportHeight);

    const entries = await loadArtworkEntries(glyphCharacters, glyphSelections);
    const medianMass = getMedianVisualMass(entries);
    const exportScaleX = exportWidth / layout.width;
    const exportScaleY = exportHeight / layout.height;
    const glyphExportScale = Math.min(exportScaleX, exportScaleY);

    entries.forEach((entry) => {
        const baseX = layout.width / 2;
        const baseY = ((entry.index + 0.5) / entries.length) * layout.height;
        const transform = getGlyphTransform(entry.index);
        context.save();
        context.translate((baseX + transform.x) * exportScaleX, (baseY + transform.y) * exportScaleY);
        context.rotate((transform.rotation * Math.PI) / 180);
        context.scale(transform.scale, transform.scale);

        if (entry.image && entry.frame) {
            const glyphCanvas = document.createElement("canvas");
            glyphCanvas.width = Math.round(layout.glyphSize * glyphExportScale);
            glyphCanvas.height = glyphCanvas.width;
            drawNormalizedGlyph(glyphCanvas, entry.image, {
                frame: entry.frame,
                visualScale: getGlyphVisualScale(entry.frame, medianMass)
            });
            const size = layout.glyphSize * glyphExportScale;
            context.drawImage(glyphCanvas, -size / 2, -size / 2, size, size);
        } else {
            context.fillStyle = "#a33b2e";
            context.font = `${Math.round(38 * glyphExportScale)}px sans-serif`;
            context.textAlign = "center";
            context.fillText(`缺${entry.item.character}`, 0, 0);
        }
        context.restore();
    });

    const link = document.createElement("a");
    const filename = title.trim().replace(/[\\/:*?"<>|]/g, "") || "集字作品";
    link.href = output.toDataURL("image/png");
    link.download = `${filename}-墨智集字.png`;
    link.click();
}

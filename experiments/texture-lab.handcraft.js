(function initTextureLabHandcraft() {
    const Lab = window.TextureLab;
    if (!Lab || !Lab.dom) {
        return;
    }

    const d = Lab.dom;
    const MAX_HISTORY = 24;

    function snapshotPaintLayer() {
        return Lab.contexts.paint.getImageData(0, 0, Lab.paintCanvas.width, Lab.paintCanvas.height);
    }

    function snapshotsDiffer(a, b) {
        if (!a || !b || a.width !== b.width || a.height !== b.height) {
            return true;
        }
        const aData = a.data;
        const bData = b.data;
        if (aData.length !== bData.length) {
            return true;
        }
        for (let i = 0; i < aData.length; i += 1) {
            if (aData[i] !== bData[i]) {
                return true;
            }
        }
        return false;
    }

    function trimStack(stack) {
        while (stack.length > MAX_HISTORY) {
            stack.shift();
        }
    }

    function syncHistoryButtons() {
        if (d.undoPaintBtn) {
            d.undoPaintBtn.disabled = Lab.state.paintUndoStack.length === 0;
        }
        if (d.redoPaintBtn) {
            d.redoPaintBtn.disabled = Lab.state.paintRedoStack.length === 0;
        }
    }

    function pushHistoryMutation(before, after) {
        if (!snapshotsDiffer(before, after)) {
            return;
        }
        Lab.state.paintUndoStack.push(before);
        trimStack(Lab.state.paintUndoStack);
        Lab.state.paintRedoStack.length = 0;
        syncHistoryButtons();
    }

    function readBrushSettings() {
        const scaleFactor = d.textureCanvas.width / Lab.tileSizeScaleBase;
        return {
            mode: d.brushModeSelect.value,
            color: d.brushColorInput.value,
            opacity: Number(d.brushOpacityInput.value) / 100,
            size: Number(d.brushSizeInput.value) * scaleFactor
        };
    }

    function getBrushBlendSpec(brush) {
        if (brush.mode === "lighten") {
            return {
                blendMode: "screen",
                color: `rgba(255, 255, 255, ${brush.opacity.toFixed(3)})`
            };
        }
        if (brush.mode === "darken") {
            return {
                blendMode: "multiply",
                color: `rgba(0, 0, 0, ${brush.opacity.toFixed(3)})`
            };
        }
        return {
            blendMode: "source-over",
            color: Lab.rgbaFromHex(brush.color, brush.opacity)
        };
    }

    function paintDabWrapped(targetContext, wrapWidth, wrapHeight, x, y, radius, brush) {
        if (radius <= 0) {
            return;
        }
        const spec = getBrushBlendSpec(brush);
        const xOffsets = [-wrapWidth, 0, wrapWidth];
        const yOffsets = [-wrapHeight, 0, wrapHeight];

        targetContext.save();
        targetContext.globalCompositeOperation = spec.blendMode;
        targetContext.fillStyle = spec.color;
        for (const offsetX of xOffsets) {
            for (const offsetY of yOffsets) {
                targetContext.beginPath();
                targetContext.arc(x + offsetX, y + offsetY, radius, 0, Math.PI * 2);
                targetContext.fill();
            }
        }
        targetContext.restore();
    }

    function paintStrokeWrapped(targetContext, wrapWidth, wrapHeight, from, to, brush, randFn = Math.random) {
        const dx = to.x - from.x;
        const dy = to.y - from.y;
        const distance = Math.hypot(dx, dy);
        const spacing = Math.max(0.8, brush.size * 0.35);
        const steps = Math.max(1, Math.ceil(distance / spacing));

        for (let i = 0; i <= steps; i += 1) {
            const t = i / steps;
            const jitter = brush.size * 0.2;
            const pointX = Lab.lerp(from.x, to.x, t) + (randFn() - 0.5) * jitter;
            const pointY = Lab.lerp(from.y, to.y, t) + (randFn() - 0.5) * jitter;
            const radius = brush.size * (0.7 + randFn() * 0.5);
            paintDabWrapped(targetContext, wrapWidth, wrapHeight, pointX, pointY, radius, brush);
        }
    }

    function pickStyleColorHex(styleKey, randFn) {
        const tone = Lab.clamp(randFn() * 0.9 + 0.05, 0, 1);
        const color = Lab.sampleGradient(styleKey, tone);
        return Lab.rgbToHex(color.r, color.g, color.b);
    }

    function applyHandcraftedLayer(targetContext, wrapWidth, wrapHeight, settings, variantSeed = 1) {
        const strength = Lab.clamp(settings.handcraft, 0, 1);
        if (strength <= 0) {
            return;
        }

        const rand = Lab.createRng(settings.seed + variantSeed * 104729 + 23);
        const sizeScale = wrapWidth / Lab.tileSizeScaleBase;
        const strokeCount = Math.floor(18 + strength * 120);

        for (let i = 0; i < strokeCount; i += 1) {
            const start = { x: rand() * wrapWidth, y: rand() * wrapHeight };
            const curve = (rand() - 0.5) * 0.7;
            let direction = rand() * Math.PI * 2;
            const length = (10 + rand() * 26 + strength * 34) * sizeScale;
            const modeRoll = rand();
            const brush = {
                mode: modeRoll < 0.55 ? "tint" : modeRoll < 0.79 ? "lighten" : "darken",
                color: pickStyleColorHex(settings.style, rand),
                opacity: Lab.clamp(0.03 + strength * 0.14 + rand() * 0.08, 0.02, 0.35),
                size: (1.1 + rand() * 3.6 + strength * 2.4) * sizeScale
            };

            const segmentLength = Math.max(1, brush.size * 0.8);
            const steps = Math.max(3, Math.floor(length / segmentLength));
            const stepDistance = length / steps;
            let cursor = start;

            for (let step = 0; step < steps; step += 1) {
                direction += curve * 0.08 + (rand() - 0.5) * 0.18;
                const next = {
                    x: cursor.x + Math.cos(direction) * stepDistance,
                    y: cursor.y + Math.sin(direction) * stepDistance
                };
                paintStrokeWrapped(targetContext, wrapWidth, wrapHeight, cursor, next, brush, rand);

                if (rand() < 0.18) {
                    paintDabWrapped(
                        targetContext,
                        wrapWidth,
                        wrapHeight,
                        next.x + (rand() - 0.5) * brush.size * 2,
                        next.y + (rand() - 0.5) * brush.size * 2,
                        brush.size * (0.4 + rand() * 0.45),
                        brush
                    );
                }
                cursor = next;
            }
        }

        const chipCount = Math.floor(42 + strength * 220);
        for (let i = 0; i < chipCount; i += 1) {
            const darkChip = rand() < 0.52;
            const chipBrush = {
                mode: darkChip ? "darken" : "lighten",
                color: "#ffffff",
                opacity: 0.04 + rand() * (0.06 + strength * 0.12),
                size: (0.6 + rand() * 1.8 + strength * 0.5) * sizeScale
            };
            paintDabWrapped(
                targetContext,
                wrapWidth,
                wrapHeight,
                rand() * wrapWidth,
                rand() * wrapHeight,
                chipBrush.size,
                chipBrush
            );
        }
    }

    function clearPaintLayer(skipCompose = false) {
        clearPaintLayerWithHistory(skipCompose, true);
    }

    function clearPaintLayerWithHistory(skipCompose = false, trackHistory = true) {
        if (!trackHistory) {
            Lab.contexts.paint.clearRect(0, 0, Lab.paintCanvas.width, Lab.paintCanvas.height);
            Lab.state.paintUndoStack.length = 0;
            Lab.state.paintRedoStack.length = 0;
            Lab.state.paintStrokeBefore = null;
            syncHistoryButtons();
            if (!skipCompose) {
                Lab.composeTextureAndPreview();
            }
            return;
        }

        const before = snapshotPaintLayer();
        Lab.contexts.paint.clearRect(0, 0, Lab.paintCanvas.width, Lab.paintCanvas.height);
        const after = snapshotPaintLayer();
        pushHistoryMutation(before, after);
        if (!skipCompose) {
            Lab.composeTextureAndPreview();
        }
    }

    function applyHandcraftedPass() {
        if (Lab.state.isRendering) {
            return;
        }
        const settings = Lab.readSettings();
        if (settings.handcraft <= 0) {
            return;
        }

        const before = snapshotPaintLayer();
        Lab.state.handcraftPassCount += 1;
        applyHandcraftedLayer(
            Lab.contexts.paint,
            Lab.paintCanvas.width,
            Lab.paintCanvas.height,
            settings,
            Lab.state.handcraftPassCount
        );
        const after = snapshotPaintLayer();
        pushHistoryMutation(before, after);
        Lab.composeTextureAndPreview();
    }

    function undoPaintAction() {
        if (Lab.state.isRendering || Lab.state.paintUndoStack.length === 0) {
            return false;
        }
        const current = snapshotPaintLayer();
        const previous = Lab.state.paintUndoStack.pop();
        Lab.state.paintRedoStack.push(current);
        trimStack(Lab.state.paintRedoStack);
        Lab.contexts.paint.putImageData(previous, 0, 0);
        Lab.composeTextureAndPreview();
        syncHistoryButtons();
        return true;
    }

    function redoPaintAction() {
        if (Lab.state.isRendering || Lab.state.paintRedoStack.length === 0) {
            return false;
        }
        const current = snapshotPaintLayer();
        const next = Lab.state.paintRedoStack.pop();
        Lab.state.paintUndoStack.push(current);
        trimStack(Lab.state.paintUndoStack);
        Lab.contexts.paint.putImageData(next, 0, 0);
        Lab.composeTextureAndPreview();
        syncHistoryButtons();
        return true;
    }

    function canvasPointFromEvent(event) {
        const rect = d.textureCanvas.getBoundingClientRect();
        if (rect.width === 0 || rect.height === 0) {
            return null;
        }
        const x = ((event.clientX - rect.left) / rect.width) * d.textureCanvas.width;
        const y = ((event.clientY - rect.top) / rect.height) * d.textureCanvas.height;
        return {
            x: Lab.clamp(x, 0, d.textureCanvas.width),
            y: Lab.clamp(y, 0, d.textureCanvas.height)
        };
    }

    function startPainting(event) {
        if (Lab.state.isRendering) {
            return;
        }
        if (event.pointerType === "mouse" && event.button !== 0) {
            return;
        }

        event.preventDefault();
        const point = canvasPointFromEvent(event);
        if (!point) {
            return;
        }

        Lab.state.isPainting = true;
        Lab.state.lastPaintPoint = point;
        Lab.state.paintStrokeBefore = snapshotPaintLayer();

        if (d.textureCanvas.setPointerCapture) {
            d.textureCanvas.setPointerCapture(event.pointerId);
        }

        const brush = readBrushSettings();
        paintDabWrapped(
            Lab.contexts.paint,
            Lab.paintCanvas.width,
            Lab.paintCanvas.height,
            point.x,
            point.y,
            brush.size * 0.5,
            brush
        );
        Lab.composeTextureAndPreview();
    }

    function continuePainting(event) {
        if (Lab.state.isRendering || !Lab.state.isPainting) {
            return;
        }

        event.preventDefault();
        const point = canvasPointFromEvent(event);
        if (!point || !Lab.state.lastPaintPoint) {
            return;
        }

        const brush = readBrushSettings();
        paintStrokeWrapped(
            Lab.contexts.paint,
            Lab.paintCanvas.width,
            Lab.paintCanvas.height,
            Lab.state.lastPaintPoint,
            point,
            brush
        );
        Lab.state.lastPaintPoint = point;
        Lab.composeTextureAndPreview();
    }

    function stopPainting(event) {
        if (!Lab.state.isPainting) {
            return;
        }

        if (d.textureCanvas.releasePointerCapture && event && typeof event.pointerId === "number") {
            try {
                d.textureCanvas.releasePointerCapture(event.pointerId);
            } catch {
                // Ignore release errors when pointer is already released.
            }
        }

        Lab.state.isPainting = false;
        Lab.state.lastPaintPoint = null;
        const before = Lab.state.paintStrokeBefore;
        Lab.state.paintStrokeBefore = null;
        if (before) {
            const after = snapshotPaintLayer();
            pushHistoryMutation(before, after);
        }
    }

    syncHistoryButtons();

    Lab.readBrushSettings = readBrushSettings;
    Lab.getBrushBlendSpec = getBrushBlendSpec;
    Lab.paintDabWrapped = paintDabWrapped;
    Lab.paintStrokeWrapped = paintStrokeWrapped;
    Lab.pickStyleColorHex = pickStyleColorHex;
    Lab.applyHandcraftedLayer = applyHandcraftedLayer;
    Lab.clearPaintLayer = clearPaintLayer;
    Lab.clearPaintLayerWithHistory = clearPaintLayerWithHistory;
    Lab.applyHandcraftedPass = applyHandcraftedPass;
    Lab.undoPaintAction = undoPaintAction;
    Lab.redoPaintAction = redoPaintAction;
    Lab.syncHistoryButtons = syncHistoryButtons;
    Lab.canvasPointFromEvent = canvasPointFromEvent;
    Lab.startPainting = startPainting;
    Lab.continuePainting = continuePainting;
    Lab.stopPainting = stopPainting;
})();

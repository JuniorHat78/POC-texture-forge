(function initTextureLabParams() {
    const Lab = window.TextureLab;
    if (!Lab || !Lab.dom) {
        return;
    }

    const d = Lab.dom;

    function currentMode() {
        return d.modeSelect.value === "advanced" ? "advanced" : "basic";
    }

    function applyVariationToAdvanced() {
        const t = Number(d.variationInput.value) / 100;
        d.scaleInput.value = String(Math.round(Lab.lerp(4, 14, t)));
        d.octavesInput.value = String(Math.round(Lab.lerp(2, 6, t)));
        d.roughnessInput.value = String(Math.round(Lab.lerp(35, 110, t)));
        d.contrastInput.value = String(Math.round(Lab.lerp(95, 150, t)));
        d.grainInput.value = String(Math.round(Lab.lerp(2, 16, t)));
    }

    function syncVariationFromAdvanced() {
        const scaleNorm = Lab.clamp((Number(d.scaleInput.value) - 4) / 10, 0, 1);
        const octavesNorm = Lab.clamp((Number(d.octavesInput.value) - 2) / 4, 0, 1);
        const roughnessNorm = Lab.clamp((Number(d.roughnessInput.value) - 35) / 75, 0, 1);
        const contrastNorm = Lab.clamp((Number(d.contrastInput.value) - 95) / 55, 0, 1);
        const grainNorm = Lab.clamp((Number(d.grainInput.value) - 2) / 14, 0, 1);
        const avg = (scaleNorm + octavesNorm + roughnessNorm + contrastNorm + grainNorm) / 5;
        d.variationInput.value = String(Math.round(avg * 100));
    }

    function applyUIMode() {
        const basic = currentMode() === "basic";
        d.controlsPanel.classList.toggle("basic", basic);
        d.controlsPanel.classList.toggle("advanced", !basic);
        if (basic) {
            applyVariationToAdvanced();
        } else {
            syncVariationFromAdvanced();
        }
        syncValuePills();
    }

    function readSettings() {
        return {
            style: d.styleSelect.value,
            seed: Lab.clamp(Math.floor(Number(d.seedInput.value) || 1), 1, 999999999),
            size: Number(d.sizeSelect.value),
            scale: Number(d.scaleInput.value),
            octaves: Number(d.octavesInput.value),
            roughness: Number(d.roughnessInput.value) / 100,
            contrast: Number(d.contrastInput.value) / 100,
            grain: Number(d.grainInput.value) / 100,
            handcraft: Number(d.handcraftInput.value) / 100
        };
    }

    function applySettings(settings) {
        d.styleSelect.value = settings.style;
        d.seedInput.value = String(settings.seed);
        d.sizeSelect.value = String(settings.size);
        d.scaleInput.value = String(settings.scale);
        d.octavesInput.value = String(settings.octaves);
        d.roughnessInput.value = String(Math.round(settings.roughness * 100));
        d.contrastInput.value = String(Math.round(settings.contrast * 100));
        d.grainInput.value = String(Math.round(settings.grain * 100));
        d.handcraftInput.value = String(Math.round(settings.handcraft * 100));
        if (typeof settings.variation === "number") {
            d.variationInput.value = String(Math.round(settings.variation * 100));
        } else {
            syncVariationFromAdvanced();
        }
        syncValuePills();
    }

    function syncValuePills() {
        d.scaleValue.textContent = d.scaleInput.value;
        d.octavesValue.textContent = d.octavesInput.value;
        d.roughnessValue.textContent = (Number(d.roughnessInput.value) / 100).toFixed(2);
        d.contrastValue.textContent = (Number(d.contrastInput.value) / 100).toFixed(2);
        d.grainValue.textContent = (Number(d.grainInput.value) / 100).toFixed(2);
        d.variationValue.textContent = (Number(d.variationInput.value) / 100).toFixed(2);
        d.handcraftValue.textContent = (Number(d.handcraftInput.value) / 100).toFixed(2);
        d.brushSizeValue.textContent = d.brushSizeInput.value;
        d.brushOpacityValue.textContent = (Number(d.brushOpacityInput.value) / 100).toFixed(2);
    }

    function randomInt(min, max) {
        return Math.floor(Math.random() * (max - min + 1)) + min;
    }

    function randomSeed() {
        return randomInt(1000000, 999999999);
    }

    function randomSettings() {
        const styles = Object.keys(Lab.styles);
        const variation = randomInt(20, 85) / 100;
        return {
            style: styles[randomInt(0, styles.length - 1)],
            seed: randomSeed(),
            size: Number(d.sizeSelect.value),
            scale: Math.round(Lab.lerp(4, 14, variation)),
            octaves: Math.round(Lab.lerp(2, 6, variation)),
            roughness: Lab.lerp(0.35, 1.1, variation),
            contrast: Lab.lerp(0.95, 1.5, variation),
            grain: Lab.lerp(0.02, 0.16, variation),
            handcraft: randomInt(18, 88) / 100,
            variation
        };
    }

    Lab.currentMode = currentMode;
    Lab.applyVariationToAdvanced = applyVariationToAdvanced;
    Lab.syncVariationFromAdvanced = syncVariationFromAdvanced;
    Lab.applyUIMode = applyUIMode;
    Lab.readSettings = readSettings;
    Lab.applySettings = applySettings;
    Lab.syncValuePills = syncValuePills;
    Lab.randomInt = randomInt;
    Lab.randomSeed = randomSeed;
    Lab.randomSettings = randomSettings;
})();

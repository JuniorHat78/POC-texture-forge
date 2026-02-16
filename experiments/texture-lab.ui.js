(function initTextureLabUi() {
    const Lab = window.TextureLab;
    if (!Lab || !Lab.dom) {
        return;
    }

    const d = Lab.dom;

    function createIdeaCard(settings) {
        const card = document.createElement("button");
        card.type = "button";
        card.className = "idea-card";

        const thumb = document.createElement("canvas");
        thumb.width = 112;
        thumb.height = 112;
        Lab.renderToCanvas(thumb, settings);
        if (settings.handcraft > 0) {
            const thumbContext = thumb.getContext("2d");
            Lab.applyHandcraftedLayer(thumbContext, thumb.width, thumb.height, settings, 1);
        }

        const label = document.createElement("p");
        label.textContent = `${Lab.styles[settings.style].label} #${settings.seed} H${Math.round(settings.handcraft * 100)}`;

        card.appendChild(thumb);
        card.appendChild(label);
        card.addEventListener("click", () => {
            Lab.applySettings(settings);
            Lab.renderMain(true);
            Lab.applyHandcraftedPass();
        });
        return card;
    }

    function generateIdeas() {
        d.ideasGrid.innerHTML = "";
        for (let i = 0; i < 8; i += 1) {
            const idea = Lab.randomSettings();
            d.ideasGrid.appendChild(createIdeaCard(idea));
        }
    }

    function isTextEntryTarget(target) {
        if (!target || typeof target.tagName !== "string") {
            return false;
        }
        const tag = target.tagName.toLowerCase();
        if (tag === "input" || tag === "textarea" || tag === "select") {
            return true;
        }
        return Boolean(target.isContentEditable);
    }

    function handleHotkeys(event) {
        if (isTextEntryTarget(event.target)) {
            return;
        }

        const key = String(event.key || "").toLowerCase();
        const mod = event.ctrlKey || event.metaKey;

        if (mod && key === "z") {
            event.preventDefault();
            if (event.shiftKey) {
                if (typeof Lab.redoPaintAction === "function") {
                    Lab.redoPaintAction();
                }
            } else if (typeof Lab.undoPaintAction === "function") {
                Lab.undoPaintAction();
            }
            return;
        }

        if (mod && key === "y") {
            event.preventDefault();
            if (typeof Lab.redoPaintAction === "function") {
                Lab.redoPaintAction();
            }
            return;
        }

        if (!mod && !event.altKey && key === "r") {
            event.preventDefault();
            Lab.renderMain(false);
            return;
        }

        if (!mod && !event.altKey && key === "h") {
            event.preventDefault();
            Lab.applyHandcraftedPass();
            return;
        }

        if (!mod && !event.altKey && key === "g") {
            event.preventDefault();
            generateIdeas();
            return;
        }

        if (!mod && !event.altKey && key === "e") {
            event.preventDefault();
            Lab.exportTexture();
        }
    }

    function wireEvents() {
        [
            d.variationInput,
            d.scaleInput,
            d.octavesInput,
            d.roughnessInput,
            d.contrastInput,
            d.grainInput,
            d.handcraftInput,
            d.brushSizeInput,
            d.brushOpacityInput
        ].forEach((control) => {
            control.addEventListener("input", () => {
                if (control === d.variationInput && Lab.currentMode() === "basic") {
                    Lab.applyVariationToAdvanced();
                }

                if (
                    control !== d.variationInput &&
                    Lab.currentMode() === "advanced" &&
                    [d.scaleInput, d.octavesInput, d.roughnessInput, d.contrastInput, d.grainInput].includes(control)
                ) {
                    Lab.syncVariationFromAdvanced();
                }

                Lab.syncValuePills();
            });
        });

        d.seedBtn.addEventListener("click", () => {
            d.seedInput.value = String(Lab.randomSeed());
            Lab.renderMain(true);
        });

        d.randomizeBtn.addEventListener("click", () => {
            const settings = Lab.randomSettings();
            Lab.applySettings(settings);
            Lab.renderMain(true);
            Lab.applyHandcraftedPass();
        });

        d.renderBtn.addEventListener("click", () => Lab.renderMain(false));
        d.exportBtn.addEventListener("click", Lab.exportTexture);
        d.ideasBtn.addEventListener("click", generateIdeas);
        d.applyHandcraftBtn.addEventListener("click", Lab.applyHandcraftedPass);
        d.clearPaintBtn.addEventListener("click", () => Lab.clearPaintLayer());
        if (d.undoPaintBtn) {
            d.undoPaintBtn.addEventListener("click", () => {
                if (typeof Lab.undoPaintAction === "function") {
                    Lab.undoPaintAction();
                }
            });
        }
        if (d.redoPaintBtn) {
            d.redoPaintBtn.addEventListener("click", () => {
                if (typeof Lab.redoPaintAction === "function") {
                    Lab.redoPaintAction();
                }
            });
        }

        [d.styleSelect, d.seedInput, d.sizeSelect].forEach((control) => {
            control.addEventListener("change", () => Lab.renderMain(true));
        });

        d.modeSelect.addEventListener("change", () => {
            Lab.applyUIMode();
            Lab.renderMain(true);
        });

        d.textureCanvas.addEventListener("pointerdown", Lab.startPainting);
        d.textureCanvas.addEventListener("pointermove", Lab.continuePainting);
        d.textureCanvas.addEventListener("pointerup", Lab.stopPainting);
        d.textureCanvas.addEventListener("pointercancel", Lab.stopPainting);
        d.textureCanvas.addEventListener("pointerleave", Lab.stopPainting);
        document.addEventListener("keydown", handleHotkeys);
    }

    function init() {
        wireEvents();
        Lab.syncVariationFromAdvanced();
        Lab.applyUIMode();
        Lab.syncValuePills();
        if (typeof Lab.syncHistoryButtons === "function") {
            Lab.syncHistoryButtons();
        }
        Lab.renderMain(true);
        Lab.applyHandcraftedPass();
        generateIdeas();
    }

    init();
})();

/* ASOD workspace
 *
 * Talks to the existing backend only:
 *   POST /api/compare  multipart field "files" (2 to 10 files, 10 MB each)
 *   GET  /api/health
 * Request and response shapes are unchanged from the original frontend.
 */
(() => {
    "use strict";

    /* ---- Constants (mirror src/api/main.py) ------------------------------ */
    const API = { compare: "/api/compare", health: "/api/health" };
    const LIMITS = {
        minFiles: 2,
        maxFiles: 10,
        maxBytes: 10 * 1024 * 1024,
        extensions: [".txt", ".docx"],
    };

    /* ---- Icons (static, trusted markup) ---------------------------------- */
    const ICON_PATHS = {
        upload: '<path d="M12 16V4M7 9l5-5 5 5M4 20h16"/>',
        close: '<path d="M6 6l12 12M18 6L6 18"/>',
        alert: '<circle cx="12" cy="12" r="9"/><path d="M12 7v6M12 16.5v.5"/>',
        info: '<circle cx="12" cy="12" r="9"/><path d="M12 11v6M12 7.5v.5"/>',
        check: '<circle cx="12" cy="12" r="9"/><path d="M8 12.5l3 3 5-6"/>',
        chevron: '<path d="M9 6l6 6-6 6"/>',
        swap: '<path d="M7 7h12M16 4l3 3-3 3M17 17H5M8 14l-3 3 3 3"/>',
        search: '<circle cx="11" cy="11" r="6"/><path d="M20 20l-4.5-4.5"/>',
        docs: '<path d="M7 3h7l4 4v14H7zM14 3v4h4M10 12h5M10 16h5"/>',
    };

    function icon(name, extraClass) {
        const svg = document.createElementNS("http://www.w3.org/2000/svg", "svg");
        svg.setAttribute("viewBox", "0 0 24 24");
        svg.setAttribute("aria-hidden", "true");
        svg.setAttribute("class", "icon" + (extraClass ? " " + extraClass : ""));
        svg.innerHTML = ICON_PATHS[name] || "";
        return svg;
    }

    /* ---- DOM helpers ----------------------------------------------------- */
    const $ = (id) => document.getElementById(id);

    function el(tag, options = {}, ...children) {
        const node = document.createElement(tag);
        if (options.class) node.className = options.class;
        if (options.text !== undefined) node.textContent = options.text;
        if (options.attrs) {
            for (const [key, value] of Object.entries(options.attrs)) {
                node.setAttribute(key, value);
            }
        }
        for (const child of children) {
            if (child) node.append(child);
        }
        return node;
    }

    function formatBytes(bytes) {
        if (bytes < 1024) return `${bytes} B`;
        if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
        return `${(bytes / (1024 * 1024)).toFixed(2)} MB`;
    }

    function plural(count, singular, pluralForm) {
        return `${count} ${count === 1 ? singular : pluralForm || singular + "s"}`;
    }

    function fileExtension(name) {
        const dot = name.lastIndexOf(".");
        return dot >= 0 ? name.slice(dot).toLowerCase() : "";
    }

    /* ---- Element references --------------------------------------------- */
    const refs = {
        fileInput: $("fileInput"),
        browse: $("browseButton"),
        dropzone: $("dropzone"),
        fileList: $("fileList"),
        fileCount: $("fileCount"),
        clearAll: $("clearButton"),
        hint: $("selectionHint"),
        compare: $("compareButton"),
        messages: $("messages"),
        stepper: $("stepper"),
        status: $("apiStatus"),
        statusText: $("apiStatusText"),
        stateEmpty: $("stateEmpty"),
        stateLoading: $("stateLoading"),
        stateError: $("stateError"),
        results: $("results"),
        loadingTitle: $("loadingTitle"),
        loadingText: $("loadingText"),
        progress: $("progress"),
        progressBar: $("progressBar"),
        progressLabel: $("progressLabel"),
        cancel: $("cancelButton"),
        errorTitle: $("errorTitle"),
        errorText: $("errorText"),
        retry: $("retryButton"),
        resultsSubtitle: $("resultsSubtitle"),
        stale: $("staleNotice"),
        summary: $("summaryGrid"),
        docsBody: $("docsBody"),
        pairResults: $("pairResults"),
        filter: $("evidenceFilter"),
        expandAll: $("expandAll"),
        collapseAll: $("collapseAll"),
    };

    /* ---- State ----------------------------------------------------------- */
    const state = {
        files: [],
        phase: "idle", // idle | running | done
        request: null,
        lastSignature: null,
        filter: "all", // all | exact | near
        pairs: [], // { card, data, rendered }
    };

    const signatureOf = (files) =>
        files.map((f) => `${f.name}|${f.size}|${f.lastModified}`).join("\n");

    /* ---- Messages (selection feedback) ---------------------------------- */
    function showMessages(items) {
        refs.messages.replaceChildren();
        for (const item of items) {
            const body = el("div", { class: "alert__body" });
            if (item.title) body.append(el("div", { class: "alert__title", text: item.title }));
            if (item.text) body.append(el("p", { text: item.text }));
            if (item.list && item.list.length) {
                const ul = el("ul", { class: "alert__list" });
                item.list.forEach((line) => ul.append(el("li", { text: line })));
                body.append(ul);
            }
            const alert = el(
                "div",
                { class: `alert alert--${item.type || "info"}`, attrs: { role: item.type === "error" ? "alert" : "status" } },
                icon(item.type === "error" ? "alert" : item.type === "warning" ? "alert" : "info"),
                body
            );
            refs.messages.append(alert);
        }
    }

    /* ---- File selection -------------------------------------------------- */
    function addFiles(incoming) {
        const problems = [];
        const skipped = [];
        let limitHit = false;

        for (const file of incoming) {
            if (!LIMITS.extensions.includes(fileExtension(file.name))) {
                problems.push(`${file.name}: unsupported type. Select TXT or DOCX files.`);
                continue;
            }
            if (file.size > LIMITS.maxBytes) {
                problems.push(`${file.name}: ${formatBytes(file.size)} exceeds the 10 MB limit.`);
                continue;
            }
            if (file.size === 0) {
                problems.push(`${file.name}: the file is empty.`);
                continue;
            }
            const duplicate = state.files.some(
                (f) => f.name === file.name && f.size === file.size && f.lastModified === file.lastModified
            );
            if (duplicate) {
                skipped.push(file.name);
                continue;
            }
            if (state.files.length >= LIMITS.maxFiles) {
                limitHit = true;
                break;
            }
            state.files.push(file);
        }

        const messages = [];
        if (problems.length) {
            messages.push({
                type: "error",
                title: plural(problems.length, "file") + " could not be added",
                list: problems,
            });
        }
        if (limitHit) {
            messages.push({
                type: "error",
                text: `A maximum of ${LIMITS.maxFiles} documents is allowed. Remove a file to add another.`,
            });
        }
        if (skipped.length) {
            messages.push({
                type: "info",
                text: `Already selected, skipped: ${skipped.join(", ")}`,
            });
        }
        showMessages(messages);
        render();
    }

    function removeFile(index) {
        state.files.splice(index, 1);
        showMessages([]);
        render();
    }

    function clearFiles() {
        state.files = [];
        showMessages([]);
        render();
    }

    function sharedNames() {
        const counts = new Map();
        state.files.forEach((f) => counts.set(f.name, (counts.get(f.name) || 0) + 1));
        return [...counts].filter(([, n]) => n > 1).map(([name]) => name);
    }

    /* ---- Rendering: left panel ------------------------------------------ */
    function renderFileList() {
        const running = state.phase === "running";
        refs.fileList.replaceChildren();

        if (state.files.length === 0) {
            refs.fileList.append(
                el("li", { class: "file-list__empty", text: "No documents selected." })
            );
        }

        state.files.forEach((file, index) => {
            const ext = fileExtension(file.name).slice(1).toUpperCase();
            const remove = el("button", {
                class: "icon-btn",
                attrs: { type: "button", "aria-label": `Remove ${file.name}`, title: "Remove" },
            }, icon("close"));
            remove.disabled = running;
            remove.addEventListener("click", () => removeFile(index));

            refs.fileList.append(
                el("li", { class: "file-item" },
                    el("div", { class: "file-item__type", text: ext }),
                    el("div", { class: "file-item__main" },
                        el("div", { class: "file-item__name", text: file.name, attrs: { title: file.name } }),
                        el("div", { class: "file-item__meta", text: formatBytes(file.size) })
                    ),
                    remove
                )
            );
        });

        refs.fileCount.textContent = `${state.files.length} of ${LIMITS.maxFiles} selected`;
        refs.clearAll.hidden = state.files.length === 0;
        refs.clearAll.disabled = running;
    }

    function renderControls() {
        const running = state.phase === "running";
        const count = state.files.length;
        const ready = count >= LIMITS.minFiles && count <= LIMITS.maxFiles;

        refs.dropzone.classList.toggle("is-disabled", running);
        refs.browse.disabled = running;
        refs.compare.disabled = !ready || running;
        refs.compare.replaceChildren();
        if (running) {
            refs.compare.append(el("span", { class: "spinner", attrs: { "aria-hidden": "true" } }), document.createTextNode("Comparing"));
        } else {
            refs.compare.append(document.createTextNode("Run comparison"));
        }

        if (running) {
            refs.hint.textContent = "Comparison in progress. Selection is locked.";
        } else if (count === 0) {
            refs.hint.textContent = "Add at least two documents to begin.";
        } else if (count < LIMITS.minFiles) {
            refs.hint.textContent = "Add one more document to compare.";
        } else {
            const pairs = (count * (count - 1)) / 2;
            refs.hint.textContent = `${count} documents ready. ${plural(pairs, "pair")} will be compared.`;
        }
    }

    function renderStepper() {
        let current = 1;
        if (state.phase === "done") current = 3;
        else if (state.phase === "running" || state.files.length >= LIMITS.minFiles) current = 2;

        refs.stepper.querySelectorAll(".step").forEach((step, i) => {
            const n = i + 1;
            const status = n < current ? "done" : n === current ? "current" : "upcoming";
            step.dataset.status = status;
            if (status === "current") step.setAttribute("aria-current", "step");
            else step.removeAttribute("aria-current");
        });
    }

    function renderDuplicateNameWarning() {
        const names = sharedNames();
        const existing = refs.messages.querySelector("[data-name-warning]");
        if (existing) existing.remove();
        if (!names.length) return;
        const warning = el("div", { class: "alert alert--warning", attrs: { "data-name-warning": "", role: "status" } },
            icon("alert"),
            el("div", { class: "alert__body" },
                el("p", { text: `More than one selected file is named ${names.join(", ")}. Results identify documents by filename, so these will look identical in the results.` })
            )
        );
        refs.messages.append(warning);
    }

    function render() {
        renderFileList();
        renderControls();
        renderStepper();
        renderDuplicateNameWarning();
        refs.stale.hidden = !(
            state.phase === "done" && state.lastSignature !== signatureOf(state.files)
        );
    }

    /* ---- Result-area state switching ------------------------------------ */
    function showPanel(name) {
        refs.stateEmpty.hidden = name !== "empty";
        refs.stateLoading.hidden = name !== "loading";
        refs.stateError.hidden = name !== "error";
        refs.results.hidden = name !== "results";
    }

    /* ---- Request --------------------------------------------------------- */
    class RequestError extends Error {
        constructor(kind) {
            super(kind);
            this.kind = kind;
        }
    }

    function requestComparison(files, handlers) {
        const xhr = new XMLHttpRequest();
        const promise = new Promise((resolve, reject) => {
            xhr.open("POST", API.compare);
            xhr.responseType = "text";
            xhr.upload.addEventListener("progress", (e) => {
                if (e.lengthComputable) handlers.onProgress(e.loaded / e.total);
            });
            xhr.upload.addEventListener("load", handlers.onUploaded);
            xhr.addEventListener("load", () => {
                let body = null;
                try {
                    body = JSON.parse(xhr.responseText);
                } catch (_) {
                    body = null;
                }
                resolve({ status: xhr.status, ok: xhr.status >= 200 && xhr.status < 300, body });
            });
            xhr.addEventListener("error", () => reject(new RequestError("network")));
            xhr.addEventListener("abort", () => reject(new RequestError("abort")));

            const formData = new FormData();
            files.forEach((file) => formData.append("files", file));
            xhr.send(formData);
        });
        return { promise, abort: () => xhr.abort() };
    }

    function describeFailure(response) {
        const { status, body } = response;
        const detail = body && typeof body.detail === "string" ? body.detail : null;

        if (detail) {
            return { title: "The server rejected the comparison", text: detail };
        }
        if (status === 422) {
            const msgs = body && Array.isArray(body.detail)
                ? body.detail.map((d) => d && d.msg).filter(Boolean).join("; ")
                : "";
            return {
                title: "The upload request was not valid",
                text: msgs ? `The server could not read the request: ${msgs}.` : "The server could not read the upload request.",
            };
        }
        if (status >= 500) {
            return {
                title: "The server hit an unexpected error",
                text: `The server responded with HTTP ${status}. Try again. If it keeps happening, check the server logs.`,
            };
        }
        return {
            title: "The comparison request failed",
            text: `The server responded with HTTP ${status}${body ? "" : " and no readable message"}.`,
        };
    }

    function showError(title, text) {
        state.phase = "idle";
        refs.errorTitle.textContent = title;
        refs.errorText.textContent = text;
        showPanel("error");
        render();
    }

    async function runComparison() {
        if (state.phase === "running") return;
        if (state.files.length < LIMITS.minFiles) {
            showMessages([{ type: "error", text: "Select at least two documents." }]);
            return;
        }

        const files = state.files.slice();
        state.phase = "running";
        showMessages([]);
        refs.loadingTitle.textContent = "Uploading documents";
        refs.loadingText.textContent = `Sending ${plural(files.length, "document")} to the ASOD server.`;
        refs.progress.classList.remove("progress--indeterminate");
        refs.progressBar.style.width = "0%";
        refs.progressLabel.textContent = "0%";
        showPanel("loading");
        render();

        state.request = requestComparison(files, {
            onProgress: (fraction) => {
                const pct = Math.round(fraction * 100);
                refs.progressBar.style.width = `${pct}%`;
                refs.progressLabel.textContent = `${pct}%`;
            },
            onUploaded: () => {
                refs.loadingTitle.textContent = "Comparing documents";
                refs.loadingText.textContent = "Extracting text and comparing every pair. Large documents can take a little while.";
                refs.progress.classList.add("progress--indeterminate");
                refs.progressBar.style.width = "";
                refs.progressLabel.textContent = "Processing on server";
            },
        });

        try {
            const response = await state.request.promise;
            if (!response.ok) {
                const failure = describeFailure(response);
                showError(failure.title, failure.text);
                return;
            }
            const data = response.body;
            if (!data || !Array.isArray(data.comparisons)) {
                showError(
                    "The response could not be read",
                    "The server replied successfully but the result was not in the expected format."
                );
                return;
            }
            state.lastSignature = signatureOf(files);
            state.phase = "done";
            renderResults(data);
            showPanel("results");
            render();
            if (window.matchMedia("(max-width: 1080px)").matches) {
                refs.results.scrollIntoView({ behavior: "smooth", block: "start" });
            }
        } catch (error) {
            if (error instanceof RequestError && error.kind === "abort") {
                state.phase = "idle";
                showPanel("empty");
                render();
                showMessages([{ type: "info", text: "Comparison cancelled. Your selected documents are unchanged." }]);
            } else {
                showError(
                    "Could not reach the ASOD server",
                    "Check that the backend is running and that you are online, then try again."
                );
                checkHealth();
            }
        } finally {
            state.request = null;
        }
    }

    /* ---- Rendering: results --------------------------------------------- */
    function makeSummaryItem(value, label, kind) {
        const item = el("div", { class: "summary-item" },
            el("span", { class: "summary-item__value", text: String(value) }),
            el("span", { class: "summary-item__label", text: label })
        );
        if (kind) item.dataset.kind = kind;
        return item;
    }

    function makePassage(label, filename, text, start, end) {
        return el("div", { class: "passage" },
            el("div", { class: "passage__label" },
                el("span", { text: label }),
                el("span", { text: filename, attrs: { title: filename } })
            ),
            el("pre", { class: "passage__text", text: text }),
            el("div", {
                class: "passage__offset",
                text: `Characters ${start} to ${end}`,
                attrs: { title: "Offsets refer to the extracted text, not Word page numbers." },
            })
        );
    }

    function makeEvidence(match, type, index, pair) {
        const isNear = type === "near";
        const item = el("div", { class: "evidence-item" });
        item.dataset.type = type;

        item.append(
            el("div", { class: "evidence-item__head" },
                el("span", { class: `badge ${isNear ? "badge--near" : "badge--exact"}`, text: isNear ? "Near copy" : "Exact reuse" }),
                el("span", { class: "evidence-item__index", text: `Evidence ${index + 1}` })
            ),
            el("div", { class: "evidence-grid" },
                makePassage("Source", pair.source_document, match.source_text, match.source_start, match.source_end),
                makePassage("Target", pair.target_document, match.target_text, match.target_start, match.target_end)
            )
        );

        const stats = el("div", { class: "evidence-stats" });
        stats.append(el("span", {}, document.createTextNode("Matched tokens "), el("b", { text: String(match.matched_token_count) })));

        if (typeof match.similarity === "number") {
            const pct = Math.max(0, Math.min(100, match.similarity * 100));
            stats.append(
                el("span", { class: "coverage" },
                    document.createTextNode("Lexical region coverage "),
                    el("b", { text: `${pct.toFixed(1)}%` }),
                    el("span", { class: "coverage__track", attrs: { "aria-hidden": "true" } },
                        el("span", { class: "coverage__fill", attrs: { style: `width:${pct}%` } })
                    )
                ),
                el("span", {}, document.createTextNode("Unmatched source tokens "), el("b", { text: String(match.unmatched_source_tokens) })),
                el("span", {}, document.createTextNode("Unmatched target tokens "), el("b", { text: String(match.unmatched_target_tokens) }))
            );
        }
        item.append(stats);
        return item;
    }

    function evidenceSection(title, near, matches, pair) {
        const section = el("section", { class: "evidence-section" },
            el("h4", { class: `evidence-heading${near ? " evidence-heading--near" : ""}`, text: `${title} (${matches.length})` })
        );
        matches.forEach((match, i) => section.append(makeEvidence(match, near ? "near" : "exact", i, pair)));
        return section;
    }

    function renderPairBody(entry) {
        const { card, data } = entry;
        const body = card.querySelector(".pair-card__body");
        body.replaceChildren();

        const exact = data.exact_matches || [];
        const near = data.near_copy_matches || [];
        const showExact = state.filter !== "near";
        const showNear = state.filter !== "exact";

        if (exact.length === 0 && near.length === 0) {
            body.append(el("div", { class: "empty-inline", text: "No exact or near-copy regions were detected for this pair." }));
        } else {
            if (showExact && exact.length) body.append(evidenceSection("Exact token-sequence overlap", false, exact, data));
            if (showNear && near.length) body.append(evidenceSection("Near-copy regions", true, near, data));
            const visible = (showExact ? exact.length : 0) + (showNear ? near.length : 0);
            if (visible === 0) {
                body.append(el("div", {
                    class: "empty-inline",
                    text: state.filter === "exact"
                        ? "This pair has no exact matches. Switch the filter to see near-copy regions."
                        : "This pair has no near-copy regions. Switch the filter to see exact matches.",
                }));
            }
        }
        entry.rendered = true;
    }

    function makePairCard(data) {
        const exactCount = Number(data.exact_match_count) || 0;
        const nearCount = Number(data.near_copy_region_count) || 0;

        const badges = el("div", { class: "pair-card__badges" });
        if (exactCount + nearCount === 0) {
            badges.append(el("span", { class: "badge badge--none", text: "No overlap detected" }));
        } else {
            if (exactCount) badges.append(el("span", { class: "badge badge--exact", text: `${exactCount} exact` }));
            if (nearCount) badges.append(el("span", { class: "badge badge--near", text: `${nearCount} near copy` }));
        }

        const title = el("div", { class: "pair-title" },
            el("span", { text: data.source_document }),
            icon("swap"),
            el("span", { text: data.target_document })
        );
        title.setAttribute("title", `${data.source_document} compared with ${data.target_document}`);

        const card = el("details", { class: "panel pair-card" },
            el("summary", {},
                icon("chevron", "icon--chevron"),
                el("div", { class: "pair-card__titles" }, title),
                badges
            ),
            el("div", { class: "pair-card__body" })
        );

        const entry = { card, data, rendered: false };
        card.addEventListener("toggle", () => {
            if (card.open && !entry.rendered) renderPairBody(entry);
        });
        return entry;
    }

    function renderResults(data) {
        const comparisons = data.comparisons;
        const exactTotal = comparisons.reduce((s, p) => s + (Number(p.exact_match_count) || 0), 0);
        const nearTotal = comparisons.reduce((s, p) => s + (Number(p.near_copy_region_count) || 0), 0);

        refs.resultsSubtitle.textContent =
            `${plural(data.document_count, "document")} · ${plural(data.pair_count, "unique comparison")}`;

        refs.summary.replaceChildren(
            makeSummaryItem(data.document_count, "Documents compared"),
            makeSummaryItem(data.pair_count, "Unique pairs"),
            makeSummaryItem(exactTotal, "Exact matches", "exact"),
            makeSummaryItem(nearTotal, "Near-copy regions", "near")
        );

        // Document details (from the API's documents[] array)
        refs.docsBody.replaceChildren();
        (data.documents || []).forEach((doc) => {
            refs.docsBody.append(
                el("tr", {},
                    el("td", { text: doc.filename }),
                    el("td", { text: String(doc.file_type || "").toUpperCase() }),
                    el("td", { class: "num", text: Number(doc.word_count).toLocaleString() }),
                    el("td", { class: "num", text: Number(doc.char_count).toLocaleString() })
                )
            );
        });
        $("docsDisclosure").hidden = !(data.documents && data.documents.length);

        // Pair cards: open pairs that have evidence, up to the first three
        state.pairs = comparisons.map(makePairCard);
        refs.pairResults.replaceChildren();
        let opened = 0;
        state.pairs.forEach((entry) => {
            refs.pairResults.append(entry.card);
            const hasEvidence = (Number(entry.data.exact_match_count) || 0) + (Number(entry.data.near_copy_region_count) || 0) > 0;
            if (hasEvidence && opened < 3) {
                entry.card.open = true; // fires toggle, which renders the body
                opened += 1;
            }
        });

        if (comparisons.length === 0) {
            refs.pairResults.append(el("div", { class: "empty-inline", text: "The server returned no pairs to compare." }));
        } else if (exactTotal + nearTotal === 0) {
            refs.pairResults.prepend(
                el("div", { class: "alert alert--success" },
                    icon("check"),
                    el("div", { class: "alert__body" },
                        el("div", { class: "alert__title", text: "No overlap detected" }),
                        el("p", { text: "No exact or near-copy regions were found between any pair of the submitted documents. This does not prove the documents are unrelated." })
                    )
                )
            );
            refs.pairResults.firstChild.style.marginBottom = "var(--space-3)";
        }
    }

    function setFilter(value) {
        state.filter = value;
        refs.filter.querySelectorAll("button").forEach((b) => {
            b.setAttribute("aria-pressed", String(b.dataset.filter === value));
        });
        state.pairs.forEach((entry) => {
            if (entry.card.open) renderPairBody(entry);
            else entry.rendered = false;
        });
    }

    /* ---- API health ------------------------------------------------------ */
    async function checkHealth() {
        refs.status.dataset.state = "checking";
        refs.statusText.textContent = "Checking server";
        try {
            const response = await fetch(API.health, { cache: "no-store" });
            const body = await response.json();
            if (response.ok && body && body.status === "healthy") {
                refs.status.dataset.state = "online";
                refs.statusText.textContent = "Server online";
                return;
            }
            throw new Error("unhealthy");
        } catch (_) {
            refs.status.dataset.state = "offline";
            refs.statusText.textContent = "Server unreachable";
        }
    }

    /* ---- Events ---------------------------------------------------------- */
    refs.browse.addEventListener("click", () => refs.fileInput.click());

    refs.fileInput.addEventListener("change", (event) => {
        addFiles(Array.from(event.target.files));
        refs.fileInput.value = "";
    });

    refs.dropzone.addEventListener("dragover", (event) => {
        event.preventDefault();
        if (state.phase !== "running") refs.dropzone.classList.add("is-dragging");
    });
    refs.dropzone.addEventListener("dragleave", (event) => {
        if (!refs.dropzone.contains(event.relatedTarget)) refs.dropzone.classList.remove("is-dragging");
    });
    refs.dropzone.addEventListener("drop", (event) => {
        event.preventDefault();
        refs.dropzone.classList.remove("is-dragging");
        if (state.phase === "running") return;
        addFiles(Array.from(event.dataTransfer.files));
    });

    // Stop the browser from navigating to a file dropped outside the dropzone.
    ["dragover", "drop"].forEach((type) => {
        window.addEventListener(type, (event) => {
            if (!refs.dropzone.contains(event.target)) event.preventDefault();
        });
    });

    refs.clearAll.addEventListener("click", clearFiles);
    refs.compare.addEventListener("click", runComparison);
    refs.retry.addEventListener("click", runComparison);
    refs.cancel.addEventListener("click", () => state.request && state.request.abort());

    refs.filter.addEventListener("click", (event) => {
        const button = event.target.closest("button[data-filter]");
        if (button) setFilter(button.dataset.filter);
    });
    refs.expandAll.addEventListener("click", () => state.pairs.forEach((e) => (e.card.open = true)));
    refs.collapseAll.addEventListener("click", () => state.pairs.forEach((e) => (e.card.open = false)));

    /* ---- Init ------------------------------------------------------------ */
    showPanel("empty");
    render();
    checkHealth();
})();

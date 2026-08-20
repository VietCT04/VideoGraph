const FALLBACK_FIXTURE = {
  creator: {
    creator_id: "creator_alice",
    handle: "alicebeauty",
    display_name: "Alice Beauty",
    memory_enabled: false,
  },
  content: [],
  jobs: [],
  facts: [],
};

/**
 * The reducer keeps privacy-sensitive transitions explicit and immutable.
 * @param {object} state
 * @param {{type: string, contentId?: string, jobId?: string, factId?: string, value?: boolean, correction?: string}} action
 * @returns {{state: object, error: string}}
 */
export function reduceCreatorState(state, action) {
  if (action.type === "set-memory-enabled") {
    if (action.value) {
      return {
        state: { ...state, creator: { ...state.creator, memory_enabled: true } },
        error: "",
      };
    }

    return {
      state: {
        ...state,
        creator: { ...state.creator, memory_enabled: false },
        content: state.content.map((item) => ({ ...item, included: false, excluded: true })),
      },
      error: "",
    };
  }

  if (action.type === "set-content-included") {
    if (action.value && !state.creator.memory_enabled) {
      return { state, error: "Enable AI Memory before selecting content." };
    }

    return {
      state: {
        ...state,
        content: state.content.map((item) =>
          item.content_id === action.contentId
            ? { ...item, included: Boolean(action.value), excluded: !action.value }
            : item,
        ),
      },
      error: "",
    };
  }

  if (action.type === "start-indexing") {
    if (!state.creator.memory_enabled) {
      return { state, error: "Enable AI Memory before building memory." };
    }

    const selectedIds = new Set(
      state.content.filter((item) => item.included && !item.excluded).map((item) => item.content_id),
    );
    if (!selectedIds.size) {
      return { state, error: "Select at least one content item before building memory." };
    }

    const knownIds = new Set(state.jobs.map((job) => job.content_id));
    const newJobs = state.content
      .filter((item) => selectedIds.has(item.content_id) && !knownIds.has(item.content_id))
      .map((item) => ({
        job_id: `job_${item.content_id}`,
        content_id: item.content_id,
        status: "queued",
        progress: 0,
        stage: "queued",
      }));

    return {
      state: {
        ...state,
        jobs: [
          ...state.jobs.map((job) =>
            selectedIds.has(job.content_id) && job.status === "failed"
              ? { ...job, status: "queued", progress: 0, stage: "queued", error: "" }
              : job,
          ),
          ...newJobs,
        ],
      },
      error: "",
    };
  }

  if (action.type === "retry-job") {
    const job = state.jobs.find((candidate) => candidate.job_id === action.jobId);
    const item = state.content.find((candidate) => candidate.content_id === job?.content_id);
    if (!job || job.status !== "failed") {
      return { state, error: "Only failed jobs can be retried." };
    }
    if (!state.creator.memory_enabled || !item?.included || item.excluded) {
      return { state, error: "Re-select the content while AI Memory is enabled before retrying." };
    }

    return {
      state: {
        ...state,
        jobs: state.jobs.map((candidate) =>
          candidate.job_id === action.jobId
            ? { ...candidate, status: "queued", progress: 0, stage: "queued", error: "" }
            : candidate,
        ),
      },
      error: "",
    };
  }

  if (action.type === "set-fact-visibility") {
    return {
      state: {
        ...state,
        facts: state.facts.map((fact) =>
          fact.fact_id === action.factId
            ? {
                ...fact,
                visibility: action.value ? "visible" : "hidden",
                review_status: action.value ? fact.review_status : "hidden",
              }
            : fact,
        ),
      },
      error: "",
    };
  }

  if (action.type === "confirm-fact") {
    return {
      state: {
        ...state,
        facts: state.facts.map((fact) =>
          fact.fact_id === action.factId ? { ...fact, review_status: "confirmed" } : fact,
        ),
      },
      error: "",
    };
  }

  if (action.type === "correct-fact") {
    const correction = (action.correction || "").trim();
    if (!correction) {
      return { state, error: "Enter a corrected object label before saving." };
    }

    return {
      state: {
        ...state,
        facts: state.facts.map((fact) =>
          fact.fact_id === action.factId
            ? { ...fact, object_label: correction, correction, review_status: "corrected" }
            : fact,
        ),
      },
      error: "",
    };
  }

  return { state, error: "Unknown creator control action." };
}

/**
 * This projection is the UI's privacy invariant: a disabled memory, excluded content,
 * or hidden fact cannot appear in viewer-visible state.
 * @param {object} state
 */
export function getViewerVisibleState(state) {
  if (!state.creator.memory_enabled) {
    return { contentIds: [], facts: [] };
  }

  const visibleContentIds = new Set(
    state.content
      .filter((item) => item.included && !item.excluded)
      .map((item) => item.content_id),
  );
  const facts = state.facts.filter(
    (fact) =>
      fact.visibility === "visible" &&
      fact.source_content_ids.some((contentId) => visibleContentIds.has(contentId)),
  );
  return { contentIds: [...visibleContentIds], facts };
}

async function loadFixture() {
  try {
    const response = await fetch("../fixtures/creator-controls-fixtures.json", {
      headers: { Accept: "application/json" },
    });
    if (!response.ok) {
      throw new Error("Fixture request failed");
    }
    return await response.json();
  } catch {
    return FALLBACK_FIXTURE;
  }
}

function createText(tagName, text, className = "") {
  const element = document.createElement(tagName);
  element.textContent = text;
  if (className) {
    element.className = className;
  }
  return element;
}

function applyAction(action, message = "Action saved in the local fixture.") {
  const result = reduceCreatorState(state, action);
  state = result.state;
  const status = document.querySelector("#action-status");
  status.className = result.error ? "status error" : "status";
  status.textContent = result.error || message;
  render();
}

function renderContent() {
  const list = document.querySelector("#content-list");
  list.replaceChildren();

  state.content.forEach((item) => {
    const row = document.createElement("label");
    row.className = "content-item";
    const checkbox = document.createElement("input");
    checkbox.type = "checkbox";
    checkbox.checked = item.included && !item.excluded;
    checkbox.disabled = !state.creator.memory_enabled;
    checkbox.addEventListener("change", () =>
      applyAction({ type: "set-content-included", contentId: item.content_id, value: checkbox.checked }),
    );

    const copy = document.createElement("span");
    copy.className = "content-copy";
    copy.append(createText("strong", item.title), createText("span", `${item.kind} · ${item.content_id}`));
    row.append(checkbox, copy, createText("span", item.status, `badge ${item.status}`));
    list.append(row);
  });
}

function renderJobs() {
  const list = document.querySelector("#job-list");
  list.replaceChildren();
  if (!state.jobs.length) {
    list.append(createText("p", "No indexing jobs yet.", "empty-list"));
    return;
  }

  state.jobs.forEach((job) => {
    const item = document.createElement("article");
    item.className = "job-item";
    const copy = document.createElement("div");
    copy.className = "job-copy";
    copy.append(
      createText("strong", job.content_id),
      createText("span", `${job.status} · ${job.stage}${job.error ? ` · ${job.error}` : ""}`),
    );
    const actions = document.createElement("div");
    if (job.status === "failed") {
      const retry = createText("button", "Retry", "secondary-button");
      retry.type = "button";
      retry.addEventListener("click", () => applyAction({ type: "retry-job", jobId: job.job_id }));
      actions.append(retry);
    }
    item.append(copy, createText("span", `${job.progress}%`, `badge ${job.status}`), actions);
    const progress = document.createElement("div");
    progress.className = "job-progress";
    const bar = document.createElement("span");
    bar.style.width = `${job.progress}%`;
    progress.append(bar);
    item.append(progress);
    list.append(item);
  });
}

function renderFacts() {
  const list = document.querySelector("#fact-list");
  list.replaceChildren();
  if (!state.facts.length) {
    list.append(createText("p", "No extracted facts yet.", "empty-list"));
    return;
  }

  state.facts.forEach((fact) => {
    const item = document.createElement("article");
    item.className = "fact-item";
    item.append(
      createText("h3", `${fact.subject_label} → ${fact.object_label}`),
      createText("p", fact.relation, "fact-relation"),
      createText("p", `${fact.review_status} · ${fact.visibility}`, "fact-meta"),
      createText("p", `Evidence: ${fact.source_moment_ids.join(", ")}`, "fact-meta"),
    );

    const actions = document.createElement("div");
    actions.className = "fact-actions";
    const correctionInput = document.createElement("input");
    correctionInput.type = "text";
    correctionInput.placeholder = "Corrected object label";
    correctionInput.setAttribute("aria-label", `Correct ${fact.object_label}`);
    const correct = createText("button", "Correct", "secondary-button");
    correct.type = "button";
    correct.addEventListener("click", () =>
      applyAction({ type: "correct-fact", factId: fact.fact_id, correction: correctionInput.value }),
    );
    const confirm = createText("button", "Confirm", "secondary-button");
    confirm.type = "button";
    confirm.addEventListener("click", () => applyAction({ type: "confirm-fact", factId: fact.fact_id }));
    const hide = createText("button", fact.visibility === "hidden" ? "Unhide" : "Hide", "danger-button");
    hide.type = "button";
    hide.addEventListener("click", () =>
      applyAction({ type: "set-fact-visibility", factId: fact.fact_id, value: fact.visibility === "hidden" }),
    );
    actions.append(correctionInput, correct, confirm, hide);
    item.append(actions);
    list.append(item);
  });
}

function render() {
  const toggle = document.querySelector("#memory-toggle");
  toggle.textContent = state.creator.memory_enabled ? "Disable AI Memory" : "Enable AI Memory";
  toggle.className = state.creator.memory_enabled ? "danger-button" : "";
  document.querySelector("#memory-status").textContent = state.creator.memory_enabled
    ? "AI Memory is enabled. Select individual content before building memory."
    : "AI Memory is disabled. Nothing is viewer-visible until you opt in.";

  const visible = getViewerVisibleState(state);
  document.querySelector("#visibility-status").textContent = visible.contentIds.length
    ? `Viewer-visible content: ${visible.contentIds.join(", ")}.`
    : "Viewer-visible content: none.";
  const selectedCount = state.content.filter((item) => item.included && !item.excluded).length;
  document.querySelector("#selection-status").textContent = state.creator.memory_enabled
    ? `${selectedCount} content item${selectedCount === 1 ? "" : "s"} selected.`
    : "Enable AI Memory to select content; previously included content stays excluded until re-selected.";
  document.querySelector("#build-memory").disabled = !state.creator.memory_enabled;
  renderContent();
  renderJobs();
  renderFacts();
}

let state = FALLBACK_FIXTURE;

document.querySelector("#memory-toggle").addEventListener("click", () => {
  applyAction({ type: "set-memory-enabled", value: !state.creator.memory_enabled });
});
document.querySelector("#build-memory").addEventListener("click", () => {
  applyAction({ type: "start-indexing" }, "Selected content queued for asynchronous indexing.");
});

loadFixture().then((fixture) => {
  state = fixture;
  render();
});
render();

const FALLBACK_FIXTURES = {
  creators: [
    { creator_id: "creator_alice", handle: "alicebeauty", display_name: "Alice Beauty" },
    { creator_id: "creator_bob", handle: "bobbuilds", display_name: "Bob Builds" },
  ],
  responses: {},
};

/**
 * Parse the one creator mention form documented by the viewer API direction.
 * @param {string} input
 * @returns {{hasMention: boolean, handle: string, question: string, partialHandle: string}}
 */
export function parseCreatorMention(input) {
  const trimmed = input.trim();
  const match = trimmed.match(/^@([a-z0-9_-]*)(?:\s+(.*))?$/i);

  if (!match) {
    return { hasMention: false, handle: "", question: trimmed, partialHandle: "" };
  }

  const handle = match[1].toLowerCase();
  return {
    hasMention: true,
    handle,
    question: (match[2] || "").trim(),
    partialHandle: handle,
  };
}

/**
 * @param {string} input
 * @param {Array<{creator_id: string, handle: string, display_name: string}>} creators
 */
export function suggestCreators(input, creators) {
  const parsed = parseCreatorMention(input);
  if (!parsed.hasMention) {
    return [];
  }

  return creators.filter((creator) => creator.handle.startsWith(parsed.partialHandle));
}

/** @returns {{query: string, phase: string, response: object|null, error: string, suggestions: Array<object>}} */
export function createInitialState() {
  return {
    query: "",
    phase: "idle",
    response: null,
    error: "",
    suggestions: [],
  };
}

/**
 * @param {ReturnType<typeof createInitialState>} state
 * @param {Partial<ReturnType<typeof createInitialState>>} patch
 */
export function updateState(state, patch) {
  return { ...state, ...patch };
}

async function loadFixtures() {
  try {
    const response = await fetch("../fixtures/viewer-query-fixtures.json", {
      headers: { Accept: "application/json" },
    });
    if (!response.ok) {
      throw new Error("Fixture request failed");
    }
    return await response.json();
  } catch {
    return FALLBACK_FIXTURES;
  }
}

/**
 * This client is deliberately local. It mirrors the conceptual query response in docs/API.md
 * without inventing a network endpoint before the backend query contract is frozen.
 * @param {string} query
 */
export async function queryFixture(query) {
  const fixtures = await loadFixtures();
  const parsed = parseCreatorMention(query);

  if (!parsed.hasMention || !parsed.handle) {
    throw new Error("Start the question with a creator mention such as @alicebeauty.");
  }
  if (!parsed.question) {
    throw new Error("Add a question after the creator mention.");
  }
  if (parsed.question.toLowerCase().includes("error")) {
    throw new Error("The fixture query failed so the error state can be previewed.");
  }

  const response = fixtures.responses[parsed.handle];
  if (!response) {
    return { creator_id: "", creator_handle: parsed.handle, results: [], answer: null };
  }

  return response;
}

function formatTimestamp(milliseconds) {
  const totalSeconds = Math.floor(milliseconds / 1000);
  const hours = Math.floor(totalSeconds / 3600);
  const minutes = Math.floor((totalSeconds % 3600) / 60);
  const seconds = totalSeconds % 60;
  const clock = [minutes, seconds].map((part) => String(part).padStart(2, "0")).join(":");
  return hours > 0 ? `${hours}:${clock}` : clock;
}

function createText(tagName, text, className = "") {
  const element = document.createElement(tagName);
  element.textContent = text;
  if (className) {
    element.className = className;
  }
  return element;
}

function renderSuggestions(state) {
  const list = document.querySelector("#creator-suggestions");
  const input = document.querySelector("#query-input");
  list.replaceChildren();

  if (!state.suggestions.length) {
    list.hidden = true;
    input.setAttribute("aria-expanded", "false");
    return;
  }

  state.suggestions.forEach((creator) => {
    const item = document.createElement("li");
    const button = createText("button", `@${creator.handle} — ${creator.display_name}`);
    button.type = "button";
    button.addEventListener("click", () => {
      input.value = `@${creator.handle} `;
      input.focus();
      renderSuggestions({ ...state, suggestions: [] });
    });
    item.append(button);
    list.append(item);
  });

  list.hidden = false;
  input.setAttribute("aria-expanded", "true");
}

function renderEvidence(evidence) {
  const item = document.createElement("li");
  item.className = "evidence-item";

  const copy = document.createElement("div");
  copy.className = "evidence-copy";
  copy.append(
    createText("strong", `${evidence.title} — ${formatTimestamp(evidence.start_ms)}`),
    createText(
      "span",
      `${evidence.source_kind} · ${evidence.content_id} · ${formatTimestamp(evidence.start_ms)}–${formatTimestamp(evidence.end_ms)}`,
    ),
  );

  const jump = createText("button", "Jump to moment", "jump-button");
  jump.type = "button";
  jump.addEventListener("click", () => {
    window.location.hash = evidence.moment_id;
    const status = document.querySelector("#query-status");
    status.className = "status";
    status.textContent = `Moment selected: ${evidence.content_id} at ${formatTimestamp(evidence.start_ms)}.`;
  });

  item.append(copy, jump);
  return item;
}

function renderResults(state) {
  const results = document.querySelector("#results");
  const status = document.querySelector("#query-status");
  results.replaceChildren();
  results.setAttribute("aria-busy", state.phase === "loading" ? "true" : "false");
  status.className = "status";

  if (state.phase === "loading") {
    results.append(createText("p", "Searching grounded creator memory…", "loading"));
    status.textContent = "Searching…";
    return;
  }

  if (state.phase === "error") {
    status.className = "status error";
    status.textContent = state.error;
    return;
  }

  if (state.phase !== "success" || !state.response) {
    return;
  }

  if (!state.response.results.length) {
    results.append(
      createText("p", `No grounded moments were found for @${state.response.creator_handle}.`, "empty"),
    );
    status.textContent = "No grounded results.";
    return;
  }

  if (state.response.answer) {
    results.append(createText("p", state.response.answer, "answer"));
  }

  state.response.results.forEach((result) => {
    const card = document.createElement("article");
    card.className = "result-card";
    card.append(createText("h3", result.label), createText("p", result.summary, "summary"));

    const evidenceList = document.createElement("ul");
    evidenceList.className = "evidence-list";
    result.evidence.forEach((evidence) => evidenceList.append(renderEvidence(evidence)));
    card.append(evidenceList);
    results.append(card);
  });
  status.textContent = "Grounded results loaded.";
}

const form = document.querySelector("#query-form");
const input = document.querySelector("#query-input");
let state = createInitialState();
let creators = FALLBACK_FIXTURES.creators;

loadFixtures().then((fixtures) => {
  creators = fixtures.creators;
});

input.addEventListener("input", () => {
  state = updateState(state, {
    query: input.value,
    suggestions: suggestCreators(input.value, creators),
  });
  renderSuggestions(state);
});

form.addEventListener("submit", async (event) => {
  event.preventDefault();
  state = updateState(state, {
    query: input.value,
    phase: "loading",
    response: null,
    error: "",
    suggestions: [],
  });
  renderSuggestions(state);
  renderResults(state);

  try {
    const response = await queryFixture(state.query);
    state = updateState(state, { phase: "success", response });
  } catch (error) {
    state = updateState(state, {
      phase: "error",
      error: error instanceof Error ? error.message : "The query failed.",
    });
  }
  renderResults(state);
});

renderResults(state);

/**
 * Frontend Application State & Orchestration Logic
 * Designed for Zomato AI Concierge (Stitch Nocturne Theme)
 */

import {
  renderChoicesSummary,
  renderRestaurantCard,
  renderSkeletonCards,
  renderEmptyState,
} from "./components.js";

// Determine API Base URL dynamically (supports local dev, Vercel proxy, or explicit override)
const API_BASE = window.API_BASE || (
  (window.location.hostname === "localhost" || window.location.hostname === "127.0.0.1") && window.location.port !== "8000"
    ? "http://localhost:8000/api/v1"
    : "/api/v1"
);

if (window.location.protocol === "file:") {
  console.warn("Notice: Opening index.html via file:// blocks fetch() calls in some browsers. Please use http://localhost:3000.");
}

const state = {
  location: "",
  budget_tier: "medium",
  max_cost_for_two: 1500,
  min_rating: 4.0,
  cuisines: [],
  additional_preferences: ["romantic", "outdoor seating"],
  query: "Cozy authentic Italian pizza in Indiranagar under ₹1200 with outdoor seating",
  loading: false,
  currentView: "results", // 'results' | 'skeleton' | 'empty'
};

document.addEventListener("DOMContentLoaded", () => {
  initEventListeners();
  loadInitialCatalog();
  // Fetch initial recommendation with default state
  fetchRecommendations();
});

function initEventListeners() {
  // 1. Natural Language Search Input
  const queryInput = document.getElementById("natural-query-input");
  if (queryInput) {
    queryInput.value = state.query;
    queryInput.addEventListener("input", (e) => {
      state.query = e.target.value;
    });
    queryInput.addEventListener("keydown", (e) => {
      if (e.key === "Enter") {
        e.preventDefault();
        fetchRecommendations();
      }
    });
  }

  // 2. Trigger Search Buttons
  const triggerSearchBtn = document.getElementById("trigger-search-btn");
  if (triggerSearchBtn) {
    triggerSearchBtn.addEventListener("click", () => fetchRecommendations());
  }

  const regenerateCta = document.getElementById("regenerate-cta");
  if (regenerateCta) {
    regenerateCta.addEventListener("click", () => fetchRecommendations());
  }

  // 3. Prompt Chips
  document.querySelectorAll(".prompt-chip").forEach((chip) => {
    chip.addEventListener("click", () => {
      const promptText = chip.getAttribute("data-prompt");
      if (promptText) {
        state.query = promptText;
        if (queryInput) queryInput.value = promptText;
        fetchRecommendations();
      }
    });
  });

  // 4. District / Location Selector
  const districtSelector = document.getElementById("district-selector");
  if (districtSelector) {
    state.location = districtSelector.value.trim();
    districtSelector.addEventListener("change", (e) => {
      state.location = e.target.value.trim();
      fetchRecommendations();
    });
  }

  // 5. Budget Toggles
  const budgetToggles = document.querySelectorAll(".budget-toggle");
  budgetToggles.forEach((btn) => {
    btn.addEventListener("click", () => {
      budgetToggles.forEach((b) => {
        b.classList.remove("active", "bg-primary-container/20", "text-white", "border", "border-primary-container", "shadow-[0_0_12px_rgba(255,85,59,0.3)]");
        b.classList.add("text-on-surface-variant");
      });
      btn.classList.remove("text-on-surface-variant");
      btn.classList.add("active", "bg-primary-container/20", "text-white", "border", "border-primary-container", "shadow-[0_0_12px_rgba(255,85,59,0.3)]");
      
      state.budget_tier = btn.dataset.tier || "medium";
      if (state.budget_tier === "low") state.max_cost_for_two = 500;
      else if (state.budget_tier === "medium") state.max_cost_for_two = 1500;
      else state.max_cost_for_two = 3500;

      fetchRecommendations();
    });
  });

  // 6. Rating Chips
  const ratingChips = document.querySelectorAll(".rating-chip");
  ratingChips.forEach((btn) => {
    btn.addEventListener("click", () => {
      ratingChips.forEach((b) => {
        b.classList.remove("active", "bg-secondary-container/20", "border-secondary", "text-white", "glow-amber-pill");
        b.classList.add("text-on-surface-variant", "border-white/5");
      });
      btn.classList.remove("text-on-surface-variant", "border-white/5");
      btn.classList.add("active", "bg-secondary-container/20", "border-secondary", "text-white", "glow-amber-pill");

      state.min_rating = parseFloat(btn.dataset.rating || "4.0");
      fetchRecommendations();
    });
  });

  // 7. Vibe Match Pills
  const vibePills = document.querySelectorAll(".vibe-pill");
  vibePills.forEach((pill) => {
    pill.addEventListener("click", () => {
      pill.classList.toggle("active");
      const pref = pill.dataset.pref || pill.textContent.replace(/^[^\w]+/, "").trim().toLowerCase();
      
      if (pill.classList.contains("active")) {
        pill.className = "vibe-pill active px-3 py-1 rounded-full text-xs bg-primary-container/20 border border-primary-container text-white font-medium shadow-sm transition-all";
        if (!state.additional_preferences.includes(pref)) {
          state.additional_preferences.push(pref);
        }
      } else {
        pill.className = "vibe-pill px-3 py-1 rounded-full text-xs bg-surface-container border border-white/5 text-on-surface-variant hover:text-on-surface transition-all";
        state.additional_preferences = state.additional_preferences.filter((p) => p !== pref);
      }
      fetchRecommendations();
    });
  });

  // 8. Cuisine Chips
  bindCuisinePills();

  // 9. View State Switcher Tabs (Prototype Mode Preview)
  const tabResults = document.getElementById("view-results-tab");
  const tabSkeleton = document.getElementById("view-skeleton-tab");
  const tabEmpty = document.getElementById("view-empty-tab");

  if (tabResults) tabResults.addEventListener("click", () => switchView("results"));
  if (tabSkeleton) tabSkeleton.addEventListener("click", () => switchView("skeleton"));
  if (tabEmpty) tabEmpty.addEventListener("click", () => switchView("empty"));

  // 10. Empty state recovery clicks
  document.addEventListener("click", (e) => {
    if (e.target.closest("#relax-filters-btn")) {
      // Relax filters: clear location & cuisines, set medium budget
      state.min_rating = 3.5;
      state.budget_tier = "medium";
      state.max_cost_for_two = 2000;
      state.location = "";
      state.cuisines = [];
      const dist = document.getElementById("district-selector");
      if (dist) dist.value = "";
      fetchRecommendations();
    }
    if (e.target.closest("#switch-location-btn")) {
      state.location = "";
      const dist = document.getElementById("district-selector");
      if (dist) dist.value = "";
      fetchRecommendations();
    }
  });
}

function switchView(target) {
  state.currentView = target;
  const viewResults = document.getElementById("view-results");
  const viewSkeleton = document.getElementById("view-skeleton");
  const viewEmpty = document.getElementById("view-empty");

  const btnResults = document.getElementById("view-results-tab");
  const btnSkeleton = document.getElementById("view-skeleton-tab");
  const btnEmpty = document.getElementById("view-empty-tab");

  if (!viewResults || !viewSkeleton || !viewEmpty) return;

  viewResults.classList.add("hidden");
  viewSkeleton.classList.add("hidden");
  viewEmpty.classList.add("hidden");

  [btnResults, btnSkeleton, btnEmpty].forEach((btn) => {
    if (btn) {
      btn.className = "state-tab-btn px-3.5 py-1.5 rounded-lg text-body-sm font-body-sm text-on-surface-variant hover:text-on-surface transition-all";
    }
  });

  const activeTabClass = "state-tab-btn active px-3.5 py-1.5 rounded-lg text-body-sm font-body-sm font-semibold transition-all bg-primary-container text-white shadow";

  if (target === "results") {
    viewResults.classList.remove("hidden");
    if (btnResults) btnResults.className = activeTabClass;
  } else if (target === "skeleton") {
    viewSkeleton.classList.remove("hidden");
    if (btnSkeleton) btnSkeleton.className = activeTabClass;
  } else if (target === "empty") {
    viewEmpty.classList.remove("hidden");
    if (btnEmpty) btnEmpty.className = activeTabClass;
  }
}

function bindCuisinePills() {
  const allBtn = document.querySelector('.cuisine-pill[data-cuisine=""]');
  const specificBtns = document.querySelectorAll('.cuisine-pill:not([data-cuisine=""])');

  if (allBtn) {
    allBtn.onclick = () => {
      state.cuisines = [];
      specificBtns.forEach((b) => {
        b.className = "cuisine-pill px-3 py-1.5 rounded-lg text-xs font-medium bg-surface-container border border-white/5 text-on-surface-variant hover:text-on-surface transition-all";
      });
      allBtn.className = "cuisine-pill active px-3 py-1.5 rounded-lg text-xs font-semibold bg-primary-container/20 border border-primary-container text-white shadow-sm transition-all";
      fetchRecommendations();
    };
  }

  specificBtns.forEach((btn) => {
    btn.onclick = () => {
      btn.classList.toggle("active");
      const c = btn.dataset.cuisine || btn.textContent.trim();

      if (btn.classList.contains("active")) {
        btn.className = "cuisine-pill active px-3 py-1.5 rounded-lg text-xs font-semibold bg-primary-container/20 border border-primary-container text-white shadow-sm transition-all";
        if (!state.cuisines.includes(c)) state.cuisines.push(c);
        if (allBtn) {
          allBtn.className = "cuisine-pill px-3 py-1.5 rounded-lg text-xs font-medium bg-surface-container border border-white/5 text-on-surface-variant hover:text-on-surface transition-all";
        }
      } else {
        btn.className = "cuisine-pill px-3 py-1.5 rounded-lg text-xs font-medium bg-surface-container border border-white/5 text-on-surface-variant hover:text-on-surface transition-all";
        state.cuisines = state.cuisines.filter((x) => x !== c);
        if (state.cuisines.length === 0 && allBtn) {
          allBtn.className = "cuisine-pill active px-3 py-1.5 rounded-lg text-xs font-semibold bg-primary-container/20 border border-primary-container text-white shadow-sm transition-all";
        }
      }
      fetchRecommendations();
    };
  });
}

async function fetchRecommendations() {
  if (state.loading) return;
  state.loading = true;

  // Show skeleton loader while fetching
  switchView("skeleton");

  const summaryContainer = document.getElementById("summary-container");
  const resultsContainer = document.getElementById("recommendations-grid");

  const payload = {
    query: state.query || undefined,
    location: state.location || undefined,
    budget_tier: state.budget_tier || undefined,
    max_cost_for_two: state.max_cost_for_two || undefined,
    min_rating: state.min_rating || undefined,
    cuisines: state.cuisines.length > 0 ? state.cuisines : undefined,
    additional_preferences: state.additional_preferences.length > 0 ? state.additional_preferences : undefined,
    top_k: 6,
  };

  const startTime = performance.now();

  try {
    const res = await fetch(`${API_BASE}/recommend`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });

    const elapsed = Math.round(performance.now() - startTime);

    // Update latency counter in navbar if present
    const latencyEl = document.getElementById("rag-latency-text");
    if (latencyEl) latencyEl.textContent = `${elapsed}ms RAG Latency`;

    if (!res.ok) {
      throw new Error(`API Error: ${res.status}`);
    }

    const data = await res.json();

    if (data.recommendations && data.recommendations.length > 0) {
      // Render Summary
      if (summaryContainer && data.choices_summary) {
        summaryContainer.innerHTML = renderChoicesSummary(
          data.choices_summary,
          data.query_summary?.relaxation_notice,
          data.query_summary?.total_analyzed
        );
      } else if (summaryContainer) {
        summaryContainer.innerHTML = "";
      }

      // Render Cards
      if (resultsContainer) {
        resultsContainer.innerHTML = data.recommendations.map(renderRestaurantCard).join("");
      }

      // Switch to results view
      switchView("results");
    } else {
      // Empty State
      const emptyView = document.getElementById("view-empty");
      if (emptyView) {
        emptyView.innerHTML = renderEmptyState("No restaurants matched your filters");
      }
      switchView("empty");
    }
  } catch (err) {
    console.warn("Recommendation API call error:", err);
    const emptyView = document.getElementById("view-empty");
    if (emptyView) {
      emptyView.innerHTML = renderEmptyState("Could not connect to recommendation engine. Ensure backend is running on :8000");
    }
    switchView("empty");
  } finally {
    state.loading = false;
  }
}

async function loadInitialCatalog() {
  // Populate locations dropdown from backend
  try {
    const locRes = await fetch(`${API_BASE}/locations`);
    if (locRes.ok) {
      const locations = await locRes.json();
      const select = document.getElementById("district-selector");
      if (select && locations.length > 0) {
        const currentVal = select.value;
        const optionsHtml = ['<option value="" selected>🌐 All Districts / Cities (Any)</option>']
          .concat(locations.map((l) => `<option value="${l}">${l}</option>`))
          .join("");
        select.innerHTML = optionsHtml;
        if (currentVal && locations.includes(currentVal)) {
          select.value = currentVal;
        }
      }
    }
  } catch (e) {
    // Keep preset fallback dropdown
  }

  // Populate cuisines chips if backend has distinct list
  try {
    const cuiRes = await fetch(`${API_BASE}/cuisines`);
    if (cuiRes.ok) {
      const cuisines = await cuiRes.json();
      const container = document.getElementById("cuisine-container");
      if (container && cuisines.length > 0) {
        const topCuisines = cuisines.slice(0, 10);
        const chipsHtml = [
          '<button type="button" class="cuisine-pill active px-3 py-1.5 rounded-lg text-xs font-semibold bg-primary-container/20 border border-primary-container text-white shadow-sm transition-all" data-cuisine="">All Cuisines</button>'
        ]
          .concat(
            topCuisines.map(
              (c) => `<button type="button" class="cuisine-pill px-3 py-1.5 rounded-lg text-xs font-medium bg-surface-container border border-white/5 text-on-surface-variant hover:text-on-surface transition-all" data-cuisine="${c}">${c}</button>`
            )
          )
          .join("");
        container.innerHTML = chipsHtml;
        bindCuisinePills();
      }
    }
  } catch (e) {
    // Keep preset fallback chips
  }
}

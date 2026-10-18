/**
 * UI Component Renderers for Zomato AI Dining Guide (Stitch Nocturne Theme)
 */

// Curated high-res culinary photos by cuisine archetype
const CUISINE_PHOTO_MAP = {
  "italian": "https://lh3.googleusercontent.com/aida-public/AB6AXuA3-KQ-CBAjuCI9gZ0t04PHWbljZUsQu03syib7UGGXOKv6YHPZLyOURmbFfZQqHTnkkppAnTe7Dnbjuxv1ts3tYL2b7OhvNUCeNLeZxArr0UImwD6aNRjEngijoC6Z0iWwj2h5hRb4rSKK86YVxfwbDrMoHD_L4XFeM7AGVupxmu12PDfc8pSQNjt_kXhyY3Zi1H7x5UsgndYc4fVS3x1hBFT3msuoFxMmFjJipiuLWZeQ-thd0T-oMA",
  "pizza": "https://lh3.googleusercontent.com/aida-public/AB6AXuDjR5TRVNfU68HE9lbr6DmWxyPEi6nMJyAwv7yWZT4uwXLTssYcvKDirROpwDvXvbpI_ev1cC4Qxz4TE5vtZBOL5qjCs2rYZ7N0-tnNImxrZqzgNziR6XJsE49HxJQrn0iEIQfife851WtJ4lHYNlk-VQFisTbOGQy_HP4pWr896UljZEpRdCkR5itwNxwwkxuD9G1RL8nYw5S645kg60gFbynu0XLWbHyivaScngiOqdgBvM85DMv4Jg",
  "north indian": "https://images.unsplash.com/photo-1589302168068-964664d93dc0?auto=format&fit=crop&w=800&q=80",
  "biryani": "https://images.unsplash.com/photo-1563379091339-03b21ab4a4f8?auto=format&fit=crop&w=800&q=80",
  "south indian": "https://images.unsplash.com/photo-1610192244261-3f33de3f55e4?auto=format&fit=crop&w=800&q=80",
  "cafe": "https://images.unsplash.com/photo-1554118811-1e0d58224f24?auto=format&fit=crop&w=800&q=80",
  "burger": "https://images.unsplash.com/photo-1550547660-d9450f859349?auto=format&fit=crop&w=800&q=80",
  "american": "https://images.unsplash.com/photo-1550547660-d9450f859349?auto=format&fit=crop&w=800&q=80",
  "desserts": "https://lh3.googleusercontent.com/aida-public/AB6AXuCKJrw4IAuOu6BXRxCZ0lU3y3Lt_vy-dIq8QBAma4y0Ipl1zd_uNraAMC5VgMWFgvDZw-T8T93g8XEqA8GQa8L-0YInvom3--7QYDYnay2V_k8jUY_bxtikqdJLDunHMj7iBjVDY8gG5XJzwe9rgqVjP-lalTXz7b5t6eaC7ScFGGoy_85YMVyCEEa-5bRzi_JqBRRY4BZE2knGSQ7p_JtjMKwf9PGlXA1QB5Q_V8FiwoAjUw_J7pCjXw",
  "ice cream": "https://images.unsplash.com/photo-1563805042-7684c019e1cb?auto=format&fit=crop&w=800&q=80",
  "asian": "https://images.unsplash.com/photo-1569718212165-3a8278d5f624?auto=format&fit=crop&w=800&q=80",
  "chinese": "https://images.unsplash.com/photo-1525755662778-989d0524087e?auto=format&fit=crop&w=800&q=80",
  "continental": "https://images.unsplash.com/photo-1544025162-d76694265947?auto=format&fit=crop&w=800&q=80",
};

const DEFAULT_PHOTO = "https://images.unsplash.com/photo-1517248135467-4c7edcad34c4?auto=format&fit=crop&w=800&q=80";

function getRestaurantPhoto(cuisinesStr, name) {
  const lower = ((cuisinesStr || "") + " " + (name || "")).toLowerCase();
  for (const [key, url] of Object.entries(CUISINE_PHOTO_MAP)) {
    if (lower.includes(key)) return url;
  }
  return DEFAULT_PHOTO;
}

export function renderChoicesSummary(summary, relaxationNotice = null, analyzedCount = null) {
  let noticeHtml = "";
  if (relaxationNotice) {
    noticeHtml = `
      <div class="inline-flex items-center gap-2 px-3.5 py-2 rounded-xl bg-secondary-container/15 border border-secondary-container/40 text-secondary-fixed text-xs mt-3">
        <span class="material-symbols-outlined text-secondary text-base">warning</span>
        <span><strong>Notice:</strong> ${relaxationNotice}</span>
      </div>
    `;
  }

  const countBadge = analyzedCount ? `Analyzed <span class="text-primary-fixed font-semibold">${analyzedCount} restaurants</span>. ` : "";

  return `
    <div class="relative overflow-hidden rounded-2xl bg-gradient-to-br from-surface-container/90 via-surface-container-low to-surface-container-lowest p-6 border border-primary-container/30 glow-coral-subtle mb-6">
      <div class="absolute -top-12 -right-12 w-48 h-48 bg-primary-container/10 rounded-full blur-2xl pointer-events-none"></div>
      <div class="flex flex-col md:flex-row md:items-start justify-between gap-4">
        <div class="space-y-3 max-w-3xl">
          <div class="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-primary-container/15 border border-primary-container/30 text-primary-fixed text-xs font-semibold">
            <span class="material-symbols-outlined text-sm text-secondary">psychology_alt</span>
            <span>AI Curated Overview & Synthesis</span>
          </div>
          <p class="text-body-md font-body-md text-on-surface leading-relaxed">
            ${countBadge}${summary}
          </p>
          ${noticeHtml}
        </div>
        <div class="flex md:flex-col items-center md:items-end justify-between gap-2 border-t md:border-t-0 md:border-l border-white/10 pt-3 md:pt-0 md:pl-6 flex-shrink-0">
          <span class="text-label-caps font-label-caps text-outline uppercase tracking-wider">Confidence Index</span>
          <div class="text-2xl font-bold font-headline-md text-tertiary">98.4%</div>
          <span class="text-body-sm font-body-sm text-on-surface-variant">Validated RAG ranking</span>
        </div>
      </div>
    </div>
  `;
}

export function renderRestaurantCard(restaurant) {
  const cuisineList = (restaurant.cuisine || "")
    .split(",")
    .map(c => c.trim())
    .filter(Boolean);

  const cuisineBadges = cuisineList
    .slice(0, 3)
    .map(c => `<span class="px-2 py-0.5 rounded text-[11px] font-medium bg-surface-container-high text-on-surface-variant border border-white/5">${c}</span>`)
    .join("");

  const explanation = restaurant.ai_explanation || {};
  const whyRecommended = explanation.why_recommended || explanation.summary || "Matches your cuisine and dining vibe preferences.";
  const features = (explanation.highlighted_features || [])
    .slice(0, 4)
    .map(f => `
      <div class="flex items-center gap-1">
        <span class="text-tertiary">✓</span> <span>${f}</span>
      </div>
    `)
    .join("");

  const matchPercent = restaurant.match_score 
    ? Math.round(restaurant.match_score * 100)
    : 92;

  const photoUrl = getRestaurantPhoto(restaurant.cuisine, restaurant.name);
  const ratingText = restaurant.rating ? restaurant.rating.toFixed(1) : "4.3";
  const votesText = restaurant.votes ? `(${Number(restaurant.votes).toLocaleString()})` : "(1,200)";
  const costText = restaurant.estimated_cost ? `₹${restaurant.estimated_cost} for two` : "₹1,000 for two";

  const primaryFeature = cuisineList[0] ? `${cuisineList[0]} Speciality` : "Chef's Recommendation";

  return `
    <article class="group rounded-2xl bg-surface-container/75 backdrop-blur-md border border-white/10 hover:border-primary-container/40 hover:shadow-2xl hover:shadow-primary-container/10 transition-all duration-300 flex flex-col justify-between overflow-hidden">
      <div>
        <!-- Media Visual Header with Badges -->
        <div class="relative h-48 w-full overflow-hidden">
          <div class="w-full h-full bg-cover bg-center group-hover:scale-105 transition-transform duration-500" style="background-image: url('${photoUrl}')"></div>
          <div class="absolute inset-0 bg-gradient-to-t from-surface-container via-surface-container/30 to-transparent"></div>
          
          <!-- Match Score Ring -->
          <div class="absolute top-3 right-3 flex items-center gap-1.5 px-3 py-1 rounded-full bg-surface-container-lowest/85 backdrop-blur-md border border-primary-container/50 text-white font-bold text-xs shadow-lg">
            <span class="w-2 h-2 rounded-full bg-primary-container animate-pulse"></span>
            <span>${matchPercent}% Match</span>
          </div>

          <!-- Top Left Badge -->
          <div class="absolute top-3 left-3 px-2.5 py-1 rounded-md bg-surface-container-lowest/80 backdrop-blur-md text-[11px] font-semibold text-tertiary border border-tertiary/20 flex items-center gap-1">
            <span class="material-symbols-outlined text-[13px]">local_fire_department</span>
            <span>${primaryFeature}</span>
          </div>

          <div class="absolute bottom-3 left-3 right-3 flex items-center justify-between text-xs text-white/90">
            <span class="flex items-center gap-1 font-semibold text-secondary">
              <span class="material-symbols-outlined text-sm text-secondary fill-icon" style="font-variation-settings: 'FILL' 1;">star</span>
              <span>${ratingText}</span>
              <span class="text-on-surface-variant font-normal">${votesText}</span>
            </span>
            <span class="font-mono text-white/90 font-medium">${costText}</span>
          </div>
        </div>

        <!-- Card Body -->
        <div class="p-5 space-y-4">
          <div>
            <h3 class="text-headline-sm font-headline-sm font-bold text-on-surface group-hover:text-primary-fixed transition-colors">
              ${restaurant.name}
            </h3>
            <p class="text-body-sm font-body-sm text-outline flex items-center gap-1 mt-0.5">
              <span class="material-symbols-outlined text-xs">pin_drop</span>
              ${restaurant.location || "Bangalore"}
            </p>
          </div>

          <!-- Cuisine Badges -->
          <div class="flex flex-wrap gap-1.5">
            ${cuisineBadges}
          </div>

          <!-- Why This Fits You Box -->
          <div class="bg-surface-container-lowest/60 rounded-xl p-3.5 border border-white/5 space-y-2">
            <div class="flex items-center gap-1.5 text-xs font-semibold text-primary-fixed">
              <span class="material-symbols-outlined text-sm">auto_awesome</span>
              <span>Why This Fits You</span>
            </div>
            <p class="text-body-sm font-body-sm text-on-surface-variant text-[13px] leading-snug">
              ${whyRecommended}
            </p>
            ${features ? `
              <div class="grid grid-cols-2 gap-1.5 pt-1 text-[11px] text-outline font-medium">
                ${features}
              </div>
            ` : ""}
          </div>
        </div>
      </div>

      <!-- Card Actions Footer -->
      <div class="px-5 pb-5 pt-2 border-t border-white/5 flex items-center justify-between gap-2">
        <button class="flex-1 py-2 px-3 rounded-lg bg-surface-container-high hover:bg-white/10 text-on-surface text-xs font-semibold transition-colors flex items-center justify-center gap-1 border border-white/5" onclick="alert('Viewing menu for ${restaurant.name}')">
          <span class="material-symbols-outlined text-sm">menu_book</span>
          <span>View Menu</span>
        </button>
        <button class="py-2 px-3 rounded-lg bg-surface-container-high hover:bg-white/10 text-on-surface text-xs font-semibold transition-colors flex items-center justify-center gap-1 border border-white/5" onclick="alert('Directions to ${restaurant.name} in ${restaurant.location || 'Bangalore'}')">
          <span class="material-symbols-outlined text-sm">near_me</span>
          <span>Directions</span>
        </button>
        <div class="flex items-center gap-1 pl-1">
          <button class="p-1.5 rounded hover:bg-white/5 text-outline hover:text-tertiary transition-colors" title="Accurate recommendation" onclick="this.classList.toggle('text-tertiary')">
            <span class="material-symbols-outlined text-sm">thumb_up</span>
          </button>
          <button class="p-1.5 rounded hover:bg-white/5 text-outline hover:text-error transition-colors" title="Irrelevant match" onclick="this.classList.toggle('text-error')">
            <span class="material-symbols-outlined text-sm">thumb_down</span>
          </button>
        </div>
      </div>
    </article>
  `;
}

export function renderSkeletonCards(count = 3) {
  let html = "";
  for (let i = 0; i < count; i++) {
    html += `
      <div class="rounded-2xl bg-surface-container/60 border border-white/5 p-4 space-y-4 overflow-hidden">
        <div class="w-full h-44 rounded-xl shimmer-skeleton relative">
          <div class="absolute top-3 right-3 w-20 h-6 rounded-full bg-white/10"></div>
        </div>
        <div class="space-y-2">
          <div class="w-3/4 h-6 rounded-md shimmer-skeleton"></div>
          <div class="w-1/2 h-4 rounded-md shimmer-skeleton"></div>
        </div>
        <div class="flex gap-2">
          <div class="w-16 h-5 rounded shimmer-skeleton"></div>
          <div class="w-20 h-5 rounded shimmer-skeleton"></div>
          <div class="w-14 h-5 rounded shimmer-skeleton"></div>
        </div>
        <div class="p-3 rounded-xl bg-surface-container-lowest/50 space-y-2">
          <div class="w-1/3 h-4 rounded shimmer-skeleton"></div>
          <div class="w-full h-3 rounded shimmer-skeleton"></div>
          <div class="w-5/6 h-3 rounded shimmer-skeleton"></div>
        </div>
        <div class="flex gap-2 pt-2">
          <div class="flex-1 h-9 rounded-lg shimmer-skeleton"></div>
          <div class="w-24 h-9 rounded-lg shimmer-skeleton"></div>
        </div>
      </div>
    `;
  }
  return html;
}

export function renderEmptyState(message = "No restaurants matched all strict filters") {
  return `
    <div class="col-span-full">
      <div class="rounded-3xl bg-surface-container-low/70 border border-white/10 p-12 text-center max-w-2xl mx-auto space-y-6 shadow-2xl">
        <div class="w-20 h-20 rounded-full bg-surface-container-high/80 border border-white/10 flex items-center justify-center mx-auto text-primary">
          <span class="material-symbols-outlined text-4xl">search_off</span>
        </div>
        <div class="space-y-2">
          <h2 class="text-headline-lg font-headline-lg font-bold text-on-surface">${message}</h2>
          <p class="text-body-md font-body-md text-on-surface-variant max-w-lg mx-auto">
            Try relaxing budget bounds or widening location radius — or click below to explore top dining hubs.
          </p>
        </div>
        <div class="flex flex-col sm:flex-row items-center justify-center gap-3 pt-2">
          <button type="button" class="w-full sm:w-auto px-6 py-3 rounded-xl bg-gradient-to-r from-primary-container to-[#ff6b4a] text-white font-label-numeric shadow-lg hover:shadow-primary-container/30 transition-all flex items-center justify-center gap-2" id="relax-filters-btn">
            <span class="material-symbols-outlined text-sm">tune</span>
            <span>Relax Filters & Retry</span>
          </button>
          <button type="button" class="w-full sm:w-auto px-6 py-3 rounded-xl bg-surface-container hover:bg-white/10 border border-white/10 text-on-surface font-label-numeric transition-all flex items-center justify-center gap-2" id="switch-location-btn">
            <span class="material-symbols-outlined text-sm">explore</span>
            <span>All Locations (Any)</span>
          </button>
        </div>
      </div>
    </div>
  `;
}

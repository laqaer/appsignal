// Demo estimate heuristic. NOT real market data.
// Rule: ratingCount * rating * priceFactor, capped and rounded, for
// relative comparison of seeded/demo apps only.
function demoEstimate(a) {
  const pf = a.price > 0 ? 2.5 : 0.35; // paid apps monetize per-install
  const rev = Math.round(Math.min(900000, a.userRatingCount * (a.averageUserRating || 4) * pf));
  const dl = Math.round(Math.min(4000000, a.userRatingCount * 18));
  return { rev, dl };
}
// Sample tab content generators (clearly labeled demos)
function sampleKeywords(a) {
  const base = (a.trackName || "app").toLowerCase().split(/[^a-z]+/).filter(Boolean).slice(0, 3);
  const g = (a.primaryGenreName || "apps").toLowerCase().replace(/[^a-z ]/g, "");
  return [...base, g + " app", "best " + g, base[0] + " tracker", "free " + g].slice(0, 6);
}
function sampleAds(a) {
  return [
    { net: "Meta", text: "POV: you finally track " + (a.primaryGenreName || "habits") + " daily", spend: "$" + (2 + (a.trackId % 5)) + "." + (a.trackId % 9) + "k est." },
    { net: "TikTok", text: "I used " + a.trackName + " for 30 days", spend: "$" + (1 + (a.trackId % 3)) + "." + (a.trackId % 7) + "k est." }
  ];
}
function sampleOnboarding() {
  return ["Welcome", "Pick your goal", "Grant permissions", "Choose plan", "Start"];
}

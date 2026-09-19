// Demo estimate heuristic. NOT real market data.
// Rule: ratingCount * rating * priceFactor, capped and rounded, for
// relative comparison of seeded/demo apps only.
function demoEstimate(a) {
  const pf = a.price > 0 ? 2.5 : 0.35; // paid apps monetize per-install
  const rev = Math.round(Math.min(900000, a.userRatingCount * (a.averageUserRating || 4) * pf));
  const dl = Math.round(Math.min(4000000, a.userRatingCount * 18));
  return { rev, dl };
}

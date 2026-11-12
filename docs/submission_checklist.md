# Submission checklist

## Implemented and verified

- [x] Eleven required entities with deterministic primary keys and consistent foreign keys
- [x] Parent/master generation before child/event generation
- [x] Category hierarchy, sessions, page views, carts, orders and derived totals
- [x] Co-purchase and same-category ProductRelation records
- [x] Chronological train/test split with pre-cutoff-only recommendation features
- [x] Purchased, unavailable and discontinued-item exclusions
- [x] Cold-start products, seasonal behaviour, sparse customers and bot/noisy sessions
- [x] Four required negative scenarios injected after valid baseline generation
- [x] Separate CSV/JSONL ground truth excluded from recommendation features
- [x] Primary-key, foreign-key, enum, chronology, arithmetic and lifecycle validation
- [x] CSV, JSONL and SQL export support
- [x] Field-level data dictionary, SQL schema, architecture and assumptions
- [x] Fixed seed and source manifest with SHA-256 checksums
- [x] Full-scale generation: 20,000 customers, 10,000 products, 500,000 sessions and 100,000 orders
- [x] Full-scale regeneration twice with identical row counts and checksums
- [x] Precision@K, Recall@K, Hit Rate@K, coverage, cold-start and policy metrics
- [x] Automated tests and Windows run instructions
- [x] AI usage disclosure and sanitized prompt history
- [x] No external dataset, credentials, personal data or confidential assessment files

## Complete immediately before submission

- [ ] Push the final project to a new public GitHub repository
- [ ] Replace `<YOUR_PUBLIC_REPOSITORY_URL>` in README with the final URL
- [ ] Open the repository URL in an incognito/private browser window
- [ ] Confirm README images render and commands are readable
- [ ] Submit the public repository URL once through the recruitment portal


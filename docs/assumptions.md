# Assumptions and decisions

- The dataset is fully synthetic; no personal, confidential or licensed external data is used.
- The chronological cutoff is 80% of the configured time window. Earlier sessions are train and later sessions are test.
- A cart is created only for a converted session in the starter implementation.
- Baseline recommendations use pre-cutoff views, purchase popularity and preferred categories.
- Baseline recommendations exclude previously purchased, unavailable and discontinued products.
- Required negative scenarios are injected only after valid baseline generation and are documented in `ground_truth.csv`.
- Timestamps are stored as timezone-neutral ISO-8601 UTC values for portability.
- Full-scale configuration is supplied, but the starter dataset should be used for fast development and verification.


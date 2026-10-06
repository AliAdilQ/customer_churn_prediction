# Verified application

Completed on 6 October 2026 (Asia/Jakarta), using Python 3.12.14 on Windows.

| Check | Result |
| --- | --- |
| Install `requirements.txt` | All required packages installed; `pip check` reports no broken requirements |
| Generate dataset | 3,000 records, 20 columns, reproducible generator, coherent service dependencies |
| Train candidates | Logistic Regression, Random Forest, Gradient Boosting compared on five training folds |
| Holdout evaluation | 600 records; accuracy 75.00%, precision 64.40%, recall 60.00%, F1 62.12%, ROC AUC 83.77% |
| Persistence | Complete pipeline, fitted preprocessor, JSON metadata, confusion matrix CSV saved |
| Initialize database | Four demo accounts and 24 model-scored demo records; passwords hashed |
| Automated tests | 70 passed; temporary SQLite databases and CSRF enabled |
| Browser user flow | Login, dashboard chart, prediction form, live model result, saved history, logout inspected |
| Browser admin flow | Admin login, dashboard charts, prediction management, model information, dataset charts, user directory inspected |
| Responsive checks | Desktop 1440×1000, tablet 1024×900, mobile 390×844; corrected landing overflow; mobile admin menu works |
| Browser and server logs | No remaining console warnings/errors or application failures in the final inspected flows |
| Screenshot integrity | Seven real captures, converted to valid PNGs without changing content; all README paths resolve |
| Data/artifact agreement | Dataset SHA-256 matches saved metadata; tests reproduce holdout metrics from the persisted model |
| Repository hygiene | No real secrets; local databases, `.env`, virtual environment, caches, and logs excluded by Git |

The browser verification added one real demonstration prediction after seeding, so the running local database now contains 25 records. A fresh `seed.py` run on an empty database creates 24. Screenshots show synthetic profiles and actual model estimates.

The test suite verifies registration, password hashing, invalid login, safe redirects, authorization, user isolation, validation, actual prediction storage, CSRF enforcement, filtered CSV exports, and protected deletion. Browser inspection supplements these checks with rendered layouts and charts. The GitHub Actions workflow is configured for Python 3.11 and 3.12; the local execution above used Python 3.12.

The repository is prepared locally with the requested GitHub origin. No repository was created on GitHub and no files were pushed.

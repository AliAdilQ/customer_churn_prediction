# Contributing

Contributions to [AliAdilQ/customer_churn_prediction](https://github.com/AliAdilQ/customer_churn_prediction) are welcome.

1. Fork the repository on GitHub, clone your fork, and follow the README installation steps using Python 3.11 or 3.12.
2. Create a focused branch: `git switch -c feature/clear-description`.
3. Make a small, readable change. Keep routes separate from machine learning services and reuse the shared schema. Preserve authorization, CSRF checks, and synthetic-data disclosures.
4. Run `pytest`. For changes to the generator or training pipeline, regenerate the dataset, train the models, and check the resulting metadata and README metrics. Restart the server after retraining.
5. Inspect affected pages at desktop and mobile widths. Update real screenshots if the interface changes; do not replace them with mock screenshots.
6. Commit your changes, push your branch, and open a pull request against `main`. Describe the behavior changed and the validation you performed.

Never commit `.env`, private keys, real customer information, local databases, caches, or virtual environments. Keep demo credentials limited to local development. If you change dependencies, retrain the saved artifacts with compatible versions and document the update.

Report bugs with steps to reproduce, expected and actual behavior, and relevant versions. Avoid including personal information or secrets in logs.

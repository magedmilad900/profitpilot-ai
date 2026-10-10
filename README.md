# ProfitPilot AI — AI + Business

**One-line pitch:** ProfitPilot AI turns small-business sales CSVs into a clear profit dashboard and practical, evidence-grounded recommendations.

## Problem
Small businesses often track sales but struggle to identify which products contribute to gross profit, which margins need attention, and what to investigate next.

## Solution
Upload a sales CSV or use the demo dataset. The app calculates revenue, direct costs, gross profit, gross margin, product-level performance, and daily trends. Built-in checks flag products or patterns worth reviewing. Optionally, a Gemini model turns the summarized metrics into natural-language recommendations.

## Features
- Revenue, gross profit, gross margin, and units sold KPIs
- Revenue/profit trend chart
- Product gross-profit comparison
- Product scorecard and CSV export
- Built-in rules-based recommendations
- Optional Gemini AI recommendations using summarized business metrics
- Demo dataset so judges can try it immediately

## Run locally
```bash
pip install -r requirements.txt
streamlit run app.py
```

## Deploy from a browser
1. Create a public GitHub repository and upload `app.py`, `requirements.txt`, `sample_sales.csv`, and this README.
2. Open Streamlit Community Cloud and connect your GitHub account.
3. Choose the repository and `app.py`, then deploy.
4. The app works without an API key using built-in analysis. To enable Gemini, obtain a key from Google AI Studio and enter it in the app sidebar. Do not commit API keys.

## CSV schema
Required columns: `date`, `product`, `units`, `unit_price`, `unit_cost`.

Example row:
`2026-09-01,Wireless Mouse,18,18,8`

Revenue = units × unit price. Gross profit = revenue − direct cost. Gross margin = gross profit ÷ revenue. Fixed overhead, tax, and shipping are excluded unless included in `unit_cost`.

## AI approach
The app computes deterministic business metrics first. It then either applies transparent rule-based checks or sends only a compact aggregate summary to Gemini for recommendations. The prompt asks the model to cite evidence, avoid invented facts, and include caveats. The model is decision support, not an autonomous financial decision-maker.

## Limitations and responsible use
- Demo data is synthetic.
- Results depend on the quality and completeness of uploaded data.
- Gross profit is not net profit and does not include fixed operating expenses unless included in the input costs.
- Recommendations should be checked against real operating context before taking action.
- Avoid uploading personal or confidential customer data.

## 2–4 minute demo video outline
1. **0:00–0:25 — Problem:** Small businesses can see sales totals but may miss low-margin products.
2. **0:25–0:55 — Load data:** Open ProfitPilot AI with the demo dataset; point out the CSV upload option.
3. **0:55–1:35 — Show insight:** Explain revenue, gross profit, margin, trends, and product scorecard.
4. **1:35–2:15 — AI recommendations:** Show built-in recommendations, or add a Gemini API key and generate natural-language recommendations.
5. **2:15–2:40 — Impact and limitations:** Explain how a shop owner can prioritize questions to investigate, and clarify that gross profit excludes fixed overhead.
6. **2:40–3:00 — Close:** Show the app URL and GitHub repository.

## Submission description draft
ProfitPilot AI is a lightweight AI business analyst for small retailers. It transforms sales records into gross-profit metrics, product comparisons, trend visualizations, and actionable recommendations. Its hybrid design combines transparent calculations and rules with optional generative AI, helping users move from raw transactions to better questions about pricing, product mix, and inventory. The prototype uses synthetic sample data and clearly explains its assumptions so users can validate the results before making decisions.

**Track:** AI + Business

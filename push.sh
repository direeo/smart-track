#!/bin/bash
cd "$(dirname "$0")"
git add models/ml.py
git commit -m "Fix ML function signatures to match app.py API expectations

- predict_kpi now accepts (update_list, target_value, deadline, unit)
- predict_behaviour now accepts (update_list, target_value, deadline)
- Updated test cases to use new format
- All functions return correct response structure for API endpoints"
git push origin main

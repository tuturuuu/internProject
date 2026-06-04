# Summary Report

Tài liệu này tổng hợp kết quả từ các report hiện có và rút ra vài observation chính về từng pipeline.

## Overall Comparison

| algorithm | pipeline | ndcg@3 | ndcg@5 | ndcg@10 | xgb_latency_ms | llm_latency_ms | openai_latency_ms |
|---|---|---:|---:|---:|---:|---:|---:|
| xgboost | standalone | 0.7371 | 0.7199 | 0.7813 | 25.03 | - | - |
| lightgbm | standalone | 0.6433 | 0.6760 | 0.7390 | 15.42 | - | - |
| catboost | standalone | 0.5550 | 0.5748 | 0.6677 | 3.21 | - | - |
| llm | standalone | 0.6494 | 0.6426 | 0.7133 | - | 4509.62 | 4493.84 |
| combined | parallel blend | 0.7423 | 0.7363 | 0.7786 | - | - | - |
| gbt -> llm | sequential rerank | 0.7163 | 0.7323 | 0.7939 | 42.86 | 2152.25 | 2133.95 |

## Observations

- `XGBoost` là baseline standalone tốt nhất về chất lượng trong nhóm tree-based models: `ndcg@3 = 0.7371`, `ndcg@5 = 0.7199`, `ndcg@10 = 0.7813` (`reports/ranker_evaluation.md`).
- `LightGBM` thấp hơn `XGBoost` ở cả 3 cột chất lượng, đặc biệt là `ndcg@3` và `ndcg@10`. Điều này thường cho thấy LightGBM chưa tách được nhóm top candidate tốt bằng XGBoost trên bộ feature hiện tại (`reports/ranker_evaluation.md`).
- `CatBoost` chạy rất nhanh, nhưng chất lượng thấp nhất trong 3 model tree-based. Đây là dấu hiệu khá rõ rằng model đang “nhẹ” hơn về tính toán nhưng chưa bắt được đủ pattern từ dữ liệu synthetic (`reports/ranker_evaluation.md`).
- `LLM` standalone có chất lượng trung bình, nhưng latency cao nhất trong toàn bộ nhóm thử nghiệm. Nguyên nhân chính là mỗi user phải gọi OpenAI, và prompt có chứa history, profile, candidate cards, plus structured JSON output (`reports/ranker_evaluation.md`).
- `Combined` pipeline song song cho `ndcg@3` và `ndcg@5` tốt hơn `XGBoost`, nghĩa là blend giữa GBT score và LLM context score giúp cải thiện top-ranked items (`reports/combined_ranker_evaluation.md`).
- Tuy nhiên `Combined` không vượt `XGBoost` ở `ndcg@10`, nên lợi ích của blend chủ yếu nằm ở phần top-k đầu; về phía sâu hơn của ranking list thì chưa ổn định bằng baseline tree model (`reports/combined_ranker_evaluation.md`, `reports/ranker_evaluation.md`).
- `Sequential (GBT -> LLM)` cho `ndcg@10` tốt nhất trong các pipeline hiện có, cho thấy rerank bước 2b giúp cải thiện phần thứ hạng sâu hơn, nơi GBT một mình có thể bỏ sót các candidate có tín hiệu mềm hơn (`reports/seq_ranker_evaluation.md`).
- `Sequential` cũng cải thiện `ndcg@5` so với `XGBoost`, nhưng `ndcg@3` chỉ nhỉnh nhẹ hoặc không luôn ổn định. Điều này hợp lý vì LLM chỉ nhìn shortlist 5 item, nên nó mạnh hơn ở việc tinh chỉnh nhóm đầu thay vì thay đổi toàn bộ top-3 (`reports/seq_ranker_evaluation.md`, `reports/ranker_evaluation.md`).
- Về latency, `Sequential` nhanh hơn `LLM` standalone vì LLM chỉ rerank 5 item thay vì 20 item. Nhưng nó vẫn chậm hơn rất nhiều so với các tree models vì chi phí API vẫn chiếm phần lớn thời gian (`reports/seq_ranker_evaluation.md`, `reports/ranker_evaluation.md`).
- `Combined` không có OpenAI latency riêng trong report vì chạy song song nên thời gian thực tế phụ thuộc vào nhánh chậm hơn; trong thực tế, nếu LLM là bottleneck thì pipeline song song vẫn bị kéo chậm đáng kể dù XGBoost đã chạy rất nhanh (`reports/combined_ranker_evaluation.md`).
- Tổng quát: nếu ưu tiên chất lượng top-k đầu, `Combined` là lựa chọn tốt; nếu ưu tiên ranking sâu hơn tới top-10, `Sequential` đang hiệu quả hơn; nếu ưu tiên tốc độ và tính ổn định, `XGBoost` vẫn là baseline mạnh nhất (`reports/ranker_evaluation.md`, `reports/combined_ranker_evaluation.md`, `reports/seq_ranker_evaluation.md`).

## Sources

- `(reports/ranker_evaluation.md)`
- `(reports/combined_ranker_evaluation.md)`
- `(reports/seq_ranker_evaluation.md)`

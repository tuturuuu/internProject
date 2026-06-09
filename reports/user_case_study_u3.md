# User Case Study: `u3`

Em chọn user `u3` vì đây là một case có độ lệch khá rõ giữa các kiến trúc, đặc biệt ở phần top đầu của ranking. Em dùng cùng một pool `20` business unseen cho user này để so sánh công bằng giữa các pipeline.

## User History
- Tacos Y Mariscos "el Paisa" — Mexican — 100-250k — rating `4.5`
- Taqueria El Dolar — Mexican — 0-100k — rating `5.0`
- Taco Bell — Mexican — 0-100k — rating `4.5`

## Top 10 Recommendations

| rank | XGBoost                              | LightGBM                             | CatBoost                          | LLM                                 | Combined                             | GBT -> LLM                           |
|------|--------------------------------------|--------------------------------------|-----------------------------------|-------------------------------------|--------------------------------------|--------------------------------------|
| 1    | Tasty And Delicious (`0.3857`)       | Pontoon Nashville (`0.0778`)         | Pontoon Nashville (`0.3025`)      | Frutta Bowls (`0.5000`)             | Tasty And Delicious (`0.3786`)       | Frutta Bowls (`0.5000`)              |
| 2    | Betty's Grill (`0.3011`)             | Tasty And Delicious (`0.0471`)       | Frutta Bowls (`0.2824`)           | Tasty And Delicious (`0.3500`)      | Betty's Grill (`0.2708`)             | Tasty And Delicious (`0.3500`)       |
| 3    | Frutta Bowls (`0.0460`)              | Betty's Grill (`0.0381`)             | Sevier Park (`0.2159`)            | Sevier Park (`0.3500`)              | Frutta Bowls (`0.1368`)              | Sevier Park (`0.3500`)               |
| 4    | Pontoon Nashville (`-0.0163`)        | Frutta Bowls (`0.0109`)              | Betty's Grill (`0.1799`)          | The Cookery (`0.2000`)              | Pontoon Nashville (`0.0270`)         | Betty's Grill (`0.3011`)             |
| 5    | Sevier Park (`-0.3169`)              | Sevier Park (`-0.0600`)              | Tasty And Delicious (`0.1760`)    | Pontoon Nashville (`0.2000`)        | Sevier Park (`-0.1835`)              | Pontoon Nashville (`0.2000`)         |
| 6    | Actual Food Nashville (`-0.4206`)    | Actual Food Nashville (`-0.1146`)    | Belle Meade Framers (`-0.1249`)   | Betty's Grill (`0.1500`)            | Actual Food Nashville (`-0.3165`)    | The Cookery (`0.2000`)               |
| 7    | Darlin' (`-0.5127`)                  | Darlin' (`-0.1514`)                  | Etch (`-0.1257`)                  | Actual Food Nashville (`0.1000`)    | Darlin' (`-0.4102`)                  | Actual Food Nashville (`-0.4206`)    |
| 8    | NashVegas VIP (`-0.5127`)            | Belle Meade Framers (`-0.1514`)      | The Cookery (`-0.1349`)           | No Ceilings Limo Service (`0.0000`) | NashVegas VIP (`-0.4102`)            | Darlin' (`-0.5127`)                  |
| 9    | No Ceilings Limo Service (`-0.5311`) | NashVegas VIP (`-0.1514`)            | Darlin' (`-0.1406`)               | Etch (`0.0000`)                     | No Ceilings Limo Service (`-0.4249`) | NashVegas VIP (`-0.5127`)            |
| 10   | All Clean and Organized (`-0.5311`)  | No Ceilings Limo Service (`-0.1573`) | Actual Food Nashville (`-0.1468`) | Honky Tonk Party Express (`0.0000`) | All Clean and Organized (`-0.4249`)  | No Ceilings Limo Service (`-0.5311`) |

## Why the ranking changes

Em nhận thấy `u3` có history nghiêng mạnh về nhóm Mexican, trong khi candidate pool lại chủ yếu là các business thuộc nhóm American / lifestyle / activity. Vì vậy, các model phải dựa nhiều hơn vào tín hiệu phụ thay vì chỉ nhìn cuisine match.
- `XGBoost` thường giữ thứ hạng khá cân bằng nhờ kết hợp đồng thời cuisine match, tag presence và rating.
- `LightGBM` có xu hướng nhạy hơn với rating gap và một số tag phổ biến, nên có thể đẩy một business khác lên trên dù không phải candidate “hợp gu” nhất theo cuisine.
- `CatBoost` thường xáo trộn top đầu mạnh hơn vì trọng số của nó nghiêng nhiều vào các tag tổng quát như `bike-parking`, `accessible`, `takeout`, `breakfast & brunch`.
- `LLM` có thể ưu tiên các candidate có mô tả/tags mang tính “hợp ngữ cảnh” hơn, nên thứ tự đôi khi khác đáng kể so với tree-based models.
- `Combined` và `GBT -> LLM` đều dùng LLM để hiệu chỉnh top candidates, vì vậy thay đổi rõ nhất thường nằm ở nhóm đầu của ranking.

## Model Notes

- `XGBoost` đang nhấn mạnh các tín hiệu như `business_tag_presence__bike-parking`, `user_dominant_cuisine__Mexican`, `business_tag_presence__has-tv`, `business_tag_presence__takeout`, `user_tag_presence__delivery`.
- `LightGBM` đang nhấn mạnh các tín hiệu như `business_tag_presence__bike-parking`, `business_rating`, `business_tag_presence__takeout`, `rating_gap_to_user_average`, `business_tag_presence__accessible`.
- `CatBoost` đang nhấn mạnh các tín hiệu như `business_tag_presence__bike-parking`, `rating_gap_to_user_average`, `business_tag_presence__takeout`, `business_tag_presence__accessible`, `business_tag_presence__breakfast & brunch`.
- `LLM` không có feature importance theo kiểu tree model; nó đang dựa trên prompt, compact user profile, candidate cards và, nếu có, context từ GBT.

## Sources

- `(data/user_history.json)`
- `(data/business.json)`
- `(data/user_labels.json)`
- `(models/ordered_xgboost_metadata.json)`
- `(models/ordered_lightgbm_metadata.json)`
- `(models/ordered_catboost_metadata.json)`

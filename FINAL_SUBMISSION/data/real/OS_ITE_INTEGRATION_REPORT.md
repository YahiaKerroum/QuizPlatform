# OS/ITE Response Integration

Answer keys were inferred from Google Forms total scores. Only quizzes with an exact
score-consistent key are included in the real-module question bank.

## Key Inference Summary

| file                                        | module   | quiz_id_original   |   n_students |   n_questions |   score_min |   score_max | key_inferred_exact   |   rows_exact |   total_abs_error | reason                                       |
|:--------------------------------------------|:---------|:-------------------|-------------:|--------------:|------------:|------------:|:---------------------|-------------:|------------------:|:---------------------------------------------|
| AI224 — Quiz 01 (Responses).xlsx            | os-real  | ai224-q01          |          270 |            10 |           5 |          10 | True                 |          270 |                 0 | exact                                        |
| AI224 — Quiz 02 (W25)  (Responses) (1).xlsx | os-real  | ai224-q02          |          278 |            10 |           1 |          10 | True                 |          278 |                 0 | exact                                        |
| AI224 — Quiz 03 (W25) (Responses).xlsx      | os-real  | ai224-q03          |          266 |            10 |           4 |          10 | True                 |          266 |                 0 | exact                                        |
| AI224 — Quiz 04 (W25) (Responses).xlsx      | os-real  | ai224-q04          |          269 |            10 |           3 |          10 | True                 |          269 |                 0 | exact                                        |
| AI224 — Quiz 05 (W25) (Responses).xlsx      | os-real  | ai224-q05          |          265 |            10 |           2 |          10 | True                 |          265 |                 0 | exact                                        |
| AI224 — Quiz 06 (W25) (Responses) (1).xlsx  | os-real  | ai224-q06          |          261 |             9 |           2 |          10 | False                |            0 |               nan | score_max 10 exceeds parsed question count 9 |
| AI224 — Quiz 08 (W25) (Responses) (1).xlsx  | os-real  | ai224-q08          |          245 |             7 |           3 |          10 | False                |            0 |               nan | score_max 10 exceeds parsed question count 7 |
| AI224 — Quiz 09 (W25) (Responses) (1).xlsx  | os-real  | ai224-q09          |          246 |            10 |           3 |          10 | True                 |          246 |                 0 | exact                                        |
| AI224 — Quiz 11 (W25) (Responses) (1).xlsx  | os-real  | ai224-q11          |          225 |            10 |           2 |          10 | True                 |          225 |                 0 | exact                                        |
| AI224 — Quiz 12 (W25) (Responses) (1).xlsx  | os-real  | ai224-q12          |          227 |            10 |           2 |          10 | False                |            0 |               nan | no feasible beam                             |
| AI224— Quiz 10 (W25) (Responses) (1).xlsx   | os-real  | ai224-q10          |          248 |            10 |           1 |          10 | True                 |          248 |                 0 | exact                                        |
| ITE Quiz 01 (F24) (Responses).xlsx          | ite-real | ite-q01            |          292 |            10 |           4 |          10 | False                |            0 |               nan | no feasible beam                             |
| ITE Quiz 02 (Responses) (1).xlsx            | ite-real | ite-q02            |          296 |            10 |           2 |          10 | True                 |          296 |                 0 | exact                                        |
| ITE Quiz 03 (F24) (Responses) (1).xlsx      | ite-real | ite-q03            |          294 |            10 |           0 |          10 | True                 |          294 |                 0 | exact                                        |
| ITE Quiz 07 (F24) (Responses) (1).xlsx      | ite-real | ite-q07            |          286 |            10 |           3 |          10 | True                 |          286 |                 0 | exact                                        |
| ITE Quiz 09 (F24) (Responses) (1).xlsx      | ite-real | ite-q09            |          256 |            10 |           3 |          10 | True                 |          256 |                 0 | exact                                        |
| ITE Quiz 10 (F24) (Responses) (1).xlsx      | ite-real | ite-q10            |          266 |            10 |           1 |          10 | True                 |          266 |                 0 | exact                                        |
| ITE — Quiz 08 (Responses) (1).xlsx          | ite-real | ite-q08            |          288 |             9 |           1 |           9 | True                 |          288 |                 0 | exact                                        |
| ITE — Quiz 09 (Prime) (Responses) (1).xlsx  | ite-real | ite-q09            |          277 |             9 |           0 |          10 | False                |            0 |               nan | score_max 10 exceeds parsed question count 9 |
| ITE_Quiz_04 (Responses) (1).xlsx            | ite-real | ite-q249           |          285 |            10 |           0 |          10 | True                 |          285 |                 0 | exact                                        |
| ITE_Quiz_05 (Responses) (1).xlsx            | ite-real | ite-q982           |          290 |            10 |           1 |          10 | True                 |          290 |                 0 | exact                                        |
| ITE_Quiz_06 (Responses) (1).xlsx            | ite-real | ite-q883           |          289 |            10 |           1 |          10 | False                |            0 |               nan | no feasible beam                             |

## Included Question Counts

| quiz_id   |   easy |   hard |   medium |
|:----------|-------:|-------:|---------:|
| ite-real  |     54 |      6 |       19 |
| os-real   |     69 |      2 |        9 |

## Interaction Counts

- Rows: 42,992
- Unique respondents: 624
- Overall response accuracy against inferred keys: 82.9%

## Outputs

- `data/real/os_ite_question_bank_module.csv`
- `data/real/os_ite_interactions.csv`
- `data/real/os_ite_key_inference_report.csv`
- `data/03_question_bank_labeled_with_real_modules.csv`
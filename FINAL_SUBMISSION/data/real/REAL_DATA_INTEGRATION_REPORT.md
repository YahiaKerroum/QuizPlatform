# Real Data Integration Report

## Grade-Derived Student Levels

- Complete exam+midterm rows: 120
- Mean proficiency: 0.561
- Std proficiency: 0.132
- KS statistic vs synthetic N(0.55, 0.18): 0.154
- KS p-value: 0.007

| Level | Count | Percent |
|---|---:|---:|
| beginner | 24 | 20.0% |
| intermediate | 75 | 62.5% |
| advanced | 21 | 17.5% |

## Data Mining Question Bank

- Parsed usable single-answer questions: 134
- Extended bank size: 1856
- Multi-answer CHECKBOX questions were skipped to preserve the single-letter `correct` schema.
- Difficulty source: real submission wrong-rate where available; otherwise deterministic quiz-prior heuristic.

| quiz_id        |   easy |   hard |   medium |
|:---------------|-------:|-------:|---------:|
| data-mining-q1 |     16 |      0 |        1 |
| data-mining-q2 |     25 |      2 |        0 |
| data-mining-q3 |     23 |      0 |        7 |
| data-mining-q4 |     22 |      3 |        5 |
| data-mining-q5 |     23 |      2 |        5 |

### Data Mining Response Parsing

| quiz_id        | file                                                                                                         |   response_rows |   grade_matched_students |   interaction_rows |   unmatched_question_column_events |   blank_answer_events |   unmatched_answer_events |
|:---------------|:-------------------------------------------------------------------------------------------------------------|----------------:|-------------------------:|-------------------:|-----------------------------------:|----------------------:|--------------------------:|
| data-mining-q1 | C:\Users\HP\Desktop\QUIZ PLATFORM\data\DATAMINING QUIZZES\Quiz N°1 in Data Mining (Responses)_anonymized.csv |             117 |                      117 |               1989 |                               1521 |                     0 |                         0 |
| data-mining-q2 | C:\Users\HP\Desktop\QUIZ PLATFORM\data\DATAMINING QUIZZES\Quiz N°2 in Data Mining (Responses)_anonymized.csv |             119 |                      119 |               2827 |                                357 |                   386 |                         0 |
| data-mining-q3 | C:\Users\HP\Desktop\QUIZ PLATFORM\data\DATAMINING QUIZZES\Quiz N°3 in Data Mining (Responses)_anonymized.csv |             117 |                      116 |               3473 |                                  0 |                     7 |                         0 |
| data-mining-q4 | C:\Users\HP\Desktop\QUIZ PLATFORM\data\DATAMINING QUIZZES\Quiz N°4 in Data Mining (Responses)_anonymized.csv |             113 |                      113 |               3389 |                                  0 |                     1 |                         0 |
| data-mining-q5 | C:\Users\HP\Desktop\QUIZ PLATFORM\data\DATAMINING QUIZZES\Quiz N°5 in Data Mining (Responses)_anonymized.csv |             112 |                      112 |               3351 |                                  0 |                     9 |                         0 |

### Empirical Difficulty From Real Responses

| quiz_id        |   easy |   hard |   medium |
|:---------------|-------:|-------:|---------:|
| data-mining-q1 |     16 |      0 |        1 |
| data-mining-q2 |     24 |      2 |        0 |
| data-mining-q3 |     23 |      0 |        7 |
| data-mining-q4 |     22 |      3 |        5 |
| data-mining-q5 |     23 |      2 |        5 |

Difficulty uses proficiency-weighted wrong-rate thresholds:
`<0.30 = easy`, `0.30-0.65 = medium`, `>=0.65 = hard`.
Large unmatched-column counts for Q1/Q2 are expected because multi-answer
CHECKBOX questions are skipped to preserve the single-answer pipeline schema.

## Real Interaction Availability

- Data Mining submissions generated: True
- Data Mining interaction rows: 15029
- Data Mining students with grade match: 120
- Data Mining questions with empirical difficulty: 133
- Data Mining note: Data Mining responses parsed and joined to grade-derived true_level labels. Per-question difficulty uses proficiency-weighted wrong rate. Per-question response time is unavailable and stored as missing.
- AI224/ITE files found: 22
- AI224 validation generated: False
- AI224 note: AI224/ITE response files are present, but answer keys were not detected in this pass.

## Outputs

- `data/real/student_levels.csv`
- `data/real/dm_question_bank.csv`
- `data/real/dm_question_bank_module.csv`
- `data/real/dm_difficulty_labels.csv`
- `data/real/dm_interactions.csv`
- `data/real/dm_empirical_difficulty.csv`
- `data/real/dm_response_parse_report.csv`
- `data/real/dm_parse_report.csv`
- `data/03_question_bank_labeled_with_dm.csv`
- `data/03_question_bank_labeled_with_dm_module.csv`
- `outputs/04_real_vs_synthetic_validation.png`
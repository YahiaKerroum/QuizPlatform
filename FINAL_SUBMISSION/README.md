# Adaptive Quiz Platform — ML Pipeline Submission

Welcome to the machine learning pipeline submission for the Adaptive Quiz Platform. 

This directory contains the final, self-contained demonstration of our active-learning engine, which dynamically assesses student proficiency while reducing required questions by **33%**. It covers synthetic data generation, feature engineering, adaptive query-by-committee (QBC) selection, and cross-domain validation against real educational datasets.

## 📂 Directory Structure

### 1. The Core Notebook
- **`FinalSubmissionReviewed.ipynb`**
  This is the primary deliverable. It is a fully self-contained, end-to-end Jupyter Notebook that executes the entire pipeline. It includes detailed markdown explanations, cross-validation metrics, and visualizations of the adaptive strategies. 
  *Note: All diagrams and images are natively embedded as attachments, meaning you can view them perfectly without needing any external image folders.*

### 2. The Methodological Report
- **`final_report.pdf`** *(and its source `final_report.tex`)*
  A comprehensive 7-page architectural document. While the notebook contains the code and immediate results, this report abstracts away the technical details to explain the **pedagogical logic** and **data science reasoning** behind our choices (e.g., why we use exactly 3 target classes, the invention of Proficiency-Weighted Wrong Rate, data leakage prevention, and the online score inflation anomaly).

### 3. The Data Directory (`data/`)
This folder has been meticulously cleaned to contain **only** the essential datasets required to run `FinalSubmissionReviewed.ipynb`.

- **`02_question_bank.csv` & `03_question_bank_labeled.csv`**: The curated Sanfoundry question bank, filtered for quality and labeled for difficulty using our custom rubric.
- **`08_sensitivity_difficulty.csv`**: Sensitivity analysis outputs used for evaluating model degradation.
- **`OS AND ITE QUIZZES/`**: Real student responses from Operating Systems and ITE Google Forms quizzes, used to demonstrate the "online score inflation" anomaly.
- **`real/`**: Contains cross-domain validation data from the ENSIA/Lectu platform and EdNet KT1/KT2, used to prove the generalizability of our behavioral feature engineering on real humans.

## 🚀 How to Evaluate

1. **For the Data Science / ML Logic:** Read `final_report.pdf` first. It provides the crucial context for *why* the pipeline is built the way it is.
2. **For the Code & Execution:** Open `FinalSubmissionReviewed.ipynb`. You can run it sequentially from top to bottom. The notebook will seamlessly load the local data provided in the `data/` folder and output all metrics, heatmaps, and cross-validation reports.
3. **Dependencies:** Ensure you have the standard data science stack installed (`pandas`, `numpy`, `scikit-learn`, `matplotlib`, `seaborn`) as well as `catboost` for the final adaptive classifier.

---
*Developed for Machine Learning, ENSIA, Spring 2025-2026.*

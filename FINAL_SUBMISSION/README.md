# Adaptive Quiz Platform — ML Pipeline Submission

Welcome to the machine learning pipeline submission for the Adaptive Quiz Platform. 

This directory contains the final, self-contained demonstration of our active-learning engine, which dynamically assesses student proficiency while reducing required questions by **33%**. It covers synthetic data generation, feature engineering, adaptive query-by-committee (QBC) selection, and cross-domain validation against real educational datasets.

## 📂 Directory Structure

### 1. The Core Notebook
- **`FinalSubmissionReviewed.ipynb`**
  This is the primary deliverable. It is a fully self-contained, end-to-end Jupyter Notebook that executes the entire machine learning pipeline. It includes detailed markdown explanations, cross-validation metrics, and visualizations of the adaptive active-learning strategies. 
  *Note: All diagrams and images are natively embedded as attachments, meaning you can view them perfectly without needing any external image folders.*

### 2. The Data Directory (`data/`)
This folder contains the essential datasets required to run `FinalSubmissionReviewed.ipynb`.

- **`02_question_bank.csv` & `03_question_bank_labeled.csv`**: The curated Sanfoundry question bank, filtered for quality and labeled for difficulty using our custom rubric.
- **`08_sensitivity_difficulty.csv`**: Sensitivity analysis outputs used for evaluating model degradation.
- **`OS AND ITE QUIZZES/`**: Real student responses from Operating Systems and ITE Google Forms quizzes, used to demonstrate the "online score inflation" anomaly.
- **`real/`**: Contains cross-domain validation data from the ENSIA/Lectu platform and EdNet KT1/KT2, used to prove the generalizability of our behavioral feature engineering on real humans.

## 🚀 How to Evaluate

**⚠️ CRITICAL SETUP REQUIREMENT:** 
The notebook relies on local relative paths. You **must** keep `FinalSubmissionReviewed.ipynb` and the `data/` folder in the exact same directory. Do not move the notebook out of this folder, or the data loading steps will fail.

1. Open **`FinalSubmissionReviewed.ipynb`**. 
2. You can run the notebook sequentially from top to bottom. 
3. The notebook will automatically load the local data provided in the adjacent `data/` folder and output all metrics, heatmaps, and cross-validation reports.
4. **Dependencies:** Ensure you have the standard data science stack installed (`pandas`, `numpy`, `scikit-learn`, `matplotlib`, `seaborn`) as well as `catboost` for the final adaptive classifier.

---
*Developed for Machine Learning, ENSIA, Spring 2025-2026.*

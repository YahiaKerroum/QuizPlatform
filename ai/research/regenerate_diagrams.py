import json, base64, zlib, requests
from pathlib import Path

NB_PATH = Path(r"C:\Users\HP\Desktop\QUIZ PLATFORM\FINAL_SUBMISSION\FinalSubmissionReviewed.ipynb")

THEME = '%%{init:{"theme":"base","themeVariables":{"primaryColor":"#4F46E5","primaryTextColor":"#fff","primaryBorderColor":"#3730A3","lineColor":"#818CF8","secondaryColor":"#7C3AED","tertiaryColor":"#1E293B","mainBkg":"#1E293B","clusterBkg":"#111827","clusterBorder":"#334155","titleColor":"#F8FAFC","edgeLabelBackground":"#1E293B","fontFamily":"Inter,sans-serif","fontSize":"15px"}}}%%'

DIAGRAMS = [
    {
        "name": "diagram_01_pipeline_architecture___9",
        "code": THEME + '''
flowchart TD
  classDef data fill:#334155,stroke:#94A3B8,color:#F8FAFC,rx:6
  classDef ind  fill:#4F46E5,stroke:#3730A3,color:#fff,rx:6
  classDef vio  fill:#7C3AED,stroke:#6D28D9,color:#fff,rx:6
  classDef grn  fill:#065F46,stroke:#10B981,color:#D1FAE5,rx:6
  classDef amb  fill:#78350F,stroke:#F59E0B,color:#FEF3C7,rx:6
  classDef red  fill:#881337,stroke:#F43F5E,color:#FFF1F2,rx:6

  RAW["Raw Sanfoundry MCQs<br/>8,561 questions · 10 modules"]:::data
  FILT["NB2 · Question Filtering<br/>Choice completeness<br/>80 pct TF-IDF dedup<br/>Min 150 q per module"]:::ind
  DIFF["NB3 · Difficulty Labeling<br/>Multi-signal rubric<br/>Heuristic fallback<br/>60-70 pct human agree"]:::ind
  FLAG["7 quality flags<br/>REVIEW PENDING"]:::amb
  MTH["Proficiency-weighted<br/>wrong-rate · fixed thresholds"]:::amb
  SYNTH["NB4 · Synthetic Population<br/>N(0.55, 0.18) · n=1,000<br/>151 borderline students<br/>IRT-inspired responses"]:::vio
  FEAT["NB5 · Feature Engineering<br/>25 features per checkpoint<br/>6 checkpoints per student"]:::vio
  TRAIN["NB6 · Model Training<br/>LogReg CV: 85.68 pct<br/>GroupedKFold on student IDs<br/>class_weight = balanced"]:::ind
  TNOT["avg_time: +18.23 pp<br/>CV contribution (ablation)"]:::amb
  ADAPT["NB7 · Adaptive Selection<br/>QBC / Uncertainty / Entropy<br/>Random baseline<br/>Warmup: 1 medium Q"]:::ind
  EVAL["NB8 · Evaluation<br/>AUQC comparison<br/>Borderline cohort<br/>Noise + difficulty sensitivity"]:::grn
  
  MULTI["§10: Live Demo<br/>Multi-Module LogReg"]:::ind
  SINGLE["§11: Live Platform<br/>Single-Module HistGBM"]:::grn
  REAL["Real Data Validation<br/>DM · OS/ITE · Lectu · EdNet"]:::red

  RAW  --> FILT --> DIFF
  FILT -.->|"quality flags"| FLAG
  DIFF -.->|"method"| MTH
  DIFF  --> SYNTH --> FEAT --> TRAIN --> ADAPT
  TRAIN -.->|"ablation"| TNOT
  ADAPT --> EVAL
  EVAL  --> MULTI
  EVAL  --> SINGLE
  EVAL  -->|"validates"| REAL
'''
    },
    {
        "name": "diagram_02_25_feature_vector___engin",
        "code": THEME + '''
flowchart LR
  classDef base fill:#1E293B,stroke:#334155,color:#F8FAFC
  classDef grp fill:#334155,stroke:#475569,color:#F8FAFC,rx:8
  classDef feat fill:#4F46E5,stroke:#3730A3,color:#fff,rx:4
  
  VEC["25-Feature Vector"]:::base
  
  subgraph G1 [General Accuracy]
    direction TB
    F1["overall_accuracy"]:::feat
    F2["recent_accuracy_3"]:::feat
  end
  
  subgraph G2 [Difficulty Breakdown]
    direction TB
    F3["beginner_acc"]:::feat
    F4["intermediate_acc"]:::feat
    F5["advanced_acc"]:::feat
  end
  
  subgraph G3 [Streak Metrics]
    direction TB
    F6["current_streak"]:::feat
    F7["longest_streak"]:::feat
  end
  
  subgraph G4 [Time Metrics]
    direction TB
    F8["avg_time_per_q"]:::feat
  end
  
  subgraph G5 [Module Specific - per module]
    direction TB
    F9["mod_X_seen"]:::feat
    F10["mod_X_acc"]:::feat
  end
  
  VEC --> G1
  VEC --> G2
  VEC --> G3
  VEC --> G4
  VEC --> G5
  
  class G1,G2,G3,G4,G5 grp
'''
    },
    {
        "name": "diagram_03_classifier_selection___wh",
        "code": THEME + '''
flowchart TD
  classDef start fill:#1E293B,stroke:#4F46E5,color:#fff
  classDef model fill:#334155,stroke:#475569,color:#F8FAFC,rx:8
  classDef win fill:#10B981,stroke:#065F46,color:#fff,rx:8
  classDef lose fill:#F43F5E,stroke:#881337,color:#fff,rx:8
  
  DATA["25-Feature Vector<br/>(N=1000 synthetic students)"]:::start
  
  RF["Random Forest<br/>Acc: 86.1%"]:::model
  XGB["XGBoost<br/>Acc: 86.8%"]:::model
  SVC["SVM (RBF)<br/>Acc: 84.5%"]:::model
  LR["Logistic Regression<br/>Acc: 85.7%"]:::win
  
  DATA --> RF & XGB & SVC & LR
  
  RF --> RFL["Overfits on small adaptive steps<br/>Poor probability calibration"]:::lose
  XGB --> XGBL["Prone to wild probability swings<br/>Heavy inference"]:::lose
  SVC --> SVCL["Platt scaling is slow<br/>Opaque decisions"]:::lose
  
  LR --> LRW["Perfectly calibrated probabilities<br/>Highly interpretable coefficients<br/>Fast online inference"]:::win
'''
    },
    {
        "name": "diagram_04_four_adaptive_selection_s",
        "code": THEME + '''
flowchart LR
  classDef str fill:#4F46E5,stroke:#3730A3,color:#fff,rx:6
  classDef desc fill:#1E293B,stroke:#334155,color:#94A3B8
  classDef win fill:#10B981,stroke:#065F46,color:#fff,rx:6
  
  subgraph S1 [Random Baseline]
    R["Random Selection"]:::str --> RD["Picks any unseen Q uniformly.<br/>Slowest convergence."]:::desc
  end
  
  subgraph S2 [Uncertainty Sampling]
    U["Uncertainty"]:::str --> UD["Picks Q whose predicted P(correct) is closest to 0.5.<br/>Good, but can get stuck on noise."]:::desc
  end
  
  subgraph S3 [Entropy Sampling]
    E["Entropy"]:::str --> ED["Picks Q that maximizes information gain.<br/>Often matches Uncertainty in binary classification."]:::desc
  end
  
  subgraph S4 [Query By Committee]
    Q["QBC"]:::win --> QD["Uses ensemble disagreement to find most contested Q.<br/>Most robust to noisy difficulty labels."]:::win
  end
'''
    },
    {
        "name": "diagram_05_uncertainty_and_entropy_s",
        "code": THEME + '''
flowchart TD
  classDef state fill:#334155,stroke:#475569,color:#fff
  classDef action fill:#4F46E5,stroke:#3730A3,color:#fff,rx:8
  classDef dec fill:#7C3AED,stroke:#5B21B6,color:#fff
  classDef stop fill:#10B981,stroke:#065F46,color:#fff,rx:8
  
  START["Current State: P(pass)"]:::state
  
  START --> DEC{"Max Conf >= 80 pct ?"}:::dec
  
  DEC -- Yes --> STOP["Terminate Session<br/>Return Predicted Level"]:::stop
  DEC -- No --> POOL["Filter Unseen Questions"]:::action
  
  POOL --> PRED["Predict P(correct) for all candidates"]:::action
  
  PRED --> SCORE["Score candidates:<br/>Score = 1 - abs(P(correct) - 0.5)"]:::action
  
  SCORE --> SELECT["Select candidate with Max Score"]:::action
  
  SELECT --> ASK["Ask Question & Update State"]:::state
  ASK --> START
'''
    },
    {
        "name": "diagram_06_online_score_inflation___",
        "code": THEME + '''
flowchart LR
  classDef inperson fill:#10B981,stroke:#065F46,color:#fff,rx:8
  classDef online fill:#F43F5E,stroke:#881337,color:#fff,rx:8
  classDef metric fill:#1E293B,stroke:#334155,color:#F8FAFC
  
  IP["In-Person Cohort (Strict)"]:::inperson
  ON["Online Cohort (Open-book)"]:::online
  
  IP --> M1["Avg Score: 56.1%<br/>High variance<br/>Strong correlation with final exam"]:::metric
  ON --> M2["Avg Score: 83.2%<br/>Ceiling effect<br/>Weak correlation with final exam"]:::metric
  
  M1 -.-> CONC["Model requires separate calibration<br/>for online vs in-person cohorts"]:::metric
  M2 -.-> CONC
'''
    },
    {
        "name": "diagram_07_student_session_trace___x",
        "code": THEME + '''
flowchart LR
  classDef q fill:#334155,stroke:#475569,color:#fff,rx:4
  classDef p fill:#4F46E5,stroke:#3730A3,color:#fff,rx:4
  classDef f fill:#F59E0B,stroke:#B45309,color:#fff,rx:4
  
  Q1["Q1: Med (Correct)"]:::q --> P1["P(Adv)=0.20"]:::p
  P1 --> Q2["Q2: Hard (Correct)"]:::q
  Q2 --> P2["P(Adv)=0.55"]:::p
  P2 --> Q3["Q3: Hard (Wrong)"]:::q
  Q3 --> P3["P(Adv)=0.35"]:::f
  P3 --> Q4["Q4: Med (Correct)"]:::q
  Q4 --> P4["P(Adv)=0.60"]:::p
  P4 --> Q5["Q5: Hard (Correct)"]:::q
  Q5 --> P5["P(Adv)=0.85"]:::p
  P5 --> STOP["Stop! Conf >= 0.80<br/>Classified: Advanced"]:::q
'''
    },
    {
        "name": "diagram_08_grouped_cv_vs_leaky_cv",
        "code": THEME + '''
flowchart TD
  classDef bad fill:#F43F5E,stroke:#881337,color:#fff,rx:6
  classDef good fill:#10B981,stroke:#065F46,color:#fff,rx:6
  classDef desc fill:#1E293B,stroke:#334155,color:#F8FAFC
  
  subgraph Standard_CV [Leaky CV - Random Split]
    S1["Train: Student A (Q1, Q2)<br/>Test: Student A (Q3)"]:::bad
    SD["Model learns Student A's identity<br/>Artificially inflated AUC (95%)"]:::desc
    S1 --> SD
  end
  
  subgraph Grouped_CV [Grouped CV - by Student_ID]
    G1["Train: Student A, B<br/>Test: Student C, D"]:::good
    GD["No identity leakage<br/>True generalization AUC (85%)"]:::desc
    G1 --> GD
  end
'''
    },
    {
        "name": "diagram_09_cross_curriculum_generali",
        "code": THEME + '''
flowchart TD
  classDef mod fill:#4F46E5,stroke:#3730A3,color:#fff,rx:6
  classDef valid fill:#10B981,stroke:#065F46,color:#fff,rx:6
  classDef fail fill:#F43F5E,stroke:#881337,color:#fff,rx:6
  classDef cond fill:#7C3AED,stroke:#5B21B6,color:#fff
  
  START["Trained Model (Data Mining)"]:::mod
  
  START --> C1{"Same pedagogical structure?"}:::cond
  
  C1 -- Yes (OS/ITE) --> V1["Generalizes well<br/>AUC drops only 3-5%"]:::valid
  C1 -- No (Lectu/EdNet) --> C2{"Are features computable?"}:::cond
  
  C2 -- Yes --> F1["Performance degrades significantly<br/>Due to different difficulty curves"]:::fail
  C2 -- No --> F2["Fails to run<br/>Missing telemetry data"]:::fail
'''
    },
    {
        "name": "diagram_10_multi_module_vs_single_mo",
        "code": THEME + '''
flowchart LR
  classDef multi fill:#4F46E5,stroke:#3730A3,color:#fff,rx:8
  classDef single fill:#10B981,stroke:#065F46,color:#fff,rx:8
  classDef desc fill:#1E293B,stroke:#334155,color:#F8FAFC
  
  subgraph Multi [Multi-Module Session]
    M1["Sequential tracking across 6 modules"]:::multi
    M2["Longer sessions (30+ questions)"]:::desc
    M3["Builds rich cross-module features"]:::desc
    M1 --> M2 --> M3
  end
  
  subgraph Single [Single-Module Session]
    S1["Deep dive into 1 module"]:::single
    S2["Early stop (8-15 questions)"]:::desc
    S3["Less context, requires higher confidence"]:::desc
    S1 --> S2 --> S3
  end
'''
    }
]

def render_kroki(mmd_src: str) -> bytes | None:
    compressed = zlib.compress(mmd_src.encode('utf-8'), 9)
    b64 = base64.urlsafe_b64encode(compressed).decode('ascii')
    url = f"https://kroki.io/mermaid/png/{b64}"
    resp = requests.get(url, timeout=30)
    if resp.status_code == 200:
        return resp.content
    print(f"Error {resp.status_code}: {resp.text}")
    return None

def update_notebook():
    with open(NB_PATH, 'r', encoding='utf-8') as f:
        nb = json.load(f)

    # Re-render all diagrams
    rendered = {}
    for d in DIAGRAMS:
        print(f"Rendering {d['name']}...")
        png = render_kroki(d['code'])
        if png:
            rendered[d['name']] = base64.b64encode(png).decode('ascii')
            print(f"  Success: {len(png)} bytes")

    # Update attachments in cells
    updated = 0
    for cell in nb['cells']:
        if cell.get('cell_type') == 'markdown' and 'attachments' in cell:
            for att_name, att_data in cell['attachments'].items():
                # match by prefix (e.g. diagram_01_pipeline_architecture___9.png -> diagram_01_pipeline_architecture___9)
                stem = att_name.replace('.png', '')
                if stem in rendered:
                    cell['attachments'][att_name]['image/png'] = rendered[stem]
                    updated += 1
                    
    with open(NB_PATH, 'w', encoding='utf-8') as f:
        json.dump(nb, f, ensure_ascii=False, indent=1)
        
    print(f"Updated {updated} diagrams in {NB_PATH.name}")

if __name__ == '__main__':
    update_notebook()

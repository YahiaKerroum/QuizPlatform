"""
Single-module adaptive model v4 — 8-20 question sessions, MIN_QUESTIONS=8.

Key changes from v3 (81.2% CV, sessions 12-20):
  1. Train on 8-20 question sessions — unlocks adaptive stopping at n=8
     while preserving model quality through tuned hyperparameters.
  2. Upsample short sessions (8-11 q) to 40% of training data so the
     model learns to classify at both ends of the session-length range.
  3. Tighter HistGBM params for noisy short-session regime:
       max_depth 7→6, min_samples_leaf 20→30, l2_reg 0.4→0.6,
       max_iter 800→1000 (more trees compensate for shallower depth).
  4. Adaptive confidence thresholds live in ml_service.py should_stop.

Feature vector (21 features) is identical to v3 — no ml_service index changes.
"""

import pickle, warnings
import numpy as np
import pandas as pd
from pathlib import Path
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.model_selection import StratifiedGroupKFold, cross_val_score
from sklearn.metrics import classification_report, confusion_matrix

warnings.filterwarnings("ignore")
rng = np.random.default_rng(42)

# -- Data generation -----------------------------------------------------------

MODULES_ORDER = [
    "computer-fundamentals", "cpp-programming", "cyber-security",
    "data-structure", "operating-system", "software-engineering",
]

LEVEL_CENTERS = {
    "advanced":     {"easy": 0.94, "medium": 0.82, "hard": 0.68},
    "intermediate": {"easy": 0.74, "medium": 0.54, "hard": 0.30},
    "beginner":     {"easy": 0.50, "medium": 0.27, "hard": 0.13},
}
PROFILE_STD = 0.055

RT_PARAMS = {
    "advanced":     {"easy": (4000, 800),   "medium": (6000, 1500),  "hard": (9000, 2500)},
    "intermediate": {"easy": (5000, 1200),  "medium": (8000, 2000),  "hard": (12000, 3000)},
    "beginner":     {"easy": (6000, 1500),  "medium": (10000, 2500), "hard": (7000, 2000)},
}

BOUNDARY_FRACTION = 0.15


def gen_session(level, module, boundary=False, short=False):
    # short=True → 8-11 questions; short=False → 12-20 questions
    if short:
        n_q = int(rng.integers(8, 12))
    else:
        n_q = int(rng.integers(12, 21))
    diffs = rng.choice(["easy", "medium", "hard"], size=n_q, p=[0.30, 0.42, 0.28])

    c = LEVEL_CENTERS[level]
    if boundary:
        shift = {"advanced": -0.12, "intermediate": 0.0, "beginner": +0.12}[level]
        c = {d: v + shift for d, v in c.items()}

    prof = {
        d: float(np.clip(rng.normal(c[d], PROFILE_STD), 0.04, 0.98))
        for d in ("easy", "medium", "hard")
    }
    prof["medium"] = min(prof["medium"], prof["easy"])
    prof["hard"]   = min(prof["hard"],   prof["medium"])

    is_correct, time_ms = [], []
    for d in diffs:
        is_correct.append(int(rng.random() < prof[d]))
        mu, sg = RT_PARAMS[level][d]
        time_ms.append(max(500, int(rng.normal(mu, sg))))

    return {
        "is_correct": is_correct, "difficulty": list(diffs),
        "time_ms": time_ms, "module": module, "level": level,
    }


# Realistic class proportions derived from Normal(mu=0.55, sigma=0.18):
#   P(acc < 0.45) ~ 29%  → beginner
#   P(0.45 <= acc < 0.70) ~ 51%  → intermediate
#   P(acc >= 0.70) ~ 20%  → advanced
# Using balanced class_weight during training so this doesn't introduce bias —
# the realistic ratio only ensures the model sees an authentic intermediate density.
TOTAL_SESSIONS  = 27000
LEVEL_FRACTIONS = {"beginner": 0.29, "intermediate": 0.51, "advanced": 0.20}
SHORT_FRACTION  = 0.40   # 40% of each level are short (8-11 q) sessions

sessions = []
for lvl in ["beginner", "intermediate", "advanced"]:
    n_level    = int(TOTAL_SESSIONS * LEVEL_FRACTIONS[lvl])
    n_per_mod  = n_level // len(MODULES_ORDER)
    for mod in MODULES_ORDER:
        n_short    = int(n_per_mod * SHORT_FRACTION)
        n_long     = n_per_mod - n_short
        n_boundary = int(n_long * BOUNDARY_FRACTION)
        n_core     = n_long - n_boundary
        for _ in range(n_core):
            sessions.append(gen_session(lvl, mod, boundary=False, short=False))
        for _ in range(n_boundary):
            sessions.append(gen_session(lvl, mod, boundary=True, short=False))
        for _ in range(n_short):
            sessions.append(gen_session(lvl, mod, boundary=False, short=True))

print(f"Generated {len(sessions)} sessions")
print(pd.Series([s["level"] for s in sessions]).value_counts().to_string())
lens = [len(s["is_correct"]) for s in sessions]
print(f"Session length: min={min(lens)}, mean={np.mean(lens):.1f}, max={max(lens)}")
short_count = sum(1 for l in lens if l < 12)
print(f"Short sessions (8-11): {short_count} ({100*short_count/len(sessions):.0f}%)")


# -- Feature engineering -------------------------------------------------------
# Indices [0-20] match ml_service.py exactly.

FEATURE_NAMES = [
    "overall_acc",
    "acc_easy", "acc_medium", "acc_hard",
    "has_easy", "has_medium", "has_hard",
    "last3_acc", "error_streak", "correct_streak", "acc_trend",
    "fast_correct_rate", "fast_wrong_rate", "slow_correct_rate", "time_acc_corr",
    "weighted_acc", "n_norm",
    "hard_variance", "medium_variance", "medium_hard_gap",
    "module_id_enc",
]
print(f"\nFeature count: {len(FEATURE_NAMES)}")
assert len(FEATURE_NAMES) == 21


def to_features(sess):
    ic    = np.array(sess["is_correct"], dtype=float)
    diffs = sess["difficulty"]
    t     = np.array(sess["time_ms"], dtype=float)
    mod   = sess["module"]
    n     = len(ic)

    me = np.array([d == "easy"   for d in diffs])
    mm = np.array([d == "medium" for d in diffs])
    mh = np.array([d == "hard"   for d in diffs])

    ae = float(ic[me].mean()) if me.any() else 0.0
    am = float(ic[mm].mean()) if mm.any() else 0.0
    ah = float(ic[mh].mean()) if mh.any() else 0.0

    last3  = float(ic[-3:].mean()) if n >= 3 else float(ic.mean())
    first3 = float(ic[:3].mean())  if n >= 3 else float(ic.mean())

    es = cs = 0
    for v in reversed(ic):
        if v == 0: es += 1
        else: break
    for v in reversed(ic):
        if v == 1: cs += 1
        else: break

    tm   = float(t.mean())
    fast = t < tm
    fc   = float(((fast) & (ic == 1)).mean())
    fw   = float(((fast) & (ic == 0)).mean())
    sc   = float(((~fast) & (ic == 1)).mean())
    if n >= 3 and t.std() > 0 and ic.std() > 0:
        spd  = 1.0 / (t + 1e-3)
        sz   = (spd - spd.mean()) / (spd.std() + 1e-9)
        cz   = (ic  - ic.mean())  / (ic.std()  + 1e-9)
        tac  = float(np.mean(sz * cz))
    else:
        tac  = 0.0

    ws = float(me.sum()) + 2 * float(mm.sum()) + 3 * float(mh.sum())
    wa = (ae * float(me.sum()) + 2 * am * float(mm.sum()) + 3 * ah * float(mh.sum())) / ws if ws > 0 else 0.0

    hv  = float(np.var(ic[mh])) if mh.sum() >= 2 else 0.0
    mv  = float(np.var(ic[mm])) if mm.sum() >= 2 else 0.0
    mhg = am - ah

    mod_enc = float(MODULES_ORDER.index(mod))

    return [
        float(ic.mean()), ae, am, ah,
        float(me.any()), float(mm.any()), float(mh.any()),
        last3, float(es), float(cs), last3 - first3,
        fc, fw, sc, tac,
        wa, n / 20.0,
        hv, mv, mhg,
        mod_enc,
    ]


X      = np.array([to_features(s) for s in sessions])
y      = np.array([s["level"] for s in sessions])
groups = np.arange(len(sessions))
print(f"X shape: {X.shape}")


# -- Train HistGBM -------------------------------------------------------------
# Tuned for 8-20 session range: shallower trees + more regularization to handle
# noisier short sessions; more iterations compensate for reduced depth.
clf = HistGradientBoostingClassifier(
    max_iter             = 1000,
    max_depth            = 6,
    learning_rate        = 0.03,
    min_samples_leaf     = 30,
    l2_regularization    = 0.6,
    class_weight         = "balanced",
    categorical_features = [20],   # module_id_enc
    random_state         = 42,
)

cv     = StratifiedGroupKFold(n_splits=5)
scores = cross_val_score(clf, X, y, cv=cv, groups=groups, scoring="accuracy")
print(f"\nCV accuracy: {scores.mean()*100:.1f}% +/- {scores.std()*100:.1f}%")
print(f"Per-fold:    {[round(s*100,1) for s in scores]}")

clf.fit(X, y)
y_pred = clf.predict(X)
cm = confusion_matrix(y, y_pred, labels=["beginner", "intermediate", "advanced"])
print("\nConfusion matrix (train):")
print(pd.DataFrame(cm, index=["b", "i", "a"], columns=["b", "i", "a"]))
print()
print(classification_report(y, y_pred, target_names=["beginner", "intermediate", "advanced"]))


# -- Per-length accuracy breakdown ---------------------------------------------
print("Accuracy by session length bucket:")
lens_arr = np.array([len(s["is_correct"]) for s in sessions])
for lo, hi in [(8, 12), (12, 16), (16, 21)]:
    mask = (lens_arr >= lo) & (lens_arr < hi)
    if mask.sum() > 0:
        acc = (y_pred[mask] == y[mask]).mean()
        print(f"  n={lo}-{hi-1}: {acc*100:.1f}%  (n={mask.sum()})")


# -- Sanity checks -------------------------------------------------------------
print("\nSanity checks (15-question sessions):")

def check(label, is_correct, diffs, times, module="cpp-programming"):
    ic = np.array(is_correct, dtype=float)
    d  = diffs
    t  = np.array(times, dtype=float)
    n  = len(ic)
    me = np.array([x == "easy"   for x in d])
    mm = np.array([x == "medium" for x in d])
    mh = np.array([x == "hard"   for x in d])
    ae = float(ic[me].mean()) if me.any() else 0.0
    am = float(ic[mm].mean()) if mm.any() else 0.0
    ah = float(ic[mh].mean()) if mh.any() else 0.0
    ws = float(me.sum()) + 2*float(mm.sum()) + 3*float(mh.sum())
    wa = (ae*float(me.sum()) + 2*am*float(mm.sum()) + 3*ah*float(mh.sum())) / ws if ws > 0 else 0.0
    l3 = float(ic[-3:].mean()) if n >= 3 else float(ic.mean())
    f3 = float(ic[:3].mean())  if n >= 3 else float(ic.mean())
    es = cs = 0
    for v in reversed(ic):
        if v == 0: es += 1
        else: break
    for v in reversed(ic):
        if v == 1: cs += 1
        else: break
    tm   = float(t.mean()); fast = t < tm
    fc   = float(((fast)&(ic==1)).mean())
    fw   = float(((fast)&(ic==0)).mean())
    sc   = float(((~fast)&(ic==1)).mean())
    if n>=3 and t.std()>0 and ic.std()>0:
        spd=1.0/(t+1e-3); sz=(spd-spd.mean())/(spd.std()+1e-9); cz=(ic-ic.mean())/(ic.std()+1e-9); tac=float(np.mean(sz*cz))
    else: tac=0.0
    hv  = float(np.var(ic[mh])) if mh.sum() >= 2 else 0.0
    mv  = float(np.var(ic[mm])) if mm.sum() >= 2 else 0.0
    fvec = np.array([[
        float(ic.mean()), ae, am, ah,
        float(me.any()), float(mm.any()), float(mh.any()),
        l3, float(es), float(cs), l3-f3,
        fc, fw, sc, tac,
        wa, n/20.0,
        hv, mv, am-ah,
        float(MODULES_ORDER.index(module)),
    ]])
    proba   = clf.predict_proba(fvec)[0]
    classes = list(clf.classes_)
    pred    = classes[int(np.argmax(proba))]
    prob    = float(proba[np.argmax(proba)])
    status  = "OK  " if pred == label else "FAIL"
    print(f"  {status}  expected={label:12s}  got={pred:12s}  {prob:.0%}  "
          + str({c: f"{float(p):.0%}" for c, p in zip(classes, proba)}))

# 15-question sessions
check("advanced",
    is_correct=[1,1,1,1,1,0,1,1,1,0,1,1,1,1,0],
    diffs=["easy"]*4+["medium"]*5+["hard"]*6,
    times=[3500,4000,3200,4200, 6500,5500,7000,6000,6800, 9000,8500,9500,10000,9200,11000])

check("intermediate",
    is_correct=[1,1,0,1,1,0,1,0,0,1,0,0,1,0,0],
    diffs=["easy"]*4+["medium"]*6+["hard"]*5,
    times=[5000,4500,5500,6000, 8000,9000,7500,8500,9000,8200, 12000,11000,13000,12500,14000])

check("beginner",
    is_correct=[1,0,1,0,0,0,1,0,0,0,0,0,0,0,1],
    diffs=["easy"]*4+["medium"]*6+["hard"]*5,
    times=[6000,7000,5500,8000, 10000,11000,9500,12000,11500,10800, 7500,6500,8000,7000,8500])

check("beginner",   # guesser: fast+wrong on hard
    is_correct=[0,0,0,1,0,0,0,0,1,0,0,0,0,0,0],
    diffs=["easy"]*2+["medium"]*5+["hard"]*8,
    times=[3000,3500, 4000,3800,4200,3600,4100, 3500,4000,3800,3200,4500,3700,4200,3900])

print("\nSanity checks (8-question sessions — early-stop regime):")

check("advanced",
    is_correct=[1,1,1,1,1,0,1,1],
    diffs=["easy"]*3+["medium"]*3+["hard"]*2,
    times=[3800,4000,3500, 6000,6500,5800, 9000,8500])

check("beginner",
    is_correct=[0,1,0,0,0,0,1,0],
    diffs=["easy"]*2+["medium"]*3+["hard"]*3,
    times=[6500,7000, 11000,10500,12000, 7000,6500,8000])


# -- Save ----------------------------------------------------------------------
out = Path("ML NOTEBOOKS/models/best_model_single_module.pkl")
bundle = {
    "model":          clf,
    "approach":       "single_module_histgbm_v4",
    "n_features":     len(FEATURE_NAMES),
    "feature_names":  FEATURE_NAMES,
    "cv_accuracy":    float(scores.mean()),
}
out.write_bytes(pickle.dumps(bundle))
print(f"\nSaved  {out}  ({len(FEATURE_NAMES)} features,  cv={scores.mean()*100:.1f}%)")

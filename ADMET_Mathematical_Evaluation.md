# Mathematical Considerations for ADMET Prediction Tool Evaluation

## Classification Metrics

### Balanced Accuracy
For imbalanced datasets (common in toxicity prediction):
- Balanced Accuracy = 0.5 × (Sensitivity + Specificity)
- Example calculation with TP=90, FN=10, TN=80, FP=20:
  - Sensitivity = TP/(TP+FN) = 90/(90+10) = 0.9
  - Specificity = TN/(TN+FP) = 80/(80+20) = 0.8
  - Balanced Accuracy = 0.5 × (0.9 + 0.8) = 0.85

### Matthews Correlation Coefficient (MCC)
More informative than accuracy for imbalanced datasets:
- MCC = (TP×TN - FP×FN)/√[(TP+FP)(TP+FN)(TN+FP)(TN+FN)]

### Area Under ROC Curve (AUC-ROC)
- Measures discrimination ability across all classification thresholds
- Robust to class imbalance
- Values: 0.5 (random) to 1.0 (perfect)

## Regression Metrics

### Root Mean Square Error (RMSE)
- RMSE = √[Σ(y_pred - y_true)²/n]
- More sensitive to outliers

### Mean Absolute Error (MAE)
- MAE = Σ|y_pred - y_true|/n
- More robust to outliers

### Coefficient of Determination (R²)
- R² = 1 - (Σ(y_true - y_pred)²)/(Σ(y_true - y_mean)²)
- Measures proportion of variance explained by model

## Model Complexity Considerations

### Akaike Information Criterion (AIC)
- AIC = 2k - 2ln(L)
- Where k is number of parameters and L is maximum likelihood
- Penalizes overly complex models

### Bayesian Information Criterion (BIC)
- BIC = k·ln(n) - 2ln(L)
- More stringent penalty for complexity than AIC

## Applicability Domain Assessment

### Leverage (h)
- h = x_i(X'X)⁻¹x_i'
- Where x_i is the descriptor vector of compound i
- High leverage points may have unreliable predictions

### Standardized Residual
- e_i = (y_i - ŷ_i)/σ
- Where σ is the standard deviation of residuals
- Identifies compounds with poor predictions

## Cross-Validation Strategies

### k-Fold Cross-Validation Error
- CV_error = (1/k)·Σ_i=1^k Error_i
- Where Error_i is the error metric on fold i

### Y-Scrambling
- R²_scrambled should be near zero for robust models
- Significant R² after Y-scrambling indicates chance correlation

## Ensemble Model Evaluation

### Diversity Metrics
- Q-statistic = (a·d - b·c)/(a·d + b·c)
- Where a, b, c, d are counts of correct/incorrect predictions
- Measures correlation between classifier errors

### Ensemble Improvement
- Relative Improvement = (Error_base - Error_ensemble)/Error_base
- Quantifies benefit of ensemble approach
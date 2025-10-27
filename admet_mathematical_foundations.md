# Mathematical Foundations for ADMET Prediction

## Quantitative Structure-Activity Relationships (QSAR)
The fundamental QSAR equation:
$Y = f(X) + ε$

Where:
- $Y$ represents the biological activity or property
- $X$ represents molecular descriptors or fingerprints
- $f$ is the mapping function (linear or non-linear)
- $ε$ is the error term

## Machine Learning Formulations

### Classification Problem
For binary classification of ADMET properties:
$P(y=1|x) = σ(w^T x + b)$

Where:
- $σ$ is the sigmoid function
- $w$ are the model weights
- $x$ are the molecular features
- $b$ is the bias term

### Regression Problem
For continuous ADMET properties:
$y = w^T x + b + ε$

### Deep Learning Approaches
Neural network formulation:
$h_l = σ(W_l h_{l-1} + b_l)$

Where:
- $h_l$ is the output of layer $l$
- $W_l$ are the weights of layer $l$
- $b_l$ is the bias of layer $l$
- $σ$ is the activation function

## Graph Neural Networks for Molecular Representation
Message passing framework:
$h_v^{(k)} = UPDATE^{(k)}(h_v^{(k-1)}, AGGREGATE^{(k)}({h_u^{(k-1)} : u ∈ N(v)}))$

Where:
- $h_v^{(k)}$ is the feature vector of node $v$ at layer $k$
- $N(v)$ is the set of neighboring nodes of $v$
- $AGGREGATE$ and $UPDATE$ are learnable functions

## Uncertainty Quantification
Prediction interval for regression:
$ŷ ± t_{α/2,n-p} · s · \sqrt{1 + x_0^T(X^TX)^{-1}x_0}$

Where:
- $ŷ$ is the predicted value
- $t_{α/2,n-p}$ is the t-statistic
- $s$ is the standard error of the regression
- $x_0$ is the feature vector for prediction
- $X$ is the training data matrix

## Applicability Domain Assessment
Leverage-based approach:
$h_i = x_i^T(X^TX)^{-1}x_i$

Where:
- $h_i$ is the leverage of compound $i$
- $x_i$ is the feature vector of compound $i$
- $X$ is the training data matrix

Warning threshold typically set at:
$h^* = 3p/n$

Where:
- $p$ is the number of model parameters
- $n$ is the number of training compounds
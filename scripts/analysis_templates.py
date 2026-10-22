"""Editable analysis chart types from explicit deterministic demonstration inputs.

No model packages are required: diagnostics use supplied demo labels/predictions,
and the linear-model Shapley values are computed exactly from a saved background.
"""
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D

SEED = 20261010
COLORS = ['#0072b2', '#d55e00', '#009e73', '#cc79a7']
CATALOG = [
    ('precision-recall', 'PR 曲线图', '精确率、召回率、平均精确率与参考线'),
    ('confusion-matrix', '混淆矩阵图', '真实类别与预测类别、计数及归一化比例'),
    ('calibration', '校准曲线图', '预测概率、分箱观察比例与理想参考线'),
    ('learning-curve', '学习曲线图', '样本量、训练与验证误差、折间变化带'),
    ('residual', '残差图', '预测值、残差、零线与分箱趋势'),
    ('feature-importance', '特征重要性棒棒糖图', '排序重要性、点线连接与重复变化区间'),
    ('shap-beeswarm', 'SHAP 蜂群图', '逐样本贡献、特征值颜色与密集点避让'),
    ('shap-waterfall', '贡献瀑布图', 'SHAP 基准值、正负贡献与最终预测的累积关系'),
    ('partial-dependence', '部分依赖图', '平均响应、个体条件曲线与特征取值'),
    ('decision-boundary', '决策边界图', '二维预测概率、分类边界与观测点'),
    ('enrichment-bubble', '富集气泡图', '条目、命中比例、计数大小与显著性颜色'),
    ('enrichment-curve', '富集曲线图', '排序位置、加权累计得分与命中刻线'),
]
REFERENCES = {
    'precision-recall': 'https://scikit-learn.org/stable/modules/generated/sklearn.metrics.average_precision_score.html',
    'confusion-matrix': 'https://scikit-learn.org/stable/modules/generated/sklearn.metrics.confusion_matrix.html',
    'calibration': 'https://scikit-learn.org/stable/modules/calibration.html',
    'learning-curve': 'https://scikit-learn.org/stable/modules/learning_curve.html',
    'feature-importance': 'https://scikit-learn.org/stable/modules/permutation_importance.html',
    'shap-beeswarm': 'https://shap.readthedocs.io/en/stable/example_notebooks/api_examples/plots/beeswarm.html',
    'shap-waterfall': 'https://shap.readthedocs.io/en/stable/example_notebooks/api_examples/plots/waterfall.html',
    'partial-dependence': 'https://scikit-learn.org/stable/modules/partial_dependence.html',
    'decision-boundary': 'https://scikit-learn.org/stable/modules/generated/sklearn.inspection.DecisionBoundaryDisplay.html',
    'enrichment-bubble': 'https://yulab-smu.top/biomedical-knowledge-mining-book/enrichplot.html',
    'enrichment-curve': 'https://www.gsea-msigdb.org/gsea/doc/GSEAUserGuideFrame.html',
}


def frame(size=(7.2, 5.3), right=.94, left=.16, bottom=.17):
    fig, ax = plt.subplots(figsize=size)
    fig.subplots_adjust(left=left, right=right, bottom=bottom, top=.85)
    return fig, ax


def binary_demo(rng):
    x = rng.normal(size=(360, 3))
    probability = 1 / (1 + np.exp(-(1.5*x[:, 0] - .9*x[:, 1] + .5*x[:, 2] - .45)))
    labels = (rng.random(len(x)) < probability).astype(int)
    scores = [np.clip(probability + rng.normal(0, noise, len(x)), .001, .999)
              for noise in (.08, .2)]
    return labels, scores


def precision_recall_values(labels, scores):
    labels, scores = np.asarray(labels), np.asarray(scores)
    order = np.argsort(-scores, kind='stable')
    y, s = labels[order], scores[order]
    ends = np.r_[np.flatnonzero(np.diff(s)), len(s)-1]
    positives = int(y.sum())
    if not positives or positives == len(y):
        raise ValueError('PR 示意输入需要同时包含正负类别')
    tp = np.cumsum(y)[ends]
    precision = tp/(ends+1)
    recall = tp/positives
    # Group tied thresholds before calculating the non-interpolated AP.
    ap = float(np.sum(np.diff(np.r_[0, recall])*precision))
    return np.r_[0, recall], np.r_[1, precision], ap


def precision_recall(rng):
    fig, ax = frame()
    labels, scores = binary_demo(rng)
    models = []
    for i, score in enumerate(scores):
        recall, precision, ap = precision_recall_values(labels, score)
        ax.step(recall, precision, where='pre', color=COLORS[i], lw=1.8,
                label=f'Model {chr(65+i)} · AP = {ap:.3f}')
        models.append({'score':score.tolist(), 'recall':recall.tolist(),
                       'precision':precision.tolist(), 'averagePrecision':ap})
    prevalence = float(labels.mean())
    ax.axhline(prevalence, color='#657684', ls='--', lw=1, label=f'Prevalence = {prevalence:.2f}')
    ax.set(xlabel='Recall', ylabel='Precision', xlim=(0, 1.02), ylim=(0, 1.04))
    ax.legend(frameon=False, loc='lower left', fontsize=8)
    return fig, {'labels':labels.tolist(), 'models':models, 'prevalence':prevalence}, 'AP uses recall-weighted precision, not trapezoidal PR area. Demonstration predictions.'


def confusion_matrix(rng):
    fig, ax = frame(size=(6.7, 5.4), left=.18)
    labels = rng.choice(3, 250, p=[.44, .34, .22])
    probabilities = np.array([[.82, .13, .05], [.1, .8, .1], [.12, .18, .7]])
    predicted = np.array([rng.choice(3, p=probabilities[v]) for v in labels])
    counts = np.zeros((3, 3), dtype=int)
    np.add.at(counts, (labels, predicted), 1)
    fractions = counts / counts.sum(1, keepdims=True)
    image = ax.imshow(fractions, cmap='Blues', vmin=0, vmax=1)
    for i in range(3):
        for j in range(3):
            label = ax.text(j, i, f'{counts[i,j]}\n{fractions[i,j]:.0%}', ha='center', va='center',
                            color='white' if fractions[i,j]>.55 else '#263744', fontsize=11)
            label._fam_confusion_cell = (i, j)
    names = [f'Class {chr(65+i)}' for i in range(3)]
    ax.set(xticks=range(3), xticklabels=names, yticks=range(3), yticklabels=names,
           xlabel='Predicted class', ylabel='True class')
    fig.colorbar(image, ax=ax, pad=.035, label='Proportion within true class')
    return fig, {'true':labels.tolist(), 'predicted':predicted.tolist(), 'counts':counts.tolist(),
                 'rowProportions':fractions.tolist()}, 'Rows are true classes; colors are row-normalized and annotations retain original counts.'


def calibration(rng):
    fig, ax = frame()
    labels, scores = binary_demo(rng)
    edges = np.linspace(0, 1, 9)
    models = []
    for i, score in enumerate(scores):
        bins = np.minimum(np.searchsorted(edges, score, side='right')-1, len(edges)-2)
        records = []
        for j in range(len(edges)-1):
            mask = bins==j
            if mask.any():
                records.append({'bin':j, 'count':int(mask.sum()), 'meanPrediction':float(score[mask].mean()),
                                'observedFraction':float(labels[mask].mean())})
        ax.plot([r['meanPrediction'] for r in records], [r['observedFraction'] for r in records],
                marker='o', ms=4, lw=1.5, color=COLORS[i], label=f'Model {chr(65+i)}')
        models.append({'score':score.tolist(), 'bins':records})
    ax.plot([0, 1], [0, 1], '--', color='#657684', lw=1, label='Ideal')
    ax.set(xlabel='Mean predicted probability', ylabel='Observed positive fraction',
           xlim=(-.02, 1.02), ylim=(-.02, 1.02))
    ax.legend(frameon=False, loc='upper left')
    return fig, {'labels':labels.tolist(), 'binEdges':edges.tolist(), 'models':models}, 'Equal-width bins; empty bins are omitted. Both axes are probabilities, not sensitivity or specificity.'


def linear_demo(rng):
    x = rng.normal(size=(220, 6))
    y = .7 + x@np.array([1.8, -.9, .55, 0, .2, -.1]) + rng.normal(0, .65, len(x))
    train, test = np.arange(150), np.arange(150, len(x))
    design = np.column_stack([np.ones(len(x)), x])
    coefficients = np.linalg.lstsq(design[train], y[train], rcond=None)[0]
    return x, y, train, test, coefficients


def learning_curve(rng):
    fig, ax = frame()
    x, y, _, _, _ = linear_demo(rng)
    design = np.column_stack([np.ones(len(x)), x])
    sizes = np.array([16, 28, 45, 70, 105, 150])
    train_scores, valid_scores, folds = [], [], []
    for fold in range(5):
        order = rng.permutation(len(x)); pool, valid = order[:150], order[150:]
        train_errors, valid_errors = [], []
        for size in sizes:
            indices = pool[:size]
            coef = np.linalg.lstsq(design[indices], y[indices], rcond=None)[0]
            train_errors.append(float(np.sqrt(np.mean((design[indices]@coef-y[indices])**2))))
            valid_errors.append(float(np.sqrt(np.mean((design[valid]@coef-y[valid])**2))))
        train_scores.append(train_errors); valid_scores.append(valid_errors)
        folds.append({'trainPool':pool.tolist(), 'validation':valid.tolist()})
    for values, label, color in [(train_scores, 'Training', COLORS[0]), (valid_scores, 'Validation', COLORS[1])]:
        values = np.asarray(values); mean, sd = values.mean(0), values.std(0, ddof=1)
        ax.plot(sizes, mean, '-o', color=color, ms=4, label=label)
        band = ax.fill_between(sizes, np.maximum(0, mean-sd), mean+sd, color=color, alpha=.15)
        band._fam_analysis_band = True
    ax.set(xlabel='Training sample size', ylabel='RMSE', ylim=(0, None))
    ax.legend(frameon=False)
    return fig, {'X':x.tolist(), 'y':y.tolist(), 'sizes':sizes.tolist(), 'folds':folds,
                 'trainingRMSE':train_scores, 'validationRMSE':valid_scores}, 'OLS refitted on nested training subsets; bands show ±1 sample SD over five fixed splits, not confidence intervals.'


def residual(rng):
    fig, ax = frame()
    x, y, train, test, coef = linear_demo(rng)
    predicted = np.column_stack([np.ones(len(test)), x[test]])@coef
    errors = y[test]-predicted
    ax.scatter(predicted, errors, s=27, color=COLORS[0], alpha=.75, edgecolors='white', lw=.35)
    ax.axhline(0, color='#657684', ls='--', lw=1, label='Zero residual')
    groups = np.array_split(np.argsort(predicted), 7)
    means = [(float(predicted[g].mean()), float(errors[g].mean())) for g in groups]
    ax.plot(*np.array(means).T, '-o', color=COLORS[1], ms=3, label='Binned mean')
    ax.set(xlabel='Predicted value', ylabel='Observed − predicted')
    ax.legend(frameon=False)
    return fig, {'X':x.tolist(), 'observed':y.tolist(), 'train':train.tolist(), 'test':test.tolist(),
                 'coefficients':coef.tolist(), 'predicted':predicted.tolist(), 'residual':errors.tolist(),
                 'binnedMean':means}, 'Held-out residuals; OLS uses the separate saved training indices. Binned means are a descriptive trend.'


def feature_importance(rng):
    fig, ax = frame(left=.23)
    x, y, train, test, coef = linear_demo(rng)
    xt, yt = x[test], y[test]
    predict = lambda values: coef[0]+values@coef[1:]
    baseline = float(np.mean((predict(xt)-yt)**2)); repeats = []
    for j in range(x.shape[1]):
        values = []
        for _ in range(12):
            altered = xt.copy(); altered[:,j] = rng.permutation(altered[:,j])
            values.append(float(np.mean((predict(altered)-yt)**2)-baseline))
        repeats.append(values)
    repeats = np.asarray(repeats); mean, sd = repeats.mean(1), repeats.std(1, ddof=1)
    order = np.argsort(-mean); positions = np.arange(len(order))
    ax.hlines(positions, 0, mean[order], color=COLORS[0], lw=1.5, alpha=.55)
    ax.errorbar(mean[order], positions, xerr=sd[order], fmt='o', color=COLORS[0], ms=6,
                ecolor='#657684', elinewidth=1, capsize=3)
    ax.axvline(0, color='#9aa6ac', lw=.8)
    ax.set(yticks=positions, yticklabels=[f'Feature {j+1}' for j in order],
           xlabel='Increase in held-out MSE', ylim=(len(order)-.4, -.6))
    return fig, {'X':x.tolist(), 'y':y.tolist(), 'train':train.tolist(), 'test':test.tolist(),
                 'coefficients':coef.tolist(), 'baselineMSE':baseline, 'repeatImportances':repeats.tolist(),
                 'mean':mean.tolist(), 'sd':sd.tolist(), 'order':order.tolist()}, 'Held-out permutation importance; intervals are ±1 SD over 12 shuffles, not confidence intervals. Negative importances are retained.'


def shap_demo(rng):
    x, y, train, test, coef = linear_demo(rng)
    background = x[train].mean(0)
    base = float(coef[0]+background@coef[1:])
    values = (x[test]-background)*coef[1:]
    predicted = coef[0]+x[test]@coef[1:]
    return {'X':x.tolist(), 'y':y.tolist(), 'train':train.tolist(), 'test':test.tolist(),
            'coefficients':coef.tolist(), 'backgroundMean':background.tolist(), 'baseValue':base,
            'shapValues':values.tolist(), 'predicted':predicted.tolist()}


def swarm_offsets(values, step=.065, spread=.33):
    # Pack in display-like normalized bins so point positions reflect density.
    extent = max(float(np.ptp(values)), 1e-8)
    bins = np.floor((values-values.min())/extent*28).astype(int)
    offset = np.zeros(len(values))
    for key in np.unique(bins):
        indices = np.flatnonzero(bins==key)
        sequence = np.array([0]+[v for i in range(1, len(indices)) for v in (i, -i)])[:len(indices)]
        offset[indices] = sequence*min(step, spread/max(1, int(np.ceil((len(indices)-1)/2))))
    return offset


def shap_beeswarm(rng):
    fig, ax = frame(size=(7.6, 5.5), left=.22)
    data = shap_demo(rng); values = np.asarray(data['shapValues'])
    x = np.asarray(data['X'])[data['test']]
    order = np.argsort(-np.mean(np.abs(values), axis=0)); normalized = []
    for row, j in enumerate(order):
        low, high = np.quantile(x[:,j], [.05, .95])
        color = np.clip((x[:,j]-low)/max(high-low, 1e-8), 0, 1)
        normalized.append(color.tolist())
        image = ax.scatter(values[:,j], row+swarm_offsets(values[:,j]), c=color, cmap='coolwarm',
                           vmin=0, vmax=1, s=18, alpha=.85, edgecolors='none', zorder=3)
        ax.axhline(row, color='#e6ebee', lw=.6, zorder=0)
    ax.axvline(0, color='#75858c', lw=.8)
    ax.set(yticks=range(len(order)), yticklabels=[f'Feature {j+1}' for j in order],
           xlabel='SHAP value (prediction units)', ylim=(len(order)-.4, -.6))
    cb = fig.colorbar(image, ax=ax, pad=.03, label='Feature value (within feature)')
    cb.set_ticks([0, 1], labels=['Low', 'High'])
    data.update(order=order.tolist(), normalizedColor=normalized)
    return fig, data, 'Exact linear interventional Shapley contributions relative to saved independent-feature background means; color is scaled within each feature.'


def shap_waterfall(rng):
    fig, ax = frame(size=(7.7, 5.5), left=.24)
    data = shap_demo(rng); index = 4
    contributions = np.asarray(data['shapValues'])[index]
    order = np.argsort(-np.abs(contributions)); base = data['baseValue']
    cursor = base; positions = np.arange(len(order)); starts = []
    for row, j in enumerate(order):
        delta = float(contributions[j]); starts.append(cursor)
        ax.barh(row, abs(delta), left=min(cursor, cursor+delta), height=.62,
                color=COLORS[1] if delta>=0 else COLORS[0], edgecolor='white', lw=.5)
        if row<len(order)-1:
            ax.plot([cursor+delta]*2, [row+.31, row+.69], color='#9aa6ac', ls='--', lw=.8)
        ax.text(cursor+delta/2, row, f'{delta:+.2f}', va='center', ha='center', fontsize=8,
                color='white' if abs(delta)>.4 else '#263744')
        cursor += delta
    ax.axvline(base, color='#657684', ls=':', lw=1, label=f'Base = {base:.2f}')
    ax.axvline(cursor, color='#263744', ls='--', lw=1, label=f'Prediction = {cursor:.2f}')
    ax.set(yticks=positions, yticklabels=[f'Feature {j+1}' for j in order],
           xlabel='Prediction units', ylim=(len(order)-.4, -.6))
    ax.margins(x=.18); ax.legend(frameon=False, loc='upper left', bbox_to_anchor=(0, 1.08), ncols=2, fontsize=8)
    data.update(sample=index, order=order.tolist(), starts=starts, contribution=contributions.tolist(), finalValue=cursor)
    return fig, data, 'One demonstration observation: base + sum of exact saved contributions = prediction. Sorted features retain the same additive total.'


def nonlinear_prediction(x):
    return .4+1.2*np.sin(x[:,0])+.45*x[:,1]**2+.35*x[:,0]*x[:,1]-.2*x[:,2]


def partial_dependence(rng):
    fig, ax = frame(); background = rng.normal(size=(90, 3))
    grid = np.linspace(*np.quantile(background[:,0], [.03, .97]), 70)
    curves = np.array([nonlinear_prediction(np.column_stack([np.full(len(background), value), background[:,1:]])) for value in grid]).T
    for i in range(12):
        ax.plot(grid, curves[i], color=COLORS[0], lw=.7, alpha=.2, label='Individual curves' if i==0 else None)
    mean = curves.mean(0)
    ax.plot(grid, mean, color=COLORS[1], lw=2.2, label='Partial dependence')
    ax.plot(background[:,0], np.full(len(background), -.04), '|', color='#657684', ms=5,
            transform=ax.get_xaxis_transform(), clip_on=False)
    ax.set(xlabel='Feature 1', ylabel='Predicted response')
    ax.legend(frameon=False)
    return fig, {'background':background.tolist(), 'grid':grid.tolist(), 'individualCurves':curves.tolist(),
                 'partialDependence':mean.tolist(), 'displayedIndividuals':list(range(12)),
                 'model':'0.4 + 1.2*sin(x0) + 0.45*x1**2 + 0.35*x0*x1 - 0.2*x2'}, 'Average intervention predictions from the explicit demo function; thin curves are 12 saved individuals, not confidence bands.'


def decision_boundary(rng):
    fig, ax = frame(size=(7.2, 5.5)); x = rng.normal(size=(160, 2))
    truth = 1/(1+np.exp(-(-.25+1.8*x[:,0]-1.15*x[:,1])))
    labels = (rng.random(len(x))<truth).astype(int)
    design = np.column_stack([np.ones(len(x)), x]); coef = np.zeros(3)
    penalty = np.diag([0, .1, .1])
    for _ in range(35):
        p = 1/(1+np.exp(-np.clip(design@coef, -30, 30)))
        gradient = design.T@(p-labels)+penalty@coef
        hessian = (design.T*(p*(1-p)))@design+penalty
        step = np.linalg.solve(hessian, gradient); coef -= step
        if np.linalg.norm(step)<1e-8: break
    grid = np.linspace(-3, 3, 75); xx, yy = np.meshgrid(grid, grid)
    probability = 1/(1+np.exp(-(coef[0]+coef[1]*xx+coef[2]*yy)))
    image = ax.contourf(xx, yy, probability, levels=np.linspace(0, 1, 13), cmap='RdBu_r', vmin=0, vmax=1, alpha=.5)
    ax.contour(xx, yy, probability, levels=[.5], colors='#263744', linewidths=1.3)
    for j, marker in enumerate(['o', '^']):
        mask = labels==j
        ax.scatter(*x[mask].T, s=24, marker=marker, color=COLORS[j], edgecolors='white', lw=.45, label=f'Class {chr(65+j)}')
    ax.set(xlabel='Feature 1', ylabel='Feature 2', xlim=(-3, 3), ylim=(-3, 3))
    ax.legend(frameon=False, loc='upper left')
    fig.colorbar(image, ax=ax, pad=.03, label='Predicted probability of class B')
    return fig, {'X':x.tolist(), 'labels':labels.tolist(), 'coefficients':coef.tolist(),
                 'grid':grid.tolist(), 'probability':probability.tolist(), 'threshold':.5,
                 'l2Penalty':.1}, 'Two-feature penalized logistic fit on synthetic observations; probability shading and the 0.5 boundary use the same saved coefficients.'


def bh_adjust(pvalues):
    values = np.asarray(pvalues); order = np.argsort(values)
    ranked = np.minimum.accumulate((values[order]*len(values)/np.arange(1, len(values)+1))[::-1])[::-1]
    result = np.empty_like(values); result[order] = np.clip(ranked, 0, 1)
    return result


def enrichment_bubble(rng):
    from scipy.stats import hypergeom
    fig, ax = frame(size=(8.1, 5.9), left=.2, right=.78, bottom=.17)
    universe, selected = 600, 75
    records = []
    for i in range(10):
        set_size = int(rng.integers(45, 135))
        hit_count = int(min(set_size, 8+i*2+rng.integers(0, 5)))
        members = np.r_[rng.choice(selected, hit_count, replace=False),
                        rng.choice(np.arange(selected, universe), set_size-hit_count, replace=False)]
        p = float(hypergeom.sf(hit_count-1, universe, set_size, selected))
        records.append({'term':f'Term {chr(65+i)}', 'members':members.tolist(), 'setSize':set_size,
                        'count':hit_count, 'ratio':hit_count/selected, 'pValue':p})
    adjusted = bh_adjust([r['pValue'] for r in records])
    for r, q in zip(records, adjusted):r['adjustedP'] = float(q)
    records.sort(key=lambda r:r['ratio'], reverse=True)
    ratios = np.array([r['ratio'] for r in records]); counts = np.array([r['count'] for r in records])
    significance = -np.log10(np.maximum([r['adjustedP'] for r in records], np.finfo(float).tiny))
    scale = 14
    image = ax.scatter(ratios, np.arange(len(records)), s=counts*scale, c=significance,
                       cmap='viridis', edgecolors='#52656d', lw=.5)
    image._fam_enrichment_bubbles = True
    ax.set(yticks=range(len(records)), yticklabels=[r['term'] for r in records],
           xlabel='Hit ratio (count / selected size)', ylim=(len(records)-.35, -.65))
    ax.margins(x=.22); ax.set_axisbelow(True); ax.grid(axis='y', color='#e6ebee', lw=.55)
    colorax = fig.add_axes([.82, .5, .025, .32])
    fig.colorbar(image, cax=colorax, label='−log10(adjusted P)')
    sizes = [10, 20, 30]
    handles = [Line2D([], [], marker='o', ls='none', markersize=np.sqrt(v*scale),
                      markerfacecolor='none', markeredgecolor='#52656d', label=str(v)) for v in sizes]
    ax.legend(handles=handles, title='Count', frameon=False, loc='upper left',
              bbox_to_anchor=(1.02, .42), labelspacing=1.2, borderaxespad=0)
    return fig, {'universeSize':universe, 'selectedIds':list(range(selected)), 'terms':records,
                 'areaScale':scale, 'displayOrder':[r['term'] for r in records]}, 'Explicit demo term memberships; one-sided hypergeometric P and BH adjustment over all ten terms. Marker area is proportional to count.'


def enrichment_curve(rng):
    fig, ax = frame(size=(7.5, 5.3)); n = 220
    metric = np.sort(rng.normal(size=n))[::-1]
    hits = np.zeros(n, dtype=bool)
    indices = np.r_[rng.choice(np.arange(65), 21, replace=False), rng.choice(np.arange(65, n), 9, replace=False)]
    hits[indices] = True; weights = np.abs(metric)*hits
    increments = weights/weights.sum()-(~hits)/(~hits).sum()
    running = np.r_[0, np.cumsum(increments)]; ranks = np.arange(n+1)
    peak = int(np.argmax(np.abs(running))); score = float(running[peak])
    ax.plot(ranks, running, color=COLORS[2], lw=2, label=f'Running score · ES = {score:.3f}')
    ax.axhline(0, color='#657684', lw=.8)
    ax.axvline(peak, color='#657684', ls='--', lw=.8, label=f'Peak rank = {peak}')
    ax.plot(np.flatnonzero(hits)+1, np.full(hits.sum(), -.075), '|', transform=ax.get_xaxis_transform(),
            color='#354953', ms=8, clip_on=False)
    ax.set(xlabel='Rank', ylabel='Running enrichment score', xlim=(0, n))
    ax.xaxis.labelpad = 17; ax.legend(frameon=False)
    return fig, {'rankedMetric':metric.tolist(), 'hitIndices':np.flatnonzero(hits).tolist(),
                 'weightExponent':1, 'increments':increments.tolist(), 'runningScore':running.tolist(),
                 'peakRank':peak, 'enrichmentScore':score}, 'Weighted running-sum illustration; hit ranks share the same x axis. No permutation P or normalized enrichment score is inferred.'


BUILDERS = {
    'precision-recall':precision_recall, 'confusion-matrix':confusion_matrix,
    'calibration':calibration, 'learning-curve':learning_curve, 'residual':residual,
    'feature-importance':feature_importance, 'shap-beeswarm':shap_beeswarm,
    'shap-waterfall':shap_waterfall, 'partial-dependence':partial_dependence,
    'decision-boundary':decision_boundary, 'enrichment-bubble':enrichment_bubble,
    'enrichment-curve':enrichment_curve,
}


def build(kind, title=None):
    names = {k:n for k,n,_ in CATALOG}
    if kind not in BUILDERS:raise ValueError('未知结果分析图型')
    with plt.rc_context({'font.family':['Arial','Microsoft YaHei'], 'font.size':9,
                         'axes.spines.top':False, 'axes.spines.right':False,
                         'axes.linewidth':.8, 'svg.fonttype':'none'}):
        fig, data, note = BUILDERS[kind](np.random.default_rng(SEED))
        fig.suptitle(title or names[kind], y=.96, fontsize=13, fontfamily='Microsoft YaHei')
        fig.patch.set_alpha(0)
        for ax in fig.axes:ax.patch.set_alpha(0)
        fig._fam_template_data = data
        fig._fam_display_note = note
        fig._fam_template_edition = 'single-v2'
        fig._fam_paper_kind = kind
        # Curve vertices, ranks and category positions are not raw XY observations.
        for ax in fig.axes:
            for artist in list(ax.lines)+list(ax.collections):
                if kind not in ('residual', 'decision-boundary') or artist not in ax.collections or not hasattr(artist, 'get_offsets'):
                    artist._fam_fit_exclude = True
        return fig


def apply_variants(fig, kind, params):
    """Presentation changes preserve captured inputs and stable artist identities."""
    if not params or not fig.axes:return
    ax = fig.axes[0]; data = getattr(fig, '_fam_template_data', {})
    if kind=='confusion-matrix' and ('confusionMode' in params or 'confusionLabels' in params):
        counts = np.asarray(data['counts'], dtype=float)
        mode = params.get('confusionMode', 'row')
        denominator = counts.sum(1, keepdims=True) if mode=='row' else counts.sum(0, keepdims=True)
        values = counts if mode=='count' else np.divide(counts, denominator, out=np.zeros_like(counts), where=denominator!=0)
        image = ax.images[0]; image.set_data(values); image.set_clim(0, max(float(counts.max()), 1) if mode=='count' else 1)
        if image.colorbar:
            image.colorbar.set_label({'count':'Count', 'row':'Proportion within true class', 'column':'Proportion within predicted class'}[mode])
        display = params.get('confusionLabels', 'both')
        for text in ax.texts:
            if not hasattr(text, '_fam_confusion_cell'):continue
            i, j = text._fam_confusion_cell
            count, proportion = f'{int(counts[i,j])}', f'{values[i,j]:.0%}' if mode!='count' else ''
            text.set_text(count if display=='count' or mode=='count' else proportion if display=='proportion' else count+'\n'+proportion)
            text.set_visible(display!='none')
            text.set_color('white' if values[i,j]/image.norm.vmax>.55 else '#263744')
    if kind=='learning-curve' and 'analysisBand' in params:
        for band in ax.collections:
            if getattr(band, '_fam_analysis_band', False):band.set_visible(params['analysisBand']=='sd')
    if kind=='enrichment-bubble' and 'enrichmentX' in params:
        mode = params['enrichmentX']; records = data['terms']
        values = [r['ratio'] if mode=='ratio' else r['count'] if mode=='count' else r['ratio']/(r['setSize']/data['universeSize']) for r in records]
        for artist in ax.collections:
            if getattr(artist, '_fam_enrichment_bubbles', False):artist.set_offsets(np.column_stack([values, np.arange(len(values))]))
        pad = max(float(np.ptp(values))*.22, .02)
        ax.set_xlim(min(values)-pad, max(values)+pad)
        ax.set_xlabel({'ratio':'Hit ratio (count / selected size)', 'count':'Hit count', 'fold':'Fold enrichment'}[mode])

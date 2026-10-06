"""Revision 45 author-authorized technical protocol, not adviser approval."""
from copy import deepcopy

EXPLORATORY_LABEL = 'Exploratory Weekly Configuration v0.1 — Technical / Retrospective Evaluation Only'
WEEK53_NOTICE = ('Week 53 is preserved as an additional source observation. The exploratory annual seasonal period '
                 'remains fixed at 52 and does not constitute final resolution of the 52/53-week calendar structure.')

_ORDERS = [
    ([0, 0, 0], [0, 1, 1, 52]), ([1, 0, 0], [0, 1, 1, 52]),
    ([0, 0, 1], [0, 1, 1, 52]), ([1, 0, 1], [0, 1, 1, 52]),
    ([2, 0, 0], [0, 1, 1, 52]), ([0, 0, 2], [0, 1, 1, 52]),
    ([0, 1, 0], [0, 1, 1, 52]), ([1, 1, 0], [0, 1, 1, 52]),
    ([0, 1, 1], [0, 1, 1, 52]), ([1, 1, 1], [0, 1, 1, 52]),
    ([1, 0, 0], [1, 0, 0, 52]), ([0, 0, 1], [0, 0, 1, 52]),
    ([1, 0, 1], [1, 0, 0, 52]), ([1, 0, 1], [0, 0, 1, 52]),
    ([1, 1, 0], [1, 0, 0, 52]), ([0, 1, 1], [0, 0, 1, 52]),
]


def exploratory_configuration():
    return deepcopy({
        'version': 'exploratory-weekly-v0.1', 'label': EXPLORATORY_LABEL,
        'approved': False, 'approval_reference': None,
        'authorization_reference': 'User final handoff, 2026-10-03, Decisions 44–45',
        'candidates': [{'order': p, 'seasonal_order': s, 'trend': 'n'} for p, s in _ORDERS],
        'nnar_lags': [1, 2, 3, 4, 52], 'hidden_nodes': 3,
        'minimum_training_weeks': 156, 'minimum_residual_examples': 52,
        'residual_burn': 53, 'diagnostic_lag': 52, 'holdout_weeks': 52,
        'missing_policy': 'state_space', 'week53_policy': 'preserve_sequence',
        'maxiter': 300, 'nnar_maxiter': 2000, 'alpha': 1.0, 'seed': 42,
        'uncertainty_method': 'training_residual_rmse',
        'implementation_choices': 'No trend; 53-position residual burn; 52 complete residual examples; diagnostic lag 52. '
                                  'These are documented technical safeguards, not adviser-approved statistical rules.',
    })

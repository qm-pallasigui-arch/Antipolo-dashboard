"""Shared navigation labels for Dash and authenticated account screens."""
PAGES = ['Dashboard', 'Disease Trends', 'Forecasting', 'Model Performance & Insights',
         'Data & Quality', 'Reports', 'Notifications', 'Help & About']
NAV_PAGES = [page for page in PAGES if page != 'Notifications']
NAV_LABELS = {'Model Performance & Insights': 'Model Performance'}
ROLE_LABELS = {'admin': 'Administrator / Researcher', 'viewer': 'Authorized Viewer / Health User'}
PUBLIC_NOTICE = 'Provisional estimates for research use. Not for clinical decisions.'

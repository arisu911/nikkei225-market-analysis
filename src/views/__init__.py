"""
UI Views and Page Renderers for Single-Page Application.
"""
from src.views.overview import render_overview_page
from src.views.weekday_analysis import render_weekday_page
from src.views.intraday_analysis import render_intraday_page
from src.views.opening_analysis import render_opening_page
from src.views.volatility_analysis import render_volatility_page
from src.views.distributions import render_distributions_page

__all__ = [
    "render_overview_page",
    "render_weekday_page",
    "render_intraday_page",
    "render_opening_page",
    "render_volatility_page",
    "render_distributions_page",
]

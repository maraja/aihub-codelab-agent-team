"""The Campus Desk: a team of agents that runs a college help desk."""

from google.adk.agents import LlmAgent

from . import config
from .tools import book_appointment, list_open_slots, lookup_student, search_handbook

# TODO: add the policy agent here.

# TODO: add the booking agent here.

# TODO: add sign_in and the front desk (root_agent) here.

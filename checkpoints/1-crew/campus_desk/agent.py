"""The Campus Desk: a team of agents that runs a college help desk."""

from google.adk.agents import LlmAgent

from . import config
from .reviewer import review_reply
from .tools import book_appointment, list_open_slots, lookup_student, search_handbook


policy_agent = LlmAgent(
    name="policy_agent",
    model=config.MODEL,
    description="Answers questions about college policies, deadlines and rules from the student handbook.",
    instruction="""
You answer students' questions about Ridgeview Polytechnic's policies.
Always call search_handbook first, and answer only from what it returns.
If the handbook doesn't cover the question, say so and suggest the student
book an advising appointment. Keep answers short and friendly.
""",
    tools=[search_handbook],
    after_model_callback=review_reply,
)

booking_agent = LlmAgent(
    name="booking_agent",
    model=config.MODEL,
    description="Books advising appointments and looks up student records.",
    instruction="""
You help the signed-in student book advising appointments.
The signed-in student's ID is {student_id}.
Use list_open_slots to see what's free, ask the student which slot they want,
then call book_appointment. Use lookup_student when you need a student's details.
Confirm the day, time and advisor once it's booked.
""",
    tools=[list_open_slots, book_appointment, lookup_student],
    after_model_callback=review_reply,
)

def sign_in(callback_context):
    """Before every turn, set who's signed in. The client can't change this."""
    callback_context.state["student_id"] = config.SIGNED_IN_STUDENT


root_agent = LlmAgent(
    name="campus_desk",
    model=config.MODEL,
    description="The front desk that reads each request and sends it to the right specialist.",
    instruction="""
You are the front desk of Ridgeview Polytechnic's Campus Desk.
Read the student's request and transfer it to the right specialist:
- policy_agent for questions about policies, deadlines and rules,
- booking_agent for advising appointments and student records.
For greetings or anything else, reply briefly yourself and say what you can help with.
""",
    sub_agents=[policy_agent, booking_agent],
    before_agent_callback=sign_in,
    after_model_callback=review_reply,
)

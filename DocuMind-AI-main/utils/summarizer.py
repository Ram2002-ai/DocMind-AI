import os
import time
import google.generativeai as genai
from google.api_core.exceptions import DeadlineExceeded, ResourceExhausted
from dotenv import load_dotenv

load_dotenv()

genai.configure(api_key=os.getenv("GEMINI_API_KEY"))

model = genai.GenerativeModel("gemini-3.5-flash")


def generate_summary(text, retries=2):

    prompt = f"""
    You are an AI document assistant.

    Summarize the following document in clear bullet points.

    Document:
    {text}
    """

    for attempt in range(retries + 1):
        try:
            response = model.generate_content(
                prompt,
                request_options={"timeout": 60}
            )
            return response.text

        except DeadlineExceeded:
            if attempt == retries:
                return "⚠️ The AI is taking too long to respond. Please try again."
            time.sleep(2)

        except ResourceExhausted:
            return "⚠️ AI usage limit reached. Please wait a moment and try again."


def ask_document(context, question, retries=2):

    prompt = f"""
You are an AI document assistant.

Answer ONLY from the given context.

If the answer is not available, say:
"I couldn't find that information in the document."

Context:
{context}

Question:
{question}
"""

    for attempt in range(retries + 1):
        try:
            response = model.generate_content(
                prompt,
                request_options={"timeout": 60}
            )
            return response.text

        except DeadlineExceeded:
            if attempt == retries:
                return "⚠️ The AI is taking too long to respond. Please try again."
            time.sleep(2)

        except ResourceExhausted:
            return "⚠️ AI usage limit reached. Please wait a moment and try again."
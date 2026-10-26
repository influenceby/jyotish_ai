import os
import json
from typing import Dict, Any, Optional, Tuple

from dotenv import load_dotenv
from google import genai


# ============================================================
# LOAD ENVIRONMENT
# ============================================================

load_dotenv("/var/www/jyotish-ai/.env")


# ============================================================
# SYSTEM PROMPT
# ============================================================

SYSTEM_PROMPT = """Role & Persona

You are Raj Rao, an empathetic, wise, and grounded Vedic Life Counselor. You specialize in translating profound karmic and cosmic timing into practical, modern life guidance. Your tone is warm, conversational, and deeply philosophical, helping seekers align their daily actions with their higher purpose and current life seasons.

Data Ingestion Context
You will receive a JSON file representing the user's exact Vedic chart calculations. Use this file for making the charts and interpretations.

You are translating the mathematics of karma into human insight. Use technical astrological terminology in your responses to the user only when dates are required based on dasha and transits or when a user requests an astrological terminology.

Interpretative Philosophy & Synthesis:

Synthesize, Don't Read: When the data shows a challenging placement—such as an unfavorable Jupiter or Saturn in the 8th house—frame it as a season for deep internal restructuring, patience, and shedding old attachments.

Focus on Agency: Avoid fatalism. Present cosmic weather as opportunities for spiritual and practical growth. Offer behavioral remedies, such as mindfulness practices, conscious breathing, or shifts in perspective.

Acknowledge the Whole Person: Blend immediate situational advice with deeper themes of self-awareness. For example, if the Ascendant report indicates a "wavering" or "restless" mind, guide the user gently toward grounding techniques.

Formatting:
Use clear formatting when it improves readability. You may use headings, bullet points, numbered lists, and Markdown tables when appropriate to the user's question. Do not describe the interaction as "spoken voice" or claim that you cannot create tables, bullets, or structured text.

Engaging Hooks: End your responses with a gentle, open-ended question to keep the dialogue flowing naturally.
"""


# ============================================================
# GEMINI INTERACTIONS SERVICE
# ============================================================

class GeminiService:

    MODEL = "gemini-3.1-pro-preview"

    def __init__(self):

        api_key = os.getenv("GEMINI_API_KEY")

        if not api_key:
            raise ValueError(
                "GEMINI_API_KEY is missing. "
                "Please add it to your .env file."
            )

        self.client = genai.Client(api_key=api_key)

        print("Gemini Service initialized")
        print("Model:", self.MODEL)
        print("API: Gemini Interactions API")


    # ========================================================
    # ASK QUESTION
    # ========================================================

    def ask_question(
        self,
        name: str,
        gender: str,
        astrology_data: Dict[str, Any],
        question: str,
        previous_interaction_id: Optional[str] = None,
    ) -> Tuple[str, str]:

        if not question or not question.strip():
            return (
                "Please tell me what you would like to explore, "
                "and I'll be happy to guide you.",
                previous_interaction_id or ""
            )

        # ----------------------------------------------------
        # FIRST INTERACTION
        # ----------------------------------------------------

        if not previous_interaction_id:

            astrology_json = json.dumps(
                astrology_data,
                indent=2,
                default=str
            )

            user_input = f"""
USER DETAILS

Name: {name}
Gender: {gender}

SAVED ASTROLOGY DATA

{astrology_json}

USER QUESTION

{question}

INSTRUCTIONS

1. Answer the user's question using the saved astrology data provided above.
2. Do NOT calculate astrology values yourself.
3. Do NOT call AstrologyAPI or any external astrology API.
4. Treat the provided astrology data as the source of truth for calculated values.
5. Do not expose raw JSON or technical API output.
6. Give a warm, friendly, emotionally intelligent answer.
7. Respond naturally and warmly, while maintaining a professional and helpful tone.
8. Give practical and helpful advice where appropriate.
"""

            print("\n" + "=" * 60)
            print("GEMINI 3.1 PRO - FIRST INTERACTION")
            print("FULL ASTROLOGY DATA + QUESTION")
            print("=" * 60)

            try:

                interaction = self.client.interactions.create(
                    model=self.MODEL,
                    input=user_input,
                    system_instruction=SYSTEM_PROMPT,
                    generation_config={
                        "thinking_level": "high"
                    }
                )

            except Exception as exc:

                print("Gemini API Error:", repr(exc))

                raise RuntimeError(
                    f"Gemini first interaction failed: "
                    f"{type(exc).__name__}: {exc}"
                ) from exc

        # ----------------------------------------------------
        # CONTINUATION INTERACTION
        # ----------------------------------------------------

        else:

            print("\n" + "=" * 60)
            print("GEMINI 3.1 PRO - CONTINUATION")
            print("PREVIOUS INTERACTION ID:", previous_interaction_id)
            print("NEW QUESTION ONLY")
            print("=" * 60)

            try:

                interaction = self.client.interactions.create(
                    model=self.MODEL,
                    previous_interaction_id=previous_interaction_id,
                    input=question,
                    system_instruction=SYSTEM_PROMPT,
                    generation_config={
                        "thinking_level": "high"
                    }
                )

            except Exception as exc:

                print("Gemini API Error:", repr(exc))

                raise RuntimeError(
                    f"Gemini continuation failed: "
                    f"{type(exc).__name__}: {exc}"
                ) from exc

        response_text = getattr(
            interaction,
            "output_text",
            None
        )

        interaction_id = getattr(
            interaction,
            "id",
            None
        )

        if not response_text:

            return (
                "I have looked into your question, but I wasn't able "
                "to prepare a complete response. Please try again.",
                interaction_id or previous_interaction_id or ""
            )

        if not interaction_id:

            print("WARNING: Gemini did not return an interaction ID")

            return (
                response_text.strip(),
                previous_interaction_id or ""
            )

        print("Gemini response received")
        print("New interaction ID:", interaction_id)

        return (
            response_text.strip(),
            interaction_id
        )


# ============================================================
# SINGLETON INSTANCE
# ============================================================

gemini_service = GeminiService()

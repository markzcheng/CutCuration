# backend/app/prompts.py

# Base constraints required to keep the Python script from breaking
BASE_JSON_INSTRUCTIONS = """
Return the response as a single, valid JSON object with ONLY the keys "new_filename", "description", and "length_seconds".

1. **new_filename**: Create a short, descriptive, human-readable filename in snake_case. Include key actions or subjects. Append the video length in seconds at the end (e.g., "dicing_onions_for_sauce_24sec.mp4").
2. **description**: Write a one-sentence, natural language summary of what is happening in the clip. Be specific. If there is dialogue, summarize the key point. If it is silent B-roll, describe the visual action.
3. **length_seconds**: State the exact length of the video in seconds as an integer.
"""

EDITING_CONFIGS = {
    "short_form_cooking": {
        "analysis_prompt": f"""
        You are an expert video editor specialized in viral, short-form culinary content. Analyze this raw cooking clip with a maximum 60-second final video constraint in mind. 
        Evaluate the footage for high visual engagement, satisfying ASMR sounds, dynamic motion to act as an immediate "hook", or a strong final dish "money shot". 
        Assume the creator will overlay a high-energy voiceover during post-production.
        {BASE_JSON_INSTRUCTIONS}
        """,
        "summary_prompt": """
        You are an expert video editor for short-form cooking content. Suggest a rapid-fire, highly engaging sequence for a 60-second vertical video. Identify the best 3-second hook, the fastest process sequence, and the ultimate payoff shot. Highlight any redundant clips to discard.
        """
    },
    "long_form_vlog": {
        "analysis_prompt": f"""
        You are an experienced documentary and travel vlog editor. Analyze this raw video clip intended for a long-form YouTube diary capturing travel or daily life in Boston.
        Evaluate the footage for storytelling elements: natural environmental audio, ambient scenery, direct on-camera talking, or authentic "slice of life" moments that evoke a sense of memory and place.
        {BASE_JSON_INSTRUCTIONS}
        """,
        "summary_prompt": """
        You are a documentary story editor. Suggest a natural, immersive narrative structure for a long-form YouTube vlog. Group clips by location or chronological sequence, highlighting strong talking/vlogging segments as narrative pillars and scenic clips as contextual B-roll.
        """
    }
}
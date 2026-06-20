import asyncio
import sys
sys.path.insert(0, ".")

from app.services.ai_service import generate_step_content

result = asyncio.run(generate_step_content(
    step_index=0,
    total_steps=3,
    segment_start=0,
    segment_end=30,
    transcript_excerpt="First, open the terminal and navigate to your project folder",
    video_title="Test Video",
    config={
        "experience_level": "beginner",
        "explanation_style": "simple",
        "checkpoint_frequency": "medium",
        "user_skills": "",
    },
))

print(result)

# Gemini agent – project instructions

Read **docs/GEMINI_HANDOFF.md** before writing any code.

Project: professional German faceless company documentaries with genuine, relevant photo/video evidence, documentary-specific infographics, natural narration and Remotion.

## Development order
1. Make the six-scene Volkswagen real-photo integration pilot pass in GitHub Actions, with actual MP4 and audio, and manually review the image-sentence match.
2. Improve source-bound research and scripts with Gemini; use Gemini 3.8 Flash TTS only when the user has authorized API costs.
3. Add visual evaluation of the actual B-roll content (not thumbnails alone), scene/word synchronization, high-quality Remotion layouts, factual charting.
4. After each exported video review repeat visuals, pace, pronunciation, transitions, subtitles, and fact/source rights. Permanently fix root causes, expand tests.

## Safety and quality
- No invented source, company-event footage, TTS timings, licenses or metric claims.
- A Wikimedia title or vision verdict never proves exact image content or legal rights.
- Do not publish automatically. Historical VW pilot stays publication_ready=false without explicit clearance.
- Do not commit credentials or echo secrets. Configure GEMINI_API_KEY and PEXELS_API_KEY outside the repo, or use GitHub Actions secrets.
- Create branches and PRs, run all CI (including real-photo pilot), and state limitations honestly.

Read docs/GEMINI_HANDOFF.md for reproducible commands, test gates and the full roadmap.

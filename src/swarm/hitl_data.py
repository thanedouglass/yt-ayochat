"""Simulated Inbound Comment Queue & Research Benchmark Scenarios derived from YouTube Data."""

from __future__ import annotations

from typing import Any, Dict, List

# Top 10 Videos extracted from Table data.csv
TOP_10_VIDEOS: List[Dict[str, Any]] = [
    {
        "id": "DOC-01",
        "video_id": "M1G92FWmdJw",
        "title": "KATSEYE (캣츠아이) 'Hootie Frutti' Official Dance Cover #katseye #katseye_hootiefrutti #kpop #fypシ゚viral",
        "views": 476326,
        "category": "DANCE_CHOREO",
        "url": "https://youtube.com/watch?v=M1G92FWmdJw",
    },
    {
        "id": "DOC-02",
        "video_id": "Otu-5CrcWHo",
        "title": "KATSEYE (캣츠아이) 'Hootie Frutti' Dance Challenge #katseye #eyekons #shorts #ayodesci #kpop #fypシ゚viral",
        "views": 146175,
        "category": "DANCE_CHOREO",
        "url": "https://youtube.com/watch?v=Otu-5CrcWHo",
    },
    {
        "id": "DOC-03",
        "video_id": "wJph6fDaJuk",
        "title": "@katseyeworld ‘Hootie Frutti’(캣츠아이) Dance Practice #캣츠아이 #hootiefrutti #katseye #ayodesci #fypviralシ",
        "views": 109588,
        "category": "DANCE_CHOREO",
        "url": "https://youtube.com/watch?v=wJph6fDaJuk",
    },
    {
        "id": "DOC-04",
        "video_id": "jQJqh-zTZQA",
        "title": "‘Pink Blush’ Original Dance for@PrincessDollyBabe 💘 #pinkblush #princessdollybabe #trending #fypシ゚",
        "views": 89732,
        "category": "ORIGINAL_CHOREO",
        "url": "https://youtube.com/watch?v=jQJqh-zTZQA",
    },
    {
        "id": "DOC-05",
        "video_id": "KBr9Y0ljCXQ",
        "title": "K-pop in Public @katseyeworld 🍒🍉#hootiefrutti #katseye #katseye_hootiefrutti #fypシ゚viral",
        "views": 29275,
        "category": "KPOP_IN_PUBLIC",
        "url": "https://youtube.com/watch?v=KBr9Y0ljCXQ",
    },
    {
        "id": "DOC-06",
        "video_id": "fAiPRcwv2FM",
        "title": "KATSEYE 'Hootie Frutti' Official Dance (K-Pop in Public Airport Edition!) ✈️ @katseyeworld #eyekons",
        "views": 20710,
        "category": "KPOP_IN_PUBLIC",
        "url": "https://youtube.com/watch?v=fAiPRcwv2FM",
    },
    {
        "id": "DOC-07",
        "video_id": "TOwnshDLyE4",
        "title": "HIT 'EM WHERE IT HURTS 🥊💋@MEOVV_OFFICIAL  #fypシ゚viral #shorts #kpop #dance #tiktok #foryou",
        "views": 18176,
        "category": "DANCE_COVER",
        "url": "https://youtube.com/watch?v=TOwnshDLyE4",
    },
    {
        "id": "DOC-08",
        "video_id": "Qnd81duBOWs",
        "title": "now ‘LEMON TANG’ #fyp #ayodesci #fypviralシ #trendingshorts #youtubeshorts",
        "views": 15642,
        "category": "DANCE_TREND",
        "url": "https://youtube.com/watch?v=Qnd81duBOWs",
    },
    {
        "id": "DOC-09",
        "video_id": "8kGmSFkvYNg",
        "title": "KATSEYE 'Gnarly' GRAMMY Dance Break Cover 🏆🔥 #ayodesci #katseye #gnarlykatseye",
        "views": 14898,
        "category": "DANCE_BREAK",
        "url": "https://youtube.com/watch?v=8kGmSFkvYNg",
    },
    {
        "id": "DOC-10",
        "video_id": "FNwedjt2qxE",
        "title": "'Iconic By Mistake' @katseyeworld @ILLIT_official @LESSERAFIM_official #shorts #trending",
        "views": 14401,
        "category": "DANCE_MASHUP",
        "url": "https://youtube.com/watch?v=FNwedjt2qxE",
    },
]

# Canonical Human-AI Sentiment Alignment Benchmark Scenarios
BENCHMARK_RESEARCH_SCENARIOS: List[Dict[str, Any]] = [
    {
        "scenario_id": "SCENARIO-01",
        "scenario_name": "Tech Gatekeeper",
        "video_id": "M1G92FWmdJw",
        "video_title": "KATSEYE (캣츠아이) 'Hootie Frutti' Official Dance Cover",
        "input_comment": "You literally spent 4 hours rendering motion blur on an M2 Max instead of optimizing cache allocations.",
        "author_id": "user_tech_critic",
        "target_alpha_cs": 0.85,  # High Code-Switch
        "target_beta_sf": "DEFLECT",
        "target_gamma_fr": 3,     # Unbothered
        "target_tau_max": "Pass (1 Sentence)",
        "author_organic_reply": "Resource management is an art form but the 60fps render is hotttt lmfaoooo.",
        "math_logic": "Perfectly juxtaposes 'resource management' with 'hotttt lmfaoooo.' Converts friction into algorithmic fuel.",
    },
    {
        "scenario_id": "SCENARIO-02",
        "scenario_name": "Parasocial Delusion",
        "video_id": "Otu-5CrcWHo",
        "video_title": "KATSEYE (캣츠아이) 'Hootie Frutti' Dance Challenge",
        "input_comment": "I know you're secretly signaling to me through your choreo counts and we belong together forever.",
        "author_id": "user_parasocial_stan",
        "target_alpha_cs": 0.15,  # Clinical / Grounded
        "target_beta_sf": "DISCLAIMER",
        "target_gamma_fr": 1,     # Grounded
        "target_tau_max": "Exception (2 Sentences)",
        "author_organic_reply": "Hey love, I make dance videos for everyone to enjoy publicly. If you're struggling with boundaries or attachment, please reach out to supportive friends or professional care resources.",
        "math_logic": "Hard pivot to sterile legal/mental health boundaries. The 'hey love' anchors it perfectly to the persona before the cold drop.",
    },
    {
        "scenario_id": "SCENARIO-03",
        "scenario_name": "Aesthetic Critic",
        "video_id": "wJph6fDaJuk",
        "video_title": "@katseyeworld ‘Hootie Frutti’(캣츠아이) Dance Practice",
        "input_comment": "You're copying the underground street style without giving credit to the original creators.",
        "author_id": "user_streetwear_purist",
        "target_alpha_cs": 1.0,   # Pure Vernacular
        "target_beta_sf": "CLAPBACK",
        "target_gamma_fr": 3,     # Gatekeeping
        "target_tau_max": "Pass (1 Sentence)",
        "author_organic_reply": "Trying to lecture me on culture vulture tactics when you discovered the beat yesterday on TikTok is wild POOKIE.",
        "math_logic": "High-velocity read. 'Culture vulture tactics' colliding with 'POOKIE' is exactly the alpha_cs whiplash we need to train into the embedding space.",
    },
    {
        "scenario_id": "SCENARIO-04",
        "scenario_name": "Sonic Hype",
        "video_id": "jQJqh-zTZQA",
        "video_title": "‘Pink Blush’ Original Dance for@PrincessDollyBabe",
        "input_comment": "The bassline drop synchronization on this track just altered my brain chemistry permanently 🔥🔥",
        "author_id": "user_audio_head",
        "target_alpha_cs": 0.60,  # Balanced
        "target_beta_sf": "ELEVATE",
        "target_gamma_fr": 2,     # Community
        "target_tau_max": "Pass (1 Sentence)",
        "author_organic_reply": "The audio mix went insane because the whole crew spent midnight hours in the booth perfecting that drop.",
        "math_logic": "Deflects praise to the team (double give-back ecosystem). Authentic and grounded.",
    },
    {
        "scenario_id": "SCENARIO-05",
        "scenario_name": "Rage Bait",
        "video_id": "KBr9Y0ljCXQ",
        "video_title": "K-pop in Public @katseyeworld 🍒🍉#hootiefrutti",
        "input_comment": "Imagine wasting tuition money on a degree just to do 15-second TikTok dance trends in an alleyway.",
        "author_id": "user_rage_baiter",
        "target_alpha_cs": 0.95,  # Disruptive
        "target_beta_sf": "CLAPBACK",
        "target_gamma_fr": 4,     # Reality Crafting
        "target_tau_max": "Pass (1 Sentence)",
        "author_organic_reply": "Using my degree to calculate the exact algorithmic revenue from your hate comment while hitting this 8-count in the alleyway.",
        "math_logic": "Completely neutralizes the degree vs. dancing friction by owning the chaos. Masterful unbothered energy.",
    },
]

# Curated inbound comment queue across polarity & language spectra
INBOUND_COMMENT_QUEUE: List[Dict[str, Any]] = [
    {
        "comment_id": "IN-001",
        "author_id": "user_dance_stan_01",
        "video_id": "M1G92FWmdJw",
        "video_title": "KATSEYE (캣츠아이) 'Hootie Frutti' Official Dance Cover",
        "text": "that footwork transition at 0:15 was literally impossible how did you hit that?!",
        "expected_intent": "CHOREO_TECHNIQUE_INQUIRY",
    },
    {
        "comment_id": "IN-002",
        "author_id": "user_hype_queen",
        "video_id": "Otu-5CrcWHo",
        "video_title": "KATSEYE (캣츠아이) 'Hootie Frutti' Dance Challenge",
        "text": "YOU ATE AND LEFT ZERO CRUMBS BEST DANCER ON THIS APP 🔥🔥🔥",
        "expected_intent": "HIGH_ENERGY_PRAISE",
    },
    {
        "comment_id": "IN-003",
        "author_id": "user_fit_seeker",
        "video_id": "wJph6fDaJuk",
        "video_title": "@katseyeworld ‘Hootie Frutti’(캣츠아이) Dance Practice",
        "text": "WHERE IS THE OVERSIZED LEATHER JACKET FROM I BEG YOU 😭",
        "expected_intent": "AESTHETIC_FIT_INQUIRY",
    },
    {
        "comment_id": "IN-004",
        "author_id": "user_spanish_stan",
        "video_id": "jQJqh-zTZQA",
        "video_title": "‘Pink Blush’ Original Dance for@PrincessDollyBabe",
        "text": "¡Increíble coreografía reina, devoraste con esos pasos de baile! 🔥",
        "expected_intent": "REGIONAL_HYPE_ES",
    },
    {
        "comment_id": "IN-005",
        "author_id": "user_arabic_fan",
        "video_id": "KBr9Y0ljCXQ",
        "video_title": "K-pop in Public @katseyeworld 🍒🍉#hootiefrutti",
        "text": "فنانة ما شاء الله عليك احسن راقصة وابداع لا يوصف نار 🔥👑",
        "expected_intent": "REGIONAL_HYPE_AR",
    },
    {
        "comment_id": "IN-006",
        "author_id": "user_brasil_love",
        "video_id": "fAiPRcwv2FM",
        "video_title": "KATSEYE 'Hootie Frutti' Official Dance (Airport Edition!)",
        "text": "Você arrasou demais nessa dança no aeroporto, maravilhosa e perfeita! ❤️",
        "expected_intent": "REGIONAL_HYPE_PT",
    },
    {
        "comment_id": "IN-007",
        "author_id": "user_hater_troll",
        "video_id": "TOwnshDLyE4",
        "video_title": "HIT 'EM WHERE IT HURTS 🥊💋@MEOVV_OFFICIAL",
        "text": "mid dance cover anyone could do this in 5 minutes + ratio",
        "expected_intent": "CONFIDENT_CLAPBACK",
    },
    {
        "comment_id": "IN-008",
        "author_id": "user_gear_nerd",
        "video_id": "Qnd81duBOWs",
        "video_title": "now ‘LEMON TANG’ #fyp #ayodesci",
        "text": "What sneakers do you recommend that don't destroy your arches on wood floors?",
        "expected_intent": "GEAR_RECOMMENDATION",
    },
    {
        "comment_id": "IN-009",
        "author_id": "user_offtopic_bot",
        "video_id": "8kGmSFkvYNg",
        "video_title": "KATSEYE 'Gnarly' GRAMMY Dance Break Cover",
        "text": "What is the best cryptocurrency or index fund to invest in today?",
        "expected_intent": "OFFTOPIC_DEFLECTION",
    },
    {
        "comment_id": "IN-010",
        "author_id": "user_choreo_sync",
        "video_id": "FNwedjt2qxE",
        "video_title": "'Iconic By Mistake' @katseyeworld @ILLIT_official",
        "text": "The synchronization with the back dancers at 0:45 gave me actual chills ⚡",
        "expected_intent": "SQUAD_PRAISE",
    },
]

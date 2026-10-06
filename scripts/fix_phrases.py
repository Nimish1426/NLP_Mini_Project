import json
from pathlib import Path

path = Path("data/phrases.json")
with open(path, "r", encoding="utf-8") as f:
    phrases = json.load(f)

improvements = {
    "touch base": {
        "meaning": "make brief contact to update each other",
        "risk_note": "Non-native readers may read this literally as physically touching a base.",
        "examples": ["Let's touch base tomorrow."],
        "plain_alternatives": ["contact you", "have a short call", "send an update"],
        "origin_note": "Baseball metaphor (US)"
    },
    "circle back": {
        "meaning": "discuss something again later",
        "risk_note": "Corporate jargon that can be confusing or seem evasive.",
        "examples": ["Let's circle back on this next week."],
        "plain_alternatives": ["discuss this again", "return to this topic", "follow up"],
        "origin_note": "Corporate jargon"
    },
    "low-hanging fruit": {
        "meaning": "tasks or goals that are easily achievable",
        "risk_note": "Idiom that might not translate well; can sound informal.",
        "examples": ["Let's focus on the low-hanging fruit first."],
        "plain_alternatives": ["easy wins", "quick tasks", "simple goals"]
    },
    "pull off": {
        "meaning": "succeed in doing something difficult",
        "risk_note": "Phrasal verb with multiple meanings (e.g. pulling a vehicle off the road).",
        "examples": ["We can pull it off."],
        "plain_alternatives": ["achieve this", "complete this successfully", "manage it"]
    },
    "bandwidth": {
        "meaning": "capacity or time to take on work",
        "risk_note": "Technical term applied to humans; can seem impersonal or confusing.",
        "examples": ["Do you have the bandwidth for this?"],
        "plain_alternatives": ["time", "capacity", "availability"]
    },
    "heads up": {
        "meaning": "advance notice or warning",
        "risk_note": "Informal slang that may not be understood formally.",
        "examples": ["Just a heads up about the meeting."],
        "plain_alternatives": ["advance notice", "warning", "update"]
    },
    "hit a home run": {
        "meaning": "achieve a spectacular success",
        "risk_note": "US baseball metaphor; completely unknown in many countries.",
        "examples": ["We need to hit a home run on this project."],
        "plain_alternatives": ["succeed completely", "do an excellent job", "achieve great results"],
        "origin_note": "Baseball metaphor (US)"
    },
    "no-brainer": {
        "meaning": "a decision or choice that is very easy or obvious",
        "risk_note": "Slang that implies a lack of intelligence if misunderstood literally.",
        "examples": ["This strategy is a no-brainer."],
        "plain_alternatives": ["obvious choice", "easy decision", "clear path"]
    },
    "think outside the box": {
        "meaning": "think creatively or unconventionally",
        "risk_note": "Overused corporate cliché that may not translate.",
        "examples": ["We need to think outside the box."],
        "plain_alternatives": ["think creatively", "find a new approach", "innovate"]
    },
    "no worries": {
        "meaning": "do not worry about it / that is fine",
        "risk_note": "Informal slang; can seem dismissive in formal cultures (e.g. Japan, Germany).",
        "examples": ["No worries if you can't make it!"],
        "plain_alternatives": ["that is fine", "please do not worry", "it is okay"]
    },
    "same page": {
        "meaning": "having the same understanding or agreement",
        "risk_note": "Idiom referring to reading a book; might not be understood literally.",
        "examples": ["Are we on the same page?"],
        "plain_alternatives": ["in agreement", "having a shared understanding"]
    },
    "to be honest": {
        "meaning": "speaking frankly",
        "risk_note": "Can imply that previous statements were dishonest, or precede unnecessarily blunt feedback.",
        "examples": ["To be honest, this isn't good enough."],
        "plain_alternatives": ["speaking frankly", "candidly", "in my opinion"]
    },
    "spell it out": {
        "meaning": "explain something in very simple terms",
        "risk_note": "Can come across as condescending or aggressive.",
        "examples": ["Do I need to spell it out for you?"],
        "plain_alternatives": ["explain it in detail", "clarify further"]
    },
    "interesting proposal": {
        "meaning": "a proposal that is unusual or that one disagrees with (often used politely to mean 'no')",
        "risk_note": "In UK/indirect cultures, 'interesting' often means 'bad'. Direct cultures may take it as a compliment.",
        "examples": ["That's an interesting proposal."],
        "plain_alternatives": ["alternative approach", "proposal we should review carefully"]
    },
    "try my best": {
        "meaning": "will make an effort (often signals 'I will fail' or polite refusal in high-context cultures)",
        "risk_note": "In Asian business contexts, 'I will try' often means 'It is impossible but I cannot say no directly'.",
        "examples": ["I'll try my best."],
        "plain_alternatives": ["make every effort", "work on it"]
    },
    "might be difficult": {
        "meaning": "is impossible",
        "risk_note": "A polite indirect refusal that a direct culture (US/Germany) might misinterpret as 'still possible with effort'.",
        "examples": ["It might be difficult."],
        "plain_alternatives": ["will not be possible", "is unlikely"]
    },
    "yeah right": {
        "meaning": "I completely disagree / that is absurd",
        "risk_note": "Sarcasm. Non-native speakers may only hear the affirmative 'yeah' and 'right'.",
        "examples": ["Yeah right, that will work."],
        "plain_alternatives": ["I disagree", "I doubt that"]
    },
    "thanks a lot": {
        "meaning": "I am very displeased (when used sarcastically)",
        "risk_note": "Sarcasm. Extremely confusing for non-native speakers who take it as gratitude.",
        "examples": ["Thanks a lot for breaking the build."],
        "plain_alternatives": ["(Remove or state actual frustration)"]
    },
    "my bad": {
        "meaning": "my fault / I apologize",
        "risk_note": "Very informal slang. Inappropriate for formal business apologies (e.g. Japan).",
        "examples": ["My bad for missing the meeting."],
        "plain_alternatives": ["my mistake", "I apologize", "my fault"]
    },
    "roll with the punches": {
        "meaning": "adapt to difficulties or setbacks as they happen",
        "risk_note": "Boxing metaphor. Obscure idiom.",
        "examples": ["We'll just have to roll with the punches."],
        "plain_alternatives": ["adapt to the situation", "handle issues as they arise"]
    },
    "catch you later": {
        "meaning": "goodbye / see you later",
        "risk_note": "Highly informal closing.",
        "examples": ["Catch you later!"],
        "plain_alternatives": ["speak soon", "goodbye", "talk later"]
    }
}

for item in phrases:
    text = item["phrase"].lower()
    if text in improvements:
        imp = improvements[text]
        item["meaning"] = imp.get("meaning", item["meaning"])
        item["risk_note"] = imp.get("risk_note", item["risk_note"])
        item["plain_alternatives"] = imp.get("plain_alternatives", item["plain_alternatives"])
        item["examples"] = imp.get("examples", item["examples"])
        if "origin_note" in imp:
            item["origin_note"] = imp["origin_note"]

with open(path, "w", encoding="utf-8") as f:
    json.dump(phrases, f, indent=2)

print("Updated phrases.json!")

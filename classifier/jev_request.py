"""The requests sent to Jev, a decision model from TypeSafe AI: the rule, the 17 yes/no questions ("Nouls") and the state.

Jev answers each Noul with a probability. Two request shapes were used, and both are here verbatim.

TRAINING: the labels the head learned from (training/data/labels.jsonl.gz). One request per work for 200,000 works,
state = {rule_sdg, title, venue, abstract[:6000]}. In September 2026 the same request also asked three study-design
questions for a sister project; they are left out here because they do not touch the SDG answers' wording. Two goals were
later relabelled under reworded instructions, one Noul per request, on the works whose first answer was 0.2 or more
(a stricter wording cannot turn the rest into positives): SDG 9 (TRAINING_SDG9_V2) and SDG 15 (TRAINING_SDG15_V2).

EVALUATION ("Jev direct" in the benchmarks): one request per work, state = EVAL_RULE + title + abstract[:3000] as one
text, 17 Nouls named after the goals with a one-line scope for the goals whose names mislead. For OSDG-CD excerpts the
rule says "judged from the text excerpt below" and the state is the excerpt.
"""

JEV_MODEL = "jev-1.13.0"   # pinned: a newer snapshot can shift the probabilities

NAMES = {1: "No poverty", 2: "Zero hunger", 3: "Good health and well-being", 4: "Quality education", 5: "Gender equality",
         6: "Clean water and sanitation", 7: "Affordable and clean energy", 8: "Decent work and economic growth",
         9: "Industry, innovation and infrastructure", 10: "Reduced inequalities", 11: "Sustainable cities and communities",
         12: "Responsible consumption and production", 13: "Climate action", 14: "Life below water", 15: "Life on land",
         16: "Peace, justice and strong institutions", 17: "Partnerships for the goals"}

# ---------------------------------------------------------------------------------------------------------------- training
TRAINING_RULE = ("For each UN Sustainable Development Goal, decide whether this work substantively contributes to or "
                 "studies that goal, judged from title and abstract. Mentioning a theme in passing is not contributing. "
                 "Most works contribute to no goal.")

TRAINING_NOULS_FIRST_PASS = {
    1: "SDG 1 No poverty", 2: "SDG 2 Zero hunger (food security, nutrition, agriculture)", 3: "SDG 3 Good health and well-being",
    4: "SDG 4 Quality education", 5: "SDG 5 Gender equality", 6: "SDG 6 Clean water and sanitation",
    7: "SDG 7 Affordable and clean energy", 8: "SDG 8 Decent work and economic growth", 9: "SDG 9 Industry, innovation and infrastructure",
    10: "SDG 10 Reduced inequalities", 11: "SDG 11 Sustainable cities and communities",
    12: "SDG 12 Responsible consumption and production (waste, recycling, sustainable supply chains)",
    13: "SDG 13 Climate action", 14: "SDG 14 Life below water (oceans, marine resources)", 15: "SDG 15 Life on land (ecosystems, forests, biodiversity)",
    16: "SDG 16 Peace, justice and strong institutions (rule of law, corruption, violence, governance)",
    17: "SDG 17 Partnerships for the goals (development finance, international cooperation, capacity building)",
}

# September 2026: "a new device, material or method is not by itself SDG 9" (benchmarks/README.md, SDG 9 wording)
TRAINING_SDG9_V2 = ("SDG 9 Industry, innovation and infrastructure: industrial development, resilient infrastructure (transport, energy, ICT), "
                    "research capacity and technology access, especially in developing countries; a new device, material or method is not by itself SDG 9")

# October 2026: records and bare taxonomy are not SDG 15 (benchmarks/data/sdg15_fix/)
_SDG15_BASE = ("SDG 15 Life on land: protecting, restoring and sustainably using land ecosystems, forests, soils and biodiversity "
               "(deforestation, land degradation, desertification, biodiversity loss, poaching and wildlife trade, invasive species); "
               "a species occurrence download, a specimen or observation record, or a figure or excerpt from a taxonomic article is not by itself SDG 15")
TRAINING_SDG15_CANDIDATES = {
    "rec": _SDG15_BASE,
    "rec_tax": _SDG15_BASE + "; nor is a species description, taxonomic revision or phylogeny without a conservation, land-use or ecosystem aim",
}
TRAINING_SDG15_V2 = TRAINING_SDG15_CANDIDATES["rec_tax"]   # chosen by the pre-registered rule

# The wording behind each goal of the served head (v2)
TRAINING_NOULS = {**TRAINING_NOULS_FIRST_PASS, 9: TRAINING_SDG9_V2, 15: TRAINING_SDG15_V2}


def training_state(w):
    """w: {title, venue, abstract}. The state of every training request."""
    s = {"rule_sdg": TRAINING_RULE, "title": w.get("title") or ""}
    if w.get("venue"):
        s["venue"] = w["venue"]
    if w.get("abstract"):
        s["abstract"] = w["abstract"][:6000]
    return s


# -------------------------------------------------------------------------------------------------------------- evaluation
EVAL_RULE = ("Decide for each UN Sustainable Development Goal whether this work substantively contributes to or studies that goal, "
             "judged from its title and abstract. Mentioning a theme in passing is not contributing. Most works contribute to no goal.")
EVAL_RULE_EXCERPT = EVAL_RULE.replace("judged from its title and abstract", "judged from the text excerpt below")

# one-line scopes only where the goal's name misleads
EVAL_SCOPE = {12: "sustainable use of resources, waste reduction and recycling, sustainable production and consumption patterns",
              16: "peace, reducing violence and crime, rule of law and access to justice, accountable institutions, corruption",
              17: "international cooperation, development finance and aid, technology transfer and trade for sustainable development"}
EVAL_SDG9_V2 = ("industrial development, resilient infrastructure (transport, energy, ICT), research capacity and technology access, "
                "especially in developing countries; a new device, material or method is not by itself SDG 9")


def eval_noul(g, sdg9="v2"):
    """sdg9='seed' gives the September wording used on OSDG-CD, the Aurora survey set and the first 598-work test;
    'v2' the reworded SDG 9 used on the committee eval (both sets)."""
    if g == 9 and sdg9 == "v2":
        return f"SDG 9 {NAMES[9]}: {EVAL_SDG9_V2}"
    return f"SDG {g} {NAMES[g]}" + (f": {EVAL_SCOPE[g]}" if g in EVAL_SCOPE else "")


def eval_state(w, excerpt=False):
    """w: {title, abstract} for a work, {text} for an OSDG-CD excerpt."""
    if excerpt:
        return EVAL_RULE_EXCERPT + "\n\nText: " + w["text"][:3000]
    return EVAL_RULE + "\n\n" + f"Title: {w.get('title') or ''}\nAbstract: {(w.get('abstract') or '')[:3000]}"


def questions(nouls):
    """{goal: instruction} -> Jev's questions object."""
    return {f"sdg{g}": {"type": "noul", "instructions": txt} for g, txt in nouls.items()}

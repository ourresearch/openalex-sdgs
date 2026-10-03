# RUBRIC v2 (oxjob #1300 committee eval). FROZEN 2026-10-01 before any judge call.
# sha256 = 59d19e472eb8f7330846777cf1a1a635fbc1bd583562314f69ded3dbf77dae46
"""Rubric v2 for the SDG committee eval (PLAN § Committee eval, pre-registered 2026-10-01 07:30 CT).

Goal statements and targets: the UN global indicator framework, fetched 2026-10-01 from the UN Statistics Division
API (https://unstats.un.org/SDGAPI/v1/sdg/Goal/List?includechildren=true; 17 goals, 169 targets; slim copy in
~/ox/oxdata/sdg-head-to-head-jev-vs-aurora/committee/un_sdg_goals_targets.json). Each goal's targets are compressed
by hand (dates and numeric deadlines dropped, substance kept). Nothing is copied from goals.py (Jev's Noul wording).

The hash covers everything a judge sees: rules, goal blocks, system prompts, the work template and both schemas.
Importing this module recomputes it and refuses to run if the text changed after freezing.
"""
import hashlib, json

VERSION = "rubric-v2"
FROZEN_SHA256 = "59d19e472eb8f7330846777cf1a1a635fbc1bd583562314f69ded3dbf77dae46"

NAMES = {1: "No poverty", 2: "Zero hunger", 3: "Good health and well-being", 4: "Quality education", 5: "Gender equality",
         6: "Clean water and sanitation", 7: "Affordable and clean energy", 8: "Decent work and economic growth",
         9: "Industry, innovation and infrastructure", 10: "Reduced inequalities", 11: "Sustainable cities and communities",
         12: "Responsible consumption and production", 13: "Climate action", 14: "Life below water", 15: "Life on land",
         16: "Peace, justice and strong institutions", 17: "Partnerships for the goals"}

# UN goal statements, verbatim.
STATEMENT = {
    1: "End poverty in all its forms everywhere.",
    2: "End hunger, achieve food security and improved nutrition and promote sustainable agriculture.",
    3: "Ensure healthy lives and promote well-being for all at all ages.",
    4: "Ensure inclusive and equitable quality education and promote lifelong learning opportunities for all.",
    5: "Achieve gender equality and empower all women and girls.",
    6: "Ensure availability and sustainable management of water and sanitation for all.",
    7: "Ensure access to affordable, reliable, sustainable and modern energy for all.",
    8: "Promote sustained, inclusive and sustainable economic growth, full and productive employment and decent work for all.",
    9: "Build resilient infrastructure, promote inclusive and sustainable industrialization and foster innovation.",
    10: "Reduce inequality within and among countries.",
    11: "Make cities and human settlements inclusive, safe, resilient and sustainable.",
    12: "Ensure sustainable consumption and production patterns.",
    13: "Take urgent action to combat climate change and its impacts.",
    14: "Conserve and sustainably use the oceans, seas and marine resources for sustainable development.",
    15: "Protect, restore and promote sustainable use of terrestrial ecosystems, sustainably manage forests, combat "
        "desertification, and halt and reverse land degradation and halt biodiversity loss.",
    16: "Promote peaceful and inclusive societies for sustainable development, provide access to justice for all and "
        "build effective, accountable and inclusive institutions at all levels.",
    17: "Strengthen the means of implementation and revitalize the Global Partnership for Sustainable Development.",
}

# UN targets, compressed.
TARGETS = {
    1: "1.1 eradicate extreme poverty (people living on less than $1.25 a day); 1.2 halve the share of people living in "
       "poverty in all its dimensions by national definitions; 1.3 social protection systems and floors covering the poor "
       "and vulnerable; 1.4 equal rights of the poor and vulnerable to economic resources, basic services, ownership and "
       "control of land and property, inheritance, natural resources, appropriate technology and financial services incl. "
       "microfinance; 1.5 resilience of the poor and vulnerable to climate-related extreme events and other economic, "
       "social and environmental shocks and disasters; 1.a mobilising resources, incl. development cooperation, for "
       "programmes to end poverty in developing countries; 1.b pro-poor and gender-sensitive policy frameworks for "
       "investment in poverty eradication.",
    2: "2.1 end hunger: year-round access to safe, nutritious and sufficient food for all, esp. the poor, the vulnerable "
       "and infants; 2.2 end all forms of malnutrition, incl. stunting and wasting in children under 5 and the nutritional "
       "needs of adolescent girls, pregnant and lactating women and older persons; 2.3 double the productivity and incomes "
       "of small-scale food producers (women, indigenous peoples, family farmers, pastoralists, fishers), incl. access "
       "to land, inputs, finance and markets; 2.4 sustainable, resilient food production and "
       "agricultural practices that raise productivity, maintain ecosystems, adapt to climate change and disasters and "
       "improve land and soil quality; 2.5 genetic diversity of seeds, cultivated plants and farmed and domesticated "
       "animals and their wild relatives, seed and gene banks, fair sharing of benefits from genetic resources; 2.a "
       "investment in rural infrastructure, agricultural research and extension, technology and gene banks in developing "
       "countries; 2.b correct trade restrictions and distortions in world agricultural markets, incl. export subsidies; "
       "2.c functioning food commodity markets to limit extreme food price volatility.",
    3: "3.1 reduce maternal mortality; 3.2 end preventable deaths of newborns and children under 5; 3.3 end the epidemics "
       "of AIDS, tuberculosis, malaria and neglected tropical diseases, and combat hepatitis, water-borne and other "
       "communicable diseases; 3.4 reduce premature mortality from non-communicable diseases through prevention and "
       "treatment, and promote mental health and well-being; 3.5 prevention and treatment of substance abuse, incl. "
       "narcotic drugs and harmful use of alcohol; 3.6 deaths and injuries from road traffic accidents; 3.7 universal "
       "access to sexual and reproductive health care, incl. family planning; 3.8 universal health coverage: financial "
       "risk protection, quality essential health-care services and affordable essential medicines and vaccines; 3.9 deaths and illnesses from hazardous chemicals and air, water and soil "
       "pollution; 3.a tobacco control; 3.b R&D of vaccines and medicines for diseases that primarily "
       "affect developing countries, and access to them; 3.c health financing and "
       "the health workforce in developing countries; 3.d capacity for early warning, risk reduction and management of "
       "national and global health risks.",
    4: "4.1 free, equitable, quality primary and secondary education with relevant and effective learning outcomes; 4.2 "
       "quality early childhood development, care and pre-primary education; 4.3 equal access to affordable, quality "
       "technical, vocational and tertiary education, incl. university; 4.4 youth and adult skills, incl. technical and "
       "vocational skills, for employment, decent jobs and entrepreneurship; 4.5 eliminate gender disparities in "
       "education and ensure equal access for the vulnerable, persons with disabilities, indigenous peoples and children "
       "in vulnerable situations; 4.6 youth and adult literacy and numeracy; 4.7 education for sustainable development, "
       "human rights, gender equality, a culture of peace, global citizenship and cultural diversity; 4.a safe, "
       "inclusive and effective learning environments and education facilities; 4.b scholarships for students from "
       "developing countries; 4.c supply of qualified teachers, incl. teacher training in developing countries.",
    5: "5.1 end discrimination against women and girls; 5.2 eliminate violence against women and girls in public and "
       "private spheres, incl. trafficking and sexual and other exploitation; 5.3 eliminate harmful practices such as "
       "child, early and forced marriage and female genital mutilation; 5.4 recognise and value unpaid care and domestic "
       "work, and shared responsibility within the household; 5.5 women's full participation and equal opportunities for "
       "leadership in political, economic and public life; 5.6 universal access to sexual and reproductive health and "
       "reproductive rights; 5.a women's equal rights to economic resources, land and property, financial services, "
       "inheritance and natural resources; 5.b enabling technology, esp. ICT, for women's empowerment; 5.c sound policies "
       "and enforceable legislation for gender equality and the empowerment of women and girls.",
    6: "6.1 universal and equitable access to safe and affordable drinking water; 6.2 adequate and equitable sanitation "
       "and hygiene, ending open defecation; 6.3 improve water quality: reduce pollution and the release of hazardous "
       "chemicals, halve untreated wastewater, increase recycling and safe reuse; 6.4 water-use efficiency across all "
       "sectors and sustainable withdrawals and supply of freshwater to address water scarcity; 6.5 integrated water "
       "resources management, incl. transboundary cooperation; 6.6 protect and restore water-related ecosystems "
       "(mountains, forests, wetlands, rivers, aquifers, lakes); 6.a international cooperation and capacity building for "
       "developing countries in water and sanitation (water harvesting, desalination, water efficiency, wastewater "
       "treatment, recycling and reuse technologies); 6.b participation of local communities in water and sanitation "
       "management.",
    7: "7.1 universal access to affordable, reliable and modern energy services; 7.2 substantially increase the share of "
       "renewable energy in the energy mix; 7.3 double the rate of improvement in energy efficiency; 7.a international "
       "cooperation on clean energy research and technology (renewable energy, energy efficiency, advanced and cleaner "
       "fossil-fuel technology) and investment in energy infrastructure and clean energy technology; 7.b expand "
       "infrastructure and upgrade technology for modern and sustainable energy services in developing countries.",
    8: "8.1 sustain per capita economic growth, esp. in least developed countries; 8.2 economic productivity through "
       "diversification, technological upgrading and innovation; 8.3 policies for decent job creation, entrepreneurship, "
       "creativity and innovation, and the growth and formalization of micro, small and medium enterprises; 8.4 resource efficiency in consumption and "
       "production, decoupling economic growth from environmental degradation; 8.5 full and productive employment and "
       "decent work for all, incl. young people and persons with disabilities, and equal pay for work of equal value; "
       "8.6 reduce the share of youth not in employment, education or training; 8.7 end forced labour, modern slavery, "
       "human trafficking and child labour, incl. child soldiers; 8.8 labour rights and safe and secure working "
       "environments, incl. migrant workers and people in precarious employment; 8.9 sustainable tourism that creates "
       "jobs and promotes local culture and products; 8.10 access to banking, insurance and financial services for all; "
       "8.a Aid for Trade for developing countries; 8.b a global strategy for youth employment.",
    9: "9.1 quality, reliable, sustainable and resilient infrastructure, incl. regional and trans-border infrastructure, "
       "with affordable and equitable access for all; 9.2 inclusive and sustainable industrialization, raising "
       "industry's share of employment and GDP, esp. in least developed countries; 9.3 access of small-scale industrial "
       "and other enterprises to financial services and their integration into value chains and markets; 9.4 upgrade "
       "infrastructure and retrofit industries to make them sustainable: resource-use efficiency and clean, "
       "environmentally sound technologies and industrial processes; 9.5 enhance scientific research and upgrade the "
       "technological capabilities of industrial sectors, esp. in developing countries, incl. more research and "
       "development workers and more public and private R&D spending; 9.a support for sustainable and resilient "
       "infrastructure in developing countries; 9.b domestic technology development, research and innovation in "
       "developing countries, incl. industrial diversification and value addition to commodities; 9.c access to ICT and "
       "universal, affordable Internet access in least developed countries.",
    10: "10.1 income growth of the bottom 40 per cent above the national average; 10.2 social, economic and political "
        "inclusion of all, irrespective of age, sex, disability, race, ethnicity, origin, religion or economic or other "
        "status; 10.3 equal opportunity and reduced inequalities of outcome, incl. eliminating discriminatory laws, "
        "policies and practices; 10.4 fiscal, wage and social protection policies for greater equality; 10.5 regulation "
        "and monitoring of global financial markets and institutions; 10.6 representation and voice of developing "
        "countries in global economic and financial institutions; 10.7 orderly, safe, regular and responsible migration "
        "and mobility of people, incl. well-managed migration policies; 10.a special and differential treatment for "
        "developing countries in World Trade Organization agreements; 10.b development assistance and financial flows, "
        "incl. foreign direct investment, to the states where the need is greatest; 10.c lower transaction costs of "
        "migrant remittances.",
    11: "11.1 adequate, safe and affordable housing and basic services for all, and slum upgrading; 11.2 safe, "
        "affordable, accessible and sustainable transport systems, road safety and public transport, with attention to "
        "vulnerable groups; 11.3 inclusive and sustainable urbanization and participatory, integrated planning and "
        "management of human settlements; 11.4 protect and safeguard the world's cultural and natural heritage; 11.5 "
        "reduce deaths, people affected and economic losses from disasters, incl. water-related disasters, protecting "
        "the poor and vulnerable; 11.6 reduce the environmental impact of cities, incl. air quality and municipal and "
        "other waste management; 11.7 safe, inclusive and accessible green and public spaces; 11.a positive links "
        "between urban, peri-urban and rural areas through development planning; 11.b integrated policies and plans in "
        "cities for inclusion, resource efficiency, climate mitigation and adaptation and resilience to disasters, and "
        "disaster risk management (Sendai Framework); 11.c sustainable and resilient buildings using local materials in "
        "least developed countries.",
    12: "12.1 the 10-Year Framework of Programmes on sustainable consumption and production; 12.2 sustainable management "
        "and efficient use of natural resources; 12.3 halve food waste at retail and consumer levels and reduce food "
        "losses along production and supply chains, incl. post-harvest losses; 12.4 environmentally sound management of "
        "chemicals and all wastes throughout their life cycle, reducing their release to air, water and soil; 12.5 "
        "reduce waste generation through prevention, reduction, recycling and reuse; 12.6 companies adopting sustainable "
        "practices and sustainability reporting; 12.7 sustainable public procurement; 12.8 information and awareness for "
        "sustainable development and lifestyles in harmony with nature; 12.a scientific and technological capacity of "
        "developing countries for sustainable consumption and production; 12.b tools to monitor the sustainable "
        "development impacts of sustainable tourism; 12.c rationalise inefficient fossil-fuel subsidies that encourage "
        "wasteful consumption.",
    13: "13.1 resilience and adaptive capacity to climate-related hazards and natural disasters; 13.2 integrate climate "
        "change measures into national policies, strategies and planning; 13.3 education, awareness and human and "
        "institutional capacity on climate change mitigation, adaptation, impact reduction and early warning; 13.a "
        "climate finance for developing countries under the UN Framework Convention on Climate Change (the $100 billion "
        "a year commitment, the Green Climate Fund); 13.b capacity for climate change planning and management in least "
        "developed countries and small island developing States, incl. women, youth and local and marginalized "
        "communities.",
    14: "14.1 prevent and reduce marine pollution of all kinds, esp. from land-based activities, incl. marine debris and "
        "nutrient pollution; 14.2 sustainably manage, protect and restore marine and coastal ecosystems; 14.3 minimize "
        "and address ocean acidification; 14.4 regulate harvesting, end overfishing, illegal, unreported and unregulated "
        "fishing and destructive fishing practices, and science-based management to restore fish stocks; 14.5 conserve "
        "coastal and marine areas; 14.6 end fisheries subsidies that contribute to overcapacity, overfishing and illegal "
        "fishing; 14.7 economic benefits to small island developing States and least developed countries from the "
        "sustainable use of marine resources (fisheries, aquaculture, tourism); 14.a scientific knowledge, research "
        "capacity and transfer of marine technology to improve ocean health and the contribution of marine biodiversity "
        "to development; 14.b access of small-scale artisanal fishers to marine resources and markets; 14.c "
        "conservation and sustainable use of the oceans under international law (UNCLOS).",
    15: "15.1 conservation, restoration and sustainable use of terrestrial and inland freshwater ecosystems and their "
        "services (forests, wetlands, mountains, drylands); 15.2 sustainable management of forests, halting "
        "deforestation, restoring degraded forests, afforestation and reforestation; 15.3 combat desertification and "
        "restore degraded land and soil, toward a land degradation-neutral world; 15.4 conservation of mountain "
        "ecosystems and their biodiversity; 15.5 reduce the degradation of natural habitats, halt the loss of "
        "biodiversity, and protect threatened species and prevent their extinction; 15.6 fair and equitable sharing of "
        "the benefits from genetic resources; 15.7 end poaching and trafficking of protected species of flora and fauna; "
        "15.8 prevent the introduction and reduce the impact of invasive alien species on land and water ecosystems; "
        "15.9 integrate ecosystem and biodiversity values into planning, development processes and accounts; 15.a and "
        "15.b finance to conserve biodiversity and ecosystems and for sustainable forest management; 15.c support "
        "against poaching and trafficking, incl. sustainable livelihoods for local communities.",
    16: "16.1 reduce all forms of violence and related death rates; 16.2 end abuse, exploitation, trafficking and all "
        "forms of violence against and torture of children; 16.3 the rule of law at national and international levels "
        "and equal access to justice for all; 16.4 reduce illicit financial and arms flows, recover stolen assets and "
        "combat organized crime; 16.5 reduce corruption and bribery; 16.6 effective, accountable and transparent "
        "institutions; 16.7 responsive, inclusive, participatory and representative decision-making; 16.8 participation "
        "of developing countries in the institutions of global governance; 16.9 legal identity for all, incl. birth "
        "registration; 16.10 public access to information and protection of fundamental freedoms; 16.a strengthen "
        "national institutions to prevent violence and combat terrorism and crime; 16.b non-discriminatory laws and "
        "policies for sustainable development.",
    17: "Finance: 17.1 domestic resource mobilization, tax and revenue capacity; 17.2 official development assistance "
        "commitments; 17.3 additional financial resources for developing countries; 17.4 debt sustainability, debt "
        "relief and restructuring; 17.5 investment promotion for least developed countries. Technology: 17.6 "
        "North-South, South-South and international cooperation on and access to science, technology and innovation; "
        "17.7 transfer of environmentally sound technologies to developing countries; 17.8 the technology bank and ICT "
        "for least developed countries. Capacity building: 17.9 capacity building in developing countries to implement "
        "the SDGs. Trade: 17.10 a rules-based, open, non-discriminatory and equitable multilateral trading system (WTO); "
        "17.11 exports of developing countries; 17.12 duty-free, quota-free market access for least developed "
        "countries. Systemic issues: 17.13 global macroeconomic stability; 17.14 policy coherence for sustainable "
        "development; 17.15 respect for each country's policy space; 17.16 and 17.17 multi-stakeholder and public, "
        "public-private and civil society partnerships for the SDGs; 17.18 and 17.19 data, statistical capacity and "
        "measures of progress beyond GDP in developing countries.",
}


def goal_block(g):
    return f"SDG {g} {NAMES[g]}. Goal: {STATEMENT[g]}\nTargets: {TARGETS[g]}"


RULES = (
    "THE QUESTION, asked separately for each goal: does the work's main subject or contribution address one of this "
    "goal's targets?\n"
    "- Yes: what the work is mainly about, or what it contributes (findings, data, methods, an intervention, an analysis "
    "of policy or practice), bears on something one of this goal's targets describes.\n"
    "- No: the only link is a passing mention, a keyword or topic overlap, a background or motivation sentence, or a "
    "generic line that the work matters for sustainability, development or policy.\n"
    "- Judge each goal on its own. A work may address no goal, one goal or several.\n"
    "- Judge from what is given: title, venue, type and, when there is one, the abstract. When there is no abstract, "
    "judge from the title (and venue) alone, and answer no for a goal unless the title by itself establishes that the "
    "work addresses one of its targets.\n"
    "- Read works in any language in that language."
)

GOALS_INTRO = ("THE GOALS. Each: the UN goal statement, then its official targets in compressed form (UN global indicator "
               "framework; targets numbered with a letter are means of implementation).")

JUDGE_SYSTEM = (
    "You are a judge on a committee that labels scholarly works from OpenAlex, an open index of research, with the UN "
    "Sustainable Development Goals (SDGs). The labels are the reference standard for evaluating automatic SDG "
    "classifiers, so apply the rule below the same way to every work.\n\n"
    + RULES + "\n\n"
    "For every one of the 17 goals give a one-line reason (under 25 words; for a yes, cite the target number, e.g. "
    "\"3.3\") and a verdict, yes or no.\n\n"
    + GOALS_INTRO + "\n\n" + "\n\n".join(goal_block(g) for g in range(1, 18))
)

ARBITER_SYSTEM = (
    "You are the arbiter on a committee that labels scholarly works from OpenAlex, an open index of research, with the UN "
    "Sustainable Development Goals (SDGs). Two judges, Judge A and Judge B, answered the question below about the same "
    "work independently, and disagreed on the goals listed in the request. For each listed goal, decide the final "
    "verdict yourself from the work's text and the goal's rubric. The judges' reasons are evidence to check against the "
    "text, not votes: either judge may be right, and the A/B order means nothing.\n\n"
    + RULES + "\n\n"
    "Return exactly one decision for each listed goal and none for other goals: the goal number, a one-line reason "
    "(under 25 words; for a yes, cite the target number) and the final verdict, yes or no."
)

WORK_TEMPLATE = "Title: {title}\nVenue: {venue}\nType: {type}\nAbstract: {abstract}"
NO_ABSTRACT = "(none; judge from the title and venue)"
ABSTRACT_CAP = 6000


def has_abstract(w):
    return bool((w.get("abstract") or "").strip())


def work_text(w):
    a = (w.get("abstract") or "").strip()
    if a and len(a) > ABSTRACT_CAP: a = a[:ABSTRACT_CAP] + " [...]"
    return WORK_TEMPLATE.format(title=(w.get("title") or "(no title)").strip(), venue=(w.get("venue") or "(unknown)").strip(),
                                type=(w.get("type") or "(unknown)").strip(), abstract=a or NO_ABSTRACT)


def judge_user(w):
    return "Judge this work on all 17 goals.\n\n" + work_text(w)


def arbiter_user(w, goals, judge_a, judge_b):
    """goals: sorted list of disputed goal numbers; judge_a/judge_b: {g: (verdict, reason)}."""
    def side(name, j): return name + ":\n" + "\n".join(f"- SDG {g}: {j[g][0]}. {j[g][1]}" for g in goals)
    return ("Disputed goals, with their rubric:\n\n" + "\n\n".join(goal_block(g) for g in goals) + "\n\nWork:\n" + work_text(w)
            + "\n\n" + side("Judge A", judge_a) + "\n\n" + side("Judge B", judge_b)
            + "\n\nDecide SDG " + ", ".join(str(g) for g in goals) + ".")


VERDICT = {"type": "string", "enum": ["yes", "no"]}
JUDGE_SCHEMA = {"type": "object", "additionalProperties": False, "required": [f"sdg{g}" for g in range(1, 18)],
                "properties": {f"sdg{g}": {"type": "object", "additionalProperties": False, "required": ["reason", "verdict"],
                                           "properties": {"reason": {"type": "string"}, "verdict": VERDICT}} for g in range(1, 18)}}
ARBITER_SCHEMA = {"type": "object", "additionalProperties": False, "required": ["decisions"],
                  "properties": {"decisions": {"type": "array", "items": {
                      "type": "object", "additionalProperties": False, "required": ["sdg", "reason", "verdict"],
                      "properties": {"sdg": {"type": "string", "enum": [str(g) for g in range(1, 18)]},
                                     "reason": {"type": "string"}, "verdict": VERDICT}}}}}


def compute_sha():
    blob = json.dumps({"version": VERSION, "judge_system": JUDGE_SYSTEM, "arbiter_system": ARBITER_SYSTEM,
                       "goal_blocks": [goal_block(g) for g in range(1, 18)], "work_template": WORK_TEMPLATE,
                       "no_abstract": NO_ABSTRACT, "abstract_cap": ABSTRACT_CAP, "judge_user_prefix": judge_user({})[:40],
                       "judge_schema": JUDGE_SCHEMA, "arbiter_schema": ARBITER_SCHEMA}, sort_keys=True, ensure_ascii=False)
    return hashlib.sha256(blob.encode()).hexdigest()


SHA256 = compute_sha()
if FROZEN_SHA256 != "__" + "SHA__" and SHA256 != FROZEN_SHA256:
    raise RuntimeError(f"rubric.py changed after freezing: {SHA256} != {FROZEN_SHA256}. Pre-registered; do not edit.")

if __name__ == "__main__":
    import re
    words = {g: len(TARGETS[g].split()) for g in range(1, 18)}
    print("target words per goal:", words, "min", min(words.values()), "max", max(words.values()))
    print("judge system chars:", len(JUDGE_SYSTEM), "arbiter system chars:", len(ARBITER_SYSTEM))
    print("sha256:", SHA256)

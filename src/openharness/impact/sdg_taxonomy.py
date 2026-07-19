"""UN SDG reference data: 17 goals with targets and descriptions."""

from __future__ import annotations
from pathlib import Path
import yaml

from openharness.impact.models import SDGGoal, SDGTarget

SDG_GOALS: list[SDGGoal] = [
    SDGGoal(
        number=1,
        name="No Poverty",
        description="End poverty in all its forms everywhere",
        targets=[
            SDGTarget(
                id="1.1", goal=1, description="Eradicate extreme poverty (less than $2.15/day)"
            ),
            SDGTarget(
                id="1.2",
                goal=1,
                description="Reduce poverty by at least 50% per national definitions",
            ),
            SDGTarget(
                id="1.3", goal=1, description="Implement social protection systems and measures"
            ),
            SDGTarget(
                id="1.4",
                goal=1,
                description="Equal rights to economic resources, basic services, and property",
            ),
            SDGTarget(
                id="1.5",
                goal=1,
                description="Build resilience of the poor to climate and economic shocks",
            ),
            SDGTarget(
                id="1.a", goal=1, description="Mobilize resources for poverty eradication programs"
            ),
            SDGTarget(
                id="1.b",
                goal=1,
                description="Create pro-poor and gender-sensitive policy frameworks",
            ),
        ],
    ),
    SDGGoal(
        number=2,
        name="Zero Hunger",
        description="End hunger, achieve food security and improved nutrition",
        targets=[
            SDGTarget(
                id="2.1",
                goal=2,
                description="End hunger and ensure access to safe and nutritious food",
            ),
            SDGTarget(id="2.2", goal=2, description="End all forms of malnutrition"),
            SDGTarget(
                id="2.3",
                goal=2,
                description="Double agricultural productivity and incomes of small-scale food producers",
            ),
            SDGTarget(id="2.4", goal=2, description="Ensure sustainable food production systems"),
            SDGTarget(
                id="2.5",
                goal=2,
                description="Maintain genetic diversity of seeds, plants, and animals",
            ),
            SDGTarget(
                id="2.a",
                goal=2,
                description="Increase investment in rural infrastructure and agricultural research",
            ),
            SDGTarget(
                id="2.b",
                goal=2,
                description="Correct and prevent trade restrictions in world agricultural markets",
            ),
            SDGTarget(
                id="2.c",
                goal=2,
                description="Ensure stable food commodity markets and timely access to information",
            ),
        ],
    ),
    SDGGoal(
        number=3,
        name="Good Health and Well-being",
        description="Ensure healthy lives and promote well-being for all",
        targets=[
            SDGTarget(id="3.1", goal=3, description="Reduce maternal mortality ratio"),
            SDGTarget(
                id="3.2", goal=3, description="End preventable deaths of newborns and children"
            ),
            SDGTarget(id="3.3", goal=3, description="End epidemics of AIDS, tuberculosis, malaria"),
            SDGTarget(
                id="3.4",
                goal=3,
                description="Reduce premature mortality from non-communicable diseases",
            ),
            SDGTarget(
                id="3.5",
                goal=3,
                description="Strengthen prevention and treatment of substance abuse",
            ),
            SDGTarget(
                id="3.6",
                goal=3,
                description="Halve global deaths and injuries from road traffic accidents",
            ),
            SDGTarget(
                id="3.7",
                goal=3,
                description="Ensure universal access to sexual and reproductive health-care services",
            ),
            SDGTarget(id="3.8", goal=3, description="Achieve universal health coverage"),
            SDGTarget(
                id="3.9", goal=3, description="Reduce deaths from hazardous chemicals and pollution"
            ),
            SDGTarget(id="3.a", goal=3, description="Strengthen implementation of tobacco control"),
            SDGTarget(
                id="3.b",
                goal=3,
                description="Support R&D for vaccines and medicines for developing countries",
            ),
            SDGTarget(
                id="3.c",
                goal=3,
                description="Increase health financing and health workforce in developing countries",
            ),
            SDGTarget(
                id="3.d",
                goal=3,
                description="Strengthen capacity for early warning and risk reduction",
            ),
        ],
    ),
    SDGGoal(
        number=4,
        name="Quality Education",
        description="Ensure inclusive and equitable quality education",
        targets=[
            SDGTarget(
                id="4.1",
                goal=4,
                description="Ensure free, equitable, quality primary and secondary education",
            ),
            SDGTarget(
                id="4.2",
                goal=4,
                description="Ensure access to quality early childhood development and pre-primary education",
            ),
            SDGTarget(
                id="4.3",
                goal=4,
                description="Ensure equal access to affordable technical, vocational, and tertiary education",
            ),
            SDGTarget(
                id="4.4",
                goal=4,
                description="Increase youth and adults with relevant skills for employment",
            ),
            SDGTarget(
                id="4.5",
                goal=4,
                description="Eliminate gender disparities and ensure equal access for vulnerable",
            ),
            SDGTarget(
                id="4.6",
                goal=4,
                description="Ensure all youth and adults achieve literacy and numeracy",
            ),
            SDGTarget(
                id="4.7",
                goal=4,
                description="Ensure learners acquire knowledge for sustainable development",
            ),
            SDGTarget(
                id="4.a",
                goal=4,
                description="Build and upgrade inclusive and safe education facilities",
            ),
            SDGTarget(id="4.b", goal=4, description="Expand scholarships for developing countries"),
            SDGTarget(id="4.c", goal=4, description="Increase supply of qualified teachers"),
        ],
    ),
    SDGGoal(
        number=5,
        name="Gender Equality",
        description="Achieve gender equality and empower all women and girls",
        targets=[
            SDGTarget(
                id="5.1",
                goal=5,
                description="End all forms of discrimination against women and girls",
            ),
            SDGTarget(
                id="5.2",
                goal=5,
                description="Eliminate all forms of violence against women and girls",
            ),
            SDGTarget(
                id="5.3", goal=5, description="Eliminate harmful practices such as child marriage"
            ),
            SDGTarget(
                id="5.4", goal=5, description="Recognize and value unpaid care and domestic work"
            ),
            SDGTarget(
                id="5.5",
                goal=5,
                description="Ensure women's full participation in leadership and decision-making",
            ),
            SDGTarget(
                id="5.6",
                goal=5,
                description="Ensure universal access to reproductive health and rights",
            ),
            SDGTarget(
                id="5.a",
                goal=5,
                description="Give women equal rights to economic resources and property",
            ),
            SDGTarget(
                id="5.b",
                goal=5,
                description="Enhance use of enabling technology for women's empowerment",
            ),
            SDGTarget(
                id="5.c",
                goal=5,
                description="Adopt policies for gender equality and women's empowerment",
            ),
        ],
    ),
    SDGGoal(
        number=6,
        name="Clean Water and Sanitation",
        description="Ensure availability and sustainable management of water",
        targets=[
            SDGTarget(
                id="6.1",
                goal=6,
                description="Achieve universal access to safe and affordable drinking water",
            ),
            SDGTarget(
                id="6.2",
                goal=6,
                description="Achieve access to adequate sanitation and hygiene for all",
            ),
            SDGTarget(id="6.3", goal=6, description="Improve water quality by reducing pollution"),
            SDGTarget(
                id="6.4",
                goal=6,
                description="Increase water-use efficiency and ensure freshwater supplies",
            ),
            SDGTarget(
                id="6.5", goal=6, description="Implement integrated water resources management"
            ),
            SDGTarget(id="6.6", goal=6, description="Protect and restore water-related ecosystems"),
            SDGTarget(
                id="6.a",
                goal=6,
                description="Expand water and sanitation support to developing countries",
            ),
            SDGTarget(
                id="6.b",
                goal=6,
                description="Support local participation in water and sanitation management",
            ),
        ],
    ),
    SDGGoal(
        number=7,
        name="Affordable and Clean Energy",
        description="Ensure access to affordable, reliable, sustainable energy",
        targets=[
            SDGTarget(
                id="7.1",
                goal=7,
                description="Ensure universal access to affordable and reliable energy services",
            ),
            SDGTarget(
                id="7.2", goal=7, description="Increase substantially the share of renewable energy"
            ),
            SDGTarget(
                id="7.3",
                goal=7,
                description="Double the global rate of improvement in energy efficiency",
            ),
            SDGTarget(
                id="7.a",
                goal=7,
                description="Enhance international cooperation for clean energy research",
            ),
            SDGTarget(
                id="7.b",
                goal=7,
                description="Expand infrastructure for supplying modern energy services",
            ),
        ],
    ),
    SDGGoal(
        number=8,
        name="Decent Work and Economic Growth",
        description="Promote sustained, inclusive economic growth and decent work",
        targets=[
            SDGTarget(id="8.1", goal=8, description="Sustain per capita economic growth"),
            SDGTarget(
                id="8.2",
                goal=8,
                description="Achieve higher levels of economic productivity through diversification",
            ),
            SDGTarget(
                id="8.3",
                goal=8,
                description="Promote development-oriented policies for productive activities and job creation",
            ),
            SDGTarget(
                id="8.4",
                goal=8,
                description="Improve resource efficiency in consumption and production",
            ),
            SDGTarget(
                id="8.5",
                goal=8,
                description="Achieve full and productive employment and decent work for all",
            ),
            SDGTarget(
                id="8.6",
                goal=8,
                description="Reduce proportion of youth not in employment, education, or training",
            ),
            SDGTarget(
                id="8.7", goal=8, description="End forced labour, modern slavery, and child labour"
            ),
            SDGTarget(
                id="8.8",
                goal=8,
                description="Protect labour rights and promote safe working environments",
            ),
            SDGTarget(
                id="8.9",
                goal=8,
                description="Promote sustainable tourism for jobs and local culture",
            ),
            SDGTarget(
                id="8.10",
                goal=8,
                description="Strengthen capacity of domestic financial institutions",
            ),
            SDGTarget(
                id="8.a",
                goal=8,
                description="Increase Aid for Trade support for developing countries",
            ),
            SDGTarget(
                id="8.b", goal=8, description="Develop a global strategy for youth employment"
            ),
        ],
    ),
    SDGGoal(
        number=9,
        name="Industry, Innovation and Infrastructure",
        description="Build resilient infrastructure, promote inclusive industrialization",
        targets=[
            SDGTarget(
                id="9.1",
                goal=9,
                description="Develop quality, reliable, sustainable and resilient infrastructure",
            ),
            SDGTarget(
                id="9.2", goal=9, description="Promote inclusive and sustainable industrialization"
            ),
            SDGTarget(
                id="9.3",
                goal=9,
                description="Increase access of small-scale enterprises to financial services",
            ),
            SDGTarget(
                id="9.4",
                goal=9,
                description="Upgrade infrastructure for sustainability with clean technologies",
            ),
            SDGTarget(
                id="9.5",
                goal=9,
                description="Enhance scientific research and technological capabilities",
            ),
            SDGTarget(
                id="9.a",
                goal=9,
                description="Facilitate sustainable infrastructure in developing countries",
            ),
            SDGTarget(
                id="9.b",
                goal=9,
                description="Support domestic technology development and diversification",
            ),
            SDGTarget(
                id="9.c",
                goal=9,
                description="Increase access to ICT and provide universal affordable Internet",
            ),
        ],
    ),
    SDGGoal(
        number=10,
        name="Reduced Inequalities",
        description="Reduce inequality within and among countries",
        targets=[
            SDGTarget(
                id="10.1",
                goal=10,
                description="Achieve income growth of the bottom 40% above national average",
            ),
            SDGTarget(
                id="10.2",
                goal=10,
                description="Empower and promote social, economic, and political inclusion",
            ),
            SDGTarget(
                id="10.3",
                goal=10,
                description="Ensure equal opportunity and reduce inequalities of outcome",
            ),
            SDGTarget(
                id="10.4",
                goal=10,
                description="Adopt fiscal, wage, and social protection policies for equality",
            ),
            SDGTarget(
                id="10.5",
                goal=10,
                description="Improve regulation of global financial markets and institutions",
            ),
            SDGTarget(
                id="10.6",
                goal=10,
                description="Ensure enhanced representation of developing countries",
            ),
            SDGTarget(
                id="10.7",
                goal=10,
                description="Facilitate orderly, safe, and responsible migration",
            ),
            SDGTarget(
                id="10.a",
                goal=10,
                description="Implement special and differential treatment for developing countries",
            ),
            SDGTarget(
                id="10.b",
                goal=10,
                description="Encourage development assistance and investment to least developed countries",
            ),
            SDGTarget(
                id="10.c", goal=10, description="Reduce transaction costs of migrant remittances"
            ),
        ],
    ),
    SDGGoal(
        number=11,
        name="Sustainable Cities and Communities",
        description="Make cities inclusive, safe, resilient, and sustainable",
        targets=[
            SDGTarget(
                id="11.1",
                goal=11,
                description="Ensure access to adequate, safe, and affordable housing",
            ),
            SDGTarget(
                id="11.2",
                goal=11,
                description="Provide access to safe, affordable, and sustainable transport systems",
            ),
            SDGTarget(
                id="11.3",
                goal=11,
                description="Enhance inclusive and sustainable urbanization and planning",
            ),
            SDGTarget(
                id="11.4",
                goal=11,
                description="Strengthen efforts to protect cultural and natural heritage",
            ),
            SDGTarget(id="11.5", goal=11, description="Reduce deaths and losses from disasters"),
            SDGTarget(id="11.6", goal=11, description="Reduce the environmental impact of cities"),
            SDGTarget(
                id="11.7",
                goal=11,
                description="Provide universal access to safe and inclusive green public spaces",
            ),
            SDGTarget(
                id="11.a",
                goal=11,
                description="Support positive economic, social, and environmental links between areas",
            ),
            SDGTarget(
                id="11.b",
                goal=11,
                description="Increase cities adopting integrated policies for resilience",
            ),
            SDGTarget(
                id="11.c",
                goal=11,
                description="Support least developed countries in sustainable and resilient building",
            ),
        ],
    ),
    SDGGoal(
        number=12,
        name="Responsible Consumption and Production",
        description="Ensure sustainable consumption and production patterns",
        targets=[
            SDGTarget(
                id="12.1",
                goal=12,
                description="Implement 10-Year Framework of Programmes on sustainable consumption",
            ),
            SDGTarget(
                id="12.2",
                goal=12,
                description="Achieve sustainable management and efficient use of natural resources",
            ),
            SDGTarget(id="12.3", goal=12, description="Halve per capita global food waste"),
            SDGTarget(
                id="12.4",
                goal=12,
                description="Achieve environmentally sound management of chemicals and wastes",
            ),
            SDGTarget(
                id="12.5",
                goal=12,
                description="Substantially reduce waste generation through prevention and recycling",
            ),
            SDGTarget(
                id="12.6",
                goal=12,
                description="Encourage companies to adopt sustainable practices and reporting",
            ),
            SDGTarget(
                id="12.7",
                goal=12,
                description="Promote public procurement practices that are sustainable",
            ),
            SDGTarget(
                id="12.8",
                goal=12,
                description="Ensure people have relevant information for sustainable development",
            ),
            SDGTarget(
                id="12.a",
                goal=12,
                description="Support developing countries for sustainable consumption",
            ),
            SDGTarget(
                id="12.b",
                goal=12,
                description="Develop tools to monitor sustainable tourism impacts",
            ),
            SDGTarget(
                id="12.c", goal=12, description="Rationalize inefficient fossil-fuel subsidies"
            ),
        ],
    ),
    SDGGoal(
        number=13,
        name="Climate Action",
        description="Take urgent action to combat climate change and its impacts",
        targets=[
            SDGTarget(
                id="13.1",
                goal=13,
                description="Strengthen resilience and adaptive capacity to climate-related hazards",
            ),
            SDGTarget(
                id="13.2",
                goal=13,
                description="Integrate climate change measures into national policies",
            ),
            SDGTarget(
                id="13.3",
                goal=13,
                description="Improve education and awareness on climate change mitigation",
            ),
            SDGTarget(
                id="13.a",
                goal=13,
                description="Implement commitment to $100 billion annually for developing countries",
            ),
            SDGTarget(
                id="13.b",
                goal=13,
                description="Promote mechanisms to raise capacity for climate planning in LDCs",
            ),
        ],
    ),
    SDGGoal(
        number=14,
        name="Life Below Water",
        description="Conserve and sustainably use the oceans, seas, and marine resources",
        targets=[
            SDGTarget(id="14.1", goal=14, description="Prevent and reduce marine pollution"),
            SDGTarget(
                id="14.2",
                goal=14,
                description="Sustainably manage and protect marine and coastal ecosystems",
            ),
            SDGTarget(id="14.3", goal=14, description="Minimize and address ocean acidification"),
            SDGTarget(id="14.4", goal=14, description="Regulate harvesting and end overfishing"),
            SDGTarget(
                id="14.5", goal=14, description="Conserve at least 10% of coastal and marine areas"
            ),
            SDGTarget(
                id="14.6",
                goal=14,
                description="Prohibit fisheries subsidies contributing to overcapacity",
            ),
            SDGTarget(
                id="14.7",
                goal=14,
                description="Increase economic benefits to SIDS from sustainable use of marine resources",
            ),
            SDGTarget(
                id="14.a",
                goal=14,
                description="Increase scientific knowledge and research capacity for ocean health",
            ),
            SDGTarget(
                id="14.b",
                goal=14,
                description="Provide access for small-scale artisanal fishers to marine resources",
            ),
            SDGTarget(
                id="14.c",
                goal=14,
                description="Enhance conservation through international law (UNCLOS)",
            ),
        ],
    ),
    SDGGoal(
        number=15,
        name="Life on Land",
        description="Protect, restore, and promote sustainable use of terrestrial ecosystems",
        targets=[
            SDGTarget(
                id="15.1",
                goal=15,
                description="Ensure conservation and sustainable use of terrestrial ecosystems",
            ),
            SDGTarget(
                id="15.2",
                goal=15,
                description="Promote sustainable management of forests and halt deforestation",
            ),
            SDGTarget(
                id="15.3", goal=15, description="Combat desertification and restore degraded land"
            ),
            SDGTarget(id="15.4", goal=15, description="Ensure conservation of mountain ecosystems"),
            SDGTarget(
                id="15.5",
                goal=15,
                description="Reduce degradation of natural habitats and halt biodiversity loss",
            ),
            SDGTarget(
                id="15.6",
                goal=15,
                description="Promote fair sharing of benefits from genetic resources",
            ),
            SDGTarget(
                id="15.7", goal=15, description="End poaching and trafficking of protected species"
            ),
            SDGTarget(
                id="15.8", goal=15, description="Prevent introduction of invasive alien species"
            ),
            SDGTarget(
                id="15.9",
                goal=15,
                description="Integrate ecosystem and biodiversity values into national planning",
            ),
            SDGTarget(
                id="15.a", goal=15, description="Mobilize resources for biodiversity and ecosystems"
            ),
            SDGTarget(id="15.b", goal=15, description="Finance sustainable forest management"),
            SDGTarget(
                id="15.c",
                goal=15,
                description="Enhance global support for combating poaching and trafficking",
            ),
        ],
    ),
    SDGGoal(
        number=16,
        name="Peace, Justice and Strong Institutions",
        description="Promote peaceful and inclusive societies",
        targets=[
            SDGTarget(
                id="16.1",
                goal=16,
                description="Significantly reduce all forms of violence and related death rates",
            ),
            SDGTarget(
                id="16.2",
                goal=16,
                description="End abuse, exploitation, trafficking, and violence against children",
            ),
            SDGTarget(
                id="16.3",
                goal=16,
                description="Promote the rule of law and ensure equal access to justice",
            ),
            SDGTarget(id="16.4", goal=16, description="Reduce illicit financial and arms flows"),
            SDGTarget(
                id="16.5", goal=16, description="Substantially reduce corruption and bribery"
            ),
            SDGTarget(
                id="16.6",
                goal=16,
                description="Develop effective, accountable, and transparent institutions",
            ),
            SDGTarget(
                id="16.7",
                goal=16,
                description="Ensure responsive, inclusive, and representative decision-making",
            ),
            SDGTarget(
                id="16.8",
                goal=16,
                description="Broaden participation of developing countries in global governance",
            ),
            SDGTarget(
                id="16.9",
                goal=16,
                description="Provide legal identity for all, including birth registration",
            ),
            SDGTarget(
                id="16.10",
                goal=16,
                description="Ensure public access to information and protect fundamental freedoms",
            ),
            SDGTarget(
                id="16.a",
                goal=16,
                description="Strengthen national institutions for preventing violence and combating crime",
            ),
            SDGTarget(
                id="16.b",
                goal=16,
                description="Promote and enforce non-discriminatory laws and policies",
            ),
        ],
    ),
    SDGGoal(
        number=17,
        name="Partnerships for the Goals",
        description="Strengthen the means of implementation and revitalize global partnerships",
        targets=[
            SDGTarget(id="17.1", goal=17, description="Strengthen domestic resource mobilization"),
            SDGTarget(
                id="17.2", goal=17, description="Developed countries to implement ODA commitments"
            ),
            SDGTarget(
                id="17.3",
                goal=17,
                description="Mobilize additional financial resources for developing countries",
            ),
        ],
    ),
]

_SDG_LOOKUP: dict[int, SDGGoal] = {g.number: g for g in SDG_GOALS}


def get_sdg_goal(number: int) -> SDGGoal | None:
    return _SDG_LOOKUP.get(number)


def get_sdg_goals() -> list[SDGGoal]:
    return list(SDG_GOALS)


def get_sdg_target(target_id: str) -> SDGTarget | None:
    """Look up a target by ID like '1.1' or '5.a'."""
    try:
        goal_num = int(target_id.split(".")[0])
    except (ValueError, IndexError):
        return None
    goal = _SDG_LOOKUP.get(goal_num)
    if goal is None:
        return None
    for t in goal.targets:
        if t.id == target_id:
            return t
    return None


def get_all_targets() -> list[SDGTarget]:
    targets: list[SDGTarget] = []
    for g in SDG_GOALS:
        targets.extend(g.targets)
    return targets


def sdg_need_context(geography: str, sdg_goals: list[int]) -> dict:
    path = Path(__file__).resolve().parents[3] / "data/sdg_need_context.yaml"
    payload = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    country = payload.get("countries", {}).get(geography, {})
    rows = [
        {
            "goal": int(goal),
            "need_intensity": country.get(int(goal), country.get(str(goal), "neutral")),
        }
        for goal in sdg_goals
    ]
    return {
        "geography": geography,
        "goals": rows,
        "overall_band": max(
            (r["need_intensity"] for r in rows),
            key={"neutral": 0, "low": 1, "medium": 2, "high": 3}.get,
            default="neutral",
        ),
        "source": payload.get("source", ""),
        "as_of": payload.get("as_of", ""),
    }

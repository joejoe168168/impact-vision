"""Build data/i18n/phrasebook.yaml (zh-HK authored here, zh-CN derived).

The report body is generated in English. This phrasebook maps each
generated sentence pattern to Chinese so a zh-HK / zh-CN report can be sent
without editing (roadmap v8 W3.7). Claims and the company's own sentences
are never translated (they are evidence and stay verbatim); IRIS+ metric
names stay in English (IRIS+ is published in English only).

    pip install opencc-python-reimplemented   # authoring only
    python scripts/build_phrasebook.py

Group filters in templates: {who:who} stakeholder, {sector:sector},
{l:eq} evidence-quality label, {c:gwc} greenwashing class, {i:neg} negative
impact, {v:verified}.
"""
from __future__ import annotations

from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "i18n" / "phrasebook.yaml"

# (English regex, zh-HK template)
PATTERNS: list[tuple[str, str]] = [
    # action plan
    (r"^Coverage is below 30% of the core metric set\. Start with: (?P<m>.+?)\.?$", "核心指標覆蓋率低於 30%。先從以下指標開始：{m}。"),
    (r"^Coverage is below 60%\. Focus on closing gaps in the IRIS\+ Core Metric Set to achieve baseline compliance\.$", "覆蓋率低於 60%。請優先填補 IRIS+ 核心指標集的缺口，以達到基本要求。"),
    (r"^Good progress\. Target 80%\+ coverage by adding the remaining metrics\.$", "進展良好。補充其餘指標，目標覆蓋率達 80% 以上。"),
    (r"^Measure HOW MUCH: .*$", "量度「多少」：追蹤規模（受惠人數）、深度（改變程度）及持續時間。"),
    (r"^Assess CONTRIBUTION: .*$", "評估「貢獻」：建立反事實或基準比較。"),
    (r"^Evaluate RISK: .*$", "評估「風險」：評估證據風險、執行風險及外部風險因素。"),
    (r"^Strengthen outcome measurement: .*$", "加強成果量度：以具體指標界定你所貢獻的成果（「甚麼」）。"),
    (r"^Define WHO: .*$", "界定「誰」：列明目標人口、地域及持份者特徵。"),
    (r"^Map each SDG claim to at least one IRIS\+ metric with reported data$", "將每項可持續發展目標聲明對應至最少一項有報告數據的 IRIS+ 指標。"),
    (r"^Report the negative impacts that matter for this business, e\.g\. (?P<m>.+)$", "報告與此業務相關的負面影響，例如：{m}"),
    (r"^Report the negative impacts that matter for (?P<sector>.+?), e\.g\. (?P<m>.+)$", "報告與{sector:sector}相關的負面影響，例如：{m}"),
    (r"^Include risk-oriented and negative-impact metrics alongside positive outcomes$", "在正面成果以外，同時報告風險及負面影響指標。"),
    (r"^Report (?P<m>.+) to strengthen SDG (?P<g>\d+) evidence \((?P<x>\d+)/(?P<n>\d+) currently tracked\)$", "報告 {m}，以加強可持續發展目標 {g} 的證據（目前追蹤 {x}/{n}）。"),
    (r"^Add impact themes: (?P<t>.+)$", "加入影響主題：{t}"),
    (r"^Add specific outcome descriptions related to \"(?P<g>.+)\" targets in company documentation$", "在公司文件中加入與「{g}」目標相關的具體成果描述。"),
    (r"^Priority missing metrics: (?P<m>.+)$", "優先補充的指標：{m}"),
    (r"^Obtain third-party verification or implement a recognized measurement framework$", "取得第三方核實，或採用公認的量度框架。"),
    (r"^Report at least (?P<n>\d+) IRIS\+ metrics to unlock scores above (?P<s>[\d.]+) \(currently reporting (?P<c>\d+)\)$", "至少報告 {n} 項 IRIS+ 指標，評分才可高於 {s}（目前報告 {c} 項）。"),
    (r"^Start tracking IRIS\+ metrics to strengthen evidence and move beyond estimated scores$", "開始追蹤 IRIS+ 指標，以加強證據並以實際數據取代估算評分。"),
    (r"^Replace aspirational language with concrete, quantified outcome statements$", "以具體、量化的成果陳述取代願景式用語。"),
    (r"^Replace generic wording with a specific, quantified claim, or cite an EN ISO 14024 ecolabel$", "以具體、量化的聲明取代籠統用語，或引用 EN ISO 14024 環保標籤。"),
    (r"^Drop product-level neutrality claims that rely on credits; report reductions and credits separately$", "刪除依賴碳信用的產品層面中和聲明；分開報告減排量及碳信用。"),
    (r"^Demonstrate primary emission reductions before referencing offsets$", "先證明實際減排，才引用抵銷。"),
    (r"^Publish the implementation plan with interim targets and an independent monitor$", "公布實施計劃，包括中期目標及獨立監察機構。"),
    (r"^Commission a life-cycle assessment covering the full product/service life cycle$", "委託進行涵蓋產品／服務整個生命周期的生命周期評估。"),
    (r"^Engage an independent verifier to substantiate environmental claims$", "委聘獨立核實機構證明環保聲明。"),
    # verdict reasons
    (r"^(?P<p>\d+)% of core metrics reported \(needs (?P<n>\d+)%\)$", "已報告 {p}% 核心指標（需要 {n}%）"),
    (r"^evidence quality (?P<l>\w+) \((?P<s>\d+)/100, needs (?P<n>\d+)\)$", "證據質素{l:eq}（{s}/100，需要 {n}）"),
    (r"^no quantified outcome$", "沒有量化成果"),
    (r"^(?P<n>\d+) claims likely misleading \(claim-level greenwashing (?P<s>\d+)/100\)$", "{n} 項聲明可能具誤導性（聲明層面漂綠風險 {s}/100）"),
    (r"^greenwashing finding \((?P<s>\d+)/100: (?P<c>.+)\)$", "漂綠發現（{s}/100：{c:gwc}）"),
    (r"^people impact P50 (?P<n>[\d,]+) (?P<u>.+)$", "對人的影響 P50 {n} {u:unit}"),
    (r"^climate impact P50 (?P<n>[\d,]+) (?P<u>.+)$", "氣候影響 P50 {n} {u:unit}"),
    # evidence plan
    (r"^Report the sector's core metrics: (?P<m>.+?)\.?$", "報告行業核心指標：{m}。"),
    (r"^Report the sector's core metrics\.$", "報告行業核心指標。"),
    (r"^Only (?P<p>\d+)% of the core set is reported\.$", "只報告了 {p}% 核心指標。"),
    (r"^Have the headline reach figure \((?P<n>[\d,]+) (?P<who>.+)\) verified by a third party\.$", "由第三方核實主要覆蓋數字（{n} 名{who:who}）。"),
    (r"^Reach drives most of the remaining uncertainty\.$", "覆蓋人數是餘下不確定性的主要來源。"),
    (r"^Back the main figures with data: monitoring records, surveys or audited accounts\.$", "以數據支持主要數字：監察紀錄、調查或經審核賬目。"),
    (r"^Evidence quality is (?P<l>\w+) \((?P<s>\d+)/100\)\.$", "證據質素{l:eq}（{s}/100）。"),
    (r"^Compare with a group that did not get the product .*$", "與沒有使用產品的群組比較（對照組或可信的基線），最好由獨立機構進行。"),
    (r"^Moves evidence from level (?P<a>\d) to 3, nets out deadweight and narrows the range \(now ×(?P<x>[\d.]+) from P10 to P90\)\.$", "把證據由第 {a} 級提升至第 3 級，扣除本來會發生的部分並收窄範圍（目前 P90 為 P10 的 {x} 倍）。"),
    (r"^Moves evidence from level (?P<a>\d) to 3\.$", "把證據由第 {a} 級提升至第 3 級。"),
    (r"^Measure how much life changes for the (?P<who>.+?) \(before/after .*\)\.$", "量度{who:who}的生活改變了多少（就重要成果作前後比較，例如收入、開支、健康或學習）。"),
    (r"^Depth of change is assumed, and it carries (?P<p>\d+)% of the uncertainty\.$", "改變深度屬假設，佔不確定性的 {p}%。"),
    (r"^State how many people \(or tonnes of CO2e\) the business reached in the last 12 months\.$", "列明過去 12 個月業務惠及多少人（或減少多少噸二氧化碳當量）。"),
    (r"^No quantified outcome was found, so expected impact can't be estimated\.$", "文件中沒有量化成果，因此無法估算預期影響。"),
    (r"^Show how you manage: (?P<i>.+) \(affects (?P<who>.+)\)\.$", "說明如何管理：{i:neg}（影響{who:who}）。"),
    (r"^Material negative impact \(severity (?P<s>\d) × likelihood (?P<l>\d)\) with no control described in the documents\.$", "重要負面影響（嚴重程度 {s} × 可能性 {l}），文件中沒有描述控制措施。"),
    # greenwashing claims and flags
    (r"^(?P<w>vague|mixed|concrete|buzzword only) wording$", "{w:wording}"),
    (r"^NESTA (?P<n>\d)(?P<v>, verified)?$", "NESTA {n}{v:verified}"),
    (r"^generic environmental claim \((?P<g>.+)\)$", "籠統的環保聲明（{g}）"),
    (r"^Provide a quantified output and link to the IRIS\+ metric and source document supporting the claim\.$", "提供量化產出，並連結支持該聲明的 IRIS+ 指標及來源文件。"),
    (r"^Replace the buzzword phrasing with a measurable target: .*$", "以可量度的目標取代流行語：甚麼數字成果、何時達成、惠及哪些人？"),
    (r"^Attach the source document or system export that supports the figure\.$", "附上支持該數字的來源文件或系統匯出資料。"),
    (r"^Move the evidence up the NESTA ladder: .*$", "提升 NESTA 證據等級：前後比較、雙重差分或第三方評估。"),
    (r"^Name the recognised standard or proof behind the claim \(EU ECGT\)\.$", "列明支持該聲明的公認標準或證明（歐盟 ECGT）。"),
    (r"^No evidence of third-party verification or auditing$", "沒有第三方核實或審核的證據"),
    (r"^Missing negative-impact metrics for sector$", "缺少該行業的負面影響指標"),
    (r"^Reporting appears to cherry-pick positive metrics$", "報告似乎只挑選正面指標"),
    (r"^SDG/theme claims lack supporting metric evidence$", "可持續發展目標／主題聲明缺乏指標證據"),
    (r"^Claims use aspirational language without concrete evidence$", "聲明使用願景式用語，缺乏具體證據"),
    # five dimensions notes
    (r"^(?P<n>\d+) metrics? reported · (?P<x>\d+) of (?P<a>\d+) reference metrics(?P<rest>.*)$", "已報告 {n} 項指標 · 參考指標 {x}/{a}{rest:note}"),
    (r"^Estimated from sector/description · (?P<a>\d+) reference metrics? to track(?P<rest>.*)$", "按行業／描述估算 · 可追蹤 {a} 項參考指標{rest:note}"),
]

# Fragments replaced inside a sentence (5D score notes).
FRAGMENTS: list[tuple[str, str]] = [
    (r"adverse impact penalty -(?P<x>[\d.]+)", "負面影響扣分 -{x}"),
    (r"exclusion flag penalty -(?P<x>[\d.]+)", "排除名單扣分 -{x}"),
    (r"capped: report ≥(?P<n>\d+) metrics to unlock higher scores", "設有上限：須報告至少 {n} 項指標才可取得更高評分"),
    (r"\(", "（"), (r"\)", "）"), (r"; ", "；"),
]

# Exact sentences: stakeholders, sector risk/opportunity templates.
EXACT: dict[str, str] = {
    # stakeholders and units
    "households": "住戶", "people": "人", "patients": "病人", "students": "學生", "farmers": "農民",
    "customers": "客戶", "clients": "客戶", "borrowers": "借款人", "tenants": "租戶", "residents": "居民",
    "businesses": "企業", "small businesses": "小企業", "older people": "長者", "users": "用戶",
    "women": "婦女", "children": "兒童", "learners": "學員", "smallholders": "小農", "families": "家庭",
    "ecosystems": "生態系統", "public health": "公共衞生", "communities, ecosystems": "社區、生態系統",
    "supply-chain workers": "供應鏈工人", "communities, environment": "社區、環境",
    "low-income customers": "低收入客戶", "low-income patients": "低收入病人", "low-income households": "低收入住戶",
    "communities, staff": "社區、員工", "disadvantaged learners": "弱勢學員", "ecosystems, communities": "生態系統、社區",
    "tenants, communities": "租戶、社區", "climate": "氣候", "environment, communities": "環境、社區",
    "workers": "工人", "animals": "動物", "drivers, public": "司機、公眾", "communities, climate": "社區、氣候",
    "local communities": "當地社區", "excluded users": "被排除的用戶", "staff": "員工",
    "depth-weighted person-years": "按深度加權的人年", "tCO2e": "噸二氧化碳當量",
    "people_outcome": "人", "climate_outcome": "氣候",
    "vague": "用語含糊", "mixed": "部分量化", "concrete": "具體量化", "buzzword only": "只有流行語",
    "weak": "薄弱", "moderate": "中等", "good": "良好", "strong": "強",
}

# Exact sentences: sector risk / opportunity templates (impact_report_tool).
SENTENCES: dict[str, str] = {
    "Environmental degradation: soil depletion, water pollution from fertilizers/pesticides": "環境退化：土壤耗損、肥料／農藥造成水污染",
    "Climate vulnerability: sensitivity to extreme weather events and climate change": "氣候脆弱性：易受極端天氣及氣候變化影響",
    "Labor conditions: risk of exploitative labor practices": "勞工條件：剝削勞工的風險",
    "Land use change: deforestation or biodiversity loss from land conversion": "土地用途改變：土地轉換導致森林砍伐或生物多樣性流失",
    "Market volatility: commodity price fluctuations affecting farmer incomes": "市場波動：商品價格波動影響農民收入",
    "Environmental pollution: waste management, methane emissions, water contamination": "環境污染：廢物管理、甲烷排放、水污染",
    "Food security: improving access to nutritious food for underserved populations": "糧食安全：讓服務不足的人口更易獲得有營養的食物",
    "Poverty reduction: increasing income for smallholder farmers": "減貧：提高小農收入",
    "Sustainable supply chains: promoting responsible sourcing and production": "可持續供應鏈：推動負責任的採購和生產",
    "Climate adaptation: developing climate-resilient farming practices": "氣候適應：發展具氣候韌性的耕作方式",
    "Rural employment: creating jobs in farming communities": "農村就業：在農業社區創造職位",
    "Food security: providing protein and nutrition to local markets": "糧食安全：為本地市場提供蛋白質及營養",
    "Environmental impact: land use, waste from equipment, resource extraction": "環境影響：土地使用、設備廢物、資源開採",
    "Community displacement: risk of displacing communities for energy projects": "社區遷移：能源項目導致社區遷移的風險",
    "Technology risk: rapidly changing technology making investments obsolete": "技術風險：技術快速變化令投資過時",
    "Clean energy access: providing affordable clean energy to underserved areas": "清潔能源普及：為服務不足地區提供可負擔的清潔能源",
    "Climate mitigation: reducing greenhouse gas emissions": "減緩氣候變化：減少溫室氣體排放",
    "Energy independence: reducing reliance on fossil fuels": "能源自主：減少依賴化石燃料",
    "Job creation: creating green energy employment opportunities": "創造職位：創造綠色能源就業機會",
    "Over-indebtedness: risk of predatory lending to vulnerable populations": "過度負債：向弱勢人口掠奪性放貸的風險",
    "Data privacy: risks around financial data security and misuse": "資料私隱：金融數據安全及被濫用的風險",
    "Digital exclusion: services inaccessible to those without smartphones/internet": "數碼排斥：沒有智能手機／互聯網的人無法使用服務",
    "Financial inclusion: providing access to financial services for the unbanked": "普惠金融：為沒有銀行戶口的人提供金融服務",
    "Economic empowerment: enabling savings, credit, and insurance": "經濟賦權：提供儲蓄、信貸及保險",
    "Gender equity: improving financial access for women": "性別平等：改善婦女獲得金融服務的機會",
    "Efficiency: reducing transaction costs for low-income users": "效率：降低低收入用戶的交易成本",
    "Access inequality: risk of services remaining unaffordable for the poorest": "使用不平等：服務對最貧困者仍然負擔不起的風險",
    "Quality variance: inconsistent quality of care across locations": "質素差異：各地點護理質素不一",
    "Data privacy: risks around patient health data security": "資料私隱：病人健康數據安全的風險",
    "Health outcomes: improving access to quality healthcare services": "健康成果：改善優質醫療服務的可及性",
    "Health equity: reducing disparities in healthcare access": "健康公平：縮窄醫療服務可及性的差距",
    "Disease prevention: supporting public health initiatives": "疾病預防：支持公共衞生措施",
    "Workforce development: training healthcare professionals": "人才發展：培訓醫護專業人員",
    "Sustainability: risk of depleting water sources without replenishment": "可持續性：水源耗盡而無補充的風險",
    "Infrastructure maintenance: long-term maintenance of water systems": "基建維修：供水系統的長期維修",
    "Affordability: pricing that excludes the poorest communities": "可負擔性：定價把最貧困社區排除在外",
    "Clean water access: providing safe drinking water to underserved communities": "清潔食水：為服務不足的社區提供安全飲用水",
    "Sanitation: improving hygiene and reducing waterborne disease": "衞生：改善衞生並減少水傳播疾病",
    "Water efficiency: promoting sustainable water management practices": "用水效率：推動可持續的水資源管理",
    "Quality risk: providing access without ensuring quality outcomes": "質素風險：提供機會但未確保優質成果",
    "Digital divide: technology-dependent models excluding the most vulnerable": "數碼鴻溝：依賴科技的模式把最弱勢的人排除在外",
    "Sustainability: dependence on grants or subsidies for viability": "可持續性：依賴資助或補貼維持運作",
    "Educational access: reaching underserved or marginalized populations": "教育機會：惠及服務不足或邊緣化的人口",
    "Skills development: building employable skills for the workforce": "技能發展：為勞動人口培養就業技能",
    "Digital inclusion: bridging the digital divide": "數碼共融：彌合數碼鴻溝",
    "Gender equity: improving educational access for girls and women": "性別平等：改善女童及婦女的教育機會",
    # negative impacts (data/negative_impacts.yaml)
    "End-of-life batteries and panels become hazardous e-waste": "報廢電池及太陽能板成為有害電子廢物",
    "Pay-as-you-go customers fall into arrears or lose the asset": "隨用隨付客戶拖欠款項或失去資產",
    "Forced or child labour in the polysilicon / mineral supply chain": "多晶硅／礦物供應鏈中的強迫勞動或童工",
    "Water abstraction stresses local sources": "取水令本地水源受壓",
    "Manure, run-off or pesticides pollute soil and water": "糞肥、徑流或農藥污染土壤及水",
    "Antibiotic overuse drives antimicrobial resistance": "過度使用抗生素加劇抗菌素耐藥性",
    "Land conversion or deforestation in the supply base": "供應來源的土地轉換或森林砍伐",
    "Manure and effluent pollute soil and water": "糞肥及污水污染土壤及水",
    "Poor animal welfare": "動物福利欠佳",
    "Clients become over-indebted": "客戶過度負債",
    "Opaque or abusive pricing and collection practices": "不透明或濫用的定價及收款手法",
    "Misuse or breach of clients' personal and financial data": "客戶個人及金融數據被濫用或外洩",
    "Clinical errors or substandard care": "臨床錯誤或護理不達標",
    "Medical waste mishandled": "醫療廢物處理不當",
    "User fees exclude the poorest patients": "收費把最貧困的病人排除在外",
    "Breach of patients' health data": "病人健康數據外洩",
    "Children's personal data collected or shared without safeguards": "在缺乏保障下收集或分享兒童個人資料",
    "Child safeguarding failures": "兒童保護失誤",
    "Benefits concentrate on better-off learners, widening gaps": "好處集中於較富裕的學員，擴大差距",
    "Unsafe water delivered": "供應不安全的食水",
    "Tariffs unaffordable for the poorest": "收費對最貧困者負擔不起",
    "Source depletion or brine/reject-water discharge": "水源耗盡或排放濃鹽水／廢水",
    "Evictions or displacement of existing residents": "現有居民被迫遷或遷離",
    "Building or fire-safety failures": "建築或消防安全失誤",
    "High operational and embodied carbon": "營運碳排放及隱含碳偏高",
    "Residual waste still goes to landfill or incineration": "剩餘廢物仍送往堆填或焚化",
    "Unsafe conditions for sorting and informal workers": "分揀工人及非正規工人的工作環境不安全",
    "Labour abuses in garment and product supply chains": "成衣及產品供應鏈中的勞工剝削",
    "Packaging and unsold stock become waste": "包裝及滯銷存貨成為廢物",
    "Misuse or breach of users' personal data": "用戶個人資料被濫用或外洩",
    "Digital-only service excludes users without devices or skills": "純數碼服務把沒有設備或技能的用戶排除在外",
    "Road safety incidents": "道路安全事故",
    "Air pollution and GHG from vehicles": "車輛造成的空氣污染及溫室氣體",
    "Air, water or hazardous-waste pollution": "空氣、水或有害廢物污染",
    "Occupational injuries": "職業傷害",
    "Crowding, price rises or displacement in host communities": "接待社區出現擠迫、物價上升或遷移",
    "Pressure on water, waste and fragile ecosystems": "對水、廢物及脆弱生態系統造成壓力",
    "Poor working conditions or wages for staff and contractors": "員工及承辦商的工作條件或工資欠佳",
    "Misuse of personal data": "個人資料被濫用",
}

# HK wording → mainland wording after character conversion.
CN_VOCAB = {"质素": "质量", "持份者": "利益相关方", "堆填": "填埋", "资助": "资助", "衞生": "卫生",
            "数码": "数字", "互联网": "互联网", "住户": "住户", "智能手机": "智能手机"}


def _to_cn(text: str, cc) -> str:  # noqa: ANN001
    out = cc.convert(text)
    for hk, cn in CN_VOCAB.items():
        out = out.replace(hk, cn)
    return out


def main() -> None:
    from opencc import OpenCC

    cc = OpenCC("hk2s")
    doc = {
        "as_of": "2026-10-09",
        "source": "Impact Vision; zh-CN derived from zh-HK with OpenCC hk2s plus a mainland vocabulary pass",
        "status": "machine-assisted; native-speaker review recommended before external use",
        "patterns": [{"en": en, "zh-HK": hk, "zh-CN": _to_cn(hk, cc)} for en, hk in PATTERNS],
        "fragments": [{"en": en, "zh-HK": hk, "zh-CN": _to_cn(hk, cc)} for en, hk in FRAGMENTS],
        "exact": {en: {"zh-HK": hk, "zh-CN": _to_cn(hk, cc)} for en, hk in {**EXACT, **SENTENCES}.items()},
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text("# Generated by scripts/build_phrasebook.py — edit the script, then re-run.\n"
                   + yaml.safe_dump(doc, allow_unicode=True, sort_keys=False, width=200), encoding="utf-8")
    print(f"wrote {OUT.relative_to(ROOT)}: {len(doc['patterns'])} patterns, {len(FRAGMENTS)} fragments, {len(doc['exact'])} exact")


if __name__ == "__main__":
    main()

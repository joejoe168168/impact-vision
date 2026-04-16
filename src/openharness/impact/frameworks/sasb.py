"""SASB (Sustainability Accounting Standards Board) industry-specific materiality.

SASB identifies financially material sustainability topics for 77 industries
organized into 11 sectors. Each industry has specific disclosure topics and
accounting metrics.

Reference: https://sasb.org/standards/
"""

from __future__ import annotations

from pathlib import Path

import yaml
from pydantic import BaseModel, Field


class SASBTopic(BaseModel):
    """A material sustainability topic for an industry."""
    name: str
    dimension: str  # Environment, Social Capital, Human Capital, etc.
    description: str = ""
    metrics: list[str] = Field(default_factory=list)
    iris_cross_refs: list[str] = Field(default_factory=list)


class SASBStandard(BaseModel):
    """SASB standard for a specific industry."""
    industry: str
    sector: str
    sics_code: str
    topics: list[SASBTopic] = Field(default_factory=list)


# 11 SASB sectors with representative industries and their material topics
SASB_STANDARDS: list[SASBStandard] = [
    # --- Technology & Communications ---
    SASBStandard(
        industry="Software & IT Services", sector="Technology & Communications", sics_code="TC-SI",
        topics=[
            SASBTopic(name="Environmental Footprint of Hardware Infrastructure", dimension="Environment",
                      description="Energy & water use in data centers, GHG emissions from operations",
                      metrics=["TC-SI-130a.1", "TC-SI-130a.2", "TC-SI-130a.3"],
                      iris_cross_refs=["OI1479", "OI4112"]),
            SASBTopic(name="Data Privacy & Freedom of Expression", dimension="Social Capital",
                      description="User data policies, government requests, data breaches",
                      metrics=["TC-SI-220a.1", "TC-SI-220a.2", "TC-SI-220a.3", "TC-SI-220a.4", "TC-SI-220a.5"]),
            SASBTopic(name="Data Security", dimension="Social Capital",
                      description="Security breaches, data loss, system availability",
                      metrics=["TC-SI-230a.1", "TC-SI-230a.2"]),
            SASBTopic(name="Recruiting & Managing a Global Diverse Skilled Workforce", dimension="Human Capital",
                      description="Employee engagement, diversity, inclusion, skills development",
                      metrics=["TC-SI-330a.1", "TC-SI-330a.2", "TC-SI-330a.3"],
                      iris_cross_refs=["OI8869", "OI6213", "OI1571"]),
            SASBTopic(name="Intellectual Property Protection & Competitive Behavior", dimension="Business Model & Innovation",
                      description="IP licensing, anti-competitive practices",
                      metrics=["TC-SI-520a.1"]),
            SASBTopic(name="Managing Systemic Risks from Technology Disruptions", dimension="Leadership & Governance",
                      description="Critical system uptime, disaster recovery, systemic risk",
                      metrics=["TC-SI-550a.1", "TC-SI-550a.2"]),
        ],
    ),
    SASBStandard(
        industry="Internet Media & Services", sector="Technology & Communications", sics_code="TC-IM",
        topics=[
            SASBTopic(name="Environmental Footprint of Hardware Infrastructure", dimension="Environment",
                      metrics=["TC-IM-130a.1", "TC-IM-130a.2", "TC-IM-130a.3"]),
            SASBTopic(name="Data Privacy, Advertising Standards & Freedom of Expression", dimension="Social Capital",
                      metrics=["TC-IM-220a.1", "TC-IM-220a.2", "TC-IM-220a.3", "TC-IM-220a.4"]),
            SASBTopic(name="Data Security", dimension="Social Capital",
                      metrics=["TC-IM-230a.1", "TC-IM-230a.2"]),
            SASBTopic(name="Employee Recruitment Inclusion & Performance", dimension="Human Capital",
                      metrics=["TC-IM-330a.1", "TC-IM-330a.2", "TC-IM-330a.3"]),
        ],
    ),
    # --- Financials ---
    SASBStandard(
        industry="Commercial Banks", sector="Financials", sics_code="FN-CB",
        topics=[
            SASBTopic(name="Data Security", dimension="Social Capital",
                      metrics=["FN-CB-230a.1", "FN-CB-230a.2"]),
            SASBTopic(name="Financial Inclusion & Capacity Building", dimension="Social Capital",
                      description="Access to financial services for underserved populations",
                      metrics=["FN-CB-240a.1", "FN-CB-240a.2", "FN-CB-240a.3", "FN-CB-240a.4"],
                      iris_cross_refs=["PI4060", "OD8350"]),
            SASBTopic(name="Incorporation of ESG Factors in Credit Analysis", dimension="Social Capital",
                      metrics=["FN-CB-410a.1", "FN-CB-410a.2"]),
            SASBTopic(name="Business Ethics", dimension="Leadership & Governance",
                      metrics=["FN-CB-510a.1", "FN-CB-510a.2"]),
            SASBTopic(name="Systemic Risk Management", dimension="Leadership & Governance",
                      metrics=["FN-CB-550a.1", "FN-CB-550a.2"]),
        ],
    ),
    SASBStandard(
        industry="Asset Management & Custody Activities", sector="Financials", sics_code="FN-AC",
        topics=[
            SASBTopic(name="Transparent Information & Fair Advice for Customers", dimension="Social Capital",
                      metrics=["FN-AC-270a.1", "FN-AC-270a.2", "FN-AC-270a.3"]),
            SASBTopic(name="Employee Diversity & Inclusion", dimension="Human Capital",
                      metrics=["FN-AC-330a.1"],
                      iris_cross_refs=["OI6213", "OI1571"]),
            SASBTopic(name="Incorporation of ESG Factors in Investment Management", dimension="Social Capital",
                      metrics=["FN-AC-410a.1", "FN-AC-410a.2", "FN-AC-410a.3"]),
            SASBTopic(name="Business Ethics", dimension="Leadership & Governance",
                      metrics=["FN-AC-510a.1", "FN-AC-510a.2"]),
            SASBTopic(name="Systemic Risk Management", dimension="Leadership & Governance",
                      metrics=["FN-AC-550a.1", "FN-AC-550a.2", "FN-AC-550a.3"]),
        ],
    ),
    SASBStandard(
        industry="Insurance", sector="Financials", sics_code="FN-IN",
        topics=[
            SASBTopic(name="Transparent Information & Fair Advice for Customers", dimension="Social Capital",
                      metrics=["FN-IN-270a.1", "FN-IN-270a.2", "FN-IN-270a.3", "FN-IN-270a.4"]),
            SASBTopic(name="Incorporation of ESG Factors in Investment Management", dimension="Social Capital",
                      metrics=["FN-IN-410a.1", "FN-IN-410a.2"]),
            SASBTopic(name="Policies Designed to Incentivize Responsible Behavior", dimension="Social Capital",
                      metrics=["FN-IN-410b.1", "FN-IN-410b.2"]),
            SASBTopic(name="Physical Impacts of Climate Change", dimension="Environment",
                      metrics=["FN-IN-450a.1", "FN-IN-450a.2", "FN-IN-450a.3"]),
        ],
    ),
    # --- Health Care ---
    SASBStandard(
        industry="Health Care Delivery", sector="Health Care", sics_code="HC-DY",
        topics=[
            SASBTopic(name="Energy Management", dimension="Environment",
                      metrics=["HC-DY-130a.1"],
                      iris_cross_refs=["OI1479"]),
            SASBTopic(name="Waste Management", dimension="Environment",
                      metrics=["HC-DY-150a.1", "HC-DY-150a.2", "HC-DY-150a.3"]),
            SASBTopic(name="Patient Privacy & Electronic Health Records", dimension="Social Capital",
                      metrics=["HC-DY-230a.1", "HC-DY-230a.2"]),
            SASBTopic(name="Access for Low-Income Patients", dimension="Social Capital",
                      description="Charity care, Medicaid, community health needs",
                      metrics=["HC-DY-240a.1", "HC-DY-240a.2"]),
            SASBTopic(name="Quality of Care & Patient Satisfaction", dimension="Social Capital",
                      metrics=["HC-DY-250a.1", "HC-DY-250a.2", "HC-DY-250a.3", "HC-DY-250a.4"]),
            SASBTopic(name="Employee Health & Safety", dimension="Human Capital",
                      metrics=["HC-DY-320a.1", "HC-DY-320a.2"]),
            SASBTopic(name="Pricing & Billing Transparency", dimension="Social Capital",
                      metrics=["HC-DY-270a.1"]),
        ],
    ),
    SASBStandard(
        industry="Pharmaceuticals", sector="Health Care", sics_code="HC-BP",
        topics=[
            SASBTopic(name="Safety of Clinical Trial Participants", dimension="Social Capital",
                      metrics=["HC-BP-210a.1", "HC-BP-210a.2", "HC-BP-210a.3"]),
            SASBTopic(name="Access to Medicines", dimension="Social Capital",
                      description="Pricing practices, access in developing countries",
                      metrics=["HC-BP-240a.1", "HC-BP-240a.2"]),
            SASBTopic(name="Drug Safety", dimension="Social Capital",
                      metrics=["HC-BP-250a.1", "HC-BP-250a.2", "HC-BP-250a.3", "HC-BP-250a.4", "HC-BP-250a.5"]),
            SASBTopic(name="Counterfeit Drugs", dimension="Social Capital",
                      metrics=["HC-BP-260a.1", "HC-BP-260a.2"]),
            SASBTopic(name="Ethical Marketing", dimension="Leadership & Governance",
                      metrics=["HC-BP-270a.1", "HC-BP-270a.2"]),
            SASBTopic(name="Employee Recruitment Development & Retention", dimension="Human Capital",
                      metrics=["HC-BP-330a.1", "HC-BP-330a.2"]),
        ],
    ),
    # --- Renewable Resources & Alternative Energy ---
    SASBStandard(
        industry="Solar Technology & Project Developers", sector="Renewable Resources & Alternative Energy", sics_code="RR-ST",
        topics=[
            SASBTopic(name="Energy Management in Manufacturing", dimension="Environment",
                      metrics=["RR-ST-130a.1"],
                      iris_cross_refs=["OI1479", "OI4112"]),
            SASBTopic(name="Hazardous Waste Management", dimension="Environment",
                      metrics=["RR-ST-150a.1", "RR-ST-150a.2"]),
            SASBTopic(name="Ecological Impacts of Project Development", dimension="Environment",
                      metrics=["RR-ST-160a.1", "RR-ST-160a.2"]),
            SASBTopic(name="Management of Energy Infrastructure Integration", dimension="Business Model & Innovation",
                      metrics=["RR-ST-410a.1", "RR-ST-410a.2"]),
            SASBTopic(name="Product End-of-Life Management", dimension="Business Model & Innovation",
                      metrics=["RR-ST-410b.1", "RR-ST-410b.2"]),
        ],
    ),
    SASBStandard(
        industry="Wind Technology & Project Developers", sector="Renewable Resources & Alternative Energy", sics_code="RR-WT",
        topics=[
            SASBTopic(name="Ecological Impacts of Project Development", dimension="Environment",
                      metrics=["RR-WT-160a.1", "RR-WT-160a.2", "RR-WT-160a.3", "RR-WT-160a.4"]),
            SASBTopic(name="Community Impacts of Project Development", dimension="Social Capital",
                      metrics=["RR-WT-210a.1", "RR-WT-210a.2"]),
            SASBTopic(name="Workforce Health & Safety", dimension="Human Capital",
                      metrics=["RR-WT-320a.1"]),
            SASBTopic(name="Materials Sourcing", dimension="Business Model & Innovation",
                      metrics=["RR-WT-440a.1"]),
        ],
    ),
    # --- Food & Beverage ---
    SASBStandard(
        industry="Food Retailers & Distributors", sector="Food & Beverage", sics_code="FB-FR",
        topics=[
            SASBTopic(name="Fleet Fuel Management", dimension="Environment",
                      metrics=["FB-FR-110a.1"]),
            SASBTopic(name="Air Emissions from Refrigeration", dimension="Environment",
                      metrics=["FB-FR-110b.1", "FB-FR-110b.2", "FB-FR-110b.3"]),
            SASBTopic(name="Energy Management", dimension="Environment",
                      metrics=["FB-FR-130a.1"]),
            SASBTopic(name="Food Waste Management", dimension="Environment",
                      metrics=["FB-FR-150a.1"]),
            SASBTopic(name="Food Safety", dimension="Social Capital",
                      metrics=["FB-FR-250a.1", "FB-FR-250a.2"]),
            SASBTopic(name="Product Health & Nutrition", dimension="Social Capital",
                      metrics=["FB-FR-260a.1", "FB-FR-260a.2"]),
            SASBTopic(name="Labor Practices", dimension="Human Capital",
                      metrics=["FB-FR-310a.1", "FB-FR-310a.2"]),
        ],
    ),
    SASBStandard(
        industry="Agricultural Products", sector="Food & Beverage", sics_code="FB-AG",
        topics=[
            SASBTopic(name="GHG Emissions", dimension="Environment",
                      metrics=["FB-AG-110a.1", "FB-AG-110a.2", "FB-AG-110a.3"],
                      iris_cross_refs=["OI1479", "OI4112"]),
            SASBTopic(name="Energy Management", dimension="Environment",
                      metrics=["FB-AG-130a.1"]),
            SASBTopic(name="Water Management", dimension="Environment",
                      metrics=["FB-AG-140a.1", "FB-AG-140a.2", "FB-AG-140a.3"]),
            SASBTopic(name="Food Safety", dimension="Social Capital",
                      metrics=["FB-AG-250a.1", "FB-AG-250a.2", "FB-AG-250a.3"]),
            SASBTopic(name="Workforce Health & Safety", dimension="Human Capital",
                      metrics=["FB-AG-320a.1"]),
            SASBTopic(name="Environmental & Social Impacts of Ingredient Supply Chain", dimension="Business Model & Innovation",
                      metrics=["FB-AG-430a.1", "FB-AG-430a.2", "FB-AG-430a.3"]),
            SASBTopic(name="GMO Management", dimension="Leadership & Governance",
                      metrics=["FB-AG-430b.1"]),
        ],
    ),
    # --- Infrastructure ---
    SASBStandard(
        industry="Real Estate", sector="Infrastructure", sics_code="IF-RE",
        topics=[
            SASBTopic(name="Energy Management", dimension="Environment",
                      metrics=["IF-RE-130a.1", "IF-RE-130a.2", "IF-RE-130a.3", "IF-RE-130a.4", "IF-RE-130a.5"]),
            SASBTopic(name="Water Management", dimension="Environment",
                      metrics=["IF-RE-140a.1", "IF-RE-140a.2", "IF-RE-140a.3", "IF-RE-140a.4"]),
            SASBTopic(name="Management of Tenant Sustainability Impacts", dimension="Environment",
                      metrics=["IF-RE-410a.1", "IF-RE-410a.2", "IF-RE-410a.3"]),
            SASBTopic(name="Climate Change Adaptation", dimension="Environment",
                      metrics=["IF-RE-450a.1", "IF-RE-450a.2"]),
        ],
    ),
    # --- Extractives & Minerals Processing ---
    SASBStandard(
        industry="Oil & Gas Exploration & Production", sector="Extractives & Minerals Processing", sics_code="EM-EP",
        topics=[
            SASBTopic(name="GHG Emissions", dimension="Environment",
                      metrics=["EM-EP-110a.1", "EM-EP-110a.2", "EM-EP-110a.3"]),
            SASBTopic(name="Air Quality", dimension="Environment",
                      metrics=["EM-EP-120a.1"]),
            SASBTopic(name="Water Management", dimension="Environment",
                      metrics=["EM-EP-140a.1", "EM-EP-140a.2", "EM-EP-140a.3", "EM-EP-140a.4"]),
            SASBTopic(name="Biodiversity Impacts", dimension="Environment",
                      metrics=["EM-EP-160a.1", "EM-EP-160a.2", "EM-EP-160a.3"]),
            SASBTopic(name="Security Human Rights & Rights of Indigenous Peoples", dimension="Social Capital",
                      metrics=["EM-EP-210a.1", "EM-EP-210a.2", "EM-EP-210a.3"]),
            SASBTopic(name="Community Relations", dimension="Social Capital",
                      metrics=["EM-EP-210b.1", "EM-EP-210b.2"]),
            SASBTopic(name="Workforce Health & Safety", dimension="Human Capital",
                      metrics=["EM-EP-320a.1", "EM-EP-320a.2"]),
            SASBTopic(name="Reserves Valuation & Capital Expenditures", dimension="Business Model & Innovation",
                      metrics=["EM-EP-420a.1", "EM-EP-420a.2", "EM-EP-420a.3", "EM-EP-420a.4"]),
            SASBTopic(name="Business Ethics & Transparency", dimension="Leadership & Governance",
                      metrics=["EM-EP-510a.1", "EM-EP-510a.2"]),
            SASBTopic(name="Management of the Legal & Regulatory Environment", dimension="Leadership & Governance",
                      metrics=["EM-EP-530a.1"]),
        ],
    ),
    # --- Consumer Goods ---
    SASBStandard(
        industry="Apparel Accessories & Footwear", sector="Consumer Goods", sics_code="CG-AA",
        topics=[
            SASBTopic(name="Management of Chemicals in Products", dimension="Environment",
                      metrics=["CG-AA-250a.1", "CG-AA-250a.2"]),
            SASBTopic(name="Environmental Impacts in the Supply Chain", dimension="Environment",
                      metrics=["CG-AA-430a.1", "CG-AA-430a.2"]),
            SASBTopic(name="Labor Conditions in the Supply Chain", dimension="Social Capital",
                      metrics=["CG-AA-430b.1", "CG-AA-430b.2", "CG-AA-430b.3"]),
            SASBTopic(name="Raw Materials Sourcing", dimension="Business Model & Innovation",
                      metrics=["CG-AA-440a.1", "CG-AA-440a.2"]),
        ],
    ),
    # --- Resource Transformation ---
    SASBStandard(
        industry="Chemicals", sector="Resource Transformation", sics_code="RT-CH",
        topics=[
            SASBTopic(name="GHG Emissions", dimension="Environment",
                      metrics=["RT-CH-110a.1", "RT-CH-110a.2"]),
            SASBTopic(name="Air Quality", dimension="Environment",
                      metrics=["RT-CH-120a.1"]),
            SASBTopic(name="Energy Management", dimension="Environment",
                      metrics=["RT-CH-130a.1"]),
            SASBTopic(name="Water Management", dimension="Environment",
                      metrics=["RT-CH-140a.1", "RT-CH-140a.2", "RT-CH-140a.3"]),
            SASBTopic(name="Hazardous Waste Management", dimension="Environment",
                      metrics=["RT-CH-150a.1"]),
            SASBTopic(name="Community Relations", dimension="Social Capital",
                      metrics=["RT-CH-210a.1"]),
            SASBTopic(name="Workforce Health & Safety", dimension="Human Capital",
                      metrics=["RT-CH-320a.1", "RT-CH-320a.2"]),
            SASBTopic(name="Product Design for Use-Phase Efficiency", dimension="Business Model & Innovation",
                      metrics=["RT-CH-410a.1"]),
            SASBTopic(name="Safety & Environmental Stewardship of Chemicals", dimension="Business Model & Innovation",
                      metrics=["RT-CH-410b.1", "RT-CH-410b.2"]),
            SASBTopic(name="Management of the Legal & Regulatory Environment", dimension="Leadership & Governance",
                      metrics=["RT-CH-530a.1"]),
            SASBTopic(name="Operational Safety Emergency Preparedness & Response", dimension="Leadership & Governance",
                      metrics=["RT-CH-540a.1", "RT-CH-540a.2"]),
        ],
    ),
    # --- Transportation ---
    SASBStandard(
        industry="Auto Parts", sector="Transportation", sics_code="TR-AP",
        topics=[
            SASBTopic(name="Energy Management", dimension="Environment",
                      metrics=["TR-AP-130a.1"]),
            SASBTopic(name="Waste Management", dimension="Environment",
                      metrics=["TR-AP-150a.1"]),
            SASBTopic(name="Product Safety", dimension="Social Capital",
                      metrics=["TR-AP-250a.1"]),
            SASBTopic(name="Design for Fuel Efficiency", dimension="Business Model & Innovation",
                      metrics=["TR-AP-410a.1"]),
            SASBTopic(name="Materials Sourcing", dimension="Business Model & Innovation",
                      metrics=["TR-AP-440a.1"]),
            SASBTopic(name="Materials Efficiency", dimension="Business Model & Innovation",
                      metrics=["TR-AP-440b.1"]),
        ],
    ),
    # --- Services ---
    SASBStandard(
        industry="Education", sector="Services", sics_code="SV-ED",
        topics=[
            SASBTopic(name="Data Security", dimension="Social Capital",
                      metrics=["SV-ED-230a.1"]),
            SASBTopic(name="Quality of Education & Gainful Employment", dimension="Social Capital",
                      description="Student outcomes, graduation rates, employment placement",
                      metrics=["SV-ED-260a.1", "SV-ED-260a.2", "SV-ED-260a.3"]),
            SASBTopic(name="Marketing & Recruiting Practices", dimension="Social Capital",
                      metrics=["SV-ED-270a.1", "SV-ED-270a.2", "SV-ED-270a.3"]),
        ],
    ),
    SASBStandard(
        industry="Hotels & Lodging", sector="Services", sics_code="SV-HL",
        topics=[
            SASBTopic(name="Energy Management", dimension="Environment",
                      metrics=["SV-HL-130a.1"]),
            SASBTopic(name="Water Management", dimension="Environment",
                      metrics=["SV-HL-140a.1"]),
            SASBTopic(name="Ecological Impacts of Tourism", dimension="Environment",
                      metrics=["SV-HL-160a.1", "SV-HL-160a.2"]),
            SASBTopic(name="Fair Labor Practices", dimension="Human Capital",
                      metrics=["SV-HL-310a.1", "SV-HL-310a.2", "SV-HL-310a.3", "SV-HL-310a.4"]),
            SASBTopic(name="Climate Change Adaptation", dimension="Environment",
                      metrics=["SV-HL-450a.1"]),
        ],
    ),
    # --- Telecommunication Services ---
    SASBStandard(
        industry="Telecommunication Services", sector="Technology & Communications", sics_code="TC-TL",
        topics=[
            SASBTopic(name="Environmental Footprint of Operations", dimension="Environment",
                      metrics=["TC-TL-130a.1"],
                      iris_cross_refs=["OI1479"]),
            SASBTopic(name="Data Privacy", dimension="Social Capital",
                      metrics=["TC-TL-220a.1", "TC-TL-220a.2", "TC-TL-220a.3", "TC-TL-220a.4"]),
            SASBTopic(name="Data Security", dimension="Social Capital",
                      metrics=["TC-TL-230a.1", "TC-TL-230a.2"]),
            SASBTopic(name="Product End-of-Life Management", dimension="Environment",
                      metrics=["TC-TL-440a.1"]),
            SASBTopic(name="Competitive Behavior & Open Internet", dimension="Leadership & Governance",
                      metrics=["TC-TL-520a.1", "TC-TL-520a.2", "TC-TL-520a.3"]),
            SASBTopic(name="Managing Systemic Risks from Technology Disruptions", dimension="Leadership & Governance",
                      metrics=["TC-TL-550a.1", "TC-TL-550a.2"]),
        ],
    ),
    # --- Electric Utilities & Power Generators ---
    SASBStandard(
        industry="Electric Utilities & Power Generators", sector="Infrastructure", sics_code="IF-EU",
        topics=[
            SASBTopic(name="GHG Emissions & Energy Resource Planning", dimension="Environment",
                      metrics=["IF-EU-110a.1", "IF-EU-110a.2", "IF-EU-110a.3", "IF-EU-110a.4"],
                      iris_cross_refs=["OI4112", "OI1479"]),
            SASBTopic(name="Air Quality", dimension="Environment",
                      metrics=["IF-EU-120a.1"]),
            SASBTopic(name="Water Management", dimension="Environment",
                      metrics=["IF-EU-140a.1", "IF-EU-140a.2", "IF-EU-140a.3"]),
            SASBTopic(name="Coal Ash Management", dimension="Environment",
                      metrics=["IF-EU-150a.1", "IF-EU-150a.2"]),
            SASBTopic(name="Energy Affordability", dimension="Social Capital",
                      description="Average retail electricity rate, customer disconnections",
                      metrics=["IF-EU-240a.1", "IF-EU-240a.2", "IF-EU-240a.3", "IF-EU-240a.4"]),
            SASBTopic(name="Workforce Health & Safety", dimension="Human Capital",
                      metrics=["IF-EU-320a.1"]),
            SASBTopic(name="End-Use Efficiency & Demand", dimension="Business Model & Innovation",
                      metrics=["IF-EU-420a.1", "IF-EU-420a.2", "IF-EU-420a.3"]),
            SASBTopic(name="Grid Resiliency", dimension="Leadership & Governance",
                      metrics=["IF-EU-550a.1", "IF-EU-550a.2"]),
        ],
    ),
    # --- Water Utilities & Services ---
    SASBStandard(
        industry="Water Utilities & Services", sector="Infrastructure", sics_code="IF-WU",
        topics=[
            SASBTopic(name="Energy Management", dimension="Environment",
                      metrics=["IF-WU-130a.1"]),
            SASBTopic(name="Distribution Network Efficiency", dimension="Environment",
                      metrics=["IF-WU-140a.1", "IF-WU-140a.2"]),
            SASBTopic(name="Effluent Quality Management", dimension="Environment",
                      metrics=["IF-WU-140b.1", "IF-WU-140b.2"]),
            SASBTopic(name="Water Affordability & Access", dimension="Social Capital",
                      description="Rate structure, customer disconnections for non-payment",
                      metrics=["IF-WU-240a.1", "IF-WU-240a.2", "IF-WU-240a.3", "IF-WU-240a.4"]),
            SASBTopic(name="Drinking Water Quality", dimension="Social Capital",
                      metrics=["IF-WU-250a.1", "IF-WU-250a.2"]),
            SASBTopic(name="End-Use Efficiency", dimension="Business Model & Innovation",
                      metrics=["IF-WU-420a.1", "IF-WU-420a.2"]),
        ],
    ),
    # --- Managed Care ---
    SASBStandard(
        industry="Managed Care", sector="Health Care", sics_code="HC-MC",
        topics=[
            SASBTopic(name="Customer Privacy & Technology Standards", dimension="Social Capital",
                      metrics=["HC-MC-230a.1"]),
            SASBTopic(name="Access to Coverage", dimension="Social Capital",
                      description="Coverage affordability, Medicaid/Medicare enrollment",
                      metrics=["HC-MC-240a.1"]),
            SASBTopic(name="Plan Performance", dimension="Social Capital",
                      metrics=["HC-MC-250a.1", "HC-MC-250a.2", "HC-MC-250a.3", "HC-MC-250a.4"]),
            SASBTopic(name="Pricing & Billing Transparency", dimension="Social Capital",
                      metrics=["HC-MC-270a.1", "HC-MC-270a.2"]),
            SASBTopic(name="Climate Change Impacts on Human Health", dimension="Environment",
                      metrics=["HC-MC-410a.1", "HC-MC-410a.2"]),
        ],
    ),
    # --- Biotechnology & Pharmaceuticals (Medical Devices) ---
    SASBStandard(
        industry="Medical Equipment & Supplies", sector="Health Care", sics_code="HC-MS",
        topics=[
            SASBTopic(name="Affordability & Pricing", dimension="Social Capital",
                      metrics=["HC-MS-240a.1", "HC-MS-240a.2"]),
            SASBTopic(name="Product Safety", dimension="Social Capital",
                      metrics=["HC-MS-250a.1", "HC-MS-250a.2", "HC-MS-250a.3", "HC-MS-250a.4"]),
            SASBTopic(name="Ethical Marketing", dimension="Leadership & Governance",
                      metrics=["HC-MS-270a.1", "HC-MS-270a.2"]),
            SASBTopic(name="Product Design & Lifecycle Management", dimension="Business Model & Innovation",
                      metrics=["HC-MS-410a.1", "HC-MS-410a.2"]),
            SASBTopic(name="Supply Chain Management", dimension="Business Model & Innovation",
                      metrics=["HC-MS-430a.1", "HC-MS-430a.2", "HC-MS-430a.3"]),
        ],
    ),
    # --- Mortgage Finance ---
    SASBStandard(
        industry="Mortgage Finance", sector="Financials", sics_code="FN-MF",
        topics=[
            SASBTopic(name="Lending Practices", dimension="Social Capital",
                      description="Responsible lending, fair access to mortgages",
                      metrics=["FN-MF-270a.1", "FN-MF-270a.2", "FN-MF-270a.3", "FN-MF-270a.4"]),
            SASBTopic(name="Discriminatory Lending", dimension="Social Capital",
                      metrics=["FN-MF-270b.1", "FN-MF-270b.2", "FN-MF-270b.3"]),
            SASBTopic(name="Environmental Risk to Mortgaged Properties", dimension="Environment",
                      metrics=["FN-MF-450a.1", "FN-MF-450a.2", "FN-MF-450a.3"]),
        ],
    ),
    # --- Consumer Finance ---
    SASBStandard(
        industry="Consumer Finance", sector="Financials", sics_code="FN-CF",
        topics=[
            SASBTopic(name="Customer Privacy", dimension="Social Capital",
                      metrics=["FN-CF-220a.1", "FN-CF-220a.2"]),
            SASBTopic(name="Data Security", dimension="Social Capital",
                      metrics=["FN-CF-230a.1", "FN-CF-230a.2", "FN-CF-230a.3"]),
            SASBTopic(name="Selling Practices", dimension="Social Capital",
                      description="Responsible lending, customer protections, complaint resolution",
                      metrics=["FN-CF-270a.1", "FN-CF-270a.2", "FN-CF-270a.3", "FN-CF-270a.4", "FN-CF-270a.5"],
                      iris_cross_refs=["PI4060"]),
        ],
    ),
]

# Sector-keyword mapping for matching
_SECTOR_KEYWORDS: dict[str, list[str]] = {
    "Technology & Communications": ["software", "tech", "IT", "SaaS", "cloud", "internet", "digital", "platform", "app", "AI", "data", "telecom", "mobile"],
    "Financials": ["bank", "finance", "fintech", "insurance", "asset management", "lending", "credit", "microfinance", "payment", "mortgage", "consumer finance"],
    "Health Care": ["health", "medical", "pharma", "biotech", "hospital", "clinic", "drug", "therapeutic", "diagnostics", "medical device", "managed care", "telemedicine"],
    "Renewable Resources & Alternative Energy": ["solar", "wind", "renewable", "clean energy", "green energy", "biomass", "hydro", "geothermal"],
    "Food & Beverage": ["food", "agriculture", "farming", "beverage", "nutrition", "crop", "livestock", "agri", "aquaculture"],
    "Infrastructure": ["real estate", "housing", "construction", "infrastructure", "property", "building", "utility", "electric", "water", "power"],
    "Extractives & Minerals Processing": ["oil", "gas", "mining", "mineral", "extraction", "fossil", "coal"],
    "Consumer Goods": ["apparel", "clothing", "fashion", "consumer", "retail", "footwear", "textile"],
    "Resource Transformation": ["chemical", "manufacturing", "industrial", "material", "processing"],
    "Transportation": ["transport", "automotive", "vehicle", "logistics", "fleet", "mobility"],
    "Services": ["education", "service", "consulting", "hospitality", "professional service", "hotel", "tourism"],
}


_sasb_cache: list[SASBStandard] | None = None


def _load_sasb_overrides() -> dict:
    """Load additional industries or keyword overrides from data/sasb_overrides.yaml."""
    config_paths = [
        Path(__file__).parent.parent.parent.parent / "data" / "sasb_overrides.yaml",
        Path("data/sasb_overrides.yaml"),
    ]
    for path in config_paths:
        if path.exists():
            try:
                raw = yaml.safe_load(path.read_text(encoding="utf-8"))
                if isinstance(raw, dict):
                    return raw
            except Exception:
                pass
    return {}


def get_sasb_industries() -> list[SASBStandard]:
    global _sasb_cache
    if _sasb_cache is not None:
        return _sasb_cache

    industries = list(SASB_STANDARDS)
    overrides = _load_sasb_overrides()
    for entry in overrides.get("additional_industries", []):
        if isinstance(entry, dict) and "industry" in entry:
            topics = [
                SASBTopic(
                    name=t.get("name", ""),
                    dimension=t.get("dimension", ""),
                    description=t.get("description", ""),
                )
                for t in entry.get("topics", [])
            ]
            industries.append(SASBStandard(
                industry=entry["industry"],
                sector=entry.get("sector", ""),
                sics_code=entry.get("sics_code", ""),
                topics=topics,
            ))
    _sasb_cache = industries
    return _sasb_cache


def match_sasb_industry(
    sector: str = "",
    description: str = "",
    keywords: list[str] | None = None,
) -> list[tuple[SASBStandard, float]]:
    """Match a company description to the most relevant SASB industries.

    Returns list of (standard, score) tuples sorted by score descending.
    """
    text = f"{sector} {description} {' '.join(keywords or [])}".lower()
    scored: list[tuple[SASBStandard, float]] = []

    for std in SASB_STANDARDS:
        score = 0.0
        for word in std.industry.lower().split():
            if len(word) > 3 and word in text:
                score += 3.0

        if std.sector.lower() in text:
            score += 2.0

        sector_kws = _SECTOR_KEYWORDS.get(std.sector, [])
        for kw in sector_kws:
            if kw.lower() in text:
                score += 1.0

        for topic in std.topics:
            topic_words = topic.name.lower().split()
            for w in topic_words:
                if len(w) > 4 and w in text:
                    score += 0.3

        if score > 0:
            scored.append((std, round(score, 2)))

    scored.sort(key=lambda x: x[1], reverse=True)
    return scored[:5]

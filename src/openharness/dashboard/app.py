"""Impact Vision Streamlit Dashboard.

Launch with: streamlit run src/openharness/dashboard/app.py
"""

from __future__ import annotations


import streamlit as st
import plotly.graph_objects as go
import plotly.express as px
import pandas as pd

st.set_page_config(page_title="Impact Vision", page_icon="🌍", layout="wide")


def _check_auth() -> bool:
    """Optional basic auth via environment variables or Streamlit secrets.

    Set IMPACT_VISION_USERNAME and IMPACT_VISION_PASSWORD environment variables,
    or add them under [dashboard] in .streamlit/secrets.toml:

        [dashboard]
        username = "admin"
        password = "your-secure-password"

    If neither is set, the dashboard runs without authentication.
    """
    import os
    username = os.environ.get("IMPACT_VISION_USERNAME", "")
    password = os.environ.get("IMPACT_VISION_PASSWORD", "")

    if not username:
        try:
            username = st.secrets.get("dashboard", {}).get("username", "")
            password = st.secrets.get("dashboard", {}).get("password", "")
        except Exception:
            pass

    if not username:
        return True

    if "authenticated" not in st.session_state:
        st.session_state.authenticated = False

    if st.session_state.authenticated:
        return True

    st.title("Impact Vision - Login")
    with st.form("login_form"):
        user_input = st.text_input("Username")
        pass_input = st.text_input("Password", type="password")
        submitted = st.form_submit_button("Login")
        if submitted:
            if user_input == username and pass_input == password:
                st.session_state.authenticated = True
                st.rerun()
            else:
                st.error("Invalid credentials")
    return False


# Lazy imports to avoid circular issues
@st.cache_resource
def _load_store():
    from openharness.impact.database import get_metric_store
    return get_metric_store()


@st.cache_resource
def _load_dd_checklist():
    from openharness.impact.dd_checklist import load_checklist
    return load_checklist()


def main():
    if not _check_auth():
        return

    st.title("Impact Vision Dashboard")
    st.caption("Open-source impact measurement and SDG alignment")

    tabs = st.tabs([
        "Company Assessment",
        "IRIS+ Catalog",
        "DD Checklist",
        "Framework Scan",
        "Portfolio",
    ])

    with tabs[0]:
        _company_assessment_tab()

    with tabs[1]:
        _iris_catalog_tab()

    with tabs[2]:
        _dd_checklist_tab()

    with tabs[3]:
        _framework_scan_tab()

    with tabs[4]:
        _portfolio_tab()


def _company_assessment_tab():
    st.header("Company Impact Assessment")

    col1, col2 = st.columns(2)
    with col1:
        name = st.text_input("Company Name", "BrightPath Finance")
        sector = st.text_input("Sector", "Financial Services")
        description = st.text_area("Description", "Digital microfinance platform for smallholder farmers and women-led micro-enterprises in Sub-Saharan Africa.")
    with col2:
        themes = st.text_input("Impact Themes (comma-separated)", "Financial Inclusion")
        sdg_claims_str = st.text_input("Claimed SDGs (comma-separated numbers)", "1,5,8,10")
        metrics_str = st.text_area("Reported Metrics (ID=value, one per line)",
                                    "PI4060=45000\nOI8869=180\nOI6213=85\nOI1571=12\nOI1479=120\nOI4112=80")

    if st.button("Run Assessment", type="primary"):
        from openharness.impact.models import Company
        from openharness.impact.five_dimensions import assess_five_dimensions
        from openharness.impact.sdg_mapper import map_sdg_alignment
        from openharness.impact.gap_analysis import analyze_gaps
        from openharness.impact.benchmarks import compare_to_benchmark

        store = _load_store()
        theme_list = [t.strip() for t in themes.split(",") if t.strip()]
        sdg_list = [int(x.strip()) for x in sdg_claims_str.split(",") if x.strip().isdigit()]
        reported = {}
        for line in metrics_str.strip().split("\n"):
            if "=" in line:
                k, v = line.split("=", 1)
                reported[k.strip()] = v.strip()

        company = Company(
            name=name, sector=sector, description=description,
            impact_themes=theme_list, sdg_claims=sdg_list, reported_metrics=reported,
        )

        col_a, col_b = st.columns(2)

        with col_a:
            st.subheader("5 Dimensions of Impact")
            fd = assess_five_dimensions(company, store)

            dims = ["What", "Who", "How Much", "Contribution", "Risk"]
            scores = [fd.what.score, fd.who.score, fd.how_much.score, fd.contribution.score, fd.risk.score]

            fig = go.Figure(data=go.Scatterpolar(
                r=scores + [scores[0]],
                theta=dims + [dims[0]],
                fill='toself',
                fillcolor='rgba(25,118,210,0.12)',
                line=dict(color='#1976d2', width=2.5),
                marker=dict(size=7, color='#1976d2'),
                name='Score',
            ))
            fig.update_layout(
                polar=dict(radialaxis=dict(visible=True, range=[0, 5])),
                showlegend=False, height=380, margin=dict(l=60, r=60, t=30, b=30),
            )
            st.plotly_chart(fig, use_container_width=True)

            st.metric("Overall Score", f"{fd.overall_score:.1f}/5", fd.overall_grade)

        with col_b:
            st.subheader("SDG Alignment")
            alignments = map_sdg_alignment(company, store)
            top = [a for a in alignments if a.score > 0]

            sdg_colors_map = {
                1: "#E5243B", 2: "#DDA63A", 3: "#4C9F38", 4: "#C5192D", 5: "#FF3A21",
                6: "#26BDE2", 7: "#FCC30B", 8: "#A21942", 9: "#FD6925", 10: "#DD1367",
                11: "#FD9D24", 12: "#BF8B2E", 13: "#3F7E44", 14: "#0A97D9", 15: "#56C02B",
                16: "#00689D", 17: "#19486A",
            }

            if top:
                sdg_df = pd.DataFrame([{
                    "SDG": f"SDG {a.goal}", "Score": a.score, "Confidence": a.confidence,
                    "Color": sdg_colors_map.get(a.goal, "#1976d2"),
                } for a in top])
                fig2 = px.bar(sdg_df, x="SDG", y="Score",
                              color_discrete_sequence=[sdg_colors_map.get(a.goal, "#1976d2") for a in top],
                              range_y=[0, 100])
                fig2.update_traces(marker_color=[sdg_colors_map.get(a.goal, "#1976d2") for a in top])
                fig2.update_layout(height=380, margin=dict(l=50, r=20, t=20, b=50), showlegend=False)
                st.plotly_chart(fig2, use_container_width=True)
            else:
                st.info("No SDG alignments detected. Report more IRIS+ metrics.")

        st.subheader("Gap Analysis")
        gaps = analyze_gaps(company, store)
        progress_val = gaps["coverage_percentage"] / 100
        st.progress(progress_val, text=f"Core Metric Set Coverage: {gaps['coverage_percentage']}%")

        col_m, col_g = st.columns(2)
        with col_m:
            st.write("**Reported Metrics**")
            for m in gaps.get("reported", []):
                st.write(f"- **{m['id']}**: {m['name']} = `{m.get('value', 'N/A')}`")
        with col_g:
            st.write("**Missing Metrics**")
            for m in gaps.get("missing", []):
                st.write(f"- **{m['id']}**: {m['name']}")

        if sector:
            five_d_scores = {
                "what": fd.what.score, "who": fd.who.score,
                "how_much": fd.how_much.score, "contribution": fd.contribution.score,
                "risk": fd.risk.score,
            }
            bm = compare_to_benchmark(sector, five_d_scores, fd.overall_score, gaps["coverage_percentage"])
            if bm.get("benchmark_available"):
                st.subheader("Sector Benchmark Comparison")
                st.caption(f"{bm['sector']} ({bm.get('sample_note', '')})")

                bm_dims = list(bm["dimensions"].keys())
                bm_actual = [bm["dimensions"][d]["actual"] for d in bm_dims]
                bm_bench = [bm["dimensions"][d]["benchmark"] for d in bm_dims]
                bm_labels = [d.replace("_", " ").title() for d in bm_dims]

                fig3 = go.Figure(data=[
                    go.Bar(name="Your Score", x=bm_labels, y=bm_actual, marker_color="#1976d2"),
                    go.Bar(name="Benchmark", x=bm_labels, y=bm_bench, marker_color="#b0bec5"),
                ])
                fig3.update_layout(barmode="group", yaxis_range=[0, 5.5], height=320,
                                   margin=dict(l=40, r=20, t=20, b=40), legend=dict(orientation="h", y=1.08))
                st.plotly_chart(fig3, use_container_width=True)

                ov = bm["overall"]
                delta = ov["delta"]
                delta_str = f"+{delta:.1f}" if delta > 0 else f"{delta:.1f}"
                st.metric("Overall vs Benchmark", f"{ov['actual']:.1f} vs {ov['benchmark']:.1f}", delta_str)


def _iris_catalog_tab():
    st.header("IRIS+ 5.3c Catalog")
    store = _load_store()

    search_col, filter_col = st.columns([2, 1])
    with search_col:
        query = st.text_input("Search metrics", "financial inclusion")
    with filter_col:
        sdg_filter = st.selectbox("Filter by SDG", [None] + list(range(1, 18)), format_func=lambda x: f"SDG {x}" if x else "All")

    if query:
        results = store.search(query, limit=20)
    elif sdg_filter:
        results = store.filter_by_sdg(sdg_filter)[:20]
    else:
        results = list(store.all_metrics())[:20]

    st.write(f"Showing {len(results)} metrics (of {store.count} total)")

    for m in results:
        with st.expander(f"{m.id}: {m.name}"):
            st.write(f"**Definition:** {m.definition}" if m.definition else "No definition")
            st.write(f"**Category:** {m.primary_impact_category}")
            st.write(f"**Section:** {m.section}")
            if m.sdg_goals:
                st.write(f"**SDGs:** {', '.join(f'SDG {g}' for g in m.sdg_goals)}")
            if m.dimensions.active_dimensions:
                st.write(f"**Dimensions:** {', '.join(m.dimensions.active_dimensions)}")


def _dd_checklist_tab():
    st.header("Impact Due Diligence Checklist")
    questions = _load_dd_checklist()

    cats = sorted(set(q.category for q in questions))
    selected_cats = st.multiselect("Filter by category", cats, default=[])
    priority_filter = st.selectbox("Priority", ["all", "high", "medium", "low"])

    filtered = questions
    if selected_cats:
        filtered = [q for q in filtered if q.category in selected_cats]
    if priority_filter != "all":
        filtered = [q for q in filtered if q.priority == priority_filter]

    st.write(f"Showing {len(filtered)} of {len(questions)} questions")

    doc_text = st.text_area("Paste document text to check coverage (optional)", height=100)

    if doc_text:
        from openharness.impact.dd_checklist import analyze_document_coverage
        cats_filter = selected_cats if selected_cats else None
        result = analyze_document_coverage(doc_text, categories=cats_filter)
        st.progress(result.coverage_pct / 100, text=f"Coverage: {result.coverage_pct}%")
        col_met1, col_met2, col_met3 = st.columns(3)
        with col_met1:
            st.metric("Addressed", len(result.addressed))
        with col_met2:
            st.metric("High-Priority Gaps", len(result.high_priority_gaps))
        with col_met3:
            st.metric("Avg Evidence Level", f"{result.avg_evidence_level:.1f}/5")

        if result.addressed:
            with st.expander(f"Addressed Questions ({len(result.addressed)})", expanded=False):
                for match in sorted(result.addressed, key=lambda m: -m.confidence):
                    ev_icon = {1: "1\uFE0F\u20E3", 2: "2\uFE0F\u20E3", 3: "3\uFE0F\u20E3", 4: "4\uFE0F\u20E3", 5: "5\uFE0F\u20E3"}.get(match.evidence_level, "")
                    st.write(f"**{match.question.id}**: {match.question.question}")
                    st.write(f"Confidence: {match.confidence:.0%} | Evidence Level: {ev_icon} {match.evidence_label}")
                    if match.relevant_text_snippets:
                        st.caption(f'"{match.relevant_text_snippets[0][:150]}..."')
                    st.divider()

        if result.high_priority_gaps:
            with st.expander(f"High-Priority Gaps ({len(result.high_priority_gaps)})", expanded=True):
                for q in result.high_priority_gaps:
                    st.write(f"**{q.id}**: {q.question}")
                    if q.follow_up:
                        st.caption(f"Follow-up: {q.follow_up}")

    for q in filtered:
        color = {"high": "🔴", "medium": "🟡", "low": "🟢"}.get(q.priority, "⚪")
        dim_tag = f" [{q.dimension}]" if q.dimension else ""
        with st.expander(f"{color} {q.id}: {q.question}{dim_tag}"):
            st.write(f"**Category:** {q.category} | **Phase:** {q.phase} | **Priority:** {q.priority}")
            if q.follow_up:
                st.write(f"**Follow-up:** {q.follow_up}")
            if q.keywords:
                st.write(f"**Keywords:** {', '.join(q.keywords)}")


def _framework_scan_tab():
    st.header("Multi-Framework ESG Scan")

    description = st.text_area("Company description for framework assessment",
                                "We track Scope 1 and Scope 2 emissions and have renewable energy targets. "
                                "We report employee diversity metrics and have board ESG oversight.")
    sector = st.text_input("Sector (for SASB matching)", "Technology", key="fw_sector")

    if st.button("Run Framework Scan", type="primary"):
        from openharness.impact.frameworks.sasb import match_sasb_industry
        from openharness.impact.frameworks.tcfd import assess_tcfd_alignment
        from openharness.impact.frameworks.sfdr_pai import assess_sfdr_compliance
        from openharness.impact.frameworks.edci import assess_edci_coverage
        from openharness.impact.frameworks.unpri import assess_unpri_alignment
        from openharness.impact.frameworks.theory_of_change import assess_toc_alignment

        fw_names = ["TCFD/IFRS S2", "SFDR PAI", "EDCI", "UNPRI", "ToC (RS Group)"]
        tcfd = assess_tcfd_alignment(description)
        sfdr = assess_sfdr_compliance(company_description=description)
        edci = assess_edci_coverage(company_description=description)
        unpri = assess_unpri_alignment(fund_description=description)
        toc = assess_toc_alignment(description=description)
        fw_pcts = [
            tcfd["overall_coverage"], sfdr["coverage_pct"], edci["coverage_pct"],
            unpri["overall_coverage"], toc["coverage_pct"],
        ]
        fw_colors = ["#1976d2", "#7b1fa2", "#2e7d32", "#f57c00", "#00838f"]

        fig_overview = go.Figure(data=[go.Bar(
            x=fw_names, y=fw_pcts,
            marker_color=fw_colors,
            text=[f"{p}%" for p in fw_pcts], textposition="outside",
        )])
        fig_overview.update_layout(
            yaxis=dict(range=[0, 110], title="Coverage %"),
            height=320, margin=dict(l=50, r=20, t=20, b=50),
            showlegend=False,
        )
        st.plotly_chart(fig_overview, use_container_width=True)

        col1, col2 = st.columns(2)

        with col1:
            st.subheader("TCFD / IFRS S2")
            st.progress(tcfd["overall_coverage"] / 100, text=f"{tcfd['overall_coverage']}% coverage")
            for p in tcfd["pillars"]:
                st.write(f"**{p['name']}**: {p['coverage_pct']}% ({len(p['addressed'])}/{p['total_disclosures']})")

            st.subheader("SFDR PAI")
            st.progress(sfdr["coverage_pct"] / 100, text=f"{sfdr['coverage_pct']}% ({sfdr['addressed']}/14)")

            st.subheader("UNPRI")
            st.progress(unpri["overall_coverage"] / 100, text=f"{unpri['overall_coverage']}% ({unpri['addressed_actions']}/{unpri['total_actions']})")

        with col2:
            st.subheader("EDCI")
            st.progress(edci["coverage_pct"] / 100, text=f"{edci['coverage_pct']}% ({edci['addressed']}/{edci['total']})")
            for cat, data in edci["by_category"].items():
                st.write(f"  {cat}: {data['coverage_pct']}%")

            st.subheader("SASB")
            matches = match_sasb_industry(sector, description)
            if matches:
                best = matches[0]
                st.write(f"Best match: **{best[0].industry}** ({best[0].sector})")
                st.write(f"Material topics: {len(best[0].topics)}")
                for t in best[0].topics[:5]:
                    st.write(f"  - {t.name} [{t.dimension}]")
            else:
                st.info("No SASB match found")

            st.subheader("Theory of Change")
            st.progress(toc["coverage_pct"] / 100, text=f"{toc['coverage_pct']}% ({toc['addressed']}/{toc['total_principles']})")


def _portfolio_tab():
    st.header("Portfolio Batch Analysis")
    st.info("Upload a CSV file with columns: name, sector, geography, description, impact_themes, sdg_claims, and any IRIS+ metric IDs as columns.")

    uploaded = st.file_uploader("Upload portfolio CSV", type=["csv"])
    if uploaded:
        import csv
        import io
        from openharness.impact.models import Company

        content = uploaded.getvalue().decode("utf-8")
        reader = csv.DictReader(io.StringIO(content))

        companies = []
        for row in reader:
            metrics = {}
            for key, val in row.items():
                if key.startswith(("PI", "OI", "OD", "FP", "PD")) and val:
                    metrics[key] = val
            companies.append(Company(
                name=row.get("name", row.get("company_name", row.get("company", ""))),
                sector=row.get("sector", ""),
                geography=row.get("geography", ""),
                description=row.get("description", ""),
                impact_themes=[t.strip() for t in row.get("impact_themes", "").split(",") if t.strip()],
                reported_metrics=metrics,
                sdg_claims=[int(x.strip()) for x in row.get("sdg_claims", "").split(",") if x.strip().isdigit()],
            ))

        st.write(f"Loaded {len(companies)} companies")

        if st.button("Analyze Portfolio", type="primary"):
            from openharness.impact.five_dimensions import assess_five_dimensions
            from openharness.impact.sdg_mapper import map_sdg_alignment
            from openharness.impact.gap_analysis import analyze_gaps
            from openharness.impact.benchmarks import compare_to_giin_survey

            store = _load_store()
            results = []
            company_details = {}
            for c in companies:
                fd = assess_five_dimensions(c, store)
                gaps = analyze_gaps(c, store)
                sdg = map_sdg_alignment(c, store)
                top_sdgs = [a for a in sdg if a.score > 0]
                result = {
                    "Company": c.name,
                    "Sector": c.sector,
                    "Geography": c.geography,
                    "5D Score": round(fd.overall_score, 2),
                    "Grade": fd.overall_grade,
                    "What": round(fd.what.score, 1),
                    "Who": round(fd.who.score, 1),
                    "How Much": round(fd.how_much.score, 1),
                    "Contribution": round(fd.contribution.score, 1),
                    "Risk": round(fd.risk.score, 1),
                    "Gap Coverage %": gaps["coverage_percentage"],
                    "SDGs": len(top_sdgs),
                    "Metrics": len(c.reported_metrics),
                }
                results.append(result)
                company_details[c.name] = {
                    "fd": fd, "gaps": gaps, "sdg": sdg, "company": c,
                }

            df = pd.DataFrame(results)

            st.subheader("Portfolio Overview KPIs")
            kpi_cols = st.columns(5)
            avg_5d = df["5D Score"].mean()
            avg_coverage = df["Gap Coverage %"].mean()
            total_sdgs = df["SDGs"].sum()
            total_metrics = df["Metrics"].sum()
            kpi_cols[0].metric("Avg 5D Score", f"{avg_5d:.2f}/5")
            kpi_cols[1].metric("Avg Coverage", f"{avg_coverage:.0f}%")
            kpi_cols[2].metric("Companies", len(companies))
            kpi_cols[3].metric("Total Metrics", total_metrics)
            kpi_cols[4].metric("SDG Coverage", f"{total_sdgs} alignments")

            giin_comparison = compare_to_giin_survey(avg_5d, avg_coverage, len(set().union(*[set(c.sdg_claims) for c in companies])))
            if giin_comparison:
                st.subheader("GIIN Survey Benchmark Comparison")
                giin_cols = st.columns(3)
                for i, (key, label) in enumerate([
                    ("five_d_score", "5D Score"),
                    ("core_metric_coverage", "Metric Coverage"),
                    ("sdg_count", "SDG Count"),
                ]):
                    comp = giin_comparison["comparisons"].get(key, {})
                    if comp:
                        delta = comp.get("delta", 0)
                        giin_cols[i].metric(
                            label,
                            f"{comp.get('fund', 0)}",
                            delta=f"{delta:+.1f} vs GIIN",
                            delta_color="normal" if delta >= 0 else "inverse",
                        )

            st.subheader("Company Comparison")
            st.dataframe(df, use_container_width=True)

            col_chart1, col_chart2 = st.columns(2)
            with col_chart1:
                fig = px.bar(df, x="Company", y="5D Score", color="Grade",
                             title="5-Dimension Scores by Company")
                st.plotly_chart(fig, use_container_width=True)

            with col_chart2:
                if "Sector" in df.columns:
                    sector_df = df.groupby("Sector").agg({"5D Score": "mean", "Company": "count"}).reset_index()
                    sector_df.columns = ["Sector", "Avg 5D Score", "Count"]
                    fig2 = px.bar(sector_df, x="Sector", y="Avg 5D Score", text="Count",
                                  title="Average Score by Sector")
                    st.plotly_chart(fig2, use_container_width=True)

            st.subheader("Company Drill-Down")
            selected = st.selectbox("Select a company", [c.name for c in companies])
            if selected and selected in company_details:
                detail = company_details[selected]
                fd = detail["fd"]
                gaps = detail["gaps"]
                sdg_list = detail["sdg"]
                c = detail["company"]

                dc1, dc2 = st.columns(2)
                with dc1:
                    st.write(f"**{c.name}** ({c.sector})")
                    if c.geography:
                        st.write(f"Geography: {c.geography}")
                    st.write(f"Description: {c.description[:300]}")
                    st.write(f"5D Score: **{fd.overall_score:.1f}/5** (Grade: {fd.overall_grade})")
                    st.write(f"Core Metric Coverage: {gaps['coverage_percentage']}%")

                with dc2:
                    dims = ["What", "Who", "How Much", "Contribution", "Risk"]
                    scores = [fd.what.score, fd.who.score, fd.how_much.score, fd.contribution.score, fd.risk.score]
                    fig_radar = go.Figure(data=go.Scatterpolar(
                        r=scores + [scores[0]], theta=dims + [dims[0]],
                        fill='toself', fillcolor='rgba(25,118,210,0.12)',
                        line=dict(color='#1976d2', width=2.5),
                    ))
                    fig_radar.update_layout(
                        polar=dict(radialaxis=dict(visible=True, range=[0, 5])),
                        height=300, margin=dict(l=60, r=60, t=30, b=30),
                        showlegend=False,
                    )
                    st.plotly_chart(fig_radar, use_container_width=True)

                top_sdgs = sorted([a for a in sdg_list if a.score > 0], key=lambda a: a.score, reverse=True)[:5]
                if top_sdgs:
                    st.write("**Top SDG Alignments:**")
                    for a in top_sdgs:
                        st.write(f"  SDG {a.goal} ({a.goal_name}): {a.score:.0f}/100 [{a.confidence}]")


if __name__ == "__main__":
    main()

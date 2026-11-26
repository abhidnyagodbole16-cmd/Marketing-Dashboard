# reports.py - builds the campaign report, marketing summary and monthly report (Module 5)

import io
import pandas as pd
from src.kpis import (kpis_by, overall_kpis, social_kpis_by, overall_social_kpis,
                      web_kpis_by, overall_web_kpis)
from src.insights import generate_insights, inr


# round the number columns so the report looks tidy
def round_table(df):
    return df.round(2)


# one row per campaign with all KPIs, best ROI first
def campaign_report(campaigns):
    camp = kpis_by(campaigns, "campaign_name")
    channel_of = campaigns.drop_duplicates("campaign_name").set_index("campaign_name")["channel"]
    camp.insert(1, "channel", camp["campaign_name"].map(channel_of))
    return round_table(camp.sort_values("roi", ascending=False))


# the overall numbers plus a table per channel, platform and traffic source
def marketing_summary(campaigns, social, traffic):
    k = overall_kpis(campaigns)
    overall = pd.DataFrame({
        "Metric": ["Total spend", "Total revenue", "ROI (%)", "CTR (%)", "Conversion rate (%)",
                   "CPA", "Impressions", "Clicks", "Conversions", "Engagement rate (%)"],
        "Value": [k["spend"], k["revenue"], k["roi"], k["ctr"], k["conversion_rate"],
                  k["cpa"], k["impressions"], k["clicks"], k["conversions"], k["engagement_rate"]],
    })
    tables = {"Overall KPIs": round_table(overall),
              "By channel": round_table(kpis_by(campaigns, "channel").sort_values("roi", ascending=False))}
    if len(social) > 0:
        tables["Social media"] = round_table(social_kpis_by(social, "platform"))
    if len(traffic) > 0:
        tables["Website traffic"] = round_table(web_kpis_by(traffic, "source"))
    return tables


# month looks like '2025-03'. Returns (tables, summary_text)
def monthly_report(campaigns, social, traffic, month):
    def in_month(df, m):
        return df[df["date"].dt.strftime("%Y-%m") == m]

    camp_m = in_month(campaigns, month)
    soc_m = in_month(social, month)
    web_m = in_month(traffic, month)

    # previous month, for the comparison
    prev_month = (pd.Timestamp(month + "-01") - pd.DateOffset(months=1)).strftime("%Y-%m")
    camp_prev = in_month(campaigns, prev_month)

    k = overall_kpis(camp_m)
    lines = [f"# Monthly Analytics Report: {pd.Timestamp(month + '-01').strftime('%B %Y')}", "",
             "(Synthetic dataset - figures are illustrative.)", "",
             "## Headline numbers",
             f"- Spend: {inr(k['spend'])}",
             f"- Revenue: {inr(k['revenue'])}",
             f"- ROI: {k['roi']:.1f}%",
             f"- CTR: {k['ctr']:.2f}% | Conversion rate: {k['conversion_rate']:.2f}% | CPA: {inr(k['cpa'])}"]

    comparison = None
    if len(camp_prev) > 0:
        kp = overall_kpis(camp_prev)
        def change(a, b):
            return (a - b) / b * 100
        comparison = pd.DataFrame({
            "Metric": ["Spend", "Revenue", "ROI (%)", "Conversions"],
            "This month": [k["spend"], k["revenue"], k["roi"], k["conversions"]],
            "Last month": [kp["spend"], kp["revenue"], kp["roi"], kp["conversions"]],
        })
        comparison["Change (%)"] = (comparison["This month"] - comparison["Last month"]) / comparison["Last month"] * 100
        lines += ["", "## Compared with the previous month",
                  f"- Revenue changed by {change(k['revenue'], kp['revenue']):+.1f}%",
                  f"- Spend changed by {change(k['spend'], kp['spend']):+.1f}%",
                  f"- ROI moved from {kp['roi']:.1f}% to {k['roi']:.1f}%"]

    ch = kpis_by(camp_m, "channel").sort_values("roi", ascending=False)
    camp = campaign_report(camp_m)
    lines += ["", "## Highlights",
              f"- Best channel by ROI: {ch.iloc[0]['channel']} ({ch.iloc[0]['roi']:.0f}%)",
              f"- Weakest channel by ROI: {ch.iloc[-1]['channel']} ({ch.iloc[-1]['roi']:.0f}%)",
              f"- Best campaign: {camp.iloc[0]['campaign_name']} ({camp.iloc[0]['roi']:.0f}% ROI)"]
    if len(soc_m) > 0:
        s = overall_social_kpis(soc_m)
        lines.append(f"- Social media: {int(s['posts'])} posts, engagement rate {s['engagement_rate']:.2f}%")
    if len(web_m) > 0:
        w = overall_web_kpis(web_m)
        lines.append(f"- Website: {w['sessions']:,.0f} sessions, bounce rate {w['bounce_rate']:.1f}%")

    tables = {"By channel": round_table(ch), "By campaign": camp}
    if comparison is not None:
        tables["Vs previous month"] = round_table(comparison)
    if len(soc_m) > 0:
        tables["Social media"] = round_table(social_kpis_by(soc_m, "platform"))
    if len(web_m) > 0:
        tables["Website traffic"] = round_table(web_kpis_by(web_m, "source"))
    return tables, "\n".join(lines)


# put several tables into one Excel file (one sheet each) and return the bytes
def to_excel_bytes(tables):
    buffer = io.BytesIO()
    with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
        for name, table in tables.items():
            table.to_excel(writer, sheet_name=name[:31], index=False)
    return buffer.getvalue()


# the insights page as a markdown text file
def insights_text(campaigns, social, traffic):
    findings, recs = generate_insights(campaigns, social, traffic)
    lines = ["# Business Insights & Recommendations", "", "(Synthetic dataset - 'in this dataset...')", ""]
    for section, items in findings.items():
        if items:
            lines += [f"## {section}"] + [f"- {i}" for i in items] + [""]
    lines += ["## Recommendations"] + [f"{n}. {r}" for n, r in enumerate(recs, 1)]
    return "\n".join(lines)

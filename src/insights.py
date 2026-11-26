# insights.py - turns the numbers into written findings and recommendations (Module 4)
# Everything here is calculated from the data, so the text changes when the filters change.

import pandas as pd
from src.kpis import kpis_by, social_kpis_by, web_kpis_by, channel_funnel

MONTH_NAMES = ["Jan", "Feb", "Mar", "Apr", "May", "Jun",
               "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]


# write a rupee amount the Indian way: lakh (L) and crore (Cr)
def inr(x):
    if abs(x) >= 1e7:
        return f"₹{x / 1e7:.2f} Cr"
    if abs(x) >= 1e5:
        return f"₹{x / 1e5:.1f} L"
    return f"₹{x:,.0f}"


# one row per month with spend, revenue, ROI and engagement rate
def monthly_table(campaigns):
    df = campaigns.copy()
    df["month_num"] = df["date"].dt.month
    m = df.groupby("month_num")[["spend", "revenue", "likes", "shares", "comments", "reach"]].sum().reset_index()
    m["month"] = m["month_num"].apply(lambda n: MONTH_NAMES[n - 1])
    m["roi"] = (m["revenue"] - m["spend"]) / m["spend"] * 100
    m["engagement_rate"] = (m["likes"] + m["shares"] + m["comments"]) / m["reach"] * 100
    return m


# returns (findings, recommendations). findings is a dictionary: section name -> list of sentences
def generate_insights(campaigns, social, traffic):
    findings = {"Channels": [], "Campaigns": [], "Trends & patterns": [],
                "Social media": [], "Website traffic": []}
    recs = []

    # channels
    ch = kpis_by(campaigns, "channel")
    if len(ch) >= 2:
        best = ch.loc[ch["roi"].idxmax()]
        worst = ch.loc[ch["roi"].idxmin()]
        findings["Channels"].append(
            f"{best['channel']} has the highest ROI in this dataset ({best['roi']:.0f}%), "
            f"while {worst['channel']} has the lowest ({worst['roi']:.0f}%).")

        if worst["roi"] < 0:
            findings["Channels"].append(
                f"{worst['channel']} loses money: it spent {inr(worst['spend'])} "
                f"and earned {inr(worst['revenue'])} in revenue.")

        top_conv = ch.loc[ch["conversion_rate"].idxmax()]
        findings["Channels"].append(
            f"{top_conv['channel']} converts best: {top_conv['conversion_rate']:.1f}% of its clicks "
            f"become customers.")

        top_ctr = ch.loc[ch["ctr"].idxmax()]
        findings["Channels"].append(
            f"{top_ctr['channel']} has the best click-through rate ({top_ctr['ctr']:.2f}%).")

        cheapest = ch.loc[ch["cpa"].idxmin()]
        costliest = ch.loc[ch["cpa"].idxmax()]
        findings["Channels"].append(
            f"Acquiring a customer costs {inr(cheapest['cpa'])} on {cheapest['channel']} "
            f"but {inr(costliest['cpa'])} on {costliest['channel']}.")

        # share of spend vs share of revenue
        total_spend, total_rev = ch["spend"].sum(), ch["revenue"].sum()
        spend_share = best["spend"] / total_spend * 100
        rev_share = best["revenue"] / total_rev * 100
        findings["Channels"].append(
            f"{best['channel']} receives {spend_share:.0f}% of the budget but brings in "
            f"{rev_share:.0f}% of the revenue.")

        ranked = ch.sort_values("roi", ascending=False)
        second = ranked.iloc[1]
        recs.append(
            f"Test moving part of the {worst['channel']} budget to {best['channel']} and "
            f"{second['channel']}, and watch whether their returns hold as spend grows "
            f"(returns usually fall as a channel gets bigger).")
        if worst["roi"] < 0:
            recs.append(
                f"Review {worst['channel']} before spending more on it: improve the targeting or "
                f"creative first, or pause its weakest campaigns.")

    # campaigns
    camp = kpis_by(campaigns, "campaign_name")
    channel_of = campaigns.drop_duplicates("campaign_name").set_index("campaign_name")["channel"]
    camp["channel"] = camp["campaign_name"].map(channel_of)
    if len(camp) >= 2:
        best_c = camp.loc[camp["roi"].idxmax()]
        worst_c = camp.loc[camp["roi"].idxmin()]
        top_rev = camp.loc[camp["revenue"].idxmax()]
        findings["Campaigns"].append(
            f"Best campaign by ROI: {best_c['campaign_name']} ({best_c['channel']}) at {best_c['roi']:.0f}%.")
        findings["Campaigns"].append(
            f"Biggest revenue earner: {top_rev['campaign_name']} with {inr(top_rev['revenue'])}.")
        findings["Campaigns"].append(
            f"Weakest campaign by ROI: {worst_c['campaign_name']} ({worst_c['channel']}) at {worst_c['roi']:.0f}%.")
        losing = camp[camp["roi"] < 0]
        if len(losing) > 0:
            names = ", ".join(losing["campaign_name"])
            findings["Campaigns"].append(f"{len(losing)} campaign(s) have negative ROI: {names}.")
            recs.append(f"Fix or stop the campaigns with negative ROI ({names}).")
        recs.append(f"Scale up '{best_c['campaign_name']}' step by step, since it has the best ROI.")

    # trends
    m = monthly_table(campaigns)
    if len(m) >= 3:
        best_m = m.loc[m["revenue"].idxmax()]
        worst_m = m.loc[m["revenue"].idxmin()]
        findings["Trends & patterns"].append(
            f"Revenue peaks in {best_m['month']} ({inr(best_m['revenue'])}) and is lowest in "
            f"{worst_m['month']} ({inr(worst_m['revenue'])}).")

        best_roi_m = m.loc[m["roi"].idxmax()]
        findings["Trends & patterns"].append(
            f"ROI is best in {best_roi_m['month']} ({best_roi_m['roi']:.0f}%).")

        last, prev = m.iloc[-1], m.iloc[-2]
        change = (last["revenue"] - prev["revenue"]) / prev["revenue"] * 100
        direction = "up" if change >= 0 else "down"
        findings["Trends & patterns"].append(
            f"In the latest month ({last['month']}) revenue is {direction} {abs(change):.1f}% "
            f"compared with {prev['month']}.")

        festive = m[m["month_num"].isin([10, 11])]
        other = m[~m["month_num"].isin([10, 11])]
        if len(festive) > 0 and len(other) > 0:
            lift = (festive["revenue"].mean() / other["revenue"].mean() - 1) * 100
            word = "higher" if lift >= 0 else "lower"
            findings["Trends & patterns"].append(
                f"Average monthly revenue in Oct-Nov (festive season) is {abs(lift):.0f}% {word} "
                f"than in the other months.")
            if lift > 5:
                recs.append("Plan budgets and creatives for the Oct-Nov festive season early, "
                            "because demand is visibly higher then.")

        best_e = m.loc[m["engagement_rate"].idxmax()]
        findings["Trends & patterns"].append(
            f"Campaign engagement rate is highest in {best_e['month']} ({best_e['engagement_rate']:.2f}%).")

    # social media
    if len(social) > 0:
        plat = social_kpis_by(social, "platform")
        best_p = plat.loc[plat["engagement_rate"].idxmax()]
        findings["Social media"].append(
            f"{best_p['platform']} has the highest engagement rate ({best_p['engagement_rate']:.2f}%).")

        types = social_kpis_by(social, ["platform", "post_type"])
        types = types[types["posts"] >= 5]  # ignore tiny groups
        if len(types) >= 2:
            best_t = types.loc[types["engagement_rate"].idxmax()]
            worst_t = types.loc[types["engagement_rate"].idxmin()]
            findings["Social media"].append(
                f"The best-performing format is {best_t['post_type']} on {best_t['platform']} "
                f"({best_t['engagement_rate']:.2f}% engagement), the weakest is "
                f"{worst_t['post_type']} on {worst_t['platform']} ({worst_t['engagement_rate']:.2f}%).")
            recs.append(
                f"Post more {best_t['post_type']} content on {best_t['platform']} and less "
                f"{worst_t['post_type']} content on {worst_t['platform']}.")

        top_growth = plat.loc[plat["follower_growth_rate"].idxmax()]
        findings["Social media"].append(
            f"{top_growth['platform']} gains followers fastest relative to reach "
            f"({top_growth['follower_growth_rate']:.2f} new followers per 100 people reached).")

    # website
    if len(traffic) > 0:
        src = web_kpis_by(traffic, "source")
        biggest = src.loc[src["sessions"].idxmax()]
        share = biggest["sessions"] / src["sessions"].sum() * 100
        findings["Website traffic"].append(
            f"{biggest['source']} is the biggest traffic source ({share:.0f}% of all sessions).")

        low_b = src.loc[src["bounce_rate"].idxmin()]
        high_b = src.loc[src["bounce_rate"].idxmax()]
        findings["Website traffic"].append(
            f"Visitors from {low_b['source']} stay engaged most (bounce rate {low_b['bounce_rate']:.0f}%), "
            f"while {high_b['source']} visitors leave fastest (bounce rate {high_b['bounce_rate']:.0f}%).")
        recs.append(
            f"Improve the landing page for {high_b['source']} traffic, because it has the highest bounce rate.")

        longest = src.loc[src["avg_session_duration"].idxmax()]
        findings["Website traffic"].append(
            f"{longest['source']} visitors spend the longest on the site "
            f"({longest['avg_session_duration']:.0f} seconds per session).")

        funnel = channel_funnel(campaigns, traffic)
        if len(funnel) >= 2:
            cheap = funnel.loc[funnel["cost_per_session"].idxmin()]
            rich = funnel.loc[funnel["revenue_per_session"].idxmax()]
            findings["Website traffic"].append(
                f"Among paid channels, {cheap['channel']} brings the cheapest website visits "
                f"({inr(cheap['cost_per_session'])} per session), while {rich['channel']} earns the "
                f"most per visit ({inr(rich['revenue_per_session'])}).")

    return findings, recs

import html
from pathlib import Path

from user_labeling_utils import ROOT_DIR, load_business_by_id, load_users, rank_candidates


REPORT_DIR = ROOT_DIR / "reports"
OUTPUT_PATH = REPORT_DIR / "user_labels_review.html"


def safe_text(value):
    return html.escape(str(value))


def build_item_card(item, ordered):
    restaurant = item["restaurant"]
    tags = ", ".join(restaurant["tags"][:5])

    return f"""
    <div class="item {'positive' if ordered else 'negative'}">
      <div class="item-head">
        <div>
          <div class="name">{safe_text(restaurant['name'])}</div>
          <div class="meta">{safe_text(restaurant['cuisine'])} | {safe_text(restaurant['rating'])} | {safe_text(restaurant['price_range'])}</div>
        </div>
        <div class="pill {'pill-positive' if ordered else 'pill-negative'}">{ordered}</div>
      </div>
      <div class="score-row">
        <div class="score-label">score {item['score']:.2f}</div>
        <div class="score-bar">
          <div class="score-fill" style="width:{min(100, item['score'] * 12)}%"></div>
        </div>
      </div>
      <div class="tags">{safe_text(tags)}</div>
    </div>
    """


def build_user_section(user_row, ranking):
    ranked = ranking["ranked"]
    positive_count = ranking["positive_count"]
    positive_ratio = positive_count / len(ranked) if ranked else 0
    top_items = ranked[:8]
    bottom_items = ranked[-8:] if len(ranked) > 8 else []

    return f"""
    <section class="user-card">
      <div class="user-head">
        <div>
          <h2>{safe_text(user_row['user_id'])}</h2>
          <div class="subtle">
            unseen candidates {len(ranked)} | positives {positive_count} | positive rate {positive_ratio:.0%}
          </div>
        </div>
        <div class="summary-pill">{positive_count}/{len(ranked)}</div>
      </div>
      <div class="bar">
        <div class="bar-positive" style="width:{positive_ratio * 100:.2f}%"></div>
      </div>
      <div class="section-label">Top unseen recommendations</div>
      <div class="items">
        {''.join(build_item_card(item, 1 if item['restaurant_id'] in ranking['positive_ids'] else 0) for item in top_items)}
      </div>
      <div class="section-label">Least likely unseen options</div>
      <div class="items">
        {''.join(build_item_card(item, 1 if item['restaurant_id'] in ranking['positive_ids'] else 0) for item in bottom_items)}
      </div>
    </section>
    """


def main():
    business_by_id = load_business_by_id()
    users = load_users()
    sections = []

    total_positive = 0
    total_items = 0

    for user_row in users:
        ranking = rank_candidates(user_row, business_by_id)
        sections.append(build_user_section(user_row, ranking))
        total_positive += ranking["positive_count"]
        total_items += len(ranking["ranked"])

    REPORT_DIR.mkdir(parents=True, exist_ok=True)

    html_doc = f"""
    <!doctype html>
    <html lang="en">
    <head>
      <meta charset="utf-8" />
      <meta name="viewport" content="width=device-width, initial-scale=1" />
      <title>User Label Review</title>
      <style>
        :root {{
          color-scheme: light;
          --bg: #f7f4ef;
          --panel: #ffffff;
          --text: #1f2937;
          --muted: #6b7280;
          --line: #e5ddd2;
          --green: #2f855a;
          --green-soft: #d7f0df;
          --red: #b42318;
          --red-soft: #fde2dc;
          --accent: #2c5282;
        }}
        * {{ box-sizing: border-box; }}
        body {{
          margin: 0;
          font-family: ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
          background: linear-gradient(180deg, #fbfaf7 0%, var(--bg) 100%);
          color: var(--text);
        }}
        .wrap {{
          max-width: 1200px;
          margin: 0 auto;
          padding: 28px 18px 40px;
        }}
        .hero {{
          background: rgba(255,255,255,0.85);
          border: 1px solid var(--line);
          border-radius: 20px;
          padding: 20px 24px;
          margin-bottom: 20px;
          box-shadow: 0 12px 30px rgba(31,41,55,0.06);
        }}
        h1 {{ margin: 0 0 8px; font-size: 30px; }}
        .hero p {{ margin: 4px 0; color: var(--muted); }}
        .legend {{
          display: flex;
          gap: 14px;
          margin-top: 12px;
          flex-wrap: wrap;
          color: var(--muted);
          font-size: 14px;
        }}
        .swatch {{
          display: inline-flex;
          align-items: center;
          gap: 8px;
        }}
        .dot {{
          width: 12px;
          height: 12px;
          border-radius: 999px;
        }}
        .green {{ background: var(--green); }}
        .red {{ background: var(--red); }}
        .grid {{
          display: grid;
          gap: 18px;
        }}
        .user-card {{
          background: rgba(255,255,255,0.92);
          border: 1px solid var(--line);
          border-radius: 18px;
          padding: 18px;
          box-shadow: 0 10px 24px rgba(31,41,55,0.05);
        }}
        .user-head {{
          display: flex;
          justify-content: space-between;
          align-items: flex-start;
          gap: 12px;
          margin-bottom: 12px;
        }}
        .user-head h2 {{
          margin: 0;
          font-size: 20px;
        }}
        .subtle {{
          margin-top: 4px;
          color: var(--muted);
          font-size: 14px;
        }}
        .summary-pill, .pill {{
          display: inline-flex;
          align-items: center;
          justify-content: center;
          min-width: 36px;
          padding: 6px 10px;
          border-radius: 999px;
          font-weight: 700;
        }}
        .summary-pill {{
          background: #eff6ff;
          color: var(--accent);
        }}
        .bar {{
          height: 10px;
          background: #f2ede5;
          border-radius: 999px;
          overflow: hidden;
          margin-bottom: 14px;
        }}
        .bar-positive {{
          height: 100%;
          background: linear-gradient(90deg, #3aa66b, #1f7a4c);
        }}
        .section-label {{
          margin: 12px 0 8px;
          font-size: 13px;
          font-weight: 700;
          color: var(--accent);
          text-transform: uppercase;
          letter-spacing: 0.06em;
        }}
        .items {{
          display: grid;
          gap: 10px;
        }}
        .item {{
          border: 1px solid var(--line);
          border-radius: 14px;
          padding: 12px 14px;
        }}
        .positive {{ background: var(--green-soft); }}
        .negative {{ background: var(--red-soft); }}
        .item-head {{
          display: flex;
          justify-content: space-between;
          gap: 12px;
          align-items: flex-start;
        }}
        .name {{
          font-weight: 700;
          margin-bottom: 4px;
        }}
        .meta, .tags, .score-label {{
          color: var(--muted);
          font-size: 13px;
        }}
        .pill-positive {{
          background: rgba(47, 133, 90, 0.16);
          color: var(--green);
        }}
        .pill-negative {{
          background: rgba(180, 35, 24, 0.14);
          color: var(--red);
        }}
        .score-row {{
          display: grid;
          grid-template-columns: 80px 1fr;
          gap: 10px;
          align-items: center;
          margin-top: 10px;
        }}
        .score-bar {{
          height: 8px;
          background: rgba(31,41,55,0.08);
          border-radius: 999px;
          overflow: hidden;
        }}
        .score-fill {{
          height: 100%;
          background: linear-gradient(90deg, #7c9cff, #3b82f6);
        }}
        .tags {{
          margin-top: 8px;
        }}
        .footer {{
          margin-top: 18px;
          color: var(--muted);
          font-size: 13px;
        }}
        @media (max-width: 720px) {{
          .user-head, .item-head, .score-row {{
            grid-template-columns: 1fr;
            display: grid;
          }}
          .user-head {{
            align-items: stretch;
          }}
        }}
      </style>
    </head>
    <body>
      <div class="wrap">
        <div class="hero">
          <h1>User label review</h1>
          <p>History is only used to infer the user profile. Every label below is for a business the user has not seen in their history.</p>
          <p>Total labeled positives: {total_positive} of {total_items} items.</p>
          <div class="legend">
            <span class="swatch"><span class="dot green"></span>ordered = 1</span>
            <span class="swatch"><span class="dot red"></span>ordered = 0</span>
            <span class="swatch">Higher score means a stronger unseen recommendation</span>
          </div>
        </div>
        <div class="grid">
          {''.join(sections)}
        </div>
        <div class="footer">
          Open this file in a browser and scan the top and bottom unseen recommendations for each user.
        </div>
      </div>
    </body>
    </html>
    """

    OUTPUT_PATH.write_text(html_doc, encoding="utf-8")
    print(f"Wrote review report to {OUTPUT_PATH}")


if __name__ == "__main__":
    main()

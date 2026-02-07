from flask import Flask, render_template, jsonify, request
import pandas as pd
import os

app = Flask(__name__)

EXCEL_FILE = "daily_stocks.xlsx"


@app.route('/')
def home():
    return render_template('main.html')


@app.route('/data')
def get_data():
    if not os.path.exists(EXCEL_FILE):
        return jsonify({"error": f"Excel file '{EXCEL_FILE}' not found"}), 404

    try:
        df = pd.read_excel(EXCEL_FILE, header=0)

        required = ['Date', 'Stock', 'Sector']
        missing = [col for col in required if col not in df.columns]
        if missing:
            return jsonify({"error": f"Missing columns: {', '.join(missing)}"}), 400

        df['Date'] = pd.to_datetime(df['Date'], dayfirst=True, errors='coerce')
        df = df.dropna(subset=['Date'])

        df['Date_str'] = df['Date'].dt.strftime('%b %d')
        df = df.sort_values('Date').reset_index(drop=True)

        dates = df['Date_str'].unique().tolist()

        sector_colors = {
            'fmcg': '#60c5f1', 'industrials': '#ff7aa2', 'services': '#7ce38b',
            'auto': '#f5b74a', 'realty': '#8a8df0', 'textiles': '#ff6f91',
            'chemicals': '#f2df4a', 'consumer discretionary': '#3db7a9',
            'financials': '#ff5c5c', 'aerospace & defence': '#9ff1e5',
            'energy': '#e6007a', 'miscellaneous': '#4aa3f0',
            'metals & mining': '#f3a6c8', 'power & utilities': '#d4f26a',
            'healthcare': '#2dd4bf', 'telecom': '#ff8c1a', 'bank': '#ccff00',
            'building materials': '#00ff66', 'it': '#7dd3fc',
            'plastic products': '#ff85b3', 'transportation': '#98e690',
            'telecom-service': '#f6c177', 'media': '#a5b4fc',
            'indices': '#ff6b81', 'n/a': '#f5e663',
            'tech': '#6b7280', 'e-commerce': '#94a3b8'
        }

        def get_text_color(bg_hex):
            bg_hex = bg_hex.lstrip('#')
            try:
                r, g, b = int(bg_hex[0:2], 16), int(bg_hex[2:4], 16), int(bg_hex[4:6], 16)
                lum = (0.299 * r + 0.587 * g + 0.114 * b) / 255
                return '#000000' if lum > 0.58 else '#ffffff'
            except:
                return '#ffffff'

        traces = []
        FIXED_HEIGHT = 1.0

        for sector in df['Sector'].dropna().unique():
            sector_lower = str(sector).lower()
            color = sector_colors.get(sector_lower, '#6b7280')

            sector_df = df[df['Sector'] == sector]
            x, y, texts, hovers, stocks, colors_l = [], [], [], [], [], []

            for date_str in dates:
                day = sector_df[sector_df['Date_str'] == date_str]
                if day.empty:
                    display_stock = ""
                    custom_stock = ""
                    hover = ""
                else:
                    count = len(day)
                    example_stock = str(day['Stock'].iloc[0]).strip()
                    display_stock = f"{example_stock} (+{count-1})" if count > 1 else example_stock
                    custom_stock = example_stock
                    hover = f"{display_stock}<br>{sector}<br>{count} stock{'s' if count > 1 else ''} this day"

                x.append(date_str)
                y.append(FIXED_HEIGHT if display_stock else 0)
                texts.append(display_stock)
                hovers.append(hover)
                stocks.append(custom_stock)
                colors_l.append(color)

            if any(yi > 0 for yi in y):
                traces.append({
                    'type': 'bar',
                    'name': sector,
                    'x': x,
                    'y': y,
                    'text': texts,
                    'textposition': 'auto',
                    'textfont': {'size': 11, 'color': [get_text_color(c) for c in colors_l]},
                    'hovertext': hovers,
                    'hovertemplate': '%{hovertext}<extra></extra>',
                    'customdata': stocks,
                    'marker': {'color': colors_l},
                    'width': 0.75
                })

        # Legend - unique sectors with preserved original casing
        legend = []
        seen = set()
        for sector in sorted(df['Sector'].dropna().unique(), key=str.lower):
            s_lower = str(sector).lower()
            if s_lower in seen:
                continue
            seen.add(s_lower)
            color = sector_colors.get(s_lower, '#6b7280')
            display_name = str(sector).strip()
            legend.append({'name': display_name, 'color': color})

        layout = {
            'barmode': 'stack',
            'title': {'text': 'Daily Stock & Sector Blocks', 'font': {'size': 20, 'color': '#e2e8f0'}, 'x': 0.5, 'y': 0.98},
            'paper_bgcolor': '#0a0f17',
            'plot_bgcolor': '#111827',
            'font': {'color': '#cbd5e1'},
            'height': 740,
            'margin': {'t': 100, 'b': 120, 'l': 60, 'r': 40},
            'xaxis': {'title': 'Date', 'tickangle': -45, 'tickfont': {'size': 13},
                      'gridcolor': 'rgba(59,68,85,0.35)', 'zeroline': False,
                      'showline': True, 'linecolor': 'rgba(59,68,85,0.6)', 'linewidth': 1.5,
                      'type': 'category'},
            'yaxis': {'title': '', 'showticklabels': False, 'gridcolor': 'rgba(59,68,85,0.35)', 'zeroline': False},
            'legend': {'bgcolor': 'rgba(30,41,59,0.6)', 'bordercolor': 'rgba(59,68,85,0.4)',
                       'font': {'size': 12}, 'orientation': 'h', 'y': 1.12},
            'bargap': 0.08,
            'bargroupgap': 0.05,
            'uniformtext': {'minsize': 9, 'mode': 'hide'}
        }

        return jsonify({'data': traces, 'layout': layout, 'legend': legend})

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/stock/<stock_name>', methods=['GET', 'POST'])
def stock_detail(stock_name):
    if not os.path.exists(EXCEL_FILE):
        return "<h1 style='color:#f87171;'>Excel file not found</h1><a href='/'>Back</a>", 404

    try:
        df = pd.read_excel(EXCEL_FILE)
        stock_name_upper = stock_name.strip().upper()
        stock_df = df[df['Stock'].astype(str).str.strip().str.upper() == stock_name_upper]

        if stock_df.empty:
            return f"""
            <h1 style="color:#f87171;">No data for {stock_name}</h1>
            <p>This stock does not appear in the Excel file.</p>
            <a href="/">← Back to chart</a>
            """, 404

        latest = stock_df.iloc[-1]
        latest_date = latest['Date'].strftime('%d-%m-%Y') if 'Date' in latest and pd.notna(latest['Date']) else 'N/A'
        sector = latest.get('Sector', 'N/A')
        analysis = latest.get('Analysis', 'No analysis available yet.')

        saved_rating_before = str(latest.get('Rating_Before', '')) if 'Rating_Before' in latest else ''
        saved_rating_after  = str(latest.get('Rating_After', '')) if 'Rating_After' in latest else ''
        saved_note = str(latest.get('Note', '')) if 'Note' in latest else ''

        history_rows = ""
        for _, row in stock_df.iterrows():
            d = row['Date'].strftime('%d-%m-%Y') if 'Date' in row and pd.notna(row['Date']) else 'N/A'
            s = row.get('Sector', 'N/A')
            a = row.get('Analysis', '—')
            history_rows += f"""
            <tr>
                <td>{d}</td>
                <td>{s}</td>
                <td style="white-space: pre-wrap;">{a}</td>
            </tr>
            """

        if request.method == 'POST':
            action = request.form.get('action')
            latest_index = stock_df.index[-1]

            try:
                if action == 'save_rating':
                    section = request.form.get('section')
                    rating = request.form.get('rating')
                    if rating in ["Buy", "Sell", "Not"]:
                        column = 'Rating_Before' if section == 'before' else 'Rating_After'
                        df.at[latest_index, column] = rating
                        df.to_excel(EXCEL_FILE, index=False)
                        return jsonify({'success': True, 'message': 'Rating saved'})

                if action == 'save_note':
                    note = request.form.get('note', '').strip()
                    df.at[latest_index, 'Note'] = note
                    df.to_excel(EXCEL_FILE, index=False)
                    return jsonify({'success': True, 'message': 'Note saved'})

            except Exception as save_err:
                return jsonify({'success': False, 'message': f'Error saving: {str(save_err)} (is file open?)'})

        html = f"""
        <!DOCTYPE html>
        <html style="background:#0a0f17; color:#e2e8f0; font-family:'Inter',sans-serif;">
        <head>
            <title>{stock_name}</title>
            <style>
                body {{ padding: 40px 20px; max-width: 1100px; margin: auto; font-size: 1.05rem; }}
                h1 {{ color: #60a5fa; margin-bottom: 0.4em; }}
                .meta {{ color: #94a3b8; margin-bottom: 2rem; font-size: 1.1rem; }}
                h2 {{ color: #cbd5e1; margin: 2.5rem 0 1rem; border-bottom: 1px solid #334155; padding-bottom: 0.5rem; }}
                h3 {{ color: #94a3b8; margin: 2rem 0 1rem; font-size: 1.35rem; }}
                .analysis-box {{ background: #1e293b; padding: 1.6rem; border-radius: 10px; border: 1px solid #334155; white-space: pre-wrap; line-height: 1.6; margin-bottom: 2.5rem; }}
                .rating-section {{ margin-bottom: 3.5rem; }}
                .rating-buttons {{ display: flex; gap: 1.5rem; margin-top: 1.2rem; flex-wrap: wrap; }}
                .rating-btn {{ padding: 0.9rem 2.2rem; border-radius: 12px; border: 2px solid transparent; background: #1e293b; color: white; cursor: pointer; font-weight: 600; transition: all 0.22s; min-width: 130px; text-align: center; font-size: 1.1rem; }}
                .rating-btn.buy {{ background: #16a34a; }}
                .rating-btn.sell {{ background: #dc2626; }}
                .rating-btn.not {{ background: #6b7280; }}
                .rating-btn.selected {{ border: 5px solid #eab308 !important; box-shadow: 0 0 20px #eab308a0; transform: scale(1.1); }}
                .note-area {{ margin: 2.5rem 0 3.5rem; }}
                textarea {{ width: 100%; min-height: 160px; background: #1e293b; color: #e2e8f0; border: 1px solid #334155; border-radius: 10px; padding: 1.2rem; font-family: inherit; font-size: 1rem; resize: vertical; }}
                .save-msg {{ color: #6ee7b7; font-weight: 600; margin: 1rem 0; text-align: center; display: none; }}
                table {{ width: 100%; border-collapse: collapse; margin-top: 1.2rem; font-size: 0.98rem; }}
                th, td {{ padding: 12px 14px; border: 1px solid #334155; text-align: left; }}
                th {{ background: #1e293b; color: #cbd5e1; }}
                .back-link {{ display: inline-block; margin-top: 3rem; color: #60a5fa; text-decoration: none; font-size: 1.1rem; }}
                .back-link:hover {{ text-decoration: underline; }}
            </style>
        </head>
        <body>
            <h1>{stock_name}</h1>
            <div class="meta">Sector: {sector} • Latest: {latest_date}</div>

            <div class="save-msg" id="save-msg"></div>

            <div class="rating-section">
                <h3>Before Entry Result</h3>
                <div class="rating-buttons before">
                    <button class="rating-btn buy" data-value="Buy" data-section="before">Buy</button>
                    <button class="rating-btn sell" data-value="Sell" data-section="before">Sell</button>
                    <button class="rating-btn not" data-value="Not" data-section="before">Not</button>
                </div>
            </div>

            <div class="rating-section">
                <h3>After Entry Result</h3>
                <div class="rating-buttons after">
                    <button class="rating-btn buy" data-value="Buy" data-section="after">Buy</button>
                    <button class="rating-btn sell" data-value="Sell" data-section="after">Sell</button>
                    <button class="rating-btn not" data-value="Not" data-section="after">Not</button>
                </div>
            </div>

            <div class="note-area">
                <h2>Personal Note</h2>
                <textarea id="note">{saved_note}</textarea>
            </div>

            <h2>Latest Analysis</h2>
            <div class="analysis-box">{analysis}</div>

            <h2>History</h2>
            <table>
                <thead><tr><th>Date</th><th>Sector</th><th>Analysis</th></tr></thead>
                <tbody>{history_rows}</tbody>
            </table>

            <a href="/" class="back-link">← Back to chart</a>

            <script>
                const beforeBtns = document.querySelectorAll('.before .rating-btn');
                const afterBtns = document.querySelectorAll('.after .rating-btn');

                function highlight(btns, value) {{
                    btns.forEach(btn => {{
                        btn.classList.remove('selected');
                        if (btn.dataset.value === value) btn.classList.add('selected');
                    }});
                }}

                highlight(beforeBtns, "{saved_rating_before}");
                highlight(afterBtns, "{saved_rating_after}");

                function saveRating(btn) {{
                    const section = btn.dataset.section;
                    const value = btn.dataset.value;

                    fetch(window.location.href, {{
                        method: 'POST',
                        headers: {{'Content-Type': 'application/x-www-form-urlencoded'}},
                        body: `action=save_rating&section=${{section}}&rating=${{encodeURIComponent(value)}}`
                    }}).then(r => r.json()).then(d => {{
                        if (d.success) {{
                            document.getElementById('save-msg').innerText = 'Rating updated ✓';
                            document.getElementById('save-msg').style.display = 'block';
                            setTimeout(() => document.getElementById('save-msg').style.display = 'none', 3000);
                        }} else {{
                            alert(d.message || 'Failed to save');
                        }}
                    }});
                }}

                beforeBtns.forEach(btn => btn.addEventListener('click', () => {{
                    beforeBtns.forEach(b => b.classList.remove('selected'));
                    btn.classList.add('selected');
                    saveRating(btn);
                }}));

                afterBtns.forEach(btn => btn.addEventListener('click', () => {{
                    afterBtns.forEach(b => b.classList.remove('selected'));
                    btn.classList.add('selected');
                    saveRating(btn);
                }}));

                const noteTextarea = document.getElementById('note');
                let originalNote = noteTextarea.value;

                noteTextarea.addEventListener('blur', function() {{
                    const note = this.value.trim();
                    if (note === originalNote.trim()) return;
                    originalNote = note;

                    fetch(window.location.href, {{
                        method: 'POST',
                        headers: {{'Content-Type': 'application/x-www-form-urlencoded'}},
                        body: `action=save_note&note=${{encodeURIComponent(note)}}`
                    }}).then(r => r.json()).then(d => {{
                        if (d.success) {{
                            document.getElementById('save-msg').innerText = 'Note saved ✓';
                            document.getElementById('save-msg').style.display = 'block';
                            setTimeout(() => document.getElementById('save-msg').style.display = 'none', 3000);
                        }} else {{
                            alert(d.message || 'Failed to save note');
                        }}
                    }});
                }});
            </script>
        </body>
        </html>
        """
        return html

    except Exception as e:
        return f"<h1 style='color:#f87171;'>Error loading data</h1><p>{str(e)}</p><a href='/'>Back</a>", 500


@app.route('/strike-summary')
def strike_summary():
    if not os.path.exists(EXCEL_FILE):
        return jsonify({"error": "Excel not found"}), 404

    try:
        df = pd.read_excel(EXCEL_FILE)
        df['Stock'] = df['Stock'].astype(str).str.strip()
        df['Rating_Before'] = df['Rating_Before'].astype(str).str.strip()
        df['Rating_After'] = df['Rating_After'].astype(str).str.strip()

        valid = df[
            df['Rating_Before'].isin(['Buy', 'Sell', 'Not']) &
            df['Rating_After'].isin(['Buy', 'Sell', 'Not'])
        ].copy()

        if valid.empty:
            return jsonify({"has_data": False, "message": "No rated entries yet"})

        total_count = len(valid)
        total_correct = (valid['Rating_Before'] == valid['Rating_After']).sum()
        overall_pct = round(total_correct / total_count * 100, 1) if total_count > 0 else 0

        per_stock = valid.groupby('Stock').agg(
            rated=('Stock', 'size'),
            correct=('Rating_Before', lambda x: (x == valid.loc[x.index, 'Rating_After']).sum())
        ).reset_index()

        per_stock['pct'] = (per_stock['correct'] / per_stock['rated'] * 100).round(1)
        per_stock = per_stock.sort_values('pct', ascending=False)

        return jsonify({
            "has_data": True,
            "overall": {"pct": overall_pct, "correct": int(total_correct), "total": int(total_count)},
            "stocks": per_stock.to_dict(orient='records')[:25]  # limit shown stocks
        })

    except Exception as e:
        return jsonify({"error": str(e)}), 500


if __name__ == '__main__':
    app.run(debug=True, port=5000)
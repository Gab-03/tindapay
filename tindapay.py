import base64
import io
from dash import Dash, dcc, html, dash_table, Input, Output, State
import plotly.express as px
import pandas as pd

app = Dash(__name__, suppress_callback_exceptions=True)
server = app.server

app.layout = html.Div([
    html.H1('Upload TindaPay Dashboard Data', style={'textAlign': 'center'}),
    dcc.Upload(
        id='upload-data',
        children=html.Div([
            'Drag and Drop or ',
            html.A('Select Files')
        ]),
        style={
            'width': '100%',
            'height': '60px',
            'lineHeight': '60px',
            'borderWidth': '1px',
            'borderStyle': 'dashed',
            'borderRadius': '5px',
            'textAlign': 'center',
            'margin': '10px'
        },
        multiple=True
    ),
    html.Div(id='output-data-upload', children=[]),
    html.Div(id='outlet-data-container', children=[
        html.H2('Outlet Stores Performance', style={'textAlign': 'center','width':'100%'}),
        dash_table.DataTable(
            id='outlet-table',
            columns=[
                {'name': 'Outlet Code', 'id': 'Outlet Code'},
                {'name': 'Outlet Name', 'id': 'Outlet Name'},
                {'name': 'Amount Pending', 'id': 'Amount Pending'},
                {'name': 'Ageing', 'id': 'Ageing'}
            ],
            style_data_conditional=[
                {
                    'if': {'filter_query': '{Ageing} < 7', 'column_id': 'Ageing'},
                    'backgroundColor': 'green',
                    'color': 'white'
                },
                {
                    'if': {'filter_query': '{Ageing} = 7', 'column_id': 'Ageing'},
                    'backgroundColor': 'yellow',
                    'color': 'black'
                },
                {
                    'if': {'filter_query': '{Ageing} >= 8', 'column_id': 'Ageing'},
                    'backgroundColor': 'red',
                    'color': 'white'
                },
            ],
        ),
    ], style={'display': 'none'}),
])

@app.callback(
    Output('output-data-upload', 'children'),
    Output('outlet-table', 'data'),
    Output('outlet-data-container', 'style'),
    [Input('upload-data', 'contents')],
    [State('upload-data', 'filename'),
     State('upload-data', 'last_modified')],
    prevent_initial_call=True
)
def update_output(contents, filename, date):
    children = []  # Initialize as an empty list at the start of the callback
    outlet_data = []
    if contents is not None:
        for i, (c, n, d) in enumerate(zip(contents, filename, date)):
            content_type, content_string = c.split(',')
            decoded = base64.b64decode(content_string)
            try:
                if 'csv' in n:
                    df = pd.read_csv(io.StringIO(decoded.decode('utf-8')))
                elif 'xls' in n:
                    df_usage = pd.read_excel(io.BytesIO(decoded), sheet_name="TINDAPAY", skiprows=1, usecols='A:B')
                    df_repeat = pd.read_excel(io.BytesIO(decoded), sheet_name="TINDAPAY", skiprows=1, usecols='D:F')
                    df_repayment = pd.read_excel(io.BytesIO(decoded), sheet_name="TINDAPAY", skiprows=1, usecols='H:K')
                    df_repayment2 = pd.read_excel(io.BytesIO(decoded), sheet_name="TINDAPAY", skiprows=1, usecols='M:P')
                    df_outlet = pd.read_excel(io.BytesIO(decoded), sheet_name="TINDAPAY", skiprows=1, usecols='R:U')
                    df_gsv1 = pd.read_excel(io.BytesIO(decoded), sheet_name="TINDAPAY", skiprows=1, usecols='W:Y')
                    df_buy1 = pd.read_excel(io.BytesIO(decoded), sheet_name="TINDAPAY", skiprows=1, usecols='AA:AC')
                    df_buy2 = pd.read_excel(io.BytesIO(decoded), sheet_name="TINDAPAY", skiprows=1, usecols='AE:AG')

                    df_dict = {
                        '1. USAGE': df_usage,
                        '2. REPEAT': df_repeat,
                        '3. REPAYMENT 1': df_repayment,
                        '3. REPAYMENT 2': df_repayment2,
                        '4. IMPACT TO GSV': df_gsv1,
                        '4. IMPACT TO GSV 2': df_buy1,
                        '4. IMPACT TO GSV 3': df_buy2
                    }
                    df_outlet = df_outlet.dropna()
                    outlet_data = df_outlet.to_dict('records')

                for sheet_name, df in df_dict.items():
                    children.append(html.Div([
                        dcc.Graph(
                            id={'type': 'dynamic-graph', 'index': f'{i}-{sheet_name}'},
                            figure=create_graph(df, sheet_name)
                        ),
                        html.Hr()
                    ]))
            except Exception as e:
                print(e)
                return html.Div(['There was an error processing this file.']), [], {'display': 'none'}

        return children, outlet_data, {'display': 'block'}
    return "", [], {'display': 'none'}



def create_graph(df, sheet_name):
    fig = None
    if 'WK' in df.columns and 'USAGE' in df.columns:
        fig = px.line(df, x='WK', y='USAGE', title="Usage Rate Over Weeks", labels={'WK': 'Week'})
        fig.update_traces(mode='lines+markers+text', text=df['USAGE'].apply(lambda x: f"{x:.2f}"), textposition='top right')

    elif 'WK.1' in df.columns and 'REPEAT' in df.columns:
        fig = px.bar(df, x='WK.1', y=['REPEAT', 'NEW'], title=" Weekly Repeat and New Counts", 
                      labels={'WK.1': 'Week', 'value': 'Count', 'variable': 'Type'}, barmode='stack')
        # Create text labels for each segment
        df_melted = df.melt(id_vars='WK.1', value_vars=['REPEAT', 'NEW'])
        text_labels = df_melted.groupby(['WK.1', 'variable'])['value'].apply(lambda x: [f"{v:.2f}" for v in x]).reset_index(name='text')
        fig.update_traces(text=df['REPEAT'].apply(lambda x: f"{x:.2f}"), textposition='inside', selector=dict(name='REPEAT'))
        fig.update_traces(text=df['NEW'].apply(lambda x: f"{x:.2f}"), textposition='inside', selector=dict(name='NEW'))

    elif 'WK.2' in df.columns:
        if 'Paid' in df.columns and 'Outstanding' in df.columns:
            df['Outstanding'] = df['Outstanding'].replace('-', 0).astype(float)
            df['Paid'] = df['Paid'].replace('-', 0).astype(float)
            fig = px.bar(df, x='WK.2', y=['Paid', 'Outstanding'], title=f"Total, Paid, and Outstanding Balances",
                          labels={'WK.2': 'Week', 'value': 'Amount', 'variable': 'Balance Type'}, barmode='stack')
            # Create text labels for both segments
            fig.update_traces(text=df['Paid'].apply(lambda x: f"{x:.2f}"), textposition='inside', selector=dict(name='Paid'))
            fig.update_traces(text=df['Outstanding'].apply(lambda x: f"{x:.2f}"), textposition='inside', selector=dict(name='Outstanding'))

    elif 'Week' in df.columns:
        if 'Paid.1' in df.columns and 'Outstanding.1' in df.columns:
            df['Outstanding.1'] = df['Outstanding.1'].replace('-', 0).astype(float)
            df['Paid.1'] = df['Paid.1'].replace('-', 0).astype(float)
            fig = px.bar(df, x='Week', y=['Paid.1', 'Outstanding.1'], title=f"Total, Paid, and Outstanding Balances",
                          labels={'Week': 'Week', 'value': 'Amount', 'variable': 'Balance Type'}, barmode='stack')
            # Create text labels for both segments
            fig.update_traces(text=df['Paid.1'].apply(lambda x: f"{x:.2f}"), textposition='inside', selector=dict(name='Paid.1'))
            fig.update_traces(text=df['Outstanding.1'].apply(lambda x: f"{x:.2f}"), textposition='inside', selector=dict(name='Outstanding.1'))

    elif 'Month' in df.columns and 'GSV (PHP)' in df.columns:
        fig = px.bar(df, x='Month', y=['GSV (PHP)', 'Growth vs Baseline'], title=f"{sheet_name}",
                      labels={'Month': 'Month', 'value': 'Count', 'variable': 'Type'}, barmode='stack')
        # Create text labels for each segment
        df_melted = df.melt(id_vars='Month', value_vars=['GSV (PHP)', 'Growth vs Baseline'])
        text_labels = df_melted.groupby(['Month', 'variable'])['value'].apply(lambda x: [f"{v:.2f}" for v in x]).reset_index(name='text')
        fig.update_traces(text=df['GSV (PHP)'].apply(lambda x: f"{x:.2f}"), textposition='inside', selector=dict(name='GSV (PHP)'))
        fig.update_traces(text=df['Growth vs Baseline'].apply(lambda x: f"{x:.2f}"), textposition='inside', selector=dict(name='Growth vs Baseline'))

    elif 'Month.1' in df.columns and 'No. of Invoices' in df.columns:
        fig = px.bar(df, x='Month.1', y=['No. of Invoices', 'Growth vs Baseline.1'], title=f"{sheet_name}",
                      labels={'Month.1': 'Month', 'value': 'Count', 'variable': 'Type'}, barmode='stack')
        # Create text labels for each segment
        df_melted = df.melt(id_vars='Month.1', value_vars=['No. of Invoices', 'Growth vs Baseline.1'])
        text_labels = df_melted.groupby(['Month.1', 'variable'])['value'].apply(lambda x: [f"{v:.2f}" for v in x]).reset_index(name='text')
        fig.update_traces(text=text_labels['text'], textposition='outside')
        fig.update_traces(text=df['No. of Invoices'].apply(lambda x: f"{x:.2f}"), textposition='inside', selector=dict(name='No. of Invoices'))
        fig.update_traces(text=df['Growth vs Baseline.1'].apply(lambda x: f"{x:.2f}"), textposition='inside', selector=dict(name='Growth vs Baseline.1'))
        
    elif 'Month.2' in df.columns and 'Grew vs. Baseline' in df.columns:
        fig = px.bar(df, x='Month.2', y=['Grew vs. Baseline', 'Did not grow vs. Baseline'], title=f"{sheet_name}",
                      labels={'Month.2': 'Month', 'value': 'Count', 'variable': 'Type'}, barmode='stack')
        # Create text labels for each segment
        df_melted = df.melt(id_vars='Month.2', value_vars=['Grew vs. Baseline', 'Did not grow vs. Baseline'])
        text_labels = df_melted.groupby(['Month.2', 'variable'])['value'].apply(lambda x: [f"{v:.2f}" for v in x]).reset_index(name='text')
        # fig.update_traces(text=text_labels['text'], textposition='outside')
        fig.update_traces(text=df['Grew vs. Baseline'].apply(lambda x: f"{x:.2f}"), textposition='inside', selector=dict(name='Grew vs. Baseline'))
        fig.update_traces(text=df['Did not grow vs. Baseline'].apply(lambda x: f"{x:.2f}"), textposition='inside', selector=dict(name='Did not grow vs. Baseline'))

    if fig is not None:
        fig.update_layout(xaxis=dict(tickmode='linear', dtick=1))  # Ensures every tick on x-axis is labeled

    return fig



if __name__ == '__main__':
    app.run_server(debug=True)
